"""Keyword pass over a unified diff — the static-analysis half, with no LLM.

Why this exists (issue #133 / #127 risk 4): `analyze_pr` used to say, in the
README, "the diff body is not parsed". So a PR adding
`pip install never-existing-package-xyz` scored the same as one that did not,
while the verdict letter read as a judgement about the change. A keyword pass is
the cheapest way to stop that being a lie.

What it is **not**:

* **Not a dependency resolver.** It cannot tell you whether a package exists on
  PyPI, and it makes no network call to find out. It reports the *install
  surface* so a reviewer looks at it.
* **Not an LLM.** Every rule here is a string match you can read in one sitting.
  That is the product's position (#114: rules-only) and this module keeps it.
* **Not a parser.** It reads added lines of a unified diff. Context and removed
  lines are ignored on purpose — `-pip install foo` is a removal, not a risk.

Design note on false positives: a scanner that cries wolf is worse than no
scanner, so the rules are narrow and the output truncates anything secret-shaped
rather than echoing it. The negative tests matter more than the positive ones.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

# ── 命令面：一次新增的安装动作就是一次新的供应链入口 ──────────────────────────
# 故意不含 `pip download` / `npm ci`（不引入新包），也不含 `python -m pip`
# 之外的长尾写法 —— 覆盖不到的写法在 LIMITATIONS 里说清，不假装全覆盖。
_INSTALL_COMMANDS = (
    ("pip install", r"\bpip3?\s+install\b"),
    ("pipx install", r"\bpipx\s+install\b"),
    ("npm install", r"\bnpm(?:\s+i|\s+install)\b"),
    ("yarn add", r"\byarn\s+add\b"),
    ("pnpm add", r"\bpnpm\s+add\b"),
    ("go get", r"\bgo\s+get\b"),
    ("cargo add", r"\bcargo\s+add\b"),
)

# ── 远程代码执行：下载即执行 ────────────────────────────────────────────────
_REMOTE_PIPE = re.compile(
    r"(?:curl|wget)\b[^\n|]{0,400}\|\s*(?:sudo\s+)?(?:bash|sh|zsh|python3?|node)\b"
)

# ── 密钥形状：只报形状，不回显 ──────────────────────────────────────────────
_SECRET_SHAPES = (
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("openai_style_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
)

_LIMITATIONS = (
    "keyword pass over added lines of a unified diff — not a dependency resolver, "
    "not an LLM, not a full parser. It cannot say whether a package exists on "
    "PyPI/npm and makes no network call. Context and removed lines are ignored."
)


def _added_lines(diff: str) -> List[str]:
    """Lines a unified diff adds. `+`-prefixed, but not the `+++` file header."""
    out: List[str] = []
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            out.append(line[1:])
    return out


def _packages_for(command: str, line: str) -> List[str]:
    """Best-effort package list for an install command — names only, no versions.

    Flags are skipped rather than guessed at, so `-r requirements.txt` does not
    come back as a package called `-r`. Unknown shapes yield no names; the hit
    is still reported, because the *command* being added is the thing to review.
    """
    tokens = line.split()
    # drop the command words themselves (e.g. "pip", "install")
    words = tokens[:]
    for pattern_name, pattern in _INSTALL_COMMANDS:
        if re.search(pattern, line):
            # strip everything up to and including the matched command words
            idx = re.search(pattern, line)
            if idx:
                words = line[idx.end():].split()
            break
    names: List[str] = []
    for word in words:
        if word.startswith("-"):
            continue  # flag / option
        if word in {"install", "add", "get"}:
            continue
        # take the bare distribution name; `foo==1.2` -> `foo`, `git+https://` -> skip
        if "://" in word or word.startswith("git+"):
            continue
        names.append(word.split("==")[0].split(">=")[0].split("<=")[0].split("[")[0])
    return names


def _mask(secret: str) -> str:
    """Never echo a secret-shaped string in full."""
    if len(secret) <= 12:
        return secret[:2] + "…" + f"({len(secret)} chars)"
    return f"{secret[:6]}…{secret[-2:]} ({len(secret)} chars)"


def scan_diff(diff: str | None) -> Dict[str, Any]:
    """Scan a unified diff for install surface, remote pipes and secret shapes.

    Returns a dict shaped for the analyze_pr verdict. `diff_scanned` is false
    exactly when no diff was supplied — a reader must never mistake "looked and
    found nothing" for "did not look".
    """
    if diff is None:
        return {
            "diff_scanned": False,
            "finding_count": 0,
            "findings": [],
            "basis": "diff-stat only — the diff body was not provided",
            "limitations": _LIMITATIONS,
        }

    findings: List[Dict[str, Any]] = []
    added = _added_lines(diff)

    for line in added:
        for command_name, pattern in _INSTALL_COMMANDS:
            if re.search(pattern, line):
                findings.append({
                    "family": "install_surface",
                    "severity": "medium",
                    "rule": command_name,
                    "detail": f"new install surface via `{command_name}`",
                    "packages": _packages_for(command_name, line),
                    "line": line.strip()[:200],
                })
                break

    for line in added:
        m = _REMOTE_PIPE.search(line)
        if m:
            findings.append({
                "family": "remote_execution",
                "severity": "high",
                "rule": "download_piped_to_shell",
                "detail": "download is piped straight into an interpreter",
                "line": m.group(0).strip()[:200],
            })

    for line in added:
        for name, pattern in _SECRET_SHAPES:
            m = pattern.search(line)
            if m:
                findings.append({
                    "family": "secret_shaped",
                    "severity": "high",
                    "rule": name,
                    "detail": "looks like a credential; verify it is not real and rotate if it is",
                    "matched": _mask(m.group(0)),
                })

    return {
        "diff_scanned": True,
        "finding_count": len(findings),
        "findings": findings,
        "basis": f"keyword pass over {len(added)} added line(s)",
        "limitations": _LIMITATIONS,
    }
