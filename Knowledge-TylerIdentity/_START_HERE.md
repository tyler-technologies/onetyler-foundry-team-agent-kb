# START HERE — Routing Guide for the Tyler Identity Knowledge Corpus

This file is **the chatbot's first read** for the Identity domain. It is a **routing guide**,
not a tutorial: its job is to pick the right file and the right *section within* a file
before answering, and to know what this corpus does not cover.

Domain: Tyler Identity — Identity Workforce (enterprise/staff SSO via the Gateway), Community
Access (citizen/public identity), federation, tokens and claims, credential templates,
client operations, identity events.

> ✅ **This corpus is deployed.** Cut over on **2026-08-24**: the `TCP-KB-Identity` collection
> now holds `Docusaurus-Identity.md`, this file, `Conf-IdentityTickets.md`, `FAQ-Identity.md`
> and the shared ticket catalog, and the old single-file `tyler-identity-knowledge-base.md` has
> been removed. **This repo is the source of truth** — edit here and re-upload; never edit the
> collection in the Foundry UI, or the next upload will silently revert it.

---

## File catalog at a glance

| File | One-liner — what's in it |
|---|---|
| `Docusaurus-Identity.md` | **The substance.** A single ~2,950-line reference distilled from Tyler Blueprint `docs/identity/` (current docs only; Legacy excluded), covering both identity solutions end to end across 39 top-level sections. Because it is one large file, the *section map* below matters more than the file name — use it to aim your answer. |
| `Conf-IdentityTickets.md` | Identity-specific **ticket reference**: which CorpDev form to file for federation, auth issues, SKU change, Okta access, identity clients, custom IdP vetting — with each form's own instructions. A derived extract; the full cross-domain catalog is `Knowledge-Shared/Conf-OneTylerTickets.md`. |
| _(also in the collection)_ `Knowledge-Shared/Conf-OneTylerTickets.md` | The authoritative cross-domain **ticket catalog**. Uploaded to every collection, so this agent can answer ticket questions directly instead of handing off. |
| `FAQ-Identity.md` | **Authored answers with no upstream source** — verbal SME guidance, observed behaviour, corrections upstream owners have not yet made. Currently: how to disambiguate "client"; the fact that ticket `4149` is *Identity SKU Change*, not the SAC-enable form the Confluence page claims; the **client-side Entra ID app-registration steps** a customer must complete before the Tyler half of a federation can be configured; and why **Admin Center bootstrap access depends on which of the four Workforce models** the org uses (Direct uses a magic link; Global is a distinct Private-Preview model, not a rename of Delegated). |

---

## The one thing to get right: Workforce or Community?

Almost every mis-answer in this domain starts by picking the wrong solution. They are
separate products with separate endpoints, flows and docs.

| | **Identity Workforce** | **Community Access** |
|---|---|---|
| Who logs in | Customer **staff / back-office** users | **Citizens and the public** |
| Identity source | The customer's own IdP, federated via the **Gateway** | Tyler-hosted; users self-register |
| Sometimes called | Gateway, TID-W, Workforce Direct/Managed/Delegated/Global | TID Citizen, Community |
| Section cluster | *Identity Workforce …* | *Community Access …* / *… with Community Access* |

If the question doesn't make the audience clear, ask. "How do I set up login?" is
unanswerable until you know which one.

`Docusaurus-Identity.md` → *Choose Your Integration Path*, *Quick Comparison* and
*Integration Approach* are written for exactly this decision — start there when the user is
orienting rather than debugging.

---

## Section map for `Docusaurus-Identity.md`

The file is large and RAG chunks independently of headings, so name the section you want.

**Orientation** — *Choose Your Integration Path* · *Quick Comparison* · *Integration
Approach* · *Understanding Customer Identifiers*

**Start-to-finish integration** — *Identity Workforce Integration Checklist* (10 stages:
Prerequisites → Product Registration → OIDC → Dynamic Auth → Token Management → API Security
→ Configuration → Testing → Security → Production Readiness) · *Community Access Integration
Checklist* (7 stages)

**Identity Workforce**

| Need | Section |
|---|---|
| First-time setup, Gateway overview, prerequisites | *Getting Started with Identity Workforce* |
| Environment URLs, local dev | *Identity Workforce Environments* |
| Endpoints, client registration, scopes, token validation, CCF, logout, ASP.NET Core example | *Identity Workforce Configuration* (12 subsections — the densest part of the file) |
| Common conceptual questions (IdP requirement, how many clients, secret rolling, token lifetime, federated/back-channel logout, scope strategy) | *Identity Workforce FAQ* |
| Multi-org context, context in id_tokens / access_tokens, session switching | *Login Context with Identity Workforce* |
| Actual token shapes | *Identity Workforce Token Examples* (identity, interactive access, UserInfo, CCF) |
| `amr` / `acr` claims, federated complications, known outliers | *AMR Passthrough* |
| Something is broken | *Troubleshooting Identity Workforce* (Gateway errors with data, auth, token validation, IdP federation, configuration, debugging tools) |
| "Are we doing this right?" | *Identity Workforce Best Practices* (security, org-key management, testing, performance, architecture patterns, anti-patterns) |

**Dynamic Auth (.NET only)** — *Dynamic Auth Overview* (when to use, benefits, alternatives)
· *Using Dynamic Auth — Installation and Configuration* (NuGet → registration id → services
→ middleware → cookie policy → controller usage → troubleshooting) · *Authorization Code
Flow with PKCE (Sequence)*

**Community Access** — *Getting Started with Community Access* (architecture, integration
steps, PKCE generation, authorization request, token exchange) · *Community Access
Configuration* (Okta endpoints, scopes, token validation, branding, registration flow) ·
*Community Access Environments* · *Troubleshooting Community Access* · *Community Access Best
Practices*

**Client Operations** — *Client Operations* (available operations, endpoint security,
expected usage) · *Client Operations API Specification* (rotate secret, update redirects,
expunge old secrets, error codes)

**Credential Templates** — *Overview* · *GitHub App Overview* (modes of operation) ·
*Provisioning SDK* · *Recipes Overview* · schema `credential-config.<environment>.yaml` ·
schema `<filename>.clients.yaml` (incl. Handlebars templating)

**Identity Events** — *Overview* (use cases, event types, subscribing) · *Example Payloads*
(10 payloads: Workforce user created/disabled/profile-changed/deleted, Community profile
email-changed/deleted, user group created/updated, user added/removed from group)

**Platform and infrastructure** — *Kubernetes Authentication* (service accounts,
`Tyler.Platform.TokenRequest`, trusting K8s tokens, Token Review API, trade-offs) ·
*Filtered User Audit Logs for Cybersecurity Product*

**Migration** — *Convert a Web Accelerator App to an Ops App* (application changes, app
registration, obtaining credentials)

**Getting human help** — *Help Desk Requests* · *Teams Channels*

---

## Common query → where to go

| The user asks… | Go to |
|---|---|
| "Which one do I need?" / "what's the difference?" | *Choose Your Integration Path* + *Quick Comparison* |
| "How do I integrate my product?" | The matching **Integration Checklist**, then *Getting Started* |
| "What are the endpoints / scopes?" | *Identity Workforce Configuration* or *Community Access Configuration* |
| "Login is failing" / an error code | *Troubleshooting …* for the right solution |
| "What does this token/claim look like?" | *Identity Workforce Token Examples*; `amr`/`acr` → *AMR Passthrough* |
| "How many clients do I need?" | *Identity Workforce FAQ* |
| "How do I rotate a client secret?" | *Client Operations API Specification* — and note secrets are **never** put in a ticket |
| "How do I manage clients as code?" | *Credential Templates* cluster |
| "How do I subscribe to identity events?" | *Identity Events Overview*, then *Example Payloads* |
| "I need a federation set up / an auth issue investigated" | `Conf-IdentityTickets.md` — **not** a section of the big file |
| "Which ticket do I file?" | `Knowledge-Shared/Conf-OneTylerTickets.md` (authoritative, all domains) |
| Something no document states | `FAQ-Identity.md` |
| "Where do I ask a human?" | *Help Desk Requests* + *Teams Channels* |

---

## Disambiguation pairs

| Confusable | Which to use |
|---|---|
| `Docusaurus-Identity.md` vs `Conf-IdentityTickets.md` | The Blueprint file explains **how identity works**; the tickets file says **which form to file** to get someone to do something. "How does federation work" → Blueprint. "Who do I ask to set up a federation" → tickets. |
| `Docusaurus-Identity.md` vs `FAQ-Identity.md` | Blueprint is the derived, re-generated source of truth. The FAQ holds only what Blueprint does *not* say — and, where flagged, corrections to it. |
| *Identity Workforce FAQ* (a section) vs `FAQ-Identity.md` (a file) | The **section** is Blueprint's own FAQ and is re-derived. The **file** is authored here. Do not add to the section; add to the file. |
| "identity client" vs "client" | An identity client is a **registered OAuth/OIDC application**. A "client" in the customer sense is an organization and belongs to Ops Center. See `FAQ-Identity.md`. |
| Gateway vs Identity Workforce | "Gateway" is the internal engine name; **Identity Workforce** is the customer-facing product name. Don't say "Gateway" to customers. |

---

## Cross-domain pointers

- **Org keys, CRM customer identifiers, licensing, Admin Center access, CAPM, workspaces** →
  `Knowledge-OpsCenter/`. Identity docs reference org keys constantly but Ops Center owns
  them.
- **⚠ Listing or querying organizations and workspaces via API** → `Knowledge-OpsCenter/`
  (`Docusaurus-OpsCenterAdoption.md` → *Listing Ops Center Organizations and Workspaces*).
  **Hand this off; do not attempt it from this corpus.** The answer is the **TCP Search API**
  (`POST /api/v1/Search/workspaces`, `GET /api/v2/Tenants` filtered by `customerId`) — not a
  Provisioning or Identity endpoint.

  This is called out because it has actually gone wrong: asked "how do I get a list of
  workspaces for an organization using the api?", this agent answered instead of handing off,
  while the correct content sat indexed in the Ops Center corpus. **Any technical or API
  question about organizations, workspaces, licensing or availability belongs to Ops Center**,
  even when the asker frames it in identity terms or mentions tokens and credentials for the
  call. Authenticating the call is this corpus's business; what to call is not.
- **Retargeting a workspace's gateway / Workforce Managed → Direct migration** →
  `Knowledge-OpsCenter/` (`Training-WorkforceManagedToDirectMigration.md`). Ops Center owns
  what an operator *does*; this corpus owns how identity is *configured*.
- **Time-bound Tyler-staff access into a customer install** → `Knowledge-SupportAccessCenter/`.
- **Platform glossary, architecture, DevOps, security, SLA** → `Knowledge-BP-General/`.
- **Any ticket question** → `Knowledge-Shared/Conf-OneTylerTickets.md`.

---

## What this corpus does NOT cover

- **Legacy / Old Docs identity content.** `Docusaurus-Identity.md` deliberately excludes it.
  If a user cites something that isn't here, it may be legacy — say so rather than guessing.
- **Okta tenant administration itself.** Access is requested by ticket; the admin work is not
  documented here.
- **Ops Center UI procedures**, even identity-related ones like retargeting.
- **Anything newer than the source pull.** `Docusaurus-Identity.md` reflects Blueprint as of
  **2026-05-20**, pulled into this repo **2026-08-21**. For anything time-sensitive, prefer
  the live Blueprint page and say the file may be behind.

---

## Naming convention legend

| Prefix | Source | Authority |
|---|---|---|
| `Docusaurus-` | Tyler Blueprint (`docs.tylerdev.io`) | Published source of truth; re-derived when Blueprint changes |
| `Conf-` | Confluence | Internal process/ticket detail |
| `FAQ-` | **Authored here, no upstream source** | The home of record for answers that exist nowhere else. Carries `Source` / `Added` / `Confidence` / `Promote when` per entry |

---

## Operating principles for the chatbot

1. **Establish Workforce vs Community before answering.** If the question doesn't say, ask.
   Then, when the answer is Workforce and the question touches **federation setup or
   first-time Admin Center access**, establish *which* Workforce deployment model the
   org uses as well — the bootstrap path genuinely differs, and Direct's magic link is
   not how the others work. See `FAQ-Identity.md` → *Can the customer get into Admin
   Center before the federation is in place?*. Ask rather than defaulting to Direct.
2. **Name the section you used.** The main file is large; citing "Identity Workforce
   Configuration → Token Validation" is far more useful than citing the file.
3. **Never put a secret in a ticket.** Client secrets and test-user passwords go via
   Kiteworks or a follow-up from the TID team — say this whenever federation config comes up.
4. **Never invent a ticket URL.** Use `Conf-IdentityTickets.md` or the shared catalog.
5. **Prefer "Identity Workforce" over "Gateway"** in anything customer-facing.
6. **Flag staleness on time-sensitive answers** — see the source dates above.
7. **Hand off rather than guess** when the question is really about org lifecycle, SAC, or
   the platform generally.

---

## Index hygiene

Update this file whenever a file is added, renamed or removed from this folder — and when
`Docusaurus-Identity.md` is re-pulled, check the **section map** above still matches its
headings. A stale start page actively misleads the agent. Also update the repo `README.md` if
team-level routing changes.
