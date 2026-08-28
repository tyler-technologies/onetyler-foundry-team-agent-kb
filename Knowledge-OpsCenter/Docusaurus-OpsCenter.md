# Ops Center — Product & Process Guide

Source: Docusaurus — *OneTyler Blueprint, App Guides > Ops > Ops Center* (`docs/app-guides/ops/ops-center/**`)
Domain: Ops Center
Audience: Tyler operational staff (project managers, deployment, implementation, support, system managers, devops engineers) using Ops Center as part of their daily workflows.

This document covers the Ops Center tool: how to get access, what is on the dashboard, how to manage Organizations and Workspaces, how to license and activate Products, how to set up AD Agent accounts and Federations, how to use Bulk Licensing, telemetry, and the recent changelog highlights.

**Companion documents in this same Knowledge folder:**
- `Docusaurus-Terminology.md` — canonical definitions for TCP, organization, workspace, identity tiers, etc.
- `Docusaurus-TylerCRM.md` — how to prepare a valid Tyler CRM account record (prerequisite for creating customer orgs).
- `Docusaurus-OrgAdminInfo.md` — what an Org Admin is and how to source the client IT contact.
- `Knowledge-Shared/Conf-OneTylerTickets.md` — full catalog of OneTyler tickets and permissions (the chatbot should hand out direct links from there for access requests).

---

## How to use this guide (quick decision guide)

**If the user is asking one of the four Foundry starting prompts**, jump straight to *Starting prompts — quick answers* below. Those answers are self-contained and link out to the deeper sections when more detail is needed.

| If the user wants to… | Go to section |
|---|---|
| Get a direct answer to one of the four Foundry starting prompts | **Starting prompts — quick answers** |
| Find Ops Center URLs per environment | **Access — environment URLs** |
| Get access (basic) for themselves or a teammate | **Access — request a ticket** |
| Self-promote teammates in non-prod (TCPCI / TCPQA / localdev) | **Access — promote teammates** |
| Understand what's on the landing dashboard | **Dashboard** |
| Find / search an organization | **Organizations — list & search** |
| Understand identity tiers (WD / WM / Delegated) | **Organizations — Identity Workforce product tiers** |
| Create a customer org (Workforce Direct) | **Organizations — Import an organization** |
| Create a customer org (Workforce Managed) | **Organizations — file a ticket** (see `Knowledge-Shared/Conf-OneTylerTickets.md`) |
| Create an internal org | **Organizations — Create internal organization** |
| Use a Tyler-provided pre-created standard org for dev/test/training | **Standard organizations** |
| See org details / change contact / view admins | **Organization Details** |
| Add an Org Admin or self-promote | **Organization Details — Admins** |
| License a product to an org | **Product licensing (org) and availability (workspace)** |
| Make a licensed product available on a specific workspace | **Product licensing — availability step** |
| Create a non-prod workspace | **Workspaces — create** |
| Deactivate/delete an org or workspace | **Deactivating and deleting** |
| Set up the AD Agent account for a Workforce Managed org | **Add/Reset AD Agent account** |
| Set up or reestablish a federation | **Establish or reestablish federations** |
| View authentication logs | **Authentication logs** |
| Find product details / contacts / Ops Apps / registration JSON | **Product Registry** |
| Bulk-license a product across many orgs/workspaces | **Bulk Licensing** |
| Request additional Ops Center permissions | **Additional Permissions** |
| See production stats / dashboards | **Ops telemetry (AWS QuickSight)** |
| Find what was recently added to Ops Center | **Changelog highlights** |

---

## Starting prompts — quick answers

These are the canonical answers to the four **Foundry starting prompts** that users see when first interacting with the Ops Center agent. Each answer is self-contained; deeper detail lives in the sections that follow. **The chatbot should prefer these answers verbatim when the incoming question matches one of these prompts** — they are deliberately worded to start the conversation on the right foot.

### How do I get access to Ops Center?

Two-step process:

1. **Self-test first** — click the URL for your environment. A blank screen or a **403** means you don't have access yet:
   - TylerPortico (production): https://admin.tylerportico.com/portal/ops-center
   - TCPQA: https://admin.tcpqa.com/portal/ops-center
   - TCPCI: https://admin.tcpci.com/portal/ops-center
2. **For TCPCI / TCPQA / TylerPortico**, file the generic Ops Center access ticket: `https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3333/create/4133`. Select the matching environment from the **TCP Tool Selection** dropdown. Notes-field wording: `"Need access to Ops Center for <reason>"`. *(Same form 4133 is also used to request additional Ops Center permissions — federation management, +Import, AD Agent setup, Reestablish Federation, etc. — only the Notes-field wording varies. See `Knowledge-Shared/Conf-OneTylerTickets.md` for the full catalog.)*
3. **Non-prod shortcut** — in **TCPCI / TCPQA**, an existing Tyler Ops user on your team can promote you themselves (Ops Center → side menu → **Manage Tyler Ops users** → **+ Add Tyler Ops User**). **This shortcut is not available in TylerPortico** — production Tyler Ops users can only be added by the **OneTyler Engineering Services team**.

For ongoing formal support: the *Tyler Cloud Platform (TCP) | Ops Center Related Tickets and Permissions* Confluence page (https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386600308/). For informal support: the **CorpDev Collaboration** Microsoft Teams team — channels *Cloud Platform Community*, *Identity Workforce*, *Identity Community*.

See *Access — environment URLs*, *Access — request a ticket*, and *Access — promote teammates* for the full detail.

### How can I get access to a client's Admin Center?

The standard path is the **Client Admin Center access request** ticket:

- URL: `https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3333/create/4165`
- **Prerequisites:** the organization must already exist in Ops Center for the requested environment, and you must not already have access.
- After approval, expect up to **5 minutes** for access to take effect — a **clock icon** appears next to your name under Organization Details → Admins during the pending state; once it clears, you're live.
- **Fields to fill in:** Product team(s); **CRM Customer Identifier** (= the Org Key from Ops Center); Reason for Access (closest matching reason for external orgs); Customer email address (if requesting on a customer IT admin's behalf); Notes (justification; include the customer IT admin's first/last name if applicable).

**Alternative — self-promote in Ops Center (faster, but permission-gated):** OneTyler grants elevated *Promote / Remove yourself as Org Admin* rights to select Ops users whose roles require routine customer access. Managers of product ops teams can also be granted rights to add customer Org Admins and to let their direct reports self-promote (provided the report already has Ops Center access). If you've been granted these rights, you do this in-product under Ops Center → **Organization Details → Admins**. The canonical procedure is the **Tyler Cloud Platform (TCP) | Org Admin promotions (Admin Center access) — a Manager's guide** Confluence page (https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386629479/). Important: this self-promote flow does **NOT** use generic ticket form 4133.

See `Knowledge-Shared/Conf-OneTylerTickets.md` → *Client Admin Center access request* and *Org Admins* for full detail, and `Docusaurus-OpsCenter.md` → *Organization Details — Admins*.

### Where can I see the Identity Configuration details for a customer?

Open Ops Center for the relevant environment, search for the customer's Organization (by name or CRM Customer Identifier) on the Organizations list, and click into it. A customer's **Identity Configuration** is reflected across three places on the Organization Details page:

1. **Org Details — Basic details + Manage workspaces.** The basic details panel at the top shows the **Identity Tier** (Workforce Managed / Workforce Direct / Workforce Delegated). The **OnPrem Target** (Okta / Gateway) is a per-workspace property — reach it from the same Org Details page under **Manage workspaces** → *OnPrem target* column.
2. **Identity Workforce** (the *Identity Workforce* menu item / section in Org Details) — the tier-specific identity setup deep dive:
   - **Workforce Managed** — Administration URL, default authority, IdP federations, **Okta AD Agent pool info / Add/Reset AD Agent account / history**, **Reestablish federation** (with history).
   - **Workforce Direct** — IdP federations, **Establish new federation** (with history).
   - **Workforce Delegated** (Sub orgs) — a link points to the **Super** org, where the actual identity setup and authentication logs live.
3. **Authentication logs** — recent sign-ins for the org's users. Behavior differs **substantially** by tier (availability, retention, detail level, delay, activity types) — see the auth-logs comparison table under *Authentication logs* in this file.

Important gotchas to surface alongside the answer:

- **Identity Tier cannot be changed after org creation.** The only exception is the narrow UNINITIATED Workforce Direct → Workforce Managed conversion ticket (`…/create/4860`); any other tier change requires deleting and recreating the org.
- For **Workforce Delegated Sub orgs**, the identity setup and authentication logs live on the **Super** org — the Sub's page just links over.
- For conceptual depth on the tier model: `Docusaurus-Terminology.md` → *Identity Workforce* cluster. For step-by-step setup walkthroughs: *Establish or reestablish federations* and *Add / Reset AD Agent account* in this file.

### Where can I see Ops Center training and other useful guides?

**Primary answer — the single most important link, must be surfaced verbatim in any response to this question:**

https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386599613/Tyler+Cloud+Platform+TCP+Deployment

That URL is the **Tyler Cloud Platform — Deployment / Operational Training Hub** on Confluence. It is the umbrella page that hosts the **6-part operational training video series**, the **Q1 2026 slide deck**, the **handout PDF**, and pointers to operational support tickets and Tyler CRM access. **Effective until H1 2026 only** — bookmark the hub page, not individual assets, since content will change with new Identity features releasing later in 2026.

**The 6-part operational training video series — all 6 parts are operationally relevant** (linked from the hub URL above):

1. **Overview** — Tyler 2030 Pillars, OTCOM 14.3/14.4, the cross-sell story, suite-like experience, Tyler SaaS control plane.
2. **Basic Concepts** — vocabulary (app types, user types, identity tiers, Workforce Direct/Managed/Delegated, TCP vs non-TCP registration, Product/Org/Workspace, environments).
3. **Process Overview** — sales-side CRM 4-point active-customer criteria + the ops-side Step 1 / 2A / 2B / 2C / 3 model.
4. **Typical Process Demo** — live walkthrough of Part 3 in the actual tools.
5. **Cloud Tools Demo** — live demo of Ops Center, Admin Center, Workforce App Directory, Community Launcher, CAPM.
6. **Support Overview, Access & Resources** — distributed support model, issue routing rules, forums to join.

The conceptual parts (1, 2, 3, 6) have been distilled into narrative summaries inside this Knowledge corpus at `Training-OpsCenterOperations.md` for fast retrieval. **Parts 4 and 5 are equally operational — they are live-screen-recording walkthroughs of the same operations content shown in action. They are not distilled because live demos do not transcribe usefully; to learn that content, watch the videos directly on the training hub URL above.** The companion file `Training-WorkforceManagedToDirectMigration.md` distills the separate WM → WD migration training.

**Individual operational guides on Confluence — start with the primary training hub URL (repeated as the first bullet so RAG retrieval cannot drop it); the remaining items are task-specific guides:**

- **Tyler Cloud Platform — Deployment / Operational Training Hub** (PRIMARY — same URL as the top of this answer, repeated here so it survives chunking) — https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386599613/Tyler+Cloud+Platform+TCP+Deployment
- **Ops Center Related Tickets and Permissions** — https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386600308/
- **Import an organization (Demo)** — https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386630359/
- **Org Admin promotions (Admin Center access) — a Manager's guide** — https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386629479/
- **Ops Center — Setup AD Agent User Account** — https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386599721/
- **Reestablish Federation Demo** — https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386625934/
- **CRM Customer Identifiers** (deep technical reference) — https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386599914/

**Beyond Confluence:**

- **Blueprint Docusaurus** (https://docs.tylerdev.io/) — public-facing engineering docs; ~160 entries across 9 sections (Cloud Platform API, Identity, Eventing, Search, Permissions, Community, etc.). Full catalog in `Misc-Links.md`.
- **Tyler Community** — customer-facing video guides (federation setup, AD Sync with Okta AD Agent, etc.).

---

## Overview

Ops Center manages the core constructs of **Organizations**, **Workspaces**, **Products**, and **Systems** within the One Tyler Cloud Living Ecosystem and the composite relations between these constructs. It is designed for Tyler's **operational team members**, including (but not limited to) project managers, deployment, implementation, support, and systems managers, as part of their daily workflows.

Content under Ops Center includes integration guides, change logs, and user guides (both *product* and *process*).

---

## Access — environment URLs

| Environment | URL to access Ops Center |
|---|---|
| localdev | http://admin.localdev.tcpci.com/portal/ops-center |
| TCPCI | https://admin.tcpci.com/portal/ops-center |
| TCPQA | https://admin.tcpqa.com/portal/ops-center |
| TylerPortico (Production) | https://admin.tylerportico.com/portal/ops-center |

**Self-test first:** Click the URL for the environment you want. If you don't see any information or get a **403** error, you don't have access yet.

## Access — request a ticket

For **localdev**, access is part of building the local developer environment — nothing to request.

For **TCPCI / TCPQA / TylerPortico**, submit an Ops Center access request via the *Ops Center Related Tickets and Permissions* portal. Specifically, this is the generic Ops Center access form `…/create/4133` — see `Knowledge-Shared/Conf-OneTylerTickets.md` for the exact URL and the Notes-field wording.

When filing, **select the environment in which you need access** (TCPCI, TCPQA, TylerPortico).

For ongoing formal support, see the *Ops Center Related Tickets and Permissions* Confluence page: https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386600308/Tyler+Cloud+Platform+TCP+Ops+Center+Related+Tickets+and+Permissions

For informal support, use the channels under the **CorpDev Collaboration** Microsoft Teams team:
- **Cloud Platform Community** channel
- **Identity Workforce** channel
- **Identity Community** channel

## Access — promote teammates (non-prod only)

In **localdev, TCPCI, and TCPQA**, you are encouraged to promote other team members into Ops Center yourself. **In TylerPortico (production), only the OneTyler Engineering Services team can add Tyler Ops users.**

Steps:

1. Ops Center → side/hamburger menu → **Manage Tyler Ops users**.
2. Search by name or email to check if the user is already a Tyler Ops user.
3. If not found, click **+ Add Tyler Ops User**.
4. Search under the **Existing user** tab for the email. If they aren't already in the profile store, switch to the **New user** tab and create the record (First/Last/Email), then **Save & Close**.

---

## Dashboard

The dashboard is the starting point of the Ops Center experience. It provides links to various Ops Center sections, to external Ops tools, and to common ops tasks. Commonly accessed links on the dashboard:

- **Organizations** — Listing of organizations and their details.
- **Products** — Listing of products that can be licensed, Product Ops Apps, and registration info.
- **Systems** — Listing of Tyler systems serving client-facing functionality.
- **Client Admin Center access request** — Request access to an organization's Admin Center for yourself or for a client IT admin (users with AC access are "Org Admins").
- **New Organization request** — For product deployment/implementation teams to request a new organization.
- **Community Access Profile Manager (CAPM) access request** — Request CAPM access for Tyler staff to troubleshoot community resident accounts. **Note:** This cannot be used to request access for *client* staff to *their* CAPM tool — that is done by the client Org Admin through Admin Center.
- **Ops Center access request (or additional permissions)** — To get access to this tool (typically for others, e.g. managers requesting it on behalf of staff).

For full ticket details and exact URLs, see `Knowledge-Shared/Conf-OneTylerTickets.md`.

---

## Organizations — list & search

When you first land on Ops Center, you see a list of Organizations. You can also reach this view from Ops Center → Hamburger menu → **Manage organizations**. Search by **Customer ID** to find a specific client, then drill down for additional details.

## Organizations — Identity Workforce product tiers

Each organization is configured with one of these Identity Tiers. **This cannot be changed after the organization is created** — to change the tier, the org must be deleted and recreated. (Limited exception: an UNINITIATED Workforce Direct org can be converted to Workforce Managed via a specific ticket — see `Knowledge-Shared/Conf-OneTylerTickets.md`.)

- **Workforce Managed** — Provisioned an Okta user store. The org can federate to its IdP and add users outside the IdP.
- **Workforce Direct** — Directly federated into the organization's IdP. All users must reside in the org's IdP unless the user is part of a global (B2B) domain.
- **Workforce Delegated** — A special variant of Workforce Direct that delegates identity and user setup to another org (the "Super") it depends on. Orgs using this setup are called "Sub" orgs. Only the Super can set up federations and add users. Sub orgs can only add users that already exist in the Super. Both Super and Sub orgs can have their own solutions and grant access independently. Deleting a user in the Super removes them from all Sub orgs; deleting in a Sub only affects that Sub.

## Organizations — when OneTyler needs to create the org (vs self-service)

OneTyler limits who can create organizations to ensure callers understand the prerequisites: a well-formed CRM record and the org's IT admin contact info. **Orgs in these cases must be requested through OneTyler support** (i.e., a ticket, not self-service):

- Organizations with **Workforce Managed** Identity Tier.
- Organizations for internal uses that will not have well-formed CRM records (file a ticket OR use the Create internal feature if you have that permission).

For self-service paths, see Import and Create internal below.

## Organizations — Import an organization (self-service for Workforce Direct/Delegated)

**As of 4/1/26, Ops Center automatically creates customer organizations** when CRM account records become sales-enabled (see *Tyler CRM* doc for what "sales-enabled" / "valid record" means). The need to manually use Import is therefore greatly reduced. Automatically-created orgs do **not** have customer contact information or domains set — to add a technical contact and set their userid domain as the org domain, go to **Organization Details > Admins** and use the **"Use as technical contact"** option when adding an Org Admin. These auto-created orgs are **Workforce Direct**. To change the Identity Tier, use the convert-org ticket (see `Knowledge-Shared/Conf-OneTylerTickets.md`).

The **+Import (an organization)** option remains available in Ops Center for users with the requisite permissions. Criteria for using Import:

- Identity Workforce product tier is **Workforce Direct** or **Workforce Delegated**.
- Non-Tyler-Tech Org Admin (see `Docusaurus-OrgAdminInfo.md`).
- CRM customer account record meets:
  - Status: **Active/Approved**.
  - Relationship type: **Direct** or **Indirect**.
  - At least one **active customer product item** with status Active.
  - **Support-only Customer = No.**
  - Has a **CUSTOMER IDENTIFIER** with **Business Use = Default** (see `Docusaurus-TylerCRM.md`).

### Import wizard — step by step

1. **Access the Import** — From the Organizations list page, click **+Import (an organization)**. If you don't have permission, you'll see a no-access message; request permission via the generic Ops Center permission ticket (see `Knowledge-Shared/Conf-OneTylerTickets.md`).
2. **Select Identity Setup** — Pick **Workforce Direct** for most orgs. (If the customer opted for **Workforce Managed**, you cannot use this wizard.) **Workforce Delegated** is for special cases: software installed in multiple sub-orgs with identity/users maintained at a higher super org (e.g., a school district with a global email domain across multiple schools, or a city across its departments). Note: When only 1–2 sub-orgs are involved and the Super isn't administering any Tyler solutions, prefer Workforce Direct with separate federations.
3. **Look up CRM Customer** — Enter the **CRM Customer Identifier (Business Use=Default)** in the CRM ID Lookup tab. If the record fails validation, errors block you from proceeding.
4. **Review imported info** — Confirm you are importing the correct account record. If anything is wrong, cancel and have your product sales team correct CRM.
5. **(Workforce Delegated only) Select the Super org** — Pick a valid existing org that is not itself Workforce Delegated.
6. **Customer Org Admin + magic link** — Enter the customer IT contact info (see `Docusaurus-OrgAdminInfo.md` for sourcing). The Org Admin is also normally the federation-setup contact. Select **"Send magic link on org creation"** so they receive an email with a federation-setup link. (Magic link does **not** apply if you selected Workforce Delegated; the specified Org Admin will also be added to the Super if not already present.) Alternatively, select **"Skip Org Admin setup"** and add them later via Add an Org Admin (with **"Use as technical contact"** to also designate the technical contact). Then use **Setup new federation** under Identity Workforce to send magic links.
7. **Review summary, Save & close** — The org is created and the **production workspace is automatically created**. (For Workforce Delegated, the Super org will also be shown.)

## Organizations — Create internal organization

The **+Create internal (organization)** option lets Ops Center users with the requisite permissions create internal orgs without needing a backing CRM record. Users with the permission can **Create, Deactivate, and Delete any internal organization** and its workspaces.

### Create-internal wizard — step by step

1. **Access** — From the Organizations list page, click **+Create internal**. (Permission gated; request it via the [**Ops Center Related Tickets and Permissions**](https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386600308/Tyler+Cloud+Platform+TCP+Ops+Center+Related+Tickets+and+Permissions) Confluence page → *Orgs* → **Ops Center Access or Additional Permissions** — see also `Knowledge-Shared/Conf-OneTylerTickets.md`.)
2. **Select Identity Setup** — Same options as Import (Workforce Direct typical; Workforce Delegated for special cases like a group/division with an IdP for internal demo users plus dependent internal orgs).
3. **Enter Org Key + Org Title** — Manually enter both. Org Key format: `{3-char division/group code}{purpose code}{label}`, max 50 chars total. Follow internal-org naming conventions (Confluence: *Internal Orgs creation in Ops Center → Internal-Org-Naming-Construct*, `/wiki/spaces/SPY/pages/407176942/`).
4. **(Workforce Delegated only) Select Super org** — Must be a valid existing internal org that is not itself Workforce Delegated.
5. **Org Admin + magic link** — Same as Import. The contact here is a Tyler staff or demo user.
6. **Review summary, Save & close** — The org is created and the production workspace is automatically created.

## Standard organizations (OneTyler-provided for dev/test/training)

**OneTyler intentionally limits org creation in TCPCI and TCPQA** to force product teams to learn to coexist on the same Organization and Workspace, reflecting real-world client experience. OneTyler provides standard demo/dev/test "customers" with corresponding CRM records and Tyler Deploy tenants. Two more (`uat`, `impl`) exist for high-quality data used for global/holistic testing/training.

| Environment | Standard "Customer" IDs (use only these unless one was specifically provisioned for your team) | Source |
|---|---|---|
| localdev | `tide-broker` | Part of local dev setup |
| TCPCI | `demo`, `dev`, `test`, `uat`, `impl` | Standard 5 from OneTyler, sourced from CRM |
| TCPQA | `demo`, `dev`, `test`, `uat`, `impl` | Standard 5 from OneTyler, sourced from CRM |
| TylerPortico | `demo`, `testinprod` | Standard 2 from OneTyler, sourced from CRM |

**If you need your own dedicated org with valid business reason:** use **Create internal** to create a Workforce Direct/Delegated org. **If you need an Okta-tenant-based org** with a strong business justification, file a ticket on the Ops Center Tickets portal.

### Recommended usage of the standard orgs

| Org | Recommended use |
|---|---|
| `demo`, `dev`, `test`, `testinprod` | Dev / test / unscripted / casual use |
| `uat`, `impl` | **High-quality scripted testing/training data — do NOT junk up.** |

### Standard org reference table (CRM, Okta, Auth URLs, Admin Center)

| Property | demo | dev | test | uat | impl | testinprod |
|---|---|---|---|---|---|---|
| **Primary use** | Default/casual (consistent across all 3 envs) | Developer | Test/QA | **Scripted high-quality testing** | **Scripted high-quality training** | Testing in production |
| **CRM Account record (numeric)** | 455438 | 462012 | 462010 | 462014 | 462016 | 456050 |
| **Okta tenant — TCPCI/TCPQA** | tyler-demo.tylerpreview.com | tyler-dev.tylerpreview.com | tyler-test.tylerpreview.com | tyler-uat.tylerpreview.com | tyler-impl.tylerpreview.com | — |
| **Okta tenant — TylerPortico** | tyler-demo.okta.com | — | — | — | — | tyler-testinprod.tylerpreview.com |
| **Auth URL — TCPCI/TCPQA** | https://tyler-demo.oktapreview.com/oauth2/ausz5pmg5sgJT1GgD0h7 | https://tyler-dev.oktapreview.com/oauth2/aus1806m6jdqMdosI0h8 | https://tyler-test.oktapreview.com/oauth2/aus1807emvrm9cZfa0h8 | https://tyler-uat.oktapreview.com/oauth2/aus1806twx2B6ehW60h8 | https://tyler-impl.oktapreview.com/oauth2/aus18072b8vApHHLp0h8 | — |
| **Auth URL — TylerPortico** | https://tyler-demo.okta.com/oauth2/aus9kq8734pqUu6Eu357 | — | — | — | — | https://tyler-testinprod.okta.com/oauth2/aus9nzw1hgTlBH1nD357 |
| **Admin Center — TCPCI** | https://demo-admin.tcpci.com/org/admin-center | https://dev-admin.tcpci.com/org/admin-center | https://test-admin.tcpci.com/org/admin-center | https://uat-admin.tcpci.com/org/admin-center | https://impl-admin.tcpci.com/org/admin-center | — |
| **Admin Center — TCPQA** | https://demo-admin.tcpqa.com/org/admin-center | https://dev-admin.tcpqa.com/org/admin-center | https://test-admin.tcpqa.com/org/admin-center | https://uat-admin.tcpqa.com/org/admin-center | https://impl-admin.tcpqa.com/org/admin-center | — |
| **Admin Center — TylerPortico** | https://demo-admin.tylerportico.com/org/admin-center | — | — | — | — | https://testinprod-admin.tcpci.com/org/admin-center *(see note)* |

**Tyler Deploy listing:** All portals for these orgs are under the **TCP Ecosystem** tool/project in TD's side navigation.
- For TCPCI/TCPQA, search `Tyler Cloud Platform Demo Portals - OneTyler - <org>` in `dev.tylerdeploy.com` (→ tcpci) or `internal.tylerdeploy.com` (→ tcpqa).
- For TylerPortico, search `Tyler Cloud Platform Demo Portals - OneTyler - <org> - TX 999999990000` in `tylerdeploy.com`.

---

## Organization Details

The organization-details view shows details about an org and lets you perform several actions.

### Title row
- Organization Name (with Identifier).
- Link to open the organization's **Admin Center**.
- Link to open the **community app directory** for the production workspace (a quick way to check the org is functional).
- Link to open the organization's corresponding **CRM record** (if available).

### Basic details
- Org Id, Name, Identity Tier, Allow Tyler support access status, etc.
- **Last Admin Center sign-in** — tracks when a non-Tyler-Tech user last logged into the org's Admin Center (for revenue recognition tracking).
- Contact information.

### Admins (Org Admins)
- Lists all Org Admins (users with rights to the org's Admin Center).
- **Tyler Tech Org Admins** can remove their own Org Admin rights and optionally delete their user record from the org's Admin Center entirely. Implementation/support should use this to clean up once they no longer need access.
- For select Ops users whose roles require routine customer access, OneTyler provides elevated permissions to **Promote/Remove themselves as an Org Admin** quickly.
- For managers of product ops teams, OneTyler provides elevated permissions to **add customer Org Admins** and to promote their direct reports to **self-promote** as Org Admins, provided (a) the user already has Ops Center access and (b) doesn't already have self-promotion permissions.
- When adding an Org Admin, the **"Use as technical contact"** option simultaneously sets that admin as the org's technical contact. Especially relevant for orgs auto-created from sales-enabled CRM records (which lack contact info).
- For **Workforce Delegated** orgs, adding an Org Admin to a Sub org auto-adds the user to the Super if not already present.
- **Permission propagation delay:** granting/removing Org Admin takes a small bit of time. Freshly granted permissions show a **"Pending"** status during which the user cannot yet access Admin Center.

### Manage workspaces
- Create additional non-production workspaces.
- Make products available on workspaces that have been previously licensed (see Licensing below).
- Access Ops Apps with a workspace context.

### Licensed products
- Add products to the licensing list to make the org eligible.
- To enable a **functional** copy of a product, it must additionally be made available against individual workspaces (Manage workspaces).

### Identity Workforce (org details)
- Options depend on the org's tier (Direct / Managed / Delegated).
- **Workforce Managed** orgs: Administration URL, default authority, IdP federations, **Okta AD Agent pool info / Add/Reset AD Agent account / history**, **Reestablish federation** (with history).
- **Workforce Direct** orgs: IdP federations, **Establish new federation** (with history).
- **Workforce Delegated** Sub orgs: a link points to the Super org for identity setup and authentication logs.

### Authentication logs

Available behavior differs sharply by tier:

| Aspect | Workforce Managed | Workforce Direct |
|---|---|---|
| **Availability** | Ops Center, Admin Center | Ops Center only (*client must use their IdP for logs in lieu of AC*) |
| **Retention** | 90 days (Okta policy) | 90 days (Gateway policy) |
| **Users reflected** | All users (incl. TylerTech) | Only users associated with federation(s) on the org; **excludes** TylerTech users or Workforce Delegated users (check the Super org instead) |
| **Detail level** | Considerable (Okta — primary function is identity) | Compact (Gateway — primary function is redirect/negotiate) |
| **Delay** | Near instantaneous | 5–10 min delay (data first indexed in OpenSearch before presentation) |
| **Activity types** | Comprehensive (users + services) | User activity only |

---

## Product licensing (organization) and availability (workspace)

**Licensing ≠ Activation/Availability.** A product must be **licensed** to an Org AND **available** on a Workspace for a functional copy to exist.

- **Licensing** indicates a client is **eligible** for the product. Done at org level.
- **Availability / Activation** is the actual enablement of the product copy on a specific workspace.

### Step-by-step
1. Filter to the Organization on the Ops Center landing page and click into it.
2. Click **Licensed Products** in the side nav. Search/filter to see if your product is already licensed. If not, click **License a product**.
3. Select the product and click **Save**. This licenses the product to the entire organization — usable on any workspace under it.
4. Make the product available on a specific workspace: **Manage workspaces** → workspace details → activate the product. (If the workspace doesn't exist yet, see **Workspaces — create**.)

---

## Workspaces

A **Workspace** is analogous to a client environment in which solutions are installed for a particular need: production use, testing, training, etc. Each customer typically has **1 production workspace** and optionally **3–7 non-production workspaces**. (Some org-to-org relationships folded into one Customer Id may exhibit multiple production portals.) A workspace often has multiple products licensed on it; product teams should test with co-existing products on shared workspaces (not separate-workspace-per-product) to simulate real client usage. **Test with at least 2 organizations** to better reflect production diversity.

### Workspaces — create

#### Step 1: Pick a standard customer when possible
Use the standard customers (`demo`, `dev`, `test` or `testinprod` for unscripted use; `uat`, `impl` for scripted high-quality data). See the **Standard organizations** table above. If you have an unavoidable business reason for a dedicated org, open a discussion with OneTyler via the Tickets portal.

#### Step 2: Run the Add a Workspace wizard

Under organization details → **Manage workspaces** → **+ Add a workspace**.

**Naming convention:**
- Production workspace key = `<organization id>` (only 1 allowed; for standard orgs, this already exists).
- Non-production workspace key = `<organization id>-<unique workspace id>`. The user-selectable suffix must be **alphanumeric only**, no spaces, no special characters, **no `-`** in the suffix.
- Examples: `demo-notify001`, `demo-vijayvenkataraman`, `demo-cityofrentonwa`.

Wizard tabs:

1. **Workspace details** — Enter Workspace Title, Type (Non Production for standard orgs), and Workspace id. Click **Next**.
2. **Select products to make available** — Picked from products previously licensed on the org. Click **Next**.
3. **Confirm, Save and close** — Initiates workspace creation.

### Workspace details

Click the chevron next to a workspace to see its details. Permissions may unlock **Deactivate workspace** / **Delete workspace** options for internal-org workspaces (CorpDev Support has these rights for all orgs).

- **Available products** — Lists licensed products that can be made available. Making a product available indicates the product is deployed/provisioned for this workspace's business purpose. For non-TCP products (e.g., clusters), an API call to the product's API resolver sources the product link(s) from registration.
- **Ops Apps** — Bookmarks to external Tyler operation tools provided in the product's registration. You still need to be authorized by the product team to actually access the tool.

### Workspace Deactivate / Delete

Deactivation can be reversed; deletion is permanent and non-recoverable. **Recommended:** always deactivate first (observation period) before deleting. Workspaces can also be deactivated from Admin Center. Enter the workspace key to confirm either action.

---

## Add / Reset AD Agent account (Workforce Managed orgs only)

Okta provides the capability to sync an existing Windows Server Active Directory (AD) user store directly with a Workforce Managed Org user store as reflected in the Admin Center. This requires the **Okta AD Agent** to be installed on the AD server. This feature in Ops Center creates a new **AD Agent account** required to access the backend Okta screens of Identity Workforce, download/install the Agent, and use the account to sync users.

A client-facing video guide is on Tyler Community: *AD Sync with Okta AD Agent*.

Steps:

1. Identify the Customer IT Admin responsible for installing the agent. **Add them to the Org as an Org Admin** and confirm they appear under the Admin section. Alert them to expect an email and point them to the community video guide.
2. Click **Add/Reset AD Agent account**.
3. Select the customer Org Admin from the dropdown.
4. Click **Create and send**. An email is sent with instructions, including resetting the password on the AD Agent account. **The link expires in 7 days — customer IT must respond immediately.**

---

## Establish (Workforce Direct only) or Reestablish (Workforce Direct + Managed) federations

Use to help customer IT Admins establish new federations or reestablish existing federations about to expire or already expired.

Steps:

1. Ensure at least **1 domain** exists in the domains list under Organization details (other than `tylertech.com`).
2. Ensure the customer IT Admin responsible for setting up federations is added as an Org Admin.
3. Click **Add Federation** or **Reestablish Federation** as appropriate.
4. Select the customer IT Admin from the Org Admin list.
5. For reestablish scenarios, select the **IdP** from the IdP list.
6. Click **Create and send**. **The link expires in 7 days.**

See also: Confluence *Tyler Cloud Platform (TCP) | Reestablish Federation Demo* (`/wiki/spaces/TTI/pages/386625934/`).

---

## Deactivating and Deleting Organizations

Some Ops Center users see options to **Deactivate** and **Delete** the org. This is exposed only on internal orgs (`IsInternal=true`) for users with the requisite permission. **Only CorpDev Support currently has rights for customer organizations.**

### Deactivating and Reactivating

Deactivation prevents users in the org from logging in through Identity Workforce / Community Access and from accessing any cloud tools (Admin Center, Workforce App Directory, Community Launcher). Recommended as an observation period before deletion. A deactivated org can be deleted directly; it can also be **reactivated** to make it active again. A memo field is available in either dialog (paste links to tickets, etc.). Enter the org key to confirm.

### Deleting

Deletion is **permanent**. Customer org deletion: restricted to CorpDev Support. Internal org deletion: available to users with the maintain-internal-orgs permission. Enter the org key to confirm. The **Delete TID resources** option (checked by default) removes all identity configuration on the org — uncheck **only for troubleshooting** when you plan to recreate the org with the preserved identity setup.

---

## Product Registry

The Product Registry lists all registered products and exposes their details.

### Navigation
- Ops Center dashboard → **Products** link (in the Links section).
- Use the **Name** and **Description** filter fields to find your product. Click the chevron (>) to open product details.

### Product Overview tab
- **Orgs with product licensed** — count of orgs licensing this product.
- **Workspaces with product activated** — count of workspaces (across all orgs) where the product is activated.
- **Contact Information** — Product team's registered contact links (Microsoft Teams channel, distribution list email, etc.). Sourced from registration. Useful for reaching the product dev team.

### Ops Apps tab
Lists operational applications registered by the product team for Tyler staff. External tools launchable directly from Ops Center for product-specific operational tasks. Filterable by name.

### Registration Details tab
Four sub-tabs:
- **Applications** — Apps in the registration with descriptions. Expandable for further detail; right-hand panel shows registration ID, URI path, domains, and navigation-links summary.
- **Navigation Links** — Nav links registered for the product, grouped by audience category (Admin, Workforce, Community, User profile, Ops). Each link: label, source URL, description.
- **JSON** — Raw JSON of the full product registration. Useful for verifying that a registration change pushed to the `tcp-product-catalog` GitHub repository was picked up. Use **download** or **copy** buttons.

### Bulk Licensing

**Bulk Licensing** licenses a product across many orgs and their workspaces in one operation, instead of activating each workspace individually. Especially useful when onboarding a product across many existing customer orgs.

- **Permission gated.** Request access via the *Ops Center Related Tickets and Permissions* portal (see `Knowledge-Shared/Conf-OneTylerTickets.md`).
- A more comprehensive guide (with video) is in the Coda documentation: https://coda.io/d/_dKV_6fSnfBc/Post-registration-activities_suK0yhd_#_lu-oRzAm
- Path: **Ops Center → Product Registry → (Select a Product) → Product details → Bulk License**.

#### License Jobs status table

| Status | Description |
|---|---|
| **Submitted** | Job processed; workspaces have been activated. |
| **Select Workspaces** | Org keys imported successfully; waiting for workspace selection. Click **Continue** to resume. |
| **Failed - Org Import** | One or more org keys in the uploaded CSV could not be found. Click **View Log** for failing keys. |
| **Cancelled** | Job was cancelled before completion. |

#### Step 1: Upload Org Keys
- Click **New** → **New bulk license** dialog.
- Upload a **single-column `.csv`** of organizational keys — **no header row**, one key per line.
- Select **Workspace Type(s)**: Production, Non-production, or both. At least one required.
- Click **Submit**.

**Handling org-import errors:** If any keys can't be found, the job moves to **Failed - Org Import**. Click **View Log** for the Bulk License Job Log which shows creation/close times, processing time, error ratio (e.g. `1 / 2`), and a table of failed org keys with reasons (e.g. *Organization does not exist*). Use **Export log** to download. Correct invalid keys and submit a new job.

#### Step 2: Select Workspaces
- Job transitions to **Select Workspaces** status. Click **Continue**.
- Dialog lists all workspaces (across imported orgs) that don't currently have the product available, filtered by workspace type(s) from Step 1. Columns: Org Key, Org name, Workspace type, Workspace key, Workspace name.
- Select workspaces to activate. Count is shown at the bottom (e.g. `2 of 194 selected`).
- **Tip:** Use **Export results** to download the full list, edit the selection column locally, then **Import selection** to load back. Useful for large workspace lists.
- Click **Submit**.

#### Viewing Job Results
After submission, job moves to **Submitted**. Click **View Log** for full results — creation/close times, status, processing time, count processed (e.g. `277 / 277`), and a row-by-row breakdown with each workspace's activation result. **Successfully activated** is the success indicator. **Export log** downloads the full log.

---

## Additional Permissions

A **Tyler Ops User** is anyone with access to Ops Center. When you request access in TCPCI/TCPQA/TylerPortico, you become a Tyler Ops User with **basic** access.

For restricted functionality (manage federations, +Import, +Create internal, AD Agent setup, Reestablish Federation, Bulk Licensing, etc.), request additional permissions via the *Ops Center Related Tickets and Permissions* portal. See `Knowledge-Shared/Conf-OneTylerTickets.md` for ticket URLs and the exact Notes-field wording for each permission.

---

## Ops telemetry (AWS QuickSight)

OneTyler publishes core telemetry on **production (tylerportico.com)** Organizations, Workspaces, Products/Licensing, and Systems on an AWS QuickSight dashboard called **"TCP Prod Stats"**.

**Direct dashboard link** (does NOT prompt for Tyler SSO if you're not logged in — use the SSO flow below first if you hit issues):
https://us-east-1.quicksight.aws.amazon.com/sn/dashboards/b10d73d5-06b6-4b74-8df4-6a15d4eaf8b6

### Access via Tyler SSO (recommended first time)
1. https://sso.tylertech.com/app/UserHome
2. Click **Tyler Cloud Insights Center** to log into QuickSight.
3. Locate **TCP Prod Stats** card. (Optional: star it as favorite.)
4. Click the card to open the dashboard.

If you don't see **Tyler Cloud Insights Center**, file a ticket with `help.desk@tylertech.com`.

### Exporting data
Each card supports CSV download (Excel additionally available on list-type data). Select the card → 3-dot menu (top right) → **Export to CSV** / **Export to Excel**.

### Dashboard sections
- **Customer Organizations** — Orgs marked External (Ops Center > Organizations > Details). Sample telemetry: Customer Org Count, Total Workspace Count, Avg Active Workspace Count Per Org, Production vs Non-Production Workspaces, Top Customer Workspace Count, Org Count By Number of Products Licensed, Top Orgs by Number of Products Licensed. Downloads: Customer Orgs, Customer Workspaces.
- **Internal Organizations** — Same telemetry shape as Customer Orgs but for Tyler-internal use (demo, etc.). Downloads: Internal Orgs, Internal Workspaces.
- **Products** — Telemetry by product. Sample: Total Products Registered in Prod, Distinct Products Licensed To Customers, Avg Product Licensed Count Per Org, Product Licensing Instances (Customer/Internal), Org Count By Licensed Product Instances, Org Count By Product Licensed. Download: Product Licensing Info.
- **Systems** — Sample: System Count, Active System Count, Count by Hosting Type, Hosting Account, Division, Product, Domain, Environment, Creator. Downloads: Systems Breakdown, Full Systems Breakdown.

---

## Video guides

An *Overview of the Control plane and Ops Center / Admin Center tools* video is available as an embedded recording on the Docusaurus *Video Guides* page (SharePoint stream link, internal access).

---

## Changelog highlights (most recent first)

This is a curated set of notable Ops Center changes. For the full chronological list, see the Docusaurus changelog page.

- **4/1/26 — Automatic organization creation from Tyler CRM.** Ops Center now auto-creates customer organizations from sales-enabled CRM account records. Auto-created orgs have **no contact info or domains set**. Use **"Use as technical contact"** under Org Details > Admins to designate one. Auto-created orgs are **Workforce Direct**.
- **3/18/26 — Bulk Licensing.** Added Bulk Licensing in the Product Registry.
- **12/12/25 — Org Admin optional during Import.** Added the ability to skip Org Admin details during Import; added the ability to specify a technical contact when adding an Org Admin.
- **12/11/25 — Create internal organizations.** Added the +Create Internal feature for users with the maintain-internal-orgs permission.
- **11/12/25 — Clear Tyler Identity config on delete.** Added an option (default-on) to also delete corresponding TID configuration when deleting a Workforce Direct/Delegated org.
- **10/30/25 — Authentication logs for Workforce Direct orgs.** Previously only Workforce Managed orgs had auth logs in Ops Center. WD log content differs substantially from WM (see the Auth Logs table above).

---

## Notes for the chatbot

- **Always pair "license" with "activate/availability"** — they are not the same thing. Users frequently confuse them. A product not appearing for users on a workspace usually means licensed at org level but never activated on the workspace.
- **Identity Tier cannot be changed after org creation** — except for the narrow UNINITIATED Workforce Direct → Workforce Managed conversion ticket (see `Knowledge-Shared/Conf-OneTylerTickets.md`). For other tier changes, the org must be deleted and recreated.
- **Workspace key conventions:** prod = org key; non-prod = `<orgkey>-<suffix>`, suffix must be alphanumeric (no spaces, special chars, or further `-`).
- **OneTyler intentionally limits new-org creation in TCPCI/TCPQA.** When a user asks how to create an org for dev/test, first redirect to the standard orgs (`demo`, `dev`, `test`, `uat`, `impl`) or to **+Create internal** before recommending a ticket.
- **Self-service hierarchy:** Workforce Direct → use **+Import**; internal org → use **+Create internal**; Workforce Managed → must file a ticket. Always prefer self-service.
- **Magic-link emails for federation/AD Agent setup expire in 7 days** — call this out when discussing these flows.
- **Org Admin permission propagation has a "Pending" period** — set expectations for users who can't immediately log in.
- **Auto-created (4/1/26+) orgs have no contact info or domains** — always recommend the **"Use as technical contact"** option when first adding an Org Admin.
- **Production org/workspace deletion is restricted to CorpDev Support.** For internal orgs, deletion is available to those with the maintain-internal-orgs permission.
- **TylerPortico org creation by Tyler Ops users is restricted** — only OneTyler Engineering Services can add Tyler Ops users in production.
- For prerequisites on creating a customer org, the chatbot should always reach for `Docusaurus-TylerCRM.md` (CRM record validity) and `Docusaurus-OrgAdminInfo.md` (Org Admin sourcing).
