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
| Merge the change request | A reviewer, on GitHub. |
| Upload to Foundry, close out the transcripts | You, one command each. |

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

**You do not have to fill in the dropdowns.** Writing the correction in your own words is the
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

## Admins: the rest of the loop

Only needed when a review led to an actual knowledge-file change, and only after the change
request has been **merged**.

```bash
python3 scripts/publish_to_foundry.py --dry-run   # what would go, and where
python3 scripts/publish_to_foundry.py             # asks before writing anything
python3 scripts/check_foundry_drift.py            # confirm repo and Foundry agree
python3 scripts/mark_pushed.py                    # close out the transcripts
```

On Windows use `python` instead of `python3`.

`publish_to_foundry.py` refuses any file that is not byte-identical to `origin/main`, so it
cannot ship something unmerged. It uploads everything before triggering a single ingestion job,
and then confirms the content is **retrievable** rather than trusting the status field — a file
can report "ingested" and hold no searchable text.

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
