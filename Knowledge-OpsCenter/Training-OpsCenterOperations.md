# Ops Center Operations — Training Distillation

Source: Distilled from official Ops Center operational training videos — transcripts under `Revoice/completed/Part1-Session1-Overview`, `Part2-Session1-TermsAndBasicConcepts`, `Part3-Session1-ProcessOverview`, and `Part6-Session2-SupportResourcesWrapUp` (Whisper-generated + manually edited).

**All 6 parts of the official training are operational content.** This file distills the four conceptual parts (1, 2, 3, 6). The remaining two parts — **Part 4 (Typical Process Demo)** and **Part 5 (Cloud Tools Demo)** — are live screen-recording walkthroughs of the same operational content in action; they are not distilled because live demos do not transcribe usefully. To learn that material, **watch the videos directly on the official training hub:** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386599613/Tyler+Cloud+Platform+TCP+Deployment
Domain: Ops Center
Audience: Tyler operational staff — project managers, deployment, implementation, support, and product-engineering personnel who interact with One Tyler concepts (Organizations, Workspaces, Products, Identity Workforce/Community) as part of their daily product-deployment work.

This document is the **narrative / "how to think about it" companion** to the more reference-style files in this Knowledge folder. It is a distillation of training content — strategic context, vocabulary, the typical operational process, and the support/resources model — written so the chatbot can answer "why do we do this?" and "how does this fit together?" questions, in addition to "what is the exact field on the ticket?" questions which are answered in the other files.

**Companion documents in this same Knowledge folder:**
- `Docusaurus-Terminology.md` — canonical glossary; trust it as the authoritative definitions.
- `Docusaurus-OpsCenter.md` — product/process reference for Ops Center (env URLs, wizards, fields).
- `Docusaurus-TylerCRM.md` — exact CRM validity rules and how to find the Customer Identifier.
- `Docusaurus-OrgAdminInfo.md` — sourcing the customer IT contact for federation.
- `Docusaurus-ProductRegistration.md` — what a registered product is and how to prepare a registration.
- `Conf-OpsCenterTickets.md` — every ticket URL and Notes-field template.

The training omits product-specific deployment/configuration steps; **that content lives with each product team**. This file focuses only on the parts that interact with One Tyler.

---

## How to use this guide (quick decision guide)

| If the user wants… | Go to section |
|---|---|
| Strategic background (why Tyler is doing this) | **Overview — strategic context** |
| Suite-like experience explained (cross-sell story) | **Overview — the cross-sell story** |
| What "Tyler SaaS control plane" means | **Overview — Tyler SaaS control plane** |
| Vocabulary: app types, user types | **Basic Concepts — app types and user types** |
| Identity Workforce / Community explained (the WHY) | **Basic Concepts — identity** |
| TCP vs non-TCP product registration | **Basic Concepts — product registration variants** |
| Product / Organization / Workspace as a unit | **Basic Concepts — Product, Org, Workspace** |
| TCPCI vs TCPQA vs TylerPortico (when to use which) | **Basic Concepts — the three environments** |
| End-to-end operational process | **Typical Process** |
| Sales / CRM responsibilities | **Typical Process — sales responsibility (CRM)** |
| Ops responsibilities (Step 1 / 2A / 2B / 2C / 3) | **Typical Process — ops responsibilities** |
| When an existing org is "inactive" | **Typical Process — recognizing an inactive org** |
| Federation setup and customer handoff | **Typical Process — federation and handoff** |
| When to come to One Tyler vs product engineering | **Support — distributed support model** |
| Specific routing rules by issue type | **Support — issue routing rules** |
| Resources (Blueprint, Confluence, JSM, Teams) | **Resources — where everything lives** |
| Forums and ongoing communication | **Resources — forums to join** |

---

# OVERVIEW

## Strategic context

Tyler has **strategic 2030 Pillars**. Two are directly relevant to this work:

1. **Enable cross-sell** by delivering a **Tyler 365 Public Sector Suite** experience. Tyler offers 130+ solutions; customers should be able to source all their needs from Tyler. A suite-like experience makes that compelling vs buying best-of-breed components from different vendors.
2. **Reduce cost** by transitioning to **scalable cloud operations** — a framework that lets Tyler move to the cloud and achieve operational savings.

These pillars are operationalized in **OTCOM** (the **One Tyler Cloud Operating Model**) — a long execution document. The relevant section is **Section 14 — Cloud Living**, which pertains to One Tyler technology. Within Section 14, items **14.3** (identity integration) and **14.4** (product registration and licensing) are the scope of this operational training. (Other Section 14 topics — Aligned Releases, SLAs, Status Pages, Forge, Tyler Interactive Reporting, Foundry — are out of scope here but related.)

**Product registration is the first step** for any team doing Aligned Releases — register and license before participating. Most Tyler products (excluding new acquisitions) have already been registered. The next critical step for product teams is **license them on customer organizations and workspaces** and keep that data fresh, so Ops Center becomes the **deployment system of record** for downstream Cloud Living initiatives.

OTCOM goals are currently 2026-targeted (likely to slip). Regardless of timing, product teams should accomplish registration + licensing as soon as possible — it is the baseline for everything else.

## The cross-sell story — why a suite-like experience matters

Tyler's customer base is large but mostly acquired. Most customers run one flagship Tyler solution plus a few dependents. When customers have multiple Tyler solutions, the consistent complaint is **"there's no benefit to sourcing from Tyler — I add users in every product separately, set branding in every product separately, federate to every product separately."** When that is the experience, you might as well buy best-of-breed.

Analogy: a couple of years ago Tyler chose Teams over Slack — not because Slack was worse at chat, but because **Teams offered a more cohesive, integrated administrative package**. That's the operational-cost story for a suite.

After studying Office 365 / Google Workspace as models, the One Tyler ecosystem now provides suite-like tools, all powered by what is registered and licensed:

- **Workforce App Directory** — a collection of bookmarks to all licensed products. Users click and navigate; no hunting for URLs in old emails. Over time users bookmark favorites, but the directory ensures every new back-office user has a starting point.
- **Community Launcher** — same idea for **public users** (residents, small businesses, vendors). The focus is on **services** (make a payment, schedule an inspection), not on products. Same login can carry across cities/orgs.
- **Admin Center** — customer-facing centralized administrative experience: add users, manage user groups, set up identity. Also offers **one-click jumps directly into a product's admin/setup screens**, sidestepping the need to navigate inside the product to find its admin section.
- **Ops Center** — Tyler-staff-side counterpart. The **system of record for what is deployed**. Hosts bookmarks to operational tools per product (registered as part of registration). Also hosts **product contact info** — every product must provide a public Teams channel for inbound questions. (Individual contacts go stale; Teams channels are more durable as people change roles.)
- **Tyler Cloud Platform (TCP)** — Tyler's PaaS. Defined in Terraform (Platform as Code), with rapid-application-development templates. Disaster-recovery proof: every quarter a full cluster is spun up from the ground in under an hour. Multiple TCP copies exist within Tyler (One Tyler / formerly CorpDev, ERP, EPL, more recently Municipal and Schools); other divisions are expected to follow. **"TCP" refers to the infrastructure type, not a specific instance.**

## Tyler SaaS control plane

**"Tyler SaaS control plane"** is the umbrella engineering term for everything above. It encompasses **common constructs** and **shared services**.

### Common constructs (bind inter-product communication)

| Construct | What it represents |
|---|---|
| **Organization key** | The customer |
| **Workspace key** | The tenant / business-purpose installation |
| **Product ID** | A deployed product |

When two Tyler products need to talk — e.g., Enterprise ERP talking to Tyler Interactive Reporting — the caller identifies: **this product, this organization, this workspace**, asking for the corresponding installation at the other end. The other product stores the same keys against its installations and knows which instance is being addressed. **The workspace key is the universal tenant identifier across Tyler.** Within a single product, internal tenant identifiers can be whatever; but for cross-product communication these keys MUST be tagged on product installations.

### Shared services

TCP (infrastructure), Forge (UX), Branding (logos/colors), Identity (SSO), Aligned Releases (release management), status pages, SLAs. All aimed at delivering Tyler 365 suite-like experience. Your product may not have adopted all of these yet — adopt them on the Cloud Living timeline.

## Licensing vs availability

- **Licensing** — assigns a registered product to a customer organization. Indicates **entitlement**. Does NOT mean software has been deployed.
- **Availability** (a.k.a. **activation**) — indicates an actual installation has been made against a **workspace** for a given business purpose (production, test, training, staging, etc.).

**OTCOM 14.4** requires both. They are the **baseline deployment system of record** for Aligned Releases, SLAs, and status pages — those services only operate on customer orgs/workspaces where the product is indicated as deployed. They are also the substrate for the suite-like experiences for customers.

Suite-like experiences delivered through **Admin Center / Workforce App Directory / Community Launcher**; shared services through **Forge / cloud identity / branding**; cloud-ops infrastructure through **Ops Center / Support Access Center / TCP (PaaS)**.

---

# BASIC CONCEPTS

Consistent vocabulary matters — the next sections lean heavily on these definitions. See `Docusaurus-Terminology.md` for the canonical glossary.

## App types and user types

The SaaS control plane recognizes **four app types** and **four corresponding user types**. Don't mix them up — confusion here is rampant, especially around "admin".

| App type | Audience | User type |
|---|---|---|
| **Workforce app** | Customer back-office users (e.g., invoice management) | **Workforce users** |
| **Admin app** (a subtype of Workforce) | Customer IT / Solutions admins — setup, configuration, authorization | **Org Admins** (using Admin Center) — note: an Org Admin can also be a "Product Admin," a customer workforce user who configures the product and manages authorization in it |
| **Access app** (a.k.a. Community app) | Customers' customers — residents, small businesses, public users. Service-oriented (make a payment, schedule inspection); users don't care about "products" | **Public Users** |
| **Ops app** | **Tyler staff only** — deployment, implementation, metrics. Customers cannot see these | **Ops Users / Tyler Ops Users** (with `@tylertech.com` email) |

### Common terminology trap: "Admin"

Many product deployments use "admin" colloquially to mean what we call an **Ops app**. **For us, anything Tyler-staff-only is an Ops app, not an Admin app.** Admin apps are for customer IT/Solutions admins inside Admin Center. Whenever a product team uses "admin" ambiguously, force them to clarify: customer-side admin (= Admin app, surfaces in Admin Center) or Tyler-staff-only (= Ops app, surfaces in Ops Center)?

## Identity (the deep dive)

There are two main cloud identity solutions: **Identity Workforce** and **Identity Community**. Both are about **authentication** — confirming a person owns the account they're using. **Authentication is not authorization.** Authentication accounts hold only first name, last name, email, user id. Granting product access is a product-level concern.

### Identity Workforce (back-office users)

Identity Workforce is configured **per organization**. Once set up at the org level, **all Workforce apps of participating products experience SSO** — a back-office user can jump freely between authorized apps without re-logging.

Configured in **Ops Center** (initialization) and managed by customers in **Admin Center**.

**Three configurations:**

- **Workforce Direct** — *Preferred and default option.* The customer brings their own user store / IdP through federation. Users log in with their existing org credentials.
- **Workforce Managed** — Tyler provides the user store via a dedicated Okta tenant for the customer. **Being de-emphasized in 2026** and may effectively be removed from the terminology as Identity goes through a new iteration. Used today for customers who don't have a public IdP.
- **Workforce Delegated** — Special case where one org **depends 100% on another org** for its identity and user store. The "Sub" org consumes the "Super" org's identity setup. Examples: a school district (Super) and its schools (Subs); a city and its police department, if the police department is truly 100% dependent on the city's identity. Otherwise, prefer separate Workforce Direct orgs.

### Identity Community (public users)

Tyler-owned solution. Once a Public User logs in, they can cut across **different products AND different customers** with the same login. Example: a user with properties in two different cities — both running Tyler Access apps — can switch between them seamlessly with the same credentials and preferences. Each public user has a **Community Profile**. The **Community Access Profile Manager (CAPM)** is a tool for **customer CSRs** to support their public users.

### Identity terminology notes for the chatbot

There has been confusion around the name: **TID-E, TID-W, TID-G, Identity Workforce, Gateway, Enterprise** — these all refer to the **same evolving solution**. The current official brand is **Identity Workforce**. **Use "Identity Workforce" with customers.** **Do NOT say "Gateway"** to customers — it's not an official brand name (though it appears internally and on login error screens).

Internally we are on roughly the **third iteration** of Identity Workforce, moving to the **fourth in 2026**, which will change some operational processes. Training will be updated when that occurs.

### Ops apps and identity

Ops apps use **Tyler single sign-on**, not Identity Workforce or Identity Community. Tyler staff log in with their `@tylertech.com` credentials.

## Product registration variants — TCP vs non-TCP

Product registration ties everything together: app types, identity choices, navigation links, contact info. There are **two implicit variants** of registration:

- **TCP registration** — for products purpose-built on the Tyler PaaS (TCP) infrastructure. Comes with a fair degree of automation (One Tyler constructs handled by the platform + templates). For TCP products, **Ops Center is BOTH the primary deployment tool AND the system of record**. Even TCP products are often triggered by external deploy tools (Tyler Deploy, Cloud Provisioner) via Ops Center APIs.
- **Non-TCP registration** — for products not built on TCP. **Ops Center is ONLY the system of record** — adopting One Tyler constructs, integrating with identity, consuming branding, etc., must be done explicitly.

**The distinction is not an explicit label on the registration — it's an interpretation of how the registration is done.** Hybrid registrations exist for products transitioning between TCP and non-TCP.

## Product, Organization, Workspace — the three constructs

These three constructs are the heart of everything Ops Center does. Internalize them:

- **Product** — high-level deployment package a customer would reasonably understand; the licensing entity; appears in the Product Registry.
- **Organization** — a customer entity with a **1:1 relationship to a CRM record**. CRM stores the org; the org references the CRM record back. An organization can have many installations (tenants/workspaces).
- **Workspace** — represents a **business purpose** — production, or non-production cases like test, training, staging. Product installations are mapped to workspaces under an Organization.

### Licensing vs availability (revisited)

A product is **licensed on an Organization** (entitlement only; no installation yet). A licensed product is **made available on a Workspace** (true indicator of an actual installation). **You cannot make a product available on a workspace until it is licensed on the org.** What people loosely call "licensing" is actually two steps: license on org → activate on workspace.

### Connection to CRM

CRM has a customer account record that maps 1:1 with our Orgs. CRM also has product **suites and modules** purchased by customers — but those are **SKUs in the CRM sense**, and **do not map cleanly to our deployed-product definition**. There isn't much explicit linkage today between CRM SKUs and our Products. (SKUs change with sales market conditions, so a tight binding is brittle.) **From a SaaS control plane standpoint, what matters is: Product, Organization, Workspace + a CRM reference we try to maintain.**

## The three environments

One Tyler operates **three TCP clusters**, each hosting a distinct copy of the Ops Center system of record:

| Cluster | Purpose | Reliability | Customer-facing? |
|---|---|---|---|
| **tcpci.com** | Internal product **Development** | **Very unreliable** | No |
| **tcpqa.com** | Internal **QA** testing; sometimes used for **internal Tyler demos** | Much more stable than CI, but product teams run load tests here — so it can struggle | **No customer-facing** content |
| **tylerportico.com** | **Production** | High | **Yes — the only customer-facing environment** |

**Rules to internalize:**

- **The three clusters are completely independent.** The same org key can exist in CI, QA, and prod independently.
- **All customer-facing demos, training, and revenue-impacting use cases run on `tylerportico.com`.** "Million-dollar demos" do NOT run on `tcpqa.com`.
- If a customer has separate production + test infra, both map to **different workspaces in `tylerportico.com` under the same org**.
- For most ops staff, expect `tylerportico.com` to be the only environment they care about. CI and QA are for product dev teams.

---

# TYPICAL PROCESS

This is a process **overlay** on top of your product's existing deployment process — it does NOT displace product-specific steps for getting the product functional or for authorizing users. Those steps live with each product team.

Two responsibilities: **Sales** and **Operations**.

## Sales responsibility (CRM)

Your sales team must create a **CRM account record** for every customer Tyler deploys software to. That record must have specific attributes that mark it an **"active customer"** — see `Docusaurus-TylerCRM.md` for the canonical validity rules.

CRM is a **lifecycle management** tool: lead → prospect (via active RFP) → active customer (contracts signed) → former customer (exit). **We are only interested in the "active customer" stage.**

### The four active-customer criteria

A CRM customer account record is **sales-enabled / active** when ALL four hold:

1. **Status:** Active or Approved.
2. **Relationship Type:** Direct customer OR Indirect customer.
   - **Direct** = the lead customer signing the contract.
   - **Indirect** = a customer entitled to software because of someone else's contract.
   - **Common deficiency:** Sales create the Direct record (because the contract demands it) but miss the Indirect ones. Implementation/PMs often have to read the contract themselves to ensure each additional city/county/sub-entity has its own Indirect CRM record. **If new to this process, engage sales early and educate them.**
3. **Active Customer Product Item:** at least one (the SKU we discussed earlier) in Active status.
4. **Support-only Customer:** No. (That flag excludes the record from sales queries; if Yes, the record is filtered out.)

When all four hold, sales has effectively confirmed who can have software, and there's no mismatch between sales expectations and implementation.

### CRM IDs — don't confuse them

Tyler CRM (Microsoft Dynamics) exposes several IDs. Don't mix them up:

| # | What it is | Notes |
|---|---|---|
| **1. ID** | A 1–6 digit number per account record (e.g., 83,000) | Used by many deploying tools. |
| **2. GUID** | The GUID equivalent | Visible only in the URL. Needed to construct a direct record link. Captured in Ops Center to link back to CRM. **ID and GUID are different values.** |
| **3. Account Number** | The Softrax billing account number | **NOT unique** — Direct and Indirect customers share the same account number. Cannot identify a specific customer. |
| **4. CRM Customer Identifier** | **THE one that matters most.** Found under the **Tyler System Administration** tab. Alphanumeric, typically ≤25 chars, **Business Use = Default**. There may be other Business Use values, but **only the Default one is the org key**. | Generated automatically within ~10 seconds of a record becoming Active. Uses Company Name, State, and (for non-US/Canada) Country to construct the value. **Make sure those fields are correct BEFORE the record is activated.** |

**Critical property of the Customer Identifier:** **portability across CRM duplicates.** When CRM ends up with duplicates (e.g., a legal entity changes its name and a new sales contract is created without noticing the old record), the sales governance board merges the records. The ID and GUID may go stale, but the **Customer Identifier migrates to the active record**. **Only the Customer Identifier has this built-in portability — that's why we use it as the org key.** Any lookup using the org key always points to the live record, never to a canceled duplicate.

**Internal automation note for the chatbot:** Customer Identifier values are fully system-managed. They are **not** a branding choice and not configurable by the customer. Do not present them to customers as something they can pick or change. If no Customer Identifier is generated, ping sales to verify the four active-customer criteria are met.

## Ops responsibilities

The high-level operational flow:

1. Make sure the **Organization** exists in Ops Center.
2. Make sure the **Workspace(s)** exist.
3. Then **deploy, provision, and implement** your product.
4. In **parallel**, the PM (or whoever is engaged with the customer) **facilitates the customer-side setup** — identity federation, customer access to Admin Center, customer access to the product. **Goal: enable self-service.** Customers own their own setup as much as possible; we don't do it for them.
5. **Hand off** the product to the customer; recognize revenue.

### Visual model

| Step | Purpose |
|---|---|
| **Step 1** | Org analysis + creation (if missing) |
| **Step 2A** | Product deployment + configuration |
| **Step 2B** | Collect customer info (federation contact, Org Admin) |
| **Step 2C** | Apply that info in Ops Center (make Org Admin, send magic link) |
| **Step 3** | Customer handoff |

**Step 2A can run independently of 2B/2C** — deploying the product doesn't have to wait on federation/Admin Center work.

### Step 1 — Org analysis and creation

1. **Check if the Org exists.** Use Ops Center or your deployment tool (if integrated with Ops Center) to look up the org and workspace.
2. **Most active customer orgs should already exist** — an overnight job imports new active customers from CRM. But records that became active today may not yet be in Ops Center.
3. If the **Org is missing**: use the **Import** functionality in Ops Center to create it. (See `Docusaurus-OpsCenter.md` → Import wizard.) You need the **CRM Customer Identifier** to start. **Orgs can only be created in Ops Center** — deployment tools cannot create customer organizations.
   - **Default Identity Tier on Import is Workforce Direct.** Customer is expected to federate.
   - If the customer is too small to have a public IdP, sales should have flagged Workforce Managed on the CRM record (as a Product Module). For those, **file a Workforce-Direct-to-Workforce-Managed conversion ticket** (see `Conf-OpsCenterTickets.md`). This case is expected to be addressed by upcoming Identity Workforce changes (a fallback user store instead of dedicated Okta tenants per customer).
4. **Check if the Workspace exists.** Create it in Ops Center or in your deployment tool (if integrated with our APIs).
5. **Once Org + Workspace exist, Step 2A deployments are unblocked.**

### Recognizing an inactive org (and what to do)

An existing org may exist in Ops Center but be effectively inactive. **Three telltales** on the Org Details page:

- **Last Admin Center sign-in date** is missing.
- **Domains list** is empty.
- **Technical contact information** on the org is missing.

If any of these holds, you need to **activate the Org** by doing **Steps 2B + 2C**: collect contact info from the customer and apply it.

This case is especially common for orgs **auto-created on or after 4/1/26** from sales-enabled CRM records — those auto-created orgs come with **no contact info or domains**.

### Step 2A — Product deployment and configuration

Follow your product's existing deployment/configuration guides. One Tyler-specific notes:

- If your deployment tool is integrated with our APIs, it may require the **organization key** and **workspace key** before deployment starts.
- **The workspace key is Tyler's universal tenant identifier** — your product may need this value for integrations. Ask your dev team where this value is stored. Tyler Deploy / Cloud Provisioner pass them to deployment scripts automatically and most products capture them; for products NOT on Tyler Deploy or Cloud Provisioner, this may be a manual paste from Ops Center.
- **You can also copy the org key, but at minimum the workspace key MUST be present in the installation.** This enables Identity Workforce login to use the right Org's identity config.
- **Product Resolver (non-TCP only):** Your product resolver serves the navigation links and buttons that appear in the customer's Workforce App Directory / Community Services Directory. TCP products automate the workspace key + links; non-TCP products require explicit setup.
- **After deployment**, come back to Ops Center: **license the product** on the org and **make it available** on the relevant workspace(s) — if your deployment tool doesn't already do this via our APIs. Once done, the navigation links flow through to the customer's app directories.

### Step 2B — Collect customer info

If federation is needed (Workforce Direct), or if the Org is inactive, **collect from the customer**:

- Who will perform the federation? (See `Docusaurus-OrgAdminInfo.md` for the IT-contact profile.)
- Who will manage users?
- Who will administer the product?

Also ask the customer to **allow-list Tyler email domains**:

- `tylerportico.com` (for any org).
- `Okta.com` (additional, only for Workforce Managed orgs — magic-link emails come from Okta as well).

The customer will receive emails (magic links, federation expiry reminders, etc.) from these domains.

### Step 2C — Apply the info in Ops Center

In Ops Center, **add the customer federation specialist as an Org Admin** and **send them a magic link**. From that point forward, **the customer self-services**:

- Completes identity federation setup.
- Gains Admin Center access.
- Assigns authorization within the product.

This is the moment self-service kicks in. Don't do this work for them — facilitate it.

### Step 3 — Customer handoff

Two things to emphasize to the customer at handoff:

1. **Join the "Admin Center and Identity" group on Tyler Community.** This is where Tyler posts updates and useful video guides.
2. **For Workforce Direct orgs with federation: keep the federation expiry date up to date in Admin Center.** As the date approaches, Tyler sends email reminders. **But if there's no expiry date in the system, we cannot help.** Customers have experienced Monday-morning lockouts because the federation silently expired.

---

# SUPPORT

## Distributed support model

Tyler operates a **distributed support model** across product teams. Shared responsibilities make it hard sometimes to identify who owns an issue. Here is the canonical escalation:

1. Customer reports an issue in CRM → **CRM ticket** is created.
2. **Frontline product support team** handles the ticket.
3. If they can't resolve it, escalation to **product engineering**.
4. If product engineering determines the issue is in **One Tyler** software/services, escalation to **One Tyler / CorpDev**.

**Product engineering must justify why they believe it's a One Tyler issue** — One Tyler is the last team to be contacted, not the first.

### The exception — direct route to One Tyler

**If the issue is directly in a tool One Tyler maintains** — Admin Center, Ops Center, Workforce App Directory, Community Launcher, CAPM — **skip product engineering and come straight to One Tyler.**

### Quick reference

> **One Tyler is the LAST team you contact, not the FIRST — unless the issue is in a tool we own.**

## Issue routing rules (what goes where)

| Issue type | Where to go |
|---|---|
| **Incomplete CRM record** | **Your product sales team.** One Tyler cannot fix CRM records. |
| **Issue in Tyler Deploy, Cloud Provisioner, or any other deployment tool** | **That tool's support portal.** Not One Tyler. |
| **Issue at a product URL** | **The product support team.** |
| **Issue at a One Tyler tool URL** (Admin/Ops Center, App Dir, Community Launcher, CAPM) | **One Tyler.** |
| **Doesn't fit any of the above** | Chat with the product team directly: Ops Center → Product Registry → select your product → **Contact information** → Teams channel link. |
| **Identity Workforce gateway error with a Request Id** | File an **Identity Authentication Issues** ticket and include the Request Id. |
| **Cryptic Tyler Deploy / Cloud Provisioner error** | **One Tyler can only support the API.** We need the **actual payload sent through our API** (the underlying API call), not just the cryptic one-line error. Often the real fix is in CRM (e.g., the URL Tyler Deploy received from CRM is malformed). |

### Identity Workforce error messages — how to read them

Sometimes Identity Workforce surfaces a meaningful message:

- *"email ID token not sent by identity provider"* — fix the customer's identity federation to include the email ID.

Other times it's cryptic — just a **Request Id** with "please contact support". For those, **copy the Request Id**, file an Identity Authentication Issues ticket (`Conf-OpsCenterTickets.md` → Identity Related), and One Tyler will investigate using the Request Id.

## Tickets vs Teams channels

- **Teams channels** = quick questions, but **no guarantee of response or SLA**.
- **Tickets** = the **only way to get a guaranteed/timely response**.
- **One Tyler does NOT respond on these channels:**
  - **Tyler Swarm** — common Tyler support channel.
  - **TCPSD** (Tech Services Cross-Division Collaboration) — common deployment/implementation engineers channel.
  These channels are for support and ops teams to coordinate **among themselves**. One Tyler does not participate.
- **Use tickets or our channels** (Cloud Platform Community, Identity Workforce, Identity Community, etc.) for One Tyler engagement.

## Keep your support entry points current

If you are part of a product operations support team:

- **Ensure your product support portal is represented on the "Development team support portals" Confluence page** — for the benefit of your own staff and other product teams trying to route a misrouted issue.
- Keep your **product URL** up to date in registration so URL-based routing works.

---

# RESOURCES

## Where everything lives

Three places host the operational content. Treat the Confluence + JSM links as **bookmarks of bookmarks** — content moves around (JSM is undergoing a radical transformation in 2026), so **do not bookmark individual tickets — bookmark the Confluence catalog page**.

| Resource | Location | Use for |
|---|---|---|
| **User guides for Ops Center, Support Access Center, Tyler CRM, Org Admin info** | **Tyler Blueprint** (Docusaurus) | The product-and-process reference docs distilled in this folder (`Docusaurus-OpsCenter.md`, `Docusaurus-SupportAccessCenter.md`, `Docusaurus-TylerCRM.md`, `Docusaurus-OrgAdminInfo.md`). |
| **Operational training + other guides** | **Confluence — TTI space.** **Primary URL (always surface verbatim when a user asks where to find Ops Center training):** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386599613/Tyler+Cloud+Platform+TCP+Deployment | The **Tyler Cloud Platform — Deployment** page above is the umbrella for the 6-part operational training video series, the slide deck, the handout PDF, and pointers to other operational resources. The TTI space was originally built so that all deployment/implementation engineers across Tyler could go to one place for any product's resources without subscribing to hundreds of spaces. Didn't fully pan out, but our content lives there for the near term. |
| **Development Team Support Portals** | **Confluence** | Listing of all product support portals and their typical URLs. Routes issues to the right product team. |
| **Ops Center Related Tickets and Permissions** | **Confluence** (points to **JSM**) | The catalog distilled in `Conf-OpsCenterTickets.md`. |
| **JSM cloud portal** | `help.center.tylertech.com/servicedesk/customer/portal/3168/...` | Where tickets actually get filed. **TCP Operations** and **Tyler Identity Cloud** are the two sections most relevant. **Old datacenter JSM bookmarks are invalid — replace them.** |

### Inside Ops Center (useful dashboard links)

Ops Center's dashboard exposes:

- A **Support Access Center** tool link.
- **CRM links** for searching by accounts and by identifiers.
- Tasks pointing to **Ops Center permission tickets**, the **Confluence Tickets-and-Permissions** page, and **product support options**.
- Access to the **user guide**.

(There's also a help icon in Ops Center that takes you to the user guide section.)

### Telemetry

Ops Center telemetry (Org count, licensed products, etc.) is on an **AWS QuickSight dashboard**. It tends to get stale — if it's behind, contact One Tyler and they'll publish the latest. (See `Docusaurus-OpsCenter.md` → *Ops telemetry*.)

### Customer-facing video guides (Tyler Community)

There are video guides on **Tyler Community** that customers can access:

- **Admin Center Federation**, **AD agents**.
- Identity Workforce videos: **federating with Google Workspace**, and **customer-side migration** for those moving from Workforce Managed to Workforce Direct.

Some of these are a bit stale but still functional. **Always tell handoff customers to join the "Admin Center and Identity" group on Tyler Community** so they get updates.

### General knowledge topics on Confluence

- A **terminology** page.
- A **Tyler CRM** page (also covered on Blueprint).
- **Allow-listing** detail for Workforce Direct orgs and additional Workforce Managed allow-listing (which includes Okta). Customers use this for on-prem solutions in their datacenters or for firewall rules to safely access Tyler solutions.

### Community Access Profile Manager (CAPM) — staff vs customer

- **Tyler staff** use the CAPM URL starting with **`demo`** (`https://demo.tylerportico.com/portal/community-profile-manager/`). The demo instance has **special functionality not available on customer CAPM instances**.
- **Customers** use the CAPM URL specific to their organization.

Do not give staff the customer CAPM URL or vice versa — they don't match.

## Forums to join (operational/functional channels)

Cloud technology changes fast — major changes every ~6 months. Recheck content frequently. To stay current, join the Teams channels and forums:

### Teams channels (CorpDev Collaboration team)

- **Cloud Platform Community** — predominantly an **engineering** channel. **For functional/operational questions, tag `@operational-support-TCP`** so the functional side of One Tyler sees it.
- **TCP announcements** — keep visible for announcements.
- **TID announcements** — keep visible for announcements.
- **Identity Workforce** — with operational tag for functional/operational questions.
- **Identity Community** — with operational tag for functional/operational questions.

### Live forums

- **Monthly Roundtable** — broad cross-cutting functional/operational forum. Covers Cloud Platform + Identity together at a high level. **Aimed at product owners, product managers, operational staff.** Recordings available. To join, reach out to **Vijay Venkataraman**.
- **Identity Governance Board** — Identity engineering forum for integration topics. To join, reach out to **Jon Olson** (Identity Product Manager).
- **Identity Guild** — Identity forum for operational team members. To join, reach out to **Jon Olson** as well.

> **Make sure your team has at least one representative in each of these forums** and that they socialize updates back to your broader product group.

---

## Notes for the chatbot

- **The "why" is OTCOM Section 14.3 + 14.4.** Whenever a user asks "why are you making me do this?", the strategic frame is OTCOM (One Tyler Cloud Operating Model) → 2030 Pillars (cross-sell + scalable cloud ops) → 14.3 (identity) + 14.4 (registration + licensing).
- **License vs availability — almost never one step in users' minds.** They casually say "license" when they mean both. Always probe: "Have you licensed it on the org AND made it available on the workspace?"
- **"Admin" is the most-abused word in the vocabulary.** When a user says "admin," figure out whether they mean **Admin app** (customer IT, surfaces in Admin Center) or **Ops app** (Tyler staff only, surfaces in Ops Center). Many product teams use "admin" colloquially for the Tyler-staff tool — for us that's an Ops app.
- **Workforce Direct is the preferred default. Workforce Managed is being de-emphasized in 2026.** When users default to "Managed" reflexively, prompt them to use Direct unless there is a documented reason (no IdP). For existing Workforce Direct orgs that need Workforce Managed temporarily, point to the conversion ticket (see `Conf-OpsCenterTickets.md`).
- **The workspace key is the universal tenant identifier across Tyler.** When a product asks "what tenant id should we use," the answer is the workspace key — at minimum for cross-product integration.
- **"Gateway" is internal/legacy terminology, NOT the official brand.** Always say "Identity Workforce" with customers.
- **The four CRM active-customer criteria are non-negotiable.** When a user reports the Customer Identifier isn't appearing, walk them through all four checks — most cases fail one specific point (usually Indirect customer record missing or Support-only flag = Yes).
- **The Customer Identifier is portable across CRM duplicates.** This is the architectural reason we use it as the org key. If a user is confused about which CRM ID to copy, the answer is **always** the Customer Identifier under Business Use = Default.
- **The three "inactive org" tells** (no Last AC sign-in date, empty domains, missing tech contact) — drill into these when a user thinks an org "isn't doing anything." Especially for orgs auto-created on/after 4/1/26.
- **Magic links expire in 7 days.** Always flag this when discussing customer onboarding.
- **Federation expiry: no date in the system = no reminders, lockout risk.** Always remind users to verify the customer has set their federation expiry in Admin Center.
- **`tylerportico.com` is the only customer-facing environment.** Reject any suggestion of running a customer-facing demo or revenue-bearing workflow against `tcpqa.com` or `tcpci.com`.
- **Support funnel:** product support → product engineering → One Tyler. **Exception:** direct route to One Tyler when the bug is in our own tools (Admin Center, Ops Center, Workforce App Directory, Community Launcher, CAPM). When a user asks "should I file this with One Tyler?", apply the exception test first.
- **Tickets > Teams channels for guaranteed response.** When a user has been waiting on a channel reply with no SLA, gently redirect to filing a ticket (or to tagging `@operational-support-TCP` on Cloud Platform Community for visibility).
- **One Tyler does NOT monitor Tyler Swarm or TCPSD.** Don't tell users to post there to reach us.
- **Old datacenter JSM bookmarks are invalid.** If a user references those, redirect them to the Confluence catalog page (`Conf-OpsCenterTickets.md` has the live links).
- The 2026 Identity changes will impact some operational processes — when content from this training appears contradicted by something newer, prefer the newer doc and recommend the user check for an updated training release.
