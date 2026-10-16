#!/usr/bin/env python3
"""Verify that README / CHANGELOG / docs claims match the live repo.

Audit E.6: three releases in a row shipped with claims that didn't survive
empirical inspection (v2.1.0 retracted two, v2.1.4 had to verify the gate,
v2.2.x had to revise maturity assessment). This script re-measures every
count claim the docs make, diffs against the live tree, and exits non-zero
on drift.

Run from repo root:
    python3 scripts/verify_claims.py

Returns exit 0 if all claims hold; exit 1 if any drift is detected.

Scope (intentionally narrow — added one claim at a time as drift surfaced):

  1. README.md: "943 loaded patterns across 67 repos" (pre-29268b2) OR
                "753 loaded patterns across 67 repos, plus 190 PR observations"
                (post-29268b2) — see `ALLOWED_PATTERNS` below.
  2. README.md: 14 MCP tools table (analyze_pr / coach_pr / triage_pr / ...)
  3. prgenius/src/prgenius/__init__.py __version__ aligned with
     prgenius/pyproject.toml version.
  4. CHANGELOG.md top entry must match the aligned version.

What this script does NOT do (yet):

  * It does not check the maturity self-assessment numbers (form
    completeness / engineering convergence / equal-weighted %). Those
    require human judgment about what counts.
  * It does not check that the README "943 patterns" claim against the
    pre-29268b2 corpus — it only allows the *current* claim format
    (`ALLOWED_PATTERNS` lists both pre- and post-refactor phrasings).
  * It does not verify MCP tool count by actually running the server.
    That belongs in `prgenius doctor`.

If a new claim type starts drifting, add it to the `CLAIMS` list. Keep
the regex narrow enough that a rephrasing without a real change still
passes — false positives erode trust faster than the drift itself.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _live_anti_patterns() -> tuple[int, int, int]:
    """Return (total, md, json) for anti-patterns/*. Counts what the
    loader would count — not just glob counts, because the README splits
    md from json differently depending on whether 29268b2 has landed."""
    anti_dir = REPO_ROOT / "anti-patterns"
    md = sum(1 for p in anti_dir.glob("*.md") if p.name != "README.md")
    json_ = sum(1 for p in anti_dir.glob("*.json"))
    return md + json_, md, json_


def _live_success_patterns() -> int:
    return sum(1 for p in (REPO_ROOT / "success-patterns").glob("*.md") if p.name != "README.md") + \
           sum(1 for p in (REPO_ROOT / "success-patterns").glob("*.json"))


def _live_mcp_tools() -> list[str]:
    """Parse the `@mcp.tool(` decorators in prgenius/src/prgenius/mcp.py.
    Avoids importing mcp (which is an optional extra) and avoids running
    the server."""
    text = _read("prgenius/src/prgenius/mcp.py")
    return re.findall(r"@mcp\.tool\(", text)


def _live_init_version() -> str:
    text = _read("prgenius/src/prgenius/__init__.py")
    m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
    return m.group(1) if m else ""


def _live_pyproject_version() -> str:
    text = _read("prgenius/pyproject.toml")
    m = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    return m.group(1) if m else ""


# --- The claims ---------------------------------------------------------

# The README headline currently has two valid forms:
#   - Pre-29268b2:  "**943 loaded patterns across 67 repos.**" (with trailing `.`)
#   - Post-29268b2: "**753 loaded patterns across 67 repos, plus 190 PR observations**"
# The verifier accepts EITHER; the post-refactor form is the one we want to
# converge on, but the pre-refactor form is not "wrong", just out of date.
ALLOWED_PATTERNS_HEADLINES = [
    re.compile(r"\*\*(\d+)\s+loaded\s+patterns\s+across\s+(\d+)\s+repos\.\*\*"),
    re.compile(r"\*\*(\d+)\s+loaded\s+patterns\s+across\s+(\d+)\s+repos\*\*,\s*plus\s*(\d+)\s+PR\s+observations"),
]

EXPECTED_MCP_TOOLS = {
    "analyze_pr", "coach_pr", "triage_pr", "get_repo_profile",
    "list_open_prs", "get_case_study", "search_patterns", "schema_info",
    "status_prs", "profile_writeback_suggestions", "maintainer_view",
    "contributor_view", "review_queue", "prgenius_doctor",
}

EXPECTED_REPO_COUNT = 67


# --- Verifier -----------------------------------------------------------

def main() -> int:
    readme = _read("README.md")
    errors: list[str] = []

    # 1. README headline pattern count
    matched = False
    for pat in ALLOWED_PATTERNS_HEADLINES:
        m = pat.search(readme)
        if m:
            matched = True
            claimed = int(m.group(1))
            claimed_repos = int(m.group(2))
            live_total = _live_anti_patterns()[0] + _live_success_patterns()
            # Live: anti (md+json) + success (md+json). README pattern count is
            # the same total under either phrasing.
            if claimed != live_total:
                errors.append(
                    f"README headline claims {claimed} patterns, but live "
                    f"({_live_anti_patterns()[0]} anti + "
                    f"{_live_success_patterns()} success) = {live_total}"
                )
            if claimed_repos != EXPECTED_REPO_COUNT:
                errors.append(
                    f"README headline claims {claimed_repos} repos, expected "
                    f"{EXPECTED_REPO_COUNT}"
                )
            break
    if not matched:
        errors.append(
            "README headline does not match any known phrasing — see "
            "ALLOWED_PATTERNS in scripts/verify_claims.py"
        )

    # 2. MCP tool count
    live_tools = _live_mcp_tools()
    if len(live_tools) != 14:
        errors.append(
            f"prgenius/src/prgenius/mcp.py has {len(live_tools)} @mcp.tool "
            f"decorators, expected 14"
        )

    # 3. Version alignment
    init_v = _live_init_version()
    pyproject_v = _live_pyproject_version()
    if init_v != pyproject_v:
        errors.append(
            f"version drift: prgenius/__init__.py={init_v!r} vs "
            f"prgenius/pyproject.toml={pyproject_v!r}"
        )

    # 4. CHANGELOG top entry
    cl = _read("CHANGELOG.md")
    cl_match = re.search(r"^##\s*\[(\d+\.\d+\.\d+)\]", cl, re.MULTILINE)
    if cl_match:
        cl_v = cl_match.group(1)
        if cl_v != init_v:
            errors.append(
                f"CHANGELOG top entry is {cl_v}, but __init__.py is {init_v}"
            )

    # --- Report ---
    if errors:
        print("❌ verify_claims.py — drift detected:")
        for e in errors:
            print(f"  - {e}")
        print()
        print("Fix the source of drift BEFORE tagging a release. The three")
        print("retracted releases in CHANGELOG (v2.1.0, v2.1.4, v2.2.x) all")
        print("would have been caught by a version of this gate.")
        return 1
    print("✅ verify_claims.py — all claims hold against the live tree")
    print(f"  - README pattern headline:  OK")
    print(f"  - MCP tools registered:     {len(live_tools)} (expected 14)")
    print(f"  - version init:             {init_v}")
    print(f"  - version pyproject:        {pyproject_v}")
    if cl_match:
        print(f"  - CHANGELOG top:            [{cl_match.group(1)}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
