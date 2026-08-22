# Tyler Cloud Platform (TCP) — API Service Catalog

Source: https://docs.tylerdev.io/architecture/cloud-platform-api/ (Tyler Blueprint Docusaurus)
Domain: Blueprint General — Tyler Cloud Platform / Blueprint docs not served by a specialized Foundry agent
Audience: Tyler product and platform engineers integrating with TCP backend APIs

**Companion documents:**
- `_START_HERE.md` — routing guide for this corpus
- `Docusaurus-PlatformOverview.md` — high-level TCP architecture and concepts
- `Docusaurus-ClientApps.md` — client-side app integration guidance
- `Docusaurus-OpsApps.md` — operational app development
- `Docusaurus-ServiceArchitecture.md` — service-to-service patterns and architecture decisions
- `Docusaurus-DevOps.md` — CI/CD, deployment, and infra
- `Docusaurus-Security.md` — security patterns, auth flows
- `Docusaurus-ProductSystemReg.md` — product and app registration workflows
- `Docusaurus-AlignedReleases.md` — aligned release and cohort process
- `Docusaurus-StatusPageAndSLA.md` — platform status and SLA

**Dedicated-agent hand-offs (do NOT answer in depth here — redirect):**
- **Ops Center** questions → https://docs.tylerdev.io/app-guides/ops/ops-center/overview/
- **Support Access Center (SAC)** conceptual/workflow questions → https://docs.tylerdev.io/ops/support-access-center/
- **Identity / TID** conceptual/workflow questions → https://docs.tylerdev.io/identity

---

## How to use this guide

Use this table to find the right API for your task. Then jump to the named section for endpoints and key details.

| I need to… | Start with |
|---|---|
| Link/manage user payment or external accounts | [tcp-accountlinking-service](#tcp-accountlinking-service) |
| Check whether an app is available in a workspace, or manage nav link caches | [tcp-app-availability](#tcp-app-availability) |
| Register a product or app (internal/pipeline use) | [tcp-app-registration-api](#tcp-app-registration-api) |
| Register a product or app from an external caller / app team | [tcp-app-registration-api-public](#tcp-app-registration-api-public) |
| Search or write audit log events in OpenSearch | [tcp-audit-opensearch](#tcp-audit-opensearch) |
| Manage roles, groups, permissions, service accounts, users for TCP authorization | [tcp-authorization-api](#tcp-authorization-api) |
| Query or ingest authorization decision logs (OPA/policy decisions) | [tcp-authorization-decision-logs](#tcp-authorization-decision-logs) |
| Manage org/workspace branding colors, logos, themes (v2 API) | [tcp-branding-api](#tcp-branding-api) |
| Manage legacy branding assets — banners, logos, welcome messages | [tcp-branding-service](#tcp-branding-service) |
| Bulk license a product across many orgs/workspaces via CSV | [tcp-bulk-product-licensing-api](#tcp-bulk-product-licensing-api) |
| Manage community portal services, departments, user groups, change logs | [tcp-community-services-api](#tcp-community-services-api) |
| Read or write credential templates for app OAuth clients | [tcp-credential-template-api](#tcp-credential-template-api) — see also Identity agent |
| Search, redrive, or purge failed eventing outbox/DLQ messages | [tcp-eventing-retry-api](#tcp-eventing-retry-api) |
| Manage event schema definitions in the eventing registry | [tcp-eventing-schema-registry](#tcp-eventing-schema-registry) |
| Publish identity lifecycle events (user created/changed/deleted) into webhook pipeline | [tcp-identity-events-api](#tcp-identity-events-api) |
| Track system installation records | [tcp-infrastructure-tracking-api](#tcp-infrastructure-tracking-api) |
| Check user app access, group membership, or SAC access (login-time security) | [tcp-login-security-api](#tcp-login-security-api) — see also SAC agent |
| Send platform notifications (magic links, welcome emails, SAC emails) | [tcp-notifications-api](#tcp-notifications-api) |
| Retrieve navigation/launcher links for the omnibar | [tcp-omni-service](#tcp-omni-service) |
| Manage orgs, workspaces, products, profiles, user groups, cohorts, features, releases | [tcp-platform-service](#tcp-platform-service) |
| Manage Okta tenant clients, tenants, or send provisioning emails | [tcp-provisioning-service](#tcp-provisioning-service) |
| Search/autocomplete for orgs and workspaces in Admin Center | [tcp-search-api](#tcp-search-api) |
| Read or write service URLs for app routing (internal; prefer Omni for reads) | [tcp-service-url-api](#tcp-service-url-api) |
| Manage SAC support requests, user groups, products, access revocation | [tcp-support-access-center-api](#tcp-support-access-center-api) — see also SAC agent |
| Provision/activate/deactivate Tyler support accounts in a customer Okta tenant | [tcp-support-accounts-api](#tcp-support-accounts-api) — see also SAC agent |
| Bulk import users into an org | [tcp-user-import-api](#tcp-user-import-api) |
| Subscribe to or publish TCP webhook message types | [tcp-webhook-api](#tcp-webhook-api) |
| Manage community identity apps/clients (TID-C) | [tid-c-service](#tid-c-service) — see also Identity agent |
| Write identity configuration key-value settings | [tid-identity-configuration-api](#tid-identity-configuration-api) — see also Identity agent |
| Read identity configuration settings (app teams) | [tid-identity-configuration-lookup-api](#tid-identity-configuration-lookup-api) — see also Identity agent |

---

## Service index

| Service | One-line purpose | Externally available | App teams usable | Docs URL |
|---|---|---|---|---|
| tcp-accountlinking-service | Link/manage user account records (e.g. financial account associations) | Yes | Yes | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-accountlinking-service/tcp-accountlinking-service |
| tcp-app-availability | Track app availability per workspace; manage workforce/admin/community navigation caches | No | No | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-app-availability/tcp-app-availability |
| tcp-app-registration-api | Internal API to register/upsert/delete product+app registrations | No | Yes | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-app-registration-api/tcp-app-registration-api |
| tcp-app-registration-api-public | External-facing API to register/upsert/delete product registrations | Yes | Yes | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-app-registration-api-public/tcp-app-registration-api-public |
| tcp-audit-opensearch | Write and search platform audit log events in OpenSearch | Yes | No | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-audit-opensearch/tcp-audit-opensearch |
| tcp-authorization-api | Manage TCP authorization: roles, groups, permissions, users, service accounts | Yes | No | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-authorization-api/tcp-authorization-api |
| tcp-authorization-decision-logs | Ingest and search OPA/authorization policy decision logs | No | No | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-authorization-decision-logs/tcp-authorization-decision-logs |
| tcp-branding-api | Manage org/app login and app colors, logos, hero images (v2) | Yes | Yes | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-branding-api/tcp-branding-api |
| tcp-branding-service | Manage legacy branding assets: banners, logos, welcome messages, CSS | Yes | Yes | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-branding-service/tcp-branding-service |
| tcp-bulk-product-licensing-api | Bulk-license a product to many orgs/workspaces via uploaded CSV files | No | No | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-bulk-product-licensing-api/tcp-bulk-product-licensing-api |
| tcp-community-services-api | Manage community portal services, departments, roles, user groups, change logs | — | — | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-community-services-api/tcp-community-services-api |
| tcp-credential-template-api | CRUD credential templates for OAuth app client configurations | — | — | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-credential-template-api/tcp-credential-template-api |
| tcp-eventing-retry-api | Search, redrive, and purge failed TCP eventing outbox and DLQ messages | Yes | No | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-eventing-retry-api/tcp-eventing-retry-api |
| tcp-eventing-schema-registry | Register and manage event schema definitions for the TCP eventing system | No | No | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-eventing-schema-registry/tcp-eventing-schema-registry |
| tcp-identity-events-api | Publish identity lifecycle events (workforce/community user changes) into the webhook pipeline | No | No | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-identity-events-api/tcp-identity-events-api |
| tcp-infrastructure-tracking-api | Track and retrieve infrastructure installation records | Yes | Yes | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-infrastructure-tracking-api/tcp-infrastructure-tracking-api |
| tcp-login-security-api | Check app availability, user access, product group access, SAC access, and user group membership at login time | Yes | Yes | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-login-security-api/tcp-login-security-api |
| tcp-notifications-api | Send platform-triggered email notifications (magic links, welcome, SAC request emails) | No | No | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-notifications-api/tcp-notifications-api |
| tcp-omni-service | Retrieve navigation/launcher links (intents) for the Tyler omnibar | Yes | Yes | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-omni-service/tcp-omni-service |
| tcp-platform-service | Central platform data API: orgs, workspaces, products, apps, profiles, user groups, cohorts, features, releases | Yes | Yes | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-platform-service/tcp-platform-service |
| tcp-provisioning-service | Manage Okta auth clients and tenants; send provisioning emails | Yes | Yes | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-provisioning-service/tcp-provisioning-service |
| tcp-search-api | Search and autocomplete for organizations and workspaces (Admin Center search) | Yes | No | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-search-api/tcp-search-api |
| tcp-service-url-api | Store and retrieve service URLs for app routing (internal use; callers should prefer tcp-omni-service) | No | No | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-service-url-api/tcp-service-url-api |
| tcp-support-access-center-api | Manage SAC support requests, user groups, products, and user access revocation | Yes | Yes | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-support-access-center-api/tcp-support-access-center-api |
| tcp-support-accounts-api | Provision, activate, and deactivate Tyler support user accounts in customer Okta tenants | No | Yes (ERP only) | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-support-accounts-api/tcp-support-accounts-api |
| tcp-user-import-api | Bulk import users into an organization | No | No | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-user-import-api/tcp-user-import-api |
| tcp-webhook-api | Register webhook subscriptions and manage message types | Yes | Yes | https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-webhook-api/tcp-webhook-api |
| tid-c-service | Tyler Identity Community (TID-C): manage community identity apps, clients, user profiles, self-service, and admin | Yes | Varies | https://docs.tylerdev.io/architecture/cloud-platform-api/tid-c-service/tid-c-service |
| tid-identity-configuration-api | Write identity configuration key-value settings (app team use) | No | Yes | https://docs.tylerdev.io/architecture/cloud-platform-api/tid-identity-configuration-api/tid-identity-configuration-api |
| tid-identity-configuration-lookup-api | Read-only retrieval of identity configuration settings | Yes | Yes | https://docs.tylerdev.io/architecture/cloud-platform-api/tid-identity-configuration-lookup-api/tid-identity-configuration-lookup-api |

---

## Glossary

| Term | Meaning |
|---|---|
| TCP | Tyler Cloud Platform — the overall SaaS platform underpinning Tyler portals |
| TID | Tyler Identity Domain — identity infrastructure (Okta-based) |
| TID-C | Tyler Identity Community — identity service scoped to Community (citizen) auth model |
| Workforce | Auth model for internal/employee users (Tyler Workforce) |
| Community | Auth model for citizen/external-public users |
| ExternalWorkforce | Auth model for external workforce (e.g. contractors) |
| ExternalCommunity | Auth model for external community users |
| Org / Organization | A Tyler customer entity (`customerId` / `orgKey`) |
| Workspace / Portal | A deployment instance of the portal for an org (`portalId` / `workspaceKey`) |
| Registration ID | Unique identifier for a product or app registration in TCP |
| Identity Sub | The Okta subject identifier (`identitySub`) for a user profile |
| Ingress | The public URL path prefix through which the API is reachable externally |
| BASE_URL | Environment-specific base URL (e.g. `https://api.tylerportico.com` for production) |
| DLQ | Dead-Letter Queue — holds failed eventing messages pending retry |
| OPA | Open Policy Agent — used for authorization policy decisions |
| SAC | Support Access Center — Tyler's product for managing vendor support access |
| Cohort | A named release segment (e.g. Cohort 1, 2, 3) used to progressively roll out features |
| Product Group | A grouping of apps within a workspace that controls user access |
| PlatformGroup | See Product Group |
| CRM ID | Dynamics CRM GUID identifying the customer in Tyler's CRM |
| JWT | JSON Web Token — auth credential passed as `Bearer {token}` |
| Presigned URL | Time-limited S3 upload URL generated by the API |

---

## tcp-accountlinking-service

**Purpose:** Links external account records (e.g. financial or utility accounts) to TCP user profiles, enabling account-based access and lookup across Tyler community applications.

**Ingress:** `{BASE_URL}/portal/accountlinking`
**Auth:** JWT Bearer token
**Externally available:** Yes | **Usable by app teams:** Yes
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-accountlinking-service/tcp-accountlinking-service

**Key operations:**

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/Accounts` | List linked accounts (filter by params) |
| POST | `/api/v1/Accounts` | Add an account link |
| PUT | `/api/v1/Accounts` | Update account number or description |
| DELETE | `/api/v1/Accounts` | Delete an account link |
| GET | `/api/v1/AccountTypes` | List available account types |
| GET | `/api/v1/UserAccounts` | List account links for the calling user |
| DELETE | `/api/v1/UserAccounts` | Delete all account links for a user |
| GET | `/api/v1/Users` | Get users linked to a specific account |

---

## tcp-app-availability

**Purpose:** Tracks which apps and products are available (licensed and active) per workspace, and manages the navigation link caches used by the portal for Workforce, Admin, and Community navigation menus.

**Auth:** JWT Bearer token
**Externally available:** No | **Usable by app teams:** No (internal platform use)
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-app-availability/tcp-app-availability

**Key operation groups:**

| Group | Key operations |
|---|---|
| AppAvailability | GET/POST/DELETE/bulk upsert availability records by org, workspace, product, app |
| ProductAvailability | GET/POST/DELETE/bulk upsert product-level availability records |
| WorkforceNavigation | GET/POST navigation links for a workspace; add/remove group assignments; activate/deactivate by org |
| AdminNavigation | GET/POST admin navigation links for an org; workspace-scoped CRUD and group assignment |
| CommunityNavigation | GET/POST community navigation links for a workspace; workspace-scoped CRUD |
| Workspace | Check if app is available in a workspace; get products with at least one available app |
| Organization | Get all app availabilities for an org; activate/deactivate all |

**Note:** Navigation cache management (clear, replace, activate/deactivate) is destructive — only used by platform infrastructure operations. App teams should prefer `tcp-platform-service` for product/app availability queries.

---

## tcp-app-registration-api

**Purpose:** Internal API for registering (upsert) and deleting product+app registrations in TCP. Functionally identical to the public variant but not externally accessible.

**Auth:** JWT Bearer token
**Externally available:** No | **Usable by app teams:** Yes (internal/pipeline callers)
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-app-registration-api/tcp-app-registration-api

**Key operations:**

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/ProductAppRegistration` | Register/upsert a product (and its apps) |
| DELETE | `/api/v1/ProductAppRegistration/{registrationId}` | Delete a product registration |
| GET | `/api/v1/ProductAppRegistration/{registrationId}` | Get a product registration by ID |

**Use when:** Automating product registration from a CI/CD pipeline (internal network). For external/app-team callers use [tcp-app-registration-api-public](#tcp-app-registration-api-public).

---

## tcp-app-registration-api-public

**Purpose:** Externally accessible API allowing app teams to register (upsert) and manage product registrations in TCP. This is the standard entry point for product registration from app-team pipelines.

**Ingress:** `{BASE_URL}/api/tcp-app-registration-api`
**Auth:** JWT Bearer token
**Externally available:** Yes | **Usable by app teams:** Yes
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-app-registration-api-public/tcp-app-registration-api-public

**Key operations:**

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/ProductAppRegistration` | Register/upsert a product (and its apps) |
| DELETE | `/api/v1/ProductAppRegistration/{registrationId}` | Delete a product registration |
| GET | `/api/v1/ProductAppRegistration/{registrationId}` | Get a product registration by ID |

**Companion:** See `Docusaurus-ProductSystemReg.md` for the full product registration workflow and schema guidance.

---

## tcp-audit-opensearch

**Purpose:** Writes and queries platform audit log events stored in OpenSearch. Used to create audit log entries, manage audit indexes, and search audit history.

**Ingress:** `{BASE_URL}/search/audit`
**Auth:** JWT Bearer token; specific permissions required per operation (see below)
**Externally available:** Yes | **Usable by app teams:** No (platform use only)
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-audit-opensearch/tcp-audit-opensearch

**Key operations:**

| Method | Path | Required Permission |
|---|---|---|
| POST | `/api/v1/Document` | `create:auditlog` |
| POST | `/api/v1/Document/bulk` | `create:auditlog` |
| POST | `/api/v1/Search` | `read:auditlog` |
| POST | `/api/v1/Index` | `create:auditindex` |
| GET | `/api/v1/Index` | `read:auditindex` |
| DELETE | `/api/v1/Index/{indexName}` | `delete:auditindex` |
| POST | `/api/v1/Index/Migrate/{source}/{target}` | `migrate:auditindex` |

**Note for the chatbot:** External audit log *searching* by user-facing tools uses tcp-cli (`tcp-cli search audit`) or the Admin Center UI, not this API directly. This API is for platform services writing and managing the underlying data.

---

## tcp-authorization-api

**Purpose:** Manages the TCP authorization model — roles, groups, permissions, users, and service accounts. This is the backbone of TCP's access control: every product, user, group, and service account with a permission needs to be registered here.

**Ingress:** `{BASE_URL}/platform/authorization`
**Auth:** JWT Bearer token; write operations require specific permissions (e.g. `register:authorizationpermission`, `update:authorizationrole`, `update:authorizationuser`)
**Externally available:** Yes | **Usable by app teams:** No (platform/ops use)
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-authorization-api/tcp-authorization-api

**Key operation groups:**

| Group | Purpose |
|---|---|
| Role | CRUD roles; assign/remove users, service accounts, groups, permissions to roles |
| Group | CRUD groups; assign/remove users and service accounts; get group roles |
| Permission | Register, list, delete permissions (`action:resource` format) |
| User | CRUD users; assign roles, groups, product scopes |
| ServiceAccount | CRUD service accounts; assign roles, groups, permissions, product scopes |
| AdminCenter | Get/set Admin Center attributes for a user or org; get users by role |
| Product | List, upsert, delete products in the authorization store |
| Export | Export all authorization data to S3 |

**Important fields:** Permissions use `{action}:{resource}` format (e.g. `read:auditlog`). Roles are named strings. Product associations scope a user or service account to a specific product registration.

---

## tcp-authorization-decision-logs

**Purpose:** Ingests and queries OPA (Open Policy Agent) authorization decision logs — the record of every policy evaluation TCP makes at runtime.

**Auth:** JWT Bearer token
**Externally available:** No | **Usable by app teams:** No (internal platform use)
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-authorization-decision-logs/tcp-authorization-decision-logs

**Key operations:**

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/Ingest/decision-log` | Ingest a single decision log entry |
| POST | `/api/v1/Ingest/decision-logs` | Ingest multiple decision log entries |
| POST | `/api/v1/Ingest/status` | Check ingest status |
| POST | `/api/v1/Search` | Query decision logs |
| POST | `/api/v1/Document` / `/api/v1/Document/bulk` | Write document(s) directly |
| POST/GET/DELETE | `/api/v1/Index[/{name}]` | Manage OpenSearch indexes |

---

## tcp-branding-api

**Purpose:** v2 branding API for managing org-level and app-level visual identity in TCP — login page colors, app colors, logos, and hero images. Uses a presigned-URL upload pattern for image assets.

**Ingress:** `{BASE_URL}/portal/branding`
**Auth:** JWT Bearer token
**Externally available:** Yes | **Usable by app teams:** Yes
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-branding-api/tcp-branding-api

**Key operation groups:**

| Group | Purpose |
|---|---|
| Login `/{orgKey}` | GET/POST/DELETE login page colors; upload/publish/delete login logo; check image status |
| App `/{orgKey}` | GET/POST/DELETE app colors; manage hero image (upload URL, download URL, publish, delete); manage app logo; get theme CSS; get Forge adapter CSS |

**Upload pattern:** Call `POST .../uploadurl` → receive presigned S3 URL → upload file → call `POST .../publish/{guid}` to make live.

**Note:** For older/legacy branding assets (welcome messages, banners) use [tcp-branding-service](#tcp-branding-service).

---

## tcp-branding-service

**Purpose:** Legacy v1 branding service managing workspace-level branded HTML content (header, banner, footer, CSS), asset manifests, customer logos, and welcome messages.

**Auth:** JWT Bearer token
**Externally available:** Yes | **Usable by app teams:** Yes
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-branding-service/tcp-branding-service

**Key operations:**

| Method | Path | Purpose |
|---|---|---|
| GET/PUT | `/api/v1/AssetManifest/{portalId}` | Get/update asset manifest for a workspace |
| GET/PUT | `/api/v1/CustomerAssetManifest/{customerId}` | Get/update asset manifest for an org |
| GET | `/api/v1/Content/Header` | Generate branded header HTML |
| GET | `/api/v1/Content/LargeBanner` | Generate branded banner HTML |
| GET | `/api/v1/Content/Footer` | Generate branded footer HTML |
| GET | `/api/v1/Content/TenantStyle` | Generate tenant CSS |
| GET | `/api/v1/CustomerBanner/.../presignedUrl` | Get S3 presigned URL for banner upload |
| POST | `/api/v1/CustomerBanner/.../publishStaged` | Publish staged banner to S3 |
| GET | `/api/v1/CustomerLogo/.../presignedUrl` | Get S3 presigned URL for logo upload |
| POST | `/api/v1/CustomerLogo/.../publishStaged` | Publish staged logo to S3 |
| GET/POST | `/api/v1/WelcomeMessage/customer/{customerId}` | Get/update welcome message |

---

## tcp-bulk-product-licensing-api

**Purpose:** Supports bulk licensing of a product to many organizations/workspaces at once via a CSV-driven job workflow — upload org list, review workspace selection, execute licensing, monitor job status.

**Auth:** JWT Bearer token
**Externally available:** No | **Usable by app teams:** No (platform/admin operations)
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-bulk-product-licensing-api/tcp-bulk-product-licensing-api

**Workflow summary:**

1. `POST .../org-import/presigned-url` → upload org-list CSV to S3
2. `GET .../job-summary` → check job creation and status
3. `POST .../workspace-selection/presigned-url` → upload workspace selection CSV
4. `PATCH .../job-summary/{jobSummaryId}/workspaces/{workspaceKey}` → update individual workspace selection
5. `POST .../job-summary/{jobSummaryId}/process` → trigger bulk processing
6. `GET .../job-summary/{jobSummaryId}/details` → review results
7. `GET .../job-summary/{jobSummaryId}/errors` → review errors
8. `POST .../job-summary/{jobSummaryId}/cancel` → cancel if needed

---

## tcp-community-services-api

**Purpose:** Manages community portal metadata — services (civic service records), departments, user groups, roles, change logs, and queue management for community workspace configurations. Also handles authorization data synchronization.

**Auth:** JWT Bearer token
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-community-services-api/tcp-community-services-api

**Key operation groups:**

| Group | Purpose |
|---|---|
| Services | Search/CRUD civic services within a workspace |
| Departments | CRUD departments; set defaults for org or workspace |
| UserGroups | CRUD user groups; manage group roles; add/remove users; list by workspace |
| Users | Get/update/delete user in an org; set/unset org admin; add to workspace |
| Roles | List available roles |
| ChangeLogs | Get change logs for a workspace; post service/dept/user-group/workspace change entries |
| DataSynchronizations | Queue or trigger authorization data sync for an org |
| Queue | Get queue message count; redrive or purge queues |
| Outbox | Search, redrive, or delete outbox (eventing) messages |
| Workspaces | Get workspace maintenance mode status; update workspace |
| Dashboard | Get dashboard data |

---

## tcp-credential-template-api

**Purpose:** CRUD operations for credential templates that define OAuth client configurations for app registrations. Used in the Identity domain to template how app clients are provisioned.

**Auth:** JWT Bearer token with scoped permissions
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-credential-template-api/tcp-credential-template-api

**Key operations:**

| Method | Path | Required Permission |
|---|---|---|
| GET | `/api/v1/Templates/{registrationId}` | `readcredentialtemplate` |
| GET | `/api/v1/Templates/{registrationId}/{templateVersion}` | `readcredentialtemplate` |
| POST | `/api/v1/Templates` | `createcredentialtemplate` |
| DELETE | `/api/v1/Templates` | `deletecredentialtemplate` |

**Identity agent hand-off:** For conceptual questions about credential templates and how they relate to app registration and Okta client provisioning, see the Identity Foundry agent: https://docs.tylerdev.io/identity

---

## tcp-eventing-retry-api

**Purpose:** Allows authorized platform operators to inspect, redrive (reprocess), and purge failed eventing messages from the TCP event outbox and dead-letter queues (DLQs).

**Ingress:** `{BASE_URL}/platform/eventing-retry`
**Auth:** JWT Bearer token with specific permissions
**Externally available:** Yes | **Usable by app teams:** No
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-eventing-retry-api/tcp-eventing-retry-api

**Key operations:**

| Method | Path | Required Permission |
|---|---|---|
| POST | `/api/v1/Outbox/search` | `read:eventerrors` |
| POST | `/api/v1/Outbox/redrive` | `redrive:eventerrors` |
| DELETE | `/api/v1/Outbox/delete` | `purge:eventerrors` |
| GET | `/api/v1/Queue/{queueName}/count` | `read:eventerrors` |
| POST | `/api/v1/Queue/redrive/{dlQueueName}` | `redrive:eventerrors` |
| POST | `/api/v1/Queue/purge/{dlQueueName}` | `purge:eventerrors` |

---

## tcp-eventing-schema-registry

**Purpose:** Manages event schema definitions and versions for the TCP eventing system, ensuring all producers and consumers agree on message structure.

**Auth:** JWT Bearer token with scoped permissions
**Externally available:** No | **Usable by app teams:** No
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-eventing-schema-registry/tcp-eventing-schema-registry

**Key operations:**

| Method | Path | Required Permission |
|---|---|---|
| GET | `/api/v1/Schema/{schemaName}` | `read:eventschema` |
| DELETE | `/api/v1/Schema/{schemaName}` | `delete:eventschema` |
| PUT | `/api/v1/Schema` | `update:eventschema` |

---

## tcp-identity-events-api

**Purpose:** Publishes identity lifecycle events (profile created/changed/deleted, user enabled/disabled) from the identity system into the TCP webhook pipeline, so downstream subscribers can react to user changes.

**Auth:** JWT Bearer token
**Externally available:** No | **Usable by app teams:** No (identity infrastructure use)
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-identity-events-api/tcp-identity-events-api

**Published events (all POST `/api/v1/Publish/...`):**

| Event | Path suffix |
|---|---|
| Workforce profile email changed | `WorkforceProfileEmailChanged` |
| Workforce user created | `WorkforceUserCreated` |
| Workforce user disabled | `WorkforceUserDisabled` |
| Workforce user enabled | `WorkforceUserEnabled` |
| Workforce user profile changed | `WorkforceUserProfileChanged` |
| Workforce user deleted | `WorkforceUserDeleted` |
| Community profile email changed | `CommunityProfileEmailChanged` |
| Community profile deleted | `CommunityProfileDeleted` |
| Community profile changed | `CommunityProfileChanged` |

**Identity agent hand-off:** For questions about how identity events are wired and consumed, see the Identity Foundry agent: https://docs.tylerdev.io/identity

---

## tcp-infrastructure-tracking-api

**Purpose:** Tracks infrastructure installation records — storing and retrieving information about what is installed where in the TCP infrastructure landscape.

**Ingress:** `{BASE_URL}/platform/infrastructure-tracking`
**Auth:** JWT Bearer token with scoped permissions
**Externally available:** Yes | **Usable by app teams:** Yes
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-infrastructure-tracking-api/tcp-infrastructure-tracking-api

**Key operations:**

| Method | Path | Required Permission |
|---|---|---|
| GET | `/api/v1/Installations` | `read:installation` |
| POST | `/api/v1/Installations` | `create:installation` |
| GET | `/api/v1/Installations/{registrationId}` | `read:installation` |
| DELETE | `/api/v1/Installations/{registrationId}` | `delete:installation` |
| GET | `/api/v1/InstallationTypes` | `read:installationtype` |

---

## tcp-login-security-api

**Purpose:** Runtime login-security checks — verifies whether a user can access an app in a workspace, checks product-group access, looks up SAC access, and returns a user's group memberships. Called at login/access-check time.

**Ingress:** `{BASE_URL}/platform/login-security`
**Auth:** JWT Bearer token
**Externally available:** Yes | **Usable by app teams:** Yes
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-login-security-api/tcp-login-security-api

**Key operations:**

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/Availability/{workspaceKey}/{appRegistrationId}` | Check if app is available on a workspace |
| GET | `/api/v1/CheckAccess/{identitySub}/workspace/{workspaceKey}/app/{appRegistrationId}` | Full access check for a user + workspace + app |
| GET | `/api/v1/ProductGroup/{workspaceKey}/{appRegistrationId}/{identitySub}` | Check user's product group access for an app |
| GET | `/api/v1/SupportAccess/{orgKey}/{workspaceKey}/{productRegistrationId}/{identitySub}` | Check if user has SAC-granted support access |
| GET | `/api/v1/UserGroup/{organizationKey}` | Get all user groups a user is a member of (by `identitySub` or `username`) |

**SAC agent hand-off:** For SAC concepts and workflow, see the SAC Foundry agent: https://docs.tylerdev.io/ops/support-access-center/

---

## tcp-notifications-api

**Purpose:** Sends platform-triggered email notifications: magic links for community self-service, welcome/access emails for new users and admins, and SAC support access request/resolution notifications.

**Auth:** JWT Bearer token
**Externally available:** No | **Usable by app teams:** No (platform infrastructure use)
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-notifications-api/tcp-notifications-api

**Key operations:**

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/MagicLink/initial` | Send initial magic link for community self-service |
| POST | `/api/v1/MagicLink/reestablish` | Re-send magic link |
| POST | `/api/v1/Profile/OrgAdminAdded` | Notify user they were added as org admin |
| POST | `/api/v1/Profile/OpsUserAdded` | Notify user they were added as ops user |
| POST | `/api/v1/Profile/AdAgentAccountReset` | Notify AD agent account reset |
| POST | `/api/v1/Profile/UserCreated` | Send user creation welcome notification |
| POST | `/api/v1/SupportAccess/RequestCreated` | Notify relevant parties of a new SAC request |
| POST | `/api/v1/SupportAccess/RequestResolved` | Notify relevant parties of SAC request resolution |

---

## tcp-omni-service

**Purpose:** The primary read API for retrieving navigation/launcher links ("intents") for the Tyler omnibar — the cross-product navigation component. App teams should call this rather than tcp-service-url-api directly.

**Ingress:** `{BASE_URL}/app/tyler-omnibar`
**Auth:** No auth listed on public intents endpoints (varies by endpoint)
**Externally available:** Yes | **Usable by app teams:** Yes
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-omni-service/tcp-omni-service

**Key operations:**

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/Intents/Organization/{organizationId}/CustomerAdmin/{actionType}` | Admin Center app intents for an org |
| GET | `/api/Intents/OpsCenterProducts` | Ops Center product intents (all) |
| GET | `/api/Intents/OpsCenterProducts/{organizationId}` | Ops Center product intents for a specific org |
| GET | `/api/Intents/Enterprise/Category/{serviceUrlType}` | Workforce/Enterprise launcher intents |
| GET | `/api/Intents/Category/{serviceUrlType}` | Community/Citizen launcher intents |
| GET | `/api/Intents/NoACLFiltering/Workspace/{workspaceKey}/IdentitySub/{identitySub}` | All launcher links for user (no ACL filtering) |

---

## tcp-platform-service

**Purpose:** The core TCP platform data API — the authoritative store for organizations, workspaces, products, apps, profiles, user groups, product groups, cohort assignments, features, and releases. Most portal and Admin Center operations go through or are reflected in this service.

**Ingress:** `{BASE_URL}/portal/platformservice`
**Auth:** JWT Bearer token
**Externally available:** Yes | **Usable by app teams:** Yes
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-platform-service/tcp-platform-service

**Key operation groups:**

| Group | Purpose |
|---|---|
| Customer (Orgs) | CRUD orgs; activate/deactivate; get org products, product groups, workspace apps, admin profiles; license/unlicense products |
| Portals (Workspaces) | CRUD workspaces; manage product groups, profiles, domains, products; look up by domain; workspace status |
| Products | CRUD products; upsert product+apps; manage default/portal product groups; get apps and service URLs; app-to-product-group management; refresh cache; divisions list |
| Profiles | CRUD user profiles; manage product groups, portal memberships, admin roles, workspace admins, product admins; get profile's apps; email domain queries |
| UserGroups | CRUD user groups; manage membership; check membership by identitySub or username; get unassigned profiles |
| Availability | Check app/product availability per workspace; refresh navigation cache for all or a specific app |
| CohortAssignment | Get/set cohort assignments per product-workspace; batch cohort assignments |
| Feature | CRUD features; set state; assign to release; activate/deactivate per workspace or cohort; get activations |
| Release / ReleaseCohort | CRUD releases and release cohorts; manage features and products within releases; mark releases as GA or executed |
| Module | CRUD modules (feature tagging) |
| OrganizationReleaseOverview | Get aggregated release status overview for an org |

**Use when:** Building or integrating any Admin Center or product portal feature that needs org/workspace/product/profile data. This is the most comprehensive platform data API.

---

## tcp-provisioning-service

**Purpose:** Manages Okta auth clients and TCP tenants (Okta tenant registrations), and sends provisioning-related emails (e.g. Admin Center welcome emails). This is the provisioning layer between TCP and the underlying identity infrastructure.

**Ingress:** `{BASE_URL}/portal/provisioning`
**Auth:** JWT Bearer token; some endpoints require specific permissions (e.g. `notify:admincenteruserwelcome`)
**Externally available:** Yes | **Usable by app teams:** Yes
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-provisioning-service/tcp-provisioning-service

**Key operations:**

| Method | Path | Purpose |
|---|---|---|
| POST/GET/PUT/DELETE | `/api/v1/IdentityClient[/{id}]` | CRUD TCP auth clients (Okta app clients) |
| GET | `/api/v1/IdentityClient/{env}/{tenantKey}` | Get Okta tenant URI for an environment/tenant |
| PUT | `/api/v1/IdentityClient` | Update auth client by name |
| POST/GET/PUT/DELETE | `/api/v1/Tenants[/{urlPrefix}]` | CRUD tenants (Okta customer tenants) |
| PUT | `/api/v1/Tenants/{urlPrefix}/products` | Update licensed products for a tenant |
| GET | `/api/v1/Tenants/OktaCustomerId/{customerId}` | Check if a customer Okta tenant exists |
| GET | `/api/v1/Products` / `/api/v1/Products/details` | List TCP products or get product details |
| POST | `/api/v1/Profile/{profileId}/SendAdminCenterAccessEmail` | Send Admin Center welcome email to a profile |

---

## tcp-search-api

**Purpose:** Powers the Admin Center search/autocomplete functionality — searches and autocompletes organization and workspace records stored in an OpenSearch index.

**Ingress:** `{BASE_URL}/platform/search`
**Auth:** JWT Bearer token
**Externally available:** Yes | **Usable by app teams:** No
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-search-api/tcp-search-api

**Key operations:**

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/Search/organizations` | Full-text search for organizations |
| POST | `/api/v1/Search/workspaces` | Full-text search for workspaces |
| GET | `/api/v1/Search/organizations/autocomplete/{search}` | Autocomplete org search |
| GET | `/api/v1/Search/workspaces/autocomplete/{search}` | Autocomplete workspace search |
| POST | `/api/v1/Reindex/organizations` | Trigger reindex of all organizations |
| POST | `/api/v1/Reindex/workspaces` | Trigger reindex of all workspaces |
| POST | `/api/v1/Search/aliases` | Manage OpenSearch index aliases |

---

## tcp-service-url-api

**Purpose:** Internal store for service URLs — the physical endpoint URLs associated with apps and their service URL types/auth models. Most callers should use [tcp-omni-service](#tcp-omni-service) instead; this API is for platform infrastructure that needs to read/write the underlying URL data directly.

**Auth:** API Key
**Externally available:** No | **Usable by app teams:** No
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-service-url-api/tcp-service-url-api

**Key operations:**

| Method | Path | Purpose |
|---|---|---|
| GET | `/replacementtokens` | List valid URL replacement tokens |
| GET | `/serviceurl` | Get service URLs by URL type and auth model |
| POST | `/serviceurl` | Save/register an app service URL |
| DELETE | `/serviceurl` | Delete a service URL |
| POST | `/serviceurl/bulk/save` | Bulk save service URLs |
| POST | `/serviceurl/bulk/delete` | Bulk delete service URLs |
| POST | `/serviceurl/repopulate` | Repopulate the service URL cache |
| GET | `/serviceurlbyproducts` | Get service URLs by product, URL types, and auth model |
| POST | `/serviceurlbyworkspaces` | Get service URLs for a list of workspaces, URL types, and auth model |

---

## tcp-support-access-center-api

**Purpose:** The REST API backing the Support Access Center (SAC) — manages SAC support requests, user groups, product associations, user access checks, and SAC-specific reindex operations.

**Ingress:** `{BASE_URL}/platform/support-access-center-api`
**Auth:** JWT Bearer token
**Externally available:** Yes | **Usable by app teams:** Yes
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-support-access-center-api/tcp-support-access-center-api

**Key operation groups:**

| Group | Key operations |
|---|---|
| Requests | Create/get/delete SAC requests; approve/reject/extend/cancel; resend notifications; list active/past requests by org; get counts |
| UserAccess | Check user access (`/check`); get user access details; revoke access |
| UserGroups | CRUD SAC user groups; manage product assignments |
| Products | Register/list/delete SAC products |
| Users | Get products a user has access to via SAC |
| Reindex | Trigger reindex of products or user groups |

**SAC agent hand-off:** For SAC workflow, configuration, and conceptual questions, see the dedicated SAC Foundry agent: https://docs.tylerdev.io/ops/support-access-center/

---

## tcp-support-accounts-api

**Purpose:** Provisions, activates, and deactivates Tyler support user accounts within a customer's Okta tenant — enabling Tyler support staff to access customer environments for troubleshooting.

**Auth:** JWT Bearer token
**Externally available:** No | **Usable by app teams:** Yes (ERP division only)
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-support-accounts-api/tcp-support-accounts-api

**Key operations:**

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/SupportAccounts/Customers` | List all Okta tenants / customers (paged) |
| GET | `/api/v1/SupportAccounts/{crmId}` | Get all support accounts for a customer |
| POST | `/api/v1/SupportAccounts/{crmId}/Activate/{username}` | Prepare Okta tenant for support accounts; create/activate a support account |
| POST | `/api/v1/SupportAccounts/{crmId}/Deactivate/{username}` | Reset password and deactivate a support account |
| POST | `/api/v1/SupportAccounts/Deprovision/{crmId}` | Remove all support account resources from a customer's Okta tenant |

**SAC agent hand-off:** For SAC workflow and support access concepts, see the dedicated SAC Foundry agent: https://docs.tylerdev.io/ops/support-access-center/

---

## tcp-user-import-api

**Purpose:** Bulk imports users into an organization in TCP — accepts an import job, processes records asynchronously, and exposes status/summary/error endpoints for monitoring the import progress.

**Auth:** JWT Bearer token
**Externally available:** No | **Usable by app teams:** No
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-user-import-api/tcp-user-import-api

**Key operations:**

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/ImportUsers/{organizationKey}` | Start a user import job for an org |
| GET | `/api/v1/ImportUsers/{organizationKey}` | List all import jobs for an org |
| GET | `/api/v1/ImportUsers/{organizationKey}/pending` | Get pending import jobs |
| GET | `/api/v1/ImportUsers/{organizationKey}/running` | Get running import jobs |
| GET | `/api/v1/ImportUsers/{organizationKey}/error` | Get failed import jobs |
| DELETE | `/api/v1/ImportUsers/{organizationKey}/error` | Clear failed import records |
| GET | `/api/v1/ImportUsers/{organizationKey}/summary` | Get summary of import results |

---

## tcp-webhook-api

**Purpose:** Manages TCP webhook subscriptions — allows services and app teams to register subscriptions to TCP-produced event message types, and provides cache management for webhook registrations.

**Ingress:** `{BASE_URL}/api/tcp-webhook-api`
**Auth:** JWT Bearer token (restricted domain management requires specific permissions)
**Externally available:** Yes | **Usable by app teams:** Yes
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-webhook-api/tcp-webhook-api

**Key operations:**

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/MessageTypes` | List available webhook message types |
| POST | `/api/v1/Registrations/subscribe` | Subscribe to a webhook (upsert) |
| GET | `/api/v1/Registrations/{referenceId}` | Get subscription by reference ID |
| GET | `/api/v1/Registrations/search` | Search subscriptions by message type |
| DELETE | `/api/v1/Registrations/unsubscribe/{referenceId}` | Unsubscribe by reference ID |
| POST | `/api/v1/Cache/rebuild` | Rebuild the webhook registration cache |
| GET/POST/DELETE | `/api/v1/RestrictedDomains` | Manage restricted webhook endpoint domains (`read/create/delete:webhookrestricteddomains`) |

---

## tid-c-service

**Purpose:** Tyler Identity Community (TID-C) service — manages community identity infrastructure including IdP (identity provider) app client registrations, community user profiles, self-service account operations, staged users, and admin/manager user operations for the community auth model.

**Ingress:** `{BASE_URL}/tid/tid-c-service`
**Auth:** Varies by API group (see below)
**Externally available:** Yes | **Usable by app teams:** Varies by API
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tid-c-service/tid-c-service

**Auth model by group:**

| API Group | Auth required |
|---|---|
| Manager | Workforce bearer token with group access |
| Profile | User's own bearer token |
| User | Workforce bearer token |
| App (IdpAdmin) | Workforce bearer token |

**Key operation groups:**

| Group | Purpose |
|---|---|
| IdpAdmin | Manage IdP app clients (CRUD), client secrets and certificates, groups, workforce profile integration; search apps |
| Manager | Search users; get user details; send verification code/password reset/unlock/unblock emails; reset MFA; resend activation; view user activity (sign-in, email, access) |
| Profile | Get/update/delete own profile; manage password, MFA factors, email update; view activity; recent communities; federated check |
| SelfService | Create/update user without auth; check email exists; send verification/reset/unlock emails |
| User | Get/create/update users with Workforce token |
| StagedUsers | Manage staged (pre-activation) user records and factors |
| Proofing | Identity proofing score and workflow |

**Identity agent hand-off:** For conceptual/workflow questions about TID-C and the community identity system, see the Identity Foundry agent: https://docs.tylerdev.io/identity

---

## tid-identity-configuration-api

**Purpose:** Write API for identity configuration key-value settings — allows authorized services to set, update, and delete identity configuration values used by the TCP identity layer.

**Auth:** Not explicitly specified (internal use, app-team accessible)
**Externally available:** No | **Usable by app teams:** Yes
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tid-identity-configuration-api/tid-identity-configuration-api

**Key operations:**

| Method | Path | Purpose |
|---|---|---|
| POST | `/` | Set multiple config values (bulk) |
| DELETE | `/` | Delete multiple config values (bulk) |
| GET | `/kv/{key}` | Get config KV pair by key |
| GET | `/{key}` | Get config value by key |
| POST | `/{key}` | Set a config value by key |
| DELETE | `/{key}` | Delete a config value by key |

**Identity agent hand-off:** For questions about what identity configuration values mean and how they affect behavior, see the Identity Foundry agent: https://docs.tylerdev.io/identity

---

## tid-identity-configuration-lookup-api

**Purpose:** Read-only API for retrieving identity configuration values — intended for app teams needing to look up identity configuration settings at runtime without write access.

**Auth:** API Key
**Externally available:** Yes | **Usable by app teams:** Yes
**Docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tid-identity-configuration-lookup-api/tid-identity-configuration-lookup-api

**Key operations:**

| Method | Path | Purpose |
|---|---|---|
| GET | `/kv/{key}` | Get config KV pair by key |
| GET | `/{key}` | Get config value by key |

**Identity agent hand-off:** For questions about what these configuration values control, see the Identity Foundry agent: https://docs.tylerdev.io/identity

---

## Notes for the chatbot

1. **Always cite the service-specific section** when directing an engineer to an API. The service index table is your first stop; use the "I need to…" routing table for intent-to-service matching.

2. **"Externally available" vs "Usable by app teams"** are distinct. A service can be externally reachable (`true`) but still restricted to platform-internal callers (`false` for app teams). Check both flags before advising an app team to call a service directly.

3. **tcp-platform-service is the most comprehensive API** — it covers orgs, workspaces, products, profiles, user groups, cohorts, features, and releases all in one. When a question could be answered by multiple APIs, tcp-platform-service is usually the correct canonical source.

4. **tcp-omni-service, not tcp-service-url-api, for navigation links.** The service URL API is an internal data store; the omni service is the correct read API for launcher/navigation intents.

5. **Three dedicated agents exist** — SAC (`tcp-support-access-center-api`, `tcp-login-security-api`, `tcp-support-accounts-api`, `tcp-notifications-api` for SAC emails), Identity (`tid-*`, `tcp-identity-events-api`, `tcp-credential-template-api`), and Ops Center. Include a one-line pointer to those agents for conceptual/workflow questions even when you answer an API-specific question from this catalog.

6. **Ingress BASE_URL is environment-specific.** Production is `https://api.tylerportico.com`; QA is `https://api.tcpqa.com`; CI is `https://api.tcpci.com`. The swagger docs use `{BASE_URL}` or `{{BASE_URL}}` as a placeholder.

7. **All APIs use JWT Bearer token auth** except `tcp-service-url-api` and `tid-identity-configuration-lookup-api` which use API Key auth. When an engineer asks about auth, specify both the header format (`Authorization: Bearer {token}`) and whether the token must be Workforce or user-scoped based on the service.

8. **Permissions follow `action:resource` format** (e.g. `create:auditlog`, `update:authorizationrole`). When an engineer gets a 403, ask them to verify the permission name against the endpoint's Required Permissions field in this catalog.

9. **Upload patterns** (branding images, bulk licensing CSVs) all follow the same pattern: request a presigned S3 URL → upload to S3 → call a "publish" or "process" endpoint. Don't skip the publish step.

10. **This catalog is generated from OpenAPI specs.** If an endpoint is missing or has changed, direct the engineer to the live Blueprint docs at the `Docs:` URL in each section, as those render the live swagger for the most current schema.
