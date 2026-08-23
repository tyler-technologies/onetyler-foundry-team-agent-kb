# CorpDev Tickets and Permissions — the authoritative catalog

**This is the single source for every "which ticket do I file?" question, in every domain.**
Shared across all agents — see `Knowledge-Shared/_START_HERE.md`.

Reconciled from **three** upstream sources:

| # | Source | Covers | Precedence |
|---|---|---|---|
| 1 | Confluence — *Tyler Cloud Platform (TCP) \| Ops Center Related Tickets and Permissions* (https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386600308) | The most common requests, with pointed field-by-field instructions | **Wins on HOW to fill in a form** |
| 2 | JSM — CorpDev Support portal (https://help.center.tylertech.com/servicedesk/customer/portal/3168) | Every request type across 6 groups, with each form's own help text | **Wins on WHICH forms exist** |
| 3 | JSM — CorpDev Feature Requests portal (https://help.center.tylertech.com/servicedesk/customer/portal/3185) | All feature requests and enhancement ideas | Sole authority for feature requests |

Domain: cross-domain (Ops Center · Identity · Support Access Center · Development/Infra · Forge/TCW · 3rd-party)
Audience: Tyler product, deployment, implementation, identity-support and engineering staff who need to file a request against CorpDev.

This document catalogs every Ops Center–related ticket: what it does, when to use it, who is eligible, prerequisites, the direct link to file it, and the exact fields/Notes content expected. Each ticket is a self-contained entry — they can be read independently.

---

## How to use this catalog (quick decision guide)

Match the user's intent to one of the entries below. Each row points to the section that has the full ticket details.

| If the user wants to… | Go to section |
|---|---|
| Get basic access to Ops Center, Admin Center, or CAPM | **Basic Access** |
| Get additional permissions inside Ops Center (federation mgmt, Import org, AD Agent, Reestablish Federation, etc.) | **Basic Access** (same generic form; Notes field varies) |
| Report a bug in a CorpDev-maintained application | **General Issues — Bug Report** |
| Delete a workspace or delete an organization, or any other org/workspace request that doesn't fit elsewhere | **General Issues — Other org/workspace assistance** |
| Create a NEW customer organization (Workforce Managed) | **New Org Request** |
| Create a NEW Workforce Direct (federation-only) org | **Use self-service +Import** — see *Import an organization* |
| Create a NEW internal organization (Tyler-internal use) | **Create Internal Organization** |
| Convert an unused Workforce Direct org → Workforce Managed | **Convert Org: Workforce Direct → Workforce Managed** |
| Add an Org Admin, or promote yourself as Org Admin | **Org Admins** |
| Migrate workspaces (WM → WD retargeting) | **Workspace Migration** |
| Request a non-standard workspace (suffix not in the standard set) | **Non-Standard Workspace Request** |
| Report that an entire environment is down (platform-wide issue) | **Environment Issues (global)** |
| Request a new feature or give feedback on a CorpDev tool | **Feature Requests** |
| Enable Support Access Center on a WM org with OnPrem Target=Gateway | **Support Access Center** |
| Report an authentication issue (Workforce or Community) | **Identity — Authentication Issues** |
| File an Identity Client request | **Identity — Identity Client** |
| Get Okta admin backend access | **Identity — Okta Admin Backend Access** |
| Request a GitHub user license | **Infrastructure — GitHub Access** |
| Any other infra request (GitHub config/teams, other tools) | **Infrastructure — Other** |
| Ask a general question or request something not listed | **General Information / Inquiry** |

---

## Glossary (resolve before answering)

- **TCP** — Tyler Cloud Platform.
- **OC** — Ops Center. Internal Tyler tool for managing TCP orgs/workspaces.
- **AC** — Admin Center. Customer-facing administration UI per org.
- **CAPM** — Community Access Profile Manager. Lives at `https://demo.tylerportico.com/portal/community-profile-manager/`.
- **CorpDev** — The internal team that maintains Ops Center and many TCP tools and that fulfills these tickets.
- **Org / Organization** — A TCP customer or internal tenant (has a `customerId` / org key).
- **Workspace** — A sub-tenant under an organization (has a `portalId`). Production workspace key usually equals the org key; non-prod uses suffixes. The **6 standard non-prod suffixes** are `test`, `train`, `staging`, `dev`, `uat`, `impl`; anything else is a "non-standard workspace" requiring a separate request.
- **Workforce Direct** — Federation-only identity model. Customer brings their own IdP. **Self-service org creation is supported** via +Import in Ops Center.
- **Workforce Managed** — Tyler-hosted Okta tenant for the customer. Org must be created via a ticket and requires a CRM contract.
- **Workforce Delegated** — Third identity flavor (see internal docs for details).
- **CRM Customer Identifier** — The org key, sourced from a well-formed CRM record. Required field on most org-related tickets.
- **CRM Id** — The numeric CRM Id (different from Customer Identifier). Enter `0` if not applicable.
- **AD Agent** — Active Directory agent account used by Identity Workforce.
- **Reestablish Federation** — A specific recovery/maintenance action on a federated (Workforce Direct) org.
- **Support Access Center** — Feature that lets Tyler support reach into a customer org; only enableable on WM orgs with OnPrem Target=Gateway.

---

## IMPORTANT: shared "generic access" ticket form

The URL `https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3333/create/4133` is the **single generic Ops Center permission/access request form**. It is used for many distinct purposes, distinguished by:

- **TCP Tool Selection** dropdown — pick "OPS Center - TylerPortico" for production, or another environment for dev/test/train.
- **Notes** field — write what you actually want (free text from the templates below).

Requests filed through this form include:
- Basic Ops Center access
- CAPM access (TCP Tool Selection = "CAPM (Community Access Profile Manager)")
- Additional Ops Center permissions: manage federations; +Import organization; Setup/Reset AD Agent User Account; Reestablish Federation

For each of these, the Notes-field wording is given in the sections below. **Do NOT assume separate ticket URLs for these — they all funnel through form 4133.**

Exception: Org Admin promotion / "Add an Org Admin" / self-promote — **does NOT use this form**. See the *Org Admins* section.

---

## Basic Access (OC, AC, CAPM) and Additional Ops Center Permissions

### Ops Center access request (and additional permissions)

- **Use when:** You need basic access to Ops Center, OR you already have access and need an additional permission inside it (manage federations, +Import org, etc.).
- **Ticket:** https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3333/create/4133
- **Fields:**
  - **Product team(s):** Select the product team(s) you represent. If your product isn't listed, choose "Other" and name it in Notes.
  - **TCP Tool Selection:** "OPS Center - TylerPortico" for production. Pick a non-prod environment if this is for development testing, training, or QA.
  - **Notes:** State what you need. Examples:
    - `"Need access to Ops Center for <reason>"`
    - `"Please provide me additional permissions to be able to manage federations"`
    - `"Please provide me additional permissions to be able to use the Import organizations feature"`
- **Does NOT cover:** "Add an Org Admin" or "Promote me as admin" — those go through the **Org Admins** flow further down.

### Client Admin Center access request

- **Use when:** You (a Tyler employee) need to access a specific customer's Admin Center, OR you are requesting that a customer IT admin be added to their org's Admin Center.
- **Ticket:** https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3333/create/4165
- **Prerequisites:**
  - The organization must already exist in Ops Center in the requested environment.
  - You must not already have access.
  - After approval, expect up to **5 minutes** for access to take effect. A clock icon appears next to your name under Organization Details > Admins during the pending state; once cleared, access is live.
- **Fields:**
  - **Product team(s):** As above.
  - **CRM Customer Identifier:** The Organization Key value from Ops Center.
  - **Reason for Access:** Closest matching reason for the access (for external orgs).
  - **Customer email address:** Customer IT admin's email if requesting on their behalf.
  - **Notes:** Justification. If on behalf of a client IT admin, include their first/last name here in addition to the email.

### CAPM (Community Access Profile Manager) access request

- **Use when:** You need access to CAPM.
- **Ticket:** https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3333/create/4133 *(same generic form)*
- **Fields:**
  - **Product team(s):** As above.
  - **TCP Tool Selection:** "CAPM (Community Access Profile Manager)" for production; choose another environment for non-prod.
  - **Notes:** Use as needed.
- **After approval:** Access CAPM at https://demo.tylerportico.com/portal/community-profile-manager/
- **Docs:** Confluence — *Tyler Cloud Platform (TCP) | Community Access Profile Manager* (`/wiki/spaces/TTI/pages/386599847/`)

---

## General Issues

### Report bugs in CorpDev-maintained applications

- **Use when:** You have a confirmed bug in a CorpDev-maintained app.
- **Before filing:** Confirm the bug is in a CorpDev-maintained application. See Confluence — *Tyler Cloud Platform (TCP) | Development team support portals* (`/wiki/spaces/TTI/pages/386599215/`).
- **Ticket:** https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3333/create/4143
- **Fields:**
  - **Product team(s):** As above.
  - **Severity:** Mark production-blocking vs workaround-available appropriately.
  - **TCP Application or Service:** Pick the affected app/service.
  - **TCP Environment(s):** Pick the affected env.
  - **Engineer(s) email list:** Product engineering contacts who did initial investigation, if any.
  - **Summary:** Concise headline.
  - **Description:** Repro steps, supporting URL, screenshots, investigation notes.
  - **Issue related URL:** Direct link where the issue can be reproduced.

### Other non-product assistance with Organizations and Workspaces

- **Use when:** Your org/workspace request doesn't fit any of the more specific tickets. Common examples:
  - Delete a workspace (customer org workspace)
  - Delete a customer organization
- **Ticket:** https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3333/create/4150
- **Fields:**
  - **Product team(s):** As above.
  - **Delivery Deadline:** Yes/No. CorpDev typically completes org tasks within **5 business days** (often sooner). They will try to honor deadlines but no guarantees.
  - **Delivery Date:** Required if Delivery Deadline = Yes.
  - **CRM Id:** Numeric CRM Id (NOT the Customer Identifier). Enter `0` if not applicable.
  - **CRM Company Name:** Org's company name in CRM, or `"Not applicable"`.
  - **CRM Customer Identifier:** Org key, or `"Not applicable"`.
  - **CRM Case/Support ticket URL:** Link if this is related to a customer-filed ticket.
  - **Description:** Describe the issue.

---

## New Org Request

### Create a NEW Organization

- **Use when:** A new customer org needs to be created (typically Workforce Managed). Also for internal-org creation when you can't self-service.
- **Self-service alternative:** If you are creating a **Workforce Direct (federation-only)** org, do NOT file this ticket — use the **+Import an organization** feature in Ops Center yourself. Self-service is strongly preferred over loading CorpDev support. To get the +Import permission, see *Orgs > +Import (an organization)* below.
- **Ticket:** https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3333/create/4158
- **Prerequisites:**
  - A "well-formed" CRM customer account record. See https://docs.tylerdev.io/opscenter/tylercrm/ for what "well-formed" means.
  - If the customer purchased Workforce Managed: have the contract-completion link ready.
  - For internal-org requests: have (a) justification for why an existing org can't be reused, (b) Name of the org, (c) preferred subdomain ready.
- **Fields:**
  - **CRM Customer Identifier:** From the well-formed CRM record (Business Use = Default).
  - **Environment:** Environment(s) to create the org in.
  - **Identity SKU:** Pick per internal instructions.
  - **CRM Contract Quote URL:** Link to the contract URL (required for Workforce Managed purchases).
  - **Customer Technical Contact Name:** First/last name of the Client IT Admin who will federate (WD) or take Admin Center ownership (WD/WM).
  - **Customer Technical Contact Email:** Email of the above.
  - **Delivery Deadline / Delivery Date:** Same as above; CorpDev targets 5 business days.
  - **Notes:** Any extras, especially for internal-org requests.

---

## Convert Org: Workforce Direct (federation-only) → Workforce Managed (Okta tenant)

### Convert an UNINITIATED Workforce Direct org to Workforce Managed

- **Use when:** A Workforce Direct org needs to be converted to Workforce Managed. Allowed **only** when ALL of these are true:
  - The org is Workforce Direct (not Managed, not Delegated).
  - There are no customer federations on the org.
  - There are no non-Tyler users on the org.
- **Ticket:** https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3333/create/4860
- **Fields / Notes:**
  - If the customer has purchased Workforce Managed, paste the CRM contract link (ask sales if you can't find it).
  - If this is a **temporary workaround** because a product isn't "Gateway"-compatible, state in the description which product is blocking WD use and link the relevant CRM record.

---

## Orgs > +Import (an organization)

### Request permission to use the +Import feature

- **Use when:** You need to be able to self-create Workforce Direct (federation-only) orgs via Ops Center's +Import functionality. Eligibility: deployment/implementation staff for a product team.
- **Ticket:** https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3333/create/4133 *(same generic form)*
- **Fields:**
  - **Product team(s):** As above.
  - **TCP Tool Selection:** "OPS Center - TylerPortico" for production; other for non-prod.
  - **Notes:** `"Please provide me access to the Import an organization functionality. I am a deployment/implementation staff member for my product team."`
- **Docs/Demo:** Confluence — *Tyler Cloud Platform (TCP) | Import an organization* (`/wiki/spaces/TTI/pages/386630359/`)

---

## Orgs > +Create Internal (organization)

### Request permission to use +Create Internal

- **Use when:** You maintain internal orgs for a Tyler group/division and need UI or API access to create them.
- **Ticket link:** N/A — no self-service ticket. Reach out to **Vijay Venkataraman** directly.
  - Confluence reference: `/wiki/people/557058:71326a8b-b1c7-460a-87d3-a0a58f108b97?ref=confluence`
- **Notes:**
  - Provided to maintainers of internal orgs for groups/divisions.
  - UI or API access available.
  - Follow the naming conventions: Confluence — *Internal Orgs creation in Ops Center → Internal-Org-Naming-Construct* (`/wiki/spaces/SPY/pages/407176942/Internal+Orgs+creation+in+Ops+Center#Internal-Org-Naming-Construct`)

---

## Orgs > Organization Details > Admin (Org Admins)

### Add an Org Admin, or self-promote as Org Admin

- **Use when:** You want to add an Org Admin to an existing org, or you want to promote yourself.
- **Ticket link:** No single ticket URL — follow the manager's-guide procedure.
- **Procedure / Docs:** Confluence — *Tyler Cloud Platform (TCP) | Org Admin promotions (Admin Center access) - a Manager's guide* (`/wiki/spaces/TTI/pages/386629479/`)
- **Note for chatbot:** The generic "Ops Center additional permissions" form (4133) does NOT cover this — direct users to the manager's-guide flow.

---

## Orgs > Organization Details > Identity Workforce (Permissions)

### Setup / Reset AD Agent User Account — permission request

- **Use when:** You are in an identity-support role and need permission to use the *Setup/Reset AD Agent User Account* feature inside Ops Center.
- **Ticket:** https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3333/create/4133 *(same generic form)*
- **Fields:**
  - **Product team(s):** As above.
  - **TCP Tool Selection:** "OPS Center - TylerPortico" (or other for non-prod).
  - **Notes:** `"Please provide me access to the Setup/Reset AD Agent User Account functionality. I am in a identity support role and need access to this to be able to provide AD Agent support to clients"`
- **Docs/Demo:** Confluence — *Tyler Cloud Platform (TCP) | Ops Center - Setup AD Agent User Account* (`/wiki/spaces/TTI/pages/386599721/`)

### Reestablish Federation — permission request

- **Use when:** You are in an identity-support role and need permission to use the *Reestablish Federation* feature inside Ops Center.
- **Ticket:** https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3333/create/4133 *(same generic form)*
- **Fields:**
  - **Product team(s):** As above.
  - **TCP Tool Selection:** "OPS Center - TylerPortico" (or other for non-prod).
  - **Notes:** `"Please provide me access to the Reestablish Federation functionality. I am in a identity support role and need access to this to be able to provide federation support to clients"`
- **Docs/Demo:** Confluence — *Tyler Cloud Platform (TCP) | Reestablish Federation Demo* (`/wiki/spaces/TTI/pages/386625934/`)

---

## Orgs > Organization Details > Workspace migration

### Access to Workspace Migration

- **Use when:** You need to perform a Workforce Managed → Workforce Direct retargeting/migration on workspaces.
- **Ticket link:** No single ticket URL — follow the documented procedure.
- **Docs:** Confluence — *Tyler Cloud Platform (TCP) | Workforce Managed to Workforce Direct Retargeting and Migration* (`/wiki/spaces/TTI/pages/386635412/`)

---

## Orgs > Manage workspaces > Non-Standard Workspace Request

### Request a non-standard workspace for a customer org

- **Use when:** You need a non-production workspace whose suffix is NOT one of the 6 standard values: `test`, `train`, `staging`, `dev`, `uat`, `impl`.
- **Ticket:** https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3333/create/7513
  — **"Non-Standard Workspace Request"**, a dedicated form (verified live 2026-08-23). This
  replaces the older guidance of filing the general `create/4150` form with a prose
  description; the Confluence source page still shows the old route.
- **Required fields on the form:** Product Team(s) · Org Key (Customer Identifier) ·
  Workspace Name · Explanation ("Please explain why this non-standard workspace is required").
- **Instructions:**
  - In the description, justify why you need the non-standard workspace. Workspaces represent a "customer business purpose" — explain how your suffix reflects a customer business purpose.
  - For a limited time, **numbered extensions** to the approved suffixes are being approved — e.g. `impl1`, `impl2`, `impl3`, `test1`, `test2`, etc.
  - Any other suffix, or any request for **more than 7 workspaces total per customer**, is subject to greater scrutiny and CorpDev will likely reach out to understand the business need.

---

## Environment Issues (global)

### Environment not working (platform-wide issue)

- **Use when:** An entire environment is not working AND you have already done the research to show it is a **platform-wide** issue. (CorpDev is NOT the default first investigator.)
- **Ticket:** https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3328/create/4129
- **Instructions:**
  - Preferably filed by an engineer.
  - Must include logs, investigation notes, etc. demonstrating why the engineer believes it is a platform issue.

> Note: the "Request new features or provide feedback on any CorpDev tool" row that appears alongside this in the source is covered separately under **Feature Requests** (portal 3185).

---

## Feature Requests

### Request a new feature or provide feedback on any CorpDev tool

- **Use when:** You want to propose a new feature or leave feedback on a CorpDev tool (Ops Center, Admin Center, CAPM, etc.).
- **Where to go:** https://help.center.tylertech.com/servicedesk/customer/portal/3185

---

## Support Access Center

### Enable Support Access Center on a Workforce Managed org with OnPrem Target=Gateway

- **Use when:** You need to enable Support Access Center on a WM org whose OnPrem Target is Gateway.
- **Ticket:** ⚠ **Link unresolved — do not guess.** The Confluence source page points this at
  `group/3329/create/4149`, but that form is verified live as **"Identity SKU Change"**, a
  different request entirely. Direct the user to the CorpDev portal
  (https://help.center.tylertech.com/servicedesk/customer/portal/3168) → **2. TCP - Operations**
  and pick the closest matching request, or file *General Information / Inquiry*
  (`group/3333/create/4141`) asking to be routed. Flag to the page owner that the link needs fixing.
- **Reference:** https://help.center.tylertech.com/servicedesk/customer/portal/3185

### Be authorized to use Support Access Center for a product

- **Use when:** You are Tyler staff who needs to be authorized to use SAC **for a specific
  product** — i.e. added to that product's SAC group. This is the per-product authorization,
  distinct from simply logging in to the SAC dashboard (any `@tylertech.com` user can do that).
- **Ticket:** https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3333/create/4150
  ⚠ This is the **shared generic form** (`create/4150`) — see *IMPORTANT: shared "generic
  access" ticket form* above. It is distinguished only by the description content below.
- **In the description, specify all three:**
  - **Division** — the division/group code. Codes are listed at
    https://tylertech.atlassian.net/wiki/spaces/SPY/pages/407176942/Internal+Orgs+creation+in+Ops+Center#Division/Group-Codes-(up-to-3-char)
  - **Product** — the product **registration Id** (e.g. `pbb`), as shown in
    Ops Center → Product Registry → (select product) → Registration details.
  - **Role** — your job role, e.g. `Development-Engineering`,
    `Development-Product Management`, `Operations-Project Manager`,
    `Operations-Deployment`, `Operations-Implementation`, `Operations-Support`.
- **Companion:** `Knowledge-SupportAccessCenter/Docusaurus-SupportAccessCenter.md` — for what
  SAC groups are, the all-or-nothing vs fine-grained distinction, and the naming convention.

---

## Identity Related

### Authentication issues

- **Use when:** You (or a customer) are hitting an authentication problem in Identity Workforce or Identity Community Access.
- **Ticket:** https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3329/create/4138
- **What to include:**
  - Which solution is affected: **Identity Workforce** or **Identity Community Access**.
  - Organization Key or Okta tenant having the issue (if available).
  - Detailed description of the problem.
  - If there is a login error code, paste it in the description.

### Federations

- **Use when:** Anything federation-related — creating, changing, or troubleshooting a
  customer federation.
- **Ticket:** https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3329/create/4128
- **What to include:**
  - **Organization Key** (CRM Customer Identifier).
  - Details of the federation or the change being requested.
- **Do NOT use this for Ops Center *permissions*.** If what you actually need is permission
  to manage federations *within Ops Center*, that is the Ops Center access/permissions
  ticket (`create/4133`) — see *Ops Center access request (and additional permissions)*
  above, and *Reestablish Federation — permission request*.

### Identity Client

- **Use when:** Identity Client-related request. Note "Identity Client" here means a
  registered OAuth/OIDC **application**, not a Tyler customer.
- **Ticket:** https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3329/create/4153
- **Notes:** Follow the on-form header instructions.

### Okta Admin Backend Access

- **Use when:** You need Okta admin backend access.
- **Ticket:** https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3329/create/4152
- **What to include:** The organization key OR the Okta tenant URL.

---

## Infrastructure (GitHub, etc.)

### GitHub Access — new-user license

- **Use when:** You need a GitHub user license (just the access — not team/permission configuration).
- **Prerequisite:** You have already created a GitHub user account before filing.
- **Ticket:** https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3328/create/4176

### All other infrastructure requests (incl. GitHub config — teams, permissions)

- **Use when:** Any infra request beyond a simple GitHub user license, INCLUDING new GitHub teams or permission changes.
- **Ticket:** https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3328/create/4140
- **Notes:** This ticket covers several tools/options — read the on-form choices carefully before submitting.

---

## General Information / Inquiry / New features / Modify features (any subject)

### General questions

- **Use when:** Your question or request doesn't match any of the above.
- **Ticket:** https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3333/create/4141
- **Notes:** Provide enough detail for someone to answer your question or scope your request.

---

## Quick ticket-URL index (for direct lookup)

| Ticket URL | Used for |
|---|---|
| `.../create/4133` | **Generic** Ops Center / CAPM access AND additional permissions (Notes field varies: manage federations, +Import, AD Agent setup, Reestablish Federation) |
| `.../create/4165` | Client Admin Center access |
| `.../create/4143` | Bug report in CorpDev-maintained apps |
| `.../create/4150` | Other org/workspace assistance (incl. delete workspace, delete org) |
| `.../create/4158` | New org request (Workforce Managed creation; internal-org creation) |
| `.../create/4860` | Convert UNINITIATED Workforce Direct org → Workforce Managed |
| `.../group/3328/create/4129` | Environment not working — platform-wide issue (engineer-filed, with logs) |
| *(to be published Aug '26)* | Non-standard workspace request (suffix outside `test/train/staging/dev/uat/impl`) |
| `.../create/4138` | Identity — authentication issues |
| `.../create/4153` | Identity — Identity Client |
| `.../create/4152` | Identity — Okta admin backend access |
| `.../create/4149` | Support Access Center enablement (WM + OnPrem Target=Gateway) |
| `.../create/4176` | GitHub user license |
| `.../create/4140` | Other infra requests (GitHub teams/permissions, other infra tools) |
| `.../create/4141` | General questions / catch-all |
| `https://help.center.tylertech.com/servicedesk/customer/portal/3185` | Feature requests / feedback on CorpDev tools |

Full URL prefix for all of the above (except the feature-request portal): `https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/<group>/create/<id>`

---

## Notes for the chatbot

- When a user describes their need, prefer pointing them to **self-service** first (e.g., +Import for Workforce Direct orgs) before recommending a ticket.
- Watch for the **shared form 4133** confusion — many distinct asks land at the same URL with different Notes wording. Always give the user the exact Notes-field template.
- "Add an Org Admin" / "Promote me as admin" is NOT handled by the generic form 4133 — route to the manager's-guide flow under *Org Admins*.
- For workspace migration (WM → WD retargeting), there is no single ticket URL — route the user to the migration runbook on Confluence.
- The **non-standard workspace request** now has a dedicated live form: `group/3333/create/7513`. Hand out that URL plus the suffix rules (standard set + numbered extensions like `impl1`/`test2`; >7 workspaces gets scrutiny). Do NOT send people to the general `4150` form for this any more.
- The **Environment not working** ticket (4129) is in **group 3328**, not the usual 3333 — and is gated on the filer having already proven a platform-wide issue with logs. Don't recommend it for ordinary single-org outages.
- Internal-org creation is gated and largely manual — direct users to Vijay Venkataraman for `+Create Internal`.
- **Never invent a ticket URL.** If the right form is not listed here, send the user to the portal root (https://help.center.tylertech.com/servicedesk/customer/portal/3168) and name the group to pick, or to *Request or Share Functional Information* (`group/3333/create/4141`).
- **All feature requests and enhancement ideas go to a different portal** — `3185`, not `3168`. See *Feature requests* below.
- Confluence wiki links in this document use Tyler-internal paths (e.g. `/wiki/spaces/...`). They are usable from inside Tyler systems; tell external readers they are internal references.


---

# Complete CorpDev portal reference (harvested from JSM, 2026-08-23)

The sections above are the **curated** catalog, mirroring the Confluence source page, which
deliberately covers only the most common requests. This section is the **complete** set of
request types on the live portal, captured directly from JSM including each form's own
top-of-form instructions.

**Precedence:** where this section and the curated sections above disagree on *how to fill
in* a form, the Confluence-derived guidance above wins — it is more pointed. Where they
disagree on *which form exists*, the live portal wins, because a form either exists or it
does not.

URL pattern: `https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/GROUP/create/ID`

Portal groups:

| Group | Name | Scope |
|---|---|---|
| `3328` | TCP - Development | Environments, GitHub, infrastructure, deployment pipelines, training |
| `3333` | TCP - Operations | Orgs, workspaces, access, Gateway migration, portal issues |
| `3329` | Tyler Identity Cloud | Authentication, federation, identity clients, Okta, SKU |
| `3332` | Forge and TCW | Design system: components, icons, illustrations, glossary, UX |
| `3330` | 3rd Party Solutions | OneTrust cookie reporting |
| `3331` | Internal CorpDev ONLY | Not for product teams |

---

## Feature requests — a DIFFERENT portal (3185)

**Use when:** requesting any new feature, enhancement, or modification to existing
functionality, or giving feedback on any CorpDev-owned solution — Ops Center, Admin Center,
Identity Workforce, Community Access, Workforce/Community App Directories, Workforce and
Community profiles, CAPM, and so on.

- **Portal:** https://help.center.tylertech.com/servicedesk/customer/portal/3185
  — *CorpDev Feature Requests*
- **Form:** *Suggest a feature or provide feedback* —
  https://help.center.tylertech.com/servicedesk/customer/portal/3185/group/3385/create/4367
- **Voting and comments:** existing requests are visible on the CorpDev Feature Requests
  board, where you can comment and vote after submission. The board shows tickets up to
  **60 days after completion**.
- This is where the deprecated `4137` *Enhancement request* form now redirects.

---

## Deprecated and superseded forms — do not use

These still exist and are reachable, so users will find them. Recognise them and redirect.

### `3333/create/4137` — Enhancement request — **DEPRECATED**

The form's own help text reads: *"This ticket has been deprecated - DO NOT SUBMIT A TICKET
HERE."* It redirects to:
- New features → the feature-request portal `3185` (above).
- Anything infrastructure-related → *Infrastructure resource or access requests*
  (`3328/create/4140`).

### `3329/create/4154` — TID Okta Tenant Request — **SUPERSEDED**

*"This request type has been superseded by the Org Creation request for TCP - Operations.
Unless you have a pre-approved reason to use this form, please use the Org Creation request
instead."* → `3333/create/4158`. **Unapproved requests are auto-closed.**

### Broken links inside the portal itself

The `3333/create/4150` form's help text links to `create/1853` ("2. TCP Operations > Admin
Center Access Request") and `create/956` ("2. TCP Operations > OPS Center/Okta Access").
**Both 404.** The current IDs are `4165` and `4133` respectively. If a user reports a dead
link from that form, this is why — give them the working IDs.

---

## Group 3329 — Tyler Identity Cloud (complete)

### `4128` — Federate Identity Provider

Assistance federating a client's identity provider when it cannot be set up in Admin Center.

- The description **must state what prevented using Admin Center** for the federation.
- **Configuration settings must be sent securely via Kiteworks — never in the ticket.**
- For adding or modifying a client's IdP in TID-W, the description must list: a client ID on
  the provider, scopes, issuer endpoint, authorization endpoint, token endpoint, JWKS
  endpoint, userinfo endpoint, and a **test user account** on the provider for validation.
- The TID team will contact you separately for the client secret and test user password.
- Requires the CRM Customer Identifier. Related: Federation FAQ.

### `4138` — Authentication Issues

Inability to log in, failed email verification, and similar. Provide: which solution
(Identity Workforce or Community Access), the Organization Key or Okta tenant, a detailed
description, and any login error code verbatim.

### `4149` — Identity SKU Change

Updates a customer's TID deployment after their Identity Workforce SKU changes.

- **READ ME FIRST:** the org must **already exist in Ops Center**. If not, file *Org
  Creation* (`3333/create/4158`) instead.
- Provide the correct **CRM Customer Identifier** — see *TID - Finding the CRM Customer
  Identifier (and other information in Dynamics CRM)*.
- Provide the **new Identity SKU level**, which is verified against current records.
- ⚠ Note the Confluence source page mislabels this URL as the Support Access Center enable
  request. It is not.

### `4152` — Okta Access Request

Access to TID Okta tenants. Provide the organization key or the Okta tenant URL.

### `4153` — Identity Client

Add, modify, or request details of **OAuth clients** for applications. "Client" here means a
registered application, not a Tyler customer. Follow the on-form header instructions.

### `4159` — Custom IdP Investigation

For a customer requesting a **non-standard** custom IdP for federation. Tyler Identity vets
it and concludes whether that IdP type will be supported. Reference: *Non-Standard IdP
Verification Process*. Required fields include Customer Name and Vendor Name.

### `4154` — TID Okta Tenant Request — superseded, see above.

---

## Group 3333 — TCP Operations (additions beyond the curated sections)

### `7513` — Non-Standard Workspace Request

Dedicated form; see *Orgs > Manage workspaces* above for the suffix rules.
Fields: Product Team(s) · Org Key (Customer Identifier) · Workspace Name · Explanation.

### `4177` — Retarget Workspace

Retargets a workspace for use with Gateway. CorpDev performs the retarget on processing.
Provide: your product team name, the CRM Customer Identifier for the org containing the
workspace, the workspace name, and the **type of deployment** to retarget.

### `4162` — Enable Org migration to Gateway

Enables the Gateway migration option in a customer's Admin Center, after which an org admin
can migrate the org's identity provider(s) themselves.
**By submitting you confirm the organization is ready to migrate** — read the form's
readiness criteria before filing.

### `4150` — TylerPortico.com: Requests and Issues

The general Operations form. Its own help text redirects several common cases:
- Admin Center access for you or a client → *Admin Center Access Request* (`4165`).
- Ops Center / Okta access → *OPS Center / CAPM Access Request* (`4133`).
- **Tyler Deploy issues → do NOT file here until the Tyler Deploy team has sent a JSON
  payload to the TCP APIs first.**

### `4166` — Delete Org

Requests deletion of an existing org.
**READ ME FIRST: you must confirm the org is not in use by another application team.**
Tyler Identity does not validate this for you.

### `4178` — Tylertechnologiestx Access

**Authorized users only** — a stop-gap letting managers request access to the
`tylertechnologiestx` org without org-admin access there. Unauthorized requests are not
serviced; the authorized-user list is in the linked Confluence documentation.

### `4174` — TCP Documentation and Support Portal Feedback

Report errors or suggest improvements to the internal TCP documentation and support portal.

### `4141` — Request or Share Functional Information

Functional information requests to or from the TCP team. Also the safe fallback when no
other form clearly fits.

### `4164` — Request functional consulting or training

Functional consulting or training on TCP and core applications, for product development,
support, and implementation teams. (Also present in group 3328.)

### `4137` — Enhancement request — deprecated, see above.

---

## Group 3328 — TCP Development (complete)

### `4129` — Environment

Issues with TCP environment availability. Gated: intended for engineers who have already
established a platform-wide problem, with logs and investigation notes. CorpDev is not the
default investigator.

### `4126` — Production deployment review

Review of a deployment pipeline before Production, for new applications or modifications to
an existing Harness pipeline. Before filing, confirm: the product is deployed and tested in
QA, and a Tyler customer is ready.

### `4130` — Troubleshoot deployments

Help creating or updating a deployment pipeline. **Read the deployment documentation first.**

### `4140` — Infrastructure resource or access requests

Infrastructure resources or access. Covers several tools and options — read them carefully
before submitting. Also the destination for infrastructure requests that used to go to the
deprecated `4137`.

### `4147` — Request technical training

Technical introduction and training for a new product development team. If requesting for an
**entire product team as part of a new product/project launch, you must select a JS/IMM
session.**

### `4161` — New product/project deployment pipeline

Help setting up a new project for TCP. Post questions about the requested information in the
**`#tyler-cloud-platform` Slack channel**. Supplying all required information correctly
provisions the pipeline.

### `4170` — Troubleshoot Infrastructure

Troubleshooting AWS infrastructure or **CorpDev-owned Terraform modules**. For
infrastructure CorpDev does not own, they will try to help but ultimate responsibility
remains with the owning team.

### `4175` — Move Product Registration

Moves a product registration currently maintained via a bootstrapper to the new Product
Catalog. Provide the product's **registration-id** and name.

### `4176` — GitHub Access Request

Access to the Tyler GitHub Enterprise. **Create your GitHub user id first.**

---

## Group 3332 — Forge and Tyler Components Web (complete)

Design-system requests. These are **not** Ops Center or Identity topics — they belong to the
Forge/TCW team — but they live on the same CorpDev portal, so they are catalogued here.

| ID | Request type |
|---|---|
| `4132` | Request new component |
| `4139` | Request enhancement to component |
| `4157` | Report a component bug |
| `4146` | Request a new icon |
| `4155` | Request new illustration |
| `4167` | Request empty or error state |
| `4168` | Request content writing |
| `4148` | Request UX Consulting |
| `4160` | App Launcher Application (add an app to the application launcher) |
| `4163` | Request Glossary Addition |
| `4169` | Request Glossary Change |
| `4156` | Forge Feedback (feedback on the Forge website) |

---

## Group 3330 — 3rd Party Solutions

### `4135` — OneTrust: 1st Party Cookie & 3rd Party Cookie/Solution Reporting

Updates OneTrust cookie and third-party solution reporting for **public** applications.
**READ ME FIRST:** only for TCP product teams with public applications running and
accessible through the TCP domains.

---

## Group 3331 — Internal CorpDev ONLY

Contains `tcpsd test` and `Security Event`. **Not for product teams** — do not recommend
these.
