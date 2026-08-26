# Contributor first-run prompt

The very first thing a new contributor gives their AI agent. It clones the repo, gets the
agent oriented, starts the review UI, and sets the boundary on what the agent may change.

**How to use it:** open a terminal in the folder where you keep repos, start your AI coding
agent, and paste everything in the box below as your first message. Nothing to install
first — the repo is public and every script is stdlib-only Python.

You only need this once per machine. After that, start each session with
`./scripts/start_review_session.sh`.

---

## The prompt — copy everything between the lines

---8<--- COPY FROM HERE ---8<---

Clone and set up the OneTyler Foundry knowledge-base repo so I can review agent transcripts.

    git clone https://github.com/tyler-technologies/onetyler-foundry-team-agent-kb.git
    cd onetyler-foundry-team-agent-kb

Then, in this order:

1. Read `CLAUDE.md` in full, first, before doing anything else. It is your operating manual
   for this repo and it overrides your own defaults. Then read `transcripts/ONBOARDING.md`
   (my walkthrough as a reviewer) and `transcripts/README.md` (the process and every review
   field). Don't skim these — the whole workflow depends on details in them.

2. **Do not modify the instructions.** These files are admin-only:

   `CLAUDE.md`, `README.md`, `contributor-initial-prompt.md`, `transcripts/README.md`,
   `transcripts/ONBOARDING.md`, `scripts/`, `templates/`, `.github/`, `.gitignore`,
   `contributors.json`, and any `Knowledge-*/_START_HERE.md`.

   I am a contributor, not an admin. The only path you write to is `transcripts/` — my review
   verdicts. If you spot a genuine problem in any instruction file — a wrong command, a stale
   number, a contradiction — **tell me about it and leave it alone.** Don't fix it, and don't
   edit the CI check that enforces this. An admin decides. This matters more for you than for
   me: if you rewrite your own instructions mid-session you'll then follow the rewrite, and
   nobody reviewing my pull request can tell which rules you were actually working under.

3. Sync the reviewer list, so I can pick my own name as a reviewer:

       python3 scripts/sync_contributors.py --check   # exits 1 if it has drifted
       python3 scripts/sync_contributors.py           # rebuild if it has

   This reads GitHub team membership using my own `gh` credentials. If it fails for lack of
   scope, tell me to run `gh auth refresh -s read:org`. If my GitHub username isn't in
   `contributors.json` afterwards, stop and tell me — I'm not on the team yet and I can't
   record a review until I am. Don't hand-edit the file to work around it; it's generated,
   the next sync overwrites it, and it grants no access anyway.

4. Start the transcript review UI in the background and confirm it responds:

       python3 scripts/review_server.py

   It serves http://127.0.0.1:7777 on loopback only. If that port is busy use `--port 7778`
   and tell me the port you actually used.

5. Show me the state of the queue — `python3 scripts/review_status.py` — and explain in your
   own words what I'm looking at: how many transcripts are waiting, and what the lifecycle
   states mean.

6. **Finish your reply with the review UI's URL, visually separated so I can't miss it**,
   with the pending count and anything waiting specifically on me. Something like:

       ────────────────────────────────────────────
         Transcript review UI:  http://127.0.0.1:7777
         4 pending · 1 suggestion awaiting you
       ────────────────────────────────────────────

Then stop and wait. Don't start reviewing transcripts for me — reviewing is a human
judgement and your verdict isn't mine. Once I've reviewed some, I'll ask you to process them.

If any step fails, say which one and what the error was rather than working around it.

---8<--- COPY TO HERE ---8<---

---

## What should happen

A correct first run ends with:

- The repo cloned, on `main`, working tree clean.
- The agent having read `CLAUDE.md`, `transcripts/ONBOARDING.md`, `transcripts/README.md`.
- `contributors.json` containing your GitHub username — **check this**, it's the one thing
  that silently blocks everything else.
- The review UI answering on http://127.0.0.1:7777.
- A queue summary and the URL in a box at the end of the reply.

Nothing committed, nothing pushed, no transcript reviewed. That's all yours.

## If something goes wrong

| Symptom | What it means |
|---|---|
| Your username is missing from `contributors.json` after the sync | You're not on `onetyler-tcp-pm-contributors` yet. Ask an admin to add you; the sync can only reflect the team, not change it. |
| `sync_contributors.py` errors about scope or permissions | `gh auth refresh -s read:org`, then re-run. |
| Port 7777 already in use | Something else is on it — `--port 7778` is fine. |
| The agent starts editing `CLAUDE.md` or anything under `scripts/` | Stop it and re-paste step 2. If it already did, `git checkout -- <file>`. CI would have caught it, but a wandering agent is worth catching earlier. |
| The agent starts filling in review verdicts itself | Stop it. Verdicts are yours; an agent-authored verdict is exactly the input that produces a confidently wrong knowledge-file change. |

## Then what

Your reviewing loop, from `transcripts/ONBOARDING.md`:

1. `./scripts/start_review_session.sh` at the start of each session — pulls `main` first,
   which is what stops two reviewers silently overwriting each other.
2. Review in the UI. A clean transcript is one click; the ⓘ icon next to every field explains
   what it means and what each value commits you to.
3. Commit and open a PR from the UI's **Git & PR** tab.
4. Ask the agent to process the reviewed ones.

Reviewing an area you don't own? Use **Suggest & next** instead of Mark reviewed, with
`awaiting` set to whoever does own it. It records your work under your name and leaves the
decision to them.
