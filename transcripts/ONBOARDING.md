# Onboarding — your first transcript review session

A linear walkthrough for a new reviewer. `README.md` in this folder is the reference; this is
the "do this, in this order" version. Budget about 45 minutes for a first session.

---

## What you're actually doing, and why it matters

Five Foundry agents answer Tyler staff questions about Ops Center, Support Access Center,
Identity, Aligned Releases, and the rest of Blueprint. Everything they know comes from the
markdown files in this repo — the `Knowledge-*/` folders **are** the agents' knowledge.

Reviewing a transcript means reading a real conversation and deciding: was that a good
answer, and if not, *what kind* of not-good was it? That last part is the whole job. A bad
answer can come from missing content, wrong content, the wrong agent picking it up, or the
agent reasoning badly over perfectly good content — and those need four completely different
fixes. Your verdict is what tells Claude which one to make.

**Most transcripts need no change.** That's expected and fine. The form is pre-filled for
exactly that case, so a clean one is a single click.

---

## Setup, once

**You need:** Python 3.9+, `git`, and the `gh` CLI. That's it — no `pip install`, no build
step, and **no Foundry API key** (the transcripts are already in the repo; a key is only
needed to pull new ones).

```bash
git clone https://github.com/tyler-technologies/onetyler-foundry-team-agent-kb.git
cd onetyler-foundry-team-agent-kb
```

Then make sure your `gh` token can read org team membership — the session script uses it to
check the reviewer list is current:

```bash
gh auth status                    # are you logged in?
gh auth refresh -s read:org       # only if the check below complains
```

There is deliberately **no shared token** for this. Each member uses their own, on their own
machine, so nobody has to manage another secret.

**You should already be** on the `onetyler-tcp-pm-contributors` GitHub team (that's your
write access to the repo) and listed in [`contributors.json`](../contributors.json) (that's
what lets your name be recorded as a reviewer). If the reviewer dropdown doesn't offer your
name later, that second part is missing — ask, or run
`python3 scripts/sync_contributors.py` and commit the result.

---

## Every session starts the same way

```bash
./scripts/start_review_session.sh
```

This does four things: syncs `main`, creates your review branch, fetches any new transcripts
from Foundry, and tells you what's pending.

**Use it rather than a manual `git pull`.** Two reviewers who each start from a stale `main`
can both review the same transcript — the diffs apply cleanly, git reports no conflict, and
whoever merges second silently overwrites the other. CI catches that and blocks the merge,
but you'll have wasted the review. Starting fresh avoids it.

It refuses to run on a dirty working tree. If it stops, commit or stash first.

---

## Reviewing

```bash
python3 scripts/review_server.py
```

Opens http://127.0.0.1:7777 — a local page, loopback only, nothing leaves your machine.

The list defaults to **open** — pending plus anything suggested to you — newest first. Click
one.

### What to look at, in order

**1. The question.** Would you have understood what the user wanted?

**2. The "Tools called" line.** This is the most informative thing on the page and it's easy
to skip. It tells you what the agent actually *did*:

| What it says | What happened |
|---|---|
| `searchTenantKnowledge` | It searched its knowledge base |
| **`none — answered without searching`** (highlighted) | It answered from the model's own priors — it never looked |

**3. The answer.** Judge it against what you'd have told the person.

**4. For team transcripts, the Delegation table** — which sub-agent(s) the router handed to.
If a CAPM question went to Identity, that's a routing problem, not a content problem.

### Filling in the verdict

If the answer was good: **change nothing and click "Mark reviewed & next."** The form is
already set to routing `correct`, answer `good`, diagnosis `n-a`, nothing to fix. Pick your
name once and it's remembered for the rest of the session.

**Every field has an ⓘ icon.** Click it for what the field is for and what each value
commits you to — `diagnosis` in particular, where the wrong value sends the fix to the wrong
place. Use it rather than guessing; Esc or a click outside closes it.

If it wasn't, the field that matters most is **`diagnosis`**, and you read it off the
tools-called line:

| `diagnosis` | You saw | Whose problem |
|---|---|---|
| `no-search` | Tools called: none | The agent's **prompt** — it should have searched |
| `search-empty` | It searched, found nothing | **Missing content** — a knowledge file gap |
| `search-irrelevant` | It searched, got the wrong material | **Wrong content**, or badly structured |
| `retrieved-ok-answered-badly` | Right content, bad answer | The agent's **prompt** |
| `routing-only` | Good answer, wrong agent | **Team routing rules** |

Then `fix_target` says where the fix goes: `knowledge-file`, `agent-instructions`,
`team-routing`, `sample-prompts`, or `none`.

**The single most valuable thing you can write** is the ideal response under a bad answer — what
it *should* have said, in your own words. That's what Claude turns into content. A vague
"this is wrong" produces a vague fix.

**And that alone is enough.** You don't have to set `diagnosis` or `fix_target` or any of the
other dropdowns — write the ideal response, hit *Mark reviewed & next*, and Claude classifies it
from what you wrote. Set the fields if you have a clear view; skip them if you don't. Either
way the feedback gets acted on.

### When the call isn't yours to make — "Suggest & next"

You'll hit transcripts where you can see something's off but you're not the person who should
decide: a corpus you don't own, a product area someone else runs. Don't skip it and don't
guess.

Fill everything in exactly as you would for a real review, set **`awaiting`** to whoever owns
that area, and click **Suggest & next** instead of Mark reviewed. That records it as a
suggestion under your name — `suggested_by: you`, `reviewer` deliberately left blank, because
nobody has made the call yet. Commit and PR it the normal way from the **Git & PR** tab.

The owner sees it on their next pull, with a banner saying it's your suggestion and not a
verdict. They accept it by marking it reviewed under their own name, or override it. Either
way your reasoning stays in git history. Claude will not act on a suggestion — only a human
moving it to `reviewed` releases it.

To see suggestions waiting on you: `python3 scripts/review_status.py --suggestions --for
<your-username>`.

### Two things people get wrong at first

- **`kb_files` must be a file that's actually deployed.** `Knowledge-Shared/_START_HERE.md`
  looks like a knowledge file but is repo-only documentation, in no collection — a fix there
  reaches no agent. If you're unsure, name the corpus and say so in `notes`; Claude will place
  it and tell you where it went.
- **Save without marking is a real state.** Use it for anything *you* want to come back to.
  It stays `pending` and nobody will act on it, which is the point. That's different from
  **Suggest** below — a save is a note to yourself, a suggestion is a handoff to someone else.

---

## Your first three: the Identity transcripts

Three are assigned to you, all Identity, all `pending`. Other pending transcripts may show
up in the list — new ones arrive whenever someone uses an agent — but **start with these
three**; the rest will be assigned separately.

| Transcript | Exchanges | Opens with |
|---|---|---|
| `identity/2026-08-20--02ffc8a0` | 1 | "We are evaluating how **Workforce Direct**, **Tyler…**" |
| `identity/2026-08-20--5b287c87` | 2 | "We are evaluating how **Workforce Direct**, **Tyler…**" |
| `identity/2026-08-21--6d1eb508` | **7** | "We are trying to understand the capabilities of **TI…**" |

Do the two short ones first to get the rhythm, then the 7-exchange one.

To see just yours: filter the list by **Handled by = identity** and sort is already newest
first. Yours are the three dated 2026-08-20 and 2026-08-21.

Worth knowing before you start: the first two open with the same sentence, and the third is a
long capability question — it reads like one person's evaluation session split across
conversations. That context helps when judging whether an answer was adequate *for what they
were actually trying to work out*.

Reference material for judging Identity answers is in
[`../Knowledge-TylerIdentity/_START_HERE.md`](../Knowledge-TylerIdentity/_START_HERE.md) — in
particular the Workforce-vs-Community distinction, which is the source of most wrong answers
in this domain.

---

## Finishing up

```bash
git add -A && git commit -m "Review: identity transcripts"
git push -u origin <your-branch>
gh pr create --fill
```

Your PR needs an approval from a code owner (currently Vijay) and a passing `validate` check.
That check enforces two things: frontmatter is well-formed, and nobody else already reviewed
the same transcript.

**If `validate` fails with a collision:** someone else's review of that transcript reached
`main` while yours was open. Don't force it. Pull `main`, read what they concluded, and if you
still disagree, hit **Re-review** — that raises `review_round` so both verdicts are on the
record. Re-reviewing is encouraged; it just has to be deliberate.

Then tell Claude to process the reviewed ones. It reads your verdicts, makes the changes,
opens a PR, uploads to Foundry, and closes the transcripts out as `pushed`. You don't do any
of that part.

---

## The lifecycle, so the dashboard makes sense

```
pending  ──►  suggested  ──►  reviewed  ──►  pushed
   │              │              │              │
   │              │              │              └── re-review returns it to reviewed
   │              │              │                  at a higher round
   │              │              └── a verdict is in; this is Claude's queue
   │              └── your worked-up opinion, waiting on the area owner.
   │                  Optional — skip it for areas you own.
   └── nobody has looked at it (including saved-but-unmarked)

excluded ─── not real feedback at all: pre-go-live internal testing
```

34 of the 41 transcripts are `excluded` — everything before the chatbot went live on
**2026-08-19 19:42 UTC** was the team testing its own agents. You'll only ever see the 7 real
ones.

---

## Cheat sheet

```bash
./scripts/start_review_session.sh          # sync + branch + fetch + what's pending
python3 scripts/review_server.py           # the UI on :7777
python3 scripts/review_status.py           # lifecycle dashboard
python3 scripts/review_status.py --pending  # what's left
python3 scripts/review_status.py --check    # validate frontmatter (what CI runs)
python3 scripts/review_status.py --suggestions --for me   # handoffs waiting on me
python3 scripts/validate_reviews.py         # check for review collisions
python3 scripts/sync_contributors.py        # refresh the reviewer list from GitHub teams
```

Fuller detail: [`README.md`](README.md) for the process and every field;
[`../CLAUDE.md`](../CLAUDE.md) for how Claude works the repo.

Anything ambiguous, ask rather than guessing — a wrong verdict produces a wrong fix, and
that's worse than an unreviewed transcript.
