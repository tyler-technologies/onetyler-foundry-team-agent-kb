# Placeholder — Tyler Identity Assistant corpus

This folder is the landing spot for the **Tyler Identity Assistant** corpus, the fourth
sub-agent on the **OneTyler Cloud Living** Foundry team. It is **maintained separately**
and has not been contributed to this repo yet.

**This folder currently contains no knowledge content.** Do not upload it to a Foundry
knowledge base collection — there is nothing to ingest, and this file is deliberately
named `PLACEHOLDER.md` rather than `_START_HERE.md` so it cannot be mistaken for corpus
content by a retriever or by the routing convention.

## For the corpus owner joining this repo

Please follow the conventions in the repo [README](../README.md):

1. Add an **`_START_HERE.md`** routing guide — file catalog, common query → file routing
   table, disambiguation pairs, cross-domain pointers, what the corpus does *not* cover.
2. Use the **source-prefix filename convention** (`Docusaurus-`, `Conf-`, `Training-`,
   `GitHub-`, `Misc-`).
3. Delete this file once real content lands.
4. Update the repo README's team-composition table to drop the *(placeholder)* note.

## Scope this agent owns

Per the team routing table: Identity Workforce/Community, Gateway, Workforce
Direct/Managed/Delegated configuration, federation, credential templates, and login &
token flows.

Note the deliberate boundary with **Ops Center**: Ops Center owns what an operator *does
in the Ops Center UI* (including retargeting a workspace's gateway); this corpus owns how
the identity system itself is configured and how tokens and federation actually work.
Blueprint reference: https://docs.tylerdev.io/identity
