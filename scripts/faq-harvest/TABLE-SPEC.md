# Review table spec

`scripts/coda_faq_review.py` can read rows, upsert rows and delete rows. It **cannot create
the table**, and it cannot add or remove columns — the Coda REST API has no endpoint for
either. Columns are a UI job, once.

Verified 2026-09-08: a markdown table passed as page `canvasContent` renders as *static text*,
not a grid. A probe page was created with a three-column markdown table and no new table
appeared under `GET /docs/{docId}/tables`. So there is no API trick — import the CSV.

## The quick route: import the CSV

`team-config/faq-harvest/FAQ Review Queue (Aligned Releases).csv` carries the header row and
one disposable sample row, so Coda infers the whole schema.
`team-config/faq-harvest/README-import.md` says which page each CSV goes to.

## Where

| Domain | Coda page | Page id | Table |
|---|---|---|---|
| Aligned Releases | **FAQs - Aligned Releases** | `canvas-xQGl2GpyJF` | rebuilt 2026-09-09 for the 8-column layout — id in `coda_faq_review.py` |
| Status Pages / SLAs | **FAQs - Status Pages** | `canvas-fDCK9ni2hA` | not built |

Both pages are in the **OneTyler Initiatives Trackers** doc, `KV_6fSnfBc` —
<https://docs.superhuman.com/d/_dKV_6fSnfBc>.

## Columns

Eight, in the order a reviewer reads them. **Names must match exactly** — the script addresses
columns by name (`useColumnNames=true`), so a renamed column silently stops being written.

| # | Column | Type | Who fills it | Notes |
|---|---|---|---|---|
| 1 | `Date` | date | harvester | When the candidate was harvested. Coda coerces `2026-09-09` to `2026-09-09T00:00:00.000-05:00`, so never string-compare it. |
| 2 | `Key` | Text | harvester | Stable id, `ar-<teams-message-id>`. The upsert key, so a repeat harvest updates rather than duplicates. Do not edit by hand. |
| 3 | `Question` | Text | harvester | Phrased the way a user would ask it. |
| 4 | `Answer` | Text | harvester | Proposed answer in the FAQ's markdown style. **Edit this in place** — the loop indexes the cell as it reads when the box is ticked, not the original harvest. |
| 5 | `Source` | Text | harvester | Who said it and when — a person and a date, per FAQ policy. |
| 6 | `Source link` | link | harvester | Permalink to the Teams message. Verified to preserve `?groupId=…&tenantId=…` intact. |
| 7 | `Notes` | Text | both | Everything the reviewer needs flagged, assembled by `build_notes()`. Empty when there is nothing to say — 11 of the first 21 candidates had an empty cell. |
| 8 | `Ready for Processing` | **checkbox** | **reviewer** | **The only gate.** See below. |

### What `Notes` carries

Two things lost their own column but must still reach a reviewer, so they are prefixed onto
`Notes` in this order:

- **`CONFLICTS WITH the live entry “…”.`** The candidate contradicts or refines an entry the
  agent is already answering from. This is the flag that stops a conflict being applied
  silently, so it must never be dropped — it is the reason `conflicts_with` survives at all.
- **`PROVISIONAL — confirm before publishing.`** The source was not authoritative. FAQ policy
  is that an unconfirmed claim must not be published as fact, because the agent will state it
  as one.

Then the harvester's own note, if any — a routing question, a reconciliation suggestion, a
recommendation to reject.

## What is deliberately NOT a column

The table is a **review surface, not the record.** It carries only what a human reads or
edits. Everything below is tracked in the candidates JSON and written into the FAQ entry at
indexing time. Reviewers were being asked to read a column per FAQ field, which made the
thing harder to read for no decision gained.

| Not a column | Why | Where it lives |
|---|---|---|
| `Status` | Redundant once the checkbox is the gate. A row does not survive processing, so an Approved/Rejected value on it would never be read again. | the ledger, which outlives the row |
| `Type` | `New` / `Conflict` / `Refinement` / `Duplicate` was review triage; `Notes` says it in plain words. | candidates JSON |
| `Confidence` | Required by the FAQ **entry** format, but needs no reviewer input. | JSON; the actionable half is the `PROVISIONAL` prefix |
| `Promote when` | The entry's *exit condition* — which upstream doc should eventually carry the answer, so the entry can be retired rather than accumulating forever. Useful in the file, nothing to decide. | candidates JSON |
| `Conflicts with` | Still essential, but as a sentence rather than a column. | the `CONFLICTS WITH` prefix on `Notes` |

## How the reviewer uses it

**Tick `Ready for Processing`** and nothing else is required. Edit `Answer` first if it needs
changing.

**To reject a candidate, just delete the row.** There is no Rejected state. The next `push`
notices that a key it previously sent is gone from the table and not in the ledger, records it
as `rejected (row removed in Coda)`, and never proposes it again.

**To defer**, leave the box unticked. Unticked rows are invisible to `pull` and are not
re-proposed by a later harvest, because they are already present.

`delete` refuses to remove a row that is not ticked unless `--force` is passed — deleting an
unreviewed row loses the candidate for good, since the ledger then suppresses it.

## Why the ledger exists

`team-config/faq-harvest/ledger-<domain>.json`, committed on purpose:

- `pushed` — every key ever sent to the table. Needed to tell "you rejected this" apart from
  "this was never proposed".
- `decided` — what happened to it (`indexed`, `rejected (row removed in Coda)`, `discarded`).
- `table_id` — which table `pushed` refers to. **Rebuilding the table is the normal way a
  column change happens**, since the Coda API can neither rename nor delete a column. Without
  this field, pointing the script at a fresh empty table would make every previously-pushed
  key look deleted and be recorded as a rejection wholesale. `reconcile` checks it first and
  treats a mismatch as a rebuild.

The table only ever holds outstanding items, which is the point — so the table cannot itself
remember that something was already handled. Without this file every harvest re-proposes
everything already dealt with.

## A trap worth knowing

Coda writes are **asynchronous**. A POST or DELETE returns a `requestId` and the change is not
visible for a few seconds — a probe page took about 20 seconds to disappear.
`coda_faq_review.py` polls `/mutationStatus/{requestId}` to completion on every mutation, so
"delete the processed row" either finishes or reports that it did not. Do not add a code path
that fires a write and moves on.
