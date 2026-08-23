# START HERE — Routing Guide for the {{NAME}} Knowledge Corpus

This file is **the chatbot's first read** for the {{NAME}} domain. It is a **routing guide**,
not a tutorial: its job is to pick the right file before answering, and to know what this
corpus does not cover.

Domain: {{DOMAIN — one sentence}}
Audience: {{AUDIENCE}}

> ⚠️ **This corpus is a scaffold — it has no substantive content yet, and no Foundry agent or
> collection.** It exists so that {{NAME}} content has an obvious home the moment it is
> written, instead of accumulating in `Knowledge-BP-General/`. Until an agent exists,
> {{NAME}} questions are answered by the **General Blueprint Docs Agent** from the files listed
> under *Where this content lives today*.

---

## File catalog at a glance

| File | One-liner — what's in it |
|---|---|
| `FAQ-{{SLUG}}.md` | **Authored answers with no upstream source** — verbal SME guidance, observed behaviour, corrections upstream owners have not yet made. Empty of entries today. |

_No distilled source files yet._ When the first one lands, add a row here and follow the
`<Source>-<Topic>.md` naming convention (`Conf-`, `Docusaurus-`, `Training-`, `GitHub-`,
`Misc-`).

---

## Where this content lives today

{{Where this content lives today, or 'Nowhere yet.'}}

**Do not move that content here yet.** It is currently deployed to the `OT-BPD` collection
and retrieved by the General Blueprint Docs Agent. Moving it before this corpus has its own
agent and collection would delete it from a live agent with nowhere for it to go. The
migration sequence is in *Becoming a real corpus* below.

---

## Scope — what belongs here

{{- bullet list of what belongs here}}

## What does NOT belong here

{{- bullet list of what does NOT, each with the corpus that owns it}}

---

## Cross-domain pointers

{{- cross-domain pointers}}
- **Any ticket question** → `Knowledge-Shared/Conf-OneTylerTickets.md`, the authoritative
  catalog for every domain.

---

## Becoming a real corpus

This scaffold graduates in this order. Doing it out of order loses content from a live agent.

1. **Create the Foundry agent** and its KB collection.
2. **Record the IDs** in the *Constants* table in `CLAUDE.md` and the team-composition table
   in `README.md`.
3. **Add the routing rule** for this domain to the team `system_prompt`
   (`team-config/team-routing-prompt.md`), push it to Foundry, and verify — otherwise the
   team router will keep sending these questions to General Blueprint Docs.
4. **Move the content** listed above out of `Knowledge-BP-General/` into this folder,
   splitting files where a single upstream file covers more than one of the new domains.
5. **Upload** the moved files to the new collection, **then** delete them from `OT-BPD`, and
   re-upload the BP-General start page with its catalog rows removed.
6. **Update this file** — replace the scaffold warning, fill in the file catalog and add a
   *Common query → file routing* table.

---

## Operating principles for the chatbot

1. While this corpus is empty, **do not treat its existence as evidence** that a question has
   been considered. Fall back to the files under *Where this content lives today*.
2. Never answer a {{NAME}} question from model priors. If neither this corpus nor the
   BP-General files cover it, say so.
3. Entries in `FAQ-{{SLUG}}.md` have **no upstream document** — if challenged, say the answer
   comes from internal Tyler subject-matter guidance rather than published documentation.

---

## Index hygiene

Update this file whenever a file is added, renamed or removed from this folder, and when this
corpus graduates. Also update `README.md` if team-level routing changes. A stale start page
actively misleads the agent.
