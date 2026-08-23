# Ops Center — Tickets and Permissions Catalog

Source: Confluence — *Tyler Cloud Platform (TCP) | Ops Center Related Tickets and Permissions*
Domain: Ops Center
Audience: Tyler product, deployment, implementation, and identity-support staff who need to file a ticket against CorpDev to do something in Ops Center, Admin Center, or related TCP tools.

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
- **Ticket link:** *To be published in August '26.* (No live ticket URL yet — note this when answering.)
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
- **Ticket:** https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3329/create/4149
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
- The **non-standard workspace request** ticket is not live yet (publishing August '26). Until then, tell the user the form is pending and relay the suffix rules (standard set + numbered extensions like `impl1`/`test2`; >7 workspaces gets scrutiny) rather than handing out a URL.
- The **Environment not working** ticket (4129) is in **group 3328**, not the usual 3333 — and is gated on the filer having already proven a platform-wide issue with logs. Don't recommend it for ordinary single-org outages.
- Internal-org creation is gated and largely manual — direct users to Vijay Venkataraman for `+Create Internal`.
- Confluence wiki links in this document use Tyler-internal paths (e.g. `/wiki/spaces/...`). They are usable from inside Tyler systems; tell external readers they are internal references.
