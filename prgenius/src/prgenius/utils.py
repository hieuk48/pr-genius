"""Shared utilities for pr-genius scripts and CLI.

Extracted from scripts/coach_cases.py and scripts/daily_content_expand.py
to avoid code duplication.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Decision-critical markers: a directory is a knowledge root when it carries
# these two.  ``success-patterns`` is deliberately **not** a marker (issue
# #116): the wheel ships the scoring subset without it, and a root without it
# is still a usable knowledge base — the loader for that corpus degrades to
# empty and `doctor` reports it as not installed.
_KB_MARKERS = ("anti-patterns", "profiles")

# The npm/DSH package name whose install tree carries the full corpus.
_NPM_PACKAGE = "pr-genius"


def _is_kb_root(path: Path) -> bool:
    """True when *path* looks like a pr-genius knowledge root."""
    return path.is_dir() and all((path / m).is_dir() for m in _KB_MARKERS)


def _npm_bundle_roots(here: Path | None = None, cwd: Path | None = None) -> list[Path]:
    """Find ``node_modules/pr-genius`` knowledge bundles near here / cwd.

    The npm package ships the full corpus (it is what the DSH plugin runs
    against), so a wheel install can find it one directory up instead of
    falling back to "no knowledge base".  Walks up from the working directory
    first (how a plugin invocation is usually reached), then from this module.
    """
    here = here or Path(__file__).resolve()
    cwd = cwd or Path.cwd()
    seen: set[Path] = set()
    out: list[Path] = []
    for base in (cwd, here.parent):
        try:
            chain = (base, *base.parents)
        except OSError:  # pragma: no cover - unresolvable cwd
            continue
        for ancestor in chain:
            cand = (ancestor / "node_modules" / _NPM_PACKAGE).resolve()
            if cand in seen:
                continue
            seen.add(cand)
            if _is_kb_root(cand):
                out.append(cand)
    return out


def _iter_kb_candidates(here: Path | None = None, cwd: Path | None = None) -> list[tuple[Path, str]]:
    """Knowledge roots visible from *here*, in resolution order (env excluded).

    Order, and why:
      ``found``         a full checkout above the package — the live tree wins.
      ``package-data``  the corpus bundled into the wheel (issue #116) —
                        version-matched to the code that imported it.
      ``npm-node_modules`` the npm package's corpus (DSH installs already have
                        it; it also carries success-patterns).
      ``dev-layout``    running from a source checkout that was not caught by
                        ``found``.
    """
    here = here or Path(__file__).resolve()
    cwd = cwd or Path.cwd()
    out: list[tuple[Path, str]] = []

    for ancestor in here.parents:
        if _is_kb_root(ancestor):
            out.append((ancestor, "found"))

    bundled = here.parent / "data"
    if _is_kb_root(bundled):
        out.append((bundled, "package-data"))

    for cand in _npm_bundle_roots(here=here, cwd=cwd):
        out.append((cand, "npm-node_modules"))

    # Dev layout: prgenius/src/prgenius/utils.py → repo root is parents[3].
    dev = here.parents[3] if len(here.parents) > 3 else here.parent
    if dev not in {p for p, _ in out} and _is_kb_root(dev):
        out.append((dev, "dev-layout"))

    return out


def _find_repo_root() -> tuple[Path, str]:
    """Locate the pr-genius knowledge root (repo root or bundled corpus).

    Resolution order:
      1. ``PRGENIUS_REPO_ROOT`` env-var (explicit override — trusted even when
         it does not carry the markers, so a partial tree can be pointed at).
      2. The first entry of :func:`_iter_kb_candidates` (see that function for
         the order and the reasoning).

    Returns ``(path, source)`` where source is one of ``env`` / ``found`` /
    ``package-data`` / ``npm-node_modules`` / ``dev-layout`` / ``none``.
    ``none`` means no knowledge bundle was located: the returned path is still
    a real directory, but it is **not** a knowledge root and callers must say
    so instead of pretending.

    Why anything other than "walk up" has to check the markers: for a wheel
    install (``site-packages/prgenius/utils.py``) ``parents[3]`` evaluates to
    the environment's ``lib/`` directory. That looks like a plausible path and
    is not one, so ``prgenius-core doctor`` used to report it as ``repo_root``
    and a new user was told their knowledge base was missing "at /…/lib".
    Check the markers or admit you did not find it.
    """
    # 1. Env-var override
    env = os.environ.get("PRGENIUS_REPO_ROOT")
    if env:
        p = Path(env).resolve()
        if p.is_dir():
            return p, "env"

    candidates = _iter_kb_candidates()
    if candidates:
        return candidates[0]

    return Path(__file__).resolve().parent, "none"


REPO_ROOT, REPO_ROOT_SOURCE = _find_repo_root()


def find_reference_bundles(here: Path | None = None, cwd: Path | None = None) -> list[Path]:
    """Knowledge roots that carry ``success-patterns`` (the reference corpus).

    The wheel ships the decision subset without it (issue #116), so
    ``prgenius doctor`` uses this to name an actionable upgrade path instead
    of just reporting the corpus as absent.
    """
    roots: list[tuple[Path, str]] = []
    env = os.environ.get("PRGENIUS_REPO_ROOT")
    if env:
        p = Path(env).resolve()
        if p.is_dir():
            roots.append((p, "env"))
    roots.extend(_iter_kb_candidates(here=here, cwd=cwd))
    out: list[Path] = []
    seen: set[Path] = set()
    for path, _source in roots:
        if path in seen:
            continue
        seen.add(path)
        if (path / "success-patterns").is_dir():
            out.append(path)
    return out


def get_repo_root_source() -> str:
    """How the knowledge-base root was resolved: env / found / package-data /
    npm-node_modules / dev-layout / none.

    ``none`` means nothing was found — the path from :func:`get_repo_root` is
    not a knowledge base and should be reported as such.
    """
    return REPO_ROOT_SOURCE


def get_repo_root() -> Path:
    """Return the repo root directory containing the knowledge bundle."""
    return REPO_ROOT


def run_gh(args: list[str], timeout: int = 30) -> dict | list | None:
    """Run gh CLI and return JSON result."""
    cmd = ["gh"] + args
    if "--json" not in args:
        cmd += ["--json", "number,title,state,mergedAt,closedAt,author,createdAt,additions,deletions,changedFiles,reviews,comments,labels"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        if result.returncode != 0:
            logger.warning("gh command failed (exit %d): %s", result.returncode, result.stderr.strip())
    except FileNotFoundError:
        logger.error("gh CLI not found — install from https://cli.github.com/")
    except subprocess.TimeoutExpired:
        logger.warning("gh command timed out after %ds", timeout)
    except json.JSONDecodeError as exc:
        logger.warning("gh returned invalid JSON: %s", exc)
    return None


def fetch_recent_prs(repo: str, state: str = "all", limit: int = 10) -> list[dict]:
    """Fetch recent PRs from a repo using gh pr list."""
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--repo", repo, "--state", state,
             "--limit", str(limit), "--json",
             "number,title,state,mergedAt,closedAt,author,createdAt,additions,deletions,changedFiles,reviews,comments,labels,updatedAt"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout.strip():
            prs = json.loads(result.stdout)
            for pr in prs:
                pr["_repo"] = repo
            return prs
        if result.returncode != 0:
            logger.warning("gh pr list failed for %s (exit %d): %s", repo, result.returncode, result.stderr.strip())
    except FileNotFoundError:
        logger.error("gh CLI not found — install from https://cli.github.com/")
    except subprocess.TimeoutExpired:
        logger.warning("gh pr list timed out for %s", repo)
    except json.JSONDecodeError as exc:
        logger.warning("gh pr list returned invalid JSON for %s: %s", repo, exc)
    return []


def _read_profile_text(repo: str, repo_root: Optional[Path] = None) -> Optional[str]:
    """Read repo profile index.md text, or None if missing/inaccessible."""
    root = repo_root or REPO_ROOT
    index_file = root / "profiles" / repo.replace("/", "-") / "index.md"
    if not index_file.exists():
        return None
    try:
        return index_file.read_text()
    except OSError as exc:
        logger.warning("Failed to read profile for %s: %s", repo, exc)
        return None


def get_merge_rate(repo: str, repo_root: Optional[Path] = None) -> float:
    """Read external_merge_rate from repo profile."""
    text = _read_profile_text(repo, repo_root)
    if text is None:
        return 0.0
    m = re.search(r'external_merge_rate:\s*([\d.]+)', text)
    return float(m.group(1)) if m else 0.0


def get_star_count(repo: str, repo_root: Optional[Path] = None) -> int:
    """Read star count from repo profile."""
    text = _read_profile_text(repo, repo_root)
    if text is None:
        return 0
    m = re.search(r'^star:\s*(\d+)', text, re.MULTILINE)
    return int(m.group(1)) if m else 0


def classify_pr(pr: dict) -> str:
    """Classify PR into quality category."""
    state = pr.get("state", "").lower()
    merged = pr.get("mergedAt") is not None
    reviews = pr.get("reviews", [])
    comments = pr.get("comments", [])

    if merged:
        return "merged_success"
    elif state == "closed":
        comment_bodies = " ".join((c.get("body", "") or "").lower() for c in comments)
        if "duplicate" in comment_bodies:
            return "closed_duplicate"
        elif "already" in comment_bodies or "superseded" in comment_bodies:
            return "closed_already_done"
        else:
            return "closed_rejected"
    elif len(reviews) > 0:
        has_critical = any(
            (r.get("state", "") or "").lower() in ("changes_requested", "dismissed")
            for r in reviews
        )
        if has_critical:
            return "review_changes_requested"
        else:
            return "review_approved_pending"
    else:
        return "open_pending"


def extract_signals(pr: dict) -> dict:
    """Extract learning signals from a PR (text + metadata)."""
    body = pr.get("body", "") or ""
    title = pr.get("title", "") or ""
    title_lower = title.lower()
    body_lower = body.lower()

    files = pr.get("changedFiles", 0)
    additions = pr.get("additions", 0)
    deletions = pr.get("deletions", 0)
    total_changes = additions + deletions

    return {
        "has_issue_link": "fixes #" in body_lower or "closes #" in body_lower,
        "has_description": len(body) > 100,
        "has_test_mention": any(w in body_lower for w in ["test", "spec", "coverage"]),
        "has_breaking_change": any(w in title_lower for w in ["breaking", "major", "v2"]),
        "is_docs_only": any(w in title_lower for w in ["docs", "readme", "documentation", ".md"]),
        "is_bug_fix": any(w in title_lower for w in ["fix", "bug", "patch", "hotfix"]),
        "is_feature": any(w in title_lower for w in ["feat", "feature", "add", "support"]),
        "is_refactor": any(w in title_lower for w in ["refactor", "clean", "chore", "perf"]),
        "is_small_pr": files <= 3 and total_changes < 50,
        "is_large_pr": files > 10 or total_changes > 500,
        "is_backport": "backport" in title_lower or "release" in title_lower,
        "is_dependency_update": any(w in title_lower for w in ["bump", "update", "upgrade", "dependabot"]),
        "is_bot_pr": any(w in title_lower for w in ["dependabot", "renovate", "bot", "auto-", "[ci"]),
        "has_reviews": len(pr.get("reviews", [])) > 0,
        "has_comments": len(pr.get("comments", [])) > 0,
        "files_changed": files,
        "additions": additions,
        "deletions": deletions,
        "review_count": len(pr.get("reviews", [])),
        "comment_count": len(pr.get("comments", [])),
        "change_ratio": round(deletions / max(additions, 1), 2),
    }
