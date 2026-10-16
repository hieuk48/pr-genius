---
type: Knowledge Bundle
title: PR Genius — the board for the PRs you sent out
description: Project management for your outbound open-source contributions — not a code reviewer. Know which of your open PRs needs you today, and what to do about it.
version: 2.2.3
created: 2026-07-01
updated: 2026-10-17
author: zsxh1990
conforms_to: OKF v0.1 (Sudhakaran88/okf-conformance) + agent_guidelines extension
---
mcp-name: io.github.zsxh1990/pr-genius

# PR Genius

> Somewhere in your GitHub there are PRs you have stopped opening.
>
> One needs a rebase you keep meaning to do. One has been red for four days and
> nobody told you. Three have sat untouched for three weeks. And one you avoid
> entirely, because opening it would mean confirming that it is dead.

**PR Genius is the board for that work** — the contributions you sent out into
other people's repositories, where you have no tracker, no standup, and no
clue.

It is **not** a code reviewer. It never reads your diff and it will never tell
you your code is correct. There are good tools for that, and this is not one of
them.

It answers the question a working contributor actually has on a Tuesday
morning: **of everything I have sent out, what do I touch today — and what
exactly do I do about it?**

[![CI](https://github.com/zsxh1990/pr-genius/actions/workflows/validate.yml/badge.svg)](https://github.com/zsxh1990/pr-genius/actions/workflows/validate.yml)
[![PyPI](https://img.shields.io/pypi/v/prgenius-core)](https://pypi.org/project/prgenius-core/)
[![Python](https://img.shields.io/badge/python-3.9+-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/zsxh1990/pr-genius?style=flat&color=blueviolet)](https://github.com/zsxh1990/pr-genius/blob/main/LICENSE)
[![Glama score](https://glama.ai/mcp/servers/zsxh1990/pr-genius/badges/score.svg)](https://glama.ai/mcp/servers/zsxh1990/pr-genius)
[![GitHub Marketplace](https://img.shields.io/badge/Marketplace-PR%20Genius-blue?logo=github)](https://github.com/marketplace/actions/pr-genius)
[![DSH Plugin](https://img.shields.io/badge/DSH--plugin-pr--genius-blueviolet)](docs/dsh-integration.md)

---

## Why this exists

GitHub remembers the PR.

It does **not** remember why you closed your third attempt on a given repo.
What worked. What didn't. Which reviewer actually answers and which commented
once and vanished. Whether the thing that got you bounced last time was the
size, the missing issue link, or the tone.

That knowledge lives in your head. It dies when the session ends.

PR Genius is where it goes instead.

> A Repo Profile captures the **what** a project wants.
> A case study captures the **how** a contribution landed or died.
> Your own status history captures the **then-what** — how long it waited, what
> changed, whether it ever came back.

Neither a code reviewer nor a chat model can have the third one. They see your
PR once, in someone else's repo. This sees your portfolio over months.

---

## What it knows

| It knows | Why it matters to you |
|---|---|
| **How 67 large projects actually behave** — merge rates, review cadence, what gets closed | You stop guessing what `encode/httpx` wants and start matching it |
| **Why real PRs got rejected** — written down, with the evidence | You stop repeating the mistake that already cost someone else three weeks |
| **What your own PRs did over time** — which state each sat in, for how long | You find out a PR died *while it was dying*, not three weeks later |
| **The policy of the repo you are aiming at** | A `Fixes #N` in the body is still the single most common reason a first PR gets bounced |

Numbers, for the sceptical: 753 loaded patterns, 190 harvested failed-PR
observations, 67 repo profiles, 302 reviewed cases. Those are receipts for the
sentence above, not the point of it — every one of them is verified against the
live tree on each release by `scripts/verify_claims.py`.

---

## The nine states are nine decisions

A number on a dashboard tells you something is wrong. A *state* tells you what
to do about it.

| State | What it means for you today |
|---|---|
| `NEEDS_REBASE` | Twenty minutes of work and this PR is still alive. |
| `CI_FAILING` | It has been red for days and nobody was going to tell you. |
| `STALE_REVIEW` | Someone looked and stopped. Move now or it goes cold. |
| `STALE_NO_REVIEW` | Nobody looked. Wait, ping, or walk away — but decide. |
| `CLEAN` | Leave it alone. That is also a decision worth being told. |
| `WAITING` | Still inside a normal response window. Go do something else. |

Half the value of a board is being told **what not to spend today on**.

---

## The two moments it shows up for

**Before you open something.** Is this ready, or am I about to waste a
maintainer's attention?

```bash
python3 -m prgenius coach "fix: timeout in connection pool" \
  --repo encode/httpx --body "Fixes #4821"
```

Five answers, each with a next move — `READY_TO_SUBMIT`, `FIX_BEFORE_SUBMIT`,
`NEEDS_DISCUSSION`, `IMPROVE_CHANCE`, `ASK_MAINTAINER`. It is read-only and
advisory: it never comments, labels, closes or merges anything.

**After it is out there.** Which of these needs me?

```bash
python3 -m prgenius status --author your-handle
```

Nine states, stale detection, and a suggestion per PR — fix CI, rebase, ping,
wait, or abandon. Run it from cron and it becomes the daily line you actually
read.

---

## Install

```bash
pip install "prgenius-core[mcp]"     # engine + MCP server
```

> **Honest limitation, for now.** The wheel ships the engine, not the knowledge
> bundle — the corpus lives in this repository. Until that is fixed you need a
> checkout and one environment variable:
>
> ```bash
> git clone https://github.com/zsxh1990/pr-genius.git
> export PRGENIUS_REPO_ROOT="$PWD/pr-genius"
> prgenius-core doctor      # tells you exactly what it found and what it did not
> ```
>
> `doctor` is the first thing worth running. It never lies about what is
> missing.

```bash
python3 -m prgenius analyze "feat: add feature" --repo org/repo --body "Fixes #123"
python3 -m prgenius status --author your-handle
python3 -m prgenius profile get owner/name     # what does this project actually want?
```

### CLI reference

Console script is `prgenius-core`; `python3 -m prgenius` is equivalent. Every
command takes `--repo-root` to point at a knowledge-base checkout.

| Command | What it does | Key flags |
|---|---|---|
| `status` | Health of your in-flight outbound PRs | `--author`, `--format json`, `--save-snapshot` |
| `coach` | Ready to open? — exit 0 = pass, 1 = fail | `title`, `--repo`, `--body` |
| `contributor` | Contributor decision (5 actions) | `title`, `--repo`, `--diff-stat` |
| `maintainer` | The maintainer's side of the same call (5 actions) | `title`, `--repo` |
| `analyze` | PR analysis + improvement suggestions | `title`, `--repo`, `--body`, `--diff-stat` |
| `triage` | Policy-aware preflight checks | `title`, `--repo`, `--diff-stat` |
| `profile get` | Show a repo profile | `owner/repo` |
| `profile writeback` | Profile update suggestions (dry-run) | `--author` |
| `auto-ping` | Suggest pings for stale PRs (**dry-run**; `--confirm` acts) | `--author`, `--confirm` |
| `auto-rebase` | Suggest rebases (**dry-run**; `--confirm` acts) | `--author`, `--confirm` |
| `harvest` | A rejected PR → an anti-pattern draft | `owner/repo [number]` |
| `doctor` | Install / knowledge-base / `gh` / MCP self-test | `--format json` |
| `issue` / `issue-batch` | Score one issue, or a labelled batch | `--repo`, `--number`, `--state`, `--limit`, `--format` |
| `review-queue` | Prioritised review-queue digest | `--prs-file` |
| `mcp serve` | MCP server on stdio | — |
| `eval` / `suggest` | Older aliases, kept for compatibility | — |

---

## Where it runs

**From your shell** — what is above.

**From cron**, as the one line you read with coffee:

```bash
# scripts/pr_status_heartbeat.sh --all
0 10 * * * cd /path/to/pr-genius && bash scripts/pr_status_heartbeat.sh --all
```

**As an MCP server**, so your coding agent can read your contribution history
instead of starting from zero every time. 14 tools — `status_prs`,
`contributor_view`, `maintainer_view`, `get_repo_profile`, `search_patterns`
and the rest. See [MCP Configuration](#-mcp-configuration).

**As a GitHub Action** on a repository you maintain — advisory comments on
incoming PRs, never blocking. See [GitHub Action](#-github-action).

**As a DSH (Cordis) plugin**, so the board lives next to the chat you are
already in: sidebar action, session tab, right-hand panel, settings, and
`/prgenius`. See [DSH Plugin](#-dsh-plugin).

---

## What it will never do

Stated plainly, because the rest of this page is worthless if these are fuzzy:

- **It will not tell you your code is correct.** It does not read your diff.
- **It will not write or send anything on your behalf** unless you pass an
  explicit `--confirm`. Every mutating command is dry-run by default.
- **It will not phone home.** Analysis is local: no LLM, no API key, no network
  call. The commands that touch GitHub do it with *your* token and only for PR
  metadata. There is no telemetry — see [docs/ADOPTION_DATA.md](docs/ADOPTION_DATA.md)
  for what is measured instead and why we chose not to build the rest.
- **It will not pretend.** If a fact is not verified, the docs say so. This
  page has been wrong before and the corrections are in the
  [changelog](CHANGELOG.md).

---

## 🤖 GitHub Action

Advisory analysis on incoming PRs to a repository you maintain. It never
blocks a merge and never fails a job — every path degrades to a warning.

```yaml
name: PR Genius
on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  issues: write   # required when comment_mode != never (post/update PR comment)

jobs:
  pr-genius:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: zsxh1990/pr-genius@v2.1.4
        id: pr-genius
        with:
          title: ${{ github.event.pull_request.title }}
          repo: ${{ github.repository }}
          body: ${{ github.event.pull_request.body }}
          pr_number: ${{ github.event.pull_request.number }}
          comment_mode: always   # never | high_risk | always
```

`comment_mode` controls *whether* the analysis is posted as a PR comment:
`never` (default), `high_risk`, or `always` (existing comments are updated in
place — no spam). `comment_on_high_risk: true` still works as an alias.

`comment_format` controls *how long* that comment is:

- `compact` — **default.** A short bullet list: risk tier, finding counts, the
  one-line summary, and a link to the action run. Around 6 lines.
- `verbose` — the full table: every signal, the whole anti-patterns table, the
  full checklist. Can exceed 100 lines.

Any other value falls back to `compact` and warns on the run — a typo is never
a reason to post a 100-line comment. The long form is not gone: it lives on the
run page and in `$GITHUB_STEP_SUMMARY`, which is exactly where the compact
comment points.

> **Behavior change worth knowing:** the default is now `compact`, so workflows
> that set `comment_mode` but not `comment_format` post shorter comments than
> they used to. Set `comment_format: verbose` for the old output.

### Version pins

Use a pinned tag (`@v2.1.4`) for reproducibility. There is **no** floating
`v2` tag; the only floating major is `v1`, frozen at `v1.8.0`.

### Docker image

`ghcr.io/zsxh1990/pr-genius` is available if you prefer not to run the
composite action; see the [docs index](docs/index.md) for the `docker://` form.

---

## 🤖 MCP Configuration

```json
{
  "mcpServers": {
    "pr-genius": {
      "command": "python3",
      "args": ["-m", "prgenius", "mcp", "serve"],
      "env": { "PRGENIUS_REPO_ROOT": "/path/to/pr-genius" }
    }
  }
}
```

14 read-only tools, including `status_prs`, `contributor_view`,
`maintainer_view`, `get_repo_profile`, `get_case_study`, `search_patterns`,
`list_open_prs`, `review_queue`, `profile_writeback_suggestions`,
`prgenius_doctor`. All annotated `readOnlyHint: true` — the surface cannot
write to GitHub.

`diff_stat` is a summary string (`git diff --stat` output). Summary counts
only: the diff body is **not** parsed. Size and impact come from those counts,
or from title keywords when no `diff_stat` is given.

---

## 🧩 DSH Plugin

PR Genius runs as a DSH (Cordis) plugin inside the DeepSeek Harness.

```bash
dsh plugin add pr-genius
```

Or apply the one-line patch in [`cordis.patch.yml`](cordis.patch.yml). Full
guide: [`docs/dsh-integration.md`](docs/dsh-integration.md).

Five surfaces: sidebar footer action (dashboard), conversation tab, right-hand
panel, `/prgenius` command, and settings. The dashboard surface shows knowledge
base scale, install health, and your in-flight PRs.

> **Honesty note.** The DSH plugin has been verified for TypeScript
> compilation, unit tests, and static contract conformance
> (`scripts/check_dsh_plugin_contract.py`, 27/27). It **has** been run in a live
> DSH runtime — that is how issues #100, #101 and #103 were found. What is
> still unverified is the **current** code: the fixes shipped since 2.1.5 have
> not been re-verified in a host, and the version matrix in
> [`docs/compatibility.md`](docs/compatibility.md) is entirely unrun. Treat the
> plugin as **not yet confirmed working end to end**. See
> [`docs/maturity-self-assessment.md`](docs/maturity-self-assessment.md).

---

## 📊 For agents

If you are an LLM reading this to act on someone's behalf: this is a
**knowledge bundle** first and a tool second. The markdown in
`anti-patterns/`, `success-patterns/`, `profiles/`, `pr-observations/` and
`review-cases/` is the durable part. Read [`docs/index.md`](docs/index.md) for
the file map and the intended reading order, then
[`AGENT_GUIDELINES_SCHEMA.md`](AGENT_GUIDELINES_SCHEMA.md) for the
`agent_guidelines` field.

Nothing here is a command for you to execute without checking it. It is data.

---

## 🤝 Contributing

Profiles, case studies and anti-patterns are all welcome — see
[CONTRIBUTING.md](CONTRIBUTING.md). The bottleneck is curation hours per
upstream, not infrastructure: a repo profile is roughly 30 minutes of research
plus the work of landing a supporting PR upstream.

Code of conduct: [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
Security: [SECURITY.md](SECURITY.md) (coordinated disclosure + privacy).

## 中文文档

[README.zh-CN.md](README.zh-CN.md) · [README.zh.md](README.zh.md) ·
[docs/BLOG.md](docs/BLOG.md) — the long-form version of the story above.

## Citation

```bibtex
@software{pr_genius,
  title  = {PR Genius — the board for your outbound open-source contributions},
  author = {zsxh1990},
  year   = {2026},
  url    = {https://github.com/zsxh1990/pr-genius}
}
```
