# FAQ harvesting — Teams → Coda review → `FAQ-<Domain>.md`

Recurring questions get answered in Teams by the people who own the answer, and then the answer
is lost. This loop catches them and lands the confirmed ones in the corpus, with a human
approval gate in Coda so nothing unreviewed reaches Foundry.

## Why it is half agent, half script

Reading a Teams **channel** requires the Microsoft 365 MCP tool `teams_list_channel_messages`.
That tool is available to Claude inside a session; it is not available to a plain Python
process, because there are no Graph app credentials on this machine. Verified working
2026-09-08 against both Aligned Releases channels, including threaded replies and pagination.

So the split is:

| Step | Who | How |
|---|---|---|
| 1. Read the channels | **agent** | `teams_list_channel_messages`, top-level then `parentMessageId` for each Q&A thread |
| 2. Extract candidates, dedupe against the FAQ, classify conflicts | **agent** | judgement — this is the part that cannot be a script |
| 3. Push to the Coda review table | script | `coda_faq_review.py push` |
| 4. Approve / reject | **human** | tick **Ready for Processing** in Coda; reject by deleting the row |
| 5. Pull the ticked rows | script | `coda_faq_review.py pull` |
| 6. Index into `FAQ-<Domain>.md` | **agent** | the FAQ entry format, in the right place in the file |
| 7. Delete the row, record the key | script | `coda_faq_review.py delete` |

Steps 3, 5 and 7 are deterministic on purpose: they are the ones that must not half-happen.

## Sources

### Aligned Releases → `Knowledge-AlignedReleases/FAQ-AlignedReleases.md`

| Channel | teamId | channelId |
|---|---|---|
| Cloud Living – FACC / General | `969b039c-b765-48ea-a12e-973d42c45c17` | `19:S23ooVbxKDBsZ_X3OhvHtDlWNLSDG8G68CUaclunpPk1@thread.tacv2` |
| Aligned Releases | `20442058-b54b-4742-a4ec-49c7f40764f8` | `19:1d8562afa885458ea35bf410ba7d50d9@thread.tacv2` |

Coda review page: **FAQs - Aligned Releases**, `canvas-xQGl2GpyJF`.

### Status Pages / SLAs → `Knowledge-StatusPageAndSLA/FAQ-StatusPageAndSLA.md`

| Channel | teamId | channelId |
|---|---|---|
| SPARC – Working Group / General | `97bf1b86-985d-4f26-ae13-85361c039c7d` | `19:PK1E_uJ3uwfVuu_-00XH83InYFnFFUiq3t9xU4NC5xQ1@thread.tacv2` |

Coda review page: **FAQs - Status Pages**, `canvas-fDCK9ni2hA`.

> **This domain has nowhere to deploy yet.** `Knowledge-StatusPageAndSLA/` is a scaffolded
> corpus with no Foundry agent and no collection. Harvesting and Coda review work; step 6 lands
> the entry in a file that nothing retrieves until the agent is stood up. That is fine — just do
> not report an entry as live.

Tenant for all channels: `7cc5f0f9-ee5b-4106-a62d-1b9f7be46118`.

## Running it

```bash
export CODA_API_TOKEN=...   # REST token from ~/.../Repo/claude/coda-details.md
python3 scripts/coda_faq_review.py status --domain AlignedReleases
```

Then ask Claude to harvest. The agent writes a batch to
`team-config/faq-harvest/candidates-<domain>-<date>.json`, and:

```bash
python3 scripts/coda_faq_review.py push --domain AlignedReleases --dry-run \
    team-config/faq-harvest/candidates-alignedreleases-2026-09-08.json
python3 scripts/coda_faq_review.py push --domain AlignedReleases \
    team-config/faq-harvest/candidates-alignedreleases-2026-09-08.json
```

After review:

```bash
python3 scripts/coda_faq_review.py pull   --domain AlignedReleases > /tmp/ready.json
# agent indexes them into FAQ-AlignedReleases.md, updates _START_HERE.md
python3 scripts/coda_faq_review.py delete --domain AlignedReleases --keys ar-123,ar-456
```

`pull` prints the exact `delete` command for the rows it returned, so the two halves cannot
drift apart. `delete` records each key in the ledger, which is what stops the next harvest
re-proposing it — the table holds only outstanding items and therefore cannot be the memory.

**Rejection has no state of its own: delete the row in Coda.** The next `push` sees that a key
it previously sent has gone and records it as rejected.

## Rules the harvest step follows

These come from `FAQ-AlignedReleases.md`'s own "What belongs here" section and from
`CLAUDE.md`. They are the reason this is not just a scraper.

1. **Only what exists nowhere else.** If the answer is already in Blueprint or a Confluence
   page, it belongs in that source's file — or nowhere — not in the FAQ. `Docusaurus-` and
   `Conf-` files are re-derived from upstream and would silently lose a hand-added entry.
2. **Never add an unconfirmed claim as an answer.** Every entry carries Source / Added /
   Confidence / Promote when. "Nobody has decided yet" is a legitimate entry and is kept
   deliberately — without it the agent invents a process. A guess is not.
3. **Conflicts do not get applied.** A candidate that contradicts a live entry goes to the
   review table with the existing question named in `Conflicts with` and a `Reviewer notes`
   explanation of how the two might reconcile. Never quietly overwrite.

   **A provisional candidate is flagged in `Reviewer notes`**, prefixed
   `PROVISIONAL — confirm before publishing.` The table has no Confidence column, so that
   prefix is the half of confidence a reviewer has to act on.
4. **Ticket and permission questions are not FAQ entries.** Per the team README's routing rule
   0, "which form do I file / how do I request access" is answered from
   `Knowledge-Shared/Conf-OneTylerTickets.md` — one catalog, so copies cannot drift. Harvest
   them, flag the routing, let the reviewer decide.
5. **Bug reports are not FAQs.** "Both tabs are highlighted when I navigate" is a defect, not a
   question with an answer. Drop it.
6. **Attribute to a person and a date.** "Someone in the channel said" is not a source.
7. **No customer conversation data, no credentials, ever** — see `.gitignore` and
   `Knowledge-*/`'s deployment surface.

## Landing the entry

Step 6 is a normal corpus change, so the normal rules apply:

- Update the corpus `_START_HERE.md` in the same change if the file's coverage shifts.
- Nothing reaches Foundry until it is merged to `main`. Run `scripts/preflight_upload.py` on
  the changed file, then `scripts/check_foundry_drift.py` after the merge.
- Back up the Foundry object before any write, into `team-config/backups/`.

## Cadence

Currently **on request** — ask Claude to run a harvest. The channels are low-volume: the
Aligned Releases channel produced 26 top-level messages between 2026-05-11 and 2026-09-03, so
a sweep every few weeks comfortably keeps up, and a weekly one would usually find nothing.

If this should run unattended, it has to be a scheduled *Claude* job rather than a cron entry,
because step 1 needs the MCP tool. Nothing is scheduled today.
