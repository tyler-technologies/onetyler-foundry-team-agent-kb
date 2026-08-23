# START HERE — Routing Guide for the Ops Center Knowledge Corpus

This file is **the chatbot's first read**. It is a **routing guide**, not a glossary or a tutorial. Its purpose is to help the chatbot pick the right file(s) before answering, and to know what this corpus does and does NOT cover. The actual answers live in the other files; this file just tells you where to look.

Domain: Ops Center (Tyler Cloud Platform — operational tooling, organization/workspace lifecycle, identity, CRM prerequisites, product registration, support models, webhooks, environments).

---

## File catalog at a glance

16 files in this folder (plus this one). The ticket catalog that used to live here has moved to `Knowledge-Shared/Conf-OneTylerTickets.md`. One-liner per file — read the full file for the substance.

| File | One-liner — what's in it |
|---|---|
| `Conf-CRMCustomerIdentifiers.md` | The deep technical/operational reference for the **CRM Customer Identifier** (= the Ops Center Org Key). Generation algorithm, portability across CRM merges, usage across TCP / Tyler Deploy / TID-W / SaaS / Twilio, troubleshooting tree, exact ticket subjects. |
| `Conf-GatewayOperationalTesting.md` | How to validate a **Gateway-ready product** against the real-world test org `tylertownwa`. Test account emails (**password NOT in this corpus** — points to the source Confluence page), 4 Gateway integration components, Core vs Full compliance, Tyler Deploy addendum, net-new-customer routing rules. |
| `Conf-AddingExternalUsersToEntraId.md` | The **Workforce Direct-only** workaround for adding non-employee users (temps, contractors) to a customer's Entra ID **without consuming an Office 365 license**. Tyler-staff coaching material — NOT to share with customers directly. |
| `Conf-CommunityAccessProfileManager.md` | How a **customer Org Admin** grants their support staff access to **CAPM** via an Admin Center group. Default flow (pre-provisioned group) + manual group creation flow (older orgs). |
| `Conf-EnvironmentsAndAllowListing.md` | The canonical **environments + firewall allow-listing** reference. 3 AWS environments (CI/QA/Prod), inbound root-domain allow-list, outbound IP lists (with "original" IPs flagged), 4 TID Okta instances. |
| `Docusaurus-Terminology.md` | The **canonical TCP glossary**. Use as the authority for every term. Disambiguation pairs (Authentication↔Authorization, Licensing↔Availability, Customer↔Organization, Tenant↔Workspace, Environment↔Workspace, Workforce Direct↔Managed↔Delegated, Cloud↔Cloud-native, Server-based↔Serverless, etc.). |
| `Docusaurus-OpsCenter.md` | The Ops Center **product + process reference**. Leads with a **Starting prompts — quick answers** section that contains canonical, retrieval-tuned answers to the **four Foundry starting prompts** ("How do I get access to Ops Center?", "How can I get access to a client's Admin Center?", "Where can I see the Identity Configuration details for a customer?", "Where can I see Ops Center training and other useful guides?"). Then: env URLs, access flow, dashboard, organizations/identity tiers, +Import & +Create Internal wizards, the standard pre-created orgs table, Org Details, Admins, Licensing/Availability, AD Agent setup, Federation flows, Product Registry, Bulk Licensing, Permissions, Telemetry (QuickSight), changelog highlights. |
| `Docusaurus-OpsCenterAdoption.md` | The **Ops Center API integration guide** for deployment-tool owners — TCP Search API for listing Orgs/Workspaces, Provisioning v2 for Licensing/Availability and workspace create, Platform Service for Internal-Org workspace deactivate/activate, Webhook API events. Covers numeric-id vs key gotchas, declarative set-style POST semantics, workspace-key rules, the `manage:internalorganization` gate, and the Customer-vs-Internal Org lifecycle split. |
| `Docusaurus-TylerCRM.md` | Shorter Docusaurus version of the **CRM record validity** flow — 4-point validity checklist, where to find the Customer Identifier. Use `Conf-CRMCustomerIdentifiers.md` for the deep dive. |
| `Docusaurus-OrgAdminInfo.md` | Who an **Org Admin** is, ideal profile, probing questions to source the customer IT contact when only functional contacts are known, post-creation Org Admin add flow. |
| `Docusaurus-ProductRegistration.md` | What a **registered product** is, the 4 application types (Ops/Workforce/Admin/Community) and where they surface, PM/PjM preparation checklist, FAQs (Product vs SKU, where Ops Apps appear, single-web-destination pattern, pre-defined product groups), worked example (Cemetery Manager). |
| `GitHub-TCPWebhookApi.md` | Full catalog of all **25 TCP webhook event types** across 6 domains (Identity Community, Identity Workforce, Organization, Product, Support Access, User Group). Schemas, example payloads, filter fields, the `ProductLicensed` custom filter, three auth methods (JWT/API Key/None), HTTPS required, all V1. |
| `Training-OpsCenterOperations.md` | The **narrative "how to think about it" companion** distilled from the official 6-part training. Strategic context (OTCOM 14.3/14.4, cross-sell story), vocabulary, the typical operational process (Step 1 / 2A / 2B / 2C / 3), distributed support model, resources/forums. |
| `Training-WorkforceManagedToDirectMigration.md` | The two-part **WM → WD conversion** runbook. Part 1 (Tyler-staff Retargeting in Ops Center): permission gate, eligibility checklist, cross-product coordination, SubjectId reset warning, per-workspace Target Gateway flow, Enable self-service migration. Part 2 (customer Admin Center migration): Import Federations → IdP update (Google example) → Configuration / Testing / Domains wizard → Activate → Finalize or Revert. |
| `Misc-Links.md` | The **catch-all bookmark catalog**. Live URLs to: Confluence training hub + 6-part videos + handout PDFs, Confluence operational deep-dives, the **Blueprint Docusaurus reference catalog** (160 entries across 9 sections at `docs.tylerdev.io`). Use when the user wants a URL we haven't distilled. |

---

## ⛔ Ticket questions are answered from the SHARED catalog

Any "which ticket do I file / how do I request access or permissions" question — in **any**
domain — is answered from **`Knowledge-Shared/Conf-OneTylerTickets.md`**, not from this
corpus. It is the only authoritative catalog, covering Ops Center, Identity, Support Access
Center, infrastructure, Forge/TCW and 3rd-party tickets, plus the separate feature-request
portal and the deprecated forms. **Never construct a ticket URL.**

---

## Common query → file routing table

When the user asks about… reach for these first (in order of priority):

### Foundry **starting prompts** — answer from the dedicated quick-answer section first
The Ops Center Foundry agent surfaces four starting prompts to new users. The canonical answers live in `Docusaurus-OpsCenter.md` → **Starting prompts — quick answers** (placed deliberately near the top of the file, right after the *How to use this guide* table). **Prefer those answers verbatim** when a user's question matches one of the four — they are tuned to start the conversation well. Route to deeper sections only if the user follows up with more detail. The four prompts:

1. **"How do I get access to Ops Center?"** — *Starting prompts → How do I get access to Ops Center?*; deeper: `Docusaurus-OpsCenter.md` → *Access — environment URLs*, *Access — request a ticket*, *Access — promote teammates*; `Knowledge-Shared/Conf-OneTylerTickets.md` → *Basic Access* for the exact Notes-field wording on shared form 4133.
2. **"How can I get access to a client's Admin Center?"** — *Starting prompts → How can I get access…*; deeper: `Knowledge-Shared/Conf-OneTylerTickets.md` → *Client Admin Center access request* (form 4165) for the standard path, and `Docusaurus-OpsCenter.md` → *Organization Details — Admins* + the *Org Admin promotions — a Manager's guide* Confluence page for the elevated-permission self-promote alternative.
3. **"Where can I see the Identity Configuration details for a customer?"** — *Starting prompts → Where can I see the Identity Configuration…*; deeper: `Docusaurus-OpsCenter.md` → *Organization Details* (Basic details for Identity Tier; Manage workspaces for per-workspace OnPrem Target), *Identity Workforce (org details)* for tier-specific federation/AD-Agent setup, and *Authentication logs* for sign-in history. Always flag that Identity Tier cannot be changed after org creation (the narrow UNINITIATED WD→WM conversion ticket is the only exception).
4. **"Where can I see Ops Center training and other useful guides?"** — *Starting prompts → Where can I see Ops Center training…*. **Primary URL — must be surfaced verbatim, never paraphrased:** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386599613/Tyler+Cloud+Platform+TCP+Deployment — the Tyler Cloud Platform Deployment / Operational Training Hub on Confluence, which hosts the 6-part video series, the slide deck, and the handout PDF. Deeper: `Misc-Links.md` → *TCP / TID Operational Training* for the same URL plus the individual demo/setup Confluence pages; `Training-OpsCenterOperations.md` → *Resources* table also carries the URL; `Training-OpsCenterOperations.md` and `Training-WorkforceManagedToDirectMigration.md` for the GPT-distilled training narratives.

### "How do I file a ticket / what's the right ticket for X?"
- `Knowledge-Shared/Conf-OneTylerTickets.md` (start here always)
- **Critical disambiguation:** "Add an Org Admin / Promote me as admin" does NOT use the generic form 4133 — see *Org Admins* section in that file.

### "What does this Tyler term mean?"
- `Docusaurus-Terminology.md` (authoritative glossary)
- For deep CRM term context: `Conf-CRMCustomerIdentifiers.md`

### "How do I use Ops Center to do X?"
- `Docusaurus-OpsCenter.md` (product/process reference; covers wizards, AD Agent, federation setup, Bulk Licensing, etc.)
- `Training-OpsCenterOperations.md` for the "why" narrative
- `Conf-EnvironmentsAndAllowListing.md` for env URLs

### "How do I integrate my deployment tool with Ops Center via API?"
- `Docusaurus-OpsCenterAdoption.md` (canonical reference — TCP Search API for listing; Provisioning v2 for Licensing/Availability/workspace create; Platform Service for Internal-Org workspace deactivate/activate; Webhook API for change events)
- **Customer-Org workspace deletion / Org lifecycle changes are forbidden for external tools** — route via OneTyler ticket (`Knowledge-Shared/Conf-OneTylerTickets.md`).
- For the broader webhook catalog (Identity, Support Access, User Group events): `GitHub-TCPWebhookApi.md`

### "Why is my customer's org / Customer Identifier missing or wrong?"
- `Docusaurus-TylerCRM.md` (4-point validity quick check)
- `Conf-CRMCustomerIdentifiers.md` (deep troubleshooting + regeneration + post-deployment cases)

### "I'm creating / importing an org and need to source the customer IT admin"
- `Docusaurus-OrgAdminInfo.md` (probing questions, ideal profile)
- `Docusaurus-OpsCenter.md` → Import an organization wizard (mechanics)

### "What's Gateway / Identity Workforce / Workforce Direct vs Managed vs Delegated?"
- `Docusaurus-Terminology.md` → *Identity Workforce* cluster
- `Training-OpsCenterOperations.md` → *Basic Concepts — Identity*
- `Conf-GatewayOperationalTesting.md` (testing) and `Training-WorkforceManagedToDirectMigration.md` (migration)
- **Customer-facing rule:** Always say **"Identity Workforce" / "Workforce Direct" / "Workforce Managed"**. **Never say "Gateway"** to customers — it's an internal code name.

### "How does my product migrate a customer from Workforce Managed to Workforce Direct?"
- `Training-WorkforceManagedToDirectMigration.md` (both parts)
- `Knowledge-Shared/Conf-OneTylerTickets.md` → *Orgs > Organization Details > Workspace migration* for the permission gate
- For Gateway-readiness prerequisite: `Conf-GatewayOperationalTesting.md`

### "How do I test my Gateway-ready product?"
- `Conf-GatewayOperationalTesting.md` (test org `tylertownwa`, test account emails, etc.). For the **test password**, send the user to the source Confluence page — it is deliberately not stored in this corpus.

### "How does Workforce Direct customer add temp / contractor users without burning O365 licenses?"
- `Conf-AddingExternalUsersToEntraId.md` — but **DO NOT share the page URL with customers**; coach their IT admin from this content.

### "Customer wants to give helpdesk staff access to CAPM"
- `Conf-CommunityAccessProfileManager.md` — customer Org Admin flow.
- For TYLER STAFF requesting CAPM access (different flow): `Knowledge-Shared/Conf-OneTylerTickets.md` → CAPM access request.

### "I'm registering a product / what app types exist / Product vs SKU?"
- `Docusaurus-ProductRegistration.md`
- For the live registration source-of-truth: `Misc-Links.md` → Blueprint catalog entries under *Product System Registration*.

### "What webhooks are available / how do I subscribe / what's the payload for X?"
- `GitHub-TCPWebhookApi.md` (full catalog — all 25 event types across 6 domains)
- For just the Org / Workspace / Product subset relevant to deployment-tool integration: `Docusaurus-OpsCenterAdoption.md` → Webhooks section
- For SAC's `support-access-revoked` event specifically: cross-reference `../Knowledge-SupportAccessCenter/Docusaurus-SupportAccessCenter.md`.

### "What environments does TCP have / how do I allow-list / what's the Ops Center URL for X?"
- `Conf-EnvironmentsAndAllowListing.md` (canonical egress IPs + DNS endpoints + per-env URLs)
- `Docusaurus-OpsCenter.md` → *Access — environment URLs* has the same Ops Center URLs

### "What support team owns this issue / where do I escalate?"
- `Training-OpsCenterOperations.md` → *Support — distributed support model* and *Issue routing rules*
- For ticket URLs: `Knowledge-Shared/Conf-OneTylerTickets.md`

### "Give me the URL / link to <some Tyler doc>"
- `Misc-Links.md` (bookmark catalog)
- For the Blueprint Docusaurus site specifically: the **Blueprint Docusaurus reference catalog** section inside `Misc-Links.md`

### "What did the official training video say about X?"
- `Training-OpsCenterOperations.md` (Parts 1, 2, 3, 6 distilled)
- `Training-WorkforceManagedToDirectMigration.md` (the WM→WD-specific training distilled)
- For the videos themselves and handouts: `Misc-Links.md` → *TCP / TID Operational Training* section

---

## Disambiguation pairs (when two files seem to overlap)

| Files that look similar | How to choose |
|---|---|
| `Docusaurus-TylerCRM.md` vs `Conf-CRMCustomerIdentifiers.md` | **Docusaurus** is the lighter version (4-point checklist + where to find the Identifier); **Confluence** is the deep dive (generation algorithm, portability, usage across systems, troubleshooting tree, ticket subjects). For "is my record valid?" → Docusaurus; for "why isn't the Identifier showing up / what does it look like across TCP / Tyler Deploy / etc.?" → Confluence. |
| `Docusaurus-OpsCenter.md` vs `Training-OpsCenterOperations.md` | **Docusaurus-OpsCenter** is the *product reference* (how the screens work). **Training-OpsCenterOperations** is the *narrative* (why we do this, the OTCOM context, the typical end-to-end process). For "how do I import an org?" → Docusaurus. For "why does Tyler require a CRM record?" → Training. |
| `Docusaurus-OpsCenter.md` vs `Docusaurus-OpsCenterAdoption.md` | **Docusaurus-OpsCenter** is for users *operating Ops Center through the UI* — wizards, screens, AD Agent, federation, Bulk Licensing, Permissions. **Docusaurus-OpsCenterAdoption** is for engineers *integrating with Ops Center via API* from another deployment tool — Search API, Provisioning v2, Platform Service, Webhook API. For "how do I license a product in the Ops Center UI?" → Docusaurus-OpsCenter. For "what API do I call to license a product from my deployment tool?" → Docusaurus-OpsCenterAdoption. |
| `Docusaurus-OpsCenterAdoption.md` vs `GitHub-TCPWebhookApi.md` | **OpsCenterAdoption** enumerates only the Org / Workspace / Product webhook events relevant to integration. **GitHub-TCPWebhookApi** is the full catalog (all 25 events across 6 domains, including Identity / Support Access / User Group). For the integration-focused subset → OpsCenterAdoption; for any other event family → GitHub-TCPWebhookApi. |
| `Knowledge-Shared/Conf-OneTylerTickets.md` vs `Misc-Links.md` | **Conf-OneTylerTickets** is the *distilled catalog* with exact field instructions. **Misc-Links** has the live Confluence catalog URL plus other Confluence deep-dives. For "what ticket?" → Conf-OneTylerTickets. For "give me the URL to the live catalog or to a sibling Confluence page" → Misc-Links. |
| `Docusaurus-OpsCenter.md` (Bulk Licensing section) vs `Misc-Links.md` (Bulk licensing preview entry) | Docusaurus has the *how-to*; Misc-Links has the live Coda guide URL with videos. Use Docusaurus first, then offer the Coda URL for video walkthrough. |
| Conf-* files vs Blueprint catalog in Misc-Links.md | **Conf-** files are DISTILLED Confluence content (Tyler-internal, sometimes customer-side guidance). **Blueprint** is the public-facing Docusaurus reference (`docs.tylerdev.io`). When the user wants the public, current, evolving doc → Blueprint URL. When they want a fast answer the chatbot can ground in → Conf-* or Docusaurus-* file. |
| `Training-OpsCenterOperations.md` vs `Training-WorkforceManagedToDirectMigration.md` | Both are training distillations. The first is the *general* 6-part operational training (overview, basic concepts, typical process, support). The second is *specifically* the WM→WD conversion. For broad ops questions → general; for the specific migration → WM-to-WD. |
| `Conf-CommunityAccessProfileManager.md` vs `Knowledge-Shared/Conf-OneTylerTickets.md` (CAPM access) | **Conf-CommunityAccessProfileManager** is the customer-side flow (Org Admin grants their staff access via Admin Center). **Conf-OneTylerTickets** → CAPM access request is the TYLER-STAFF flow (Tyler employee requests access to the *demo* CAPM instance via a ticket). Different audience + different URL. |

---

## Cross-domain pointer

When the user asks about **Support Access Center (SAC)** — engineering requirements, group setup, request flow, security API, the support-access-revoked webhook — look in the **`Knowledge-SupportAccessCenter/`** folder (sibling of this one), specifically `Docusaurus-SupportAccessCenter.md`. The Ops Center corpus only references SAC at the level of "here's the ticket to enable it" (`Knowledge-Shared/Conf-OneTylerTickets.md`) and "here's the webhook signature" (`GitHub-TCPWebhookApi.md`). For everything else SAC-related, hand off to the SAC corpus.

---

## What this corpus does NOT cover

Be honest with the user when they ask about these — don't fabricate:

- **Customer-facing product user guides** for any specific Tyler product (e.g., how to use Enterprise ERP). This corpus is operational/platform, not per-product feature documentation.
- **Pricing, licensing terms, or contract negotiation.** That lives in CRM and sales tools, not here.
- **Anything below the platform layer** — AWS infrastructure deep-internals, Kubernetes cluster ops, raw Terraform modules. The Blueprint catalog in `Misc-Links.md` has pointers to DevOps documentation; this corpus does not distill it.
- **Customer-facing Identity Workforce setup runbooks** (federation setup steps the customer's IT does in their own IdP, beyond the Workforce-Direct migration example in `Training-WorkforceManagedToDirectMigration.md`). For other IdPs (Entra ID, Okta, ADFS, Ping), the customer follows their IdP's own docs.
- **Product Registration technical schema and APIs.** Conceptual / preparation guidance is in `Docusaurus-ProductRegistration.md`. The technical registration JSON / API / GitHub repo for the catalog (`tcp-product-catalog`) is referenced but not distilled.
- **Foundry / GPT internals.** This is documentation FOR a Foundry agent — not documentation OF Foundry.

When a user asks about something we don't cover, say so plainly and (if applicable) suggest the Blueprint catalog in `Misc-Links.md` or the relevant Confluence space.

---

## Naming convention legend

The filename prefix tells you the source system. Use this to assess freshness and authority:

| Prefix | Source | What that means for the chatbot |
|---|---|---|
| **`Conf-`** | Confluence (`tylertech.atlassian.net/wiki/`) | Tyler-internal Confluence pages. Generally Tyler-staff-only. Often the most current operational guidance. Always note "internal Tyler reference" when surfacing the URL. |
| **`Docusaurus-`** | Blueprint Docusaurus (`docs.tylerdev.io`) | Tyler-internal but publicly addressable. The structured docs site for product/platform engineering. Live URL works for anyone with the link. |
| **`Training-`** | Distilled from official training assets (videos, decks, PDFs hosted on SharePoint / Tyler Community) | Narrative / "why" content. Time-bounded — the source training is **effective until H1 2026** with major revisions expected with new Identity features later in 2026. Flag this when answering. |
| **`GitHub-`** | GitHub repo content (`github.com/tyler-technologies/...`) | Tyler-private repos. Technical references (schemas, APIs, code-adjacent docs). |
| **`Misc-`** | Curated bookmark catalog (spans all of the above + Tyler Community + Coda + SharePoint) | The catch-all live-URL index when content isn't distilled into its own file. |

---

## Operating principles for the chatbot

1. **Read this file first on every session.** Then retrieve / consult the specific files routing tells you to.
2. **Cite the file you're answering from** when relevant — e.g., "per `Knowledge-Shared/Conf-OneTylerTickets.md`…" — so the user can verify.
3. **Surface URLs verbatim.** Don't paraphrase or guess them. If a URL appears in a file, copy it exactly. If you don't have a URL for something the user asks about, say so.
4. **Match audience tags.** Many files are Tyler-internal guidance and **must not** be shared with customers directly. Flag this when surfacing internal content. The `Notes for the chatbot` section in each file usually calls out specific audience constraints.
5. **Prefer the distilled file over the live URL for fast answers**, but **prefer the live URL** when the user explicitly asks "where can I learn more?" or "show me the current source" — content evolves, and the live source is canonical for currency.
6. **For exact terminology, defer to `Docusaurus-Terminology.md`** — it is the canonical glossary. When the user uses an ambiguous term (e.g., "client" could mean customer or Identity Client; "admin" could mean Admin app or Ops app), reach for the glossary's disambiguation cluster and surface the relevant pair.
7. **Don't fabricate ticket URLs, environment IPs, or webhook event names.** If you're unsure, route to the relevant `Conf-*` or `GitHub-*` file and quote from it.
8. **When a user describes a problem that touches multiple files**, name the files you're consulting in your answer. This both helps the user follow up and helps you stay grounded across the corpus.

---

## Index hygiene

This file should be **updated whenever a file in `Knowledge-OpsCenter/` is added, removed, or substantially restructured**. If the file catalog at the top is out of date, the routing table downstream becomes misleading. Keep it lean — one line per file in the catalog; longer descriptions belong in the per-file headers, not here.
