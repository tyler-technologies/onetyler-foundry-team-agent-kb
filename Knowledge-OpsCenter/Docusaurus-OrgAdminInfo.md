# Org Admin — Who They Are and How to Source Them When Creating an Organization

Source: Docusaurus — *OneTyler Blueprint, App Guides > Ops > Ops Center > Org Admin info for Importing Organizations* (`docs/app-guides/ops/ops-center/orgadmininfo/orgadmininfo.md`)
Domain: Ops Center
Audience: Tyler product, deployment, and implementation staff who are about to **request** or **+Import** a new Organization in Ops Center and need to identify the client IT contact who will serve as the first **Org Admin**.

This document explains what an Org Admin is, who makes an ideal Org Admin, why their info is required at org-creation time, and how to find the right contact when you only know functional (non-IT) people at the customer.

**Companion documents in this same Knowledge folder:**
- `Docusaurus-Terminology.md` — see **Organization Admin** (canonical definition).
- `Docusaurus-OpsCenter.md` — where the Org Admin is entered (Import wizard / Create Internal wizard / Org Details > Admins).
- `Docusaurus-TylerCRM.md` — how to confirm the CRM record is valid before you start hunting for the Org Admin.
- `Knowledge-Shared/Conf-OneTylerTickets.md` — the "Add an Org Admin / self-promote" flow does NOT go through the generic permission form — see that catalog for the actual route.

---

## How to use this guide (quick decision guide)

| If the user wants to… | Go to section |
|---|---|
| Define "Org Admin" / understand who qualifies | **Who is an Org Admin?** |
| Identify what kind of client contact to target | **Ideal Org Admin profile** |
| Understand why Ops Center asks for this info up front | **Why Ops Center requires Org Admin info at org-creation time** |
| Find the right IT contact when their only known contacts are non-technical | **What to do when you don't know the IT contact** |
| Add an Org Admin after the org is already created | **Adding an Org Admin after org creation** |

---

## Who is an Org Admin?

**Organization Administrators (Org Admins)** are client back-office users with access to their organization's **Admin Center** and assigned a role with **full access to all functionality** available within it. This gives them access to all Tyler solutions that participate in centralized administration.

**Tyler staff** can also be granted Org Admin permissions on a customer's org. When that happens, the Tyler staff member is functioning **in a client Org Admin capacity** — not as a separate "Tyler" role.

For canonical definition see `Docusaurus-Terminology.md` → *Organization Admin*.

---

## Ideal Org Admin profile

An **ideal Org Admin** — to whom Admin Center access is granted — is typically:

- An **experienced technical lead, manager, or director** in the client's IT operations.
- **Responsible for maintaining the org's software subscriptions and their maintenance.**
- The person who **onboards new employees/users into the org's Identity Provider (IdP)** and grants access to hardware, systems, and software (provisioning email accounts, assigning Office 365 licenses, etc.).
- Works with the dedicated group(s) that **manage federations of their IdP to third-party solutions**.

In short: you want a real IT operator, not a functional department head.

---

## Why Ops Center requires Org Admin info at org-creation time

Two reasons drive this:

1. **Cloud self-service onboarding.** Tyler's cloud direction is to **empower customers to manage their own software**. Admin Center is the **starting point** for the client's engagement with Tyler's cloud ecosystem. Onboarding them as soon as the org is provisioned is important. Setting up Admin Center **does not require any other software solution to be installed** — so we can hand off immediately.
2. **Federation setup (Workforce Direct default).** Tyler's default policy is for clients to **federate their IdP into Identity Workforce using Workforce Direct** (cost-reducing for both sides). Setting up that federation is a core part of onboarding the client into their new org. This requires that the **first Org Admin is technically competent enough to use the self-service federation tools** — which is exactly why we ask for a real IT contact.

---

## What to do when you don't know the IT contact

If your only client counterparts are **functional people** (department heads, etc.) who are not technical, **reach out to any/all existing client contacts** to source the right IT admin contact.

Suggested probing questions to ask the customer's functional contacts:

- *"Who provisions email IDs for new employees? Can you reach out and get me the name of a key person in that department who can manage access to Tyler solutions?"*
- *"Who ensures that you can use your organization credentials when you try to access Office 365? Can you locate the department and ask the right person who is able to federate? Also let them know to expect an email from the `tylerportico.com` domain to set up the federation."*

The **goal** is to identify the IT person who already owns the customer's IdP and federation work.

---

## Adding an Org Admin after org creation

You don't have to specify the Org Admin at the moment of import or create. Both wizards have a **"Skip Org Admin setup"** option, and you can add the Org Admin later via **Org Details > Admins > Add an Org Admin**.

When adding the Org Admin later:

- Use the **"Use as technical contact"** option to simultaneously designate them as the org's technical contact. This is **especially important** for orgs that were automatically created on or after **4/1/26** from sales-enabled CRM records — those orgs are created **without contact information or domains set**.
- For **Workforce Delegated** Sub orgs, adding an Org Admin to the Sub auto-adds the user to the Super if not already present.
- Permission propagation has a small delay — a freshly added Org Admin will show **"Pending"** status during which they can't yet access Admin Center.
- The "Add an Org Admin" / self-promote flow is **NOT handled by the generic permission ticket form (4133)** — see `Knowledge-Shared/Conf-OneTylerTickets.md` → *Org Admins* for the actual route (the manager's-guide procedure on Confluence).

---

## Notes for the chatbot

- **Org Admin ≠ Tyler Ops User.** Tyler Ops Users have access to **Ops Center** (the internal tool). Org Admins have access to a specific organization's **Admin Center** (customer-facing tool). A Tyler staff member can be both — different permission systems.
- **Magic-link emails for federation setup expire in 7 days.** The chatbot should always flag this when discussing org creation / Org Admin onboarding.
- When users ask **"who should the Org Admin be?"**, give them the *Ideal Org Admin profile* — they are usually about to make the mistake of using a functional department head.
- When users ask **"the customer doesn't know who to give us"**, give them the suggested probing questions verbatim — they work.
- For **internal-use orgs** (no real customer), the Org Admin is a Tyler staff member or a demo user. Same wizard concepts apply.
- For **Workforce Managed** orgs created via ticket: the Org Admin is the **Customer Technical Contact** field on the ticket. Same concept as the wizard, different surface.
- The "Use as technical contact" option exists specifically because **auto-created orgs (4/1/26+) have no contact info** — always remind users to set this on the first Org Admin they add.
