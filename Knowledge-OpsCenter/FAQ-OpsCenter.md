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

### Q: Is there a way to see all the Admin Center instances I have access to?

**A:** **No — there is currently no single place** that lists every Admin Center instance a
user has access to.

Once a product has adopted **Support Access Center**, Tyler users will be able to see all of
their access requests — to Admin Center *and* to products — on the **SAC Dashboard**. That is
the closest thing to a consolidated view, and it only covers products that have adopted SAC.

Do not offer a workaround that implies a consolidated list exists.

- **Source:** Vijay Venkataraman, reviewing transcript `team/2026-08-21--e7510651`, where the
  team routed this to Tyler Identity and the answer was wrong. Diagnosis was `search-empty` —
  nothing in any corpus answered it.
- **Added:** 2026-08-24 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** if Blueprint documents a consolidated access view, move it there.

### Q: I need to be an Org Admin / I need access to a customer's Admin Center — how do I get it?

**A:** **There are two different paths, and the right one depends on how often you need
access.** Present both; do not send someone down the manager's-guide route when a single
ticket would do.

**Occasional access to one customer's Admin Center** — use the **Client Admin Center access
request** ticket:
<https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3333/create/4165>

This is the normal path, and it is what most people asking this question want. Being granted
it makes you an Org Admin for that one organization. Requirements: the org must already exist
in Ops Center in that environment, and you must not already have access. Allow up to five
minutes after approval.

**Frequent access across many customers' Admin Centers** — follow the **Manager's Guide**:
*Tyler Cloud Platform (TCP) | Org Admin promotions (Admin Center access) - a Manager's guide*
(`/wiki/spaces/TTI/pages/386629479/`)

This exists so a team that routinely needs Admin Center access does not have to raise a
separate ticket per organization. It is a manager-driven workflow — the team's manager
delegates special permissions — and there is no single ticket URL for it.

Neither path uses the generic "Ops Center additional permissions" form (`4133`).

**Why this entry exists:** asked as "need to add myself as an org admin for product add", the
team agent returned only the Manager's Guide. That answer is not wrong, but for a one-off
request it sends the user into a manager-approval process when ticket `4165` would have
settled it. The two routes are catalogued separately in
`Knowledge-Shared/Conf-OneTylerTickets.md`; what was missing everywhere was the rule for
choosing between them.

- **Source:** Vijay Venkataraman, reviewing transcript `team/2026-08-24--53d51e27`. Ticket
  numbers and prerequisites cross-checked against `Knowledge-Shared/Conf-OneTylerTickets.md`
  (*Client Admin Center access request*, and *Add an Org Admin, or self-promote as Org
  Admin*).
- **Added:** 2026-08-25 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** the Confluence ticket page or the Manager's Guide itself states the
  occasional-vs-frequent rule. The form details belong in
  `Knowledge-Shared/Conf-OneTylerTickets.md`, which is re-derived from upstream — only the
  choice-between-them rule lives here.

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
