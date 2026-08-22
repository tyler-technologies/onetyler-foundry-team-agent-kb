# Identity Workforce — Workspace Retargeting and Org Migration (Workforce Managed → Workforce Direct)

Source:
- **Part 1 (Tyler-staff retargeting):** Presentation deck `GatewwayRetargetingAndMigration.pptx` (slides 1–11) and the rendered video `Part1-OverviewAndGatewayRetargeting.mp4` (296s). Step-by-step demo content distilled from scene-change frame extraction of the video.
- **Part 2 (customer-side migration):** Slides 12–15 of the same deck and the rendered video `Part2-WorkforceDirectMigration.mp4` (266s). Step-by-step demo content distilled from scene-change frame extraction of the video. Example IdP used: **Google Workspace**.

Domain: Ops Center

Audience:
- **Part 1:** Tyler operational staff (deployment, implementation, support) responsible for **retargeting customer workspaces** from Workforce Managed (Okta-based) to gateway mode. Requires cross-product coordination, may require redeployments.
- **Part 2:** **Customer Org Admins** (or Tyler Org Admins acting in that capacity) executing the final identity-federation migration via Admin Center, after Tyler has completed Part 1.

This document explains the two-part WM→WD conversion: (a) **Retargeting** — a Tyler-staff-only workspace-flag flip plus per-product redeployment coordination, executed in Ops Center; (b) **Migration** — the customer-side federation reconfiguration in Admin Center.

**Companion documents in this same Knowledge folder:**
- `Conf-GatewayOperationalTesting.md` — Gateway-readiness validation (a prerequisite for WM→WD eligibility).
- `Conf-OpsCenterTickets.md` — see *Orgs > Organization Details > Workspace migration* for the gating permission/ticket route.
- `Docusaurus-Terminology.md` — *Identity Workforce* (Workforce Direct / Managed / Delegated) canonical definitions; also "Gateway is internal code, Identity Workforce is the customer-facing brand."
- `Docusaurus-OpsCenter.md` — *Workspace migration* and *Add/Reset AD Agent account* / *Federation* setup flows in Ops Center.
- `Misc-Links.md` — the live Confluence page *Tyler Cloud Platform (TCP) | Workforce Managed to Workforce Direct Retargeting and Migration* (`/wiki/spaces/TTI/pages/386635412/`) is bookmarked there.

---

## How to use this guide (quick decision guide)

| If the user wants to… | Go to section |
|---|---|
| Understand the two-part Tyler / customer split | **Two-part model** |
| Disambiguate "Retargeting" vs "Migration" terminology | **Terminology — Retargeting vs Migration** |
| See the 5-step process diagram | **Process overview diagram** |
| Check whether an organization is eligible | **Eligibility checklist** |
| Know how to get the Workspace Migration permission | **Permission gate** |
| Understand the cross-product coordination warning | **Cross-product coordination** |
| Avoid SubjectId-based post-migration breakage | **SubjectId reset warning** |
| (Tyler staff) See the per-workspace Ops Center clickflow | **Part 1 — Ops Center step-by-step** |
| (Customer) See the Admin Center click-by-click | **Part 2 — Admin Center step-by-step** |
| Find the click points in Google Cloud Console (sample IdP) | **Part 2 — IdP-side configuration (Google Workspace example)** |
| Know about the activation revert window | **Activation, revert, finalize** |
| Know about PASC support routing change | **PASC users — routing change post-migration** |

---

## Two-part model

This is a **two-part series**, originally published on Tyler Community:

- **Part 1: Gateway Retargeting** — Tyler Staff only, executed in **Ops Center**. Covered in detail below.
- **Part 2: Gateway Migration** — Executed in **Admin Center** by **Client or Tyler Org Admin**. Step-by-step below.

**The two parts run in sequence, per workspace.** You cannot start Part 2 until Part 1 is complete on all workspaces in the org and the Tyler staff member has enabled self-service migration.

---

# PART 1 — GATEWAY RETARGETING (Tyler Staff only, Ops Center)

## Terminology — Retargeting vs Migration

These two terms are precise — do not use them interchangeably:

- **Retargeting** — *Tyler Staff only.* Facilitates deployment / redeployment of **gateway-ready** versions of Tyler products in **gateway mode**, by setting a **flag on a workspace** that tells deployment tools (e.g., Tyler Deploy) to set the product's configuration to use gateway settings. Done in **Ops Center**.
- **Migration** — Comes **AFTER** retargeting is complete on all workspaces in the organization **AND** self-service is enabled. Allows a **Client Org Admin or Tyler Org Admin** to **migrate existing federations** or **add new federations** through **Admin Center**. Those federations then provide authentication for all non-Tyler-Tech user ids in the converted Workforce Direct org.

## Overview

This process converts **eligible Workforce Managed (Okta-based) orgs** into **Workforce Direct (Federation-only) orgs**.

- Before starting, **confirm the organization is eligible** (see *Eligibility checklist*).
- The process **requires the customer's involvement** — they must update their existing federations with new redirect URIs in their IdP admin console. You cannot complete the migration without them.

## Permission gate

The **"Workspace Migration"** menu option in **Ops Center > Organization details** is **permission-gated**. Tyler staff must be **granted explicit access** via a support ticket before they can see/use the option.

- See `Conf-OpsCenterTickets.md` → *Orgs > Organization Details > Workspace migration* for the request flow.
- The Confluence runbook bookmarked in `Misc-Links.md` (page `386635412`) is the authoritative live document.

## Eligibility checklist

Before an organization can be migrated WM → WD, it must satisfy **ALL** of the following:

1. **No local accounts.** The customer must **NOT** be using any local accounts (gmail, outlook, etc.) that are **not part of a userid domain they own and federate.**
2. **Existing federation under current Okta tenant.** The customer must already have a federation set up against their current Workforce Managed Okta tenant — that federation is what gets migrated.
3. **All installed Tyler solutions must support Gateway.** Every Tyler product installed for the customer must be Gateway-ready (Core compliance minimum). See `Conf-GatewayOperationalTesting.md`.

### Additional considerations (strong recommendations)

- **Engage the customer's federation contact BEFORE the migration.**
  - Know who owns federation setup on the customer side.
  - That contact must have **Admin Center access** to the org.
  - Brief them to **expect** the Migration option appearing in Admin Center and the work they'll do in their IdP admin console.
- **See *PASC users — routing change post-migration* below.**

## Cross-product coordination

> ⚠️ **The Tyler employee changing the targeting of the workspace is responsible for coordinating retargeting across ALL of the customer's licensed products AND establishing communications with the customer.**

- **Not all products are reflected in Ops Center** at this time.
- You must **analyze the customer's CRM record** to identify additional Identity-Workforce-consuming products that may be installed.
- Each product team owning a Gateway-ready version may need to **redeploy** in gateway mode against the newly-targeted workspace.
- Establish customer communications **early**.

## SubjectId reset warning

> ⚠️ **If any Tyler product tracks `@tylertech.com` users using their Identity SubjectId sourced from the current Workforce Managed Okta tenant, those users may hit access / authorization errors after migration** — because the new Workforce Direct SubjectIds will differ from the old Okta-tenant SubjectIds.

- **Mitigation:** **Reset the SubjectIds of affected users** so the product can map them again post-migration.
- **Test thoroughly** before using on real customer orgs.
- **PASC users with `@tidsupport.com` domain** should **NOT** see disruptions.

## Process overview diagram

The deck (slide 10) shows a 5-step flow with two color tracks (Tyler-staff in Ops Center / Tyler or Client staff in Admin Center):

```
[OC: Tyler Staff only]                              [AC: Tyler or Client Staff]
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Retarget    │→ │   Redeploy   │→ │ Enable self- │→ │  Import or   │→ │  Activate    │
│ each         │  │   gateway    │  │ service for  │  │     Add      │  │  Workforce   │
│ workspace    │  │   versions   │  │  migration   │  │ federations  │  │   Direct     │
└──────┬───────┘  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
       │ ↑
       └─┘ Repeat for each workspace
```

- **Step 1 (OC):** Using Ops Center, mark Workspace as targeting Gateway. If multiple product teams are involved, coordinate / schedule this activity.
- **Step 2 (OC):** (Re)Deploy gateway-ready versions of Tyler solutions. **Repeat Steps 1 + 2 for each workspace.**
- **Step 3 (OC):** When Steps 1 & 2 are completed for all workspaces in the org, the option to enable self-service for migration is available. **Enable it.**
- **Step 4 (AC):** Import and/or Add federations. Refer to documentation for details.
- **Step 5 (AC):** Transition the organization to Workforce Direct.

---

## Part 1 — Ops Center step-by-step

### Setup — navigate to Workspace Migration

1. Open Ops Center → **Orgs** → search for and select the customer organization (example used in video: `tylerschool`).
2. In the left side nav of the org details page, click **Workspace Migration**.
   - URL pattern: `https://admin.{tcpci|tcpqa|tylerportico}.com/portal/ops-center/manage-organizations/<orgKey>/workspace-migration`
   - **If you don't see this menu item**, your account doesn't have the permission — file the ticket (see *Permission gate*).
3. You land on the **org-level Workspace Migration overview page**, showing:
   - **Workspace retargeting** table with all workspaces and a **Target Gateway** column (initially empty — workspaces still target Okta).
   - **Workforce direct migration** section: status: **disabled** with a message that all workspaces must be retargeted first.
   - **Enable self-service migration** button (initially grayed-out / inactive).

### Step 1+2 — Per-workspace retargeting

For each workspace in the org (repeat the loop):

1. Click into a workspace from the **Workspace retargeting** table.
2. The per-workspace view shows:
   - **Name** / **Workspace/Profile** / **Target** (currently `Okta`).
   - **IMPORTANT** warning panel:
     > *You are responsible for validating the organization is ready for migration to the Gateway before making this change. By proceeding you confirm that:*
     > - *Customer org admins are familiar with the migration process and expecting this change.*
     > - *All workspaces on the organization have been retargeted to use the gateway.*
     > - *All non-TCP applications have been redeployed in each workspace after retargeting and are configured to use the Gateway.*
     > - *All non-TCP applications were tested after redeployment to ensure they work satisfactorily.*
   - **Target Gateway** button.
3. Coordinate with product teams: ensure they are ready to (re)deploy their products before clicking Target Gateway.
4. Click **Target Gateway**.
5. **Confirm dialog** appears:
   > *All on-premise or single tenant software will need to be redeployed. This includes all software that are deployed in the cloud as lift-and-shift. Are you sure you want change target to Gateway?*
6. Click **Confirm**.
7. **Toast:** *"Update workspace target success"*.
8. The workspace now shows **Target = Gateway**. A ✓ appears in the **Target Gateway** column on the org-level overview page.
9. Product teams (re)deploy gateway-ready versions of their applications against this workspace. Test after redeployment.
10. **Repeat** for the next workspace.

### Step 3 — Enable self-service migration (once ALL workspaces are retargeted)

1. Return to the org-level Workspace Migration overview page.
2. The **Workspace retargeting** section now shows a green **complete** badge, with ✓ in the Target Gateway column for every workspace.
3. The **Enable self-service migration** button is now **active** (no longer grayed-out).
4. Click **Enable self-service migration**.
5. **Confirm dialog** appears:
   > *Are you sure you want to enable self-service migration? Once enabled, you will no longer be able to change the targeting on any workspaces.*
6. Click **Confirm** — **retargeting becomes locked**; you cannot revert workspace targets after this point (only the migration itself is revertible by the customer; see Part 2).
7. **Toast:** *"Enable direct federation migration successful"*.
8. The **Workforce direct migration** section now shows:
   - Status: **enabled**
   - **Enabled by:** (Tyler staff email, e.g. `vijay.venkataraman@tylertech.com`)
   - **Enabled at:** (timestamp with timezone)
   - **Original Okta Sku:** (e.g. `OktaAdvancedCustomIdp`) — kept for reference / revert.
   - A **Disable self-service migration** button (revert option — available before customer completes Part 2).

This completes the Retargeting part of the process. The customer can now perform Part 2.

---

# PART 2 — MIGRATION (Customer Org Admin, via Admin Center)

> **Who:** Customer Org Admins (or Tyler Org Admins acting in that capacity).
> **Where:** Admin Center for the customer's org (e.g. `https://<org>-admin.tylerportico.com/org/admin-center/`).
> **Trigger:** A Tyler staff member has completed Part 1 (enabled self-service migration). The customer sees a banner and a new Migration menu item.

## Part 2 — Admin Center step-by-step

### Entry point — Admin Center banner + new menu

1. Customer Org Admin logs into Admin Center for the org.
2. **Banner at top of every page:**
   > *You are now using Workforce Direct. Go to the **Migration page** to finalize the migration process.* **Learn more**
3. A new **Migration** menu item appears at the bottom of the **left side nav**, with a notification dot.
4. Click **Migration** (or the "Migration page" link in the banner).
5. URL: `https://<org>-admin.{tcpci|tcpqa|tylerportico}.com/org/admin-center/migration`

### Migration page — landing

The page shows:
- Headline: **"You can now migrate your identity providers to Workforce Direct"**
- 3-step instructions:
  1. To begin the process, click **Import federations**.
  2. Once imported, follow the verification process for each identity provider listed.
  3. When every identity provider has been verified, you can then activate Workforce Direct for your Tyler solutions.
- **More info** box: **Technical overview** link + **Vendor documentation** link.
- **Identity providers** section: empty initially, with message *"Click Import federations to import your current identity providers."*
- Buttons: **Import Federations** | **Add a new provider**.

### Step 1 — Import federations

1. Click **Import Federations** button.
2. **Import federations dialog** appears:
   - Title: "Import federations"
   - Body: *"Select the identity providers to import."*
   - *"Only providers that have a status of **In use** can be imported."*
   - *"Providers with the status of **Staged** will need a domain assigned to it before it is able to be imported."*
   - Table shows existing federations from the org's current Workforce Managed Okta tenant. Each row: Name (e.g. `tylerschool.org`), Type (e.g. `Google`), Date, Status.
3. Select the federation(s) to import.
4. Click **Import federations**.
5. The provider now appears in the **Identity providers** list with status **Staged** (initial state before verification).

### Step 2 — Update redirect URIs at the customer's IdP

> 📌 **The customer's IT admin does this in their own IdP admin console.** Tyler does NOT have access. The Tyler-side staff member must coordinate this step with the customer.

Each imported provider has Tyler-issued **Sign-in** and **Sign-out** redirect URIs that the customer must add to their IdP application config. To find them, click into the imported provider in Admin Center (see Step 3 below) — the Configuration step shows the URIs.

**The two new Tyler-issued URIs** (format):
- **Sign-in:** `https://idgw.{tcpci|tcpqa|tylerportico}.com/tg-federation/<federationKey>/signin`
- **Sign-out:** `https://idgw.{tcpci|tcpqa|tylerportico}.com/tg-federation/<federationKey>/signout-callback`

Where `<federationKey>` is a unique federation identifier specific to the org+provider (e.g. `0i2omttms` in the video example).

### Part 2 — IdP-side configuration (Google Workspace example)

The video demonstrates updating redirect URIs in **Google Cloud Console**. The pattern is the same conceptually for other IdPs (Entra ID, Okta, ADFS) — the screens differ; refer to the IdP's own documentation.

For **Google Workspace**:

1. Open Google Cloud Console → **Google Auth Platform** → **Clients**.
2. Open the existing **TID-W** OAuth 2.0 client (Web application).
3. In **Authorized JavaScript origins**, ADD the new Tyler entry:
   - New entry: `https://idgw.{tcpci|tcpqa|tylerportico}.com`
   - Keep the existing entry (`https://tyler-<orgkey>.oktapreview.com` or similar) — do NOT remove yet.
4. In **Authorized redirect URIs**, ADD the new Tyler-issued URIs:
   - New URI: `https://idgw.<env>.com/tg-federation/<federationKey>/signin`
   - New URI: `https://idgw.<env>.com/tg-federation/<federationKey>/signout-callback`
   - Keep the existing Okta URIs — do NOT remove yet.
5. Click **Save**.
6. **Wait for the changes to propagate** — Google's note says *"It may take 5 minutes to a few hours for settings to take effect"*.

### Step 3 — Verify federation in Admin Center (Edit OIDC provider wizard)

Back in Admin Center → Migration page:

1. Click into the imported provider row (status: Staged).
2. **Edit OIDC provider** dialog opens — a 3-step wizard: **Configuration | Testing | Domains**.

#### Step 3a — Configuration tab (Required)

Fill in:
- **Display name** (e.g., `tylerschool.org`). Status badge: **Staged**.
- **Redirects and scopes** (Tyler-issued, read-only — these are the URIs you added to the IdP):
  - **Sign-in redirect URI** (e.g., `https://idgw.tcpqa.com/tg-federation/0i2omttms/signin`)
  - **Sign-out redirect URI** (e.g., `https://idgw.tcpqa.com/tg-federation/0i2omttms/signout-callback`)
  - **Required scopes:** `openid, profile, email`
- **Authority data**:
  - **Authority** (e.g., `https://accounts.google.com` for Google)
  - **Flow:** `Authorization Code Flow`
  - **Client ID** (from the IdP — e.g., the Google OAuth client ID)
  - **Client secret** (from the IdP)
  - **Secret expiration** (date)
  - **Get claims from user info endpoint** (toggle, IdP-dependent)
3. Click **Next**.

#### Step 3b — Testing tab

The dialog explains:
> *You can test the details of your provider by clicking the button below. This test will automatically open a new tab to test logging into your new identity provider. If the test is successful, the testing tab will close and you can continue to the next step where you will assign domains to your new identity provider.*
> *You may also skip this step by clicking Next if you do not want to perform a test.*

1. Click the test button.
2. A new browser tab opens to test the federation login.
3. On success, the tab closes and the dialog shows: **"Test successful!"** ✓.
4. Click **Next**.

#### Step 3c — Domains tab

1. Assign domain(s) to this provider (the userid domains it owns).
2. Click **Save**.

After save, back on the Migration page:
- Provider status changes from **Staged** → **Ready** (with tooltip showing associated domain count, e.g., *"1 associated domain"*).
- Steps 1 and 2 on the instruction list now have green ✓ checkmarks.
- **Activate Workforce Direct** button becomes active.

### Step 4 — Activate Workforce Direct

1. Click **Activate Workforce Direct** button.
2. **Success dialog** appears:
   - Thumbs-up icon.
   - **"Workforce Direct is active"**
   - *"You can revert these changes within the next 3 days if any issues arise."*
3. Click **Close and reload application**.

### Activation, revert, finalize

After activation, the Migration page changes state:
- Headline: **"Workforce Direct activated"**
- Message: *"Workforce Direct activated. You have **N** days left to revert your changes. To undo your changes, begin the process by clicking **Revert changes**."*
- Two buttons: **Finalize Workforce Direct** | **Revert changes**
- Identity providers table: status now shows **In use** (no longer Ready).

Customer choices during the revert window:
- **Finalize Workforce Direct** — commits permanently, removes the revert option, removes the Migration menu item from Admin Center, and removes the migration banner. The org is now fully on Workforce Direct.
- **Revert changes** — rolls back to Workforce Managed; status returns to Ready; the customer can re-Activate later when ready.

#### Post-finalization state

After Finalize:
- **Migration menu item disappears** from the left nav.
- The migration banner at the top of Admin Center pages is gone.
- The org is fully on Workforce Direct.
- The customer's IT admin can now safely remove the OLD Okta redirect URIs from their IdP (they kept them for the revert window — see Step 2 of the IdP-side config).

---

## PASC users — routing change post-migration

If the organization has utilized the **PASC** (Public Access Support Center) support system **prior to migration**, the PASC users will be **routed to `tidsupport.com`** after the migration is completed.

- **PASC users with `@tidsupport.com` domain should NOT see any disruptions** after migration.
- Communicate this routing change to the customer's support stakeholders before completing migration.

---

## Notes for the chatbot

- **"Retargeting" and "Migration" are NOT synonyms.** Retargeting is the **Tyler-staff workspace-flag flip + product redeployment coordination** in Ops Center. Migration is the **customer-side federation reconfiguration** in Admin Center. Migration is gated by Retargeting being complete on all workspaces in the org AND self-service being enabled.
- **The Workspace Migration menu option in Ops Center is permission-gated** — request access via ticket (`Conf-OpsCenterTickets.md`).
- **Eligibility is 3 hard requirements:** no local accounts, existing federation under current Okta tenant, all installed Tyler products support Gateway. If ANY is not met, the org is not eligible — explain the specific blocker.
- **Cross-product coordination is the responsibility of the Tyler employee initiating the retargeting** — they must check the customer's CRM record for products that may not yet be in Ops Center.
- **SubjectId reset is needed for @tylertech.com users tracked by SubjectId.** PASC users on `@tidsupport.com` are NOT at risk.
- **Use customer-facing terminology:** "Identity Workforce", "Workforce Direct", "Workforce Managed". Internally "Gateway" is fine.
- **Per-workspace flow in Ops Center:** Workspace Migration menu → click into workspace → Target Gateway button → Confirm dialog (4 confirmations listed) → repeat for each workspace → org-level Enable self-service migration button → Confirm (locks targeting).
- **Enabling self-service migration LOCKS retargeting** — once enabled, targets can't be changed. There is a "Disable self-service migration" button that reverts the enable, but only before the customer activates in Part 2.
- **Customer-side flow in Admin Center:** Migration menu → Import Federations dialog → select providers → status: Staged → customer updates IdP redirect URIs → click into provider → Configuration / Testing / Domains wizard → status: Ready → Activate Workforce Direct → 4-day revert window → Finalize OR Revert.
- **Customer keeps OLD Okta URIs in their IdP during the revert window** — they should only remove them AFTER clicking Finalize.
- **New Tyler-issued redirect URI format:** `https://idgw.{env}.com/tg-federation/<federationKey>/signin` and `/signout-callback`. The federation key is unique per org+provider.
- **The video demonstration uses Google Workspace as the IdP example** — Tyler-side steps are identical for other IdPs (Entra ID, Okta, ADFS); only the IdP's admin console differs.
- **Activation has a 3-day (sometimes 4-day) revert window.** The Activate dialog says "3 days"; the post-activation page says "4 days left" — likely an off-by-one or window-extension at activation. Don't quote a precise number; check the actual page value.
- **After Finalize, the Migration menu item disappears** from Admin Center. If a customer reports the Migration option is gone and they want to migrate, they're likely already finalized — no further action needed.
- **PASC users route to `tidsupport.com` post-migration** — flag this proactively.
- **The two-part guide is published on Tyler Community.** Video files: `Part1-OverviewAndGatewayRetargeting.mp4` (Tyler-internal) and `Part2-WorkforceDirectMigration.mp4` (customer-facing).
- **This whole flow is the operational implementation of Tyler's 2026 strategic shift away from Workforce Managed** — WM is being de-emphasized; WD is the preferred default.
