# Community Access Profile Manager (CAPM) — Implementation and Access Guide

Source: Confluence — *Tyler Cloud Platform (TCP) | Community Access Profile Manager* (https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386599847/) — captured from the `CAProfileManagerIG.pdf` "Implementation and Access Guide" attachment.
Domain: Ops Center (CAPM is a customer-facing tool but Tyler operational staff use the demo instance, and Tyler PMs/implementers coach customer Org Admins through this setup.)
Audience: Tyler operational staff (deployment, implementation, support) coaching a **customer's Org Admin** through granting their helpdesk/CSR staff access to CAPM. Also useful directly for customer Org Admins.

This document explains what CAPM is, when it is licensed by default, how a customer's Org Admin grants their support staff access to it via an Admin Center group, and what to do when the default group doesn't exist (older orgs).

**Companion documents in this same Knowledge folder:**
- `Docusaurus-Terminology.md` — see *Community Access*, *Community Profile*, *Community User*, *Public user* for the canonical definitions of the constructs CAPM operates on.
- `Conf-OpsCenterTickets.md` — for **Tyler-staff** CAPM access requests (a separate flow: form 4133 with the right TCP Tool Selection — used so Tyler staff can troubleshoot community resident accounts using the **demo** CAPM instance).
- `Misc-Links.md` — the live link to this Confluence page and to related bookmarks.

---

## How to use this guide (quick decision guide)

| If the user wants to… | Go to section |
|---|---|
| Know what CAPM is and what it can do | **What CAPM is** |
| Know whether their org has CAPM | **When CAPM is licensed** |
| Grant their customer support staff CAPM access (group exists) | **Default Setup — assigning users** |
| Grant their staff CAPM access (group does NOT exist — older orgs) | **Implementation — manually creating the group** |
| Understand best-practice for the group setup | **Best-practice recommendations** |
| Find the right Tyler-staff CAPM URL (vs the customer URL) | **Tyler-staff CAPM access (separate flow)** |

---

## What CAPM is

The **Community Access Profile Manager (CAPM)** tool enables organizations to support their **residents, small business owners, and other constituents** who have a **Community Access** account. Community Access is the **shared identity provider** included with Tyler's public-facing solutions for **bill payment, form submission**, and other public-sector activities.

Community Access uses a **self-service model** with several help tools directly accessible by end users. Although Community Access is operated and managed by Tyler, **users of public services typically contact their community or service provider directly** when they need help — not Tyler. CAPM is the tool that lets the customer's helpdesk/support team **find user accounts and perform basic support functions**, such as:

- **Resetting accounts.**
- **Unlocking accounts.**

---

## When CAPM is licensed

If the organization has purchased a Tyler application that **includes a public-facing site or services**, the CAPM tool will be **included as a licensed application** — no separate licensing required.

For a user in the organization to **actually use** CAPM, they must be **granted explicit access** to it through a workspace group containing the CAPM application.

---

## Default Setup — assigning users (when the "Community Access Support" group exists)

The default setup for newer orgs includes a pre-provisioned **"Community Access Support"** workspace group containing the CAPM application.

### Steps

1. Navigate to your **Production workspace**.
2. Look for a group named **"Community Access Support"** under **Manage Workspaces > Groups**.
3. **If the group exists:**
   - Click the group to open its right-side details pane.
   - Click **"Assign a new user"** in the details pane.
   - In the **Add members to the group** dialog, filter by Name / Email and select the users you want to grant CAPM access to. Click **Save**.
4. **If the group does NOT exist** (older orgs provisioned before CAPM was available): see **Implementation** below to create it manually.

---

## Implementation — manually creating the group (older orgs)

Older organizations may not have the **"Community Access Support"** group because they were provisioned **before CAPM was available**. In that case, the group needs to be **manually created**.

### Best-practice recommendations

- **Create a dedicated group containing JUST the CAPM application** — do not bundle CAPM with other apps in an existing group. CAPM is designed for **helpdesk and support personnel**; the dedicated group makes it easier to ensure only the right people have access.
- **Set the group up on the production workspace only.** The tool is **universal in behavior across workspaces**, so creating it in additional workspaces adds noise without benefit. *(The wizard lets you pick multiple workspaces, but stick to production.)*

### Step-by-step wizard

The wizard has 4 steps: **Create a group → Apps → Users → Review**.

#### Step 1 — Create a group (name, description, workspaces)

1. Use the side menu (hamburger menu, very top left) to navigate to the **Production workspace**.
2. Under **Manage Workspaces**, click **Create new group**.
3. In the **Create a group** dialog:
   - **Group name:** `Community Access Profile Manager` (or your preferred name).
   - **Group description:** an apt description (e.g., reuse "Community Access Support").
   - **Workspace(s):** select **only the production workspace** (per the best-practice note above).
4. Click **Next**.

#### Step 2 — Apps tab (select the CAPM application)

1. Search for the **"Community Access Profile Manager"** application (Product name: Portico).
2. Select it (check the checkbox).
3. Click **Next**.

#### Step 3 — Users tab (optionally assign users now)

1. Optionally select the users you want to grant CAPM access to (filter by Name / Email).
2. **You can skip this step and add users later** — Step 3 is not required at creation time. If the users you need don't yet have Workforce profiles, you'll need to **create them first under Manage users**.
3. Click **Next**.

#### Step 4 — Review

1. Confirm:
   - Group name and description.
   - Target workspace(s).
   - **1 app** (Community Access Profile Manager / Portico) will be in the group.
   - The user count (0 if you skipped Step 3).
2. If anything is wrong, use **Back** to go back and edit.
3. Click **Save & Close** to create the group.

After the group is created, follow the **Default Setup** steps above to assign users — that flow is identical regardless of whether the group was pre-provisioned or manually created.

---

## Tyler-staff CAPM access (separate flow)

The procedure documented here grants **customer organization staff** access to **their own CAPM instance** (org-specific URL).

**Tyler staff** who need CAPM access to **troubleshoot community resident accounts** use a **different flow**:

- **Different URL:** Tyler staff use the **demo CAPM instance** at `https://demo.tylerportico.com/portal/community-profile-manager/` — the demo instance has **special functionality not available on customer CAPM instances**.
- **Different access path:** Tyler staff request CAPM access via the generic **Ops Center permission ticket** (form 4133) with **TCP Tool Selection = "CAPM (Community Access Profile Manager)"**. See `Conf-OpsCenterTickets.md` → *CAPM (Community Access Profile Manager) access request* for the exact ticket URL and Notes-field wording.
- **Not requestable for customer staff via Tyler tickets.** Tyler staff CAPM-access tickets **cannot** be used to grant access to customer staff on their CAPM — that has to be done by the customer's own Org Admin via the steps in this document.

---

## Notes for the chatbot

- **CAPM is a CUSTOMER-side tool.** It is the customer's own helpdesk staff who use CAPM to support their public users. Tyler staff *occasionally* use a demo CAPM instance to troubleshoot — but that is a separate URL and flow.
- **"Community Access Support" is the pre-provisioned group name.** When a user asks "where's the group?", check the production workspace first, then fall back to manual creation. The pre-provisioned group already includes the CAPM application.
- **For older orgs, the group does NOT exist** — they were provisioned before CAPM was a thing. The fix is manual group creation, not a CorpDev ticket.
- **Best practice: dedicated group, production workspace only.** Don't add CAPM to an existing mixed group; don't replicate the group across multiple workspaces. The tool is universal across workspaces, so production-only is sufficient.
- **CAPM access is for helpdesk/support personnel — not all customer end-users.** Surface this expectation when answering "who should I add to the group?"
- **For "I'm Tyler staff and I need CAPM access" questions** — DO NOT direct them to this Confluence page or PDF. Direct them to the **Tyler-staff CAPM access ticket** in `Conf-OpsCenterTickets.md`, and the demo URL: `https://demo.tylerportico.com/portal/community-profile-manager/`.
- **Customer CAPM URLs are org-specific** (they live under the customer's Tyler Cloud Platform portal). They are NOT the same as the demo URL. If a Tyler staff member tries the demo URL while a customer is asking about *their* CAPM, set the expectation clearly: the customer logs in via their own org-specific URL, not the demo.
- **CAPM is a licensed app** — if a customer doesn't see it at all, check first that they have a Tyler product with a public-facing site/services. No public-facing product → no CAPM by default.
- **Permission propagation has a small delay** — same as other Admin Center group changes. Newly added group members may take a few seconds to be able to actually open CAPM.
- For deeper community-identity context (Community Profile, Community User, Public user, the SSO behavior across customer orgs), reach for `Docusaurus-Terminology.md`.
