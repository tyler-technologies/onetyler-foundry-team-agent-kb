# CLAUDE.md

Operating instructions for Claude Code instances working in this repository.

Read this fully before touching the Foundry API. It is self-contained — it does **not**
depend on any locally-installed skill. (If `~/.claude/skills/foundry-transcripts/` or
`manage-kb-collection/` happen to exist on your machine, they cover the same ground in more
depth, but never assume they are present.)

---

## 🚫 HARD RULES — read these first

1. **Every corpus in this repo is the source of truth for its Foundry collection.** All five
   agents' knowledge now flows from here — including Tyler Identity, which was cut over on
   2026-08-24. Edit here, then upload. Never edit a collection's content in the Foundry UI:
   that creates drift the repo cannot see, and the next upload from here silently reverts it.
   Check for drift before assuming you are in sync.
2. **Never commit credentials.** No API keys, tokens, or passwords in any file, including
   knowledge files. `.gitignore` blocks the obvious names but is not a substitute for
   checking. The Foundry API key lives only in the environment.
3. **Never commit a RAW transcript dump.** Reviewable transcripts under `transcripts/` are
   tracked on purpose, but only ever as written by `scripts/fetch_transcripts.py`, which
   redacts credentials, staff emails, and tokens on the way in. Raw API output goes to a
   scratch dir outside the repo. Never hand-write a transcript file or bypass the script —
   agents have been observed reproducing knowledge-base credentials verbatim in answers.
4. **`main` is protected.** A pull request is required for every change, including from
   admins. Zero approvals are required, so you can merge your own PR — but you cannot push
   to `main` directly. Branch, PR, merge.
5. **A Foundry write is a production change.** Collections and configs back live agents.
   Confirm with the user before uploading, deleting, syncing, or changing any config. Never
   do it as a side effect of another task.

   **Nothing reaches Foundry until it is MERGED to `main` — not merely PR'd.** Run
   `python3 scripts/preflight_upload.py <files>` first; it refuses anything whose bytes
   differ from `origin/main`. Uploading from an unmerged branch puts content in front of
   users that the repo has not accepted, and then the next drift check tries to undo it. This
   has happened once — a 6.5-hour window on 2026-08-25 — which is why the check exists.

   **After EVERY PR merge, run `python3 scripts/check_foundry_drift.py`.** A merge is the
   moment `main` gets ahead of the live agents, and nothing else notices: a knowledge file
   only reaches an agent when someone uploads it, so an unshipped change leaves the agent
   answering from old text while the repo looks correct. It covers all five collections,
   every shared file against every one of its `upload_targets`, and the team router. Report
   what it says even when the answer is "in sync".
6. **Contributors own knowledge content. Admins own routing.** The split matters because
   the blast radius differs: a bad knowledge edit gives one wrong answer, while a bad routing
   edit misroutes every conversation — and the transcript that reveals it looks like a
   content problem, so it gets misdiagnosed.

   **Contributors MAY change**, and are expected to:
   - knowledge content in any `Knowledge-<Domain>/` folder — the `Conf-`, `Docusaurus-`,
     `FAQ-`, `Misc-`, `Training-` and `GitHub-` files
   - their review verdicts under `transcripts/`

   **ADMIN-ONLY.** The list is `.github/admin-only-paths.txt` — read it rather than
   remembering it. In summary: `README.md` (the team routing table), `team-config/`,
   **every `Knowledge-*/_START_HERE.md`**, and the machinery — `CLAUDE.md`,
   `contributor-initial-prompt.md`, `transcripts/README.md`, `transcripts/ONBOARDING.md`,
   `scripts/`, `templates/`, `.github/`, `.gitignore`, `contributors.json`.

   `_START_HERE.md` catches people out. It reads like within-corpus routing and partly is,
   but it also carries **cross-agent hand-off rules** — `Knowledge-BP-General/_START_HERE.md`
   opens by telling the agent to decide whether the question belongs to one of the four
   specialized agents, and routes to Identity / Ops Center / SAC by name. That is team-level
   routing, and a path-based rule cannot own half a file, so the whole file is admin-only.

   **If you are running for a contributor, do not touch the admin-only paths.** The reason is
   specific to you: an agent that edits its own instructions then follows the edited version
   for the rest of the session, and nobody reviewing the PR can tell which rules you were
   operating under. Improving a doc feels helpful and is exactly the move to avoid.

   Found a real problem — a wrong command, a stale count, a contradiction? **Say so in your
   response and in the PR description. Do not fix it.** Being right about the problem does not
   make the edit yours to make.

   **What none of this can enforce:** nothing stops team-level routing advice being written
   *inside* a knowledge file — "for identity questions, use the Identity agent" in an FAQ is
   routing content in a file a contributor may edit. Path-based rules cannot see it. So when
   you review or write content edits, read them for routing claims and flag them. Human
   review is the only control there, and pretending otherwise is worse than knowing it.

   Enforced by CODEOWNERS plus branch protection (server-side; a PR cannot weaken it), a CI
   tripwire, and `scripts/start_review_session.sh`. All three read one boundary —
   `check_admin_paths.py` asserts CODEOWNERS and `admin-only-paths.txt` agree. **Do not edit
   the tripwire to get past it**: same violation, one level up.

7. **NEVER broaden access without asking.** The approved grants are exactly two teams:
   `onetyler-tcp-pm-admins` (**admin**) and `onetyler-tcp-pm-contributors` (**write**), plus
   named individuals from `contributors.json`.

   **The admin/write split is load-bearing, not cosmetic.** Branch protection exempts
   administrators — it has to, because a PR author cannot approve their own PR and the sole
   code owner would otherwise be permanently blocked on his own changes. So **admin =
   bypasses review; write = subject to review**. Anyone whose PRs should be approved must be
   on the *contributors* team. Adding a reviewer to the admins team silently removes the gate
   from them. Do **not**
   infer an access model by copying it from a reference repo or a sibling project — derive it
   from the actual contributor list. Anything wider than the repo owner and his own team needs
   explicit confirmation first. This repo's owner does not work across the rest of Tyler
   engineering; the scope is divisional. Since **SecureGuard**, org-wide cross-divisional
   access is not possible anyway — everything is divisionally protected — so an org-wide grant
   is both unwanted and ineffective. A public repo needs no grant for outside contribution:
   people fork and open a PR.
8. **ALWAYS back up before changing anything in Foundry, and commit the backup.** Backups
   live in the repo forever — `team-config/backups/<object>-backup-<YYYYMMDD-HHMMSS>.json`,
   never in a scratch dir, never deleted. Fetch the current object, scan it for credentials,
   commit the backup, and only then write. This applies to every config object that exists
   **only** in Foundry — teams, agents, collections metadata — because there is no other
   copy and no undo. Knowledge-file *content* is already covered by git history, but a
   config object is not.

---

## What this repo is

Knowledge corpora for the **OneTyler Cloud Living** Foundry Team agent and its five
sub-agents. Each `Knowledge-<Domain>/` folder is a deployment surface: its files are what
one agent retrieves from its tenant knowledge-base collection.

There is no application code, build, or test suite. The deliverables are content files.
See `README.md` for the team-level routing model and `_START_HERE.md` in each folder for
within-corpus routing.

---

## Session start — do these five things, every session

Before the user's first real request, in this order. It takes well under a minute and it is
what makes a session usable rather than nearly-usable.

### 0. Re-read the instructions — every day, not once

**The instructions change. Reading them once is not enough, and an agent operating from
last week's understanding will confidently apply rules that no longer hold.** This repo's
rules have changed materially on consecutive days — what a contributor may edit, whether
review header fields are required, and what must happen before anything reaches Foundry have
all moved.

At the start of every session, after pulling `main`, check what moved and re-read it:

```bash
git log --since="3 days ago" --name-only --format="%h %ad %s" --date=short -- \
  CLAUDE.md README.md contributor-initial-prompt.md contributor-update-prompt.md \
  transcripts/README.md transcripts/ONBOARDING.md \
  scripts/ templates/ .github/ .gitignore contributors.json \
  'Knowledge-*/_START_HERE.md'
```

Quote the last pathspec — git expands `Knowledge-*/` itself, and an unquoted glob fails in zsh
when no directory matches literally. (Do not try to build this list from
`.github/admin-only-paths.txt`: those are regexes, not pathspecs, and converting them produces
a glob that silently matches nothing.)

Anything listed, **re-read in full** — not the diff alone. A diff shows what changed but not
what it now means in context, and the surrounding paragraph is usually what carries the
intent.

Widen the window if you have been away longer, and if `git log` is unavailable for any
reason, re-read `CLAUDE.md`, `transcripts/README.md` and `.github/admin-only-paths.txt`
anyway — they are short and it costs less than acting on a stale rule.

**Say what you found in your first response**, even when the answer is "no instruction
changes in the last 3 days". That tells the user which rules you are operating under, which
is the thing they cannot otherwise see.

### 1. Sync the reviewer list from GitHub

New contributors join the team and cannot then be named as a `reviewer`, because
`contributors.json` is generated from team membership and the review UI offers only what is
in it. A reviewer who cannot pick their own name is stuck before they start.

```bash
python3 scripts/sync_contributors.py --check   # exits 1 if drifted
python3 scripts/sync_contributors.py           # rebuild, then commit
```

Run the `--check` first. If it reports drift, regenerate and **commit the result** — the file
is only useful to the next person if it lands in the repo.

- Uses **your own `gh` credentials**; there is deliberately no shared PAT. If it errors, the
  token probably lacks the scope: `gh auth refresh -s read:org`.
- Sources are the `onetyler-tcp-pm-admins` and `onetyler-tcp-pm-contributors` teams.
- **Never hand-edit `contributors.json`** — the next sync overwrites it and a hand-added
  entry confers no repo access anyway.
- This syncs **from** the team. It does not add anyone **to** a team: that is broadening
  access and needs the user's explicit say-so (hard rule 7).
- If the sync cannot run at all (no `gh`, no network), say so plainly rather than proceeding
  as though the list were current — a stale list silently blocks the new contributor.

### 2. Start the review server

**Use the launcher, not the server directly.** It also updates the repo, refreshes the
reviewer list and fetches new transcripts, which are steps 1 and 3 of this list:

```bash
python3 scripts/start.py             # http://127.0.0.1:7777, opens the browser
python  scripts\start.py             # Windows
```

Humans double-click `Start-reviewing.command` (macOS) or `Start-reviewing.bat` (Windows) and
never need you for this — say so rather than offering to run it for them. See
`RUNNING-WITHOUT-AI.md`, which is the page to point a contributor at.

Run the bare server only when you need it detached from a session or on a different port:

```bash
python3 scripts/review_server.py --port 7778 --no-browser
```

Either way, **confirm it answers before telling anyone it is up**, and quote the port you
actually used. Loopback-only; nothing leaves the machine except avatar images (`--no-avatars`
turns even those off).

⚠ A harness-tracked background task gets reaped when the turn ends. Launch it detached
(`nohup … & disown`, then check `ppid` is 1) or it will be dead by the time they click the
link.

### 3. Check Foundry still matches the repo

Only if a merge has landed since anyone last looked, which after any active day it will have:

```bash
python3 scripts/check_foundry_drift.py
```

Cheap, read-only, and it catches the case nothing else does — `main` carrying content the
live agents have not received. Mention the result in your first response either way; "in
sync" is information too. If it reports drift, do NOT fix it silently: say what drifted and
in which direction, and ask, because an upload is a production change (hard rule 5).

### 4. Finish by putting the URL in front of them

**End your first response with the URL, visually separated — not buried in a paragraph.**
Every admin and every contributor needs it, and it is the one thing that makes the review
queue reachable. Something like:

```
────────────────────────────────────────────
  Transcript review UI:  http://127.0.0.1:7777
  4 pending · 1 suggestion awaiting you
────────────────────────────────────────────
```

Include the counts from `python3 scripts/review_status.py` — "4 pending" tells someone
whether to open it now. If suggestions are waiting on them specifically
(`--suggestions --for <user>`), say so on that line: it is addressed to them and nobody else
will pick it up.

---

## Constants — agent, team, and collection IDs

Verified live 2026-08-21. Everything lives in tenant **Tyler Technologies**, project
*OneTyler - Cloud Living Agents - v1.0.0*.

| Sub-agent | Agent ID | KB collection | Local folder | Foundry upload? |
|---|---|---|---|---|
| Ops Center | `5b3efdff-921a-4131-be81-b7a4be427d9b` | `OT-OpsCenter` | `Knowledge-OpsCenter/` | ✅ yes |
| General Blueprint Docs Agent | `bd1c5d91-8234-486e-9f5a-2f1b7a947426` | `OT-BPD` | `Knowledge-BP-General/` | ✅ yes |
| Support Access Center | `55444576-1fa3-4d12-a738-6ba83b17e6a7` | `OT-SAC` | `Knowledge-SupportAccessCenter/` | ✅ yes |
| Aligned Releases | `b0544224-b120-469a-8f39-c4a7b14c17c0` | `OT-AlignedReleases` | `Knowledge-AlignedReleases/` | ✅ yes |

All five collections are writable from this repo.
| Tyler Identity Assistant | `3f5e586f-0d0f-4638-9839-bebe45a6cb47` | `TCP-KB-Identity` | `Knowledge-TylerIdentity/` | ✅ yes (since 2026-08-24) |

Team **OneTyler Cloud Living**: `e92bd437-cb84-4e18-88e6-757370b39c90`

**Go-live: `2026-08-19 19:42:29 UTC`.** The merge of `tyler-technologies/tcp-ops-center`
PR **#1206** ("Feat/cd 285/foundry chatbot"), which shipped the chatbot into Ops Center.
Every Foundry conversation **before** that instant is the team testing their own agents, not
user signal — see *Acting on transcript reviews*. Use the full timestamp, not the date: the
2026-08-19 21:28 UTC transcript is post-go-live while the merge was 19:42 the same day.

Base URL: `https://foundry.tylertechai.com` (override with `$FOUNDRY_API_URL`).

Re-verify IDs rather than trusting this table if anything 404s — agents can be recreated.
List agents with `GET /api/transcripts/agents`.

---

## Setup

### 1. The API key

```bash
test -n "$FOUNDRY_API_KEY" && echo "key set (${#FOUNDRY_API_KEY} chars)" || echo "NOT SET"
```

If unset, ask the user for it. Assume they know how to load an env var — the part worth being
explicit about is **where the key is kept**, because the obvious answer is wrong here.

#### Keep it in the OS credential store, not in a file

**Ask which platform the user is on before giving instructions.** The team runs both macOS and
Windows, and the two have different credential stores and different cloud-sync traps.

##### macOS — Keychain

This is the documented default as of 2026-08-26. No plaintext on disk, encrypted at rest,
unlocked by the login session:

```bash
# store once — prompts for the value, so it never lands in shell history
security add-generic-password -a "$USER" -s foundry-api-key -U -w

# in ~/.zshrc
export FOUNDRY_API_KEY=$(security find-generic-password -a "$USER" -s foundry-api-key -w)
```

Verify with the request in step 3 below rather than assuming the export worked. A shell that
was already open will not have it — the user needs a fresh terminal.

Caveats, so this is not oversold: the first access from a new process may prompt for keychain
permission, and a cron or otherwise non-interactive run needs the keychain unlocked. If that
bites, the file fallback below is legitimate.

##### Windows — DPAPI-encrypted file (PowerShell)

The closest equivalent, with no modules to install. `ConvertFrom-SecureString` encrypts with
DPAPI keyed to **that user on that machine**, so the file is useless if copied anywhere else —
including if OneDrive syncs it:

```powershell
# store once — prompts, so the value never lands in PowerShell history
New-Item -ItemType Directory -Force "$env:LOCALAPPDATA\Foundry" | Out-Null
Read-Host -AsSecureString "Foundry API key" | ConvertFrom-SecureString |
  Set-Content "$env:LOCALAPPDATA\Foundry\key.dpapi"

# add to your PowerShell profile ($PROFILE)
$sec = Get-Content "$env:LOCALAPPDATA\Foundry\key.dpapi" | ConvertTo-SecureString
$env:FOUNDRY_API_KEY = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
  [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec))
```

`%LOCALAPPDATA%` is deliberate: unlike `%USERPROFILE%\Documents` or `%OneDrive%`, it is not
roamed or cloud-synced.

If they would rather use PowerShell SecretManagement (`Install-Module Microsoft.PowerShell.SecretStore`),
that is also fine and arguably nicer — it just needs a module install, which some machines
restrict.

**A plain user environment variable is NOT equivalent.** `setx FOUNDRY_API_KEY ...` stores the
key as cleartext in the registry under `HKCU\Environment`, readable by any process running as
that user and visible in `setx` history. Use it only if the options above are unavailable, and
say plainly that it is weaker.

##### Running the tooling on Windows

The Python scripts are stdlib-only and run as-is with `python` instead of `python3`.
`scripts/start_review_session.sh` is bash — it works under **Git Bash** (ships with Git for
Windows) or WSL, but not in PowerShell or cmd. If a contributor is stuck, the equivalent is
`git switch main && git pull --ff-only`, then `python scripts/fetch_transcripts.py` and
`python scripts/review_status.py`.

#### If a file is used instead — three rules, not two

1. **Outside this repo.** `.gitignore` blocks `*.env` and `foundry-secrets*`, but that is a
   backstop; being outside the working tree is the actual control.
2. **Outside any cloud-synced folder** — OneDrive, Dropbox, iCloud Drive, Google Drive.
   This is the one that catches people, including this repo's own instructions until
   2026-08-26: they said "one directory above this checkout", and for a checkout under
   `~/Library/CloudStorage/OneDrive-.../Repo/...` that put a live production key straight into
   OneDrive, replicated off the laptop and onto every device on the account. A path can
   satisfy rule 1 and still be badly wrong.

   On Windows the same trap is `C:\Users\<you>\OneDrive - Tyler Technologies, Inc\...`, and
   note that `Documents` and `Desktop` are often redirected into OneDrive by policy — so those
   are cloud-synced even though the path does not say so. `%LOCALAPPDATA%` is not.
3. **`chmod 600`.** It is a tenant-scoped production credential that can rewrite what live
   agents tell customers.

Safe locations that satisfy all three, wherever the repo is checked out:
`~/.config/foundry/secrets.env` (`chmod 700` the directory) on macOS/Linux, and
`%LOCALAPPDATA%\Foundry\` on Windows.

**Check, do not assume.** If the user already has a key file, test the path rather than trust
it:

```bash
f=<their key file>
ls -l "$f"                       # want -rw------- (600)
case "$(cd "$(dirname "$f")" && pwd -P)" in
  *CloudStorage*|*Dropbox*|*"Google Drive"*|*"Mobile Documents"*)
    echo "CLOUD-SYNCED — this key is leaving the machine; tell the user" ;;
  *) echo "not cloud-synced" ;;
esac
```

**A key that has been in a cloud-synced folder, a chat window, or a log should be rotated,**
not just relocated. Deleting the file does not purge OneDrive version history.

Never write the key into a file in this repo, a script, a command that gets committed, or your
own response. Never ask the user to paste it to you — point them at **Dev → API Keys**.

**Every person uses their own key.** Keys are per-user, so a shared one would make every
action look like one person's in the audit trail and rotating it would break everyone at once.
Keys are tenant-scoped (a key from another tenant returns 403 with no useful message) and each
user may hold 10. A 401 means the key was rotated or revoked — ask for a fresh one.

Note what a contributor's key can do: **uploading changes what live agents tell users, with no
review gate of its own.** The only thing keeping that honest is hard rule 5 — upload only what
is already merged to `main`, and run `preflight_upload.py` to prove it.

### 2. Two required request headers

```bash
-H "X-API-Key: $FOUNDRY_API_KEY"     # NOT "Authorization: Bearer" — that form is deprecated
-A "claude-code-foundry-kb/1.0"      # any User-Agent; a request with none gets a 403 from the WAF
```

The missing-User-Agent 403 is the single most confusing failure mode: the key is valid, the
URL is right, and it still fails. Always pass `-A`.

### 3. Verify access before doing anything else

```bash
curl -s -A "claude-code-foundry-kb/1.0" -H "X-API-Key: $FOUNDRY_API_KEY" \
  "https://foundry.tylertechai.com/api/transcripts/agents" \
  -o /tmp/agents.json -w "HTTP %{http_code}\n"
```

HTTP 200 and a JSON array means you are good. HTML back means auth failed and you were
redirected to a login page.

### 4. Is there a Foundry MCP server?

**No — use the REST API.** There is no MCP server for *managing* Foundry, and none is
configured in this project. Do not go looking for `mcp__foundry__*` tools.

Two things are easy to confuse here:

- **MCP *inside* Foundry** — Foundry agents can call external MCP tool servers you register
  in Dev Studio → MCP Registry. That is a runtime capability *of the agents*, unrelated to
  managing knowledge bases or reading transcripts.
- **`mcp__tcp-mcp__*` tools** — if present in your session, these query the **Tyler Cloud
  Platform** database (orgs, workspaces, products, profiles, audit logs). Useful for
  fact-checking knowledge-file content, but they have nothing to do with Foundry.

For the full API surface beyond what's documented here, Foundry serves an OpenAPI 3.1 spec
plus Swagger UI at `/api/swagger-ui`, and there is an API Explorer at `/dev/api-explorer`.
There is **no Python or .NET SDK** — the only client SDK is TypeScript (`@ai-foundry/sdk`),
and it is for embedding chat widgets, not for this work. Call REST directly.

---

## Pulling transcripts

### Which API to use

There are two, and the obvious one is the wrong one:

- ❌ `/api/chat/conversations` — scoped to **your own** conversations only. Useless for
  corpus analysis, despite being the documented one.
- ✅ `/api/transcripts/*` — admin-scoped, sees all conversations you have rights to. Use
  this. It is not documented on Confluence.

### Endpoints

| Purpose | Endpoint |
|---|---|
| List agents | `GET /api/transcripts/agents` |
| List teams | `GET /api/transcripts/teams` |
| Find agent conversations | `GET /api/transcripts/conversation_ids` |
| Find team conversations | `GET /api/transcripts/team_conversation_ids` |
| Full agent transcript | `GET /api/transcripts/{conversationId}` |
| Full team transcript | `GET /api/transcripts/team/{conversationId}` |
| Aggregate stats | `GET /api/analytics/stats` |
| Run-level logs (tokens, model, errors) | `GET /api/agent-logs?agentId=…` |
| OpenTelemetry spans for a run | `GET /api/agent-logs/spans?runId=…` |

`conversation_ids` parameters: `agent_id`, `feedback` (`positive`/`negative`),
`conversation_type=conversation_with_feedback` (any feedback), `search` (free text, max 500
chars), `startDate` / `endDate` (`MM/DD/YYYY`, `YYYY-MM-DD`, or ISO 8601).
`team_conversation_ids` takes the same plus `team_id`, and includes `feedbackType` inline.

### Example — list then fetch

```bash
UA="claude-code-foundry-kb/1.0"; B="https://foundry.tylertechai.com"
AGENT="5b3efdff-921a-4131-be81-b7a4be427d9b"   # Ops Center

# list
curl -s -A "$UA" -H "X-API-Key: $FOUNDRY_API_KEY" \
  "$B/api/transcripts/conversation_ids?agent_id=$AGENT&startDate=01/01/2026" \
  | python3 -m json.tool

# fetch one (returns a single-element array)
curl -s -A "$UA" -H "X-API-Key: $FOUNDRY_API_KEY" \
  "$B/api/transcripts/<CONVERSATION_ID>" | python3 -m json.tool
```

### Transcript shape

```
[{ "conversationId": "...",
   "conversation": [
     { "question": "...", "response": "...",
       "feedback": "THUMBS_UP | THUMBS_DOWN | NO_ACTION",
       "thumbsDownTextFeedback": "user's written complaint",
       "metadataMessages": [ ... full message stream incl. toolCalls and tool results ... ] }]}]
```

**`metadataMessages` is the whole point.** It shows what the agent actually did. Use it to
tell apart four failures that look identical in the visible chat:

| What you see in `metadataMessages` | Diagnosis | Fix belongs in |
|---|---|---|
| No tool calls at all | Answered from model priors | Agent prompt |
| `searchTenantKnowledge` returned nothing | Content missing or unretrievable | **Knowledge file** |
| Searched, got irrelevant chunks | Wrong content or bad chunking | **Knowledge file** |
| Got the right chunks, answered badly | Reasoning/prompt problem | Agent prompt |

Only the middle two are knowledge-file problems. Do not rewrite a knowledge file to fix a
prompt bug.

### Gotchas

- **200-result cap**, newest first. Exactly 200 back means you are truncated — narrow the
  date window and page through.
- Default lookback is **3 months** if you omit `startDate`.
- `/api/analytics/feedback` and `/api/analytics/feedback-trends` are unreliable (they read a
  different table). Use `/api/transcripts/*` for feedback and `/api/analytics/stats` for
  totals.
- **There is very little feedback on these agents** (as of 2026-08-21: one rated
  conversation across the whole team). Expect to analyze raw conversations rather than
  filtering on thumbs-down.
- Write dumps outside the repo (`/tmp/...`), never into it. See Hard Rule 3.

---

## Pushing KB files

### The model you must internalize

**Re-uploading the same filename replaces it cleanly, in place.** Verified 2026-08-22 on
`OT-OpsCenter`: the response returns the **same `id`** with `wasUpdated: true`, the new
`fileSize`, and `ingestionStatus` reset to `pending`. The collection file count does not
change and **no duplicates are created**. You do not need to delete the old record first.

**The filename is the identity key.** So a *rename* is not an update — uploading
`NewName.md` adds a second record and leaves `OldName.md` in place. Renaming therefore
requires upload-new → `DELETE` old → verify count.

Always pass an explicit mime type: `-F "files=@X.md;type=text/markdown"`. Without it curl
sends `application/octet-stream`, which lands in the file record and makes the collection
inconsistent with files uploaded through the UI.

### Endpoints

| Purpose | Endpoint |
|---|---|
| List collections | `GET /api/tenant-knowledge-base/collections` |
| Create collection | `POST /api/tenant-knowledge-base/collections` `{name}` |
| List files + status | `GET /api/tenant-knowledge-base/collections/{name}/files` |
| **Download a file** (undocumented) | `GET /api/tenant-knowledge-base/collections/{name}/files/{fileId}/download` |
| Upload files | `POST /api/tenant-knowledge-base/collections/{name}/files` (multipart, field `files`) |
| Delete a file | `DELETE /api/tenant-knowledge-base/collections/{name}/files/{fileId}` |
| Start ingestion | `POST /api/tenant-knowledge-base/sync` → `{jobId}` |
| Poll ingestion | `GET /api/tenant-knowledge-base/sync/{jobId}` |
| Refresh statuses (read-only) | `POST /api/tenant-knowledge-base/reconcile-statuses` |
| Retrieval probe | `POST /api/tenant-knowledge-base/retrieve` |

Upload limits: **10 files per request**, 100 MB per file. Allowed extensions include `md`,
`txt`, `pdf`, `docx`, `csv`, `xlsx`, `png`, `jpg`.

### Step 1 — detect drift before changing anything

`fileSize` on the file record is your drift signal (there is no content hash). Compare
against local bytes:

```bash
UA="claude-code-foundry-kb/1.0"; B="https://foundry.tylertechai.com"
COL="OT-OpsCenter"; DIR="Knowledge-OpsCenter"
curl -s -A "$UA" -H "X-API-Key: $FOUNDRY_API_KEY" \
  "$B/api/tenant-knowledge-base/collections/$COL/files" -o /tmp/kbf.json
python3 - "$DIR" <<'PY'
import json, os, sys
for f in sorted(json.load(open('/tmp/kbf.json')), key=lambda x: x['fileName']):
    p = os.path.join(sys.argv[1], f['fileName'])
    if os.path.exists(p) and os.path.getsize(p) != f['fileSize']:
        print(f"DRIFT {f['fileName']:46} kb={f['fileSize']:>7} local={os.path.getsize(p):>7}")
PY
```

Sizes matching is strong but not conclusive evidence of identical content. If it matters,
download the remote copy with the download endpoint above and `diff` it.

### Step 2 — upload ALL files, THEN sync once

This is the biggest trap. Bedrock runs **one ingestion job at a time per data source**, and
a job only indexes files present in S3 when its scan snapshot is taken. Every upload request
**auto-triggers its own scoped sync**. So a naive 30-file upload becomes 3 queued jobs, the
first indexes only its 10 files, and the rest sit `pending` for hours.

Correct order: **upload every batch first → then trigger ONE consolidated sync → poll to
terminal → re-sync until everything reports `ingested`.**

```bash
UA="claude-code-foundry-kb/1.0"; B="https://foundry.tylertechai.com"; COL="OT-OpsCenter"

# upload (repeat -F per file, max 10 per request; ALWAYS set the mime type)
curl -s -A "$UA" -H "X-API-Key: $FOUNDRY_API_KEY" \
  -F "files=@Knowledge-OpsCenter/Misc-Links.md;type=text/markdown" \
  -F "files=@Knowledge-OpsCenter/_START_HERE.md;type=text/markdown" \
  "$B/api/tenant-knowledge-base/collections/$COL/files"

# ...all other batches...

# ONE consolidated sync — Content-Type header is REQUIRED even with no body
curl -s -X POST -A "$UA" -H "X-API-Key: $FOUNDRY_API_KEY" \
  -H "Content-Type: application/json" \
  "$B/api/tenant-knowledge-base/sync"       # -> {"jobId":"...","status":"STARTING"}

# poll (jobs on a large shared tenant can take a long time)
curl -s -A "$UA" -H "X-API-Key: $FOUNDRY_API_KEY" \
  "$B/api/tenant-knowledge-base/sync/<JOB_ID>"
```

Omitting `Content-Type: application/json` on `POST /sync` returns
`{"error":"Content-Type must be application/json"}` — easy to mistake for a transient
failure and retry pointlessly. `POST /sync` *also* returns genuine intermittent 500s
(`{"error":"Failed to start sync"}`) on Bedrock job conflicts; retry those every ~45s.

**If you uploaded a single batch (≤10 files), you probably don't need a manual sync at
all** — the upload's own auto-sync picks it up, and the files will already be `ingesting`
by the time you look. Check statuses before starting another job; launching a second sync
while one is running just queues behind it.

The sync job covers the **whole tenant** data source, so `numberOfDocumentsScanned` and
`numberOfDocumentsFailed` include other teams' files. Judge your collection by its own file
statuses and retrieval probes, never the global counters.

### Step 3 — verify retrieval, not status

**`ingestionStatus: "ingested"` proves nothing.** A file can report ingested and hold zero
retrievable text. Markdown avoids the worst of this (the classic victims are scanned or
encrypted PDFs), but always confirm:

```bash
curl -s -X POST -A "claude-code-foundry-kb/1.0" -H "X-API-Key: $FOUNDRY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"<question the file should answer>","numberOfResults":5,
       "searchType":"HYBRID","filterCollectionNames":["OT-OpsCenter"]}' \
  "https://foundry.tylertechai.com/api/tenant-knowledge-base/retrieve" \
  | python3 -c "
import json,sys
for r in json.load(sys.stdin):
    uri=str(r.get('metadata',{}).get('x-amz-bedrock-kb-source-uri','?')).split('/')[-1]
    c=r.get('content') or ''
    print(round(r.get('score',0),3), 'len=%d'%len(c), uri[:60])"
```

**Always pass `filterCollectionNames`.** An unfiltered retrieve searches the entire shared
tenant KB — other teams' collections included — which both pollutes your results and
misrepresents what the agent sees (the agent's own `searchTenantKnowledge` is scoped to the
collections in its config).

Red flags: zero results for content that should match, or results with `len=0` (the file
indexed but produced no text).

**Retrieval can go live before `ingestionStatus` flips.** Measured 2026-08-22 on a 6-file
replace in `OT-OpsCenter`: retrieval was already serving the new chunks (and had purged the
superseded ones) within ~100 seconds, while the status field stayed `ingesting` until
**~6 minutes** after upload. So a content probe confirms a change sooner and more reliably
than the status field — but expect **minutes, not hours**. If files are still `ingesting`
after ~30 minutes, treat that as a real problem worth investigating, not as normal lag.

To confirm, probe for a string that exists **only** in the new version, and separately
confirm a string unique to the **old** version returns nothing:

```bash
# did the new text land, and is the old text gone?
... | python3 -c "
import json,sys
rs=json.load(sys.stdin)
print('new:', sum('<STRING ONLY IN NEW VERSION>' in (r.get('content') or '') for r in rs))
print('old:', sum('<STRING ONLY IN OLD VERSION>' in (r.get('content') or '') for r in rs))"
```

`new>0 and old==0` means the reindex is done regardless of what the status field says.

Note that **re-sync cannot repair an already-indexed file** — Bedrock skips what it
considers indexed. Delete and re-upload instead.

### Step 4 — record what needs re-uploading

End any response that edits knowledge files with an explicit, visually separated list of the
files to re-upload and which collection they belong to. Do not bury it in prose.

---

## Renaming a knowledge file — read before you do it

Because there is no update-in-place, **renaming a file locally and pushing creates a second
file in the collection** rather than renaming the existing one. To rename properly:

1. Upload under the new name.
2. `DELETE` the old file record by its `fileId`.
3. Sync once.
4. Verify the collection has exactly one copy.

This was applied to `Knowledge-TylerIdentity/Docusaurus-Identity.md` on 2026-08-24: uploaded
under the new name, `tyler-identity-knowledge-base.md` deleted from `TCP-KB-Identity`, count
verified. That collection is now fully in sync with this repo.

Note the asymmetry: re-uploading the *same* name is a clean in-place replace (see "The
model you must internalize"), so ordinary content updates need no deletion. Only renames do.

---

## Changing the team router prompt — ADMINS ONLY

**You can do this yourself. Do not hand it back to the user as manual work.** It is the
highest-blast-radius object in the system, so it needs a procedure — not avoidance. Everything
below was verified end to end on 2026-08-27.

**Who:** repo admins only. `team-config/` is admin-only (hard rule 6), and this is a
production config change (hard rule 5), so **confirm the change with the user first** and
never do it as a side effect of another task. If you are running for a contributor, stop and
say the change needs an admin.

**Why it is worth doing rather than deferring:** editing
`team-config/team-routing-prompt.md` changes *nothing* at runtime — it is only a mirror. Until
the live prompt changes, routing behaves exactly as before, so a repo-only "fix" to a routing
bug is not a fix at all.

### The procedure

```bash
T=e92bd437-cb84-4e18-88e6-757370b39c90      # OneTyler Cloud Living
UA="claude-code-foundry-kb/1.0"; B="https://foundry.tylertechai.com"
```

**1. Native version snapshot — a real restore point.**

```bash
curl -s -X POST -A "$UA" -H "X-API-Key: $FOUNDRY_API_KEY" -H "Content-Type: application/json" \
  -d '{"type":"full","name":"pre-<what-you-are-changing>-YYYYMMDD"}' "$B/api/teams/$T/versions"
```

`type` is **required** and must be `"full"` or `"draft"` — undocumented in the OpenAPI spec;
omitting it returns a 400 Zod error that names the allowed values. Foundry also auto-creates a
version when someone saves in the UI, so there is usually a recent one already.

Restore path if anything goes wrong:
`POST /api/teams/{teamId}/versions/{versionId}/restore`.

**2. Back up the object to the repo as well, and commit it** (hard rule 8) —
`team-config/backups/team-backup-<YYYYMMDD-HHMMSS>.json`. Scan it for credentials first.

**3. Fetch the CURRENT live object and edit only `system_prompt`.** Never build the payload
from an older backup: someone may have edited in the UI since. Assert your find-target appears
**exactly once** before replacing it.

**4. No angle brackets in prompt text.** Foundry HTML-escapes `>` and strips `<tag>`-shaped
text, so a prompt containing them comes back altered. Use hyphens for dashes.

**5. PUT the FULL object back.**

```bash
curl -s -X PUT -A "$UA" -H "X-API-Key: $FOUNDRY_API_KEY" -H "Content-Type: application/json" \
  --data @payload.json "$B/api/teams/$T"
```

The spec documents **no request body** for this endpoint, so the semantics are not knowable
from the docs. Measured: it is a **full replace**, and sending the whole 18-field object back
loses nothing. Sending only `{"system_prompt": ...}` risks wiping `agent_ids`,
`orchestrator_config`, `routing_rules` and `chatExperience` — which would take the team down.
Send everything.

**6. Verify — three checks, all of them.**

- `system_prompt` matches your intended text **exactly** (not just "longer than before"), and
  contains no `&gt;` / `&lt;` / `&amp;`.
- **Field-by-field diff against the pre-PUT backup.** Only `system_prompt` and `updated_at`
  may differ. This is the check that catches a bad payload contract.
- **A behavioural test, plus a control.** Text landing is not the same as routing changing.

```bash
curl -s -N -X POST -A "$UA" -H "X-API-Key: $FOUNDRY_API_KEY" -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"<the question that was misrouted>"}]}' \
  "$B/api/team/$T/stream"
```

Note the payload shape: **`messages` array**, not `message` — the singular form returns
`400 Messages array is required`. The response is SSE `text-delta` chunks, so **reassemble the
deltas before matching on content**; grepping the raw stream fails because words are split
across chunks. Read which collection the answer cites to see where it routed.

Always run a **control** question that must still route somewhere else, or you have only shown
you can pull everything toward one agent.

**7. Update `team-config/team-routing-prompt.md` to match**, so
`scripts/check_foundry_drift.py` reports the router in sync. Update `README.md` too if the
team-level routing rules changed.

## Acting on transcript reviews

`transcripts/` holds preserved conversation history, one markdown file per conversation,
with review fields in the frontmatter. Humans review; you act on what they wrote. Full
workflow and field definitions: `transcripts/README.md`.

Humans review through a local web UI (`python3 scripts/review_server.py`, loopback-only on
port 7777) or by editing the markdown directly. Either way the output is the same files.

**The lifecycle is `pending → suggested → reviewed → pushed`** (plus `excluded` for
pre-go-live testing). `reviewed` is your inbox. `pushed` means processed *and* live in
Foundry — it is a claim about Foundry, not the repo, so only set it after the upload is
verified. Close out with `python3 scripts/mark_pushed.py`, which refuses to close a transcript
whose `kb_action` is still unresolved.

**`suggested` is not your inbox.** It is a reviewer's worked-up opinion on an area they do not
own, handed to the owner named in `awaiting`, with `suggested_by` recording who wrote it and
`reviewer` deliberately blank. The fields look exactly like a finished verdict, which is the
trap: acting on one applies a change nobody approved and takes the decision away from the
person the state exists to reserve it for. `--actions` lists these separately as "not
actionable yet" and `mark_pushed.py` refuses them; do not work around either. If a suggestion
looks obviously right and is blocking, say so and ask the owner to accept it — never accept it
on their behalf, and never put a human's name in `reviewer` yourself.

**Your half of the process is steps (e)–(g):** process the reviewed ones, update knowledge
files if needed, open a **PR** (do not push content changes straight to `main` — the admin
exemption exists so the owner isn't blocked, not so you can skip review), then upload to
Foundry and mark the transcripts `pushed`. Full seven-step process: `transcripts/README.md`. A new human reviewer is onboarded via `transcripts/ONBOARDING.md` — keep it accurate when the tooling or process changes, since it is the first thing they read.

**To find work:**

```bash
python3 scripts/review_status.py --actions   # reviewed items with an open KB action
python3 scripts/review_status.py             # dashboard + regenerate INDEX.md
```

**Review collisions are a real failure mode.** Two people can first-review the same
transcript and both diffs apply cleanly, so the second merge silently overwrites the first
verdict. `scripts/validate_reviews.py` runs in CI and fails a PR that re-marks something
already `reviewed` on the base branch unless `review_round` is raised. Never resolve that by
lowering the round or reverting the other person's verdict — pull the base branch, read it,
and re-review explicitly if you still disagree.

**READ ALL THE FEEDBACK AS ONE BODY BEFORE CHANGING ANYTHING.** Do not walk the reviewed
transcripts one at a time, fixing each as you go. Read every piece of feedback in the batch
first, then decide what to change.

The reason is that the same underlying problem shows up in several transcripts wearing
different clothes, and one-at-a-time processing produces three narrow patches instead of one
correct fix. A worked example, from the 2026-08-27 batch: three separate transcripts —
org-admin access, internal org creation, and an Admin Center login error — each carried a
note about the wrong ticket link. Treated individually they look like three content gaps. Read
together they are one missing rule about which link to hand out, fixed once.

The reverse trap is just as real: two transcripts can look like the same question and need
different fixes. In that same batch, "I need to be added as an org admin" and "add org admin
to org" are the same question, but one got a good answer needing refinement and the other got
a clarifying question instead of an answer — a content refinement versus a retrieval failure.

So, in order:

1. Read every reviewed transcript's prose in full, plus the questions and the answers given.
2. Group the feedback by underlying cause, not by transcript.
3. **Check what is already fixed.** Some feedback predates a change you already shipped.
   Compare the transcript's `date:` against when the relevant file was last uploaded, and
   test the question live before writing anything. Do not re-fix something that works.
4. Decide the smallest set of changes that covers the whole batch, then apply them.
5. Report per-transcript so the reviewer can follow their own feedback through, even where
   several transcripts resolved to one change.

**`contributor-initial-prompt.md` AND `contributor-update-prompt.md` CONTAIN NOTHING BUT THE
PROMPT.** No title, no headings, no copy-paste markers, no explanation, no "what should happen"
section. Every explanatory word belongs in `contributor-prompting-guide.md` instead.

The reason is observed, not theoretical: the first contributor copied an entire prompt file —
surrounding commentary included — and pasted the lot. No damage, but it showed that asking
someone to select the right block between markers is a design flaw, not a user error. Now the
whole file IS the block, so copying everything is the correct action and there is no wrong part
to pick.

**So if you find yourself adding a heading or a note to either file, stop** — put it in the
guide and link to it. Anything you add to those files is text a human will paste to an agent as
if you had addressed it to them.

**WHEN YOU REFER TO A TRANSCRIPT, GIVE A LOCATOR THE HUMAN CAN OPEN.** Never identify one by
its hash alone. `75043484` means nothing to the person who wrote the feedback — they reviewed
it in a browser, not in a filename.

Every time you mention a transcript in a question or a report, include:

```
http://127.0.0.1:7777/t/<agent>/<YYYY-MM-DD>--<hash>.md
```

plus **the question the user actually asked, quoted**, and the date. The question text is what
they will recognise; the URL is what lets them check you. For example:

> **http://127.0.0.1:7777/t/team/2026-08-26--75043484.md** — 2026-08-26 16:23, team agent,
> asked: `add org admin to org`

Use the repo-relative path as well when the point is about the file rather than the
conversation (`transcripts/team/2026-08-26--75043484.md`), and quote the reviewer's own note
back when you are asking what they meant by it — they wrote it hours or days ago.

If the review server is not running, start it, or say plainly that the URL will not resolve
until it is. A link that 404s is worse than a path.

This came from getting it wrong: a question referring to "75043484" was unanswerable because
nobody could find what it pointed at.

**ASK WHEN FEEDBACK IS AMBIGUOUS. NEVER ASSUME.** If a piece of feedback could reasonably
mean two different things, stop and ask which. Do not pick the more likely reading and
proceed.

This costs a round-trip and saves a wrong change to a live agent. The asymmetry is the whole
argument: a question costs minutes, while a misread correction ships wrong content to
customers, looks resolved on the dashboard, and is only caught if someone re-reads the
transcript later.

Ambiguity worth asking about, in practice:

- **Where a fix belongs** when the feedback describes a behaviour rather than a fact — a
  knowledge file, an agent's system prompt, or the team router. These have different owners
  and different blast radii, and only the knowledge file is yours to change from here.
- **Which transcript or file** a reference points to, when the feedback says "the same as the
  other one" or "that page" and more than one candidate exists.
- **How far to go** — whether "improve the answer" means editing existing content or writing
  a new entry, and whether it should apply to one agent or all of them.
- **Anything requiring the user's own action**, such as a Foundry UI edit. Never assume they
  will do it; confirm they want to.

Ask **one question at a time**, not a bundled list, and do all the unambiguous work first so
the question is not blocking progress. State plainly what you have already done, what you are
blocked on, and what you would do under each reading.

**THE PROSE IS THE FEEDBACK. THE FIELDS ARE A HINT, AND OFTEN A WRONG ONE.**

Reviewers write the correction under the bad answer, and/or a **Proposed fix**, and click
*Mark reviewed*. They frequently do not touch the dropdowns — and they are not expected to.
Writing "this is wrong, it should have said X" is the valuable part; turning that into
`diagnosis` and `fix_target` is clerical work, and it is **your** job.

This matters because the form opens **pre-filled as "nothing wrong"** (routing `correct`,
answer `good`, diagnosis `n-a`, `fix_target: none`, `kb_action: none`,
`action_status: none-needed`), so a transcript can assert nothing is wrong in its frontmatter
while its body says the answer was wrong. Measured on 2026-08-26 in exactly that state:
`--check` passed and `--actions` printed **nothing** while the dashboard said work was
waiting. An agent followed that pointer, found an empty list, and would have concluded there
was nothing to do.

So:

1. **Read the whole transcript body** — every `<!-- review:N -->` block and the
   `<!-- proposed-fix -->` block. Never decide there is no work from the fields alone.
2. `--actions` now reports these under *"reviewed transcript(s) with WRITTEN feedback and no
   classification"*. Treat that list as the real inbox.
3. **You may — and should — fill in the classification fields from the prose**:
   `routing_verdict`, `reassign_to`, `answer_verdict`, `diagnosis`, `fix_target`, `kb_action`,
   `kb_files`, `action_status`. Say in your response which values you derived and from which
   sentence, so a human can check your reading.
4. **Never set or change `review_status` or `reviewer`.** Those record a human's judgement
   and their identity. The human has already reviewed it; you are classifying, not deciding.
   Do not "upgrade" a `suggested` transcript to `reviewed` either.
5. If the prose is genuinely ambiguous, **ask** rather than picking a `diagnosis` — the wrong
   diagnosis sends the fix to the wrong place, which is worse than a delay.
6. Clear the `needs-triage` marker from `notes` once you have classified it, and record what
   you concluded.

**Only act on files with `review_status: reviewed`.** A `pending` file has not been looked
at by a human, and a `suggested` one has been looked at by someone who explicitly declined to
decide; do not infer corpus changes from either unprompted.

The `reviewer`, `suggested_by`, and `awaiting` fields are all constrained to the `github`
values in `contributors.json`, which is
a **generated file** — `python3 scripts/sync_contributors.py` rebuilds it from the
`onetyler-tcp-pm-admins` and `onetyler-tcp-pm-contributors` GitHub teams. Never hand-edit it:
an entry added by hand is overwritten on the next sync and confers no repo access anyway. To
add a reviewer, add them to the contributors team, re-run the sync, and commit.
`--check` exits 1 when the file has drifted from team membership.

Never invent a reviewer name, and never set `review_status: reviewed` yourself — that field
records a human's judgement. `python3 scripts/review_status.py --check` enforces both
(unknown reviewer, or reviewed-with-no-reviewer, exits 1); run it before committing review
changes.

For each open action:

1. Read the transcript — the `diagnosis` field, and the reviewer's "should have said" text
   in the `<!-- review:N -->` block.
2. **Check `fix_target` first.** It states where the reviewer decided the fix belongs:
   `knowledge-file`, `agent-instructions`, `team-routing`, `sample-prompts`, or `none`. Only
   `knowledge-file` means you edit a corpus file. For the others, the deliverable is a
   concrete proposal, not a corpus edit — read the `## Proposed fix` block and either apply
   it where you can (the team routing table in `README.md`, a `_START_HERE.md` hand-off
   rule) or surface it to the user for the parts you cannot change from here, such as an
   agent's system prompt or its sample questions, which live in Foundry rather than in this
   repo.
3. **Respect the diagnosis.** It encodes whether this is a knowledge problem at all:
   `search-empty` and `search-irrelevant` are corpus problems; `no-search` and
   `retrieved-ok-answered-badly` are agent-prompt problems, and `routing-only` is a team
   routing-rules problem. Do not edit a knowledge file to paper over a prompt bug — say so
   and leave `kb_action: none`.
4. Make the edit in the file(s) named by `kb_files`, following the conventions below.
5. Update that folder's `_START_HERE.md` if you added, renamed, or removed a file.
6. Set `action_status: applied` in the transcript frontmatter.
7. Re-run `review_status.py` to refresh `INDEX.md`.
8. List the files needing re-upload to Foundry, and **ask before pushing** (Hard Rule 5).

If a reviewer set `reassign_to`, the fix is usually in the **team routing table** in
`README.md`, or in the sibling-agent hand-off guidance inside the relevant
`_START_HERE.md` — not in the answer content. Repeated reassignments to the same target
are the strongest signal the routing rules need work.

**Pre-go-live transcripts are not feedback.** Anything before `2026-08-19 19:42:29 UTC`
(see *Constants*) is internal testing. Mark it `review_status: excluded` — **not**
`reviewed`, which would inflate the reviewed percentage with work nobody did — with
`fix_target: none`, `kb_action: none`, `action_status: wontfix`, and a `notes` line citing
the cutoff. An exclusion still needs a `reviewer`, because it is a judgement. 34 of the
first 41 transcripts fall before go-live; only 7 are in scope, all `team` or `identity`.
Do not re-litigate the cutoff: it was settled against PR #1206's merge time, and the
commit linked from that PR (`a3be96ca`) is only a merge-from-main dated Aug 11.

**No shared PAT — by decision.** `contributors.json` drift is checked locally, using each
member's own `gh` credentials, not in CI. `GITHUB_TOKEN` cannot read org team membership, and
storing a PAT as a repo secret would be reachable by any write-access contributor's PR — a
same-repo-branch PR receives repo secrets, unlike a fork PR. So the check runs in
`scripts/start_review_session.sh` instead. Do not add a shared token for this. If drift
automation is ever wanted, use a `schedule`-triggered workflow: it always runs the
default-branch version, so a PR cannot alter what executes.

**Pulling new transcripts:** `python3 scripts/fetch_transcripts.py`. It never overwrites an
existing file, so review edits are safe. It also drops canned starting-prompt exchanges
(`chatExperience.sampleQuestions`, hardcoded in the script) — re-check that list if the
agents' chat experience is reconfigured, or the filter will silently stop working.

---

## Keeping the ticket catalog current

`Knowledge-Shared/Conf-OneTylerTickets.md` answers every "which ticket do I file" question
for every agent. It is reconciled from **three** upstream sources — all of them, every time,
because each covers something the others do not:

| Source | Covers | Precedence | How to fetch |
|---|---|---|---|
| Confluence `386600308` | Only the most common requests, but with pointed field-by-field instructions | **Wins on HOW to fill in a form** | Confluence MCP tools (`getConfluencePage`) |
| JSM portal `3168` | **Every** request type, 6 groups, each form's own help text | **Wins on WHICH forms exist** | **Browser required** — authenticated SPA, `curl` will not work. Use Claude in Chrome |
| JSM portal `3185` | All feature requests / enhancement ideas | Sole authority for feature requests | Browser |

Intervals and per-source notes live in `scripts/sources.json`;
`python3 scripts/check_freshness.py` reports what is overdue.

**Procedure:**

1. Fetch Confluence `386600308` and diff it against the curated sections.
2. Browse JSM `3168`: for each group (`3328`, `3333`, `3329`, `3332`, `3330`, `3331`) scrape
   the group page for `create/<id>` links, then open each form and read its top-of-form help
   text. Extract with `document.body.innerText`, slicing after the portal boilerplate —
   `main` returns the sidebar, not the form. Avoid returning raw `href` strings; the
   safety filter blocks them. Use `new URL(a.href).pathname`.
3. Check JSM `3185` for changes to the feature-request route.
4. Reconcile. **Record deprecated and superseded forms rather than deleting them** — users
   still find them, and the redirect target is the useful part. Note dead links too.
5. Where the sources conflict on *which form exists*, trust the portal; on *how to fill it
   in*, trust Confluence. Flag Confluence errors for the page owner instead of silently
   propagating them.
6. `python3 scripts/check_freshness.py --mark <id>` for each source, and commit.
7. **Upload to every collection in `upload_targets`** (see below), then verify retrieval.

---

## Creating a new corpus

Every `Knowledge-<Domain>/` folder gets **both** an `_START_HERE.md` routing guide and a
`FAQ-<Domain>.md`, from the first commit — even before any content exists. Copy
`templates/_START_HERE.md` and `templates/FAQ-Domain.md` and fill in the `{{PLACEHOLDERS}}`.

The FAQ exists from day one on purpose: without it, the first unsourced answer gets wedged
into a derived file and the next reconciliation silently deletes it.

A scaffolded corpus has **no agent and no Foundry collection**. Until it graduates, its
domain's questions are still answered from wherever that content lives today (usually
`Knowledge-BP-General/`). The graduation sequence is in each scaffold's *Becoming a real
corpus* section — the order matters, because moving content out of a deployed collection
before the new one exists deletes it from a live agent.

Currently scaffolded, awaiting an agent: **`Knowledge-StatusPageAndSLA/`** — Status Pages and
SLAs share one corpus and will share one agent. As of 2026-08-23 the upstream Blueprint
section is seven stub pages, so there is nothing to distil.
`Knowledge-AlignedReleases/` graduated on 2026-08-23 — it has an agent and a collection.

**Readiness is checked, not guessed.** `python3 scripts/check_freshness.py` scans registered
upstream sources and reports `⏳ not ready` or `✅ READY` against thresholds in
`scripts/sources.json` (no stub markers left, and enough substantive lines). Only build the
corpus and agent when it says READY. A source path that doesn't exist on your machine reports
"not available here" rather than failing.

---

## Shared corpus — one file, several collections

`Knowledge-Shared/` deliberately breaks the one-folder-per-agent rule: its files go to
**all** writable collections, so any agent can answer directly instead of handing off. In a
direct (non-team) conversation there is nobody to hand off to, and the failure mode is an
invented ticket URL.

`scripts/sources.json` → `upload_targets` is the authoritative list. Today:
`Knowledge-Shared/Conf-OneTylerTickets.md` → `OT-OpsCenter`, `OT-BPD`, `OT-SAC`,
`OT-AlignedReleases`, `TCP-KB-Identity` — **all five**.

A change to a shared file that is not uploaded to *every* target leaves the copies drifting.
Check all of them with the drift script before assuming you are done.

---

## Editing knowledge files

Full conventions are in `README.md`. The essentials:

- `.md` only; filename is `<Source>-<Topic>.md` (`Conf-`, `Docusaurus-`, `Training-`,
  `GitHub-`, `Misc-`).
- **`FAQ-<Domain>.md` is the exception**: one per agent corpus, authored here with no upstream
  source. It is the home of record for answers that exist nowhere else — verbal SME guidance,
  observed behaviour, corrections an upstream owner has not yet made. Put such content
  **there, not in a `Docusaurus-` or `Conf-` file**, because those are re-derived from their
  sources and the next reconciliation would silently delete it. Every entry carries
  `Source` / `Added` / `Confidence` / `Promote when`. Never add an unconfirmed claim: the
  agent will state it as fact.
- Optimize for **retrieval**, not source fidelity: clean markdown, a decision/lookup table
  near the top, self-contained sections (RAG chunks independently of headings), repeated
  explicit "Use when:" / "Prerequisites:" / "Fields:" patterns, and URLs preserved verbatim.
- Add a **"Notes for the chatbot"** section for routing nuances and traps.
- **A behavioural rule must be CO-LOCATED with the data it governs, not only stated once.**
  Retrievers chunk independently of headings, so a rule in a "Notes for the chatbot" section at
  the end of a long file is in a different chunk from the entry it is meant to modify — and the
  agent answering a specific question retrieves the entry, not the note. State the rule beside
  the data as well, and say in-file that the repetition is deliberate so nobody tidies it away.

  Measured 2026-08-27: the rule "give the Confluence ticket page, not the raw JSM form URL" was
  added to `Conf-OneTylerTickets.md`'s notes at line 463 of a 777-line file. Retrieval probes
  confirmed the rule was live in all five collections — and the agent still handed out only the
  bare form URL, because the chunk it retrieved was the ticket entry at line 124. **Content
  being retrievable is not the same as content being applied.**

  The same logic applies to contradictions: if an entry elsewhere shows the thing the rule
  forbids, the agent will follow the concrete example over the general instruction. Fix the
  example, not just the rule.
- **Update `_START_HERE.md`** in that folder whenever you add, rename, or remove a file. A
  stale start page actively misleads the agent. Update `README.md` too if team-level routing
  changes.
- Never put a credential in a knowledge file. If the source has one, replace it with a
  pointer to the authoritative internal page (see
  `Knowledge-OpsCenter/Conf-GatewayOperationalTesting.md` for the pattern).

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| 403 with a valid key | Missing `User-Agent` header, or the key belongs to another tenant |
| 401 | Key rotated or revoked — ask for a fresh one |
| HTML instead of JSON | Redirected to login; auth failed |
| 429 | Rate limited. General ~60 req/min; chat/stream ~20 req/min per user. Respect `Retry-After` |
| Exactly 200 results | Result cap hit — narrow the date range |
| `GET /api/agents/{id}` → 404 | Wrong route for config; use `GET /api/configurable-agents/{id}`. The `/api/agents` prefix only serves streaming/generation |
| Agent config shows fewer KB files than the collection | The config's file list is a **stale cache**. The collection endpoint is authoritative |
| File `ingested` but agent says it can't find content | Probe retrieval. Re-sync won't fix an empty index — delete and re-upload |
| Files still `ingesting` after a few minutes | Normal up to ~6 min; retrieval often live already. Assert on retrieved *content*. Past ~30 min, investigate |
| `POST /sync` → "Content-Type must be application/json" | Add `-H "Content-Type: application/json"`; not a transient error, retrying won't help |
| Uploaded file shows `application/octet-stream` | Missing `;type=text/markdown` on the `-F` argument |
| `POST /sync` → 500 | Transient Bedrock job conflict; retry every ~45s |
| zsh poll loop breaks | Don't name a shell variable `status` — it's a read-only builtin |
| Prompt text comes back altered after a config PUT | Foundry HTML-escapes `>` and strips `<tag>`-shaped text. Never put `<` or `>` in a prompt; diff live-vs-mirror on **content**, since the length can be unchanged |

---

## Index hygiene

When you change the corpus, update in the same PR:

1. The folder's `_START_HERE.md` (file catalog + routing table).
2. `README.md`, if team-level routing or the corpus list changed.
3. This file, if an ID, endpoint, or procedure changed.
4. The re-upload list in your response.
