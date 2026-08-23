# Transcript review

Preserved conversation history for the OneTyler Cloud Living team agent, and the workflow
for turning it into knowledge-file improvements.

There are two ways to review: a **local web UI** (recommended) or editing the markdown
files by hand. Both write to the same files, so you can mix freely.

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

### Using it

- The landing page lists all transcripts with their status. Click one.
- Each exchange shows the question, the answer, and — importantly — **which tools the agent
  called**. `none — answered without searching` is highlighted, because it usually means the
  agent answered from model priors rather than the knowledge base.
- Fill in the dropdowns, write a correction under any bad answer, and write the
  **Proposed fix** at the bottom.
- **Mark reviewed & next** saves and moves to the next transcript, so you can work through
  a batch without going back to the list.
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
3. Fill in the review fields.
4. Set `review_status: reviewed`.
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
| `review_status` | `pending` · `reviewed` | Set to `reviewed` when you're done. |
| `reviewer` | free text | Your name or initials. |
| `routing_verdict` | `correct` · `wrong-agent` · `ambiguous` | Did the *right* sub-agent handle this? |
| `reassign_to` | `ops-center` · `bp-general` · `sac` · `identity` | Which agent *should* have. Only if `wrong-agent`. |
| `answer_verdict` | `good` · `incomplete` · `wrong` · `stale` · `refused` | Quality of the answer given. |
| `diagnosis` | see below | *Why* it went wrong. The most important field. |
| `fix_target` | `none` · `knowledge-file` · `agent-instructions` · `team-routing` · `sample-prompts` | **Where the fix belongs.** Pick `agent-instructions` or `team-routing` when no knowledge file needs to change. |
| `kb_action` | `none` · `add` · `update` · `split` | What needs to happen to the corpus. `none` is a valid answer. |
| `kb_files` | paths | Which files, e.g. `Knowledge-OpsCenter/Misc-Links.md`. |
| `action_status` | `open` · `applied` · `wontfix` | Claude sets `applied` once the change ships. |
| `notes` | free text | Anything else. |

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

python3 scripts/fetch_transcripts.py          # pull new conversations
python3 scripts/fetch_transcripts.py --dry-run
```

`fetch_transcripts.py` **never overwrites an existing file**, so re-running it is always
safe — your review edits can't be clobbered. It only adds new conversations as `pending`.

---

## Working as a team

Several people review; one person opens the PR. Since we coordinate verbally, the
convention is deliberately light:

- **Claim a slice out loud** — by agent folder (`identity/`, `ops-center/`) or by date
  range. One reviewer per folder at a time avoids merge conflicts entirely, since each
  transcript is its own file.
- **Put your initials in `reviewer`** so credit and questions have an owner.
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
