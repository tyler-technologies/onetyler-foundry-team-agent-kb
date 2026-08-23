# Tyler CRM — Preparing a Valid Account Record for Ops Center

Source: Docusaurus — *OneTyler Blueprint, App Guides > Ops > Ops Center > Tyler CRM* (`docs/app-guides/ops/ops-center/tylercrm/tylercrm.md`)
Domain: Ops Center
Audience: Tyler product, deployment, and implementation staff who need to source customer information from Tyler CRM (Microsoft Dynamics) to request or import an Organization into Ops Center.

This document covers what Ops Center needs from Tyler CRM, how to confirm/obtain access to CRM, how to find a customer record, how to validate that the record is in a state Ops Center will accept, and how to read out the **CRM Customer Identifier** that becomes the Organization Key in Ops Center.

**Companion documents in this same Knowledge folder:**
- `Docusaurus-Terminology.md` — see the *CRM* cluster for canonical CRM term definitions (Active customer, Customer Identifier, Customer Relationship Type, Support-only customer, Hierarchy, Case, Product Suite/Module, etc.). The chatbot should always reach for those definitions when answering CRM-related questions.
- `Docusaurus-OpsCenter.md` — how the validated CRM record is then used in the **+Import (an organization)** wizard and the **New Org Request** ticket.
- `Knowledge-Shared/Conf-OneTylerTickets.md` — exact ticket URLs and Notes-field wording for new-org requests.

---

## How to use this guide (quick decision guide)

| If the user wants to… | Go to section |
|---|---|
| Know why CRM matters for Ops Center | **Why CRM matters** |
| Check if they already have access to Tyler CRM | **Check CRM access** |
| Request access to Tyler CRM | **Request CRM access** |
| Open the CRM Accounts page directly | **Direct CRM Accounts link** |
| Find a specific customer record | **Search for a client** |
| Validate a customer record is in a state Ops Center will accept | **Validate the account record (4-point checklist)** |
| Fix a CRM record that's missing/incorrect data | **Fixing a record** |
| Find the Organization Key (Customer Identifier) | **Read the Customer Identifier** |
| Troubleshoot a missing Customer Identifier | **Troubleshoot missing Customer Identifier** |

---

## Why CRM matters

To **request** or **+Import** an Organization into Ops Center, the source of truth is Tyler CRM. Ops Center requires that the CRM customer account record is **valid** — sales has approved it and it is tracked in sales queries as a valid customer. CRM is also the source of the **Customer Identifier** that becomes the Organization Key in Ops Center.

**As of 4/1/26**, Ops Center additionally **automatically creates customer organizations** from sales-enabled CRM records (no manual Import required). Manually fixing CRM data is still the prerequisite path for orgs that need to exist in Ops Center.

---

## Check CRM access

Open the **Sales Power App** view of Tyler CRM:

- https://tylertech.crm.dynamics.com/main.aspx?appid=bcbec218-67b3-e811-a965-000d3a1c53e4&forceUCI=1&pagetype=entitylist&etn=account&viewid=00000000-0000-0000-00aa-000010001001&viewType=1039

If you aren't already logged in, you'll be redirected to enter your Tyler Tech credentials. If you have access, the Sales Power App view will load.

## Request CRM access

Email `help.desk@tylertech.com`. **CC your manager** on the email — they must approve. Before the ticket is closed, confirm you actually have access.

**Suggested request text** (copy/paste; replace placeholders):

> I need a **Power Apps Premium** license that will allow me to get access to the Sales (both Sales and Service views) and Customer Service Power Apps, and allow me to collect the necessary Tyler CRM information needed to create organizations and license products in Ops Center. This is the primary URL that I will be accessing:
>
> https://tylertech.crm.dynamics.com/main.aspx
>
> Approving Manager: `{Manager's full name and email}`

## Direct CRM Accounts link (after access is granted)

- https://tylertech.crm.dynamics.com/main.aspx?forceUCI=1&pagetype=entitylist&etn=account&viewid=00000000-0000-0000-00aa-000010001001&viewType=1039

## Search for a client

Use the **quick search box above the listing** (not the global search at the top of the page) and enter the **customer name only**. Carefully note the **state** of the customer — multiple public clients may share a name across states. Select the matching record to drill into details.

---

## Validate the account record (4-point checklist)

Ops Center requires that ALL of the following are true on the account record:

### 1. Sales view: Status = Approved, Relationship Type = Direct or Indirect
- Switch to the **Sales view** on the customer record.
- Ensure the **Status** is **Approved**.
- Ensure **Relationship Type** is **Direct customer** or **Indirect customer**.
  - **Direct** = the customer signed the contract and maintains the billing relationship.
  - **Indirect** = customer is entitled to software due to a contract signed by a Direct customer.

### 2. Service view: Identity fields and Support-only check
- Switch to the **Service view**.
- Verify **Company Name**, **State**, and **Country** all match the customer.
- Verify **website** is present and a valid link.
- Verify **Support-only Customer = No**.

### 3. Products tab: Active customer product item exists
- Switch to the **Products** tab (within Service view).
- In the **Active Customer Product Items** section, ensure your product's **Suite/Module** is reflected.

### 4. Customer Identifier exists (Business Use = Default)
- See **Read the Customer Identifier** below — required.

**If any of the four conditions is not met**, the record is not yet usable for Ops Center. See *Fixing a record*.

---

## Fixing a record

Reach out to your **product sales team members** to fix the record — or to create one if missing — with all values set correctly. **Common gap:** sales team members frequently miss setting up Indirect-customer records, so for sub-entities (departments, business units) check that the Indirect record exists and is linked correctly via the customer hierarchy.

---

## Read the Customer Identifier (the value that becomes the Organization Key)

- Switch to the **Tyler System Administration** tab on the account record.
- Navigate to the **CUSTOMER IDENTIFIERS** section.
- Look for the row with **Business Use = Default**.
- The value in the **Identifier (Needed for Ops Center)** column is your Organization Key.

There may be other Customer Identifier records on the account, but **only one** unique value will be against **Business Use = Default** — that is the one Ops Center uses.

## Troubleshoot missing Customer Identifier

If the **Identifier (Business Use=Default)** value is missing **and** the account record otherwise meets the 4-point validity checklist above, refer to the Confluence troubleshooting page:

- https://confl.tylertech.com/display/TTI/Tyler+Cloud+Platform+%28TCP%29+%7C+CRM+Customer+Identifiers#TylerCloudPlatform(TCP)|CRMCustomerIdentifiers-Troubleshooting&Support

(Internal Confluence link.)

---

## Notes for the chatbot

- The **Customer Identifier** is the term users will use interchangeably with **"Organization Key"** in Ops Center. They are the **same value** — generated in CRM, imported into Ops Center.
- A common user misconception: there are multiple Customer Identifier rows on an account. Only the one with **Business Use = Default** is the Organization Key. Always specify this filter in any answer.
- "Sales view" and "Service view" are **different views of the same Account record** in CRM. Users may not know they need to switch views to find the fields they need. The 4-point checklist crosses both views — make sure both are checked.
- **All four checklist items are required.** Don't tell a user their record is valid because three of four pass — Ops Center will block import.
- If a user reports "Ops Center says my org doesn't exist" or "Import failed validation," the most common root cause is one of:
  - Status not Approved (Sales view).
  - Relationship Type is not Direct or Indirect.
  - Support-only Customer = Yes.
  - No active customer product item for their product.
  - Customer Identifier (Business Use = Default) hasn't been generated yet.
  Walk through the checklist and identify which.
- **CRM ≠ Ops Center.** CRM is where sales-enabled records live; Ops Center pulls from it. Don't confuse "create org in Ops Center" with "create record in CRM" — when CRM is wrong, sales (not OneTyler) fixes it.
- **Internal Tyler-use orgs do NOT have CRM records.** For those, use **+Create Internal** in Ops Center (see `Docusaurus-OpsCenter.md`), not CRM/Import — and follow naming conventions (Confluence: *Internal Orgs creation in Ops Center → Internal-Org-Naming-Construct*).
- **Support-only Customer = Yes** is intentionally used to keep an account from showing up in sales queries — but that exact attribute also blocks Ops Center from accepting the record for customer-org creation. If a record is marked Yes and should be a real customer, sales must change it to No.
