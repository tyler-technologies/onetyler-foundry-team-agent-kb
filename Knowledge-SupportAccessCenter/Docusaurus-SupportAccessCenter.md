# Support Access Center (SAC) — Concepts, Administration, and Usage

Source: Docusaurus — *OneTyler Blueprint, App Guides > Ops > Support Access Center* (`docs/app-guides/ops/support-access-center/**`)
Domain: Support Access Center
Audience: Tyler product engineering teams adopting SAC; Support Council representatives administering SAC groups; Tyler operational staff making access requests to customer installations; customer Org Admins approving/denying those requests.

This document covers what SAC is, compatibility constraints with Org Identity Tier and Workspace OnPrem Target, the engineering requirements for products adopting SAC (security API + revoked webhook), SAC group concepts, how Support Council reps create/administer groups, how Tyler staff make/extend/revoke access requests, the customer's role in approvals, and history/auditing.

**Companion documents (cross-domain):**
- `../Knowledge-OpsCenter/Docusaurus-Terminology.md` — see *Identity Workforce* (Workforce Direct / Managed / Delegated), *Organization*, *Workspace*, *Org Admin*, *Tyler Ops User*.
- `../Knowledge-OpsCenter/Docusaurus-OpsCenter.md` — context on Org Identity Tier and Workspace OnPrem target (both gate SAC compatibility).
- `../Knowledge-Shared/Conf-OneTylerTickets.md` — the ticket for **enabling SAC on a Workforce Managed org with OnPrem Target=Gateway** (form `…/create/4149`).

---

## How to use this guide (quick decision guide)

**If the user is asking one of the five Foundry starting prompts**, jump straight to *Starting prompts — quick answers* below. Those answers are self-contained and link out to the deeper sections when more detail is needed.

| If the user wants to… | Go to section |
|---|---|
| Get a direct answer to one of the five Foundry starting prompts | **Starting prompts — quick answers** |
| Understand what SAC is and why it exists | **Introduction** |
| Check whether SAC is supported on a particular org/workspace | **Compatibility with Org Identity Tier + Workspace OnPrem target** |
| Enable SAC on a Workforce Managed + Gateway org | **Enabling SAC on WM/Gateway** |
| Understand SAC Groups and Support Council role | **SAC groups** |
| Know what an adopting product team must build | **Engineering requirements** |
| Understand the Security API (used by products) | **Security API** |
| Understand the support-access-revoked webhook | **Support Access Revoked Webhook** |
| (Tyler staff) Make an access request | **Making a support request** |
| (Tyler staff) Extend or revoke an existing request | **Extending or revoking** |
| (Customer Org Admin) Approve or deny a request | **Customer approval workflow** |
| Find environment URLs for SAC | **Links to SAC** |
| Find environment URLs for SAC group administration | **Group administration links** |
| Audit SAC history | **History and auditing** |
| Find out who to contact for permissions | **Getting administrative permissions** |

---

## Starting prompts — quick answers

These are the canonical answers to the five **Foundry starting prompts** that users see when first interacting with the SAC agent. Each answer is self-contained; deeper detail lives in the sections that follow. **The chatbot should prefer these answers verbatim when the incoming question matches one of these prompts** — they are deliberately worded to start the conversation on the right foot.

### How do I get access to Support Access Center?

If you are a **Tyler staff member with an `@tylertech.com` email**, you already have access to Support Access Center — **no special authorization or pre-approval is required to sign in.** Go to the SAC dashboard for your environment:

- TylerPortico (production): https://admin.tylerportico.com/platform/support-access-center/dashboard
- TCPQA: https://admin.tcpqa.com/platform/support-access-center/dashboard
- TCPCI: https://admin.tcpci.com/platform/support-access-center/dashboard

What *does* require setup is **requesting access to a particular product on a customer workspace**. The *Select products* step of the request wizard is filtered to only the products your **SAC user group memberships** allow. If, after logging in, the product you need is not listed, contact your product's **Support Council representative** to be added to the right SAC group. See *Who can use SAC* and *Making a support request* for the full flow.

(Non-Tyler email logins are not supported. Support Council representatives who need to **administer** SAC groups follow a separate, narrower path — see *Getting administrative permissions* — but that audience is specifically trained for the role and is not the typical asker.)

### How do I integrate my product with Support Access Center?

A product that wants to adopt SAC must meet **all** of the following engineering requirements:

1. **Integrated with Identity Workforce (Gateway).** SAC is not supported over Workforce Managed + Okta. See *Compatibility with Org Identity Tier + Workspace OnPrem target*.
2. **Registered in the Tyler Cloud Platform**, including any application definitions that expect to check user access.
3. **Indicate in product registration that the product has adopted SAC.** *(Capability not yet available — will be added in the future.)*
4. **Adopt the Security API (`tcp-login-security-api` v1)** to query whether a user has access to your application on a given workspace: `GET /platform/login-security/api/v1/checkaccess/{sub}/workspace/{workspaceKey}/app/{appRegistrationId}` on the environment host. For SAC, the relevant response fields are `supportAccess.hasAccess` / `supportAccess.expiresOn` and `supportAccessUserGroups` — everything else on the response (`userIsMemberOfOrg`, `productGroupAccess`, `userGroups`) is **not used by SAC**. Docs at `/architecture/cloud-platform-api/tcp-login-security-api/`.
5. **Subscribe to the `support-access-revoked` webhook event** so the product can terminate active sessions immediately when access expires or is revoked. Filter fields available at subscription: `OrganizationKey`, `Sub`, `Username`. Each payload includes `Sub`, `ProductRegistrationIds`, and `WorkspaceKeys` — that combination identifies which sessions to kill. Subscription docs at `/platform-architecture/service-architecture/Webhooks/subscribing-to-a-webhook/`; event docs at `https://github.com/tyler-technologies/tcp-webhook-api/blob/main/docs/SUPPORT-ACCESS-MESSAGES.md`.

A product is **not** considered to "support SAC" until **both** #4 (Security API) and #5 (revoked webhook) are in place — that pair is non-negotiable. See *Engineering requirements*, *Security API*, and *Support Access Revoked Webhook* for the full detail, including the sample JSON response and webhook payload.

### How do I request access to my product for a customer installation?

From the SAC Dashboard for your environment (links above), click **Request access** and walk through the four-step wizard (*Making a support request*):

1. **Access details** — pick the **Organization** and the **Access through** value, paste a **support ticket link** (the Search icon brings up active CRM cases for the org so you can auto-fill from one), and enter an **Access reason** that will make sense to the customer if manual approval is required.
2. **Select products** — the list is filtered to products you can reach via your SAC group memberships. If the product you need isn't there, contact your Support Council rep. At least one product is required.
3. **Select workspaces** — at least one workspace required.
4. **Review** — confirm details, then click **Request access**.

What happens next depends on the org's Admin Center *Tyler access* setting:

- **Full access** (the default) — your request is **auto-approved** and appears under **MyAccess** on the dashboard. You receive a "System approved" email.
- **Limited access** — your request goes into **Pending Approval** and the customer Org Admin receives an email with **Approve / Deny** buttons. Once they decide, you receive an email naming the client user who approved or rejected the request.

See *Customer approval workflow* for the customer-side flow.

### How do I extend access?

From the **active request's details page**, open the right-side **Actions** menu → **Extend access** → pick a new expiration date (up to the allowable limit) → **Save**. (See *Extending or revoking*.)

Two things to keep in mind:

- **Extensions go through the same approval policy as the original request.** If the org is in **Full access**, your extension is auto-approved. If in **Limited access**, the customer Org Admin must approve the extension through the same email workflow as the original.
- **Extensions create a second access-request record** on the dashboard — the original plus the extension. This is by design, to preserve the audit trail. If you later want to fully revoke access, you must **revoke both records** — revoking only the extension leaves the original active.

### How do I see past access?

SAC provides two views of access history (*History and auditing*):

- **Per-organization view** — from the **Organizations** view, click into an organization, then click the **History** button on the org details page. This shows the history of access requests **scoped to your user and that org**. The org details page also links out to the **CRM Record**, **Ops Center**, **App Directory**, and **Community App Directory** for the same org.
- **Global History view** — the **History** view in the SAC dashboard shows all access-request activity. **Support Council reps and product teams are strongly encouraged to periodically audit access history for their product(s) using this view.**

SAC does not currently expose a programmatic / API path to access history — these views are UI-only.

---

## Introduction

**Support Access Center (SAC)** provides a framework for a **standardized, secure, time-bound, transparent, and customer-controlled** approach to providing access to **customer installations** for Tyler's operational staff.

SAC introduces the concept of **SAC User Groups**. A Tyler staff user's membership in these groups entitles them to **request access to specific products** installed against a workspace.

### Who can use SAC

When a Tyler staff member asks "how do I access SAC?" the answer is almost always one of these two:

- **Logging into SAC (the dashboard and the request workflow)** — **any Tyler staff member with an `@tylertech.com` email** can sign into SAC and reach the dashboard. **No special authorization, group membership, or pre-approval is required just to log in.** Non-Tyler email logins are not supported.
- **Requesting access to a particular product on a customer workspace** — the staff member must be a member of an SAC user group that has been **mapped to that product** by the product's Support Council representative. The *Select products* step in the request wizard is filtered to only the products reachable via your group memberships, so a staff member who has logged into SAC but has no relevant group memberships will simply see no products available to request. If you need access to a product you don't see, contact your product's Support Council rep.

(A third, much narrower path — **administering SAC groups** — applies only to Support Council representatives and is documented separately under *Group administration (Support Council reps only)* → *Getting administrative permissions*. Those reps are specifically trained for the role and are not the typical audience asking "how do I access SAC?")

---

## Compatibility with Org Identity Tier + Workspace OnPrem target

SAC is **not compatible with all combinations** of Organization Identity Tier and Workspace OnPrem target. Check both before assuming SAC support.

- To check the **Identity Tier**: Ops Center > Orgs > (search and select org) > Details > **Identity Workforce product tier**.
- To check the **Workspace OnPrem target**: from the same Org Details page → **Manage workspaces** > **OnPrem target** column.

| Identity Tier | Workspace OnPrem Target | SAC Support |
|---|---|---|
| **Workforce Managed** | **Okta** | **No SAC support.** |
| **Workforce Managed** | **Gateway** | **SAC supported after enablement.** Note: After enablement, **all users will see the Gateway login screen**; they can dismiss it by entering their userid and selecting **"Remember me"**. **Alert the customer to the new login screen before enabling**, then **reach out to Jason Howard** to request the Identity Configuration change for the organization. |
| **Workforce Direct / Workforce Delegated** | **Gateway** | **Full SAC support.** Users will also see the Gateway login screen, dismissible by clicking **"Remember me"**. |

### Enabling SAC on WM/Gateway

For Workforce Managed + Gateway orgs, SAC must be **explicitly enabled**:

- File the ticket: `https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3329/create/4149` (see `Knowledge-Shared/Conf-OneTylerTickets.md` → *Support Access Center*).
- **Before enabling**, alert the customer to the updated Gateway login screen they will see post-change.

---

## SAC groups

SAC groups are administered by **Tyler's Support Council**. Each product has a representative (or representatives) in the Support Council, responsible for creating groups, associating them with products, and managing user membership.

Before creating SAC groups, the product team must decide whether to provide **fine-grained access control** to specific operational roles (Inquiry, Configuration setup, etc.) or use **all-or-nothing access**.

- **All-or-nothing** — simplest. **A single SAC group** associated with the product; all users needing access live in that one group.
- **Fine-grained access control** — a **separate SAC group per access level**. Each group is mapped to the product. Users go into the group matching the maximum level of access they should have for their job functions.

All-or-nothing is simpler but might be too permissive. The fine-grained model takes more setup but gives finer control.

---

## Engineering requirements (for products adopting SAC)

A product must meet ALL of the following to adopt SAC:

- Must be **integrated with Identity Workforce (Gateway)**.
- Must be **registered as a product in the Tyler Cloud Platform**, including any application definitions that expect to query for a user's ability to access the application.
- Must **indicate in its product registration that it has adopted SAC**. *(Not currently available; will be available in the future.)*
- Must adopt the **`tcp-login-security-api` v1** to query whether the user has access. Docs at `/architecture/cloud-platform-api/tcp-login-security-api/` on the same Docusaurus site.
- Must adopt the **`support-access-revoked` webhook event** so the product/application is notified when access expires for a user, allowing active sessions to be terminated immediately. Docs at `https://github.com/tyler-technologies/tcp-webhook-api/blob/main/docs/SUPPORT-ACCESS-MESSAGES.md`.

---

## Security API (`tcp-login-security-api` v1)

The Security API tells you whether a user can access an application of a product installed against a given workspace.

### Inputs
- Identity sub of the Tyler staff user.
- Application registration id.
- Workspace key.

### URL

```
https://api.{tcpci, tcpqa, tylerportico}.com/platform/login-security/api/v1/checkaccess/{tyler-user-subject-id}/workspace/{workspace-key}/app/{app-registration-id}
```

### Output (JSON sections)

- **API Inputs** — Repeats inputs: `identitySub`, `appRegistrationId`, `workspaceKey`.
- **`userIsMemberOfOrg`** — **Not used for SAC.** `true` if the Tyler staff member exists as a workforce user in the organization.
- **`supportAccess`** — When `hasAccess = true`, the Tyler staff user has been authorized to access the product/application in the workspace **until `expiresOn`**.
- **`supportAccessUserGroups`** — All SAC groups the user is part of. For fine-grained access models, the application can decide what to permit based on the group(s) the user is in.
- **`productGroupAccess`** — **Not used for SAC.** Legacy: ACL flags (`hasAppGroupAccess`) and System Administrator flag on workforce profile (`hasSystemAdminAccess`).
- **`userGroups`** — **Not used for SAC.** Admin Center user groups the staff user is part of.

### Sample JSON

```json
{
  "identitySub": "4A6z3ODI7NME9n61xe8gXxp-",
  "appRegistrationId": "workforceApp-erp-pro-10",
  "workspaceKey": "tylertownwa",
  "userIsMemberOfOrg": true,
  "supportAccess": {
    "hasAccess": true,
    "expiresOn": "2025-08-28T04:00:00+00:00"
  },
  "supportAccessUserGroups": [
    {
      "name": "M&S Development",
      "description": "M&S Development team"
    }
  ],
  "productGroupAccess": {
    "hasAppGroupAccess": false,
    "hasSystemAdminAccess": false
  },
  "userGroups": [
    {
      "name": "ERP Pro Users",
      "description": "ERP Pro Users"
    }
  ]
}
```

---

## Support Access Revoked Webhook

Subscribing to the `support-access-revoked` webhook is a **one-time** requirement. Available filter fields at subscription time:

- `OrganizationKey`
- `Sub`
- `Username`

When a message arrives at the product endpoint, the **combination of `Sub`, `ProductRegistrationIds`, and `WorkspaceKeys`** can be used to terminate any active sessions for the Tyler staff user in the product installation.

Subscription docs at `/platform-architecture/service-architecture/Webhooks/subscribing-to-a-webhook/`. Event docs at `https://github.com/tyler-technologies/tcp-webhook-api/blob/main/docs/SUPPORT-ACCESS-MESSAGES.md`.

### Sample webhook payload

```json
{
  "MessageType": "support-access-revoked",
  "OrganizationKey": "orgKey",
  "Sub": "sub",
  "Username": "username",
  "ProductRegistrationIds": [
    "product-registration-id1",
    "product-registration-id2"
  ],
  "WorkspaceKeys": [
    "workspaceKey1",
    "workspaceKey2"
  ]
}
```

---

## Links to SAC (Tyler staff dashboard for access requests)

| Environment | Support Access Center Dashboard URL |
|---|---|
| TCPCI | https://admin.tcpci.com/platform/support-access-center/dashboard |
| TCPQA | https://admin.tcpqa.com/platform/support-access-center/dashboard |
| TylerPortico | https://admin.tylerportico.com/platform/support-access-center/dashboard |

---

## Admin Center Tyler Access setting (org-level approval policy)

Customers control the org-level approval policy through Admin Center. Options:

- **Full access** — *Default when an org is provisioned.* All support requests for the org are **auto-approved**.
- **Limited access** — All support requests **must be explicitly approved by the customer Org Admin**.

This setting is the gating factor between auto-approval and the manual workflow described below.

---

## Making a support request (Tyler staff)

**Prerequisite:** Logging into SAC requires no special authorization — any Tyler staff member with an `@tylertech.com` email can reach the dashboard (see *Who can use SAC*). To **request access to a specific product**, however, your Support Council representative must have added you to a SAC user group that has been mapped to that product. If you log in and find the *Select products* step shows no products, that's the signal — contact your Support Council rep to be added to the right group.

Steps in the **Request access** wizard from the SAC Dashboard:

1. **Access details tab:**
   - Select or enter the **Organization** and **Access through** values.
   - Provide a **link to the support ticket**. Expected to point to a CRM support ticket, but can be any other link that justifies the access request. The **Search icon** brings up all active support cases for the org — select one to auto-fill.
   - Enter an **Access reason** that will make sense to the customer if manual approval is required.
   - Click **Next**.
2. **Select products tab:**
   - Filter and select the products. The product list is **constrained to those reachable via your SAC group memberships**. If you don't see the product you need, contact your Support Council rep to be added to the right group.
   - At least **one** product required. Click **Next**.
3. **Select workspaces tab:**
   - Filter and select workspaces. At least **one** required. Click **Next**.
4. **Review tab:**
   - Confirm details. Click **Request access** to submit (or **Back** to correct).

After submit:

- If the org is **Full access**: request is **auto-approved**; appears in **MyAccess** on the dashboard.
- If the org is **Limited access**: request waits for customer approval; appears under **Pending Approval** on the dashboard.

---

## Customer approval workflow (Limited access orgs)

When **Tyler access = Limited access**, a customer Org Admin must approve. Workflow:

1. Customer Org Admin **receives an email** with **Approve / Deny** buttons (template subject to change).
2. Clicking either button prompts the Org Admin to log into their organization's **Admin Center**.
3. A dialog presents request details; the Org Admin **Approves** or **Denies**.

### Approval / rejection notifications back to Tyler staff

- **Auto-approval** — email notification stating **System** approved.
- **Manual approval/rejection** — email specifying the name of the client user who approved or rejected the request.

---

## Viewing request details

Click any request from the **Dashboard** or from **History** to see details.

## Extending or revoking

From an **active request's** details, the right-side **Actions** menu offers:

- **Extend access** — Pick a new expiration date up to the allowable limit, then **Save**. Depending on the Tyler access setting, this is **automatic** or routed through the **manual client approval workflow** described above. If approved, the dashboard shows **two access request records** — the original and the extension — to preserve the audit trail.
- **Revoke access** — Click **Revoke access** then **Confirm** in the dialog. **Important:** revoking an *extension* request only revokes the extension. If you want to fully revoke all access, you must **also revoke the original request** if it is still active.

---

## History and auditing

### Per-organization view

The **Organizations** view lists orgs (Organization key, Name, Tyler access). Clicking an org shows its details with convenient links to the **CRM Record**, **Ops Center**, **App Directory**, and **Community App Directory**. The **History** button shows a filtered view of history scoped to your user and that organization.

### Global History view

The global **History** view shows all access-request activity. **Strongly recommended:** Support Council reps and product teams **periodically audit access history** for their product(s) using this view.

---

## Group administration (Support Council reps only)

This section applies **only** to Support Council representatives for product teams. The administration work is **setup of groups + association with products + ongoing maintenance of user membership**.

### Getting administrative permissions

If you are an approved Support Council representative, reach out to **Vijay Venkataraman** or **Jason Howard** to be granted the requisite permissions. **Permissions are normally granted only in production (TylerPortico).** If you also need access to other environments, specify when reaching out.

### Group administration links

| Environment | Admin Center — tylertechnologiestx | Support Access Center |
|---|---|---|
| TCPCI | https://tylertechnologiestx-admin.tcpci.com/org/admin-center/user-groups | https://admin.tcpci.com/platform/support-access-center/group-access |
| TCPQA | https://tylertechnologiestx-admin.tcpqa.com/org/admin-center/user-groups | https://admin.tcpqa.com/platform/support-access-center/group-access |
| TylerPortico | https://tylertechnologiestx-admin.tylerportico.com/org/admin-center/user-groups | https://admin.tylerportico.com/platform/support-access-center/group-access |

### SAC Group setup — Step 1: decide model with engineering

Work with product engineering to determine whether the product is adopting **all-or-nothing** or **fine-grained** authorization:

- **All-or-nothing** → a **single SAC group** for the product is sufficient.
- **Fine-grained** → one SAC group per access level (e.g., Inquiry-only for support; Setup for implementation). Each group is mapped to the product. Users go into the group matching their max permitted access.

### SAC Group setup — Step 2: create groups in the `tylertechnologiestx` Admin Center

Use the Admin Center link above for `tylertechnologiestx`. **Caution:** Tyler staff with access can see groups from **other** product teams — take care not to disturb those groups.

**Group naming convention:**

```
Group Name = {Division/Major Group code} - {Optional Product} - {Optional Team, Role, or Permission Type}
```

**Division/Major Group codes:**

| Code | Represents |
|---|---|
| **MS** | Municipal and Schools |
| **AT** | Appraisal and Tax |
| **CJ** | Courts and Justice |
| **PS** | Public Safety |
| **SF** | State and Federal |
| **ECC** | ERP, Civic, and Cybersecurity |
| **OT** | One Tyler |

Suggestion: for all-or-nothing, the group name is `{Division/Major Group code} - {Product}`. For fine-grained, add the team/role/permission type suffix.

**Wizard:**

1. `tylertechnologiestx` Admin Center → **User groups** → **Create user group**.
2. **Add User Group** dialog — enter the structured group name and a useful description. Click **Next**.
3. **Add Users** tab — optionally add an initial user list (can be done later). Click **Next**.
4. **Summary** tab — verify, then **Save & close**.
5. Repeat for each SAC group needed.

### SAC Group setup — Step 3: associate group(s) with product(s)

Use the SAC application's **Group Access** link (above) to find the groups you created. Click into a group → **Add product** → select one or more products in the wizard → **Add**. After this, users in this group can make access requests for the selected products.

### Adding/removing users from existing SAC groups

- Open the user group in the `tylertechnologiestx` Admin Center.
- **Add users** wizard — select users, **Save & close**.
- To remove: select users in the user group details → **Remove selected users**.

### Periodic auditing

It is **strongly recommended** to periodically audit access history for your product(s) using the SAC History view (see *History and auditing* above).

---

## Changelog

- **09/22/25** — First release of Support Access Center in production.

---

## Notes for the chatbot

- **Always check both Identity Tier and OnPrem target** when a user asks "does SAC work for this org?". WM/Okta is the **only** unsupported combination. WM/Gateway needs explicit **enablement** + customer pre-notification + Jason Howard.
- For **WM/Okta orgs**, the chatbot should suggest the customer needs to be moved to WM/Gateway (or WD/Gateway) to get SAC — and flag that this requires OneTyler coordination (Jason Howard) plus a customer-facing change to the login screen.
- **Any Tyler staff member with an `@tylertech.com` email can log into SAC and reach the dashboard — no special authorization or group membership is required just to sign in.** What is gated by SAC group membership is the ability to **request access to a specific product**: the *Select products* step of the request wizard is filtered to products reachable via the staff member's SAC group memberships. When the user asks "how do I get access to SAC?", default to this login-is-open interpretation — it's by far the most common framing. Only mention the Support Council administration path as a brief aside, since that audience is specifically trained for the role and rarely asks the chatbot this question. Non-Tyler email logins are not supported.
- The **"Tyler access" Admin Center setting** is the gating control between auto-approval (**Full access**, default) and manual approval (**Limited access**). When a user reports their request is stuck, first check the org's Tyler access setting.
- **Extensions create a second audit record** — if a user thinks they have "duplicate" requests after extending, that is by design (audit trail preservation). Revoking the extension does NOT revoke the original; remind users they must revoke both if they want all access gone.
- **Magic-link / approval emails** are how the customer Org Admin learns about requests — set expectations that an Org Admin must actually exist (and have email reachability) for a Limited-access org's manual workflow to function.
- For products **adopting SAC**, the chatbot should never claim a product "supports" SAC without verifying both the Security API integration AND the support-access-revoked webhook subscription — both are required.
- **Group naming convention is enforced** (`{DivisionCode} - {Product} - {Role}`) — when a Support Council rep asks the chatbot for group-name suggestions, always use the convention with the right division code from the table above.
- **Permission grants for group administration default to production only.** If a Support Council rep needs non-prod, they must explicitly say so when reaching out to Vijay Venkataraman or Jason Howard.
- This SAC `Knowledge-SupportAccessCenter/` corpus is **its own Foundry agent domain** — separate from `Knowledge-OpsCenter/`. Cross-domain references (Org Identity Tier, OnPrem target, ticket form 4149) should still resolve via the companion Ops Center documents listed at the top.
