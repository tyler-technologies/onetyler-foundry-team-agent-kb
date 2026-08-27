The OneTyler Foundry knowledge-base repo has been updated. Bring my checkout up to date and
re-read the instructions before doing anything else.

**Protect my work first.** I may have uncommitted review edits. Before pulling:

    git status --short

If anything is modified, **commit it on a branch or stash it — do not discard it.** Never run
`git reset --hard`, `git checkout -- .`, or `git clean` to get a clean tree. Uncommitted
transcript edits are review work that exists nowhere else and cannot be recovered from git.
If you are unsure whether something is mine, stop and ask me.

Then:

1. Pull the latest `main`:

       ./scripts/start_review_session.sh        # Git Bash on Windows, not PowerShell

   It syncs `main`, fetches new transcripts, checks the reviewer list, and tells me what is
   waiting. It refuses to run on a dirty tree — that is deliberate, so deal with step zero
   rather than forcing past it. If you cannot run it, `git switch main && git pull --ff-only`
   and say what failed.

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

5. Restart the review UI so it runs the new code:

       # stop any existing server on 7777 first — a running one has the OLD code in memory
       python3 scripts/review_server.py

   Confirm it responds before telling me it is up.

6. Show me the queue — `python3 scripts/review_status.py` — and call out anything carrying
   written feedback that has not been classified yet.

7. **End your reply with the review UI's URL, visually separated**, with the pending count and
   anything waiting specifically on me.

Then stop. Don't review transcripts for me, don't edit knowledge files unprompted, and don't
"tidy up" any instruction file — if you think one is wrong, tell me and leave it alone.
