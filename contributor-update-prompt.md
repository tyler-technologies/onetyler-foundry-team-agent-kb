The OneTyler Foundry knowledge-base repo has been updated. Bring my checkout up to date and
re-read the instructions before doing anything else.

**Protect my work first.** I may have uncommitted review edits. Before pulling:

    git status --short

If anything is modified, **commit it on a branch or stash it — do not discard it.** Never run
`git reset --hard`, `git checkout -- .`, or `git clean` to get a clean tree. Uncommitted
transcript edits are review work that exists nowhere else and cannot be recovered from git.
If you are unsure whether something is mine, stop and ask me.

Then:

1. Pull the latest `main` and start everything, with the launcher:

       python3 scripts/start.py        # macOS / Linux
       python  scripts\start.py        # Windows — works in PowerShell and cmd

   It updates the repo, refreshes the reviewer list, fetches new transcripts, starts the
   review UI and opens the browser. Every step fails independently, so one broken step does
   not stop the rest — read what it says rather than assuming it all worked.

   I can also just double-click `Start-reviewing.command` (macOS) or `Start-reviewing.bat`
   (Windows) and skip you entirely; `DAILY-WORKFLOW.md` is the page written for me. If the
   launcher will not run, `git switch main && git pull --ff-only` and say what failed.

2. **Re-read these in full. Do not skim, and do not rely on what you remember — several of
   these rules changed.** Check what actually moved first, so you know where to look:

       git log --since="7 days ago" --name-only --format="%h %ad %s" --date=short -- \
         CLAUDE.md README.md transcripts/README.md transcripts/ONBOARDING.md \
         scripts/ .github/ 'Knowledge-*/_START_HERE.md'

   Do this at the start of **every** session from now on, not just today — the instructions
   here change often enough that reading them once is not enough. Anything the log lists,
   re-read in full rather than just the diff.

   The files:
   - `CLAUDE.md` — your operating manual. Note especially the hard rules about what may be
     edited, and about Foundry uploads.
   - `.github/admin-only-paths.txt` — the authoritative list of what only admins may change.
   - `transcripts/README.md` — the review process and every field.
   - `transcripts/ONBOARDING.md` — my walkthrough as a reviewer.

3. Tell me, in your own words, what changed since I started — specifically:
   - which files I may and may not edit now
   - whether I have to fill in the header fields when I review a transcript
   - what has to happen before anything reaches Foundry

   If your answer to any of those is just a restatement of my question, re-read the file. I
   want to know you have actually absorbed it, because I am going to rely on it.

4. Check how my Foundry API key is stored, if I have one. It must be in the OS credential
   store (macOS Keychain / Windows DPAPI) or at minimum in a file that is **outside the repo,
   outside any cloud-synced folder, and permission-locked**. If it is sitting in OneDrive —
   including anywhere under `~/Library/CloudStorage/OneDrive-.../` on macOS, or `Documents`/
   `Desktop` on Windows, which are often redirected into OneDrive — tell me, because that key
   is leaving my machine and needs rotating, not just moving. `CLAUDE.md` has the setup for
   both platforms. Don't ask me to paste the key to you.

5. If a review UI was already running before step 1, **restart it** — a running server
   holds the OLD code in memory, so it will not show any of the changes you just pulled.
   `scripts/start.py` handles this; if you start the server directly instead, stop the old
   one on port 7777 first. Confirm it responds before telling me it is up.

6. Show me the queue — `python3 scripts/review_status.py` — and call out anything carrying
   written feedback that has not been classified yet.

7. **End your reply with the review UI's URL, visually separated**, with the pending count and
   anything waiting specifically on me.

Then stop. Don't review transcripts for me, don't edit knowledge files unprompted, and don't
"tidy up" any instruction file — if you think one is wrong, tell me and leave it alone.
