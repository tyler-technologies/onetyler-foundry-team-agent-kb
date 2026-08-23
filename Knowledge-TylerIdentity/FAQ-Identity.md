# FAQ — Tyler Identity

Source: **authored in this repo — no upstream document.** The rest of this folder is derived
from Tyler Blueprint `docs/identity/`. This file is the **home of record** for identity
answers that exist nowhere else.

Domain: Tyler Identity
Audience: Tyler product, engineering and identity-support staff.

**⚠ Not yet in Foundry — but fully version-controlled.** This file is committed to the
GitHub repo like any other knowledge file; edit and commit it freely. What it is *not* yet is
**uploaded to the `TCP-KB-Identity` Foundry collection**, because that collection is
maintained by another owner whose on-disk structure differs from this repo's, so the
switchover needs their agreement. Expected to be resolved soon. See Hard Rule 1 in
`CLAUDE.md`. Until then the live Identity agent cannot retrieve this content.

**Companion:** for "which ticket do I file", use `Knowledge-Shared/Conf-OneTylerTickets.md`.

---

## What belongs here

- Answers given verbally by a subject-matter expert that are not written down anywhere.
- Behaviour learned by observation or testing that no document describes.
- Corrections to an upstream source the owner has not yet fixed.
- Disambiguation and phrasing guidance the agent needs but no doc states.
- Recurring questions from real transcripts whose answer had to be assembled from scratch.

## What does NOT belong here

- Anything already in Blueprint `docs/identity/` — it belongs in `Docusaurus-Identity.md`,
  so it is re-derived when Blueprint changes.
- Ticket forms — `Knowledge-Shared/Conf-OneTylerTickets.md`.
- Speculation. If nobody has confirmed it, leave it out; the agent will state it as fact.

## Entry format

```markdown
### Q: <the question, phrased the way a user would ask it>

**A:** <the answer>

- **Source:** <who said it / where it was observed — name a person or a verifiable check>
- **Added:** <YYYY-MM-DD> by <github username>
- **Confidence:** confirmed by owner | provisional — needs confirmation
- **Promote when:** <the upstream doc that should eventually carry this, if any>
```

Keep entries self-contained — retrievers chunk independently of headings.

---

## Entries

### Q: Someone said "client" — do they mean an identity client or a customer?

**A:** In an identity context "client" usually means a **registered OAuth/OIDC application**,
not a company. Treat it that way when the question sits near authentication vocabulary:
"identity client", OAuth, OIDC, SAML, scopes, tokens, claims, client credentials or CCF,
`client_id` / `client_secret`, redirect URI, PKCE, `application_type`, or a login or consent
error.

If instead it appears near **licensing, contracts, onboarding, org keys, CRM identifiers,
Admin Center**, or in phrases like "a client's Admin Center" or "client administrator", the
user means a **Tyler customer / organization** and the question belongs to Ops Center.

If the sense is genuinely unclear, **ask one clarifying question** rather than guessing —
e.g. "do you mean an identity client registration, or a Tyler customer?"

- **Source:** Vijay Venkataraman, 2026-08-23, in response to observed routing failures.
- **Added:** 2026-08-23 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** if Blueprint's identity glossary adds this distinction, move it there.

### Q: Which ticket enables Support Access Center on a Workforce Managed org?

**A:** **Not `group/3329/create/4149`**, despite what the Confluence page *Ops Center Related
Tickets and Permissions* says. That URL is verified live as the **Identity SKU Change** form,
a different request. Do not send SAC-enable requests there.

Until the Confluence page is corrected, direct the user to the OneTyler portal
(https://help.center.tylertech.com/servicedesk/customer/portal/3168) → **2. TCP -
Operations**, or have them file *Request or Share Functional Information*
(`group/3333/create/4141`) to be routed.

- **Source:** verified 2026-08-23 by opening the live form at that exact URL; it renders as
  "Identity SKU Change" with a READ-ME-FIRST about the org already existing in Ops Center.
- **Added:** 2026-08-23 by vijay-tylertech
- **Confidence:** confirmed — the live form is authoritative over the wiki page
- **Promote when:** the Confluence page is fixed. Then delete this entry; the corrected
  mapping belongs in `Knowledge-Shared/Conf-OneTylerTickets.md`.

---

## Notes for the chatbot

- Entries here have **no upstream document**. State them plainly, but if challenged, say the
  answer comes from internal Tyler subject-matter guidance rather than published docs.
- An entry marked **provisional** has not been confirmed by an owner. Hedge accordingly.
- Where an entry exists to *correct* an upstream source, it says so in **Source** — in that
  case the entry wins over the document it corrects.
