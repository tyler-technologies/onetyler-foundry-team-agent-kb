# START HERE — Routing Guide for the Blueprint General Knowledge Corpus

This file is **the chatbot's first read** for the BP-General domain. It is a **routing guide**, not a tutorial. Its job is to help the chatbot (1) decide whether the question belongs to one of the **three specialized Foundry agents** and hand off, and (2) otherwise pick the right BP-General file before answering. The actual answers live in the other files.

**Domain:** Blueprint General — the rest of the **Tyler Blueprint** documentation (`docs.tylerdev.io`) and **Tyler Cloud Platform (TCP)** content that is **not** owned by a specialized agent. Covers platform orientation/glossary, client & ops applications, the TCP/TID API catalog, service architecture, DevOps, platform security, product/system registration, Aligned Releases, and Status Page & SLA.

---

## ⚠️ First: should this go to a specialized agent?

Tyler runs **three specialized Foundry agents** alongside this general one. **If the question is squarely about one of these, recommend that agent and give its Blueprint URL** rather than answering from this corpus.

| Specialized agent | Trigger keywords | Point the user to (Blueprint URL) |
|---|---|---|
| **Ops Center** | "Ops Center", org/workspace lifecycle in Ops Center, product licensing & activation in Ops Center, org import/create, CRM customer identifiers, Ops Center permissions/telemetry | https://docs.tylerdev.io/app-guides/ops/ops-center/overview/ |
| **Support Access Center (SAC)** | "Support Access Center", "SAC", time-bound staff access to customer installs, SAC groups, access requests/approvals/extensions | https://docs.tylerdev.io/ops/support-access-center/ |
| **Identity** (managed separately) | "Identity", "Identity Workforce", "Identity Community", "Gateway", Workforce Direct/Managed/Delegated, federation, credential templates, login/token flows | https://docs.tylerdev.io/identity |

**The canonical answer to "What specialized agents are available?"** is the three rows above — always give the agent name, its trigger keywords, and its URL. The full answer also lives in `Docusaurus-PlatformOverview.md` → *Specialized Foundry agents — when to hand off* (retrievable as content). **Everything else is BP-General's job.**

Defining a term (e.g., what "Workforce Managed" means — it's in the glossary) does **not** require a hand-off. Hand off when the user needs **workflows, configuration, or deep how-to** in one of the three specialized domains.

---

## File catalog at a glance

11 files in this folder (plus this one). One-liner per file — read the full file for substance.

| File | One-liner — what's in it |
|---|---|
| `Docusaurus-PlatformOverview.md` | **Orientation + canonical glossary + specialized-agent routing.** Cloud Living / Tyler 2030, what TCP is, platform applications, Client vs Ops app types, getting support (service desk + Teams channels), and the full Blueprint **terminology glossary**. The agent's grounding file — read it early. |
| `Docusaurus-ClientApps.md` | The **client-application reference**: Admin Center (sign-in, roles, ACLs, Identity Workforce config in the AC UI, users/bulk import, page-by-page feature reference, Tyler-internal integration + sandbox tenants), App Directory, CAPM, Community Launcher, Community Profile, Workforce Profile, and Community Services Directory (CSD admin/config/public directory). |
| `Docusaurus-OpsApps.md` | The **Tyler-staff Ops app family** *excluding* Ops Center & SAC: app taxonomy (client vs ops), **Audit Center**, **Authorization Config**. (Audit Center / Authorization Config source pages are stubs — file says so; don't fabricate.) Hands off to the Ops Center & SAC agents. |
| `Docusaurus-CloudPlatformAPI.md` | The **TCP/TID API service catalog** — 29 services (tcp-* and tid-*) distilled from their OpenAPI specs: purpose, ingress URL, auth model, key endpoints. Answers "which API do I call for X?". Includes SAC/Identity-related APIs as catalog entries but hands off conceptual questions. |
| `Docusaurus-ServiceArchitecture.md` | **Platform service-architecture engineering guides** across 5 subsystems: **Authorization** (permissions, Styra DAS, service-account registration), **Search** (CQRS/OpenSearch, EF interceptor, event/reindex handlers, endpoints), **Webhooks** (architecture, developing, subscribing, message types), **TCP Eventing** (SQS/EventBridge, publishers/subscribers, schema validation, failed messages), **Community Service Directory** (reference architecture). |
| `Docusaurus-DevOps.md` | The **CorpDev DevOps/platform-engineering reference** (largest file): Datadog, Harness (incl. governance standard + FME), JSM/on-call, CI (GitHub/Artifactory), DB migration, Terraform/IaC + Workspace Manager, TCP AWS infrastructure (VPC, EKS/Karpenter, CI/CD), Disaster Recovery (guides + regional-failover runbooks), and operational runbooks (P1 incident, AWS SSO, K8s upgrade, PagerDuty, dev-tool provisioning). Internal-only. |
| `Docusaurus-Security.md` | **Platform-security engineering**: RDS IAM authentication, Akeyless secrets-management design, vulnerability scanning (AquaSec + admission control), and WAF rules (ITAR GeoIP block list). |
| `Docusaurus-ProductSystemReg.md` | **Product & System Registration**: what a registered product is, the 4 application types, PM prep guidelines, the `tcp-product-catalog` GitOps registration workflow, URL-mapping secret setup, verifying registration in Ops Center, the Cemetery Manager worked example, FAQs, and customer onboarding concepts. (Several source pages are stubs — flagged in-file.) |
| `Docusaurus-AlignedReleases.md` | **Aligned Releases**: key concepts (feature lifecycle, cohorts), the integration guide (auth, releases/cohorts/features, GA trigger, end-to-end workflow), the API reference, and an integration checklist. |
| `Docusaurus-StatusPageAndSLA.md` | **Status Page & SLA tracking** — concepts, guides, and checklists. NOTE: the source pages are largely "content coming soon" stubs; the file is honest about that and tells the chatbot not to fabricate API details. |

---

## Common query → file routing table

When the user asks about… reach for these first (after checking the specialized-agent hand-off table above):

### "What is TCP / Cloud Living / what does <term> mean / which agent do I use?"
- `Docusaurus-PlatformOverview.md` (orientation, glossary, and the specialized-agent routing answer).

### "How does Admin Center / App Directory / CAPM / CSD / Community or Workforce Profile work?"
- `Docusaurus-ClientApps.md`.
- For deep **identity** federation/protocol questions that Admin Center merely configures → **Identity agent** (https://docs.tylerdev.io/identity).

### "What's the Audit Center / Authorization Config ops app?"
- `Docusaurus-OpsApps.md` (note: those pages are stubs).
- For Ops Center itself → **Ops Center agent**; for SAC → **SAC agent**.

### "Which API do I call for X / what endpoints does service Y have?"
- `Docusaurus-CloudPlatformAPI.md` (service index + per-service sections).
- For the *architecture/how-to* behind Authorization, Search, Webhooks, Eventing, CSD → `Docusaurus-ServiceArchitecture.md`.

### "How do I add a permission / register a service account / build a search endpoint / develop or subscribe to a webhook / set up an event publisher or subscriber?"
- `Docusaurus-ServiceArchitecture.md`.
- For the corresponding API surface → `Docusaurus-CloudPlatformAPI.md`.

### "How do I use Datadog / Harness / Terraform / the AWS infra / do DR / run this runbook (P1, AWS SSO, K8s upgrade, PagerDuty, dev-tool provisioning)?"
- `Docusaurus-DevOps.md` (internal-only operational content).

### "RDS IAM auth / Akeyless / vulnerability scanning / WAF rules?"
- `Docusaurus-Security.md`.

### "How do I register a product / what app types exist / Product vs SKU / customer onboarding & provisioning?"
- `Docusaurus-ProductSystemReg.md`.
- For product registration *in the Ops Center UI specifically* → **Ops Center agent**.

### "What is Aligned Releases / how do I integrate with it / cohorts / GA trigger?"
- `Docusaurus-AlignedReleases.md`.

### "Status Page / SLA tracking?"
- `Docusaurus-StatusPageAndSLA.md` (mostly stubs today — set expectations).

### "How do I get support / which Teams channel or ticket?"
- `Docusaurus-PlatformOverview.md` → *Getting support*.

---

## Disambiguation pairs (when two files seem to overlap)

| Files that look similar | How to choose |
|---|---|
| `Docusaurus-CloudPlatformAPI.md` vs `Docusaurus-ServiceArchitecture.md` | **CloudPlatformAPI** = the *reference catalog* (endpoints, auth, ingress per service). **ServiceArchitecture** = the *engineering how-to/architecture* for Authorization, Search, Webhooks, Eventing, CSD. "What endpoint?" → API catalog. "How do I build/integrate it?" → ServiceArchitecture. |
| `Docusaurus-ClientApps.md` vs `Docusaurus-OpsApps.md` | **ClientApps** = applications customers use (Admin Center, App Directory, CAPM, profiles, CSD). **OpsApps** = Tyler-staff ops apps (Audit Center, Authorization Config). |
| `Docusaurus-ClientApps.md` (Admin Center → Identity Workforce config) vs **Identity agent** | ClientApps covers the Admin Center *UI workflow* for configuring identity. Deep identity protocol/federation/credential-template questions → **Identity agent**. |
| `Docusaurus-ProductSystemReg.md` vs **Ops Center agent** | ProductSystemReg covers the Blueprint product-registration concepts + `tcp-product-catalog` GitOps workflow. The Ops Center *UI* for licensing/availability/verification → **Ops Center agent**. |
| `Docusaurus-PlatformOverview.md` glossary vs any deep file | Glossary = quick term definitions. For the actual workflow/architecture behind a term, route to the relevant deep file. |

---

## Cross-domain pointers (hand off to a specialized agent)

| If the question is about… | Hand off to |
|---|---|
| Ops Center workflows, org/workspace/product lifecycle in Ops Center, CRM customer identifiers, Ops Center permissions/telemetry | **Ops Center agent** — https://docs.tylerdev.io/app-guides/ops/ops-center/overview/ |
| Support Access Center / SAC — requests, approvals, groups, extensions, the support-access-revoked flow | **SAC agent** — https://docs.tylerdev.io/ops/support-access-center/ |
| Identity — Identity Workforce/Community, Gateway, Workforce Direct/Managed/Delegated, federation, credential templates, login/token flows | **Identity agent** — https://docs.tylerdev.io/identity |

Note: SAC-/Identity-related **APIs** (e.g., `tcp-support-access-center-api`, `tcp-login-security-api`, the `tid-*` services) still appear as **catalog entries** in `Docusaurus-CloudPlatformAPI.md` because they're API-reference docs in the Blueprint architecture section — but for *conceptual/workflow* questions, hand off to the specialized agent.

---

## What this corpus does NOT cover

Be honest when asked about these:
- **Deep Ops Center, SAC, or Identity guidance** — those have dedicated agents (hand off).
- **Per-product customer-facing user guides** (e.g., how to use Enterprise ERP) — this is platform/Blueprint content, not product feature docs.
- **Pricing, licensing terms, contracts** — those live in CRM/sales tools.
- **Content behind stub pages** — Audit Center, Authorization Config, most Status Page & SLA pages, and several product-system-reg pages are stubs in the source. The relevant files flag this; do not invent details. Offer the live Blueprint URL so the user can check for newer content.

---

## Naming convention legend

| Prefix | Source | What it means for the chatbot |
|---|---|---|
| **`Docusaurus-`** | Tyler Blueprint Docusaurus (`docs.tylerdev.io`) | Tyler-internal but publicly addressable. The structured docs site for product/platform engineering. Live URL works for anyone with the link; it's the canonical source for currency. |
| (future) `Conf-`, `GitHub-`, `Training-`, `Misc-` | Confluence / GitHub / training assets / bookmark catalog | Add consistent with the parent project conventions as new sources are distilled into this folder. |

All current files are `Docusaurus-` distillations of the Blueprint docs that don't fall under the three specialized-agent paths.

---

## Operating principles for the chatbot

1. **Read this file first.** Decide hand-off vs answer-here before retrieving deeper.
2. **Hand off the three specialized domains** (Ops Center, SAC, Identity) with the agent name + keywords + URL. Don't try to answer deep questions in those areas from this corpus.
3. **Cite the file you're answering from** (e.g., "per `Docusaurus-CloudPlatformAPI.md`…").
4. **Surface URLs verbatim** — Blueprint doc links, ticket links, Teams channels. Don't guess them.
5. **Ground term definitions in the glossary** (`Docusaurus-PlatformOverview.md`); surface disambiguation pairs for ambiguous terms ("client", "admin", "environment vs workspace").
6. **Flag stubs honestly.** Where a file notes the source page is a stub / "content coming soon," say so and offer the live Blueprint URL rather than inventing detail.
7. **Internal-audience caution.** Most of this is Tyler-internal operational/engineering content (especially `Docusaurus-DevOps.md` and `Docusaurus-Security.md`) — not customer-facing.

---

## Index hygiene

Update this file whenever a file in `Knowledge-BP-General/` is added, removed, or substantially restructured — and keep the **specialized-agent hand-off table** accurate (today: exactly three agents — Ops Center, SAC, Identity). A stale start page actively misleads the chatbot. Keep the catalog to one line per file.
