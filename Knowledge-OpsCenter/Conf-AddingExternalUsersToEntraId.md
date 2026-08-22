# Adding External Users to Entra ID Without Consuming an Office 365 License (Workforce Direct Orgs ONLY)

Source: Confluence — *Tyler Cloud Platform (TCP) | Adding external users to Entra Id without consuming an Office 365 license (Workforce Direct Orgs ONLY)* (https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386635379) — last updated Aug 01, 2025.
Domain: Ops Center
Audience: Tyler operational staff (deployment, implementation, support) working with a **Workforce Direct** customer whose Entra ID (Azure AD) IdP needs to host **non-regular-employee** users (temp workers, contractors, etc.) who do not have a dedicated company email inbox. **Not a document to share with the customer directly** — it's a primer so Tyler staff can have an informed conversation with the customer's IT admin who actually performs the steps.

This document describes a 3-step workaround on the **customer's** Entra ID instance to register such users with a customer-domain "email-shaped" username while pointing the actual email property to their real (external) email — **without consuming an Office 365 license**.

**Companion documents in this same Knowledge folder:**
- `Docusaurus-Terminology.md` — see *Identity Workforce* (Workforce Direct vs Managed vs Delegated). This whole workaround is specific to **Workforce Direct**.
- `Conf-OpsCenterTickets.md` — for unrelated Identity Workforce permission and authentication tickets.
- `Misc-Links.md` — for the live link to this Confluence page and related bookmarks.

---

## How to use this guide (quick decision guide)

| If the user wants to… | Go to section |
|---|---|
| Know when this workaround applies (and when it does NOT) | **When to use this workaround** |
| Understand why the workaround exists (the O365-license cost issue) | **Why this exists** |
| See the 3-step procedure | **The 3-step procedure** |
| Know how to position this with the customer | **Working with the customer** |
| Understand a current quirk (username = email today) and the planned change | **Current quirk: username and email are the same field** |

---

## When to use this workaround

**Use this when ALL of the following are true:**

- The organization is on **Workforce Direct** Identity Tier (i.e., the customer brings their own Entra ID / Azure AD IdP and federates).
- The customer needs to grant a Tyler product to a user who is **NOT a regular employee** — examples: temp workers, contractors, short-term staff.
- The user **does not have a dedicated email inbox** in the customer's organization (i.e., they aren't on the company's email/Office 365 system).
- The customer wants to **avoid consuming an Office 365 license** for this user.

**DO NOT use this workaround for Workforce Managed orgs.** WM orgs **allow any email id to be used as a login id** without these contortions — there's nothing to work around.

> 🚨 **Workforce Managed Orgs Only Warning (from source):**
> This guidance is ONLY for Workforce Direct orgs. **Do NOT setup users with usernames that do not match emails in Workforce Managed orgs.** WM orgs allow any email id to be used as login id without needing these workarounds.

---

## Why this exists

In **Workforce Direct**, all users must reside in the customer's IdP (Entra ID / Azure AD). When the customer adds a user to Entra ID through the normal flow, that user typically consumes an **Office 365 license** — even if they never actually use Office 365 services. For non-regular-employee users (temps, contractors, etc.) who don't actually need an email inbox or any Office 365 functionality, this is wasted spend.

The workaround creates a user record in Entra ID with a **customer-domain "email-shaped" username** (matching the org's domain, which Identity Workforce expects as the login id) but explicitly **does not assign a license**. The user's **actual email** is then set on the email-id property to point to their **real external email** so they can receive any necessary communications.

This still gives the customer-domain username that Identity Workforce + Tyler products need for login, without the O365 license cost.

---

## The 3-step procedure

These steps are executed by the **customer's IT admin** (the person who manages their Entra ID instance), not by Tyler staff.

### Step 1 — Create a user (email-shaped username) in Entra ID, do NOT assign a license

In the customer's Entra ID instance, create a new user record. The **username** must be in email format using the **customer's domain** (e.g., `jdoe@customer.org`) — this is what Identity Workforce will treat as the login id.

**Critically: do not assign an Office 365 license** to this user. That's the whole point — skipping the license assignment keeps the cost away.

### Step 2 — Update the email-id property on the new user to point to the actual (external) email

On the new user record, find the **email-id** property and set it to the **user's real (external) email** address — i.e., wherever they actually receive email (a personal address, a temp agency mailbox, a contractor's company address, etc.).

This ensures that any notification or communication intended for the user (password resets, magic links, etc.) goes to a place they can actually read.

### Step 3 — Add the new user using Admin Center and provide necessary permissions

In the customer's **Admin Center**, add the user (who now exists in Entra ID by the customer-domain username) and grant whatever product/group permissions they need to do their work.

This is the normal Admin Center user-management flow — at this point the user behaves like any other Workforce Direct user.

---

## Working with the customer

> ⚠️ **Do NOT share this Confluence page directly with the customer.**
> The page is **internal Tyler staff guidance**, written so Tyler staff can have an informed conversation with the customer's IT admin. **The customer's IT person in charge of their Entra ID instance is expected to have the skills to manage their own instance** — Tyler's role is to flag the use case and the high-level approach, not to walk through Entra ID screens for them.

When having this conversation with a customer who has a temp/contractor scenario:

1. Acknowledge they want to grant access without paying for an Office 365 license.
2. Mention that **for Workforce Direct orgs**, the customer's Entra ID admin can create the user with an email-shaped username on the customer's domain, set the email property to point to the user's real external email, and skip the license assignment.
3. Make sure they're willing to manage this themselves in Entra ID — Tyler does not perform this work on the customer's IdP.
4. After Step 1 + Step 2 are done by their IT admin, you can complete Step 3 in Admin Center (or guide their Org Admin to do it).

---

## Current quirk: username and email are the same field

> 📌 **From the source page note:**
> *"At the time of this document, the username (which corresponds to the new user record in email format with customer's domain) is also treated as the email id for the user. In the future, this will be separated into different attributes that products can use as user name and email id respectively."*

**Interpretation:** Today, products that consume Identity Workforce read the same field for both login-id and "email" — meaning if you set the username to `jdoe@customer.org`, that string is *also* what some products will treat as the user's "email" for product-internal purposes. That's why **Step 2** matters — it sets the user's "real" email on the dedicated email-id attribute, so that downstream products that **do** read that attribute see the right value. Future Identity Workforce work will fully separate "username" and "email id" into distinct attributes so products can disambiguate cleanly.

For the chatbot: when a user asks why bother with Step 2 if the login already looks like an email, the answer is **forward compatibility** — and to keep the user's real email reachable for systems that already read the email-id attribute correctly.

---

## Notes for the chatbot

- **Workforce Direct only.** If a user is asking this question and the org is Workforce Managed, the answer is "you don't need this workaround — WM orgs allow any email id as a login id."
- **Customer's IT admin does the Entra ID work.** Tyler staff do not log into the customer's Entra ID and create users — Tyler educates the customer on the approach.
- **No O365 license assigned** is the critical instruction in Step 1 — call this out explicitly when discussing.
- **Don't share the Confluence page URL directly with customers** — share the *concept* with their IT admin instead. The page is internal-only context for Tyler staff.
- **This is specifically for non-employee users without a company email inbox.** Regular employees who have a company email inbox should be added the normal way (and Office 365 license applies).
- The future Identity Workforce changes will separate the username and email attributes — this workaround's necessity may evolve. When the user asks "is this still the right approach in 2026+", note that the source page hasn't been updated for that and recommend they confirm with Identity team / Vijay Venkataraman.
- For broader Identity tier / Workforce Direct / Workforce Managed context, always reach for `Docusaurus-Terminology.md` → *Identity Workforce*.
