# Product & System Registration — Registered Products, Licensing, Customer Onboarding

Source: Tyler Blueprint Docusaurus — `https://docs.tylerdev.io/product-system-reg/`
Domain: Blueprint General — Tyler Cloud Platform / Blueprint docs not served by a specialized Foundry agent
Audience: Product engineering teams, product managers, and CorpDev staff responsible for registering Tyler products on the TCP platform and onboarding customers.

**Companion documents:**
- `_START_HERE.md` — routing guide for this corpus
- `Docusaurus-PlatformOverview.md` — TCP architecture, organizations, workspaces
- `Docusaurus-OpsApps.md` — Ops Center application details
- `Docusaurus-ClientApps.md` — Workforce/Community/Admin app patterns
- `Docusaurus-CloudPlatformAPI.md` — API patterns, identity tokens
- `Docusaurus-DevOps.md` — Harness pipelines, GitHub Actions, secrets
- `Docusaurus-Security.md` — security requirements for deployments

> **Related Ops Center corpus:** The Ops Center Foundry agent covers the Ops Center UI for registration management (viewing, licensing, activating products through the Ops Center interface). This file covers the *engineering* side — how to build and submit a product registration definition. For Ops Center UI guidance, see: https://docs.tylerdev.io/app-guides/ops/ops-center/overview/

---

## How to use this guide

| User intent | Go to section |
|---|---|
| Understand what a "registered product" is | [What Is a Registered Product](#what-is-a-registered-product) |
| Understand the four app types (Ops, Workforce, Admin, Community) | [Application Types](#application-types) |
| Create a product registration YAML from scratch | [Product Registration Guide](#product-registration-guide) |
| Understand RegistrationId rules and constraints | [Product and App RegistrationId Rules](#product-and-app-registrationid-rules) |
| Configure app launcher links (Workforce/Community) | [App Launcher Configurations](#app-launcher-configurations) |
| Configure Admin Center admin links | [App Administration Configurations](#app-administration-configurations) |
| Configure Ops Center product/org/workspace links | [Ops Center Configurations](#ops-center-configurations) |
| Set up URL token replacement in configuration URLs | [URL Token Replacement](#url-token-replacement) |
| Configure default product groups (auto-created on licensing) | [Default Product Groups](#default-product-groups) |
| Store secrets for URL resolver APIs | [URL Mapping API Secret Setup](#url-mapping-api-secret-setup) |
| Use the CorpDev-managed default gateway secret | [New Default Gateway ClientId/Secrets](#new-default-gateway-clientidsecrets) |
| Verify registration in Ops Center | [Using Ops Center to Verify Registration](#using-ops-center-to-verify-registration) |
| Understand product vs. SKU distinction | [FAQ: Product vs. SKU](#faqs) |
| See a worked end-to-end example (Cemetery Manager) | [Example Case Study](#example-case-study--cemetery-manager) |
| Understand PM steps to prepare for registration | [PM Guidelines for Registration Preparation](#pm-guidelines-for-registration-preparation) |
| Customer onboarding or licensing a product to a customer | [Customer Onboarding](#customer-onboarding) |

---

## Glossary

| Term | Meaning |
|---|---|
| Product Registry | The central registry of all Tyler products on TCP, maintained by CorpDev, with each product team owning their entry |
| `RegistrationId` | Unique, immutable identifier for a product or app; changing it creates a new entity |
| AuthenticationModel | How users authenticate to an app — `Workforce`, `Community`, `ExternalWorkforce`, or `ExternalCommunity` |
| AccessModel | Authorization model — `Group` (TCP user groups), `Everyone` (no restriction), `SystemAdmin` (Tyler-only) |
| tcp-product-catalog | GitHub repo containing YAML product registration files; GitOps-driven; https://github.com/tyler-technologies/tcp-product-catalog |
| AppLauncherConfiguration | Link surfaced in the Workforce or Community launcher (9-box) |
| ExternalLauncherConfiguration | Launcher link for `ExternalWorkforce`/`ExternalCommunity` apps; resolved dynamically via URL resolver API |
| AppAdministrationConfiguration | Link surfaced in the Admin Center admin-links page |
| ProfileAdministrationConfiguration | Link surfaced in the Admin Center user profile side-nav |
| OpsCenterConfiguration | Link surfaced in Ops Center (product, org, or workspace context) |
| Default Product Group | A named group auto-created when a product is licensed to an org; predefines standard access groups |
| LicensedByDefault | If `true`, product is automatically licensed to every org and cannot be unlicensed |
| TCPCI / TCPQA / TCPPROD | TCP environments: development (`tcpci.com`), QA (`tcpqa.com`), production (`tylerportico.com`) |
| URL resolver / mapping API | An endpoint CorpDev POSTs workspace context to; returns the actual launcher URL for ExternalWorkforce/Community apps |
| CCF token | Client credentials flow JWT token for authenticating API-to-API calls within TCP |

---

## What Is a Registered Product

A **registered product** is the operational/administrative definition of a Tyler product on the Tyler Cloud Platform. It is:

- A collection of applications belonging to a specific business/functional domain
- Defined from a deployment and administration perspective (not a marketing or sales perspective)
- The entity that is **licensed** to organizations and **activated** on workspaces

**One registration per product is the standard.** Splitting a product into multiple registrations is rare and requires CorpDev approval. Contact the [Product Registration Community Teams Channel](https://teams.microsoft.com/l/channel/19%3AoVLpzEarOxFx-RwQc70RhkOA0xXbUS6R52LrTWKhIMQ1%40thread.tacv2/Product%20Registration%20Community?groupId=d9db441d-35fa-433c-8fe0-ff7fe5825d3c&tenantId=7cc5f0f9-ee5b-4106-a62d-1b9f7be46118&ngc=true&allowXTenantAccess=true) if you believe you need it.

The **Product Registry** is the registry of all Tyler products. It is maintained by CorpDev with each product team contributing their own registration details.

---

## Application Types

Four application types are recognized in a product registration. Each maps to a distinct user persona and UX surface.

| App type | Persona | Discovered in | Key rule |
|---|---|---|---|
| **Ops** | Tyler staff — deployment, implementation, support | Ops Center | Exclusive to Tyler employees; can appear in product, org, or workspace context |
| **Workforce** | Customer back-office employees | Workforce App Directory; 9-box (omnibar) | Most products have one primary entry point |
| **Admin** | Customer IT / solutions admin | Admin Center > Admin Apps | Ideally one entry point per product; surfaced per-workspace |
| **Community** | Public users (residents, small businesses, vendors, etc.) | Community Services Directory | Title and description should have service-level leanings; optional guest experience |

**General expectations:**
- Most products expose a main entry point for each applicable persona type.
- For simple products, each app should match the product name and icon for easy discoverability.
- For complex/flagship products, module-level entry points may be appropriate — consult CorpDev.

### Ops App surfaces in Ops Center

Ops Apps appear in one of three Ops Center locations depending on context:
- **Product context**: Ops Center > Product Registry > Ops App (generalized product settings)
- **Organization context**: Ops Center > Organization > Details > Licensed Apps > Ops Apps (org-wide settings)
- **Workspace context**: Ops Center > Organization > Details > Manage Workspaces > Ops Apps (workspace-level settings)

---

## PM Guidelines for Registration Preparation

Product Management team members should complete these steps before handing off to engineering.

| Step | Action | Details |
|---|---|---|
| 1. App categorization | Categorize all product functionality into the 4 app types | Identify Ops, Workforce, Admin, Community apps and their entry points |
| 2. Product Name | Collaborate with Product Marketing for approved name | Used in Ops Center Product Registry, Admin Center Manage Products |
| 3. Product Description | Short description (1–2 sentences) | Used in Admin Center Manage Products |
| 4. Product About & Help Text | Longer description (up to a paragraph) | Not currently displayed publicly |
| 5. Product Icon | Select a Forge icon (Standard, Extended, or Custom) | Used in Workforce App Directory and Community Services Directory cards |
| 6. Product Contact Information | Set up MS Teams channels and/or distribution list emails | Use team channels and DLs — avoid individual contact info (goes stale) |
| 7. Registration review | Review with stakeholders and CorpDev before registering | Prevents costly corrections post-registration |
| 8. Hand off to engineering | Provide all collected data to engineers with a pointer to the technical docs | Engineering completes the remaining YAML-based steps |

**Contact information guidance:** Register a public MS Teams community channel and/or email distribution lists for Development, Operations, and Support types. Avoid individual person emails.

---

## Product Registration Guide

Product registration uses a GitOps approach via the **tcp-product-catalog** GitHub repository:
https://github.com/tyler-technologies/tcp-product-catalog

Definitions live as YAML files (`{registration_id}.yaml`) in `/product-catalogs/{environment}/`. Changes submitted via PR to the master branch are automatically deployed by built-in Harness automation.

**TCP environment → domain mapping:**
- TCPCI (dev): `tcpci.com`
- TCPQA: `tcpqa.com`
- TCPPROD: `tylerportico.com`

**For initial product registration setup:** Check the Coda doc to see if a generated definition already exists:
- Coda: https://coda.io/d/Gateway-Rollout_dKV_6fSnfBc/0-Start-Here_suxF9#_lukrO
- Contact Vijay Venkataraman and Product Owners for guidance if the product is not listed.

**Access requests (GitHub, Coda, Harness):** https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386600308/Tyler+Cloud+Platform+TCP+Ops+Center+Related+Tickets+and+Permissions

---

### Product and App RegistrationId Rules

**Prerequisites:** Read carefully before creating any registration.

- `RegistrationId` is a **permanent, immutable identifier** for a product or app.
- Changing the `RegistrationId` of a product treats it as a **new product** — the old one is not removed automatically.
- Changing the `RegistrationId` of an app **deletes the old app and creates a new one**.
- `RegistrationId` must be **unique** across all products (for products) and across all apps (for apps).
- If `RegistrationId` is not provided for an app, the app title is used as the ID.
- During the initial data migration, `RegistrationId` values were set to product/app names.

---

### Product Fields

| Field | Required | Description |
|---|---|---|
| `registrationId` | Yes | Unique, immutable identifier |
| `name` | Yes | Display name |
| `description` | Yes | Short description |
| `tylerComponentsWebIconName` | Yes | Forge icon name for the product header |
| `LicensedByDefault` | No | If `true`, auto-licensed to all orgs; cannot be unlicensed |
| `productContacts` | No | Array of `{type, description, link}` — types: `Development`, `Operations`, `Support` |
| `defaultProductGroups` | No | Groups auto-created when the product is licensed (see [Default Product Groups](#default-product-groups)) |
| `apps` | Yes | Array of app definitions |

**Product contacts example:**
```yaml
productContacts:
  - link: https://teams.microsoft.com/l/channel/...
    description: Teams channel
    type: Development
  - link: mailto:support@tylertech.com
    description: Product Support Manager Email
    type: Support
  - link: mailto:operations@tylertech.com
    description: Product Operations Manager Email
    type: Operations
```

---

### App Fields

| Field | Required | Description |
|---|---|---|
| `registrationId` | No (defaults to title) | Unique, immutable identifier |
| `title` | Yes | Display name |
| `description` | Yes | Short description |
| `authenticationModel` | Yes | `Workforce`, `Community`, `ExternalWorkforce`, or `ExternalCommunity` |
| `accessModel` | Yes | `Group`, `Everyone`, or `SystemAdmin` |
| `path` | Required for `Workforce`/`Community`; ignored for `External*` | Base path; used to construct Okta redirect URLs |
| `domains` | No | Explicit domain list; if omitted, uses environment default |

**AuthenticationModel rules:**
- `Workforce` — uses enterprise (customer org) identity; formerly "Enterprise"; can have `AppLauncherConfigurations`
- `Community` — uses Tyler citizen identity; formerly "Citizen"; can have `AppLauncherConfigurations`
- `ExternalWorkforce` — off-platform (on-prem or non-TCP) Workforce app; cannot have `AppLauncherConfigurations`; can have `ExternalLauncherConfigurations`
- `ExternalCommunity` — off-platform Community app; can only have `ExternalLauncherConfigurations`

**Only `Workforce` apps can use `accessModel: Group`.** (`ExternalWorkforce` apps can also use `Group` for admin/profile configurations.)

---

### App Launcher Configurations

**Use when:** Surfacing an app link in the Workforce or Community launcher (9-box in the omnibar).

- `Workforce` and `Community` apps use `appLauncherConfigurations`
- `ExternalWorkforce` and `ExternalCommunity` apps use `externalLauncherConfigurations`

**ExternalLauncherConfiguration URL resolver:** TCP POSTs this JSON to the registered `url`:
```json
{
  "PlatformDomain": "tcpci.com",
  "PlatformWorkspaceName": "coffeecup",
  "CrmCustomer": "demo",
  "CrmAccountNumber": "12345"
}
```
TCP expects a plain string response — the actual launcher URL for that workspace. Example response: `https://myapp.example.com/demo/coffeecup`

Example resolver service: https://github.com/tyler-technologies/example-app-navigation-url-svc/

After updating a URL resolver endpoint, re-POST the registration object to the App Registration API to refresh cached links.

---

### App Administration Configurations

**Use when:** Surfacing admin links in Admin Center > Admin Links (`/org/admin-center/admin-links`).

- Only loaded for `Workforce` (Enterprise) apps.
- Multiple admin configurations can be registered (e.g., one per module).
- For `ExternalWorkforce` apps: the static `url` property is required.
- For `ExternalWorkforce` apps with a URL resolver: use `externalAppAdministrationConfigurations`.

**Fields:** `label`, `helpText`, `priority`, `domain` (if the app has multiple domains), `url` (for external), `TylerComponentsWebIconName`

---

### Profile Administration Configuration

**Use when:** Surfacing a per-user settings link in Admin Center user profile side-nav (`/org/admin-center/users`).

- Mutually exclusive with `AppLauncherConfigurations` and `AppAdministrationConfigurations`.
- Only one `profileAdministrationConfiguration` per app.
- Only loaded for `Workforce` apps.

---

### Ops Center Configurations

**Use when:** Surfacing operational links in Ops Center.

Three configuration types:
- `opsCenterProductConfigurations` — global product-level config/tools
- `opsCenterOrganizationConfigurations` — org-specific tools
- `opsCenterWorkspaceConfigurations` — workspace-specific tools

**Requirements:**
- `authenticationModel` must be `ExternalWorkforce` or `Workforce`
- `url` required when using `ExternalWorkforce`
- TCP access groups are **not evaluated** in Ops Center — `accessModel` of `Group` or `Everyone` both work

---

### URL Token Replacement

Tokens in `url` properties are replaced at display time with actual values. Applicable to: `ProfileAdministrationConfiguration`, `AppAdministrationConfiguration`, `OpsCenterConfigurations`.

| Token | Replaced with |
|---|---|
| `{customer}` | CRM customer key |
| `{organization}` | Organization key |
| `{crmid}` | CRM ID |
| `{customeraccountid}` | Customer account ID |
| `{workspace}` | Workspace key |
| `{__TENANTID__}` | Tenant ID |
| `{id}` | Entity ID |
| `{userid}` | User ID |
| `{usersub}` | User Okta sub |
| `{email}` | User email |

Example: URL `https://{workspace}.somedomain.com/product/app` renders as `https://demo.somedomain.com/product/app` for the `demo` workspace.

Full token reference: https://github.com/tyler-technologies/tcp-service-url-api#url-tokens

---

### Icon Configuration

Icons appear on launcher cards and admin link entries. Specify an `icon` object with:

| `type` | Required property | Description |
|---|---|---|
| `font` | `name` | Forge icon name (from https://forge.tylertech.com/components/omnibar-app-launcher/development/#icontype) |
| `image` | `uri` | Relative URI to image file |
| `svg` | `uri` | Relative URI to SVG file |

---

### Default Product Groups

**Use when:** A product uses TCP group access management and needs standard groups created automatically when licensed to a new org.

- Each default product group is auto-created when the product is licensed to an org (or when a new portal is created with the product licensed).
- Group names must be globally unique — prefix with product name to avoid collisions.
- Each group requires a list of `apps` (app titles registered under the same product).

```yaml
defaultProductGroups:
  - title: PetRegAdmins
    description: Administrators for Pet Registration
    apps:
      - PetReg-Administration
      - PetReg-UserSettings
```

---

### Additional Logout Redirect URIs

A product may specify logout redirect URIs to be applied to Okta tenants created when the product is licensed to a workspace. Add an `additionalLogoutURIs` array under the relevant app in the `apps` collection.

---

## URL Mapping API Secret Setup

**Use when:** The product registration includes an ExternalWorkforce/Community launcher that calls a URL resolver API and needs to pass a secret credential.

**Never store secrets in plaintext in the YAML.** Use Harness secret placeholders — the Harness operator replaces them before the CRD is applied.

### New Default Gateway ClientId/Secrets (Recommended)

CorpDev manages and rotates these secrets — you do not need to maintain them yourself.

| Environment | `authority` | `clientId` | `clientSecret` placeholder |
|---|---|---|---|
| TCPCI | `https://idgw.tcpci.com/tg/` | `tyler-cloud-platform-resolver` | `'<+secrets.getValue("tcpci-jwt-default")>'` |
| TCPQA | `https://idgw.tcpqa.com/tg/` | `tyler-cloud-platform-resolver` | `'<+secrets.getValue("tcpqa-jwt-default")>'` |
| TCPPROD | `https://idgw.tylerportico.com/tg/` | `tyler-cloud-platform-resolver` | `'<+secrets.getValue("tcpprod-jwt-default")>'` |

See the [Identity Dual Trust Guide](https://docs.tylerdev.io/identity/identity-guides/api-dual-trust/overview/) for how to implement authentication against these gateway credentials.

**CI environment YAML example (JWT, default gateway):**
```yaml
externalLauncherConfigurations:
  - label: Enterprise ERP
    helpText: Complete enterprise resource planning solutions
    priority: 0
    url: https://tenantmanagement.ci.enterpriseerp.tylerapi.com/url
    authorizationType: Jwt
    authority: https://idgw.tcpci.com/tg/
    clientId: tyler-cloud-platform-resolver
    clientSecret: '<+secrets.getValue("tcpci-jwt-default")>'
    scopes: tyler-cloud-platform-resolver-access
```

### Using Your Own Harness Secret

If you cannot use the default gateway secret, store your own in Harness.

**Placeholder format:**

| Pattern | Format | Example |
|---|---|---|
| One API instance per environment | `'<+secrets.getValue("{registration_id}_secret_{env}")'` | `'<+secrets.getValue("enterprise_erp_secret_tcpci")'` |
| One API instance for all environments | `'<+secrets.getValue("{registration_id}_secret")'` | `'<+secrets.getValue("enterprise_erp_secret")'` |

Note: Replace hyphens with underscores in secret IDs (Harness does not allow hyphens in secret IDs).

**How to add the secret to Harness:**

1. Request access to Harness (if needed): submit a ticket at the [Ops Center Related Tickets and Permissions](https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386600308/Tyler+Cloud+Platform+TCP+Ops+Center+Related+Tickets+and+Permissions) page — request the `Product Registry Product Manager` role in the Product Registry project under the CorpDev org.
2. Navigate to the Product Registry project: https://app.harness.io/ng/account/NVsV7gjbTZyA3CgSgXNOcg/home/orgs/CorpDev/projects/Product_Registry/details
3. Click **Secrets** in the Project Setup menu.
4. Add a new text secret. Use lower-kebab-case for the name and lower-underscore for the ID. The ID value must match the ID in the YAML placeholder.

---

## Using Ops Center to Verify Registration

**Prerequisites:** Access to Ops Center (TCPCI for dev). Request access at [Ops Center Related Tickets and Permissions](https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386600308/Tyler+Cloud+Platform+TCP+Ops+Center+Related+Tickets+and+Permissions).

**Verification workflow:**

1. **View your product:** Ops Center Home → Products → search by name
   - URL: https://admin.tcpci.com/portal/ops-center/dashboard
   - The JSON tab in Registration Details should match the YAML in `tcp-product-catalog` on master.
2. **License to dev org:** https://admin.tcpci.com/portal/ops-center/manage-organizations/dev/licensed-products
3. **Activate on dev workspace:** https://admin.tcpci.com/portal/ops-center/manage-organizations/dev/workspaces/dev
4. **Test in Enterprise Launcher:** https://dev.tcpci.com/portal/enterpriselauncher/

After pushing a PR to master, allow time for the registration to update, then verify in Ops Center.

---

## Example Case Study — Cemetery Manager

This fictional product illustrates how to apply registration guidance end-to-end.

**Product:** Tyler Cemetery Manager — a cloud-based, multi-tenant app with:
- Cemetery Manager app (Workforce — main employee app)
- Supervisor app (Workforce — limited to supervisors)
- Administration app (Admin — IT/site admin configuration)
- Plot Viewer app (Community — public plot search)
- Ops app (Ops — Tyler cloud operations)

### Final Registration Approach

| Entity | App type | Surfaces in | Key attributes |
|---|---|---|---|
| Cemetery Manager Product | N/A | Ops Center Product Registry; Admin Center Manage Products | Name, Description, About, Contact info |
| Cemetery Manager | Workforce | Workforce App Directory | Icon: `hospital_marker` (extended) |
| Cemetery Manager Supervisor | Workforce | Workforce App Directory | Icon: `approval` (standard) |
| Cemetery Manager Admin | Admin | Admin Center > Admin Apps | Icon: `hospital_marker` (extended) |
| Cemetery Plot Viewer | Community | Community Services Directory | Name: "View cemetery plots"; Icon: `person_pin_circle` |
| Cemetery Manager Ops | Ops | Ops Center | Icon: `hospital_marker` (extended) |

### Post-Registration UI Impacts

**Ops Center:**
- Product appears under Ops Center > Product Registry with contact info (Teams channel + email DLs), Ops App tab, and Registration Details tab.
- Licensing option appears under Organizations > Licensed Products.
- Activation toggle appears under Organizations > Manage Workspaces.

**Admin Center** (after licensing + activation):
- Product listed under Admin Center > Products with name, description, and application list.
- Admin app appears under Admin Center > Admin Apps with per-workspace links.

**Workforce App Directory** (after licensing + activation):
- Cards for "Cemetery Manager", "Cemetery Manager Supervisor", and "Cemetery Manager Admin" (with [Admin] badge).

**Community Services Directory** (after licensing + activation):
- Card: "View cemetery plots" — "View details and availability of plots".

---

## FAQs

### How does a Product differ from a SKU?

A **product** = what is *installed/provisioned* on the platform. A **SKU** (in Tyler's CRM) = what a customer has *subscribed/licensed* commercially.

- One-to-one alignment is common (product name matches SKU name).
- A single SKU can bundle multiple products.
- Multiple SKUs may include the same product at different price points.

Example: Content Manager is a product included with Enterprise Appraisal and Tax (one SKU), but also sold standalone alongside Enterprise ERP (separate SKU). Both provision the same Content Manager product.

### What is the Product Registry?

The Product Registry is the registry of all Tyler products on TCP. Each product team is responsible for contributing and maintaining their own registration details. It is maintained operationally by CorpDev.

### I need a single Tyler-branded portal shared across all organizations — how do I register it?

Some products (e.g., Recording Access, AP Automation Vendor Hub) use a single Tyler-branded public portal across all orgs. These are *domain-specific Tyler branded products* — they are not designed to be licensed on regular customer organizations and do not contain Workforce or Admin apps. Registration guidance is handled case-by-case. Contact CorpDev via the [Product Registration Community Teams Channel](https://teams.microsoft.com/l/channel/19%3AoVLpzEarOxFx-RwQc70RhkOA0xXbUS6R52LrTWKhIMQ1%40thread.tacv2/Product%20Registration%20Community?groupId=d9db441d-35fa-433c-8fe0-ff7fe5825d3c&tenantId=7cc5f0f9-ee5b-4106-a62d-1b9f7be46118&ngc=true&allowXTenantAccess=true).

### How can I minimize manual group creation for my product?

For products using TCP group access management, define `defaultProductGroups` in the product registration. These groups are automatically created when the product is licensed to any org.

---

## Customer Onboarding

> **Note:** The Blueprint pages for Provisioning Customers, Licensing Products, Importing Customers from CRM, Product Licensing Data Population, Customer Onboarding Checklist, and Product Registration Checklist are currently **stubs / placeholders** — no substantive content has been published yet. For current customer onboarding procedures, contact CorpDev or consult the Ops Center agent: https://docs.tylerdev.io/app-guides/ops/ops-center/overview/

The conceptual flow for customer onboarding is:
1. **Product is registered** in tcp-product-catalog (engineering task, covered in this file)
2. **Product is licensed to an organization** — via Ops Center (ops task)
3. **Product is activated on a workspace** — via Ops Center (ops task)
4. Users gain access through TCP group membership and Admin Center

---

## Notes for the Chatbot

1. **RegistrationId is immutable** — this is the most common trap. Emphasize strongly: never change a RegistrationId after initial registration. Changing a product's RegistrationId creates a duplicate. Changing an app's RegistrationId deletes the old app.
2. **One registration per product is the rule.** If someone asks about splitting a product into multiple registrations, instruct them to contact CorpDev first.
3. **tcp-product-catalog is the authoritative source** for live registration state. The JSON visible in Ops Center Registration Details should always match the YAML in the master branch of tcp-product-catalog.
4. **External vs. non-external auth model distinction is critical.** `ExternalWorkforce`/`ExternalCommunity` apps cannot have `AppLauncherConfigurations`; they use `ExternalLauncherConfigurations` and a URL resolver API. `Workforce`/`Community` apps use `AppLauncherConfigurations` and a `path` property.
5. **Customer onboarding pages (provisioning, licensing, importing from CRM, checklists) are stubs** as of the source date. Do not attempt to answer questions from this file about those topics — direct users to CorpDev directly or the Ops Center agent.
6. **Secrets in YAML are always Harness placeholders** — never plaintext. Recommend the default CorpDev-managed gateway secret when users ask about URL resolver authentication; only guide them through custom Harness secrets as a fallback.
7. **Dedicated agents exist for:** Ops Center → https://docs.tylerdev.io/app-guides/ops/ops-center/overview/ | Support Access Center (SAC) → https://docs.tylerdev.io/ops/support-access-center/ | Identity → https://docs.tylerdev.io/identity — route Ops Center UI questions, SAC questions, and identity/Okta questions to those agents.
8. **Product Registration Community Teams Channel** is the correct escalation path for complex registration questions: https://teams.microsoft.com/l/channel/19%3AoVLpzEarOxFx-RwQc70RhkOA0xXbUS6R52LrTWKhIMQ1%40thread.tacv2/Product%20Registration%20Community?groupId=d9db441d-35fa-433c-8fe0-ff7fe5825d3c&tenantId=7cc5f0f9-ee5b-4106-a62d-1b9f7be46118&ngc=true&allowXTenantAccess=true — surface this URL verbatim when a user needs guidance that goes beyond what this file covers.
