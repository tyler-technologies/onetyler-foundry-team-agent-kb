# FAQ — Ops Center

Source: **authored in this repo — no upstream document.** Every other file in this folder is
distilled from something external (Confluence, Blueprint, training, GitHub) and is
re-derived when that source changes. This file is the opposite: it is the **home of record**
for answers that exist nowhere else.

Domain: Ops Center
Audience: Tyler product, deployment, implementation and operational staff.

**Companion:** `_START_HERE.md` for routing across this corpus. For "which ticket do I file",
use `Knowledge-Shared/Conf-OneTylerTickets.md` — not this file.

---

## What belongs here

- Answers given verbally by a subject-matter expert that are not written down anywhere.
- Behaviour learned by observation or testing that no document describes.
- Corrections to an upstream source that the source owner has not yet fixed.
- Disambiguation and phrasing guidance the agent needs but no doc states.
- Recurring questions from real transcripts whose answer had to be assembled from scratch.

## What does NOT belong here

- Anything already in an upstream source — put it in the file for that source, so it is
  re-derived when the source changes.
- Ticket forms and permissions — `Knowledge-Shared/Conf-OneTylerTickets.md`.
- Glossary definitions — `Docusaurus-Terminology.md` is the canonical glossary.
- Speculation. If nobody has confirmed it, do not write it here; the agent will state it as
  fact.

## Entry format

Copy this block. Every field earns its place: without **Source** and **Added** a future
reader cannot judge whether the answer is still true, and without **Promote when** entries
silently become permanent shadow documentation.

```markdown
### Q: <the question, phrased the way a user would ask it>

**A:** <the answer>

- **Source:** <who said it / where it was observed — name a person or a verifiable check>
- **Added:** <YYYY-MM-DD> by <github username>
- **Confidence:** confirmed by owner | provisional — needs confirmation
- **Promote when:** <the upstream doc that should eventually carry this, if any>
```

Keep each entry self-contained — retrievers chunk independently of headings, so an entry
that only makes sense after reading the one above it will retrieve badly.

---

## Entries

### Q: Someone said "client" — do they mean a customer or an identity client?

**A:** It depends entirely on the surrounding words, and getting it wrong sends the question
to the wrong place. In an Ops Center / operational context, "client" almost always means the
**customer or organization**: licensing, contracts, onboarding, org keys, CRM identifiers,
"a client's Admin Center", "client administrator". Answer from the Ops Center corpus.

If the word appears near **authentication vocabulary** — "identity client", OAuth, OIDC,
scopes, tokens, client credentials or CCF, `client_id` / `client_secret`, redirect URI,
PKCE, `application_type` — it means a **registered application**, and the question belongs to
Tyler Identity.

A third sense appears occasionally: "the *product* client", as in "what's available via the
Ops Center client", meaning the client application or SDK.

If the sense is genuinely unclear, **ask one clarifying question** rather than guessing.

- **Source:** Vijay Venkataraman, 2026-08-23, in response to observed routing failures. The
  third sense was found in transcript `2026-08-10--d6f2ea37` ("What's available via the Ops
  Center client?").
- **Added:** 2026-08-23 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** `Docusaurus-Terminology.md` already warns "avoid 'client' in technical
  contexts", but does not give this routing rule. If the glossary is expanded to cover it,
  move this there.

### Q: Is the team still called CorpDev?

**A:** No — the team is **OneTyler**. "CorpDev" is the former name, but it is still used
verbatim in live systems, so treat the two as the same team: the JSM portals are titled
"CorpDev Support" and "CorpDev Feature Requests", some ticket forms still say "CorpDev
maintained applications", the Teams space is "CorpDev Collaboration", and GitHub and
infrastructure identifiers keep the `corpdev-` prefix (`corpdev-tf-docs`,
`corpdev_db_admin`, the `orgs/CorpDev/` Harness path). Answer as though the user said
OneTyler, but quote system names exactly as they appear in that system.

- **Source:** Vijay Venkataraman, 2026-08-23.
- **Added:** 2026-08-23 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** also recorded in `Docusaurus-Terminology.md` under *OneTyler (formerly
  CorpDev)*. Keep here only while the rename is still in flight.

---

## Notes for the chatbot

- Entries here have **no upstream document**. State them plainly, but if a user pushes back,
  say the answer comes from internal Tyler subject-matter guidance rather than published
  documentation.
- An entry marked **provisional** has not been confirmed by an owner. Hedge accordingly.
- If an entry contradicts a `Docusaurus-` or `Conf-` file in this folder, the upstream file
  usually wins — **unless** the entry exists precisely because it corrects that source, in
  which case it says so in **Source**.
