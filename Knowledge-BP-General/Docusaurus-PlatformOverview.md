# Tyler Cloud Platform — Orientation, Specialized-Agent Routing, and Canonical Glossary

Source: Docusaurus — Tyler Blueprint (`docs.tylerdev.io`): *Get Started* (`docs/get-started/**`, slug `/get-started`), *App Guides overview* (`docs/app-guides/overview`, slug `/app-guides`), *API Overview* (`docs/architecture/overview`, slug `/architecture`), *Platform Overview* (`docs/platform-architecture/overview`, slug `/platform-architecture`), and *Support* (`docs/support/support-channels/identity-support`, slug `/support`).
Domain: Blueprint General — Tyler Cloud Platform / Blueprint docs not served by a specialized Foundry agent.
Audience: Tyler product teams, platform/operations engineers, and anyone orienting to the Tyler Cloud Platform (TCP) and the Tyler Blueprint documentation site. This is the **first file the BP-General Foundry agent should ground itself in**.

**This is the orientation + glossary file for the BP-General corpus.** It answers "what is the platform / what does this term mean / which specialized agent should I go to?" and routes everything else to the deeper companion files.

**Companion documents (this folder):**
- `_START_HERE.md` — the routing guide for the whole BP-General corpus (read first).
- `Docusaurus-ClientApps.md` — Admin Center, App Directory, CAPM, Community Launcher, Community/Workforce Profile, Community Services Directory.
- `Docusaurus-OpsApps.md` — the Ops app family (Audit Center, Authorization Config) for Tyler staff.
- `Docusaurus-CloudPlatformAPI.md` — the TCP/TID service-API reference catalog.
- `Docusaurus-ServiceArchitecture.md` — Authorization, Search, Webhooks, TCP Eventing, Community Service Directory architecture.
- `Docusaurus-DevOps.md` — Datadog, Harness, Terraform/IaC, AWS infrastructure, disaster recovery, runbooks.
- `Docusaurus-Security.md` — RDS IAM auth, Akeyless, vulnerability scanning, WAF rules.
- `Docusaurus-ProductSystemReg.md` — product registration, licensing, customer onboarding.
- `Docusaurus-AlignedReleases.md` — Aligned Releases.
- `Docusaurus-StatusPageAndSLA.md` — Status Page & SLA tracking.

---

## How to use this guide (quick decision guide)

| If the user wants to… | Go to section |
|---|---|
| Know which specialized Foundry agent to use / what agents exist | **Specialized Foundry agents — when to hand off** |
| Understand the Tyler 2030 / Cloud Living strategy | **Cloud Living and Tyler 2030** |
| Understand what TCP (Tyler Cloud Platform) is and does | **What is the Tyler Cloud Platform (TCP)?** |
| Understand the platform applications (Admin Center, Ops Center, SAC) at a glance | **Platform applications at a glance** |
| Understand Client vs Operations application types | **Client vs Operations applications** |
| Resolve a Tyler term or abbreviation | **Canonical glossary** |
| Find how to get support / which channel or ticket | **Getting support** |
| Go deep on a specific product/API/service | route to the relevant companion file (see `_START_HERE.md`) |

---

## Specialized Foundry agents — when to hand off

> **This is the most important routing decision for this agent.** Tyler runs **three specialized Foundry agents** in addition to this general Blueprint agent. When a user's question is squarely about one of these three domains, **recommend the dedicated agent** (and give the live Blueprint URL for that domain) instead of answering from this general corpus — the specialized agents carry far deeper, curated content for their area.

**Question: "What specialized agents are available?"** → There are **three** specialized Foundry agents:

| Specialized agent | Use it when the question is about… (trigger keywords) | Where to point the user (Blueprint URL) |
|---|---|---|
| **Ops Center** | "**Ops Center**", organization/workspace lifecycle in Ops Center, product licensing & activation in Ops Center, org import/create wizards, identity tiers as shown in Ops Center, CRM customer identifiers, Ops Center permissions/telemetry | https://docs.tylerdev.io/app-guides/ops/ops-center/overview/ |
| **Support Access Center (SAC)** | "**Support Access Center**", "**SAC**", time-bound Tyler-staff access to customer installations, SAC groups, support access requests/approvals/extensions, the support-access-revoked flow | https://docs.tylerdev.io/ops/support-access-center/ |
| **Identity** (managed separately) | "**Identity**", "**Identity Workforce**", "**Identity Community**", "**Gateway**" / Workforce Direct / Managed / Delegated, federation setup, credential templates, login/token flows, the TID services | https://docs.tylerdev.io/identity |

**Everything else about the Tyler Cloud Platform / Blueprint is covered here in BP-General** — the client and ops applications, the TCP/TID API catalog, service architecture (Authorization, Search, Webhooks, Eventing, CSD), DevOps (Datadog, Harness, Terraform, AWS infra, DR, runbooks), platform security, product/system registration, Aligned Releases, and Status Page & SLA.

**How to phrase a hand-off:** Briefly answer any general-context part of the question, then say something like: *"For detailed [Ops Center / Support Access Center / Identity] guidance, there's a dedicated Foundry agent — see [URL]."* It is fine to define a term (e.g., what "Workforce Direct" means — it's in the glossary below) without handing off; hand off when the user needs **workflows, configuration, or deep how-to** in one of the three specialized domains.

---

## Cloud Living and Tyler 2030

**Source:** *Get Started > Cloud Living* — https://docs.tylerdev.io/get-started

Tyler's "One Tyler Cloud Living" strategy underpins the company's goals into 2030.

**Tyler 2030 — five pillars of growth** (shared with investors May 2023): (1) leverage the strong client base; (2) expand into new markets; (3) complete the cloud transition; (4) grow the payments business; (5) create one unified, connected Tyler ("One Tyler").

**Cloud Operations — three phases:**
- **Phase 1 (in progress):** Transition client environments from Tyler data centers to AWS.
- **Phase 2 (target Jan 2027):** Adopt a *cloud operating model* — a single release stream controlled by Tyler for net-new customers/installs.
- **Phase 3 (target Jan 2030):** Consolidate existing clients and environments into the single-release-stream model.

**One-Tyler technology standards** (OneTyler-invested, common across products):
- **Identity Management** — Tyler Identity (TID). *All Tyler cloud products use TID as a primary or integrated identity solution.* → deep content: **Identity specialized agent**.
- **SaaS Control Plane** — Tyler Cloud Platform (TCP) centralizes information about Tyler's software solutions and environments.
- **APIs** — a discoverable, documented, versioned OpenAPI-rich shared-services ecosystem (see `Docusaurus-CloudPlatformAPI.md`).
- **Data & Insights** — target primary data/reporting/analytics solution by 2030.
- **Self-Service Tooling** — Ops Center. → deep content: **Ops Center specialized agent**.

**OneTyler shared services** product teams can leverage: Identity (Identity Workforce, Community Access), App Suite (Workforce App Directory, Community Services Directory), Admin Center (user management, identity config, org/workspace config, admin apps, user groups), Ops Center (org/workspace management, product registry, systems registry, licensing & activation), and Forge (design system + UI components).

---

## What is the Tyler Cloud Platform (TCP)?

**Source:** *Get Started > Platform Overview* — https://docs.tylerdev.io/get-started/platform-overview/platform-overview

TCP (also historically called the **SaaS Control Plane**, the **Tyler Ecosystem**, or **Portico** — "Portico" is deprecated in customer communications but persists in the `tylerportico.com` domain) provides foundational functionality to manage **customers, products, and a customer's identity configuration** in Tyler's SaaS cloud environments, centrally. TCP is Tyler's **PaaS** for product teams to build cloud-native applications on shared constructs and services while adhering to Tyler branding and security standards.

TCP is foundational to upcoming Cloud Living functionality: **Identity, Aligned Releases, Status Pages, and SLA tracking.**

**Core feature areas:**
- **Product Management** — register products (product catalog + navigation), track what each customer has **licensed** and where the product is **available** (per environment/tenant/workspace). → `Docusaurus-ProductSystemReg.md`.
- **Customer Operations** — manage Organizations (customers), Workspaces (tenants/environments), and shared assets like Branding; a system of record correlating customer data across Tyler cloud systems. → `Docusaurus-ProductSystemReg.md`; org/workspace ops in **Ops Center agent**.
- **Identity & User Management** — Tyler Identity (TID) in three flavors: **TID Community (TID-C)**, **TID Workforce (TID-W)**, and **TID Direct (a.k.a. TID Gateway)**. Centralized Users and User Groups reusable across products. → deep content: **Identity specialized agent**.

---

## Platform applications at a glance

**Source:** *Platform Overview > Platform Applications*

- **Admin Center** — centralized administrative experiences for customer IT and solution administrators. Integration guide: `Docusaurus-ClientApps.md` and https://docs.tylerdev.io/app-guides/client/admin-center/overview/
- **Ops Center** — highly scalable Tyler cloud operations (org/workspace/product management). → **Ops Center specialized agent**, https://docs.tylerdev.io/app-guides/ops/ops-center/overview/
- **Support Access Center** — lets Tyler support personnel request access (with customer approval) to customer products for troubleshooting/support. → **SAC specialized agent**, https://docs.tylerdev.io/ops/support-access-center/
- **Tyler Forge** — Forge Design System + Forge Components for UI consistency. Getting started: https://forge.tylertech.com/get-started

---

## Client vs Operations applications

**Source:** *App Guides > Clients and Operations* — https://docs.tylerdev.io/app-guides

Tyler applications fall into two broad categories:

- **Client applications** — used by Tyler's clients (licensed to them). Tyler staff sometimes use them *on behalf of* a client, but they are not optimized for staff use; staff-only tasks belong in an ops application instead.
- **Operations ("ops") applications** — used by Tyler staff to manage client applications: provision, implement, upgrade, onboard, monitor, support, or offboard.

**OneTyler applications:**

| Client applications | Operations applications |
|---|---|
| Admin Center | Ops Center *(→ specialized agent)* |
| App Directory | Support Access Center *(→ specialized agent)* |
| Community Access Manager (CAPM) | Audit Center *(→ `Docusaurus-OpsApps.md`)* |
| Community Profile | Authorization Config *(→ `Docusaurus-OpsApps.md`)* |
| Community Services Directory (CSD) | |
| Workforce Profile | |

Client-app detail lives in `Docusaurus-ClientApps.md`. Ops-app detail (excluding Ops Center & SAC) lives in `Docusaurus-OpsApps.md`.

---

## Getting support

**Source:** *Support > Support for Tyler Identity* — https://docs.tylerdev.io/support

The Blueprint support page is currently framed around **Tyler Identity** support, but the channels are broadly useful for the cloud ecosystem. Two main avenues:

**1. Help Desk / service-desk requests (TCP service desk)** — the most common, effective route. Common requests: a Client Credentials Flow (CCF) client + secret for service-to-service auth; a Web/Mobile client for login auth; creation of a new organization for a customer; assistance with authentication or integration issues; creation of a new federation between the Gateway and an external IdP. Submit via **Ops Center Related Tickets and Permissions**: https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386600308/Tyler+Cloud+Platform+TCP+Ops+Center+Related+Tickets+and+Permissions

**2. Microsoft Teams channels** (all under the **OneTyler Collaboration** team):
- **Cloud Platform Community** — anything about the cloud ecosystem: https://teams.microsoft.com/l/channel/19%3A1e6bcc02bd3242a193bf9171a51a0395%40thread.tacv2/Cloud%20Platform%20Community?groupId=d9db441d-35fa-433c-8fe0-ff7fe5825d3c&tenantId=7cc5f0f9-ee5b-4106-a62d-1b9f7be46118
- **Identity Workforce** — integration/status/issues: https://teams.microsoft.com/l/channel/19%3Ae0289e84ce4a4bae841c55249970a491%40thread.tacv2/Identity%20Workforce?groupId=d9db441d-35fa-433c-8fe0-ff7fe5825d3c&tenantId=7cc5f0f9-ee5b-4106-a62d-1b9f7be46118
- **Identity Community** — Community Access identity questions: https://teams.microsoft.com/l/channel/19%3A15965417212e440eb01040eb39b67b2d%40thread.tacv2/Identity%20Community?groupId=d9db441d-35fa-433c-8fe0-ff7fe5825d3c&tenantId=7cc5f0f9-ee5b-4106-a62d-1b9f7be46118
- **TID Announcements** — policy changes, infra modifications, planned outages: https://teams.microsoft.com/l/channel/19%3Afdb47bfaf46847b58c5dcb6abda50cc3%40thread.tacv2/TID%20Announcements?groupId=d9db441d-35fa-433c-8fe0-ff7fe5825d3c&tenantId=7cc5f0f9-ee5b-4106-a62d-1b9f7be46118

**Confluence:** Total Tyler Integrations — Tyler Identity Workforce (operational support for the identity ecosystem and platform): https://confl.tylertech.com/pages/viewpage.action?pageId=160878970

**Still stuck on identity?** Contact **jason.howard@tylertech.com**.

For deep Identity questions, also point the user to the **Identity specialized agent** (https://docs.tylerdev.io/identity).

---

## Canonical glossary

**Source:** *Get Started > Terminology* — https://docs.tylerdev.io/get-started/terminology/terminology. This is the **authoritative Blueprint glossary** for the BP-General agent. Use it to resolve any Tyler term or abbreviation. (Defining a term here does **not** require a hand-off; hand off only for deep workflows in the three specialized domains.)

**Admin Center** — OneTyler-managed tool for centralized administrative experiences used by customer IT or solution administrators.

**Admin Apps** — a construct within Admin Center presenting links to administrative applications for products licensed to an organization (a centralized admin experience for customer Workforce Admins).

**API** — Application Programmatic Interface: a service with a publicly accessible interface that external products consume to access specific functionality, abstracting away direct data access for security.

**App Launcher (a.k.a. 9-box)** — the 9-dot icon in a Tyler application's omni bar for switching to a different application (not for navigation *within* an app).

**Application** — a functional entity (usually with a UI, but includes services) serving functionality to end users. Recognized types in the One Tyler Ecosystem:
- **Workforce app** — back-office users' daily business functions.
- **Admin app** — rarely used setup/configuration or in-product user authorization, for customer IT/solution admins.
- **Community app** — functionality for public users (residents, vendors, ex-employees, job applicants, etc.).
- **Ops app** — Tyler-staff-only; customers have no access; used by operations/support.
- **APIs and Services** — no direct UI; offer functionality to other apps/services.

**Application plane** — (SaaS) the hosting of applications/services serving regular non-administrative functionality to end users; contrast with **Control plane**.

**Authentication** — the "login"/"sign-on" process validating *who* the user is. Confers no product permissions. Tyler solutions: Identity Workforce and Community Access.

**Authorization** — the permissions a user has within specific product(s)/application(s) — *what* the user can do. Generally a product concern.

**Availability** — (SaaS Control Plane) provisioning of a product instance against a specific workspace; may also provision server-based solutions. Set in Ops Center. (Contrast **Licensing**.)

**Back-office user** — a customer end user performing back-office functions (full/part-time employees, contractors).

**Branding** — customizable UI guidelines (logos, naming, color scheme/CSS, fonts, design platform/philosophy) all customer- or public-facing apps adhere to, including workspace-specific branding services.

**Cloud** — computing infrastructure/resources hosted on the internet by a third party for rapid provisioning. Types: **IaaS** (virtualized hardware, e.g., AWS EC2), **PaaS** (ready-to-consume dev platform/services, e.g., TCP), **SaaS** (full software as a service, e.g., Virtual Court).

**Cloud-native** — a single instance/version of an application consumed by multiple customers with only virtual partitioning of config/data (e.g., Gmail); typically serverless, 24/7, no regular maintenance windows; customers have no direct data access.

**Community Access** — Tyler-managed cloud identity offering for public users enabling SSO across organizations; supports username/password or social login. → deep content: **Identity specialized agent**.

**Community Profile** — user profile associated with Community Access; manages cross-organization preferences (e.g., payment methods).

**Community Services Directory (CSD)** — a public portal for an organization's workspace listing all community services offered to public users. → `Docusaurus-ClientApps.md`.

**Community User** — a user authenticating through Community Access (independent of any organization); has a corresponding Community Profile.

**CI/CD (Continuous Integration/Continuous Deployment)** — cloud-native practice of frequent small low-risk releases; post-deployment release timing managed via feature flags.

**Control plane** — (SaaS) management of core constructs and shared services via tools/APIs; all administrative apps (Tyler staff and client admins) — e.g., Ops Center, Admin Center — managing Organizations, Workspaces, Licensing, Availability. Contrast **Application plane**.

**Customer or Client** — any entity with a business relationship with Tyler using its software/services. *Avoid "client" in technical contexts* (it can mean an "Identity Client"). A Customer/Client (business relationship) differs from an **Organization** (deployment entity).

**Customer Relationship Management (CRM) (a.k.a. "Tyler CRM")** — Tyler's Microsoft Dynamics CRM tracking leads, prospects, customers, ex-customers, contracts, etc. Key sub-terms: **Active customer** (Account status Active, ≥1 active product item, Direct/Indirect, Support-only = No); **Company Name** (legal name on the Account); **Customer Identifier** (auto-generated alphanumeric from Company Name + State + Country; stable once generated; required for an Organization to exist — deep content in **Ops Center agent**); **Support-only customer** (excluded from sales queries; used for Tyler-internal orgs); **Product Suite** / **Product Module** (sales categorizations; modules usually have their own SKU); **Active customer product items** (SKUs entitling the customer); **Customer Relationship Type** (Direct / Indirect / Former); **Hierarchy** (overlay connecting related Account records); **Case** (tracked activity — support tickets or deployment/implementation tasks).

**Deployment** — engineering activity delivering changes to a product/applications on infrastructure. Legacy: per-workspace install. Cloud-native: promotion through a pipeline affecting all customers. Distinct from **Release** (which controls availability).

**DevOps** — (cloud-native) the whole org from development to support as one integrated team; engineers rotate across the SDLC.

**Environment** — the infrastructure on which a product is hosted for a specific organizational use case; allows data segregation. Differs from **Workspace** (a logical construct unconcerned with the underlying infrastructure).

**Feature flags** — tags on features/changes to control release after deployment; can be a product-team process (e.g., Harness Feature Flags) or in-product config options. Require cleanup once features are widely available.

**Identity Provider (IdP)** — a software solution handling an organization's authentication (user store) using industry standards; enables SSO and central management of MFA, password policies, etc.

**Identity Workforce** — organization-managed cloud identity for back-office users enabling SSO across participating Tyler products. Two options: **Workforce Direct** (customer has a public-facing IdP to federate to and owns authentication responsibility — Tyler's default-favored option) and **Workforce Managed** (Tyler-managed back-office user store, currently Okta, for regulatory/business needs). → deep content: **Identity specialized agent**.

**Implementation** — configuration of a solution/product at a baseline "default" state; further customization is typically professional services.

**Knowledge Base (KB)** — centralized collection of FAQs, manuals, troubleshooting guides, runbooks.

**Licensing** — (SaaS Control Plane) an organization's eligibility to consume a product (done against an Organization). Followed by **Availability** (provisioning against a Workspace). A product must be both licensed and available to be usable.

**MFA / 2FA** — Multi-factor / two-factor authentication: requires more than a password (SMS, authenticator app, email, phone, etc.).

**One Tyler Ecosystem** — framework to centralize discovery and navigation of all Tyler solutions: TID for user store/authentication; centralized product registration/licensing/availability; centralized management of Organizations/Products/Users; centralized discovery/navigation; centralized Ops apps (Tyler) and Admin Center (customer); extensions to product-specific apps.

**Ops Center** — OneTyler-managed One Tyler Ecosystem tooling for centralized discovery/navigation to Tyler Ops applications; creates organizations/workspaces, licenses products to orgs, activates products on workspaces. → **Ops Center specialized agent**.

**Organization** — an entity provisioned a distinct copy of a Tyler product, intending to be its sole/primary administrator. Complex entities (states, large cities) may have multiple Organizations (departments/units). Each Organization has a unique identifier sourced from CRM and imported into Ops Center.

**Organization Admin** — a customer or Tyler user with administrative privileges for an organization (typically the customer IT admin/solution manager). Admin Center is built around these roles.

**Product** — a licensing entity (administrative/operational, not sales/marketing) containing one or more applications/services for a functional domain; may be sold in multiple SKUs. **Product Modules** (sub-domains, e.g., GL/Payroll/AP/AR) and **Product Tiers** (Basic/Standard/Professional/Enterprise) can be sub-licensing entities.

**Professional services** — tailoring a default product implementation to an organization's processes/goals (may include business-process review).

**Public user** — a Tyler-solution user who is not a back-office user (residents, job applicants, ex-employees, vendors, small businesses). Served by Community apps + Community Access.

**Release management** — a product-management function exposing deployed features/changes. In cloud-native, often distinct from deployment and managed via feature flags (docs, marketing, pre-release eval, early adopters, progressive rollout).

**Runbook** — a guide outlining steps to complete a task/procedure; manual, semi-automated, or fully automated. (See `Docusaurus-DevOps.md` for platform runbooks.)

**Sales Sheet** — a catalog of SKUs used by marketing/sales.

**Separation of concerns** — design paradigm segregating functionality for different personas into independent applications (the Ops/Workforce/Admin/Community app types), vs. monolithic apps gated by authorization.

**Server-based architecture** — a product/app running on traditional (physical/virtual) servers with an independent OS, dedicated DB, etc.; each layer maintained independently (high maintenance cost).

**Serverless architecture** — no traditional servers; lightweight self-contained containers run on standardized virtual infrastructure and scale dynamically.

**Service** — (technical) an API/micro-service serving functionality; (business) functionality offered by an external party without consumer setup/maintenance. **Micro-service** — a compact, narrow-function service enabling efficient, highly scalable infrastructure use.

**Single Pane of Glass (SPOG)** — a dashboard/platform combining data from multiple sources into one unified view.

**Single Sign-On (SSO)** — allows an organization's users to authenticate into any solution with one set of credentials in a single IdP; enables central account disablement.

**Stock Keeping Unit (SKU)** — an identifier for software licenses/products/services/bundles offered for sale, reflecting sales/marketing strategy.

**System** — physical or logical infrastructure on which products/services run, mappable to Organizations, Workspaces, and Products.

**Tenant** — a technical construct virtually segregating data/config on shared infrastructure; relates to Workspaces for most Tyler products.

**Tyler Cloud Platform (TCP, a.k.a. "Portico")** — Tyler's PaaS for product teams to build cloud-native apps on shared constructs/services with Tyler branding/security. "Portico" is the deprecated old brand name (persists in `tylerportico.com`).

**Tyler Ops User** — any Tyler staff who deploys, implements, manages, or supports a customer installation. Ops Center is designed for these roles.

**Vendor** — (Tyler business) an entity providing software/services to Tyler or its customers under a formal agreement; (in software) a public customer/user of Tyler's customers.

**Workspace** — a consistent **logical** construct grouping Tyler solutions regardless of each solution's hosting environment; associated 1:1 with a **tenant**. Some platforms (e.g., TCP) host all a customer's workspaces (prod/test/train/staging) in one environment with virtual data segregation.

**Workforce App Directory** — a directory of all Workforce applications a user can discover and navigate to. → `Docusaurus-ClientApps.md`.

**Workforce Profile** — a profile for an Identity Workforce user in the context of the organization (stores back-office user settings).

**Workforce User** — a user authenticating through the organization's Identity Workforce solution; has an associated Workforce Profile.

**Zero-trust computing paradigm** — an authorization model requiring all users be explicitly granted permissions, with no implied access.

---

## Notes for the chatbot

- **Audience:** Tyler-internal (product teams, platform/ops engineers). Blueprint (`docs.tylerdev.io`) is Tyler-internal but publicly addressable — surface URLs verbatim.
- **Hand-off discipline:** This corpus is the *generalist*. For deep **Ops Center**, **Support Access Center / SAC**, or **Identity** workflows, recommend the corresponding specialized Foundry agent and give its Blueprint URL (see *Specialized Foundry agents — when to hand off*). Defining a term from the glossary does **not** require a hand-off.
- **The "What specialized agents are available?" answer is canonical** — there are exactly three (Ops Center, Support Access Center, Identity), each with the trigger keywords and URL in the table above. Always include the keywords and the URL.
- **Glossary authority:** this file's glossary is the authoritative Blueprint glossary for the BP-General agent. When a user's term is ambiguous (e.g., "client" → Customer vs Identity Client; "admin" → Admin app vs Admin Center vs Org Admin), surface the relevant disambiguation.
- **"Portico" = TCP** (deprecated brand); don't use "Portico" in customer-facing language.
- **Empty source pages:** the *API Overview* (`/architecture`) and *Platform Overview* (`/platform-architecture`) landing pages are title-only stubs in the source — their substance lives in the companion files (`Docusaurus-CloudPlatformAPI.md`, `Docusaurus-ServiceArchitecture.md`, `Docusaurus-DevOps.md`, `Docusaurus-Security.md`). Don't fabricate landing-page content.
- **What this file does NOT cover:** deep how-to for any product/API/service — route to the relevant companion file via `_START_HERE.md`.
