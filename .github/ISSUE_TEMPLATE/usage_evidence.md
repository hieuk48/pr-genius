---
type: Community Resource
name: Usage Evidence
about: Report that you use pr-genius, and what it did — this is how the project learns it works
title: '[USAGE] '
labels: usage-evidence
assignees: ''
---

## Why this template exists

pr-genius deliberately ships **no telemetry** — nothing leaves your machine
during analysis, and we do not count how often anyone runs anything. See
[docs/ADOPTION_DATA.md](../../blob/main/docs/ADOPTION_DATA.md).

That choice has a cost: we cannot see who uses this. So the evidence that it
works has to be **told to us**, by you, here. Every number this project can
honestly claim about adoption starts life as an issue like this one.

You do not have to fill in everything. What you actually ran is worth more
than a complete form.

## What you run

- [ ] The GitHub Action (`.github/workflows/…` with `uses: zsxh1990/pr-genius@…`)
- [ ] The CLI (`prgenius-core` / `python -m prgenius`)
- [ ] The MCP server (14 tools)
- [ ] The DSH plugin
- [ ] Just reading the corpus (anti-patterns / profiles / case studies)

Paste the relevant line if you like:

```yaml
# your workflow snippet
```

## What it did

<!-- The single most useful thing you can give us: one concrete moment where
     the tool changed what you did. "It said NEEDS_DISCUSSION so I opened an
     issue first and the PR landed" is worth more than any rating. -->

## Before / after (optional, and the most valuable thing here)

If you have been submitting test PRs with and without this tool, that is the
metric this project cares about.

| | without pr-genius | with pr-genius |
|---|---|---|
| PRs submitted | | |
| merged | | |
| closed without merge | | |
| still open | | |
| first feedback after | | |
| total round trips to land one | | |

Links to the actual PRs (before set and after set) are what make this
believable. We will not quote a number we cannot point at.

## What you did with the output

- [ ] Opened the PR immediately (`READY_TO_SUBMIT`)
- [ ] Fixed the checklist first (`FIX_BEFORE_SUBMIT`)
- [ ] Opened an issue instead (`NEEDS_DISCUSSION`)
- [ ] Abandoned the PR
- [ ] Ignored it

## Permission

- [ ] You may cite this report (anonymised) in the README / case studies
- [ ] You may link to my GitHub handle alongside it
- [ ] Keep it in this issue only, do not quote me

## Anything it got wrong

<!-- Equally useful. A wrong verdict we can reproduce is worth more than
     five vague compliments. -->
