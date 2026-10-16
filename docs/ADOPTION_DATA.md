---
type: Documentation
description: What PR Genius measures, what it does not, and why there is no adoption telemetry
---

# Adoption data: what we know and what we deliberately do not collect

**Short answer: PR Genius has no adoption telemetry. We do not know how many
people use it, how often any tool is called, or whether our advice was taken.**

This page exists because the README's corpus counts ("N loaded patterns across
M repos") can read like a usage claim. It is not one. It is an inventory of
files in this repository.

## Why there is no telemetry

PR Genius's positioning is that analysis is **local, reproducible and
network-free** — no LLM, no API key, no outbound request while analyzing. That
is not a footnote; it is the reason to choose this over an LLM review bot. A
usage-ping channel would contradict it, even a hashed and opt-in one.

So the trade was made deliberately: we give up adoption numbers and keep the
"nothing leaves your machine during analysis" guarantee intact.

Issue #110 proposed a privacy-preserving opt-in (SHA-1 of input arguments,
`--no-telemetry` as the default for the Action). The design is sound and the
offer is still open — but shipping it is a product decision that changes the
guarantee above, so it is not something to slip in quietly. If it is ever
shipped, it will be announced in `CHANGELOG.md`, documented in `SECURITY.md`,
and **off by default everywhere**.

## What we *do* measure

Everything below is measured **inside this repository**, on data we already
own, and published as artifacts anyone can re-run. None of it observes users.

| What | Where it is measured | What it is not |
|---|---|---|
| Tests pass | `pytest prgenius/tests/` in CI (`validate.yml`) | Not "users are happy" |
| Doc claims match the tree | `scripts/verify_claims.py` (release gate) | Not "the docs are useful" |
| Knowledge-bundle integrity | `validate.py`, `--strict`, `--enforce-evidence` | Not "the patterns are right" |
| Pattern trigger coverage on a real PR corpus | `scripts/measure_pattern_coverage.py` over `review-cases/*.json` | Not "patterns fire in production" |
| Evidence debt on case studies | `validate_checks/review_case_evidence.py` + `validate_checks/evidence_debt_baseline.json` | Not "the evidence is true" |
| Profile / policy freshness | `validate_checks/policy_freshness.py` (90-day threshold) | Not "advice is current" |
| Offline accuracy against public PRs | `scripts/cross_validate.py`, `scripts/score_merge.py` → `predictions/` | Not "our advice helps real contributors" |
| MCP tool surface | `verify_claims.py` counts `@mcp.tool` registrations | Not "these tools are called" |

Third-party badges in the README (PyPI version, Glama score, GitHub
Marketplace) are **their** measurements of us, fetched when you load the page.
They are not a channel we open.

## What we do not know

- Install counts for `prgenius-core` or the GitHub Action
- How often any of the 14 MCP tools is invoked
- Whether any suggestion was adopted, or which ones
- Anything at all about the title, body or diff of a PR you analyze

That last one is the important one. **`analyze_pr` / `coach_pr` / `triage_pr`
do not send your PR anywhere.** They read the local knowledge bundle and return
a verdict. The commands that *do* talk to GitHub (`status`, `auto-ping`,
`auto-rebase`, `update-issue`, `harvest`) fetch PR *metadata* through the API;
they are not part of analysis.

## How the corpus numbers should be read

`README.md` opens with a pattern/repo count. That is a file inventory verified
by `scripts/verify_claims.py` against the live tree on every release build. It
says how large the knowledge bundle is. It says nothing about whether anyone
has read it.

If you want evidence that the bundle is *used*, the honest answer is: we do not
have it, and we chose not to build the instrument that would produce it.
