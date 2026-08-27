Clone and set up the OneTyler Foundry knowledge-base repo so I can review agent transcripts.

    git clone https://github.com/tyler-technologies/onetyler-foundry-team-agent-kb.git
    cd onetyler-foundry-team-agent-kb

Then, in this order:

1. Read `CLAUDE.md` in full, first, before doing anything else. It is your operating manual
   for this repo and it overrides your own defaults. Then read `transcripts/ONBOARDING.md`
   (my walkthrough as a reviewer) and `transcripts/README.md` (the process and every review
   field). Don't skim these — the whole workflow depends on details in them.

2. **Know what I may and may not change.** Read `.github/admin-only-paths.txt` — that file
   is the boundary, so use it rather than your memory of this list.

   I **can** change: knowledge content in any `Knowledge-<Domain>/` folder — the `Conf-`,
   `Docusaurus-`, `FAQ-`, `Misc-`, `Training-` and `GitHub-` files — plus my review verdicts
   under `transcripts/`. That's my job here; I know the subject matter.

   I **cannot** change: anything that decides which agent answers, or how the repo operates.
   `README.md`, `team-config/`, **every `Knowledge-*/_START_HERE.md`**, `CLAUDE.md`,
   `transcripts/README.md`, `transcripts/ONBOARDING.md`, `scripts/`, `templates/`,
   `.github/`, `.gitignore`, `contributors.json`.

   `_START_HERE.md` is the one that catches people out: it sits in a folder I can otherwise
   edit, but it carries cross-agent hand-off rules, so it's admin-only. Don't touch it.

   If you spot a genuine problem in any of those — a wrong command, a stale number, a
   contradiction — **tell me and leave it alone.** Don't fix it, and don't edit the CI check
   that enforces this. An admin decides. This matters more for you than for me: if you
   rewrite your own instructions mid-session you'll then follow the rewrite, and nobody
   reviewing my pull request can tell which rules you were actually working under.

   One thing no check can catch, so watch for it yourself: don't put routing advice *inside*
   a knowledge file. "For identity questions, use the Identity agent" in an FAQ is
   team-level routing in a file I'm allowed to edit. Flag it to me instead.

3. Sync the reviewer list, so I can pick my own name as a reviewer:

       python3 scripts/sync_contributors.py --check   # exits 1 if it has drifted
       python3 scripts/sync_contributors.py           # rebuild if it has

   This reads GitHub team membership using my own `gh` credentials. If it fails for lack of
   scope, tell me to run `gh auth refresh -s read:org`. If my GitHub username isn't in
   `contributors.json` afterwards, stop and tell me — I'm not on the team yet and I can't
   record a review until I am. Don't hand-edit the file to work around it; it's generated,
   the next sync overwrites it, and it grants no access anyway.

4. Check whether I have a Foundry API key, since fetching transcripts needs one.
   **Ask me whether I'm on macOS or Windows first** — the setup differs.

       # macOS / Linux / Git Bash
       test -n "$FOUNDRY_API_KEY" && echo "key set" || echo "NOT SET"
       # PowerShell
       if ($env:FOUNDRY_API_KEY) { "key set" } else { "NOT SET" }

   If I don't have one, tell me to create one in Foundry under **Dev → API Keys**, then give me
   the storage steps **for my platform** — the key goes in the OS credential store, not a file:

   **macOS** (Keychain):

       security add-generic-password -a "$USER" -s foundry-api-key -U -w
       # then in ~/.zshrc:
       export FOUNDRY_API_KEY=$(security find-generic-password -a "$USER" -s foundry-api-key -w)

   **Windows** (DPAPI — encrypted to my user on this machine, so a synced copy is useless):

       New-Item -ItemType Directory -Force "$env:LOCALAPPDATA\Foundry" | Out-Null
       Read-Host -AsSecureString "Foundry API key" | ConvertFrom-SecureString |
         Set-Content "$env:LOCALAPPDATA\Foundry\key.dpapi"
       # then in $PROFILE:
       $sec = Get-Content "$env:LOCALAPPDATA\Foundry\key.dpapi" | ConvertTo-SecureString
       $env:FOUNDRY_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
         [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))

   Either way I need a **fresh terminal** after editing my profile. If I insist on a file
   instead, tell me all three rules: outside the repo, **outside any cloud-synced folder**, and
   locked-down permissions. Watch for the trap — on macOS a checkout under
   `~/Library/CloudStorage/OneDrive-.../` makes "one level up" *inside* OneDrive; on Windows,
   `Documents` and `Desktop` are often redirected into OneDrive by policy. `~/.config/foundry/`
   and `%LOCALAPPDATA%\Foundry\` are safe.

   **Don't ask me to paste the key to you**, and don't write it into any file in the repo.
   Keys are per-user and tenant-scoped, and I can hold 10. `CLAUDE.md` has the rest.

   Without a key you can still work from the transcripts already in the repo — say so and
   carry on rather than stopping.

5. Start the transcript review UI in the background and confirm it responds:

       python3 scripts/review_server.py

   It serves http://127.0.0.1:7777 on loopback only. If that port is busy use `--port 7778`
   and tell me the port you actually used.

6. Show me the state of the queue — `python3 scripts/review_status.py` — and explain in your
   own words what I'm looking at: how many transcripts are waiting, and what the lifecycle
   states mean.

7. **Finish your reply with the review UI's URL, visually separated so I can't miss it**,
   with the pending count and anything waiting specifically on me. Something like:

       ────────────────────────────────────────────
         Transcript review UI:  http://127.0.0.1:7777
         4 pending · 1 suggestion awaiting you
       ────────────────────────────────────────────

8. Finally, read `contributor-prompting-guide.md` yourself and give me a **short** summary —
   five or six of the phrases I am most likely to need, in your own words. **Do not paste the
   page back at me**, and tell me plainly that it is a page to read rather than anything I paste
   into a terminal. I want to know what to say to you, not to be handed a document.

   In particular tell me the phrase that puts my work live, because nothing reaches my
   colleagues until I say it.

Then stop and wait. Don't start reviewing transcripts for me — reviewing is a human
judgement and your verdict isn't mine. Once I've reviewed some, I'll ask you to process them.

If any step fails, say which one and what the error was rather than working around it.
