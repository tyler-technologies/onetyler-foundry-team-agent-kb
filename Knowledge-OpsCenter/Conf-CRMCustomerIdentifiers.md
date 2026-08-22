# CRM Customer Identifiers — Deep Reference

Source: Confluence — *Tyler Cloud Platform (TCP) | CRM Customer Identifiers* (https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386599914) — last updated Jan 13.
Domain: Ops Center
Audience: Tyler operational staff (deployment, implementation, support) and product engineering teams that consume the **CRM Customer Identifier** in their tooling. Anyone troubleshooting a missing or wrong Customer Identifier on a CRM record.

This document is the deep technical/operational reference for the **CRM Customer Identifier** — what it is, how it is generated, why it is preferred over CRM Id / Account Number / GUID, how it surfaces in every Tyler system (TCP, Tyler Deploy, Tyler Identity Workforce, SaaS hosting, Tyler Notify), and the full troubleshooting / regeneration / merge-handling tree.

**Companion documents in this same Knowledge folder:**
- `Docusaurus-TylerCRM.md` — the shorter Docusaurus version (4-point validity checklist + "where to find it"). Use that for the quick answer; use **this** file for the deep dive.
- `Docusaurus-Terminology.md` — see *CRM > Customer Identifier* (canonical glossary entry).
- `Docusaurus-OpsCenter.md` — for how the identifier becomes the Org Key in Ops Center.
- `Training-OpsCenterOperations.md` — the "CRM IDs — don't confuse them" table that disambiguates ID / GUID / Account Number / Customer Identifier.
- `Misc-Links.md` — the live link to this Confluence page and to related Confluence resources.

---

## How to use this guide (quick decision guide)

| If the user wants to… | Go to section |
|---|---|
| Understand what the Customer Identifier IS (technically) | **What is the CRM Customer Identifier?** |
| Understand how the value is generated | **Generation algorithm** |
| Disambiguate it from CRM Id / Account Number / GUID | **Customer Identifier vs other CRM IDs** |
| Know what to do when multiple identifiers exist on one record | **Multiple identifiers — Business Use = Default rules** |
| Know whether their product team can use this value | **Which teams can use this value** |
| Find the identifier in CRM | **Where to find it** |
| Know what to tell the customer about the identifier | **Customer messaging (what NOT to say)** |
| See how the identifier surfaces in TCP / Tyler Deploy / TID-W / SaaS / Tyler Notify | **Usage across Tyler systems** |
| Handle a net-new or internal record not in CRM | **Records not in CRM (acquisitions, internal-use)** |
| Troubleshoot a missing identifier | **Troubleshooting — full flow** |
| Regenerate the identifier (pre-deployment) | **Regenerate the value after correcting Company Name** |
| Handle a post-deployment legal-name-change or merger | **Post-deployment legal-name changes** |
| Respond to a customer who doesn't like the value | **Customer doesn't like the value** |
| File the right ticket for help / regeneration | **Tickets — exact subject lines and recipients** |
| Find the forum to ask questions | **Discussion forum** |

---

## What is the CRM Customer Identifier?

The CRM Customer Identifier is a **unique, URL-friendly, database-friendly, 25-character alphanumeric value** designed to be **generated and assigned automatically** to CRM customer records.

The intent is to have a **centralized customer identifier** that can be used by:

- **Multi-tenant application platforms** that segregate data via URL substrings (e.g. TCP).
- **SaaS / client-specific hosting environments** that identify the customer's virtual environment by a string in the URL.

It is different from other unique identifiers like CRM Id (purely numeric) — it is **memorable** and **URL-friendly**.

### Example

**"City of Redmond, WA, USA"** has:

| Attribute | Value |
|---|---|
| CRM Record Id | `5350` |
| CRM Customer Identifier | `cityofredmondwa` |

The Customer Identifier is far more usable in URLs and human contexts than the numeric Id.

---

## Generation algorithm

The value is generated automatically using **CRM Company Name, State, and Country** values:

- **For US entities:** Country is **ignored**; only Company Name and State are used.
- **General format:** `<company name><2 char state><2 char country>` — must fit in **25 characters or less**.
- **When the value exceeds 25 chars**, the generator applies (in order):
  1. **An extensive 600+ abbreviation substitution list** (e.g., `school district` → `sd`).
  2. **Numbers in Company Name are preserved** as much as possible (the generator is number-sensitive).
  3. Finally, falls back to **first letters of each word**.
- **Extremely rare:** if all available methods cannot produce a unique value, generation **fails**, alerts stakeholders by email, and the value is **manually generated**.

### Why the Company Name field matters

The Company Name field **must reflect the entity's legal name** as cleanly as possible. **Do not add extraneous strings** to Company Name purely for internal reference/information — they will corrupt the generated identifier (because they will be included).

### Legacy values that don't match the algorithm

Some CRM Customer Identifiers **were not constructed using the general format** because they pre-date the standardized naming convention (some were borrowed from existing installations like InSite). To avoid changing production-use values, these legacy values were used as-is, while the automated algorithm was applied to newer records.

- **Approximately ~2,000 such manually-generated values exist in CRM** (at time of writing).
- For these older customer deployments, the identifiers used across various stakeholders may **not match** what the algorithm would have produced today.

---

## Customer Identifier vs other CRM IDs

| ID type | What it is | Uniqueness | Used where |
|---|---|---|---|
| **CRM Account Number** | Softrax billing-system account number tied to a contractual billing entity | **NOT unique** — may point to multiple customer account records | Billing only |
| **CRM Id** | Numeric record id | Unique per record | Some deployment tools |
| **CRM GUID** | GUID equivalent | Unique per record (visible only in the URL) | Construct direct record links |
| **CRM Customer Identifier** | Alphanumeric, URL-friendly, 25-char value | Unique per active customer record | **Used as the Org Key in Ops Center and tenant identifier across Tyler** |

### Why Customer Identifier is *better* than CRM Id or GUID

1. **Identifies "active" customers.** Customer Identifiers are designed to be generated **only on active customer account records** (records that are in active status AND have ≥1 active customer product item). So the **presence of a Customer Identifier is a general indicator of an active customer** — something Id and GUID values do not signal.
   - *Note:* a small number of earlier records have identifiers they aren't eligible for under the current criteria (accidentally created); these have not been cleaned up.
2. **Portability across CRM duplicate merges.** CRM frequently ends up with duplicate customer records, and the CRM data-governance team continuously merges duplicates into a single active record.
   - When this happens, **GUID and Id may continue to point to a deprecated (merged-out) record**.
   - **The Customer Identifier is moved to the active record** with `Business Use = Other` on the old one and `Business Use = Default` on the new active one (or vice versa, with a manual switch — see below).
   - **Lookups using the Customer Identifier always point to the current active record**, not a deprecated duplicate. This portability is the killer reason Tyler uses Customer Identifier as the centralized key.

---

## Multiple identifiers — Business Use = Default rules

A single CRM record can have **multiple Customer Identifiers**, but **only ONE** of them is marked **`Business Use = Default`**.

- The **Default** value is the one that should typically be used everywhere.
- After a duplicate-record merge, an `Other` business-use identifier may exist on the surviving record. If Ops Center is using the `Other` value as the Org Key (because that's the older one that was already deployed against), the CRM team will typically **switch the values** — making the `Other` value the new Default and switching the existing Default to `Other`.

### When Ops Center value doesn't match Default

If you see a **mismatch between what Ops Center is using** for an account record and **what is marked as Default in CRM**, file a ticket (see **Tickets** section) and **request that the default CRM Customer Identifier be switched**.

---

## Which teams can use this value

**Any product team in Tyler** is welcome to consume the Customer Identifier as a unique URL-friendly identifier. CRM is Tyler's primary system of record about customers, so the value is accessible:

- **Manually:** by searching in CRM.
- **By API integration with CRM:** as Tyler Deploy has done.

**Important framing:** Although the value is sourced from CRM, **Ops Center remains the reference for Tyler products on the use of these identifiers**.

### When the Customer Identifier may NOT be suitable for your product

- If your **business model requires consulting with customers** before adopting an identifier value.
- If your solution's domain has **rigid client branding/marketing conformity requirements**.

Once a Customer Identifier value is in use by multiple systems, **changes are typically impossible**. So:

- **Improve data input quality** so the algorithm produces clean values the first time.
- **Manual intervention should be extremely rare** — every effort should keep it that way.

---

## Where to find it

Navigate in CRM:

```
CRM > Customer Record > Service Account (View) > Tyler System Administration > CUSTOMER IDENTIFIERS
```

### Conditions for an identifier to exist on a record

A record will have a Customer Identifier when **ALL** of the following are true:

- Record is **active**.
- **Support-only customer = No**.
- **Company Name**, **State**, and **Country** values are present.
- At least one **active Product Information record** exists under **Sales Account (View) > Product Information**.
- A Customer Identifier value does **not already exist** (otherwise nothing new is generated).

**Any account — direct or indirect customer — that could potentially have its own deployment of software today or in the future should have a Customer Identifier.**

### Auto-generation timing

When a CRM record is created or edited and matches the conditions, the Customer Identifier is **automatically generated, typically within seconds**. A subsequent refresh of the record after sufficient time will show the value.

### Forcing a save to trigger generation

If the record meets all conditions but no identifier appears, **edit the record (even just triggering the save button and reverting the change), save it, wait 1–5 minutes, and refresh**. The identifier should now be present.

---

## Customer messaging (what NOT to say)

> 🚨 **General recommendation: do NOT discuss the generated Customer Identifier value with customers at all.**

Reasons:

- **No dedicated support personnel maintains this value** — it is designed to be fully automated. Giving customers "choices" complicates maintenance.
- The discipline of using the algorithm-generated value is what keeps the entire end-to-end deployment workflow low-maintenance.

Simply **use the value as-is** for provisioning customer resources and **provide the customer with the final URLs / environment details as part of customer handoff**.

### Why it doesn't usually matter to the customer

For most Tyler solutions, the **customer's own website is the primary engagement portal** — links to Tyler solutions are simply provided on the customer website to navigate from. So the customer's constituents don't need to remember the Tyler URL; they bookmark the city/county website instead.

**Example:** https://www.wilmette.com/ — the "Service Request" menu option on their site redirects to the 311 solution installed on TCP. The customer wants residents to remember `wilmette.com`, not the underlying Tyler URL.

---

## Usage across Tyler systems

### TCP (Tyler Cloud Platform)

TCP is multi-tenant and relies on a URL-friendly tenant identifier. URL construct:

```
https://<customer identifier>.tylerportico.com
```

**Example:** any TCP portal for the City of Redmond, WA → `https://cityofredmondwa.tylerportico.com`

For **non-production** portals, the environment suffix is appended with a hyphen:

```
https://<customer identifier>-<environment>.tylerportico.com
```

Examples for the same customer:

- `https://cityofredmondwa-test.tylerportico.com`
- `https://cityofredmondwa-train.tylerportico.com`
- `https://cityofredmondwa-staging.tylerportico.com`

### Tyler Deploy

**Tyler Deploy has a direct integration with CRM** and pulls the Customer Identifier directly. Uses:

- Creating TCP customer portals via the **"TCP Ecosystem"** tool (both production and non-production), 1:1 between a Tyler Deploy Client Environment and a TCP Portal, using the `<customer identifier>-<environment>` construct.
- Querying TCP services to check whether the client already has existing portals; displays them in Tyler Deploy to **avoid duplicating portals** for the same customer/environment combination, even if the portal was not originally created via Tyler Deploy.

> **Tyler Deploy is preferred** for creating customer TCP portals — it avoids human error. Loose integration between Tyler Deploy and TCP depends on **everyone respecting these rules**.

### Tyler Identity Workforce (TID-W)

Creates standalone Okta tenants using the construct:

```
tyler-<customer identifier>.okta.com
```

(See also: Confluence — *Tyler Cloud Platform (TCP) | New Enterprise Identity Model and TCP*, `/wiki/spaces/TTI/pages/386599279/`.)

### SaaS / Tyler Hosting

Uses the Customer Identifier to provision multiple types of web applications. E.g., **Tyler Hub URLs**:

```
<customer identifier>.tylerhub.com
```

Related: Confluence — *ERP CNAMEs* (`/wiki/spaces/ERPDEP/pages/417048965/`) and *Unique Client Identifiers* (`/wiki/spaces/TDBP/pages/287673462/`).

### Tyler Notify (Twilio)

The Tyler Notify team **tags client Twilio sub-accounts** using Customer Identifiers so activity can be **tracked and billed** to the respective clients.

---

## Records not in CRM (acquisitions, internal-use)

Customer Identifiers only exist for records **available in CRM**. TCP and TID-W **require CRM customer records AND CRM Customer Identifiers** — even for internal use cases.

### Recently-acquired companies / acquisitions

The CRM team migrates customer records from new acquisitions in a timely manner, **but there can be a delay** between when a recently-acquired solution needs to be deployed and when the customer records are migrated.

**In such cases:** the product team should reach out to the CRM team as soon as possible to **coordinate migration plans with deployment needs** — including possibly **prioritizing migration of a subset of records** earlier or manually creating a few in CRM.

### Internal Tyler use cases

When an internal Okta tenant is provisioned without a corresponding CRM customer record, an **internal-use-only customer record is created in CRM first** before provisioning the Okta tenant.

**All internal-use portals carry a CRM Account Number value in the format `99999999XXXX`** so they can be easily filtered out from real customer queries. (See: Confluence — *Tyler Cloud Platform (TCP) | Listing of internal use Ops Center organizations*, `/wiki/spaces/TTI/pages/386599668/`.)

---

## Troubleshooting — full flow

The Customer Identifier is meant to be automatic. Manual intervention is rare. Walk this tree when something is wrong:

### Step 1: Confirm the CRM record has the necessary information

- Record is **active**.
- **Support-only customer = No**.
- **Company Name**, **State**, **Country** values are present.
- At least one **active Product Information** record exists under **Sales Account (View) > Product Information**.
- **Additional requirement for Tyler Deploy:** record must have an **Account Number** either inherited through parent (if blank) OR a number directly on the record.

A visual version of these requirements lives at https://docs.tylerdev.io/application-guides/ops-center/tylercrm/#ensure-the-client-record-is-in-a-valid-state.

If all conditions are met, **edit and save** the record (even just triggering the save button and reverting the change) to force a regeneration trigger. **Wait 1–5 minutes, refresh, and check.**

### Step 2: Incomplete CRM record? Contact your product sales team

Product sales must create well-formed CRM records if they expect any deployments. **If any required information is missing, product sales must update the record. The CRM team and helpdesk no longer handle these changes.**

### Step 3: Well-formed record but still no identifier? File a ticket

See **Tickets** section below for the exact subject line and recipients.

---

## Regenerate the value after correcting Company Name (pre-deployment corrections)

Once an identifier value is generated, **changing the Company Name value will NOT automatically regenerate the identifier** — it might already be in use by other systems.

**Use this flow only BEFORE any deployments** against the identifier:

- If you just created the record and put in a wrong Company Name, **OR**
- If the customer has informed you of a legal name change **prior to any deployments**,

then file a ticket (see **Tickets** below) requesting deletion and regeneration of the value.

> **Important rule:** The CRM team will **NEVER manually enter a preferred value** — only the algorithm-generated value is available. **Company Name must contain ONLY the legal entity name**, with no extraneous strings like associated-parent or use-case.

### Determining if a Customer Identifier has been used in a deployment (so you can safely regenerate)

This is **non-trivial** because you may not know (a) which teams are using the identifier, and (b) whether they've actually deployed against it. The Enterprise group is the primary consumer at present. Use this guide:

| Team (solutions) | How to check |
|---|---|
| **CorpDev** (Tyler Cloud Platform, Tyler Identity Workforce) | If you have Ops Center access, log in and search the CRM Customer Identifier value against the organizations list. Alternatively, file a **General information request** ticket (see `Conf-OpsCenterTickets.md`). |
| **SaaS** (Enterprise group of solutions) | Check **Tyler Deploy** for the client and look at deployments / history. **No Tyler Deploy tenant for the customer + no deployment history → likely safe to assume the identifier has not been used.** |

---

## Post-deployment legal-name changes

**Do not offer to change the identifier or otherwise bring it up for discussion with the customer.**

If the customer **explicitly expresses a desire to change the value**, the internal discussion must cover:

1. What solutions have already been deployed using the existing value.
2. Whether redeployment & reconfiguration of any affected solution is even possible.
3. The costs of doing so.
4. Whether the client is willing to absorb those costs.

You will be responsible for **coordinating all impacted teams** through this activity. **Do not consider this trivial** (or even possible in many cases without major customer impact).

> **Tyler's recommendation:** change the **CRM Company Name** to reflect the new legal name, but **continue using the older identifier value**.

## Mergers between entities (post-handoff)

Same handling as a legal-name change: discuss internally, evaluate cost, prefer keeping the old identifier.

## Customer doesn't like the value

As noted, the Customer Identifier is **NOT** expected to be used in situations of marketing or branding significance. Given that, **Tyler will not entertain requests to regenerate values for reasons of dislike**.

**Exception:** if there appears to be an **actual error** (e.g., the last two characters do not show the correct state/country) **AND** you know there have been no deployments yet, follow **Regenerate the value after correcting Company Name (pre-deployment corrections)** above.

---

## Tickets — exact subject lines and recipients

Both the **request-for-assistance** and **request-for-regeneration** tickets use the same recipients.

### Ticket: Default-identifier mismatch / general assistance

| Field | Value |
|---|---|
| **Subject** | `CRM Customer Identifier: Request for assistance` |
| **To** | `help.desk@tylertech.com` |
| **CC** | `CRM-DataGovernance@tylertech.com` |
| **Body** | Provide the **CRM EC\|CRMINFO** reference link: `/wiki/spaces/TTI/pages/386600438` |

Use for: default-identifier mismatches; well-formed record but no identifier generated; other general identifier issues.

### Ticket: Regenerate identifier after Company Name correction

| Field | Value |
|---|---|
| **Subject** | `CRM Customer Identifier: Request for regeneration` |
| **To** | `help.desk@tylertech.com` |
| **CC** | `CRM-DataGovernance@tylertech.com` |
| **Body** | Provide the **CRM EC\|CRMINFO** reference link: `/wiki/spaces/TTI/pages/386600438`. Detail the situation and confirm there have been no prior deployments using the existing identifier value. |

Use ONLY when no deployments have occurred yet.

---

## Discussion forum

For **deployment personnel**, there is a Microsoft Teams channel for discussion and questions:

```
MS Teams > Tech Services Cross Division Collaboration (Team) > CRM Customer Identifiers (Channel)
```

For others **not part of that Team**, email **Vijay Venkataraman** directly for assistance.

---

## Other useful resources

- Confluence — *Child accounts in Tyler Deploy* (`/wiki/spaces/TD/pages/387156024/`).
- Confluence — *Tyler CRM - Automated Default Customer Identifier* (`/wiki/spaces/TTI/pages/386598211/`).

---

## Notes for the chatbot

- **The Customer Identifier IS the Org Key in Ops Center.** When a user says "Org Key", "tenant id", "Customer Identifier", or "CRM Customer Identifier", these are referring to the same value (when `Business Use = Default`).
- **`Business Use = Default` is non-negotiable.** Multiple Customer Identifiers can exist on a record, but **only the one with `Business Use = Default`** is the one to use. If you see a mismatch with Ops Center, file the assistance ticket.
- **Auto-generation requires the 5 conditions to ALL hold** — most "missing identifier" cases are because the record fails one of: active status, Support-only=No, Company Name+State+Country present, ≥1 active Product Information, no identifier already.
- **Editing and saving the record (even a trivial change reverted) can trigger generation** — this is a useful first remedy after confirming the 5 conditions.
- **Do not say the value to customers.** This is a recurring guidance — Tyler keeps the value internally maintained for automation discipline; customer "preferences" cause maintenance churn.
- **The value is portable across CRM duplicate merges** — explain this if a user asks "what if CRM creates a duplicate and the customer changes name." The Customer Identifier survives the merge; CRM Id and GUID do not.
- **For Tyler Deploy specifically, also check Account Number.** It can be inherited from parent or directly on the record — but must be present.
- **~2,000 legacy values in CRM do NOT match the algorithm.** When a user reports an "odd-looking" Customer Identifier on an old record, this is the likely explanation — and changing it post-deployment is **not** the move (see *Post-deployment legal-name changes*).
- **TCP URL construct is `<id>.tylerportico.com` for prod and `<id>-<env>.tylerportico.com` for non-prod.** TID-W is `tyler-<id>.okta.com`. SaaS hub is `<id>.tylerhub.com`. Tyler Notify uses it as a Twilio sub-account tag. Memorize the patterns.
- **Internal-use CRM Account Numbers follow `99999999XXXX`** — useful for filtering when answering "is this real customer data or Tyler-internal?"
- **Regeneration tickets are pre-deployment only.** If the user reports a request for regeneration after a deployment has occurred, walk them through the multi-team-coordination consideration in *Post-deployment legal-name changes*.
- **Tickets go to help.desk@tylertech.com with CRM-DataGovernance@tylertech.com on CC** — always include the `/wiki/spaces/TTI/pages/386600438` reference link in the body.
- **Company Name must be ONLY the legal entity name.** No "[demo]" suffixes, no parent-org annotations, no business-unit labels. Those corrupt the generated identifier.
- **Documentation cross-references:** the Docusaurus visual checklist at https://docs.tylerdev.io/application-guides/ops-center/tylercrm/#ensure-the-client-record-is-in-a-valid-state is the customer-facing-friendly version of the same conditions.
