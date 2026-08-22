# Ops Center — Miscellaneous Links and Bookmarks

Source: Curated bookmark list (entries link out to Confluence, Tyler Community, Coda, internal SharePoint, GitHub, etc., as noted per entry).
Domain: Ops Center
Audience: Tyler product operations team members — project managers, deployment, implementation, and support — plus anyone in adjacent ops roles who needs a quick pointer to authoritative external resources.

This file is the **catch-all bookmark catalog** for Ops Center. When a useful link doesn't belong in any of the structured reference files in this folder (Conf-OpsCenterTickets, Docusaurus-*, Training-*), it lives here. Each entry is self-contained: title, URL, what it is, audience, when to reach for it, and any related companions.

**Companion documents in this same Knowledge folder:**
- `Conf-OpsCenterTickets.md`, `Conf-GatewayOperationalTesting.md`, `Conf-AddingExternalUsersToEntraId.md`, `Docusaurus-OpsCenter.md`, `Docusaurus-Terminology.md`, `Docusaurus-TylerCRM.md`, `Docusaurus-OrgAdminInfo.md`, `Docusaurus-ProductRegistration.md`, `Training-OpsCenterOperations.md` — when an entry below has a distilled companion, it's cross-referenced.

---

## How to use this catalog

- The chatbot should retrieve entries here when a user asks for a **specific guide / page / portal / video / repo** that hasn't been distilled into one of the structured files.
- Each entry below uses the same shape — copy that shape when adding new bookmarks.
- If a link appears stale or returns 404, flag it back to the user; do not silently rewrite or guess a new URL.

### Entry shape (copy when adding new bookmarks)

```
### {Short title}

- **URL:** {full URL}
- **Source system:** {Confluence / Tyler Community / Coda / GitHub / SharePoint / Docusaurus / etc.}
- **What it is:** {one or two sentences}
- **Audience:** {who this is for}
- **Use when:** {the trigger — what the user is trying to do}
- **Related:** {pointer to companion file or other entry, if applicable}
```

---

# Bookmarks

## TCP / TID Operational Training (parent training hub + assets)

### Tyler Cloud Platform (TCP) | Deployment — Operational Training Hub (Parent Page)

- **URL:** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386599613/Tyler+Cloud+Platform+TCP+Deployment
- **Source system:** Confluence (TTI space)
- **What it is:** The umbrella training-and-resources page for **Operationalization of Product Registration and Identity Integration**. Hosts the 6-part training video series, training handouts, and pointers to operational support tickets, Tyler CRM access, and dev-team support portals. **Effective until H1 2026 only** — content will undergo significant changes with new Identity features releasing later in 2026, so bookmark the page for updates rather than the assets directly.
- **Audience:** Product **Project Managers**, **Deployment** engineers, **Implementation** engineers, and **Support** team members. Originally created for the Public Safety division and lightly edited for broader use (minor editing artifacts present in the videos).
- **Use when:** Onboarding someone new to product operations who needs the foundational training. Also a useful refresher if it's been a while.
- **Related:** **All 6 parts are operations training.** `Training-OpsCenterOperations.md` distills the conceptual parts (1, 2, 3, 6) into narrative summaries. Parts 4 (Typical Process Demo) and 5 (Cloud Tools Demo) are live-screen-recording videos of the same operational content in action — they are intentionally **not** distilled because live demos do not transcribe usefully; to learn that material, watch the videos directly on the training hub URL above.

### Part 1: Overview (Training Video)

- **URL:** https://tylertech-my.sharepoint.com/:v:/p/vijay_venkataraman/IQABLh0MocdwQ4TYZQZF-pPTARaz6vMU3GSuMMtaY1NTWVc?e=UtKL5T
- **Source system:** SharePoint (vijay.venkataraman OneDrive)
- **What it is:** Session 1, Part 1 video — strategic overview: Tyler 2030 Pillars, OTCOM 14.3/14.4, the cross-sell story, suite-like experience, Tyler SaaS control plane.
- **Audience:** PMs, Deployment, Implementation, Support (and anyone needing the "why").
- **Use when:** Someone needs the **strategic / "why are we doing this"** framing before the operational details.
- **Related:** `Training-OpsCenterOperations.md` → *Overview* section (distilled).

### Part 2: Basic Concepts (Training Video)

- **URL:** https://tylertech-my.sharepoint.com/:v:/p/vijay_venkataraman/IQB6fBMZUicCS6M8wuOijZvpAfKE6Vd9U4qMIhZTi90LnzM?e=QeEgJZ
- **Source system:** SharePoint (vijay.venkataraman OneDrive)
- **What it is:** Session 1, Part 2 video — vocabulary: app types (Workforce / Admin / Access / Ops), user types, Identity Workforce vs Community, Workforce Direct/Managed/Delegated, TCP vs non-TCP registration, Product/Org/Workspace constructs, the three environments (CI / QA / TylerPortico).
- **Audience:** PMs, Deployment, Implementation, Support — anyone shaky on the canonical terms.
- **Use when:** Someone needs the **vocabulary baseline** before getting into process or tools.
- **Related:** `Training-OpsCenterOperations.md` → *Basic Concepts* section (distilled); `Docusaurus-Terminology.md` (full canonical glossary).

### Part 3: Process Overview (Training Video)

- **URL:** https://tylertech-my.sharepoint.com/:v:/p/vijay_venkataraman/IQAghl8gOQ6YRbFFoZhx4FQnAeMtklJNvukhEuiZprXm2oU?e=6iiAR3
- **Source system:** SharePoint (vijay.venkataraman OneDrive)
- **What it is:** Session 1, Part 3 video — the typical operational process: sales-side CRM responsibilities (4-point active-customer criteria + CRM IDs), and the ops-side Step 1 / 2A / 2B / 2C / 3 model.
- **Audience:** PMs, Deployment, Implementation, Support.
- **Use when:** Someone needs the **end-to-end process model** that ties CRM record validity to org creation and customer handoff.
- **Related:** `Training-OpsCenterOperations.md` → *Typical Process* section (distilled); `Docusaurus-TylerCRM.md` (CRM validity checklist details).

### Part 4: Typical Process Demo (Training Video)

- **URL:** https://tylertech-my.sharepoint.com/:v:/p/vijay_venkataraman/IQAbcJjz_l3JRLs-VTWcIbHiATLBXiWQ44aZ7Msv1jH9FW0?e=KEldj8
- **Source system:** SharePoint (vijay.venkataraman OneDrive)
- **What it is:** Session 1, Part 4 video — live walkthrough/demo of the typical operational process described in Part 3.
- **Audience:** PMs, Deployment, Implementation, Support.
- **Use when:** Someone has already watched Part 3 (or read the distilled `Training-OpsCenterOperations.md`) and wants to see the steps actually performed in the tools.
- **Related:** **Not yet distilled** — this is a live demo with screen recording. The conceptual model lives in `Training-OpsCenterOperations.md` → *Typical Process*.

### Part 5: Cloud Tools Demo (Training Video)

- **URL:** https://tylertech-my.sharepoint.com/:v:/p/vijay_venkataraman/IQCHfUCdwWPjSYn2R1Owva-6AXcLM_-zn91thbPy9WjCEgg?e=4nAzBu
- **Source system:** SharePoint (vijay.venkataraman OneDrive)
- **What it is:** Session 2, Part 5 video — live demo of the Tyler cloud tools (Ops Center, Admin Center, Workforce App Directory, Community Launcher, CAPM, etc.).
- **Audience:** PMs, Deployment, Implementation, Support — anyone unfamiliar with the actual tool UIs.
- **Use when:** Someone needs to **see the cloud tools in action** rather than read about them.
- **Related:** **Not yet distilled.** Tool reference docs are in `Docusaurus-OpsCenter.md` and `Docusaurus-SupportAccessCenter.md` (in the SAC domain folder).

### Part 6: Support Overview, Access & Resources (Training Video)

- **URL:** https://tylertech-my.sharepoint.com/:v:/p/vijay_venkataraman/IQDPnLW3nJ6STKbNcS7JOLTSAW4U1bBmpOBHLL7V8BBfjdA?e=1oKzMw
- **Source system:** SharePoint (vijay.venkataraman OneDrive)
- **What it is:** Session 2, Part 6 video — the distributed support model (when to come to One Tyler vs product engineering), issue routing rules, resources (Blueprint / Confluence / JSM / Tyler Community), forums to join.
- **Audience:** PMs, Deployment, Implementation, Support.
- **Use when:** Someone is confused about **which support team to escalate to** or where to find which resources.
- **Related:** `Training-OpsCenterOperations.md` → *Support* and *Resources* sections (distilled).

### Handout Sheet — 2026.Q1.TCP-TID.Operational.Training-HandoutSheet.pdf

- **URL:** https://tylertech-my.sharepoint.com/:b:/p/vijay_venkataraman/IQDyrtPc9gwBSpmI-OGxIB8nASRfmnD8Poz9MQQBNC-M2rE?e=zEBatM
- **Source system:** SharePoint (vijay.venkataraman OneDrive) — PDF
- **What it is:** Single-page handout summary that accompanies the H1 2026 operational training.
- **Audience:** PMs, Deployment, Implementation, Support.
- **Use when:** Quick reference / printable summary to keep at your desk.
- **Related:** `Training-OpsCenterOperations.md` is the full distilled version.

### Presentation Deck — 2026.Q1.TCP-TID.Operational.Training.pdf

- **URL:** https://tylertech-my.sharepoint.com/:b:/p/vijay_venkataraman/IQAsqU6368WyQ5oNW41Cp9uWAV9J75ccCXKeZ7E-z3i_e5s?e=Ndh36V
- **Source system:** SharePoint (vijay.venkataraman OneDrive) — PDF
- **What it is:** The slide deck used in the training videos (Sessions 1 and 2).
- **Audience:** PMs, Deployment, Implementation, Support — and anyone delivering the training internally.
- **Use when:** You want the slides without watching the videos.
- **Related:** Distilled in `Training-OpsCenterOperations.md`.

---

## Cross-references to Other Knowledge files

These bookmarks point to the live source for content that is **also distilled into a structured Knowledge file** in this folder. Use the structured file for fast chatbot answers; use the URL for the always-current source.

### Tyler Cloud Platform (TCP) | Ops Center Related Tickets and Permissions

- **URL:** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386600308/Tyler+Cloud+Platform+TCP+Ops+Center+Related+Tickets+and+Permissions
- **Source system:** Confluence (TTI space)
- **What it is:** Confluence catalog of every CorpDev ticket type for Ops Center / Identity / Infra requests, with instructions and direct ticket-form links.
- **Audience:** Anyone filing an Ops Center, Identity, or infra ticket.
- **Use when:** You need to find the right ticket URL and the exact Notes-field wording.
- **Related:** `Conf-OpsCenterTickets.md` — full GPT-distilled catalog in this folder.

### Tyler CRM — Getting access, Sales-enabled CRM Records, CRM Customer identifiers (Docusaurus)

- **URL:** https://docs.tylerdev.io/app-guides/ops/ops-center/tylercrm/
- **Source system:** Docusaurus (`docs.tylerdev.io`)
- **What it is:** The Tyler CRM page on the CorpDev Blueprint Docusaurus site — how to get CRM access, what makes a sales-enabled CRM record, where the Customer Identifier lives.
- **Audience:** PMs, Deployment, Implementation staff who need to source the org key from CRM.
- **Use when:** Someone is trying to find or fix a CRM record so it becomes usable in Ops Center.
- **Related:** `Docusaurus-TylerCRM.md` — full GPT-distilled version in this folder.

### Tyler Cloud Platform (TCP) | Development team support portals

- **URL:** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386599215/Tyler+Cloud+Platform+TCP+Development+team+support+portals
- **Source system:** Confluence (TTI space)
- **What it is:** A registry of product support portals and the typical URLs they own. Helps route issues to the correct product team when a URL belongs to a product (vs. One Tyler tools).
- **Audience:** Tyler operational staff routing customer-reported issues.
- **Use when:** You see an unfamiliar URL in a customer ticket and need to figure out which product team owns it. **If your product's support portal isn't listed**, add it.
- **Related:** Referenced extensively in `Training-OpsCenterOperations.md` → *Support — issue routing rules*.

---

## Operational topic deep-dives (Confluence)

Each entry below is a Confluence deep-dive on a specific operational topic. **If you supply HTML for any of these, I'll distill it into its own `Conf-<Topic>.txt` Knowledge file alongside the bookmark entry.**

### Tyler Cloud Platform (TCP) | CRM Customer Identifiers

- **URL:** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386599914/Tyler+Cloud+Platform+TCP+CRM+Customer+Identifiers
- **Source system:** Confluence (TTI space)
- **What it is:** **The** deep technical/operational reference for the CRM Customer Identifier. Covers: what the value is (25-char alphanumeric, URL+DB-friendly), the **generation algorithm** (Company Name + State + Country, 600+ abbreviation substitution list, first-letters fallback), why it's **better than** CRM Id / Account Number / GUID (**portability across CRM duplicate merges**), the `Business Use = Default` rule for multiple identifiers, where it's used across **TCP (`<id>.tylerportico.com`), Tyler Deploy, TID-W (`tyler-<id>.okta.com`), SaaS hub (`<id>.tylerhub.com`), Tyler Notify (Twilio sub-account tag)**, internal-use record patterns (`99999999XXXX` Account Numbers), the full troubleshooting tree, and the exact ticket subjects/recipients for assistance and regeneration. **Roughly ~2,000 legacy CRM identifiers do NOT match the algorithm** — flagged for awareness.
- **Audience:** PMs, Deployment, Implementation, Support working with CRM records to source org keys; product engineering teams adopting the Customer Identifier; anyone troubleshooting a missing / wrong / duplicated identifier.
- **Use when:** The CRM Customer Identifier is missing, wrong, in the wrong default slot after a merge, or you need to know how a specific Tyler system consumes the value.
- **Related:** **`Conf-CRMCustomerIdentifiers.md`** — full GPT-distilled version in this folder (use that for fast chatbot answers). `Docusaurus-TylerCRM.md` is the lighter Docusaurus version (4-point validity checklist). `Training-OpsCenterOperations.md` has the "CRM IDs — don't confuse them" table.

### Tyler Cloud Platform (TCP) | Community Access Profile Manager (CAPM)

- **URL:** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386599847/Tyler+Cloud+Platform+TCP+Community+Access+Profile+Manager
- **Source system:** Confluence (TTI space) — content also available as `CAProfileManagerIG.pdf`.
- **What it is:** The CAPM **Implementation and Access Guide**. Explains what CAPM is (helpdesk tool for customer staff to support residents/small-businesses/constituents with Community Access accounts — reset accounts, unlock accounts), how it's licensed (included with any Tyler product that has public-facing site/services), and how a customer's Org Admin grants their support staff access — both via the **default pre-provisioned "Community Access Support" workspace group** AND via the **manual group-creation wizard for older orgs** that don't have the default group. Recommends a dedicated group with just the CAPM app on the production workspace only.
- **Audience:** Tyler operational staff (deployment, implementation, support) coaching a customer's Org Admin through the setup; customer Org Admins directly.
- **Use when:** A customer asks how to give their helpdesk staff access to CAPM; or you need to walk a customer through manual group creation because the "Community Access Support" group doesn't exist on their older org.
- **Related:** **`Conf-CommunityAccessProfileManager.md`** — full GPT-distilled version in this folder. **Different flow** for **Tyler-staff** CAPM access: see `Conf-OpsCenterTickets.md` → *CAPM access request* (uses form 4133 with TCP Tool Selection = "CAPM"; Tyler staff use the **demo** CAPM URL `https://demo.tylerportico.com/portal/community-profile-manager/`, not the customer's org-specific URL).

### Tyler Cloud Platform (TCP) | Identity Workforce Profile

- **URL:** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386599967/Tyler+Cloud+Platform+TCP+Identity+Workforce+Profile
- **Source system:** Confluence (TTI space)
- **What it is:** Reference on the Identity Workforce **Profile** — the extended attributes stored against a Workforce user in the context of an organization.
- **Audience:** Engineering and operational staff who need to understand what the Workforce Profile holds and how products consume it.
- **Use when:** Someone is asking what fields/attributes a Workforce user actually has, or how products read them.
- **Related:** `Docusaurus-Terminology.md` → *Workforce Profile* and *Workforce User*.

### Tyler Cloud Platform (TCP) | Reestablish Federation Demo

- **URL:** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386625934/Tyler+Cloud+Platform+TCP+Reestablish+Federation+Demo
- **Source system:** Confluence (TTI space)
- **What it is:** Demo walkthrough of the **Reestablish Federation** feature in Ops Center — how to send a customer IT admin a magic link to re-set up a federation that is about to expire or has expired.
- **Audience:** Tyler identity-support staff helping customers restore an expired/expiring federation.
- **Use when:** A customer's federation has expired or is about to, and you need to walk the customer through reestablishment.
- **Related:** `Docusaurus-OpsCenter.md` → *Establish / Reestablish federations*; `Conf-OpsCenterTickets.md` → *Reestablish Federation* permission request.

### Tyler Cloud Platform (TCP) | Ops Center — Setup AD Agent User Account

- **URL:** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386599721/Tyler+Cloud+Platform+TCP+Ops+Center+-+Setup+AD+Agent+User+Account
- **Source system:** Confluence (TTI space)
- **What it is:** Demo/documentation for the **Setup / Reset AD Agent User Account** feature in Ops Center — used on **Workforce Managed** orgs to create the AD Agent account that syncs Windows Server Active Directory with the Okta user store.
- **Audience:** Tyler identity-support staff helping customers set up Active Directory sync on a Workforce Managed org.
- **Use when:** A customer needs to install or reset the Okta AD Agent against their on-prem Active Directory.
- **Related:** `Docusaurus-OpsCenter.md` → *Add/Reset AD Agent account*; `Conf-OpsCenterTickets.md` → *Setup/Reset AD Agent* permission request.

### Tyler Cloud Platform (TCP) | Gateway Operational Testing

- **URL:** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386600150/Tyler+Cloud+Platform+TCP+Gateway+Operational+Testing
- **Source system:** Confluence (TTI space)
- **What it is:** How to plan testing of your **Gateway-ready** product under real-world conditions, using the `tylertownwa` test org. Covers the 4 Gateway components, Core vs Full compliance, test credentials, Tyler Deploy-specific guidance, and net-new-customer routing rules. **This page is the authoritative source for the `tylertownwa` test password** (see its *Test credentials* section) — the distilled file deliberately omits it.
- **Audience:** Tyler product engineering and operational team members validating a Gateway-ready product before customer deployment.
- **Use when:** Your product has reached Core Gateway readiness and you need to run real-world validation; or you're handling a net-new customer whose product mix has mixed Gateway readiness.
- **Related:** **`Conf-GatewayOperationalTesting.md`** — full GPT-distilled version in this folder.

### Tyler Cloud Platform (TCP) | Adding external users to Entra Id without consuming an Office 365 license (Workforce Direct Orgs ONLY)

- **URL:** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386635379/Tyler+Cloud+Platform+TCP+Adding+external+users+to+Entra+Id+without+consuming+an+Office+365+license+Workforce+Direct+Orgs+ONLY
- **Source system:** Confluence (TTI space)
- **What it is:** 3-step workaround for **Workforce Direct** customers who need to add non-regular-employee users (temps, contractors without a company email inbox) to their Entra ID without burning an Office 365 license.
- **Audience:** Tyler operational staff coaching a Workforce Direct customer's IT admin. **Do NOT share the Confluence URL directly with customers** — the page is internal-only guidance.
- **Use when:** A WD customer asks how to provision access for non-employees without buying O365 licenses for them.
- **Related:** **`Conf-AddingExternalUsersToEntraId.md`** — full GPT-distilled version in this folder.

### Tyler Cloud Platform (TCP) | Org Admin promotions (Admin Center access) — a Manager's guide

- **URL:** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386629479/Tyler+Cloud+Platform+TCP+Org+Admin+promotions+Admin+Center+access+-+a+Manager+s+guide
- **Source system:** Confluence (TTI space)
- **What it is:** The **manager's-guide** procedure for adding an Org Admin or self-promoting as an Org Admin in Ops Center. This is the canonical flow — **NOT** the generic permission ticket form 4133.
- **Audience:** Tyler managers of product ops teams; ops staff who need to promote themselves or a teammate to Org Admin on a customer org.
- **Use when:** Someone asks "how do I add an Org Admin" or "how do I get promoted to Org Admin on a customer org" — the generic permission ticket does NOT cover this.
- **Related:** `Conf-OpsCenterTickets.md` → *Org Admins* (this is the explicit exception flow flagged there); `Docusaurus-OpsCenter.md` → *Organization Details > Admins*.

### Tyler Cloud Platform (TCP) | Import an organization (Demo)

- **URL:** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386630359/Tyler+Cloud+Platform+TCP+Import+an+organization
- **Source system:** Confluence (TTI space)
- **What it is:** Demo walkthrough of the **+Import (an organization)** feature in Ops Center — self-service org creation for Workforce Direct / Delegated customers (the alternative to filing a new-org ticket).
- **Audience:** Deployment / implementation staff with the +Import permission, who are creating customer orgs themselves.
- **Use when:** You have a Workforce Direct customer with a valid CRM record and you want to create their Org without waiting on CorpDev.
- **Related:** `Docusaurus-OpsCenter.md` → *Import an organization* wizard; `Conf-OpsCenterTickets.md` → *+Import (an organization)* permission request; `Docusaurus-TylerCRM.md` (CRM prerequisites); `Docusaurus-OrgAdminInfo.md` (Org Admin sourcing).

### Tyler Cloud Platform (TCP) | Community Services Directory (Demo)

- **URL:** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386635432/Tyler+Cloud+Platform+TCP+Community+Services+Directory+Demo
- **Source system:** Confluence (TTI space)
- **What it is:** Demo of the **Community Services Directory (CSD)** — the public-facing portal where a customer's residents and other public users discover community services across the customer's Tyler solutions.
- **Audience:** Product teams adopting Community apps; operational staff explaining CSD to customers.
- **Use when:** Someone needs to understand what the CSD looks like / where Community apps surface to public users.
- **Related:** `Docusaurus-Terminology.md` → *Community Services Directory*; `Docusaurus-ProductRegistration.md` → *Community App* surface area.

### Tyler Cloud Platform (TCP) | Workforce Delegated

- **URL:** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386635142/Tyler+Cloud+Platform+TCP+Workforce+Delegated
- **Source system:** Confluence (TTI space)
- **What it is:** Deep-dive on the **Workforce Delegated** identity tier — Super/Sub org relationship, when it applies (e.g., school district + schools, city + dependent department), and what is and isn't allowed in a Sub org.
- **Audience:** Deployment / implementation staff working with a customer who is a candidate for Workforce Delegated; identity-support staff.
- **Use when:** A customer relationship looks like one org should depend 100% on another for identity (school district + schools, city + police), and you need to confirm whether Delegated is the right setup.
- **Related:** `Docusaurus-Terminology.md` → *Workforce Delegated* (canonical definition); `Docusaurus-OpsCenter.md` → Import/Create wizards' Workforce Delegated branch.

### Tyler Cloud Platform (TCP) | Google Workspace Federation with Workforce Direct Orgs

- **URL:** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386635174/Tyler+Cloud+Platform+TCP+Google+Workspace+Federation+with+Workforce+Direct+Orgs
- **Source system:** Confluence (TTI space)
- **What it is:** Setup guide for federating a Workforce Direct customer's **Google Workspace** IdP into Identity Workforce.
- **Audience:** Tyler identity-support staff and customers whose IdP is Google Workspace.
- **Use when:** A Workforce Direct customer uses Google Workspace as their IdP and needs federation set up.
- **Related:** Customer-facing video guide may also exist on Tyler Community (per `Training-OpsCenterOperations.md` → *Resources*).

### Tyler Cloud Platform (TCP) | Workforce Managed to Workforce Direct Retargeting and Migration

- **URL:** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386635412/Tyler+Cloud+Platform+TCP+Workforce+Managed+to+Workforce+Direct+Retargeting+and+Migration
- **Source system:** Confluence (TTI space)
- **What it is:** Runbook for migrating a customer's workspaces from **Workforce Managed → Workforce Direct** (the Tyler-strategic direction in 2026).
- **Audience:** Tyler identity / operational staff performing a WM-to-WD migration for a customer.
- **Use when:** A Workforce Managed customer is moving to Workforce Direct (typically once their product mix supports it).
- **Related:** `Conf-OpsCenterTickets.md` → *Orgs > Organization Details > Workspace migration*; `Docusaurus-OpsCenter.md` → *Workspace migration*.

### Tyler Cloud Platform (TCP) | SAC and Security API Preview Demo

- **URL:** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/477396994/Tyler+Cloud+Platform+TCP+SAC+and+Security+API+Preview+Demo
- **Source system:** Confluence (TTI space)
- **What it is:** Preview demo of **Support Access Center (SAC)** and the **`tcp-login-security-api`** that products integrate with to adopt SAC.
- **Audience:** Product engineering teams considering adopting SAC; operational staff understanding the customer-controlled access model.
- **Use when:** A product team is deciding whether/how to adopt SAC, or you need to see SAC's Security API behavior demonstrated.
- **Related:** `Docusaurus-SupportAccessCenter.md` in `Knowledge-SupportAccessCenter/` — full GPT-distilled reference for SAC.

### Tyler Cloud Platform (TCP) | Bulk licensing preview

- **URL:** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/942347495/Tyler+Cloud+Platform+TCP+Bulk+licensing+preview
- **Source system:** Confluence (TTI space)
- **What it is:** Preview/demo of the **Bulk Licensing** feature in Ops Center Product Registry, which licenses a product across many organizations and their workspaces in one operation.
- **Audience:** Product teams onboarding a product across many existing customer orgs; ops staff with Bulk Licensing permission.
- **Use when:** Looking ahead at a bulk-license job before running it (especially the first time).
- **Related:** `Docusaurus-OpsCenter.md` → *Bulk Licensing* (Product Registry); Coda has a more comprehensive guide with videos at https://coda.io/d/_dKV_6fSnfBc/Post-registration-activities_suK0yhd_#_lu-oRzAm

### Environments (SPY space) — TCP environment URLs + allow-listing reference

- **URL:** https://tylertech.atlassian.net/wiki/spaces/SPY/pages/407175596/Environments
- **Source system:** Confluence (SPY space)
- **What it is:** The canonical reference for TCP **environments and allow-listing**. Covers the three AWS environments (CI / QA / Production) with their root domains, Ops Center URLs, and TID realm pairings; **inbound allow-list** (root domains for traffic on-prem → TCP); **outbound allow-list** (cluster outbound IPs and `allow-list.<env>.com` DNS endpoints for traffic TCP → on-prem); the four Tyler Identity (Okta) instance URIs; sign-on / portal-access flow for Tyler staff getting added to TCP portals; DataDog infrastructure dashboard link; supported-browsers pointer.
- **Audience:** Tyler operational staff configuring customer firewalls or troubleshooting connectivity; customer IT admins receiving allow-list requirements; Tyler staff getting added to a TCP portal for the first time.
- **Use when:** A customer is configuring firewall allow-lists to connect on-prem systems to TCP (or vice versa); an internal Tyler staff member needs the canonical egress IPs or DNS endpoints; or someone needs the Ops Center URL for a specific environment.
- **Related:** **`Conf-EnvironmentsAndAllowListing.md`** — full GPT-distilled version in this folder (includes the explicit IP lists snapshot). `Docusaurus-OpsCenter.md` has the same three Ops Center URLs distilled. `Conf-OpsCenterTickets.md` covers the Cloud Platform support ticket referenced from this page.

---

## Blueprint Docusaurus reference catalog (`docs.tylerdev.io`)

This section catalogs **substantive content pages** from the **Tyler Blueprint** Docusaurus documentation at `https://docs.tylerdev.io/`. Pages already distilled into a structured `Docusaurus-*.txt` Knowledge file in this folder are intentionally NOT repeated here — that includes the entire Terminology page (`Docusaurus-Terminology.md`), the Ops Center user guide (`Docusaurus-OpsCenter.md`), Tyler CRM (`Docusaurus-TylerCRM.md`), Org Admin Info (`Docusaurus-OrgAdminInfo.md`), Product Registration (`Docusaurus-ProductRegistration.md`), and Support Access Center (`Docusaurus-SupportAccessCenter.md` in `Knowledge-SupportAccessCenter/`).

Entries below are grouped by Blueprint top-level section. The Blueprint site is internal Tyler documentation but does not require Tyler SSO to read — URLs work from anywhere with the link.

## Aligned Releases

### Aligned Releases Overview

- **URL:** https://docs.tylerdev.io/aligned-releases/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Framework describing Tyler's unified quarterly release system, including feature lifecycle stages (Planned → Private Preview → Public Preview → GA), cohort-based rollout schedules, and key business objects. Documents how product teams coordinate release communication and client activation across all product lines.
- **Audience:** Product teams, engineering leaders, product managers coordinating feature releases
- **Use when:** Planning quarterly releases, understanding cohort activation timelines, or learning how features move through preview stages to GA
- **Related:** Cross-references to Product Registration and Platform Architecture concepts

### Aligned Releases Integration Guide

- **URL:** https://docs.tylerdev.io/aligned-releases/guides/integrating-with-aligned-releases/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Step-by-step integration guide for adding releases and managing feature lifecycles using the Aligned Releases API. Covers OAuth 2.0 setup, authentication with Tyler Identity Gateway, API endpoints across environments (TCPCI, TCPQA, TCPPROD), and code examples in both HTTP and C# SDK.
- **Audience:** Platform engineers integrating with Aligned Releases API, backend service developers
- **Use when:** Building integrations with the Aligned Releases system, setting up OAuth authentication, or implementing release workflows programmatically

### Aligned Releases API Specification

- **URL:** https://docs.tylerdev.io/aligned-releases/api-reference/specification/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** OpenAPI/Swagger specification for the Aligned Releases API, providing technical reference for all endpoints, request/response schemas, and message types.
- **Audience:** Developers building against Aligned Releases APIs
- **Use when:** Looking up specific API endpoints, request parameters, or response structures

### Aligned Releases Integration Checklist

- **URL:** https://docs.tylerdev.io/aligned-releases/integration-checklists/aligned-releases-checklist/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Pre-integration checklist validating readiness for Aligned Releases adoption—requirements, dependencies, team alignment steps.
- **Audience:** Product teams preparing for Aligned Releases adoption
- **Use when:** Planning an Aligned Releases integration project

---

## Get Started

### Cloud Living Overview

- **URL:** https://docs.tylerdev.io/get-started/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** High-level introduction to One Tyler Cloud Living initiative covering Tyler's 2030 strategic pillars, phases of cloud transformation (Phase 1: migration to AWS; Phase 2: cloud operating model; Phase 3: consolidation), and overview of CorpDev shared services (Identity, Admin Center, Ops Center, Forge). Includes embedded video on Cloud Living, Ops Center, and Admin Center.
- **Audience:** Product teams, executives, architects understanding Tyler's cloud strategy
- **Use when:** Orienting to Cloud Living principles, understanding shared services strategy, or learning Tyler's cloud transformation roadmap

### Platform Overview

- **URL:** https://docs.tylerdev.io/get-started/platform-overview/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Multi-page guide covering the Tyler Cloud Platform (TCP) architecture, core platform services, and how they integrate to enable cloud applications.
- **Audience:** Solution architects, platform engineers, product teams adopting TCP services
- **Use when:** Understanding the overall TCP platform structure and service ecosystem

---

## Identity

### Identity Overview (Key Concepts)

- **URL:** https://docs.tylerdev.io/identity/key-concepts/overview/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Foundational overview of Tyler Identity (TID) system, covering two primary authentication models: Identity Workforce (for back-office/workforce users) and Community Access (for public-facing/citizen users), plus shared services and architecture patterns.
- **Audience:** Product teams, architects evaluating Tyler Identity solutions
- **Use when:** Deciding between Workforce and Community authentication models or understanding TID architecture

### Identity Workforce: Getting Started

- **URL:** https://docs.tylerdev.io/identity/workforce/getting-started/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Complete guide to integrating with Identity Workforce, Tyler's cloud IDaaS solution. Covers Identity Gateway as OIDC/federation router, prerequisites (OIDC fundamentals, customer IdP requirements), product registration flow (single vs. multi-tenant apps), OIDC authentication setup, configuration fields, and certified OIDC libraries. Includes links to accelerators and sample code.
- **Audience:** Backend developers, platform engineers integrating Workforce identity
- **Use when:** Starting Identity Workforce integration or implementing OIDC authentication with Tyler Gateway

### Identity Workforce: Best Practices

- **URL:** https://docs.tylerdev.io/identity/workforce/best-practices/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Security and implementation best practices for Identity Gateway integration, including mandatory PKCE usage, token claim validation, client secret protection, token lifetime management, logout handling, and code examples in JavaScript and C#.
- **Audience:** Developers implementing Workforce identity, security-focused teams
- **Use when:** Building production Identity Workforce integrations or hardening existing implementations

### Identity Workforce: Configuration

- **URL:** https://docs.tylerdev.io/identity/workforce/configuration/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to configuring Workforce identity for organizations including adding IdP domains, setting up federation with various providers (ADFS, Entra ID, Okta, Google Workspace, etc.), managing identity provider lifecycle, and troubleshooting federation issues.
- **Audience:** Ops staff, identity admins, IT teams configuring customer IdPs
- **Use when:** Setting up federation with a customer IdP or modifying existing Workforce configurations

### Identity Workforce: Troubleshooting

- **URL:** https://docs.tylerdev.io/identity/workforce/troubleshooting/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Reference guide for common Identity Workforce issues including login failures, configuration problems, federated authentication errors, token issues, and specific troubleshooting steps for each scenario.
- **Audience:** Support engineers, product team ops staff, identity admins
- **Use when:** Diagnosing Identity Workforce authentication or configuration issues

### Identity Workforce: Token Formats and Claims

- **URL:** https://docs.tylerdev.io/identity/workforce/tokens/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Reference for JWT token structure, claims, and optional claims (like `amr_passthrough` for risk-based authentication) returned by Identity Gateway, including claim descriptions and usage patterns.
- **Audience:** Developers working with JWT tokens, backend services consuming Gateway tokens
- **Use when:** Understanding token claims or configuring token-based authorization

### Identity Workforce: Advanced Multi-Tenancy (Dynamic Auth)

- **URL:** https://docs.tylerdev.io/identity/workforce/dynamic-auth/overview/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Documentation on Identity Workforce's Dynamic Auth feature for ASP.NET applications supporting multi-tenant scenarios without per-tenant client registration. Includes overview and usage guides.
- **Audience:** ASP.NET developers building multi-tenant Workforce applications
- **Use when:** Implementing dynamic tenant switching or scaling multi-tenant applications

### Identity Workforce: Identity Gateway Environments

- **URL:** https://docs.tylerdev.io/identity/workforce/identity-gateway/environments/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Reference for Identity Gateway environment endpoints, URLs, and configurations across TCPCI (dev), TCPQA (test), and TCPPROD (production).
- **Audience:** Developers, ops staff managing Gateway configurations
- **Use when:** Configuring environment-specific Gateway endpoints

### Identity Workforce: Identity Gateway FAQ

- **URL:** https://docs.tylerdev.io/identity/workforce/identity-gateway/faq/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Common questions and answers about Identity Gateway operation, configuration, and troubleshooting.
- **Audience:** Teams using Identity Gateway
- **Use when:** Finding quick answers about Gateway functionality

### Identity Workforce: Identity Gateway Token Format

- **URL:** https://docs.tylerdev.io/identity/workforce/identity-gateway/tokens/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Detailed token format and claims reference for Identity Gateway JWT tokens.
- **Audience:** Token consumers, backend service developers
- **Use when:** Understanding Gateway token structure and claims

### Identity Workforce: Identity Gateway History and Migration

- **URL:** https://docs.tylerdev.io/identity/workforce/identity-gateway/history/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Historical context on Identity Gateway evolution and migration paths for teams moving from legacy identity systems.
- **Audience:** Platform teams, legacy system owners
- **Use when:** Understanding Identity Gateway's development context or planning migrations

### Identity Workforce: Identity Gateway Transition Plan

- **URL:** https://docs.tylerdev.io/identity/workforce/identity-gateway/transition-plan/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Transition guidance for teams adopting Identity Gateway, including timelines, deprecation notices, and migration strategies.
- **Audience:** Product teams planning Gateway adoption
- **Use when:** Planning migration to Identity Gateway

### Identity Workforce: Authentication Code Flow Diagrams

- **URL:** https://docs.tylerdev.io/identity/workforce/diagrams/auth-code-flow-pkce/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Detailed sequence diagram for OAuth 2.0 Authorization Code Flow with PKCE through Identity Gateway.
- **Audience:** Developers implementing Workforce OIDC flows
- **Use when:** Understanding the step-by-step OIDC authentication flow

### Identity Workforce: FAQ

- **URL:** https://docs.tylerdev.io/identity/workforce/faq/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Frequently asked questions about Workforce identity setup and usage.
- **Audience:** Teams implementing Workforce identity
- **Use when:** Finding quick answers about Workforce functionality

### Identity Workforce: Login Context

- **URL:** https://docs.tylerdev.io/identity/workforce/login-context/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to using login context and multi-organization switching in Identity Workforce applications.
- **Audience:** Frontend developers, UX teams
- **Use when:** Implementing organization/workspace switching UI

### Identity Community Access: Getting Started

- **URL:** https://docs.tylerdev.io/identity/community/getting-started/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Complete guide to Community Access, Tyler's single sign-on for citizen-facing applications. Covers architecture (Tyler-managed Okta vs. federated state IdPs), prerequisites, integration steps, OIDC setup, and sample code links.
- **Audience:** Frontend developers, citizen-facing application teams
- **Use when:** Implementing Community authentication or citizen login

### Identity Community Access: Configuration

- **URL:** https://docs.tylerdev.io/identity/community/configuration/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Detailed guide to configuring Community Access including domain setup, Okta tenant configuration, federation with state IdPs, user directory management, and branding.
- **Audience:** Ops staff, identity admins managing Community instances
- **Use when:** Setting up or modifying Community Access configuration

### Identity Community Access: Best Practices

- **URL:** https://docs.tylerdev.io/identity/community/best-practices/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Security and implementation best practices for Community Access including public application security, PKCE requirements, session management, logout patterns, and user experience considerations.
- **Audience:** Developers building citizen-facing apps, security teams
- **Use when:** Implementing production Community Access or hardening existing implementations

### Identity Community Access: Troubleshooting

- **URL:** https://docs.tylerdev.io/identity/community/troubleshooting/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Troubleshooting guide for Community Access issues including login failures, configuration problems, federation errors, and diagnostic steps.
- **Audience:** Support engineers, ops staff
- **Use when:** Diagnosing Community Access problems

### Identity: Glossary

- **URL:** https://docs.tylerdev.io/identity/glossary/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Comprehensive glossary of identity and authentication terms used across Tyler Identity documentation (IdP, OIDC, JWT, PKCE, etc.).
- **Audience:** Teams new to identity concepts
- **Use when:** Looking up identity terminology

### Identity Workforce: Client Operations API

- **URL:** https://docs.tylerdev.io/identity/identity-guides/client-operations/overview/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Overview and API specification for managing client applications in Identity Workforce programmatically (create, update, delete clients).
- **Audience:** Platform engineers managing Identity Workforce clients programmatically
- **Use when:** Building automation for client lifecycle management

### Identity: Credential Templates Overview

- **URL:** https://docs.tylerdev.io/identity/identity-guides/credential-templates/overview/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Introduction to Tyler's credential template system for managing OAuth clients (Login PKCE, ServiceCCF) in version-controlled YAML files, including repository organization strategies.
- **Audience:** Backend teams, DevOps engineers managing application credentials
- **Use when:** Setting up credential template infrastructure

### Identity: Credential Templates Walkthrough

- **URL:** https://docs.tylerdev.io/identity/identity-guides/credential-templates/walkthrough/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Interactive walkthrough with dynamic form inputs showing end-to-end credential template setup from repo configuration through credential usage, including GitHub app setup and template file creation.
- **Audience:** New teams adopting credential templates
- **Use when:** Implementing credential templates for the first time

### Identity: Credential Template Schemas

- **URL:** https://docs.tylerdev.io/identity/identity-guides/credential-templates/schemas/credentialtemplate/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Schema reference for credential template YAML files defining OAuth client configurations.
- **Audience:** Engineers writing credential templates
- **Use when:** Creating credential template YAML files

### Identity: Credential Template Config Schemas

- **URL:** https://docs.tylerdev.io/identity/identity-guides/credential-templates/schemas/credentialconfig/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Schema reference for credential configuration files defining which repositories and branches host templates.
- **Audience:** Ops/DevOps engineers setting up credential template repos
- **Use when:** Creating `.github/credential-config` files

### Identity: Credential Template Recipes

- **URL:** https://docs.tylerdev.io/identity/identity-guides/credential-templates/recipes/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Collection of template organization patterns (file-per-service, single-file-per-env, file-per-env-by-branch) and repo organization strategies (templates-in-mono-repo, template-per-repo, templates-in-provisioning-repo).
- **Audience:** Teams designing credential template repositories
- **Use when:** Choosing credential template organization strategy

### Identity: Credential Template GitHub App Integration

- **URL:** https://docs.tylerdev.io/identity/identity-guides/credential-templates/github_app/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Setup guide for integrating the credential template GitHub App into repositories for automated validation and credential provisioning.
- **Audience:** DevOps engineers setting up GitHub integration
- **Use when:** Installing credential template GitHub App

### Identity: Provisioning SDK

- **URL:** https://docs.tylerdev.io/identity/identity-guides/credential-templates/provisioning_sdk/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Reference for the credential template provisioning SDK used to programmatically work with credential templates.
- **Audience:** Developers building credential template tooling
- **Use when:** Implementing custom provisioning workflows

### Identity: Provisioning SDK Examples

- **URL:** https://docs.tylerdev.io/identity/identity-guides/credential-templates/provisioning_sdk/examples/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Code examples showing SDK usage for credential template operations.
- **Audience:** Developers using provisioning SDK
- **Use when:** Learning SDK patterns

### Identity: Community Integration Checklist

- **URL:** https://docs.tylerdev.io/identity/integration-checklists/community-checklist/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Pre-integration checklist for Community Access adoption covering prerequisites, configuration steps, and readiness criteria.
- **Audience:** Teams planning Community Access integration
- **Use when:** Planning Community integration project

### Identity: Workforce Integration Checklist

- **URL:** https://docs.tylerdev.io/identity/integration-checklists/workforce-checklist/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Pre-integration checklist for Workforce identity adoption including prerequisites, configuration, and go-live steps.
- **Audience:** Teams planning Workforce integration
- **Use when:** Planning Workforce integration project

### Identity: Events System

- **URL:** https://docs.tylerdev.io/identity/identity-guides/events/overview/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Overview of identity events emitted by Tyler Identity system (user created, password changed, etc.) and subscribing to them.
- **Audience:** Service teams consuming identity events
- **Use when:** Building event-driven workflows on identity changes

### Identity: Events Examples

- **URL:** https://docs.tylerdev.io/identity/identity-guides/events/examples/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Code examples showing event subscription and handling patterns.
- **Audience:** Developers implementing identity event consumers
- **Use when:** Learning event subscription patterns

### Identity: Client Operations (Shared)

- **URL:** https://docs.tylerdev.io/identity/shared/client-operations/overview/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Shared client operations API reference for programmatic application management across both Workforce and Community contexts.
- **Audience:** Platform engineers, automation developers
- **Use when:** Managing applications programmatically across identity contexts

### Identity: Dual Trust (API Gateway)

- **URL:** https://docs.tylerdev.io/identity/identity-guides/api-dual-trust/overview/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Documentation on dual-trust authentication pattern for APIs accepting both Identity Workforce and legacy authentication methods during transition periods.
- **Audience:** Platform engineers building backward-compatible APIs
- **Use when:** Implementing dual-trust API authentication during identity migrations

### Identity: Workforce Direct

- **URL:** https://docs.tylerdev.io/identity/identity-guides/customer-facing/workforce-direct/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to Workforce Direct authentication model for directly managed workforce users (without customer-provided IdP).
- **Audience:** Product teams supporting managed workforce users
- **Use when:** Implementing or configuring Workforce Direct

### Identity: Dynamic Auth Usage

- **URL:** https://docs.tylerdev.io/identity/identity-guides/workforce/dynamic-auth/using/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Implementation guide for using Dynamic Auth in ASP.NET applications for multi-tenant scenarios.
- **Audience:** ASP.NET developers
- **Use when:** Building multi-tenant ASP.NET applications

### Identity: Workforce Getting Started (Identity Guides)

- **URL:** https://docs.tylerdev.io/identity/identity-guides/workforce/getting-started/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Alternative getting started guide for Workforce from identity-guides context.
- **Audience:** Teams learning Workforce implementation
- **Use when:** Learning Workforce basics

### Identity: Community Getting Started (Identity Guides)

- **URL:** https://docs.tylerdev.io/identity/identity-guides/community/getting-started/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Alternative getting started guide for Community Access from identity-guides context.
- **Audience:** Teams learning Community implementation
- **Use when:** Learning Community basics

### Identity: Kubernetes Authentication

- **URL:** https://docs.tylerdev.io/identity/identity-guides/miscellaneous/k8s-authn/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to integrating Tyler Identity with Kubernetes authentication for pod-level identity and authorization.
- **Audience:** Platform engineers, DevOps teams
- **Use when:** Implementing Kubernetes identity integration

### Identity: Ops App Development Guide

- **URL:** https://docs.tylerdev.io/identity/identity-guides/dev-guides/ops-app/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Developer guide for building ops applications using Tyler Identity (for Tyler staff apps).
- **Audience:** Tyler internal developers building ops tools
- **Use when:** Developing internal ops applications with identity

---

## Platform Architecture

### Platform Architecture Overview

- **URL:** https://docs.tylerdev.io/platform-architecture/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** High-level overview of the Tyler Cloud Platform (TCP) architecture covering core services and integration patterns.
- **Audience:** Solution architects, platform teams
- **Use when:** Understanding TCP architecture and service organization

### Service Architecture Overview

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Overview of TCP service architecture patterns including eventing, webhooks, search, authorization, and community services.
- **Audience:** Platform engineers, architects
- **Use when:** Understanding internal service communication patterns

### TCP Eventing: Architecture

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/tcp-eventing/architecture/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Core internal eventing system architecture for TCP using SQS, EventBridge, and service subscribers for asynchronous event processing and eventual consistency.
- **Audience:** Platform service teams, backend developers
- **Use when:** Understanding or implementing internal event publishing/subscription

### TCP Eventing: Configuration

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/tcp-eventing/configuration/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Configuration guide for TCP eventing system setup and event routing.
- **Audience:** DevOps, platform ops
- **Use when:** Configuring event routing and subscribers

### TCP Eventing: Publishing Events

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/tcp-eventing/setting-up-a-publisher/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide for services to publish events into TCP eventing system including schema validation and error handling.
- **Audience:** Service team developers
- **Use when:** Implementing event publishing in a service

### TCP Eventing: Subscribing to Events

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/tcp-eventing/setting-up-a-subscriber/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide for building event subscribers in TCP including listener setup, message handling, and retry patterns.
- **Audience:** Service team developers
- **Use when:** Implementing event subscription in a service

### TCP Eventing: Failed Messages

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/tcp-eventing/failed-messages/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Documentation on failed message handling, dead-letter queues, and recovery mechanisms in TCP eventing.
- **Audience:** Platform engineers, troubleshooters
- **Use when:** Debugging event publishing failures or handling dead-letter messages

### TCP Eventing: Schema Validation

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/tcp-eventing/schema-validation/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Schema registry and validation system for TCP events ensuring contract compliance.
- **Audience:** Service architects, platform engineers
- **Use when:** Defining event schemas or understanding event validation

### Webhooks: Architecture

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/Webhooks/architecture/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Architecture for external webhook delivery system translating internal events to HTTPS outbound messages for external subscribers. Covers event relay service, message enrichment, and webhook handler.
- **Audience:** Platform engineers, external integration builders
- **Use when:** Understanding how TCP sends webhooks to external consumers

### Webhooks: Developing a Webhook

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/Webhooks/developing-a-webhook/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide for service teams to add new webhook message types and integrate with the webhook system.
- **Audience:** Service team developers adding webhook support
- **Use when:** Adding webhook events to a service

### Webhooks: Subscribing to Webhooks

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/Webhooks/subscribing-to-a-webhook/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide for external systems to subscribe to TCP webhooks including registration API, authentication methods (JWT, API Key), filtering, and payload handling.
- **Audience:** External integration partners, customer apps
- **Use when:** Building webhook consumers for TCP events

### Webhooks: Message Types

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/Webhooks/webhook-message-types/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Reference for all available webhook message types and their payloads.
- **Audience:** Webhook consumers, integration builders
- **Use when:** Finding available webhook events or understanding message structures

### Search: Architecture

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/Search/search-architecture/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** TCP search subsystem architecture using OpenSearch for full-text and field-based searching.
- **Audience:** Platform engineers implementing search
- **Use when:** Understanding TCP search infrastructure

### Search: Adding Search Endpoints

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/Search/adding-a-search-endpoint/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide for services to expose searchable endpoints.
- **Audience:** Service developers implementing search
- **Use when:** Adding search capability to a service

### Search: Adding Search Event Handlers

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/Search/adding-search-event-handler/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide for building event-driven index update handlers for search.
- **Audience:** Service developers
- **Use when:** Implementing event-driven search indexing

### Search: Adding Reindex Handlers

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/Search/adding-a-reindex-handler/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide for implementing reindex operations to rebuild search indices.
- **Audience:** Service developers, ops staff
- **Use when:** Implementing bulk reindexing

### Search: Entity Framework Interceptors

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/Search/adding-ef-interceptor/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to using Entity Framework interceptors to automatically trigger search index updates on data changes.
- **Audience:** .NET service developers
- **Use when:** Implementing database-driven search index updates

### Authorization: API Authorization Pattern

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/Authorization/api-authz/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** TCP authorization pattern for API-level permission checks using authorization decision logs and service accounts.
- **Audience:** Service developers implementing authorization
- **Use when:** Adding authorization checks to APIs

### Authorization: Adding Permissions

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/Authorization/adding-permissions/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide for services to define and add new permissions to TCP authorization system.
- **Audience:** Service architects, security teams
- **Use when:** Adding new permission types to a service

### Authorization: Registering Service Accounts

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/Authorization/registering-service-accounts/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide for registering service-to-service accounts for authorization and inter-service communication.
- **Audience:** Platform engineers, DevOps
- **Use when:** Setting up service account authentication

### Community Services: Architecture Overview

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/community-service-directory/architecture-overview/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Architecture for Community Services Directory (CSD) enabling app discovery, branding, and service registration for citizen-facing applications.
- **Audience:** Platform architects, product teams
- **Use when:** Understanding community services infrastructure

### Community Services: Introduction

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/community-service-directory/introduction/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Overview of Community Services Directory ecosystem including API, branding, event handlers, and frontend.
- **Audience:** Community app builders, platform teams
- **Use when:** Learning about community services

### Community Services: API Reference

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/community-service-directory/community-services-api/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** API reference for Community Services Directory including service registration and querying.
- **Audience:** Developers integrating with community services
- **Use when:** Using community services API

### Community Services: Branding

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/community-service-directory/community-services-branding/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to branding community services for consistent citizen experience.
- **Audience:** Product teams managing community app branding
- **Use when:** Setting up community service branding

### Community Services: Event Handler

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/community-service-directory/community-services-event-handler/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to event-driven updates for community services.
- **Audience:** Platform service developers
- **Use when:** Implementing event handling for services

### Community Services: Front End

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/community-service-directory/community-services-front-end/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Documentation on the Community Services front-end component and app launcher.
- **Audience:** UI/UX teams, citizen-facing app developers
- **Use when:** Understanding community service UX

### Community Services: Webhook Handler

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/community-service-directory/community-services-webhook-handler/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Documentation on webhook handling for community service events.
- **Audience:** External integration partners
- **Use when:** Integrating with community service webhooks

### Community Services: Monitoring and Alerts

- **URL:** https://docs.tylerdev.io/platform-architecture/service-architecture/community-service-directory/monitoring-and-alerts/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Monitoring, observability, and alerting setup for community services.
- **Audience:** DevOps, platform ops
- **Use when:** Setting up community service monitoring

---

## Product System Registration

### Product Registration Guide

- **URL:** https://docs.tylerdev.io/product-system-reg/guides/product-reg/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Comprehensive guide to product registration covering product definition from scratch, app types (Community, Workforce, Admin, Ops), authentication models (Workforce, Community, ExternalWorkforce, ExternalCommunity), app configuration, and GitOps automation through tcp-product-catalog repository.
- **Audience:** Product teams registering products, platform engineers
- **Use when:** Registering a new product or updating product registration

### Product Registration Checklist

- **URL:** https://docs.tylerdev.io/product-system-reg/integration-checklists/product-reg-checklist/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Pre-registration checklist ensuring product and application definitions are complete and validated.
- **Audience:** Product teams, product owners
- **Use when:** Planning product registration

### Customer Onboarding Checklist

- **URL:** https://docs.tylerdev.io/product-system-reg/integration-checklists/customer-onboarding-checklist/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Checklist for customer onboarding workflows including product provisioning and licensing.
- **Audience:** Customer success, onboarding teams
- **Use when:** Setting up customer onboarding process

### Product Licensing and Data Population

- **URL:** https://docs.tylerdev.io/product-system-reg/guides/product-licensing-data-population/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to populating product licensing data and provisioning customers with product instances.
- **Audience:** Ops teams, product provisioning engineers
- **Use when:** Setting up customer licensing and data population

### Importing Customers from CRM

- **URL:** https://docs.tylerdev.io/product-system-reg/guides/importing-customers-from-crm/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide for importing customer and organization data from CRM systems into product registry.
- **Audience:** Data engineers, ops teams
- **Use when:** Bulk importing customer data

### Product System Registration: Customer Onboarding Concepts

- **URL:** https://docs.tylerdev.io/product-system-reg/key-concepts/customer-onboarding/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Conceptual guide to customer onboarding workflows including provisioning and licensing.
- **Audience:** Product managers, ops teams
- **Use when:** Understanding onboarding concepts

### Product System Registration: Licensing Concepts

- **URL:** https://docs.tylerdev.io/product-system-reg/key-concepts/customer-onboarding/licensing-products/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to product licensing models and concepts.
- **Audience:** Product teams, business teams
- **Use when:** Understanding licensing models

### Product System Registration: Provisioning Concepts

- **URL:** https://docs.tylerdev.io/product-system-reg/key-concepts/customer-onboarding/provisioning-customers/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to customer provisioning workflows and concepts.
- **Audience:** Platform engineers, ops teams
- **Use when:** Understanding provisioning workflows

### Product System Registration Overview

- **URL:** https://docs.tylerdev.io/product-system-reg/key-concepts/overview/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Overview of product registration system and key concepts.
- **Audience:** Teams new to product registration
- **Use when:** Learning product registration basics

---

## App Guides

### App Guides Overview

- **URL:** https://docs.tylerdev.io/app-guides/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Overview of Tyler client applications including Admin Center, Ops Center, and community apps for citizen access.
- **Audience:** Product teams, end users
- **Use when:** Understanding available Tyler applications

### Admin Center Overview

- **URL:** https://docs.tylerdev.io/app-guides/client/admin-center/overview/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Overview of Admin Center application for IT/system/solution admins covering authentication setup, access control, user management, product management, logging, and branding.
- **Audience:** Admin center users, product admins
- **Use when:** Learning Admin Center capabilities

### Admin Center: Authentication Configuration

- **URL:** https://docs.tylerdev.io/app-guides/client/admin-center/authentication/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Step-by-step guide to configuring Identity Workforce authentication in Admin Center including domain setup, IdP federation (ADFS, Entra ID, Okta, Google), testing, and troubleshooting.
- **Audience:** Identity admins, IT staff
- **Use when:** Setting up Admin Center authentication

### Admin Center: Authorization Configuration

- **URL:** https://docs.tylerdev.io/app-guides/client/admin-center/authorization/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to configuring authorization and access control in Admin Center.
- **Audience:** Admin center admins
- **Use when:** Managing Admin Center access control

### Admin Center: User Management

- **URL:** https://docs.tylerdev.io/app-guides/client/admin-center/users/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to user record management in Admin Center.
- **Audience:** Admin center users
- **Use when:** Managing users in Admin Center

### Admin Center: Product Management

- **URL:** https://docs.tylerdev.io/app-guides/client/admin-center/products/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to product/solution management in Admin Center.
- **Audience:** Product admins
- **Use when:** Managing products in Admin Center

### Admin Center: Logging

- **URL:** https://docs.tylerdev.io/app-guides/client/admin-center/logging/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Documentation on activity logging and log data available in Admin Center.
- **Audience:** Compliance/audit teams, admins
- **Use when:** Reviewing Admin Center activity logs

### Admin Center: Support Access

- **URL:** https://docs.tylerdev.io/app-guides/client/admin-center/support/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to configuring Tyler support access and assistance settings.
- **Audience:** Admin center admins
- **Use when:** Managing Tyler support access

### Admin Center: Everything Reference

- **URL:** https://docs.tylerdev.io/app-guides/client/admin-center/_everything/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Comprehensive reference guide covering all Admin Center features and capabilities.
- **Audience:** Admin center power users
- **Use when:** Finding comprehensive Admin Center documentation

### Admin Center: Tyler Internal Getting Started

- **URL:** https://docs.tylerdev.io/app-guides/client/admin-center/tyler-internal/get-started/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Getting started guide for Tyler internal staff using Admin Center.
- **Audience:** Tyler employees
- **Use when:** Tyler staff learning Admin Center

### Admin Center: Sandbox Tenants

- **URL:** https://docs.tylerdev.io/app-guides/client/admin-center/tyler-internal/sandbox-tenants/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to sandbox/test tenants for internal Tyler development and testing.
- **Audience:** Tyler developers and QA
- **Use when:** Setting up test environments

### Client Profile Apps

- **URL:** https://docs.tylerdev.io/app-guides/client/workforce-profile/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Documentation for Workforce Profile app allowing employees to manage their profile and preferences.
- **Audience:** End users, admins
- **Use when:** Learning about workforce profile functionality

### Community Profile App

- **URL:** https://docs.tylerdev.io/app-guides/client/community-profile/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Documentation for Community Profile app for citizens/residents to manage their account.
- **Audience:** End users, community app admins
- **Use when:** Learning about community profile functionality

### Workspace Apps: App Directory

- **URL:** https://docs.tylerdev.io/app-guides/client/app-directory/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to App Directory workspace application for discovering and launching available applications.
- **Audience:** Workspace users
- **Use when:** Understanding App Directory

### Workspace Apps: Community Launcher

- **URL:** https://docs.tylerdev.io/app-guides/client/community-launcher/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Documentation for Community Launcher enabling citizen discovery and access to community services.
- **Audience:** Citizens, community app admins
- **Use when:** Understanding community app launcher

### Workspace Apps: CAPM (Community App Portfolio Manager)

- **URL:** https://docs.tylerdev.io/app-guides/client/capm/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Documentation for Community App Portfolio Manager for managing community application offerings.
- **Audience:** Community app operators
- **Use when:** Managing community app portfolio

### Workspace Apps: Community Services Directory (CSD) - Admin

- **URL:** https://docs.tylerdev.io/app-guides/client/csd/admin/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Admin guide for Community Services Directory allowing admins to manage community service offerings.
- **Audience:** Community service admins
- **Use when:** Managing community services as admin

### Workspace Apps: CSD - Services Directory

- **URL:** https://docs.tylerdev.io/app-guides/client/csd/services-directory/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** User guide for browsing and accessing community services through CSD.
- **Audience:** Citizens accessing community services
- **Use when:** Understanding community service discovery

### Workspace Apps: CSD - Services Manager

- **URL:** https://docs.tylerdev.io/app-guides/client/csd/services-manager/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Manager guide for managing community service configurations and access.
- **Audience:** Service managers
- **Use when:** Managing community services configuration

### Client Apps Overview

- **URL:** https://docs.tylerdev.io/app-guides/client/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Overview and index of all client-facing applications.
- **Audience:** End users, admins
- **Use when:** Finding documentation for client applications

---

## Status Page & SLA

### Status Page and SLA Key Concepts

- **URL:** https://docs.tylerdev.io/status-page-and-sla/key-concepts/status-page/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Documentation on status page concepts for communicating system health and incidents to customers.
- **Audience:** Ops teams, product teams
- **Use when:** Learning status page concepts

### SLA Tracking Integration Guide

- **URL:** https://docs.tylerdev.io/status-page-and-sla/guides/sla-tracking/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to implementing and tracking service level agreements including measurement and reporting.
- **Audience:** Ops teams, product teams
- **Use when:** Implementing SLA tracking

### Status Page Integration and Usage Guide

- **URL:** https://docs.tylerdev.io/status-page-and-sla/guides/status-page-integration-and-usage/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to integrating status page system and communicating incidents to customers.
- **Audience:** Ops teams, incident commanders
- **Use when:** Setting up status page or reporting incidents

### Status Page Integration Checklist

- **URL:** https://docs.tylerdev.io/status-page-and-sla/integration-checklists/status-page-checklist/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Checklist for status page integration readiness.
- **Audience:** Product teams, ops teams
- **Use when:** Planning status page implementation

### SLA Tracking Checklist

- **URL:** https://docs.tylerdev.io/status-page-and-sla/integration-checklists/sla-tracking-checklist/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Checklist for SLA tracking implementation readiness.
- **Audience:** Product teams, ops teams
- **Use when:** Planning SLA tracking implementation

---

## DevOps and Infrastructure

### DevOps: Continuous Integration - GitHub Actions

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/continuous-integration/github-action-samples/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Collection of GitHub Actions samples and best practices for CI/CD pipeline automation.
- **Audience:** DevOps engineers, platform teams
- **Use when:** Implementing GitHub Actions workflows

### DevOps: Continuous Integration - Artifactory Migration

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/continuous-integration/github-artifactory-migration/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to migrating artifacts to Artifactory for central artifact management.
- **Audience:** DevOps engineers
- **Use when:** Implementing artifact repository strategy

### DevOps: Datadog - Getting Started

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/datadog/getting-started/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Getting started guide for Datadog monitoring and observability platform integration.
- **Audience:** DevOps, platform ops
- **Use when:** Setting up Datadog for the first time

### DevOps: Datadog - Setup

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/datadog/setup/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Detailed setup guide for Datadog agents and integrations.
- **Audience:** DevOps engineers
- **Use when:** Configuring Datadog infrastructure

### DevOps: Datadog - Dashboards

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/datadog/dashboards/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to creating and managing Datadog dashboards for monitoring.
- **Audience:** DevOps, operations teams
- **Use when:** Building monitoring dashboards

### DevOps: Datadog - Tagging

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/datadog/tagging/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Best practices for Datadog tagging strategy for resource organization and filtering.
- **Audience:** DevOps teams
- **Use when:** Planning Datadog tagging scheme

### DevOps: Harness - Overview

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/harness/overview/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Overview of Harness deployment platform integration with Tyler.
- **Audience:** DevOps, platform teams
- **Use when:** Understanding Harness in Tyler context

### DevOps: Harness - Onboarding Guide

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/harness/onboarding-guide/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Step-by-step onboarding guide for teams adopting Harness.
- **Audience:** DevOps teams, platform engineers
- **Use when:** Getting started with Harness

### DevOps: Harness - Governance Standards

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/harness/governance-standard/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Governance and policy standards for Harness deployments.
- **Audience:** Platform architects, compliance teams
- **Use when:** Establishing Harness governance policies

### DevOps: Database Migration - DynamoDB

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/db-migration/dynamodb-migration/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide for migrating databases to DynamoDB including schema mapping and data migration.
- **Audience:** Data engineers, DevOps
- **Use when:** Planning DynamoDB migration

### DevOps: Database Migration - RDS/Aurora

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/db-migration/aurora.md
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide for migrating databases to AWS Aurora.
- **Audience:** Data engineers, DevOps
- **Use when:** Planning Aurora migration

### DevOps: Infrastructure as Code - Overview

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/infrastructure-as-code/overview/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Overview of Infrastructure as Code (IaC) practices using Terraform for Tyler infrastructure.
- **Audience:** DevOps, infrastructure engineers
- **Use when:** Understanding TCP IaC strategy

### DevOps: Terraform - Terraform Cloud

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/infrastructure-as-code/terraform/terraform-cloud/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to using Terraform Cloud for remote state management and collaboration.
- **Audience:** DevOps engineers
- **Use when:** Setting up Terraform Cloud workflows

### DevOps: Terraform - Dynamic AWS Auth

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/infrastructure-as-code/terraform/configure-dynamic-aws-auth/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to configuring dynamic AWS authentication for Terraform.
- **Audience:** DevOps engineers
- **Use when:** Securing Terraform AWS credentials

### DevOps: Terraform - Workspace Manager (Part 1)

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/infrastructure-as-code/terraform/workspace-manager-p1/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to Terraform workspace management strategies (part 1).
- **Audience:** DevOps engineers, platform architects
- **Use when:** Organizing Terraform workspaces

### DevOps: Terraform - Workspace Manager (Part 2)

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/infrastructure-as-code/terraform/workspace-manager-p2/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Advanced Terraform workspace management strategies (part 2).
- **Audience:** Advanced DevOps engineers
- **Use when:** Scaling Terraform workspace strategy

### DevOps: Disaster Recovery - General Guidelines

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/disaster-recovery/guide/general-guidelines/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** General disaster recovery guidelines and principles for AWS infrastructure.
- **Audience:** Architects, DevOps teams
- **Use when:** Planning disaster recovery strategy

### DevOps: Disaster Recovery - Design Recovery Process

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/disaster-recovery/guide/designing-recovery-process/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to designing business continuity and disaster recovery processes.
- **Audience:** Architects, business continuity teams
- **Use when:** Creating disaster recovery plan

### DevOps: Disaster Recovery - RDS Recovery

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/disaster-recovery/guide/rds-recovery/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** RDS-specific disaster recovery and restore procedures.
- **Audience:** Database teams, DevOps
- **Use when:** Recovering RDS instances

### DevOps: Regional Failover - Decision Tree

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/disaster-recovery/regional-failover/dr-decision-tree/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Decision tree for determining regional failover procedures and timing.
- **Audience:** Incident commanders, ops teams
- **Use when:** Planning or executing regional failover

### DevOps: Regional Failover - Recovery Runbook

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/disaster-recovery/regional-failover/recovery-runbook/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Runbook for executing regional failover and recovery procedures.
- **Audience:** Incident commanders, DevOps teams
- **Use when:** Executing regional failover

### DevOps: Regional Failover - Comprehensive Runbook

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/disaster-recovery/regional-failover/runbook/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Comprehensive runbook with detailed steps for regional failover and recovery.
- **Audience:** Incident response teams, operations
- **Use when:** Executing regional failover with detailed procedures

### DevOps: Incident Management - CorpDev P1 Response

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/runbooks/01-incident-management/corpdev-p1-response/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Runbook for handling Priority 1 incidents in CorpDev infrastructure.
- **Audience:** Incident commanders, on-call teams
- **Use when:** Responding to critical production incidents

### DevOps: AWS SSO - CLI Login Setup

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/runbooks/02-aws-sso/aws-cli-login-setup/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to configuring AWS CLI with SSO authentication.
- **Audience:** Developers, DevOps engineers
- **Use when:** Setting up AWS CLI SSO access

### DevOps: AWS SSO - EKS Kubeconfig Setup

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/runbooks/02-aws-sso/eks-kubeconfig-setup/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to configuring kubectl access to EKS clusters via AWS SSO.
- **Audience:** Kubernetes engineers, DevOps
- **Use when:** Setting up kubectl access to EKS

### DevOps: Kubernetes - Upgrade Runbook

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/runbooks/03-kubernetes/upgrade/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Step-by-step runbook for upgrading EKS clusters including prerequisites, backup procedures, and version-specific steps.
- **Audience:** Kubernetes operations, DevOps teams
- **Use when:** Performing EKS cluster upgrades

### DevOps: PagerDuty - Setup Guide

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/runbooks/04-pagerduty/setup/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to configuring PagerDuty for incident alerting and on-call management.
- **Audience:** DevOps, incident management
- **Use when:** Setting up PagerDuty integration

### DevOps: Tool Provisioning - GitHub

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/runbooks/dev-tool-provisioning-runbooks/github/provisioning/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Runbook for provisioning GitHub accounts and access.
- **Audience:** IT/Access management
- **Use when:** Onboarding new GitHub users

### DevOps: Tool Provisioning - Artifactory

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/runbooks/dev-tool-provisioning-runbooks/artifactory/provisioning/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Runbook for provisioning Artifactory access.
- **Audience:** IT/Access management
- **Use when:** Setting up Artifactory access

### DevOps: Tool Provisioning - Aqua

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/runbooks/dev-tool-provisioning-runbooks/aqua/provisioning/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Runbook for provisioning Aqua security scanning tool access.
- **Audience:** Security teams, DevOps
- **Use when:** Setting up Aqua access

### DevOps: Tool Provisioning - Docker Hub

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/runbooks/dev-tool-provisioning-runbooks/docker-hub/create-user/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Runbook for creating Docker Hub accounts.
- **Audience:** DevOps, container teams
- **Use when:** Setting up Docker Hub access

### DevOps: Tool Provisioning - PrivX

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/runbooks/dev-tool-provisioning-runbooks/privx/user-management/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Runbook for managing PrivX user access and bastion host provisioning.
- **Audience:** IT security, access management
- **Use when:** Managing PrivX bastion access

### DevOps: AWS Infrastructure - Overview

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Overview of TCP AWS infrastructure including account structure and shared resources.
- **Audience:** Architects, DevOps teams
- **Use when:** Understanding TCP AWS architecture

### DevOps: AWS Shared VPC

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/02-shared-vpc/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Documentation on shared VPC architecture and networking.
- **Audience:** Network engineers, DevOps
- **Use when:** Understanding or configuring VPC

### DevOps: AWS Karpenter Node Consolidation

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/04-karpenter-node-conslidate-scheulde/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to Karpenter auto-scaling and node consolidation for Kubernetes.
- **Audience:** Kubernetes ops, cost optimization teams
- **Use when:** Optimizing Kubernetes cluster costs

### DevOps: Terraform - Creating Workspaces

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/corpdev-tf-docs/creating-a-workspace/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to creating Terraform workspaces for AWS infrastructure.
- **Audience:** DevOps, infrastructure engineers
- **Use when:** Creating new Terraform workspaces

### DevOps: Terraform - DynamoDB Configuration

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/corpdev-tf-docs/dynamo/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to managing DynamoDB through Terraform.
- **Audience:** DevOps engineers
- **Use when:** Creating or modifying DynamoDB tables via Terraform

### DevOps: Terraform - RDS Configuration

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/corpdev-tf-docs/rds/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to managing RDS databases through Terraform.
- **Audience:** Database teams, DevOps
- **Use when:** Creating or modifying RDS instances via Terraform

### DevOps: Terraform - S3 Configuration

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/corpdev-tf-docs/s3/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to managing S3 buckets through Terraform.
- **Audience:** DevOps engineers, data teams
- **Use when:** Creating or configuring S3 buckets via Terraform

### DevOps: Terraform - SNS/SQS Configuration

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/corpdev-tf-docs/sns-sqs/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to managing SNS/SQS messaging services through Terraform.
- **Audience:** DevOps, event-driven architecture teams
- **Use when:** Creating messaging infrastructure via Terraform

### DevOps: Terraform - Secrets Management

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/corpdev-tf-docs/secrets-management/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to managing secrets in Terraform-deployed infrastructure.
- **Audience:** DevOps, security teams
- **Use when:** Configuring secret management in Terraform

### DevOps: Terraform - Git2Consul Integration

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/corpdev-tf-docs/git2consul/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to Git2Consul integration for GitOps-based configuration management.
- **Audience:** DevOps, platform teams
- **Use when:** Setting up Git-driven configuration management

### DevOps: Terraform - Harness Configuration

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/corpdev-tf-docs/harness/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to Harness deployment platform configuration via Terraform.
- **Audience:** DevOps engineers
- **Use when:** Configuring Harness through Terraform

### DevOps: Terraform - General Guidelines

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/corpdev-tf-docs/general-guidelines/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Best practices and general guidelines for Terraform usage in TCP.
- **Audience:** DevOps engineers, platform teams
- **Use when:** Learning Terraform best practices for TCP

### DevOps: AWS Infrastructure - FAQ

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/faq/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** FAQ for AWS infrastructure topics and common questions.
- **Audience:** DevOps teams, infrastructure engineers
- **Use when:** Finding quick answers about AWS infrastructure

### DevOps: Application Migration Guide

- **URL:** https://docs.tylerdev.io/platform-architecture/dev-ops/application-migration/migrating/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide for migrating applications to Tyler Cloud Platform infrastructure.
- **Audience:** Application teams, architects
- **Use when:** Planning application migration to TCP

### Security: RDS IAM Authentication

- **URL:** https://docs.tylerdev.io/platform-architecture/security/RDS-IAM-Auth/rds-iam-auth/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to using IAM authentication for RDS database access instead of passwords.
- **Audience:** Security teams, database engineers
- **Use when:** Implementing IAM-based database access

### Security: Vulnerability Scanning

- **URL:** https://docs.tylerdev.io/platform-architecture/security/vulnerability-scanning/vulnerability-scanning/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to container image and dependency vulnerability scanning.
- **Audience:** Security teams, DevOps
- **Use when:** Implementing security scanning

### Security: WAF Rules

- **URL:** https://docs.tylerdev.io/platform-architecture/security/waf-rules/waf-rules/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Guide to Web Application Firewall (WAF) rule configuration and management.
- **Audience:** Security teams, DevOps
- **Use when:** Configuring WAF rules

### Security: Akeyless Design Proposal

- **URL:** https://docs.tylerdev.io/platform-architecture/security/akeyless-design-proposal/design-proposal/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Design proposal and documentation for Akeyless secrets management platform integration.
- **Audience:** Security architects, platform teams
- **Use when:** Evaluating or planning Akeyless integration

---

## Support

### Identity Support

- **URL:** https://docs.tylerdev.io/support/support-channels/identity-support/
- **Source system:** Docusaurus (Tyler Blueprint, `docs.tylerdev.io`)
- **What it is:** Support resources and channels for identity-related issues and questions.
- **Audience:** Teams using Tyler Identity, support staff
- **Use when:** Seeking identity support or escalation channels

---

## Notes for the chatbot

- This is a **growing list** — new entries land here over time. Do not assume the catalog is exhaustive; if a user asks for a link that isn't listed, say so and offer to help find it.
- **Always hand back the verbatim URL** — that's the whole point of this file.
- **Match the audience tag before recommending.** A "Project Manager / Deployment / Implementation / Support" link is not necessarily appropriate for a product-engineering or sales user — surface the audience explicitly in the answer.
- **When an entry has a distilled companion file** (`Conf-*.txt`, `Docusaurus-*.txt`, `Training-*.txt`) in this folder or in `Knowledge-SupportAccessCenter/`, mention both: the companion file for a fast answer here in the chatbot, the URL for the authoritative live source.
- **Confluence URLs under `tylertech.atlassian.net/wiki/spaces/TTI/` are internal Tyler-only.** Mention that to external readers; they will not resolve outside Tyler systems.
- **SharePoint URLs under `tylertech-my.sharepoint.com/personal/vijay_venkataraman/...`** are also internal Tyler-only and may require sign-in to the user's Tyler tenant.
- **The Confluence "Adding external users to Entra ID" page (`386635379`) is internal-only guidance for Tyler staff** — do not share the URL directly with customers. Use it to coach the customer's IT admin instead.
- **The Gateway test password is NOT in this corpus** — it lives only on the source Confluence page (`386600150`, *Test credentials* section, Tyler SSO required). `Conf-GatewayOperationalTesting.md` gives the two test account emails and points at that page for the password. Never guess or reconstruct a password; hand out the link and note it shouldn't be copied into tickets, chat, or code.
- **The training page is effective only through H1 2026** — content will be revised with new Identity features later in 2026. If a user references something that seems contradicted by newer guidance, prefer the newer source and flag the divergence.
- **The Blueprint Docusaurus catalog (`docs.tylerdev.io`)** is a **live, evolving documentation site**. Some specific URLs may change as Docusaurus is reorganized — if a URL 404s, the parent section's index page is usually still live. Prefer the Blueprint live source when a user is asking "where can I learn more?" about a topic that has a Blueprint page, even if we have a distilled Knowledge file — the file is a fast answer, the Blueprint URL is the always-current source.
- **The Blueprint catalog has dozens of Identity, Platform Architecture, DevOps, and App Guides entries** aimed at **product engineering teams and platform engineers**, NOT customers. Surface that audience tag explicitly. Do not point Tyler customers at Blueprint pages.
- **The Blueprint repo path-to-URL mapping is direct:** `docs/<path>/<page>.md` (or `.mdx`) → `https://docs.tylerdev.io/<path>/<page>/`. If a user gives you a Blueprint URL and asks "what does this cover?", you can reason about it from the path even before the live page loads.
