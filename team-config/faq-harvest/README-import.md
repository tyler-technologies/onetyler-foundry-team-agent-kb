# Importing the review-table CSVs

One CSV per domain. Each creates that domain's FAQ review queue table.

| CSV | Import to Coda page | Page id | Feeds |
|---|---|---|---|
| `FAQ Review Queue (Aligned Releases).csv` | **FAQs - Aligned Releases** | `canvas-xQGl2GpyJF` | `Knowledge-AlignedReleases/FAQ-AlignedReleases.md` |

**Aligned Releases needs a re-import** — the CSV was regenerated on 2026-09-09 for the
simplified 8-column layout (`Date`, `Key`, `Question`, `Answer`, `Source`, `Source link`,
`Notes`, `Ready for Processing`). The Coda API cannot rename or delete a column, so a column
change means a fresh import rather than an edit. The old table `grid-4mdZMRDPAE` can be
deleted once the new one is in; no review work is lost, because no row was ever ticked.
| _(not yet generated)_ | **FAQs - Status Pages** | `canvas-fDCK9ni2hA` | `Knowledge-StatusPageAndSLA/FAQ-StatusPageAndSLA.md` |

Both pages are in the **OneTyler Initiatives Trackers** doc, `KV_6fSnfBc` —
<https://docs.superhuman.com/d/_dKV_6fSnfBc>.

The two tables are near-identical in shape, so the destination is also written into each
CSV's sample row: open the file and the `Question` cell names the target page and page id.
That is deliberate — the **filename has to stay the intended table name**, because Coda names
an imported table after the file it came from, so the page cannot be put in the filename
without corrupting the table name.

## After importing

1. ~~Delete the `SAMPLE-delete-me` row.~~ (done for Aligned Releases)
2. Nothing to configure: `Ready for Processing` imports as an unticked checkbox, which is
   exactly the wanted starting state.
3. Delete the superseded table once the new one is confirmed.
4. ~~Send back the table id.~~ (done: `grid-4mdZMRDPAE`, pinned)

Optionally rename the table to drop the `.csv` suffix Coda took from the filename. Cosmetic —
the script resolves by id.

Then confirm the script can see it:

```bash
export CODA_API_TOKEN=...   # REST token from ~/.../Repo/claude/coda-details.md
python3 scripts/coda_faq_review.py status --domain AlignedReleases --table grid-XXXX
```
