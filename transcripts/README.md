# Transcript review

Preserved conversation history for the OneTyler Cloud Living team agent, and the workflow
for turning it into knowledge-file improvements.

There are two ways to review: a **local web UI** (recommended) or editing the markdown
files by hand. Both write to the same files, so you can mix freely.

---

## The process, end to end

Eight steps. The order matters — (a) before (b) is what stops two reviewers colliding, and
(f) fully completing before (g) is what stops Foundry and the repo disagreeing.

| # | Step | Who | How |
|---|---|---|---|
| a | Pull the latest `main` | you | `./scripts/start_review_session.sh` |
| b | Pull unreviewed from the repo + fresh transcripts from Foundry | you | same script — it fetches, then lists what's pending |
| c | Review | you / the team | `python3 scripts/review_server.py` → http://127.0.0.1:7777 |
| d | Tell Claude to process the reviewed ones | you | just say so |
| e | Process, and update knowledge files if needed | Claude | `review_status.py --actions`, then the edits |
| f | Push the changes to the repo as a PR, and **merge it** | Claude opens it, you merge | branch → commit → PR → your approval → **merge** |
| g | Push to Foundry, verify, then close the transcripts out | Claude | `preflight_upload.py` → upload → verify by retrieval → `mark_pushed.py` |
| h | Confirm Foundry and the repo agree | Claude | `check_foundry_drift.py` after every merge |

### Why (a) comes first

Two reviewers who each start from a stale `main` can both first-review the same transcript.
Both diffs apply cleanly, git reports no conflict, and whoever merges second silently
overwrites the other. `scripts/validate_reviews.py` catches it in CI, but syncing first
avoids the wasted work entirely.

### Why (g) comes after (f) — and why "merged", not "opened"

**Nothing goes to Foundry until it is on `main`.** Opening a PR is not enough; it has to be
merged. This is the rule that keeps the repo the source of truth, and it was the one gap in
the process for a while — the step used to read "open a PR, then upload", which is followed
to the letter by uploading from an unmerged branch.

That went wrong once, on 2026-08-25: an upload went out at 22:32 UTC and the PR carrying it
merged at 05:02 UTC the next morning. For 6.5 hours the live agents answered from content
`main` had not accepted. Had the PR been rejected or amended in review, the sequence would
have been:

1. Foundry serves the unmerged text. Agents answer from it.
2. `main` never receives it.
3. Someone runs the drift check, sees drift, and "fixes" it by uploading main's version —
   silently reverting the live agents.

Nobody does anything wrong there and the agent's behaviour changes twice.
`scripts/preflight_upload.py` now refuses to upload a file whose bytes differ from
`origin/main`, so the sequence is impossible rather than merely discouraged.

**The cost is two PRs per cycle**, and that is the honest shape:

```
PR 1   knowledge-file changes + action_status: applied   ->  merge
       upload to Foundry, verify by retrieval
PR 2   mark_pushed.py close-outs                          ->  merge
```

`pushed` is a claim about **Foundry**, not the repo, so it cannot honestly be set in the same
PR as the content — at that point nothing is live yet. `mark_pushed.py` also refuses to close
out a transcript whose `kb_action` is unresolved, so an open action cannot be quietly buried.

### Why (h) exists

A merge is the moment `main` gets ahead of Foundry. Nothing notices on its own: a knowledge
file only reaches an agent when someone uploads it, so an unshipped change leaves the agent
answering from old text while the repo looks perfectly correct.

```bash
python3 scripts/check_foundry_drift.py          # after EVERY merge
python3 scripts/check_foundry_drift.py --deep   # byte-compare, not just file size
```

It checks all five collections, every shared file against *every* one of its
`upload_targets`, and the live team router against `team-config/team-routing-prompt.md`. The
two guards face opposite directions and you want both: `preflight_upload.py` stops Foundry
getting ahead of `main`, and this stops `main` getting ahead of Foundry.

---

## The transcript lifecycle

```
pending  ──►  suggested  ──►  reviewed  ──►  pushed
   │              │              │              │
   │              │              │              └── re-review raises review_round
   │              │              │                  and returns it to reviewed
   │              │              └── a verdict is recorded; this is Claude's inbox
   │              └── someone worked it up but is NOT the one deciding.
   │                  Waiting on the area owner named in `awaiting`.
   └── nobody has looked at it. Saving without marking leaves it here on purpose —
       use that for anything YOU want to come back to.

excluded ─── out of scope entirely (pre-go-live testing). Not part of the flow.
```

`suggested` is optional. A reviewer who owns the area goes straight from `pending` to
`reviewed`.

| State | Means | Set by |
|---|---|---|
| `pending` | Nobody has looked at it. May hold partially-filled fields — a deliberate "come back to it", **for yourself**. | default |
| `suggested` | A worked-up correction and proposed fix, explicitly **not** a verdict, handed to the area owner. Claude will not act on it. | whoever hits **Suggest** |
| `reviewed` | A human verdict is recorded. **This is the queue Claude works from.** | you |
| `pushed` | Processed, and any resulting change is live in Foundry. Terminal. | Claude, at step (g) |
| `excluded` | Not real feedback — pre-go-live testing. | you |

A no-change review still ends at `pushed`: nothing needed deploying, so it's closed out.
`action_status` records which happened — `applied` for a real change, `none-needed` when
there was nothing to do.

### `suggested` — reviewing an area you don't own

Use it when you can see what went wrong but the call isn't yours to make: an Ops Center
question you have opinions about, an Identity answer that looks thin, anything where the
person who owns that corpus should sign off.

Fill in the fields and the correction exactly as you would for a real review, then hit
**Suggest & next** instead of **Mark reviewed & next**. Commit and open a PR the usual way
(the **Git & PR** tab). It merges like any other review contribution — CI does not require a
verdict — and the owner picks it up on their next pull.

Three things make it a real handoff rather than a note in a field:

- **It carries a name.** `suggested_by` is required, and `reviewer` is deliberately left
  blank — that field means *who made the call*, and nobody has. `awaiting` names the owner
  you're handing it to. All three must be registered contributors.
- **Claude will not act on it.** `--actions` lists it as "not actionable yet" and
  `mark_pushed.py` refuses to close it. Only a human moving it to `reviewed` releases it.
- **It cannot be silently overwritten.** See *Why the checks exist* below.

To find suggestions waiting on you:

```bash
python3 scripts/review_status.py --suggestions --for <your-github-username>
```

Accepting one is just reviewing it: open it, change anything you disagree with, put **your**
name in `reviewer`, and mark it reviewed. Disagree entirely? Overwrite the fields and mark it
reviewed anyway — your verdict wins, and the suggestion stays in git history. To hand it on
to someone else instead, change `awaiting` and hit **Suggest** again.

---

---

## Setup — the review UI

Run this on your own machine. It never leaves your laptop: the server binds to loopback
only, and the only thing that gets shared is the PR you open at the end.

**Prerequisites:** Python 3.9+ and git. That's all — the server uses the Python standard
library, so there is nothing to `pip install` and no build step.

```bash
git clone https://github.com/tyler-technologies/onetyler-foundry-team-agent-kb.git
cd onetyler-foundry-team-agent-kb
git switch -c review/<your-initials>-<date>      # never review on main; it's protected

python3 scripts/review_server.py                 # opens http://127.0.0.1:7777
```

Port already in use? `python3 scripts/review_server.py --port 7778`.
Don't want the browser auto-opened? add `--no-browser`.

You do **not** need a Foundry API key to review — the transcripts are already in the repo.
A key is only needed to pull *new* transcripts (`scripts/fetch_transcripts.py`).

### Getting yourself into the reviewer list

The `reviewer` field is restricted to people in
[`contributors.json`](../contributors.json), so a review always attributes to the same GitHub
identity that authors the PR.

**That file is generated, not hand-edited.** It is rebuilt from GitHub team membership:

```bash
python3 scripts/sync_contributors.py          # rebuild from the teams
python3 scripts/sync_contributors.py --check  # exit 1 if it has drifted
```

So to get yourself listed, ask to be added to the **`onetyler-tcp-pm-contributors`** team —
that is also what gives you write access to the repo. Then re-run the sync and commit the
result. Adding an entry by hand won't survive the next sync and wouldn't grant you repo
access anyway.

Until you're listed, the reviewer dropdown won't offer your name and you can't mark anything
reviewed.

### Using it

- The landing page lists all transcripts with their status. Click one.
- Each exchange shows the question, the answer, and — importantly — **which tools the agent
  called**. `none — answered without searching` is highlighted, because it usually means the
  agent answered from model priors rather than the knowledge base.
- Fill in the dropdowns, write a correction under any bad answer, and write the
  **Proposed fix** at the bottom.
- **Mark reviewed & next** saves and moves to the next transcript, so you can work through
  a batch without going back to the list.
- **Suggest & next** does the same but records it as a suggestion for the area owner rather
  than as your verdict — use it for areas you don't own. It puts your name in `suggested_by`
  and clears `reviewer`. Set `awaiting` first if you know whose call it is.
- The list defaults to showing **open (pending + suggested)**, so suggestions handed to you
  appear without changing any filter. A suggested row shows `who → whom` under its status.
- Saving rewrites the transcript's markdown file in place and regenerates `INDEX.md`. Your
  work is a normal git diff — check `git diff` any time.
- The **Git & PR** tab creates a branch, commits everything under `transcripts/`, pushes,
  and runs `gh pr create --fill`. If you don't have the `gh` CLI, it still commits and
  pushes; open the PR in the browser.

---

## How to review one transcript (the 60-second version)

Same job, whether in the UI or a text editor:

1. Pick a `pending` transcript.
2. Read the **Q**, the **A**, and the **Tools called** line.
**You do not have to touch the dropdowns.** If the answer was wrong, writing what it
*should* have said — under the exchange, and/or in **Proposed fix** — is a complete review.
Claude reads that prose and fills in `diagnosis`, `fix_target`, `kb_action` and the rest for
you. The header fields are a convenience, not the deliverable.

Two things follow from that, both handled for you:

- Saving with written feedback but untouched dropdowns sets `action_status: open` and a
  `needs-triage` note, so the file does not claim "nothing wrong" while its body says
  otherwise.
- `review_status.py --actions` finds work by reading the **body**, not the fields.

3. **If nothing is wrong, change nothing.** The form opens pre-filled as *no changes
   needed* — routing `correct`, answer `good`, diagnosis `n-a`, fix target `none`, kb action
   `none`, action status `none-needed`. Pick your name once and it is remembered, so a clean
   transcript is a single click on **Mark reviewed & next**.
4. Otherwise correct the fields that are wrong, and set `review_status: reviewed`.
5. If the answer was wrong, write what it *should* have said, and say what should change in
   **Proposed fix**.

That's it. Claude reads these fields to decide what to change — in the knowledge files, the
agent instructions, or the routing rules.

### Reviews with no knowledge-file change are still complete work

This matters: plenty of bad answers are **not** corpus problems. If the agent never
searched, or retrieved the right material and still answered badly, the fix belongs in the
agent's instructions — not in a knowledge file. Record that and commit it:

```yaml
diagnosis: no-search
fix_target: agent-instructions
kb_action: none
kb_files:
```

...with the specific wording you'd add written in **Proposed fix**. A PR containing only
verdicts and proposed instruction changes, touching zero knowledge files, is a full
contribution — it's how the agent prompts and the team routing table get improved.

---

## The review fields

All live in the frontmatter, under `# ---- review fields: edit these ----`. Leave a field
blank if it doesn't apply.

| Field | Values | What it means |
|---|---|---|
| `review_round` | integer, default `1` | Which round of review this is. The **Re-review** button raises it. Required to re-review something already reviewed on `main` — see *Why the checks exist*. |
| `review_status` | `pending` · `suggested` · `reviewed` · `pushed` · `excluded` | Set `reviewed` when you're done. Use `suggested` to hand a worked-up opinion to the area owner without claiming the verdict (see above). Use `excluded` for a transcript that is not real feedback at all (see below) — it leaves the queue without counting as review work. |
| `reviewer` | a `github` value from [`contributors.json`](../contributors.json) | Who **made the call**. **Not free text** — the UI offers only registered contributors, and `--check` fails on anything else. Required to mark a transcript `reviewed`. Stays blank on a `suggested` transcript, because nobody has decided yet. |
| `suggested_by` | a `github` value from `contributors.json` | Who drafted a suggestion they are not claiming as a verdict. **Required** when `review_status: suggested`; `--check` fails without it. Set for you by the **Suggest** button. |
| `awaiting` | a `github` value from `contributors.json` | The area owner a suggestion is handed to. Optional — blank means "anyone can pick this up" — but naming someone is what makes `--suggestions --for <user>` useful. |
| `routing_verdict` | `correct` · `wrong-agent` · `ambiguous` | Did the *right* sub-agent handle this? |
| `reassign_to` | `ops-center` · `bp-general` · `sac` · `identity` | Which agent *should* have. Only if `wrong-agent`. |
| `answer_verdict` | `good` · `incomplete` · `wrong` · `stale` · `refused` | Quality of the answer given. |
| `diagnosis` | see below | *Why* it went wrong. The most important field. |
| `fix_target` | `none` · `knowledge-file` · `agent-instructions` · `team-routing` · `sample-prompts` | **Where the fix belongs.** Pick `agent-instructions` or `team-routing` when no knowledge file needs to change. |
| `kb_action` | `none` · `add` · `update` · `split` | What needs to happen to the corpus. `none` is a valid answer. |
| `kb_files` | paths | Which files, e.g. `Knowledge-OpsCenter/Misc-Links.md`. |
| `action_status` | `none-needed` · `open` · `applied` · `wontfix` | Claude sets `applied` once the change ships. |
| `notes` | free text | Anything else. |

### `excluded` — not everything is feedback

The Foundry chatbot went live in Ops Center on **2026-08-19** (tcp-ops-center PR #1206).
Conversations before that are us testing our own agents, so they say nothing about how real
users behave. Marking them `excluded` (rather than `reviewed`) keeps them out of the pending
queue *and* out of the reviewed percentage — otherwise the dashboard would claim review work
that never happened.

Use `excluded` for anything that isn't a genuine user signal: pre-go-live testing, your own
probing, deliberate attempts to break the agent. Always say why in `notes`, and set
`reviewer` — an exclusion is still a judgement someone made.

### `diagnosis` — pick from the **Tools called** line

This is what makes the review actionable, because it separates knowledge problems from
prompt problems. Four failures look identical in the chat and have completely different fixes:

| Value | What you saw | Fix belongs in |
|---|---|---|
| `no-search` | "Tools called: _none_" — answered from model priors | Agent prompt |
| `search-empty` | Searched, found nothing | **Knowledge file** — content missing |
| `search-irrelevant` | Searched, got the wrong material | **Knowledge file** — content or structure |
| `retrieved-ok-answered-badly` | Right content retrieved, bad answer | Agent prompt |
| `routing-only` | Answer was fine, just the wrong agent | Team routing rules |
| `n-a` | Answer was good | — |

Don't rewrite a knowledge file to fix a prompt bug. If `diagnosis` is `no-search` or
`retrieved-ok-answered-badly`, set `kb_action: none` and say so in `notes`.

### Correcting an answer

Each exchange has a review block. Fill it in freely — prose is fine:

```markdown
<!-- review:2 -->
**Review —** _verdict:_ wrong · _should have said:_
The org key and the CRM Customer Identifier are the same value. It's generated
from the customer name and stays stable across CRM merges. See
Conf-CRMCustomerIdentifiers.md.
<!-- /review:2 -->
```

A concrete "should have said" is the single most useful thing you can write — it tells
Claude exactly what the corpus is missing.

---

## Commands

```bash
python3 scripts/review_server.py             # the review UI on :7777
python3 scripts/review_server.py --port 7778 --no-browser

python3 scripts/review_status.py             # dashboard + regenerate INDEX.md
python3 scripts/review_status.py --pending    # just what's left to review
python3 scripts/review_status.py --actions    # open KB actions
python3 scripts/review_status.py --check      # validate frontmatter (exit 1 on error)
python3 scripts/review_status.py --suggestions            # handoffs awaiting a decision
python3 scripts/review_status.py --suggestions --for me   # ...just the ones aimed at me
python3 scripts/validate_reviews.py           # check for review collisions vs origin/main

python3 scripts/fetch_transcripts.py          # pull new conversations
python3 scripts/fetch_transcripts.py --dry-run
```

`fetch_transcripts.py` **never overwrites an existing file**, so re-running it is always
safe — your review edits can't be clobbered. It only adds new conversations as `pending`.

---

## Why the checks exist: nobody overwrites anybody

Two reviewers can pick up the same `pending` transcript, review it, and open a PR. **Both
diffs apply cleanly** — git sees no conflict, because each branch changed the file relative
to a base where it was still `pending`. Whoever merges second silently overwrites the first
reviewer's verdict, and neither of them ever finds out. That is the specific failure this
guards against.

Three things work together:

1. **`scripts/validate_reviews.py`** runs on every PR. For each transcript you touched it
   compares the review state on `main` with yours:

   | On `main` | In your PR | Verdict |
   |---|---|---|
   | `pending` | `reviewed`, round 1 | ✅ first review |
   | `pending` | `suggested`, round 1 | ✅ first suggestion |
   | `suggested` | `reviewed`, same round, **branched after the suggestion landed** | ✅ owner accepted it |
   | `suggested` | `reviewed`, same round, **branched before it landed** | ❌ **collision** — you never saw it |
   | `suggested` | `suggested`, same round | ❌ **collision** — two independent suggestions |
   | `reviewed` | `reviewed`, round **n+1** | ✅ deliberate re-review |
   | `reviewed` | `reviewed`, same round | ❌ **collision** |
   | `reviewed` | `suggested`, same round | ❌ re-opening a decided transcript is a re-review |
   | anything | `reviewed`, no `reviewer` | ❌ un-attributable |
   | anything | `suggested`, no `suggested_by` | ❌ un-attributable |

   The two `suggested → reviewed` rows look identical in the frontmatter — the difference is
   whether you actually saw the suggestion. The check resolves it with `git merge-base`: if
   the suggestion was already present in the commit your branch was cut from, you superseded
   it deliberately; if it reached the base branch afterwards, your PR was written without it
   and merging would discard it.

2. **"Require branches to be up to date before merging"** is on. This is the part that makes
   it airtight: a PR cannot merge against a stale `main`, so the check always re-runs against
   the *current* state. A review that landed while your PR was open gets seen, not clobbered.

3. **A code-owner approval** is required on every PR, so a human also sees it.

**If you hit a collision:** don't force it. Pull `main`, read what the other reviewer
concluded, and if you still disagree, hit **Re-review** — that raises `review_round` and both
verdicts end up on the record. Re-reviewing is encouraged; it just has to be explicit.

## Finding your own rows

The review list shows an **Awaiting** column and highlights the rows that are yours, so you do
not have to read every line to find your work.

| Highlight | Means |
|---|---|
| **Amber**, with a `you` badge | `awaiting` names you — somebody handed this to you personally |
| **Blue**, with a `your area` badge | You own the agent that answered it. Nobody has asked you specifically |
| No highlight | Not yours |

There is a **mine only** checkbox in the filter bar, and `Awaiting` is filterable like any other
column.

Ownership comes from [`agent-owners.json`](../agent-owners.json) — hand-maintained, and
deliberately *not* `contributors.json`, which is generated from GitHub teams and would overwrite
anything added by hand. It uses a default owner plus per-agent overrides, so adding an agent
needs no edit:

```json
{ "default_owner": "vijay-tylertech",
  "by_agent": { "identity": "jon-olson-tylertech" } }
```

**Ownership is a convenience, not a permission.** It changes which rows are tinted and nothing
else — anyone may still review anything, and `Suggest & next` remains the way to weigh in on an
area you do not own.

The UI works out who you are from `gh api user`; override with `--me <username>`. If it cannot
tell, or the name is not in `contributors.json`, **nothing** is highlighted and it says so on
startup — highlighting the wrong person's rows would be worse than highlighting nobody's.

## Referring to a transcript

Use the review UI URL, never the bare hash:

```
http://127.0.0.1:7777/t/<agent>/<YYYY-MM-DD>--<hash>.md
```

Quote the question that was asked alongside it. A hash like `75043484` is not something anyone
recognises — reviewers see transcripts in a browser, listed by their opening question. Claude is
instructed to do the same when it asks you about one.

## Working as a team

Several people review; one person opens the PR. Since we coordinate verbally, the
convention is deliberately light:

- **Claim a slice out loud** — by agent folder (`identity/`, `ops-center/`) or by date
  range. One reviewer per folder at a time avoids merge conflicts entirely, since each
  transcript is its own file.
- **Pick yourself in `reviewer`** so credit and questions have an owner. Add yourself to
  `contributors.json` if you aren't there yet.
- **Reviewing outside your area? Suggest, don't decide.** Fill it in and hit **Suggest**
  with `awaiting` set to whoever owns that corpus. It commits and PRs like any other review,
  and they get the final say. This is the intended way to contribute an opinion on a slice
  you haven't claimed — you don't have to stay out of it, and you don't have to pretend to
  authority you don't have.
- **The PR submitter** runs `review_status.py` before committing so `INDEX.md` reflects
  reality, and titles the PR with what was covered, e.g.
  `Review: identity transcripts 2026-06`.
- **Then ask Claude to act on it** — "apply the open KB actions" — and it will read the
  reviewed files, make the corpus edits, set `action_status: applied`, and list the files
  needing re-upload to Foundry.

Conflicts are rare by construction: one file per conversation, and the only regenerated
file is `INDEX.md`. If two people do collide there, just re-run `review_status.py` after
merging — it's derived, never hand-edited.

---

## What's in here, and what isn't

**Filtered out at fetch time:**

- **Canned starting prompts.** The team and each sub-agent show clickable sample-question
  chips. A click tells us nothing about real information needs, and they dominated the raw
  data — 34 of the original 75 conversations were *nothing but* chip clicks and were
  dropped entirely. Partially-canned conversations keep only their real exchanges, and
  note how many were omitted.
- **Exchanges missing a question or a response.**

**Redacted at fetch time**, because this repo is public:

- The `tylertownwa` test password — the Identity agent was observed reproducing it verbatim
  from its knowledge base. → `[REDACTED-CREDENTIAL]`
- Real `@tylertech.com` addresses → `[REDACTED-EMAIL]`. Bare domain mentions
  ("any user with an `@tylertech.com` email") are kept, since they carry meaning.
- Real JWTs → `[REDACTED-TOKEN]`.

Doc-example addresses on other domains (`john.doe@agency.gov`) are kept deliberately —
they're part of the answer being reviewed.

**Not collected at all:** who had the conversation. The Foundry transcripts API returns
only the conversation ID and the exchanges — no user identity — and we don't want it. If
you need to reach the person who asked, find the conversation in Foundry.
