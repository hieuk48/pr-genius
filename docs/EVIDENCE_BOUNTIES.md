---
type: Documentation
description: How pr-genius collects evidence that it works — the solicitation flywheel, and the three bounties that drive it
---

# Evidence bounties — how this project learns that it works

## The mechanism, stated plainly

pr-genius ships **no telemetry**. That is a deliberate trade: the product sells
itself on analysis that never leaves your machine, and a usage-ping channel
would contradict it. See [ADOPTION_DATA.md](ADOPTION_DATA.md).

The cost of that trade is that **the project cannot see its own adoption**. And
we measured what passive channels are worth:

| Channel | What it finds |
|---|---|
| `gh search code "uses: zsxh1990/pr-genius"` | **0** — actual Action users are not indexed / not public |
| `gh search code "zsxh1990/pr-genius filename:yml"` | 4, all plugin catalogs and our own repos |
| broad search | 13, all awesome-lists and doc mirrors |

So "who runs this?" cannot be answered by looking. **It has to be asked.**

That is not a workaround — it is the only design consistent with the privacy
promise. The flywheel is:

```
publish a bounty  →  someone answers with evidence  →  it becomes a profile /
                                                       case study / anti-pattern  →
                                                       the corpus gets sharper  →
                                                       the next PR lands easier  →
                                                       that outcome is the next bounty's answer
```

Every claim this project makes about adoption must be traceable back to one of
these issues. If there is no issue, there is no number.

---

## Three bounties

Copy each block below into a new issue. They are written to be answered by
someone in five minutes or by someone in an afternoon — the short answer is
still worth having.

---

### Bounty 1 — Register your repo (the "who uses this" list)

> **Title:** `[Bounty] Register the repo where you run pr-genius (5 seats)`
>
> ## What
>
> We cannot see who runs this Action. Public code search does not index
> `uses:` lines for private repos, and we do not ship telemetry. So the only
> list of real adopters that can exist is one people add themselves to.
>
> **If you run pr-genius — Action, CLI, MCP, or DSH plugin — say so here.**
>
> ## Evidence (all four please, they are small)
>
> 1. The repo you run it in (org/name is enough; say if it is private)
> 2. The line that wires it up (workflow `uses:` snippet, or the install command)
> 3. Which surface: Action / CLI / MCP / DSH
> 4. One sentence: the last thing it told you that you acted on
>
> ## What happens to it
>
> - Your repo becomes a **profile** in this corpus (`profiles/<org-repo>/`) —
>   what it accepts, its merge rate, its review cadence. That is the asset the
>   tool is actually built on.
> - Your one sentence becomes a line in the README's adopters section.
> - Nothing else is collected. There is no follow-up, no analytics, no ping.
>
> ## Seats
>
> 5. First come first served; further reports still welcome but only the first
> five get a profile researched.

---

### Bounty 2 — Before/after test PRs (the metric this project actually cares about)

> **Title:** `[Bounty] Submit test PRs with and without pr-genius — give us the real numbers (3 seats)`
>
> ## What
>
> The claim this project wants to be able to make is narrow and checkable:
>
> > **AI-submitted PRs land more often, with fewer round trips, when the agent
> > runs pr-genius before submitting.**
>
> Right now nobody can check that, because nobody has run the experiment and
> published it. We want three people to run it.
>
> ## Design
>
> 1. **Baseline set.** Submit *N* test PRs to real upstreams **without**
>    consulting pr-genius. Record for each: link, outcome (merged / closed /
>    still open), how many round trips before the first maintainer response,
>    and why it died if it died.
> 2. **Treatment set.** Submit *N* more of comparable difficulty **with** the
>    agent running `coach` / `contributor` first and following the checklist.
>    Record the same fields.
> 3. **Report both sets here**, with links.
>
> `N` can be small. Three before and three after is a real result. What is not
> acceptable is a single set with no comparison.
>
> ## Evidence we will quote
>
> - PR links for both sets (the numbers are worthless without them)
> - The verdicts the tool gave before each treatment PR
> - What you changed because of the verdict
>
> ## What we will not do
>
> - We will not quote a number we cannot point at a PR for.
> - We will not round up. A result of "no difference" gets published as no
>   difference — that is a more useful finding than a flattering one.
>
> ## Seats
>
> 3.
>
> ## Optional, and worth doing
>
> Run the baseline set against repos that already have a
> [profile](../../profiles), so the comparison is against a known policy
> rather than an unknown one.

---

### Bounty 3 — The PR this tool saved (the low-bar, high-volume one)

> **Title:** `[Bounty] Name one PR that would have died without pr-genius`
>
> ## What
>
> One PR. Not a study. Just: here is a PR, here is what the tool said, here is
> what I did instead, here is what happened.
>
> The reason this is worth a bounty is that the corpus is built from exactly
> this shape of record — a case study is *what the maintainer did and why*. But
> we have 302 case studies of **other people's** PRs and none of ours.
>
> ## Evidence
>
> 1. PR link
> 2. The verdict the tool gave (paste it)
> 3. What that made you change — or not submit
> 4. The outcome
>
> ## What happens to it
>
> It becomes a case study. If the tool was **wrong**, say so — a wrong verdict
> we can reproduce is worth more than five compliments, and it gets filed as an
> anti-pattern against ourselves.
>
> ## Seats
>
> Unlimited. This one scales.

---

## Where returned evidence lands

| What they report | Where it goes in this repo | Why it matters |
|---|---|---|
| "I run this in repo X" | `profiles/<org-repo>/index.md` | The moat is repo behaviour; every new profile is a new project the tool can advise on accurately |
| Before/after PR sets | `review-cases/` + a case study with `evidence_urls` | This is the only evidence that the product does what it says |
| "It told me X and I did Y" | `review-cases/`, and the lesson if it generalises | Feeds the anti-pattern corpus **from real use** instead of from scraped titles |
| "It was wrong about Z" | `anti-patterns/` against ourselves | Honesty instrument; this is how the corpus stops being generic |

Nothing lands without a link back to the issue it came from. That is the whole
point: the repo's own claims must be traceable to testimony, the same way its
case studies are traceable to PRs.

---

## Why this is not telemetry

Solicitation is the opposite of telemetry in the way that matters:

- **Nothing is collected from anyone who does not choose to send it.**
- **Everything that arrives is public and attributable**, in an issue the
  reporter can edit or delete.
- **The product never phones home.** No code path in `analyze` / `coach` /
  `triage` / `status` opens a connection to anything but GitHub's API, with
  your own token, for PR metadata.

If any of that ever stops being true, this page is wrong and
[SECURITY.md](../SECURITY.md) is where the change gets announced first.
