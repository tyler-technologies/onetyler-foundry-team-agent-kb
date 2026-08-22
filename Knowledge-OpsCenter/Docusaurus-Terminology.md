# Tyler Cloud Platform — Terminology Glossary

Source: Docusaurus — *CorpDev Blueprint, Get Started > Terminology* (`docs/get-started/terminology/terminology.md`)
Domain: Ops Center (terminology is foundational across the One Tyler Ecosystem and used throughout Ops Center, Admin Center, Identity Workforce, Community Access, and Tyler CRM)
Audience: Tyler product, deployment, implementation, support, identity, and devops staff who need a precise definition for any Tyler Cloud Platform (TCP) term.

This document defines the canonical vocabulary used across the One Tyler Ecosystem. Each entry is self-contained so a retriever can surface it independently. Terms are clustered by theme; an **A–Z lookup** at the bottom resolves any alphabetical search. When a definition references another term, treat that as a cross-reference the chatbot can follow.

---

## How to use this glossary

- The chatbot's job is to **resolve a term to its canonical definition first**, then answer the user. If the user uses a near-synonym (e.g. "tenant" vs "workspace"), surface both and explain the distinction.
- Many term *pairs* in this glossary exist specifically to disambiguate things people confuse: Authentication vs Authorization, Licensing vs Availability, Customer/Client vs Organization, Tenant vs Workspace, Environment vs Workspace, Deployment vs Release, Workforce Direct vs Managed vs Delegated, etc. When a user asks about either side, give the contrast.
- Cluster headings (e.g. *Cloud paradigms*, *Identity & Authentication*) exist to help a human reader and to keep related terms in retrieved chunks together. They are not part of any term's name.

---

## Cluster: Tyler ecosystem & platform

### Tyler Cloud Platform (TCP) (a.k.a. "Portico")

Tyler's PaaS offering for Tyler Product teams to rapidly build cloud-native applications using shared constructs and services while adhering to Tyler's branding and security standards. "Portico" is the old brand name; TCP's core software/tools are hosted on the `tylerportico.com` domain, but in customer communications the term **Portico is deprecated** — use "Tyler Cloud Platform."

### One Tyler Ecosystem

A foundational framework to centralize discovery and navigation of all Tyler solutions. Key pillars:

- Use of Tyler Identity cloud solutions for user store and authentication (direct, or indirect via federations).
- Centralized registration, licensing, and availability of products.
- Centralized management of Organizations, Products, and Users.
- Centralized discovery and navigation patterns.
- Centralized Ops applications (Tyler implementer/support concerns) and a centralized Admin Center (customer-facing concerns).
- Extensions to product-specific applications from Ops or Admin Center.

### Ops Center

CorpDev-managed One Tyler Ecosystem tool for centralized discovery and navigation to Tyler Ops applications. Used to create organizations and workspaces, license products to organizations, and activate products on workspaces. See *Tyler Ops User* and *Admin Center*.

### Admin Center

CorpDev-managed tool for centralized administrative experiences used by **customer** IT or solutions administrators. Counterpart to Ops Center (which is for Tyler staff). See *Admin Apps* and *Organization Admin*.

### Control plane

Technical term (especially in SaaS) for the management of core constructs and shared services through tools and APIs. All administrative applications used by Tyler staff and client administrators fall under the Control plane. **Ops Center** and **Admin Center** are control-plane apps that manage Organizations, Workspaces, Licensing, Availability, etc. Contrast with *Application plane*.

### Application plane

Technical term (especially in SaaS) for the hosting of applications and services that serve regular non-administrative functionality to end users (typically with varying levels of authorization). Contrast with *Control plane*.

### Single Pane of Glass (SPOG)

A dashboard or platform that combines data from multiple sources into a single, unified view. Often used as a synonym for "dashboard."

---

## Cluster: Cloud paradigms

### Cloud

A paradigm in which computing infrastructure and resources are hosted on the internet by a 3rd party and available for rapid provisioning and use. The three cloud offering types:

- **Infrastructure-as-a-Service (IaaS)** — Virtualized hardware resources (e.g. AWS EC2 compute instances).
- **Platform-as-a-Service (PaaS)** — A development platform with ready-to-consume constructs and services; abstracts away infrastructure management. **TCP is an example of a PaaS.**
- **Software-as-a-Service (SaaS)** — Full software offerings consumed directly without infrastructure or maintenance concerns. Tyler's Virtual Court is a SaaS offering. **Tyler aims to be a full-fledged SaaS company by 2030.**

### Cloud-native

A paradigm where a single instance and version of an application is consumed by multiple customers, with only a virtual partition of configuration and data (e.g. Facebook, Gmail). Generally serverless, 24/7, no downtime or regular OS/DB maintenance. Customers have no direct data access, so privacy and regulatory compliance burdens shift to the software development teams.

### Server-based architecture

A product or application built to run on a traditional server (physical or virtual computer) with an independent OS, dedicated database, etc. Each layer is maintained independently → high overall maintenance cost. Contrast with *Serverless architecture*.

### Serverless architecture

Architecture where traditional servers are not used. Self-contained light-weight packages ("containers") with a minimalist OS plus application code run on standardized virtual infrastructure without typical CPU/RAM server boundaries. Copies of the package can be dynamically added to meet load. Requires specific application paradigms.

### CI/CD (Continuous Integration / Continuous Deployment)

Cloud-native practice of continuous software development and deployment to release small, low-risk changes frequently — replacing the legacy practice of large, high-risk releases on a fixed schedule. Release management is controlled post-deployment via *Feature flags*.

### Deployment

The engineering activity of delivering changes to a product on its infrastructure.

- **Legacy:** per-workspace activity — every workspace gets its own copy on its own OS + database.
- **Cloud-native:** promotion of code through a deployment pipeline across multiple cloud instances, affecting all customers simultaneously; orchestrated by an integrated devops team.
- **Deployment ≠ Release.** Deployment pushes code into production; *Release management* controls when it becomes available to customers.

### Release management

A product-management (business) function for exposing deployed features. In many cases deployment and release coincide. In cloud-native, release is a distinct step from deployment and is managed via *Feature flags*. Can include documentation updates, marketing/sales initiatives, pre-release evaluation, early-adopters programs, selective/progressive rollouts.

### Feature flags

Tags on features or changes that control their release post deployment. Can be a product-team-controlled process (e.g. Harness Feature Flags) or simply config options exposed to end users. Allow tagged features to be exposed case-by-case or in limited rollouts. Once widely available, flags must be cleaned up before they become unmanageable.

### DevOps

In a cloud-native context, the entire organization (development through support) operates as one integrated team with only a few specialists. Engineers rotate through the full SDLC.

### Implementation

Configuration of the solution/product at a baseline "default" state of operation. Further customization is delivered as *Professional services*.

### Professional services

Tailoring of a default product implementation to meet a customer's business processes and goals. May include business-process review and changes outside software. Some complex solutions include professional services as a required part of implementation.

### Knowledge Base

A KB is a centralized collection of information used by customers, employees, or technicians to find answers. Includes FAQs, manuals, troubleshooting guides, runbooks.

### Runbook

A guide outlining steps to complete a task or procedure. Used in IT to document operating and managing applications, services, and infrastructure. Can be manual, semi-automated, or fully automated.

---

## Cluster: Customer, organization, CRM

### Customer or Client

Any entity with a business relationship with Tyler. Avoid "client" in technical contexts — "Identity Client" is a separate technical term. **Customer/Client ≠ Organization:** Customer/Client refers to the contractual or business relationship; **Organization** is a deployment entity (gets a copy of software). For complex customer entities (states, large cities), multiple Organizations may exist for them by department or business unit.

### Organization

An entity provisioned a distinct copy of a Tyler product and intended to be its sole or primary administrator — regardless of who signed the contract or who manages the email domain. For complex entities (states, large cities), sub-entities (departments, business units) can each be an independent Organization in the One Tyler Ecosystem with their own copy of Tyler software.

Every Organization has a unique identifier sourced from CRM and imported into Ops Center; this becomes the reference for all products within the One Tyler Ecosystem.

### Organization Admin

A customer or Tyler user with administrative privileges for an Organization. Typically the customer IT admin, solutions manager, or other personnel responsible for managing users in the org (issuing/revoking credentials, email accounts, etc.). The Admin Center is built around these roles.

### Tyler Ops User

Any Tyler staff who deploys, implements, manages, or supports an installation for a customer. In integrated devops teams, Tyler personnel may rotate through all of these roles. Product dev teams may also be Ops users during early-release phases or for small teams. **Ops Center is designed for these roles.**

### Back-office user

A customer end user who performs back-office functions. Includes full-time/part-time employees and contractors performing those functions.

### Public user

A user of a Tyler solution who is **not** a back-office user. Includes customer's residents, job applicants, ex-employees, vendors, small businesses, etc. Community apps integrated with **Community Access** serve these user types for authentication.

### Vendor

In Tyler's business relationships: an officially recognized entity providing software or services to Tyler or its customers via a formal agreement. In Tyler's software: a Vendor is a public customer/user of Tyler's customers.

### Customer Relationship Management (CRM) (a.k.a. "Tyler CRM")

Tyler's instance of Microsoft Dynamics CRM, used to track Leads, Prospects, Customers, ex-Customers, Contracts, etc. Tyler CRM informs the One Tyler Ecosystem about Customers and the Products they are entitled to. Important CRM-specific sub-terms below.

#### CRM > Active customer

In CRM, an active customer is presented as an **'account'** record. Accounts are typically created from sales leads and progressively promoted to prospect → active customer. **Not all accounts are active customers.** Accounts also exist at all levels of a legal entity as separate records, connected via *Hierarchy*. An active customer account record is one where ALL the following hold:

1. Status on the Account record is **'Active'**.
2. The Account record has at least one **Active customer product item**.
3. It is a **Direct** or **Indirect** customer.
4. **Support-only customer = No.**

#### CRM > Company Name

The legal name of the customer, on the Account record.

#### CRM > Customer Identifier

An alphanumeric identifier auto-generated by CRM for every active customer record using Company Name, State, and Country (for non-US/Canada). Generated with **Business Use = Default** and expected to remain unchanged once generated.

**Organizations in the One Tyler Ecosystem can only exist for CRM customer (account) records that have this identifier generated** — which means they must be an active customer.

#### CRM > Support-only customer

An attribute on an account record. When set to **'Yes'**, the account is excluded from sales queries. Used for Tyler-internal-use account records without affecting sales queries.

#### CRM > Product Suite

A sales categorization grouping related products within a larger functional domain or Tyler division.

#### CRM > Product Module

A sales sub-categorization under Product Suites. Roughly corresponds to a product sold independently. Each Product Module typically has its own *SKU*.

#### CRM > Active customer product items

The SKUs listed for a given customer/account that entitle them to the corresponding products from a licensing standpoint.

#### CRM > Customer Relationship Type

Attribute on the account record indicating the primary contractual relationship to Tyler. Significant values:

- **Direct** — Customers who sign contracts with Tyler and are eligible to get Tyler software/services.
- **Indirect** — Customers eligible for Tyler software/services through a contract signed by a Direct customer. E.g. for states or large cities, departments/business units that administer Tyler software independently of the parent.
- **Former** — Customers who no longer have active contracts with Tyler.

#### CRM > Hierarchy

An overlay construct connecting related customer/account records to reflect hierarchical (legal) relations. E.g. departments and business units under departments tied back to the parent entity.

#### CRM > Case

Tracks activity to be performed against an account record. Typically used for customer support tickets or deployment/implementation tasks to be executed by Tyler operations teams.

### Sales Sheet

A catalog of SKUs used by marketing and sales to educate customers on software/service offerings. Can also be used to track actual sales.

### Stock Keeping Unit (SKU)

In software, an identifier assigned to software licenses, products, services, bundles, solutions — reflecting sales and marketing strategies. SKUs often change to reflect market conditions (repackaging the same products/services differently).

---

## Cluster: Workspace, environment, tenant, system

### Workspace

A consistent, **logical** construct that groups Tyler solutions regardless of each solution's hosting environment. On TCP, all of a customer's workspaces (prod, test, train, staging, etc.) typically share the same environment and software version with data segregated virtually. For other products, the same workspaces may be hosted in entirely different environments using different versions. From a customer's perspective, the group of solutions in "production" relate to one another even if they sit in different hosting environments. In the One Tyler Ecosystem, a workspace is **1:1 with a *Tenant***.

### Environment

The infrastructure on which a product is hosted for a specific organizational use case. **Environment ≠ Workspace.** Environment usually points to specific infrastructure that allows data segregation. Workspace is a logical construct describing different business uses of data segregation without concern for the underlying infrastructure or how segregation is accomplished.

### Tenant

A technical construct that virtually segregates data and configuration in a system designed to share infrastructure. Typically relates to **Workspaces** for most Tyler products. ("Workspace" is the functional term; "Tenant" is the technical term.)

### System

Any physical or logical infrastructure on which products and dependent services run. Impacts can typically be mapped directly or indirectly to one or more Organizations, Workspaces, and Products.

---

## Cluster: Products, licensing, availability

### Product

A licensing entity, primarily organized around administrative/operational (not sales/marketing) concerns. Contains one or more applications or services in a specific functional domain. A product may be packaged and sold in multiple SKUs.

- **Product Modules** — Sub-licensing entities representing specific sub-domains of functionality within a product. E.g. GL, Payroll, AP, AR within a typical ERP.
- **Product Tiers** — Sub-licensing entities reflecting increased breadth and sophistication of functionality within a domain/sub-domain. E.g. Basic, Standard, Professional, Enterprise.

### Licensing

In TCP's SaaS Control Plane: the **eligibility** of an organization to consume a given product. Licensing is done **against an Organization**. Contrast with *Availability*. **A product must be both licensed AND available to be usable.**

### Availability

In TCP's SaaS Control Plane: the **provisioning** of a product instance against a specific workspace. May also provision server-based software solutions. Done in Ops Center.

**Important pairing:** Licensing happens at the **Org** level; Availability happens at the **Workspace** level. Both required for a working product.

---

## Cluster: Applications & UI patterns

### Application

A functional entity (typically with a UI; can also include services) that serves functionality to end users. In the One Tyler Ecosystem, application types are:

- **Workforce app** — Surfaces functionality to customer back-office users related to daily business functions.
- **Admin app** — Surfaces rarely-used setup/configuration or user-authorization functionality within a product; used by customer IT or solutions administrators.
- **Community app** — Surfaces functionality for customer public users (residents, vendors, ex-employees, job applicants, etc.).
- **Ops app** — For Tyler staff only. Customers have no access. Typically used by ops and support teams.
- **APIs and Services** — Applications that don't serve a UI directly but offer functionality to other applications or services.

### Admin Apps

A construct within the Admin Center that presents links to administrative applications for products licensed to an organization. Facilitates a centralized administrative experience for customer Workforce Admins.

### App Launcher (a.k.a. 9-box)

The 9-dot icon in the application (omni) bar of a Tyler application that switches contexts to a new application. **Not** for navigation *within* an application — that's the job of a navigation bar/rail.

### Workforce App Directory

A directory listing of all Workforce applications a user can discover and navigate to.

### Community Services Directory (CSD)

A public portal for an organization's workspace presenting a directory containing all community services offered by the organization for their public users.

### Branding

A common set of UI guidelines customers can customize: logos, naming, color schema (including a common CSS), fonts, design platform, design philosophy, etc., that all customer- or public-facing applications adhere to. Includes any workspace-specific customizable branding services.

### Separation of concerns

A product-design paradigm in which functionality targeted for different personas is segregated into different independent applications — contrary to the legacy paradigm of building monolithic applications and using authorization to gate features. The One Tyler application types **Ops / Workforce / Admin / Community** reflect this paradigm.

---

## Cluster: Identity, authentication, authorization

### Authentication

The "login" / "sign-on" process that validates a user owns the user id they claim. Establishes **"who"** the user is. Confers **no** product or app permissions. Tyler's cloud authentication solutions include **Identity Workforce** and **Community Access**. Contrast with *Authorization*.

### Authorization

The permissions a user has in the context of specific product(s) and application(s). Establishes **"what"** the user can do. Generally a product concern — product design controls which features are subject to which authorization levels for the personas the product targets. Contrast with *Authentication*.

### Identity Provider (IdP)

A software solution that handles an Organization's authentication needs for users and services by providing a user store. Modern IdPs use industry standards, are hosted on the internet, integrate with 3rd-party solutions, and provide SSO. They also let the organization manage security configuration (MFA, password policies, etc.) to enforce a minimum auth-security baseline.

### Single Sign-On (SSO)

Allows an Organization's users to authenticate into any software solution using one set of credentials in a single IdP. Avoids forcing users to remember multiple usernames/passwords (and insecure workarounds like sticky notes). Also lets the org disable a former employee's account centrally and revoke access to all software.

### Multi-factor / 2-Factor Authentication (MFA, 2FA)

IdP configuration requiring users to authenticate with more than just a password. "Factors" include passwords, SMS, authenticator apps, email, phone calls, etc.

- **2FA:** exactly two factors required (one usually the password).
- **MFA:** multiple factors allowed; usually only 2 of the multiple are required (one usually the password).

### Identity Workforce

Organization-managed cloud identity offering for **back-office users**. Enables SSO across all participating Tyler products and solutions. Tyler offers three options:

- **Workforce Direct** — For customers with a public-facing IdP to federate to, where the customer owns all back-office-user authentication responsibilities and their security. **Tyler strongly favors this option by default.**
- **Workforce Managed** — Customers get a Tyler-managed back-office user store (currently powered by Okta). For customers who require this for regulatory or business reasons.
- **Workforce Delegated** — Special Workforce Direct variant where the org delegates identity and user setup to another org (the "Super"). The orgs depending on the Super are "Sub" orgs. Only the Super sets up federations and adds users; Sub orgs can only add users that already exist in the Super. Both Super and Sub orgs can have independent solutions and grant access to them. Deleting a user in the Super removes them from all Sub orgs; deleting in a Sub only affects that Sub. (Note: terminology.md treats Workforce Delegated separately from Workforce Direct/Managed; on Ops Center the org's Identity Tier is one of these three.)

### Workforce User

A user who authenticates through the **Identity Workforce** solution configured for a particular organization. Has an associated *Workforce Profile* capturing extended user attributes in the org context.

### Workforce Profile

A profile associated with an Identity Workforce user in the context of an organization. Stores back-office-user-specific settings.

### Community Access

**Tyler-managed** cloud identity offering for public users. Enables SSO across all organizations so public users can seamlessly access services or transact. Public users can create a username/password or use a social login. Organizations get support tools to manage support for their public users.

### Community User

A user who authenticates through Community Access. Independent of any organization. Has a corresponding *Community Profile* storing extended user attributes (e.g. MFA preferences).

### Community Profile

User profile associated with the Community Access solution. Manages preferences across organizations (e.g. payment methods).

### Zero-trust computing paradigm

Authorization model requiring all users to be **explicitly** granted permissions to all functionality — no implied access.

---

## Cluster: Services & APIs

### API (Application Programmatic Interface)

A service with a publicly accessible interface that external products can consume to access specific functionality. APIs typically abstract direct access to data and underlying data processing, increasing security by only allowing authorized access.

### Service

In **technical** discussions: an API or micro-service that serves functionality. In **business** discussions about software: a functionality offered by an external party without the consumer needing to set up or maintain systems.

- **Micro-service** — A very compact service designed to serve a narrow function. Compact code base + efficient infrastructure use. In cloud-native, micro-services can be designed for high scalability.

---

## A–Z lookup index

- **Active customer (CRM)** → Cluster: Customer, organization, CRM
- **Active customer product items (CRM)** → Cluster: Customer, organization, CRM
- **Admin app / Admin Apps / Admin Center** → Cluster: Tyler ecosystem & platform; Cluster: Applications & UI patterns
- **API / APIs and Services** → Cluster: Services & APIs; Cluster: Applications & UI patterns
- **App Launcher (9-box)** → Cluster: Applications & UI patterns
- **Application / Application plane** → Cluster: Applications & UI patterns; Cluster: Tyler ecosystem & platform
- **Authentication / Authorization** → Cluster: Identity, authentication, authorization
- **Availability** → Cluster: Products, licensing, availability
- **Back-office user** → Cluster: Customer, organization, CRM
- **Branding** → Cluster: Applications & UI patterns
- **Case (CRM)** → Cluster: Customer, organization, CRM
- **CI/CD** → Cluster: Cloud paradigms
- **Cloud / Cloud-native** → Cluster: Cloud paradigms
- **Community Access / Community Profile / Community User / Community Services Directory** → Cluster: Identity, authentication, authorization; Cluster: Applications & UI patterns
- **Community app** → Cluster: Applications & UI patterns
- **Company Name (CRM)** → Cluster: Customer, organization, CRM
- **Control plane** → Cluster: Tyler ecosystem & platform
- **CRM / Tyler CRM (and all CRM sub-terms)** → Cluster: Customer, organization, CRM
- **Customer or Client** → Cluster: Customer, organization, CRM
- **Customer Identifier (CRM)** → Cluster: Customer, organization, CRM
- **Customer Relationship Type (CRM): Direct / Indirect / Former** → Cluster: Customer, organization, CRM
- **Deployment** → Cluster: Cloud paradigms
- **DevOps** → Cluster: Cloud paradigms
- **Environment** → Cluster: Workspace, environment, tenant, system
- **Feature flags** → Cluster: Cloud paradigms
- **Hierarchy (CRM)** → Cluster: Customer, organization, CRM
- **IaaS / PaaS / SaaS** → Cluster: Cloud paradigms
- **Identity Provider (IdP)** → Cluster: Identity, authentication, authorization
- **Identity Workforce / Workforce Direct / Workforce Managed / Workforce Delegated** → Cluster: Identity, authentication, authorization
- **Implementation** → Cluster: Cloud paradigms
- **Knowledge Base** → Cluster: Cloud paradigms
- **Licensing** → Cluster: Products, licensing, availability
- **MFA / 2FA** → Cluster: Identity, authentication, authorization
- **Micro-service** → Cluster: Services & APIs
- **One Tyler Ecosystem** → Cluster: Tyler ecosystem & platform
- **Ops app** → Cluster: Applications & UI patterns
- **Ops Center** → Cluster: Tyler ecosystem & platform
- **Organization / Organization Admin** → Cluster: Customer, organization, CRM
- **Portico (deprecated; see TCP)** → Cluster: Tyler ecosystem & platform
- **Product / Product Modules / Product Tiers** → Cluster: Products, licensing, availability
- **Product Suite / Product Module (CRM)** → Cluster: Customer, organization, CRM
- **Professional services** → Cluster: Cloud paradigms
- **Public user** → Cluster: Customer, organization, CRM
- **Release management** → Cluster: Cloud paradigms
- **Runbook** → Cluster: Cloud paradigms
- **Sales Sheet** → Cluster: Customer, organization, CRM
- **Separation of concerns** → Cluster: Applications & UI patterns
- **Server-based architecture / Serverless architecture** → Cluster: Cloud paradigms
- **Service** → Cluster: Services & APIs
- **Single Pane of Glass (SPOG)** → Cluster: Tyler ecosystem & platform
- **Single Sign-On (SSO)** → Cluster: Identity, authentication, authorization
- **SKU (Stock Keeping Unit)** → Cluster: Customer, organization, CRM
- **Support-only customer (CRM)** → Cluster: Customer, organization, CRM
- **System** → Cluster: Workspace, environment, tenant, system
- **TCP (Tyler Cloud Platform)** → Cluster: Tyler ecosystem & platform
- **Tenant** → Cluster: Workspace, environment, tenant, system
- **Tyler CRM** → Cluster: Customer, organization, CRM
- **Tyler Ops User** → Cluster: Customer, organization, CRM
- **Vendor** → Cluster: Customer, organization, CRM
- **Workforce app / Workforce App Directory / Workforce Profile / Workforce User** → Cluster: Applications & UI patterns; Cluster: Identity, authentication, authorization
- **Workspace** → Cluster: Workspace, environment, tenant, system
- **Zero-trust computing paradigm** → Cluster: Identity, authentication, authorization

---

## Notes for the chatbot

- **Disambiguation pairs the chatbot should always reach for** (when the user touches one, surface the other):
  - Authentication ↔ Authorization (who vs what)
  - Licensing ↔ Availability (org-level vs workspace-level; BOTH required)
  - Customer/Client ↔ Organization (business relationship vs deployment entity)
  - Tenant ↔ Workspace (technical vs functional/logical, 1:1)
  - Environment ↔ Workspace (infra vs logical)
  - Deployment ↔ Release management (engineering vs business; can differ in cloud-native)
  - Workforce Direct ↔ Workforce Managed ↔ Workforce Delegated
  - Client (business) ↔ Identity Client (technical) — different things; warn if user mixes them
  - Server-based ↔ Serverless
  - Cloud ↔ Cloud-native
- **Portico** is deprecated in customer communications. If a user asks about "Portico," respond using "Tyler Cloud Platform" and note the `tylerportico.com` domain origin.
- "Org Admin" is a customer-IT/solutions role, but **Tyler staff can also hold Org Admin permissions** in a client capacity — don't assume Org Admin always means customer.
- For **CRM-related questions** (e.g. "what makes a customer record valid?"), always reach for the *Active customer* definition's four-point checklist plus the *Customer Identifier* requirement (Business Use = Default). Both are required for Org creation in Ops Center.
- The **Identity Workforce** product tier of an Organization (Direct/Managed/Delegated) **cannot be changed after the organization is created** — recreation is needed. The chatbot should flag this when the user asks about conversion. (See the Ops Center docs for the conversion ticket exception covering UNINITIATED Workforce Direct → Workforce Managed.)
