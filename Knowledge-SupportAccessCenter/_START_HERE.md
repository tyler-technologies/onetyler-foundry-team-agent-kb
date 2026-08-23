# START HERE — Routing Guide for the Support Access Center Knowledge Corpus

This file is **the chatbot's first read** for the SAC domain. It is a **routing guide** — it tells you which file to reach for and, importantly, when to hand off to the sibling **Ops Center** corpus for SAC-adjacent topics.

Domain: Support Access Center (SAC) — Tyler's framework for standardized, secure, time-bound, transparent, customer-controlled access to customer installations by Tyler operational staff.

---

## File catalog at a glance

This corpus is currently small — **1 substantive file**:

| File | One-liner — what's in it |
|---|---|
| `Docusaurus-SupportAccessCenter.md` | The full **SAC reference**. Leads with a **Starting prompts — quick answers** section that contains canonical, retrieval-tuned answers to the **five Foundry starting prompts** ("How do I get access to SAC?", "How do I integrate my product…?", "How do I request access…?", "How do I extend access?", "How do I see past access?"). Then: a **Who can use SAC** subsection distinguishing dashboard-login (open to any `@tylertech.com`) from product-specific access (gated by SAC group membership), the **Identity-Tier × OnPrem-Target compatibility matrix** (WM/Okta is the only unsupported combo), engineering requirements (Security API + `support-access-revoked` webhook), SAC group concept (all-or-nothing vs fine-grained), Group Admin setup (Support Council reps, naming convention `{Division/Major Group code} - {Optional Product} - {Optional Team/Role/Permission}` with division codes MS/AT/CJ/PS/SF/ECC/OT), Security API endpoint + sample JSON, webhook sample payload, Tyler-staff access-request workflow, customer Org-Admin approval workflow (Full access vs Limited access), extend/revoke flows, history and auditing, and links per environment for SAC dashboard + group administration. |

---

## Ticket questions are NOT answered from this corpus

If the user asks **which ticket to file** — including "how do I get authorized to use SAC
for a product?" — the authoritative catalog is
`Knowledge-OpsCenter/Conf-OpsCenterTickets.md`, held by the **Ops Center** agent. It covers
SAC, Identity, Ops Center, infrastructure and general-inquiry tickets in one place. Hand off
rather than answering; never construct a ticket URL. The SAC-specific entries there are
*Enable Support Access Center on a Workforce Managed org* and *Be authorized to use Support
Access Center for a product*.

---

## ⛔ Ticket questions are answered from the SHARED catalog

Any "which ticket do I file / how do I request access or permissions" question — in **any**
domain — is answered from **`Knowledge-Shared/Conf-CorpDevTickets.md`**, not from this
corpus. It is the only authoritative catalog, covering Ops Center, Identity, Support Access
Center, infrastructure, Forge/TCW and 3rd-party tickets, plus the separate feature-request
portal and the deprecated forms. **Never construct a ticket URL.**

---

## Common query → file routing table

### Foundry **starting prompts** — answer from the dedicated quick-answer section first
The SAC Foundry agent surfaces five starting prompts to new users. The canonical answers live in `Docusaurus-SupportAccessCenter.md` → **Starting prompts — quick answers** (placed deliberately near the top of the file). **Prefer those answers verbatim** when a user's question matches one of the five — they are tuned to start the conversation well. Then route to the deeper sections only if the user follows up with more detail. The five prompts:

1. **"How do I get access to Support Access Center?"** — *Starting prompts → How do I get access to Support Access Center?* Default to the staff-user interpretation (any `@tylertech.com` user can log in; group membership only gates product access). Do NOT lead with the Support Council admin path — that audience is trained separately.
2. **"How do I integrate my product with Support Access Center?"** — *Starting prompts → How do I integrate my product…*; deeper: *Engineering requirements*, *Security API*, *Support Access Revoked Webhook*.
3. **"How do I request access to my product for a customer installation?"** — *Starting prompts → How do I request access…*; deeper: *Making a support request* + *Customer approval workflow*.
4. **"How do I extend access?"** — *Starting prompts → How do I extend access?*; deeper: *Extending or revoking*.
5. **"How do I see past access?"** — *Starting prompts → How do I see past access?*; deeper: *History and auditing*.

### "What is SAC / when is it supported / what's the eligibility?"
- `Docusaurus-SupportAccessCenter.md` — *Introduction* and *Compatibility with Org Identity Tier + Workspace OnPrem target*.

### "I'm adopting SAC in my product — what do I need to build?"
- `Docusaurus-SupportAccessCenter.md` — *Engineering requirements*, *Security API*, *Support Access Revoked Webhook*.
- Cross-reference: `../Knowledge-OpsCenter/GitHub-TCPWebhookApi.md` for the **full webhook schema details** (`support-access-revoked` event).

### "How do I administer SAC groups for my product?"
- `Docusaurus-SupportAccessCenter.md` — *Group administration (Support Council reps only)*.
- Naming convention rules: division codes + product + optional role.

### "I'm Tyler staff — how do I request access to a customer org for support?"
- `Docusaurus-SupportAccessCenter.md` — *Links to SAC (Tyler staff dashboard)* and *Making a support request*.
- Customer-side approval flow context: *Admin Center Tyler Access setting* and *Customer approval workflow*.

### "How does a customer approve / deny SAC requests?"
- `Docusaurus-SupportAccessCenter.md` — *Customer approval workflow (Limited access orgs)*.

### "How do I extend or revoke an active access request?"
- `Docusaurus-SupportAccessCenter.md` — *Extending or revoking*.

### "How do I audit SAC history?"
- `Docusaurus-SupportAccessCenter.md` — *History and auditing* (per-org view + global history view).

---

## Cross-domain pointers — go to `Knowledge-OpsCenter/`

Several SAC-adjacent topics live in the **Ops Center** corpus, not here. The chatbot should pivot to the Ops Center folder for:

| If the user asks about… | Reach for (in `../Knowledge-OpsCenter/`) |
|---|---|
| **Enabling SAC on a Workforce Managed + Gateway org** (the ticket flow) | `Conf-OpsCenterTickets.md` → *Support Access Center* (ticket form `…/create/4149`). |
| **The full `support-access-revoked` webhook schema** (filter fields, payload shape, subscription mechanics) | `GitHub-TCPWebhookApi.md` → *Support Access Messages*. SAC adopters must subscribe to this. |
| **Identity Workforce / Workforce Direct / Managed / Delegated concepts** | `Docusaurus-Terminology.md` (canonical glossary). |
| **Organization Identity Tier and Workspace OnPrem Target** (the two inputs to the SAC compatibility matrix) | `Docusaurus-OpsCenter.md` → *Identity Workforce product tiers* and *Organization Details*. |
| **The "Gateway" vs "Identity Workforce" terminology rule** | `Docusaurus-Terminology.md` and `Conf-GatewayOperationalTesting.md` (the customer-facing rule: never say "Gateway" to customers). |
| **Product registration prerequisite for SAC adoption** | `Docusaurus-ProductRegistration.md`. |

> **Rule of thumb:** if the question is about **using SAC** (UI, workflows, engineering requirements), it's in this folder. If the question is about **the broader Tyler platform context that makes SAC work** (identity tiers, ticket forms, webhook subsystem, product registration), it's in the Ops Center folder.

---

## What this corpus does NOT cover

- **Per-product SAC integration code samples.** The engineering requirements (Security API + webhook) are documented here, but each product team's SAC integration code lives in that product's repo.
- **Okta-side configuration** for Workforce Managed orgs (which is why WM/Okta is unsupported for SAC). For Okta admin operations, see the Identity Cloud team's documentation referenced from the Ops Center corpus.
- **Customer-facing user guides.** This corpus is for Tyler engineering, Support Council reps, and Tyler operational staff. The customer-facing portion (Org Admin approval workflow) is described from the Tyler perspective.
- **Audit log query language / export formats.** The History view is described; programmatic access to history is not documented here.

When a user asks about something not covered, say so plainly and (if applicable) point them at the SAC team or the Identity team via the channels listed in `Docusaurus-SupportAccessCenter.md` → *Getting administrative permissions* (Vijay Venkataraman / Jason Howard).

---

## Naming convention legend

Same prefixes as the Ops Center corpus:

| Prefix | Source | What that means for the chatbot |
|---|---|---|
| **`Docusaurus-`** | Blueprint Docusaurus (`docs.tylerdev.io`) | Tyler-internal but publicly addressable URL. Authoritative for current state of the SAC product. |
| (no other prefixes used yet in this folder) | | Future SAC content from other sources will use `Conf-`, `GitHub-`, `Training-`, `Misc-` consistent with the parent project conventions. |

---

## Operating principles for the chatbot

1. **Read this file first on every session for SAC-related queries.** Then go to `Docusaurus-SupportAccessCenter.md` for the substance, OR hand off to the Ops Center corpus per the cross-domain table above.
2. **The Identity-Tier × OnPrem-Target compatibility matrix is the #1 SAC gotcha.** Always check this when a user asks "can SAC work for my customer?" — WM/Okta is unsupported; WM/Gateway needs explicit enablement plus customer pre-notification plus a Jason Howard handoff; WD/Gateway and WD-Delegated/Gateway are fully supported.
3. **Two engineering requirements for SAC adoption are non-negotiable:** (a) integrate with `tcp-login-security-api` v1, (b) subscribe to the `support-access-revoked` webhook. Don't tell a product team they "support SAC" until both are in place.
4. **SAC login is open to any `@tylertech.com` user — no special authorization is required to reach the dashboard.** What's gated by SAC group membership is the ability to **request access to a specific product** (the *Select products* step in the request wizard is filtered to products the user's groups allow). When users ask "how do I get access to SAC?", default to the staff-member login interpretation — it's by far the most common framing. Only mention the Support Council admin path as a brief aside; that audience is trained separately. Non-Tyler email logins are not supported.
5. **The "Tyler access" Admin Center setting** is the customer-side switch between auto-approval (Full access, default) and manual approval (Limited access). When a user's SAC request is "stuck," check this setting first.
6. **Extensions create a second audit record** — by design, for audit trail preservation. Revoking an extension does NOT revoke the original; remind users they must revoke both if they want all access gone.
7. **Group naming convention is enforced:** `{Division/Major Group code} - {Optional Product} - {Optional Team/Role/Permission Type}`. Division codes are MS, AT, CJ, PS, SF, ECC, OT. When a Support Council rep asks for naming help, apply this format.
8. **Permission grants for group administration default to production only.** If a Support Council rep needs non-prod access, they must explicitly request it from Vijay Venkataraman or Jason Howard.

---

## Index hygiene

Update this file when new SAC content is added to the folder. The folder is small today, but as SAC matures expect:
- A `Conf-*` file with the live SAC implementation runbook (when one becomes available).
- A `Training-*` file if/when the SAC training video is recorded.
- A `Misc-Links.md` if multiple live URLs accumulate.

When that happens, expand the **File catalog** and **Common query → file routing table** sections accordingly.
