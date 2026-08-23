# Operations Applications — Ops App Family, Audit Center, and Authorization Config

**Source:** Docusaurus — Tyler Blueprint (`docs.tylerdev.io`), paths:
`app-guides/ops/_ops-apps.md`, `app-guides/ops/_audit-center.md`, `app-guides/ops/_authorization-config.md`, `app-guides/overview/overview.md`

**Domain:** Blueprint General — Tyler Cloud Platform / Blueprint docs not served by a specialized Foundry agent.

**Audience:** Tyler staff only — operations engineers, support team members, and implementation staff. Customers do not have access to Ops applications.

**Companion documents:**
- `_START_HERE.md` — routing guide for the full BP-General corpus
- `Docusaurus-ClientApps.md` — client-facing applications (Admin Center, App Directory, CSD, Profiles)
- `Docusaurus-PlatformOverview.md` — platform concepts (orgs, workspaces, products)
- `Docusaurus-ProductSystemReg.md` — product and app registration
- `Docusaurus-Security.md` — security architecture
- **Ops Center agent** — for the primary Tyler operations application (org/workspace lifecycle, provisioning, implementation workflows): https://docs.tylerdev.io/app-guides/ops/ops-center/overview/
- **Support Access Center (SAC) agent** — for Tyler employee support access workflows: https://docs.tylerdev.io/ops/support-access-center/

---

## How to use this guide (quick decision guide)

| User intent | Go to section |
|---|---|
| What are the two categories of Tyler applications? | [Client vs. Operations applications](#client-vs-operations-applications) |
| What Ops apps does OneTyler build? | [OneTyler Ops applications](#onetylerelopment-operations-applications) |
| What is Audit Center? | [Audit Center](#audit-center) |
| What is Authorization Config? | [Authorization Config](#authorization-config) |
| Where is Ops Center documentation? | [Hand-off: Ops Center](#hand-off-ops-center) |
| Where is Support Access Center (SAC) documentation? | [Hand-off: Support Access Center](#hand-off-support-access-center) |

---

## Glossary

| Term | Meaning |
|---|---|
| Ops app / Operations application | Tyler-staff-only application for managing client environments (provisioning, support, monitoring, etc.) |
| Client application | Application licensed to customers; used by the customer (and sometimes Tyler staff on behalf of a customer) |
| OneTyler | Tyler's Corporate Development team — builds and maintains the platform apps covered here |
| Audit Center | Ops application for auditing/reviewing platform activity |
| Authorization Config | Ops application for configuring authorization settings on the platform |
| Ops Center | The primary Tyler ops application for org/workspace lifecycle management (has its own Foundry agent) |
| SAC | Support Access Center — ops application for managing Tyler employee access to customer environments (has its own Foundry agent) |

---

## Client vs. Operations applications

**Source:** https://docs.tylerdev.io/app-guides

Tyler Tech builds two categories of applications:

**Client applications** — Licensed to customers and used primarily by customers. If a task is only for Tyler staff to perform, it should be in an Ops application, not a client application.

**Operations (Ops) applications** — Used exclusively by Tyler staff to manage client applications. Typical users: operations engineers, support team members, implementation staff. Customers have no access to Ops apps.

---

## OneTylerelopment: client and operations applications

**Source:** https://docs.tylerdev.io/app-guides

OneTyler builds and maintains both categories:

### OneTyler Client applications

| Application | Brief description |
|---|---|
| Admin Center | Customer IT/admin app for authentication setup, user management, and workspace/product management |
| App Directory | Shows a user the applications they can access |
| Community Access Manager (CAPM) | Client tool to look up a public user's Identity Community account |
| Community Profile | Profile application for community (public-facing) users |
| Community Services Directory | Public-facing and staff-facing service listing directory |
| Workforce Profile | Profile application for workforce (internal) users |

For details on all client applications, see `Docusaurus-ClientApps.md`.

### OneTyler Operations applications

| Application | Brief description |
|---|---|
| Ops Center | Primary ops app for org/workspace lifecycle, provisioning, implementation — **has its own Foundry agent** |
| Support Access Center (SAC) | Ops app for managing Tyler employee access to customer environments — **has its own Foundry agent** |
| Audit Center | Ops app for auditing/reviewing platform activity |
| Authorization Config | Ops app for configuring platform authorization settings |

---

## Audit Center

**Source:** https://docs.tylerdev.io/app-guides/ops/audit-center

**Use when:** A Tyler staff member needs to review or audit activity in the Tyler Cloud Platform.

**Access:** Tyler staff only. Customers do not have access.

The Audit Center is an operations application for auditing and reviewing platform activity. (The Blueprint source file for Audit Center is a stub — detailed feature documentation is not yet published in the Blueprint docs at this source path.)

**Note:** For customer-facing sign-in and identity event logs (authentication activity visible to customers), see Admin Center > Sign-in Logs, covered in `Docusaurus-ClientApps.md`.

---

## Authorization Config

**Source:** https://docs.tylerdev.io/app-guides/ops/authorization-config

**Use when:** A Tyler staff member needs to configure authorization settings on the Tyler Cloud Platform.

**Access:** Tyler staff only. Customers do not have access.

Authorization Config is an operations application for configuring authorization settings on the platform. (The Blueprint source file for Authorization Config is a stub — detailed feature documentation is not yet published in the Blueprint docs at this source path.)

**Note:** For customer-facing authorization configuration (access control lists, role assignments), see Admin Center covered in `Docusaurus-ClientApps.md`.

---

## Hand-off: Ops Center

Ops Center is the primary Tyler operations application for managing the lifecycle of organizations, workspaces, products, and implementations on the Tyler Cloud Platform.

Ops Center has its own dedicated Foundry agent. Do not attempt to answer Ops Center questions from this file. Route to:

**Ops Center agent:** https://docs.tylerdev.io/app-guides/ops/ops-center/overview/

Keywords that indicate Ops Center: provisioning an org or workspace, activating a product, implementation tasks, onboarding a customer, managing org/workspace lifecycle, viewing platform-level operations dashboards.

---

## Hand-off: Support Access Center (SAC)

The Support Access Center (SAC) is the operations application through which Tyler employees request and manage temporary access to customer environments for support and implementation purposes.

SAC has its own dedicated Foundry agent. Do not attempt to answer SAC questions from this file. Route to:

**SAC agent:** https://docs.tylerdev.io/ops/support-access-center/

Keywords that indicate SAC: "support access", "Tyler employee access to customer", "access request", "temporary access", "SAC".

---

## Notes for the chatbot

1. **Tyler-staff-only:** All content in this file pertains to Ops applications accessible only by Tyler employees. If a customer is asking about Ops apps, clarify they do not have access and redirect them to the appropriate client application (e.g., Admin Center for sign-in logs or authorization).

2. **Stub sources:** Audit Center and Authorization Config source files in Blueprint are stubs with no detailed content published yet. Do not fabricate feature descriptions. Tell the user that detailed documentation is not yet available for these tools in Blueprint, and suggest they reach out to the relevant Tyler engineering or ops team directly.

3. **Ops Center hand-off is mandatory:** Any question about Ops Center features must be routed to the Ops Center Foundry agent at https://docs.tylerdev.io/app-guides/ops/ops-center/overview/ — do not attempt to answer from this file.

4. **SAC hand-off is mandatory:** Any question about Support Access Center must be routed to the SAC Foundry agent at https://docs.tylerdev.io/ops/support-access-center/ — do not attempt to answer from this file.

5. **What this file does NOT cover:** Ops Center workflows, SAC workflows, Identity platform internals, product registration mechanics, individual product administration, customer-facing workflows. Deep platform questions belong in `Docusaurus-PlatformOverview.md` or a specialized agent.

6. **App taxonomy is useful context:** The client vs. ops application distinction (and the OneTyler app list) is frequently useful context for orienting users who ask "what apps does Tyler's platform have?" or "where do I go to do X?" — use this file's taxonomy table as a routing aid.
