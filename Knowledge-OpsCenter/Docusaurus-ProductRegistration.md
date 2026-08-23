# Product Registration — Concepts, Guidance, and Example

Source: Docusaurus — *OneTyler Blueprint, Product/System Registration > Key Concepts > Registered Product* (`docs/product-system-reg/key-concepts/registered-product/**`)
Domain: Ops Center (Product Registration drives what appears in **Ops Center > Product Registry** and downstream in Admin Center, Workforce App Directory, and Community Services Directory.)
Audience: Tyler Product Managers and Project Managers preparing a product for cloud release. Engineering owns the technical registration steps; PMs own the product details, application categorization, and contact info gathered here.

This document covers what product registration is, why it matters (where the data surfaces across the One Tyler Ecosystem), the four application types in a registration, the PM/PjM preparation checklist, FAQs, and a worked example (fictional product: **Cemetery Manager**).

**Status note:** The source introduction page is flagged as *UNDER CONSTRUCTION*. The content below reflects what is currently published.

**Companion documents in this same Knowledge folder:**
- `Docusaurus-Terminology.md` — see *Application* (Workforce/Admin/Community/Ops/APIs), *Product*, *Workforce App Directory*, *Community Services Directory*, *Admin Apps*, *SKU* (Product ≠ SKU).
- `Docusaurus-OpsCenter.md` — see **Product Registry** for how the registration surfaces inside Ops Center (Overview, Ops Apps tab, Registration Details, JSON tab).
- `Knowledge-Shared/Conf-OneTylerTickets.md` — for permissions related to using product-registration features in Ops Center (e.g., Bulk Licensing).

**Companion technical documentation (engineering follow-up):** `/blueprints/product-reg` on the same Docusaurus site.

---

## How to use this guide (quick decision guide)

| If the user wants to… | Go to section |
|---|---|
| Understand what a "registered product" is (vs SKU) | **What is a product (in registration terms)?** / FAQ: Product vs SKU |
| Know the four application types and where each surfaces | **Application types** |
| Plan a registration for a new product | **PM/PjM preparation checklist** |
| See a worked example | **Worked example — Cemetery Manager** |
| Find the engineering side of registration | **Technical documentation** |
| Get help / get a review | **Questions, reviews, contact** |
| Know where Ops Apps can appear in Ops Center | FAQ: **Where can Ops Apps appear?** |
| Handle a single web destination across all orgs (Recording Access / Vendor Hub pattern) | FAQ: **Single web destination across all orgs** |
| Pre-populate product groups in a registration | FAQ: **Pre-define product groups** |

---

## What is product registration?

Once a product and its applications have been designed and developed, the next step **prior to publishing on the cloud is to register the product**. Registration captures the product details, application list, navigation, and contact info that surfaces across Ops Center, Admin Center, Workforce App Directory, and the Community Services Directory.

A registration answers questions like:

- What do I need to do to surface Administrative apps?
- What do I need to do to surface apps in the **Workforce App Directory**?
- What do I need to do to surface apps in the **Community App Directory** / Community Services Directory?
- What do I need to do to surface services in the **Community Services Directory**?
- What do I need to do to surface apps in the **Ops Center**?
- What do I need to do to register my team's contact information?

---

## What is a product (in registration terms)?

At a high level, a product represents a **licensable solution** with these characteristics:

- A collection of **applications** belonging to a specific business/functional domain.
- **Common admin interface(s)** and function(s) managing those apps.
- Applications **deployed/provisioned as a "single unit"**.

**Important framing:** "Product" in registration is an **operational and administrative perspective**, NOT a marketing, sales, or contractual perspective.

**Rule:** There should be **only one registration per product**. Multiple-registration cases are rare. If you feel your situation warrants splitting, **reach out to OneTyler via the Product Registration Community Teams Channel** (link below) before doing it.

---

## What is the Product Registry?

The **Product Registry** is the registry of all Tyler products. Each registration contains basic product details, applications, contact info, etc. The Product Registry is **maintained by OneTyler**, with each product team responsible for contributing their own registration details.

In Ops Center, the Product Registry is reachable from the dashboard's **Products** link. See `Docusaurus-OpsCenter.md` → *Product Registry* for the tabs (Overview, Ops Apps, Registration details with Applications / Navigation Links / JSON sub-tabs, and Bulk Licensing).

---

## Application types

The One Tyler Ecosystem recognizes **four application types** in a product registration. Each corresponds to a distinct end-user persona and a distinct discovery surface:

| Type | Persona | Where it surfaces |
|---|---|---|
| **Ops** | Tyler staff only (deployment, implementation, support, ancillary product operations) | **Ops Center** (Product Registry > Ops App; Organization context > Licensed apps > Ops Apps; Workspace context > Manage workspaces > Ops Apps) |
| **Workforce** | Customer back-office persona (routine back-office functions like invoices, inspections, etc.) | **Workforce App Directory** |
| **Admin** | Customer IT / solutions admin persona (setup, configuration, user authorization) | **Admin Center > Admin apps** |
| **Community** | Public user persona (residents, small businesses, vendors, ex-employees, applicants) — may optionally provide a guest experience without login | **Community Services Directory** |

### Entry-point conventions

- **Most products have one main entry point per persona.** For complex flagship products with several large modules, each module may have its own entry point.
- For **simple products**, expect one entry point per persona; that entry-point app should:
  - **Adopt the same name and icon as the product itself** for easy discoverability.
  - **Tweak description and help text** to reflect the application's purpose, using Tyler standards (e.g., Forge Punctuation Style guide).

For complex needs (e.g., multiple entry points per app type), discuss with OneTyler via the Product Registration Community Teams Channel.

### Ops App specifics

The Tyler staff persona uses **Ops Center** to discover the Ops App entry point you register. Matching the Ops App title to the product title helps discovery. Complex products may surface multiple Ops App entry points.

### Workforce App specifics

A Workforce App serves **routine back-office functions** (e.g., generating invoices, managing inspections). Most products have a primary entry point — typically a dashboard — through which all functions are accessed. **Match the Workforce entry-point title to the product title** for simple products. Complex products may register multiple entry points (e.g., a separate Supervisor app with limited access).

### Admin App specifics

An Admin App serves **setup/configuration and user authorization** functionality used only by customer IT / solutions admins. **Ideally a single entry point** per product, which then surfaces in **Admin Center > Admin apps**, giving customer admins a centralized administrative experience. Complex products may register multiple Admin apps if distinct administrative experiences per module are required.

### Community App specifics

A Community App serves **public users** — residents, small businesses, vendors, ex-employees, applicants, etc. — and may provide an optional guest experience without login. Public users discover Community apps as **services** they can access, so the **Title and Description should have service-level leanings**. Discuss titles/descriptions of Community apps with OneTyler via the Product Registration Community Teams Channel for guidance or approval.

---

## PM/PjM preparation checklist

Product Management team members should work through these steps before handing off to engineering for the technical registration. The output of these steps is the information engineering needs.

| # | Step | Details | Impact |
|---|---|---|---|
| 1 | **Application review and categorization** | Categorize functionality across the four application types (Ops, Workforce, Admin, Community). Most Tyler solutions have a main entry point for each applicable type. Complex products may surface module-level entry points. | Forms the basis for discoverability of Workforce/Admin/Ops/Community experiences. |
| 2 | **Assemble Product Details** | If you already have a Product Marketing-approved name, description, about, icon, and contact info, skip to step 7. Otherwise complete steps 3–6. Registration requires: Product Name, Description, About, Icon, Contact Info. | Used across Tyler applications and tools. |
| 3 | **Product Name** | Collaborate with Product Marketing/Marketing for an approved product name. Reference Brand Standards (Inside Tyler). | Surfaces wherever product listings appear, including **Ops Center Product Registry** and **Admin Center Manage Products**. |
| 4 | **Product Description** | Short description (1–2 sentences) approved by Product Marketing/Marketing. | Surfaces e.g. on **Admin Center Manage Products**. |
| 5 | **Product About & Help Text** | Longer description (~a paragraph) approved by Product Marketing/Marketing. | Not currently displayed (reserved). |
| 6 | **Product Icon** | Select from the **Forge Icon Library** (Standard, Extended, Custom). If a custom icon is required, file a ticket first to have it added. | Surfaces in **Workforce App Directory** and **Community Services Directory** cards. |
| 7 | **Product Contact Information** | Strongly suggested: (a) a **public community MS Teams channel** for others to post questions/get assistance, and (b) a **distribution list** for product dev/ops/support. Create private channels in your MS Team and use the channel email addresses. Alternatively, store contact info on Confluence pages and link to them. **AVOID registering individual contact info** — it goes stale quickly and is hard to maintain. | Allows others across Tyler to reach your team via Teams channel or email. |
| 8 | **Registration review** | Once collected, review with stakeholders and OneTyler for feedback. | Avoids corrections later. |
| 9 | **Prep for registration** | Hand off the collected info to product engineering and point them to the technical documentation. | Engineering can complete the technical registration steps. |

---

## Worked example — Cemetery Manager (fictional)

This worked example shows how to apply the guidance for a fictional product called **Cemetery Manager**.

### Product overview

Cemetery Manager is a cloud-based, multi-tenant product. Its applications:

- **Cemetery Manager app** (main Workforce app) — plot management, burial scheduling, cemetery maintenance/ops. Used by most employees regularly.
- **Supervisor app** (Workforce, limited access) — supervisors approve schedules, work orders, and other supervisory functions. Used by managers and key employees.
- **Administration app** (Admin app) — setup, configuration, and integration settings. Used occasionally by org IT / site admin.
- **Plot Viewer app** (Community app) — linked from the org's website for finding a specific plot's location.
- **Ops app** — lets Tyler employees manage and monitor services, availability, etc.

Two Workforce apps were registered (Cemetery Manager + Supervisor) because supervisory functions are pulled into a separate app with limited access rights.

### Applying the PM/PjM checklist

| Step | Outcome |
|---|---|
| **Application review and categorization** | List of apps and their types (see overview above). |
| **Assemble Product Details** | Identified need for Product Name, Description, About, Icon and per-app Name/Description/Help/Icon. |
| **Product Name** | **"Cemetery Manager"**. App names derived: Ops "Cemetery Manager", Community "Cemetery Plot Viewer", Workforce-CM "Cemetery Manager", Workforce-CMS "Cemetery Manager Supervisor", Admin-CM "Cemetery Manager Admin". |
| **Product Description** | **"Cemetery Manager allows management of plots, owners, and customers"**. Per-app descriptions tailored (e.g., Workforce-CMS: "Cemetery Manager Supervisor provides approval functions to managers"). |
| **Product About & Help Text** | About: *"Cemetery Manager allows management of plots using advanced geolocation tools, keeps track of plot ownership, manages customers, and integrates with Enterprise ERP and Payments for fast invoicing and payments collections."* Help text tailored per app. |
| **Product Icon** | Selected **`hospital_marker`** (Forge **Extended**). Per-app icons: Ops/Workforce-CM/Admin-CM `hospital_marker` (ext); Community `person_pin_circle` (std); Workforce-CMS `approval` (std). Per-app Admin `admin_panel_settings` (std) in the Admin row. |
| **Product Contact Information** | Development: MS Teams community channel link. Operations: distribution-list email. Support: `cemetery-manager-support@tylertech.com`. |
| **Registration review** | Reviewed with stakeholders + OneTyler; feedback applied. |
| **Prep for registration** | Handed off to engineering. |

### Registration approach (per entity)

| Entity | Type | Surfaces in | Key attributes |
|---|---|---|---|
| **Cemetery Manager Product** | — | Ops Center > Product Registry; Admin Center > Manage products | Name, Description, About, Contact info (Dev/Ops/Support) |
| **Cemetery Manager** | Workforce App | Workforce App Directory | Name=Cemetery Manager; Desc="Management of plots, owners, and customers"; Icon=hospital_marker (extended) |
| **Cemetery Manager Supervisor** | Workforce App | Workforce App Directory | Name=Cemetery Manager Supervisor; Desc="…provides approval functions to managers"; Icon=approval (standard) |
| **Cemetery Manager Admin** | Admin App | Admin Center | Name=Cemetery Manager Admin; Desc="Configure and manage users"; Icon=hospital_marker (extended) |
| **Cemetery Plot Viewer** | Community App | Community Services Directory | Name="View cemetery plots"; Desc="View details and availability of plots"; Icon=hospital_marker (extended) |
| **Cemetery Manager Ops** | Ops App | Ops Center | Name="Cemetery Manager Operations"; Desc="Implementation and support tools"; Icon=hospital_marker (extended) |

### Post-registration UI impacts

Once registered, the product surfaces in these places:

**Ops Center**
- **Product Registry > Product details:**
  - **Overview tab** — Contact info displayed (Development: MS Teams channel link; Operations: distribution-list mailto; Support: distribution-list mailto).
  - **Ops apps tab** — "Cemetery Manager Ops" link.
  - **Registration details tab** — Ops/Workforce/Admin applications listed.
- **Licensing option** — Ops Center > Organizations > Licensed Products > **+ Add a product** > "Cemetery Manager". Licenses the product to the Organization.
- **Activation option** — Ops Center > Organizations > Manage workspaces > Select workspace > toggle against "Cemetery Manager". Provisions a copy of the software for the workspace.

**Admin Center** (after the product is licensed to the org and activated on at least one workspace)
- **Admin Center > Products:**
  - Name "Cemetery Manager", Description, and the **Applications list** (per Workspace the product is activated on): Cemetery Manager [Workforce], Cemetery Manager Supervisor [Workforce], Cemetery Manager Admin [Workforce], Cemetery Plot Viewer [Community].
- **Admin Center > Admin apps** — Cemetery Manager → "Cemetery Manager Admin" links (one per workspace with **copy to clipboard** and **open in new tab** options).

**Workforce App Directory** (after license + activation)
- Card for Cemetery Manager.
- Card for Cemetery Manager Supervisor.
- Card for Cemetery Manager Admin (badged **[Admin]**).
- (Future) Cards show their icon.

**Community Services Directory (public)** (after license + activation)
- Featured Services card: "View cemetery plots" — "View details and availability of plots" with the registered icon.

---

## FAQs

### How does a Product differ from a SKU?

A **Product** represents what is *installed/provisioned*. A **SKU** (in Tyler CRM) represents what a customer has *subscribed/licensed*. In many cases, product ↔ SKU is 1:1 with matching names. In other cases:

- A SKU may **contain multiple products** in a bundle.
- Multiple SKUs may **include the same product** with different pricing options.

**Example:** *Content Manager* is a product included with **Enterprise Appraisal and Tax** (reflected under a single SKU). It is also sold as a separate line item for **Enterprise ERP** (separate SKUs for Enterprise ERP and Content Manager). What is deployed/provisioned in either case is the **same Content Manager product**.

> SKUs are tailored to market and sales objectives; products are built around development and deployment objectives.

### What is the Product Registry?

See *What is the Product Registry?* above. (Repeating for FAQ retrieval.)

### Where can Ops Apps appear in the Ops Center?

Ops Apps surface in OneTyler's Ops Center in **three context locations** (clicking the link takes the user to the externally hosted Ops App):

- **Product context:** Ops Center > Product Registry > Ops App — for generalized access to the product's settings and functionality.
- **Organization context:** Ops Center > Organization > Details > Licensed apps > Ops Apps — for org-wide settings and functionality.
- **Workspace context:** Ops Center > Organization > Details > Manage workspaces > Ops Apps — for workspace-level settings and functionality.

### I need to host a single web destination across all organizations. What should I do?

Some products (e.g., **Recording Access**, **AP Automation Vendor Hub**) use a special construct: a **single Tyler-branded web portal** used by public users across all organizations. Public users select the organization within the portal (or use a system that aliases directly/indirectly to an org).

These are **domain-specific Tyler-branded products** that are **not designed to be licensable on regular customer organizations**, and therefore contain **no Workforce or Admin apps**. Registration guidance for these products is **case-by-case** — reach out to OneTyler via the Product Registration Community Teams Channel.

### My implementation team routinely creates product groups manually. How can I minimize their work?

For Cloud Platform products that have adopted the **TCP group access management** construct (where an application access key is assigned to a user through a group to gain initial access), you can **pre-define standard group constructs** in the product registration so they don't have to be created manually each time. See the technical Product Registration docs for how.

---

## Technical documentation

For engineering-side guidance on actually performing the registration, see the technical doc:

- `/blueprints/product-reg` on the OneTyler Blueprint Docusaurus site.

---

## Questions, reviews, contact

Reach out to OneTyler via the **Product Registration Community Teams Channel** for:

- Questions about registration.
- Requesting a review of your planned registration **before** registering your product.
- Complex needs — multiple entry points per app type, split-registration scenarios, single-web-destination patterns, etc.

(Link in the Docusaurus source page; internal MS Teams channel.)

---

## Notes for the chatbot

- **Always reach for the "Product ≠ SKU" framing** when users describe registration as a sales/licensing concern. Registration is operational/administrative; SKUs are sales/marketing.
- **There should be only one registration per product.** When users ask about splitting, direct them to the Product Registration Community Teams Channel — don't endorse splitting yourself.
- The **four application types** (Ops / Workforce / Admin / Community) map 1:1 to four discovery surfaces (Ops Center / Workforce App Directory / Admin Center > Admin apps / Community Services Directory). Always pair the type with its surface in answers.
- **For simple products, app name + icon should match the product** — call this out as a discoverability best practice.
- **Avoid individual contacts in registration** — distribution lists and Teams channel emails are preferred because they don't rot.
- **For Community apps**, descriptions should be **service-flavored** (what the public user gets), not back-office-flavored.
- The introduction page is flagged "under construction" — content may expand. If a user asks about something that seems missing, suggest the Product Registration Community Teams Channel.
- **The Bulk Licensing feature** in Ops Center (see `Docusaurus-OpsCenter.md`) is the tool to apply a registered product across many existing orgs/workspaces at once — useful after a new product registration goes live.
