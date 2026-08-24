# CLAUDE.md

Operating instructions for Claude Code instances working in this repository.

Read this fully before touching the Foundry API. It is self-contained — it does **not**
depend on any locally-installed skill. (If `~/.claude/skills/foundry-transcripts/` or
`manage-kb-collection/` happen to exist on your machine, they cover the same ground in more
depth, but never assume they are present.)

---

## 🚫 HARD RULES — read these first

1. **`Knowledge-TylerIdentity/` — commit to git YES, upload to Foundry NO.** These are two
   separate things and only the second is restricted:

   | Action | Allowed? |
   |---|---|
   | Author, edit and **commit** files in `Knowledge-TylerIdentity/` | ✅ **Yes — treat it like any other corpus.** It must be pushed to the GitHub repo along with everything else |
   | Upload / delete / sync against the **`TCP-KB-Identity` Foundry collection** | ❌ **No** — until the repo owner (Vijay Venkataraman) says otherwise |
   | Pull *from* `TCP-KB-Identity` (download, re-pull a snapshot) | ✅ Yes |

   The reason is narrow: that Foundry collection is maintained by another owner and its
   on-disk structure differs from this repo's, so a switchover needs their agreement. It is
   expected to be resolved soon. Nothing about that restricts version control — never
   gitignore this folder, never skip it in a commit, and never describe it as "read-only".
   The other three collections may be uploaded to normally.
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
6. **NEVER broaden access without asking.** The approved grants are exactly two teams:
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
7. **ALWAYS back up before changing anything in Foundry, and commit the backup.** Backups
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

## Constants — agent, team, and collection IDs

Verified live 2026-08-21. Everything lives in tenant **Tyler Technologies**, project
*OneTyler - Cloud Living Agents - v1.0.0*.

| Sub-agent | Agent ID | KB collection | Local folder | Foundry upload? |
|---|---|---|---|---|
| Ops Center | `5b3efdff-921a-4131-be81-b7a4be427d9b` | `OT-OpsCenter` | `Knowledge-OpsCenter/` | ✅ yes |
| General Blueprint Docs Agent | `bd1c5d91-8234-486e-9f5a-2f1b7a947426` | `OT-BPD` | `Knowledge-BP-General/` | ✅ yes |
| Support Access Center | `55444576-1fa3-4d12-a738-6ba83b17e6a7` | `OT-SAC` | `Knowledge-SupportAccessCenter/` | ✅ yes |
| Aligned Releases | `b0544224-b120-469a-8f39-c4a7b14c17c0` | `OT-AlignedReleases` | `Knowledge-AlignedReleases/` | ✅ yes |
| Tyler Identity Assistant | `3f5e586f-0d0f-4638-9839-bebe45a6cb47` | `TCP-KB-Identity` | `Knowledge-TylerIdentity/` | ❌ **not yet — Hard Rule 1.** Git commits are fine and required |

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

If unset, ask the user for it. They keep it in a gitignored env file outside this repo
(`foundry-secrets.env` in the parent project) which can be sourced:

```bash
source ../foundry-secrets.env    # path depends on checkout location; ask if unsure
```

Never write the key into a file in this repo, a script, or a command that gets committed.

Keys are created in Foundry under **Dev → API Keys**, are **tenant-scoped** (a key from one
tenant 403s against another), and are limited to 10 per user. If requests start returning
401, the key was rotated or revoked — ask for a fresh one.

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

This currently applies to `Knowledge-TylerIdentity/Docusaurus-Identity.md`, which was
renamed locally from `tyler-identity-knowledge-base.md` — the name still present in
`TCP-KB-Identity`. **Do not reconcile that one**; see Hard Rule 1.

Note the asymmetry: re-uploading the *same* name is a clean in-place replace (see "The
model you must internalize"), so ordinary content updates need no deletion. Only renames do.

---

## Acting on transcript reviews

`transcripts/` holds preserved conversation history, one markdown file per conversation,
with review fields in the frontmatter. Humans review; you act on what they wrote. Full
workflow and field definitions: `transcripts/README.md`.

Humans review through a local web UI (`python3 scripts/review_server.py`, loopback-only on
port 7777) or by editing the markdown directly. Either way the output is the same files.

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

**Only act on files with `review_status: reviewed`.** A `pending` file has not been looked
at by a human; do not infer corpus changes from it unprompted.

The `reviewer` field is constrained to the `github` values in `contributors.json`. Never
invent a reviewer name, and never set `review_status: reviewed` yourself — that field
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
`Knowledge-Shared/Conf-OneTylerTickets.md` → `OT-OpsCenter`, `OT-BPD`, `OT-SAC`.
**`TCP-KB-Identity` is excluded** — Hard Rule 1.

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
