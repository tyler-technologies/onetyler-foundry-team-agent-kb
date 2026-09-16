# The daily workflow

**Reviewing transcripts needs no assistant.** Start the tool, read conversations, write what
the answer should have said, save, send it in. All buttons.

**Updating the knowledge files does need one, and that is the actual goal.** A verdict is not
the deliverable — the knowledge file that stops the agent repeating that answer is. Deciding
which file, where in it, and how to word it so the retriever finds it is judgement and writing,
and there is no button for it.

So the split is:

| | Who |
|---|---|
| Start the tool, review, save, send in | You. No assistant. |
| **Update the knowledge files from your feedback** | **An assistant.** This is the job. |
| Approve &amp; Merge the change request — which also publishes it to Foundry | An admin, one button, in this tool. |
| Close out the transcripts | An admin, one command. |

This page covers everything except the assistant step, which is one copy-and-paste — the Save &
Publish page generates the prompt for you.

---

## Every day, as a contributor

### macOS

Double-click **`Start-reviewing.command`** in the repo folder.

> The first time, macOS may say it "cannot be opened because it is from an unidentified
> developer". Right-click the file → **Open** → **Open**. Once only.

### Windows

Double-click **`Start-reviewing.bat`** in the repo folder.

> If a window flashes and vanishes, Python is probably not installed or not on PATH. Install it
> from python.org and tick **"Add python.exe to PATH"** in the installer.

### You need Python 3.12 or newer

**macOS ships 3.9, which is too old** — the review UI will not even start on it. The launcher
checks this first and tells you what to do, so you get a sentence rather than a `SyntaxError`.

```bash
python3 -V                    # want 3.12 or higher
brew install python@3.12      # macOS, if it is older
```

On Windows the python.org installer is current, so this only bites Mac users who have never
installed a Python of their own.

### Either, from a terminal

```bash
python3 scripts/start.py        # macOS / Linux
python  scripts\start.py        # Windows
```

That's it. It brings the repo up to date, pulls new conversations, opens
**http://127.0.0.1:7777**, and stays running while you work. Close the window when you're done.

**It will never throw away your work.** If you have unsaved reviews it says so and leaves
everything alone rather than tidying up first.

---

## In the browser

| You want to | Do this |
|---|---|
| See what's waiting for you | **My Transcripts** — opens on what still needs a first look |
| See everything (admins) | **All Transcripts** |
| Get new conversations | **Sync transcripts**, top right |
| Review one | Click the row. Read it. If the answer was wrong, write what it *should* have said |
| Approve a good answer | Change nothing, click **Mark reviewed & next** |
| Flag something outside your area | **Suggest & next**, and set *awaiting* to whoever owns it |
| Approve a batch of good ones | Tick the rows, then **Mark selected reviewed** |
| Understand a field | Click the blue **ⓘ** beside it |
| Save without submitting | **Save & Publish → Save progress** |
| Submit for review | **Save & Publish → Send my reviews in** |

**You do not have to fill in the dropdowns.** Writing the ideal response in your own words is the
valuable part. The classification fields are clerical and get filled in later.

---

## After you send reviews in

**Send my reviews in** opens a change request and prints its address in the output panel —
click it. Someone reviews and merges it. That part is GitHub, not this tool, and not an
assistant either.

The stage list on that step tells you what is still owed, including whether a Foundry upload is
needed at all. Most review batches change only transcripts, and **transcript reviews never need
uploading — they are not agent knowledge.**

---

## Admins: Approve &amp; Merge is the whole make-it-live step

**Publishing to Foundry is not a separate thing you have to remember.** On the **Change
Requests** page, **Approve &amp; Merge** does all of it in one click:

1. Merges the request (rebase, admin override), bringing the branch up to date first if it is
   behind and resolving a `transcripts/INDEX.md`-only conflict by itself.
2. Fast-forwards this checkout, so the app is not stale because of its own action.
3. **Uploads every `Knowledge-*` file the request touched to its collection(s)** — including a
   `Knowledge-Shared/` file to all five — then triggers ONE ingestion job and **verifies the
   content by retrieval**, not by the status field.
4. **Writes the team routing prompt live**, if the request changed it. See below — this one has
   a condition.
5. Reports failure as failure. If either publish does not land, the action is reported as
   failed, because a merge that did not reach the agents is not done.

Underneath it runs `scripts/publish_to_foundry.py`, so the guarantees are the same ones the
command line has: it refuses any file whose bytes differ from `origin/main` (nothing unmerged
can ship), uploads everything before syncing once, and proves retrievability rather than
trusting `ingestionStatus`.

**A merge made on github.com does not publish itself.** GitHub has no idea this tool exists. The
periodic sync covers it — every 30 minutes and on tab focus, an admin's session compares the five
collections against `main` and publishes anything missing — but it is a safety net, not the
route. Merge here.

### A routing-prompt change needs a backup in the same request

`team-config/team-routing-prompt.md` is a **mirror**. The live copy is `system_prompt` on the
team object, and Approve &amp; Merge now writes it — but only with an undo in place, because a
config object has no other copy and no git history of its own (hard rule 8). So the request
that changes the prompt must also carry the pre-change object:

```bash
T=e92bd437-cb84-4e18-88e6-757370b39c90
curl -s -A "claude-code-foundry-kb/1.0" -H "X-API-Key: $FOUNDRY_API_KEY" \
  "https://foundry.tylertechai.com/api/teams/$T" \
  -o "team-config/backups/team-backup-$(date +%Y%m%d-%H%M%S).json"
```

Scan it for credentials, commit it alongside the prompt change, and the merge does the rest:

- refuses unless the mirror is byte-identical to `origin/main` (nothing unmerged ships)
- refuses a prompt containing `<` or `>` — Foundry escapes and strips those, so the text could
  not survive the write
- refuses if the live prompt no longer matches the committed backup, which means **somebody
  edited the router in the Foundry UI** after this request was prepared and the new prompt was
  written against a baseline that is gone
- takes a native version snapshot, PUTs the **full** team object with only `system_prompt`
  changed, re-reads it, and diffs field by field — if anything but the prompt moved, it fails
  loudly and prints the restore command

The card says which of these applies **before** you click. Without a backup the merge still
happens and the knowledge files still ship; routing simply stays as it was.

**Routing changes for every conversation the moment this finishes**, so have the question that
was misrouted — and a control question that must still go elsewhere — ready to try.

### What Approve &amp; Merge still does NOT do

**Close out the transcripts.** `main` is protected, so the merge cannot commit this itself:

```bash
python3 scripts/mark_pushed.py --all      # after the merge output says it is live
```

On Windows use `python` instead of `python3`.

### If the button says it cannot publish

`FOUNDRY_API_KEY` has to be present in the environment **the server was started from** — the
upload runs server-side, not in your browser. A copy started without it will still merge and
will say plainly that the upload did not run, leaving `main` ahead of the live agents. The
request's card warns about this before you click. Restart the server with the key, or merge from
a copy that has it, then:

```bash
python3 scripts/check_foundry_drift.py    # confirm repo and Foundry agree, either way
```

### Adding someone to the team

```bash
python3 scripts/sync_contributors.py --check   # has the team changed?
python3 scripts/sync_contributors.py           # rebuild the reviewer list, then send it in
```

This reads GitHub team membership; it does not *add* anyone to a team. Adding someone to
`onetyler-tcp-pm-contributors` is a deliberate access change and stays a human decision.

---

## When something goes wrong

| What you see | What it means |
|---|---|
| `Port 7777 is already in use` | The tool is probably open in another window — use that one. Or `--port 7778`. |
| `FOUNDRY_API_KEY is not set` | No new conversations can be pulled. Everything already in the repo still reviews fine. |
| `the GitHub CLI (gh) is not installed` | Only matters if someone new joined the team. Ignore otherwise. |
| `you have unsaved work, so nothing was touched` | Working as intended. Carry on, or send in what you have. |
| Your name missing from the reviewer list | You are not on the GitHub team yet. Ask an admin. |
| `could not reach GitHub` | You are offline. Reviewing still works; sending in does not. |

---

## The assistant step, in detail

On **Save & Publish**, Part 2 begins with *Update the knowledge files*. It tells you how many
reviewed transcripts are waiting on it and gives you a **Copy the prompt for my assistant**
button. Paste that to your AI, and it will read all your feedback as one body, make the changes,
and summarise them per transcript so you can follow your own feedback through.

Read the summary it gives you. That is where you find out whether it misunderstood you.

Two other things still need an assistant, both admin-only and both rare:

- **Changing the team router**, agent prompts, or anything in `team-config/`. High blast radius,
  and it has to be verified by behaviour rather than by diff.
- **New features in this tooling.**

Everything else on this page is a double-click or one command.
