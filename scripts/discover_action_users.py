#!/usr/bin/env python3
"""Measure what we can and cannot see about who uses pr-genius.

Why this exists
---------------
pr-genius ships no telemetry (docs/ADOPTION_DATA.md). That is deliberate, but
it means the project cannot count its own adoption. This script is the only
passive channel available: it searches public GitHub code for references to
the Action and records the result — including the negative result.

It is a *measurement*, not a dashboard. Its job is to keep us honest about the
difference between "nobody uses this" and "we cannot see who uses this". Those
are very different claims and the README must never blur them.

What it does NOT do
-------------------
* It does not phone home, and it does not instrument anyone. It runs in this
  repository, on a schedule, and reads public code search with a token this
  repository already has.
* It does not claim to find private adopters. It cannot. The gap it reports
  is the point.

Usage
-----
    python3 scripts/discover_action_users.py            # human summary
    python3 scripts/discover_action_users.py --json     # machine output
    python3 scripts/discover_action_users.py --markdown # issue body

Exit codes: 0 = ran and reported (even if zero adopters found), 2 = could not
run at all (no gh / no auth).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
KNOWN_FILE = REPO_ROOT / "docs" / "known-adopters.json"

# What counts as "actually running the tool" versus "mentioning it".
# An awesome-list entry is reach, not usage. A `uses:` line is usage.
USAGE_QUERIES = [
    ("uses-line", 'uses: zsxh1990/pr-genius'),
    ("workflow-yml", "zsxh1990/pr-genius filename:yml"),
]
REACH_QUERIES = [
    ("broad", "zsxh1990/pr-genius"),
]

# Our own repos and the plugin catalogs that mirror us. They show up in every
# search and are not adopters.
OWN_OR_PREFIXES = ("Ikalus1988/", "zsxh1990/")
CATALOG_HINTS = ("awesome-", "catalog/", "/plugins/", "data/plugins", "mirrors/")


def _search(query: str, limit: int = 50) -> list[dict]:
    """Run one gh code search. Returns [] on any failure — never raises, so a
    transient GitHub error cannot turn into a fake 'nobody uses us'."""
    try:
        out = subprocess.run(
            ["gh", "search", "code", query, "--limit", str(limit),
             "--json", "repository,path"],
            capture_output=True, text=True, timeout=60,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"  ! search failed ({query!r}): {exc}", file=sys.stderr)
        return []
    if out.returncode != 0:
        print(f"  ! gh exited {out.returncode} for {query!r}: "
              f"{out.stderr.strip()[:200]}", file=sys.stderr)
        return []
    try:
        return json.loads(out.stdout or "[]")
    except json.JSONDecodeError:
        print(f"  ! unparseable result for {query!r}", file=sys.stderr)
        return []


def _classify(hits: list[dict]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Split into likely-adopters vs catalog/own mentions."""
    adopters: dict[str, list[str]] = {}
    other: dict[str, list[str]] = {}
    for h in hits:
        repo = h.get("repository", {}).get("nameWithOwner", "")
        path = h.get("path", "")
        if not repo:
            continue
        bucket = adopters if _looks_like_adoption(repo, path) else other
        bucket.setdefault(repo, []).append(path)
    return adopters, other


def _looks_like_adoption(repo: str, path: str) -> bool:
    if repo.startswith(OWN_OR_PREFIXES):
        return False
    p = path.lower()
    return not any(hint in p or hint in repo.lower() for hint in CATALOG_HINTS)


def _load_known() -> dict[str, dict]:
    if not KNOWN_FILE.is_file():
        return {}
    try:
        data = json.loads(KNOWN_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def run() -> dict:
    known = _load_known()
    result = {
        "known_adopters_on_file": sorted(known),
        "usage_search": {},
        "reach_search": {},
        "discovered_adopters": [],
        "new_since_last_run": [],
        "unseen_floor": None,
        "notes": [],
    }

    for label, query in USAGE_QUERIES:
        hits = _search(query)
        adopters, other = _classify(hits)
        result["usage_search"][label] = {
            "query": query,
            "raw_hits": len(hits),
            "likely_adopters": sorted(adopters),
            "catalog_or_own": sorted(other),
        }
        for repo in adopters:
            if repo not in result["discovered_adopters"]:
                result["discovered_adopters"].append(repo)

    for label, query in REACH_QUERIES:
        hits = _search(query)
        _, other = _classify(hits)
        result["reach_search"][label] = {
            "query": query,
            "raw_hits": len(hits),
            "non_adoption_mentions": sorted(other),
        }

    discovered = set(result["discovered_adopters"])
    known_set = set(known)
    result["new_since_last_run"] = sorted(discovered - known_set)

    # The number that matters for honesty: how many adopters do we know about
    # by testimony but cannot see in public search? Testimony lives in its own
    # block and may carry a count without names — that is the whole point of
    # recording it, so count it even when we cannot list the repos.
    named_testimony = {
        r for r, meta in known.get("adopters", {}).items()
        if isinstance(meta, dict) and meta.get("source") == "testimony"
    }
    testimony = known.get("testimony") or {}
    claimed = testimony.get("action_reuse_repos") or 0
    names_missing = bool(testimony.get("names_unavailable"))
    unseen_named = named_testimony - discovered
    result["unseen_floor"] = max(len(unseen_named), claimed if names_missing else 0)
    result["unseen_repos"] = sorted(unseen_named)
    result["testimony_claimed_repos"] = claimed
    result["testimony_names_unavailable"] = names_missing

    if result["unseen_floor"]:
        result["notes"].append(
            f"{result['unseen_floor']} known adopter(s) are NOT visible to public "
            f"code search. Public search is not a usage count; never present it "
            f"as one."
        )
    if not result["discovered_adopters"]:
        result["notes"].append(
            "Public code search found no third-party adopters. This is evidence "
            "about the *visibility* of adoption, not about adoption itself."
        )
    return result


def to_markdown(r: dict) -> str:
    lines = [
        "## Who uses pr-genius — measured, not guessed",
        "",
        "This is a **visibility** measurement, not a usage count. See "
        "[docs/EVIDENCE_BOUNTIES.md](../blob/main/docs/EVIDENCE_BOUNTIES.md) "
        "for why the project cannot count adoption and how it asks instead.",
        "",
        "| Channel | Found |",
        "|---|---|",
    ]
    for label, d in r["usage_search"].items():
        lines.append(f"| usage search `{label}` | {d['raw_hits']} raw, "
                     f"{len(d['likely_adopters'])} likely adopters |")
    for label, d in r["reach_search"].items():
        lines.append(f"| reach search `{label}` | {d['raw_hits']} raw, "
                     f"{len(d['non_adoption_mentions'])} non-adopters |")
    lines += [
        "",
        f"- Adopters discovered by search: "
        f"{', '.join(r['discovered_adopters']) or 'none'}",
        f"- Adopters we know by testimony but cannot see: "
        f"{r['unseen_floor']}"
        + (f" ({', '.join(r['unseen_repos'])})" if r.get("unseen_repos") else ""),
        f"- New since last run: "
        f"{', '.join(r['new_since_last_run']) or 'none'}",
        "",
    ]
    if r["notes"]:
        lines.append("> " + "\n> ".join(r["notes"]))
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args()

    if args.json:
        print(json.dumps(run(), indent=2, ensure_ascii=False))
        return 0
    if args.markdown:
        print(to_markdown(run()))
        return 0

    r = run()
    print("pr-genius adopter visibility")
    print("-" * 40)
    for label, d in r["usage_search"].items():
        print(f"  usage  {label:12} raw={d['raw_hits']:3}  "
              f"adopters={len(d['likely_adopters'])}")
    for label, d in r["reach_search"].items():
        print(f"  reach  {label:12} raw={d['raw_hits']:3}  "
              f"non-adopters={len(d['non_adoption_mentions'])}")
    print()
    print(f"  discovered : {', '.join(r['discovered_adopters']) or 'none'}")
    print(f"  unseen     : {r['unseen_floor']}"
          + (f"  ({', '.join(r['unseen_repos'])})" if r.get("unseen_repos") else ""))
    print(f"  new        : {', '.join(r['new_since_last_run']) or 'none'}")
    for n in r["notes"]:
        print(f"\n  NOTE: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
