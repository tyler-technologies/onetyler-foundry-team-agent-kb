# Ops Center Adoption — Integration Guide for Deployment Tools

**Source**: Blueprint Docusaurus, `https://docs.tylerdev.io/app-guides/ops/ops-center/adoption/`
**Domain**: Ops Center (Tyler Cloud Platform)
**Audience**: Engineers / owners of **other Tyler deployment / ops tools** that need to integrate with Ops Center as the system of record for Organizations, Workspaces, Products, Licensing, and Availability. Tyler-internal, but publicly addressable on the Blueprint Docusaurus site.

This is the canonical reference for **how to integrate with Ops Center via API** — which API to call for which construct, what permissions are required, the difference between Licensing and Availability, the workspace key rules, the Internal vs Customer/External Organization lifecycle split, and the webhook events to subscribe to in place of polling.

## Companion documents (within this corpus)

- `Docusaurus-OpsCenter.md` — Ops Center **product / process reference** (how the screens work, wizards, AD Agent, federation, Bulk Licensing, Permissions, Telemetry). Use that when the user is operating Ops Center through the UI; use **this** file when the user is integrating with Ops Center via API.
- `Docusaurus-Terminology.md` — canonical TCP glossary. Disambiguates Licensing↔Availability, Customer↔Organization, Tenant↔Workspace, Workforce Direct↔Managed↔Delegated, etc. This file's *Terminology* section maps API field-name synonyms; the glossary covers the broader vocabulary.
- `GitHub-TCPWebhookApi.md` — the full catalog of all 25 webhook event types across 6 domains. **This** file only enumerates the Org / Workspace / Product webhook events relevant to adoption; the GitHub file has the complete listing including Identity, Support Access, and User Group events.
- `Docusaurus-ProductRegistration.md` — what a registered product is, app types (Ops/Workforce/Admin/Community), PM/PjM preparation checklist. Useful upstream context when the integrating tool needs to know how products get registered before they can be licensed.
- `Conf-EnvironmentsAndAllowListing.md` — canonical environments + firewall allow-listing. The *Environments and authentication* section below names the three API hosts; that file is the source of truth for egress IPs and broader env metadata.

## Quick lookup — "Use when…" routing

| User intent | Section to retrieve |
|---|---|
| "How do I list Organizations / Workspaces from my deployment tool?" | [Listing Ops Center Organizations and Workspaces](#listing-ops-center-organizations-and-workspaces) — use **TCP Search API**, not Provisioning. |
| "What API do I call to license a product to an Org?" | [Licensing (Organization level)](#licensing-organization-level) on Provisioning v2. |
| "What's the difference between licensing a product and making it available?" | [Licensing and Availability](#licensing-and-availability) — Org-level vs Workspace-level, two-stage model. |
| "How do I make a licensed product available on a workspace?" | [Availability (Workspace level)](#availability-workspace-level) — prefer the `/by-registrationid` variant. |
| "What are the rules for a workspace key (`urlPrefix`)?" | [Workspace key rules](#workspace-key-rules). |
| "How do I create a workspace?" | [Creating Workspaces](#creating-workspaces) for Customer/External Orgs; [Create Workspace (Internal Org)](#create-workspace-internal-org) for Internal Orgs. |
| "Can my deployment tool delete a customer workspace?" | **No.** [Workspace deletion (Customer / External Orgs)](#workspace-deletion-customer--external-orgs) — must go via OneTyler support ticket. |
| "How do I create / deactivate / delete an Internal Org?" | [Internal Organization Lifecycle Management](#internal-organization-lifecycle-management) — requires `manage:internalorganization` on the JWT. |
| "How do I deactivate / reactivate a workspace on an Internal Org?" | [Deactivate / Activate Workspace (Internal Org)](#deactivate-activate-workspace-internal-org) — on the **TCP Platform Service**, not Provisioning. Uses **numeric workspace id**. |
| "What webhook do I subscribe to instead of polling for changes?" | [Webhooks](#webhooks) — TCP Webhook API; subscribe per event type. |
| "What's the synonym for `customerId` / `urlPrefix` / `portalId` in this other API?" | [Terminology](#terminology) field-name synonym map. |
| "Which environment host do I hit?" | [Environments and authentication](#environments-and-authentication). |

## Non-obvious traps the chatbot must surface

1. **`organizationId` (numeric internal id) ≠ Organization key (`customerId`).** Several Provisioning v2 endpoints take the numeric id, not the key. The Search API and most Tenant endpoints take the key. See [Terminology](#terminology). Confusing the two will produce 404s or wrong-record reads.
2. **Bulk Licensing and Bulk Availability POSTs are DECLARATIVE (set-style).** The body is the **complete desired set** — anything currently licensed/available but missing from the body **will be unlicensed / made unavailable**. Callers that just want to add one product must GET the current set first, append, and resend the full list. This is the single most common foot-gun in the API.
3. **Licensing is async.** `POST .../products` returns `202 Accepted`; the change is applied in the background. A follow-up `GET .../products` may not immediately reflect the change. Poll, or subscribe to the relevant webhook.
4. **Availability prerequisite.** A product must be **licensed to the Org** before it can be made **available on a workspace**. Trying to make an unlicensed product available returns `400`.
5. **Workspace deletion / deactivation on Customer (External) Orgs is forbidden from external tools.** Regardless of held permissions, the Provisioning v2 DELETE Tenant endpoints and the Platform Service status PUT must **not** be called against customer workspaces from a deployment tool — route through a OneTyler support ticket. The same applies to all Customer-Org lifecycle changes.
6. **`manage:internalorganization` is a section-wide governance gate.** Every Internal-Org operation (create / deactivate / activate / delete the Org, plus create / deactivate / activate / delete workspaces on Internal Orgs) requires this permission **in addition to** the base CRUD permission on the underlying API. Without it, **no** Internal-Org operation succeeds.
7. **`identityType: Managed` cannot be provisioned via API.** It is a valid `WorkforceIdentityType` enum value but is only provisioned through a OneTyler Support ticket with strong business justification. External tools must not send it.
8. **Production workspace key rules are tight.** For `portalType: Production` the workspace key must equal `<orgKey>` exactly — no hyphen, no suffix, and at most **one Production workspace per Organization**. For `NonProduction`, the suffix rules differ for Customer (enumerated set) vs Internal (any `[a-z0-9]{1,20}`) orgs. See [Workspace key rules](#workspace-key-rules).
9. **`expirationDate`, `licensedProducts` (by name), `availableProducts` (by name) are deprecated.** Use the `*RegistrationIds` array variants. The `/by-registrationid` availability variant is preferred over the by-name variant.
10. **Reuse before create.** Before creating a new workspace, **always** check whether the Org already has a workspace for the intended business purpose. Production keys collide on the first create; non-production workspaces accumulate cruft if the integrating tool doesn't dedupe.

---

## Introduction

This guide is intended for owners of other Tyler deployment tools who want to integrate with Ops Center's core constructs — **Organizations**, **Workspaces**, **Products**, **Licensing**, and **Availability**. It describes the supported integration points, the data shapes you can expect, and the workflows that keep your tool aligned with Ops Center as the system of record.

### Terminology

The same logical identifier appears under different field names depending on which API or message payload you are looking at. The table below maps the synonyms to the canonical concept:

| Concept | Field names across APIs / payloads | Type | Notes |
|---|---|---|---|
| Organization key | `customerId`, `OrganizationKey`, `organizationKey`, `Key`, "Org key" | string | Human-readable Org identifier (e.g. `cityofmobileal`). Used everywhere the API takes a "by-key" filter. |
| Organization type | "Customer Org" / "External Org" (`isInternal == false`); "Internal Org" (`isInternal == true`) | classification | **"Customer" and "External" are used interchangeably** throughout this guide to refer to Organizations representing real Tyler customers. "Internal" refers to Tyler-owned demo / test / operational Organizations. |
| Organization id (internal) | `organizationId` (path parameter on certain Provisioning v2 endpoints) | integer | **Internal numeric** id, **distinct from the Organization key**. Required by the single-record and licensing endpoints on `/api/v2/Organization/{organizationId}/...`. |
| CRM account id | `crmId` | string (GUID) | GUID of the matching CRM Dynamics account record. |
| Tyler id (CRM) | `tyl_id` | integer (≤ 6 digits) | Tyler-internal id from CRM. Planned addition to the Search index. |
| Workspace key | `urlPrefix`, `WorkspaceKey`, `workspaceKey`, `portalId`, "workspace key" | string | Workspace / tenant identifier (e.g. `cityofmobileal-test`). |
| Workspace id (internal) | `id` (on `Portal` / `PortalInfo`); `defaultProductionWorkspaceId` (on `CreateOrganizationResponse`); the numeric `{id}` path param on the TCP Platform Service workspace endpoints | integer | **Internal numeric** workspace id, **distinct from the workspace key**. Required by the TCP Platform Service workspace status endpoint used to deactivate / reactivate a workspace. |
| Workspace type | `portalType`, `WorkspaceType`, `Type` | string enum | `Production` or `NonProduction`. |
| Product registration id | `productRegistrationId`, `RegistrationId`, `registrationId` | string | Stable product identifier (e.g. `financials-erp`). |

### Environments and authentication

Each API documented below is reachable on one of three environment hosts:

| Environment | Host | Use |
|---|---|---|
| Production (`tylerportico`) | `https://api.tylerportico.com` | Used for all things customer facing including customer environments, customer facing demos, product-adjacent support and testing use cases. |
| QA (`tcpqa`) | `https://api.tcpqa.com` | Heavily used for pre-release testing, support, training, documentation, Tyler internal demos and for automated provisioning of environments for sales. |
| CI (`tcpci`) | `https://api.tcpci.com` | Used primarily by developers to test their integrations. |

A copy of the Ops Center core constructs exists in each of these environments. It is expected that the integrating ops tool has a corresponding Dev / QA / Production instance reading from TCPCI / TCPQA / TylerPortico respectively. The ops tool may alternatively provide an explicit environment-selection option, letting the user pick one Ops Center environment as the reference.

The per-API ingress path appends to the host:

| API | Ingress | Swagger reference |
|---|---|---|
| TCP Search API | `/platform/search` | `https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-search-api/` |
| TCP Provisioning Service v2 | `/portal/provisioning` | `https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-provisioning-service/?version=v2` |
| TCP Platform Service | `/portal/platformservice` | `https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-platform-service/` |
| TCP Webhook API | `/api/tcp-webhook-api` | `https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-webhook-api/` |

All endpoints require a **JWT bearer token** with the relevant scopes / permissions called out in each section below. A representative request — looking up a tenant by key in CI — looks like:

```bash
curl -X GET "https://api.tcpci.com/portal/provisioning/api/v2/Tenants/cityofredmondwa-test" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/json"
```

For a `POST`/`PUT` that takes a JSON body (e.g. creating a workspace):

```bash
curl -X POST "https://api.tcpci.com/portal/provisioning/api/v2/Tenants" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @workspace.json
```

## Listing Ops Center Organizations and Workspaces

**Use when:** enumerating or searching Ops Center Organizations or Workspaces from a deployment tool.

Integrating tools enumerate Ops Center Organizations and Workspaces through the **TCP Search API**. The full Swagger reference (request/response schemas, error codes, auth) is here:

- Swagger: `https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-search-api/`
- Ingress: `{BASE_URL}/platform/search`
- Auth: JWT (the `tyler-cloud-platform-api-access` scope)

Two endpoints are relevant for adoption:

| Purpose | Method & Path | Operation |
|---|---|---|
| List/search Organizations | `POST /api/v1/Search/organizations` | `Search_OrganizationSearch` |
| List/search Workspaces | `POST /api/v1/Search/workspaces` | `Search_WorkspaceSearch` |

Both endpoints accept a JSON body. Any property left unset is treated as "no filter." Combine properties to AND filters together.

### Search Organizations — payload options

`POST /api/v1/Search/organizations` — request body (`OrganizationSearchParams`):

| Field | Type | Purpose |
|---|---|---|
| `id` | string | Exact match on the internal Organization id. |
| `key` | string | Exact match on the Organization key (`customerId`, e.g. `cityofmobileal`). |
| `name` | string | Exact match on the Organization display name. |
| `allowTylerSupportAccess` | boolean | Filter by the Organization's Tyler Support access toggle. This is a customer-set value indicating how the Organization handles Tyler Staff access requests to its installations: **enabled** (`true`) means access requests are auto-approved, **disabled** (`false`) means each request must be manually approved by the customer. |
| `inactive` | boolean | `true` returns inactive orgs only; `false` returns active orgs only; omit for both. |
| `excludeOrganizationKeys` | string[] | Org keys to exclude from results. |
| `fullTextSearch` | string | Free-form query across indexed fields — see [Full-text search](#full-text-search-opensearch-query-string-syntax) below. |
| `skip`, `take` | integer | Page offset and page size. |
| `searchAfter` | object | Cursor for deep pagination — pass back the `searchAfter` value returned by the previous page. |

Response shape: `{ documents: Organization[], total: number, searchAfter: OrganizationSearchAfter | null }`. Each `Organization` document includes `id`, `key`, `name`, `allowTylerSupportAccess`, `inactive`, and a `timestamp` for the indexed version.

### Search Workspaces — payload options

`POST /api/v1/Search/workspaces` — request body (`WorkspaceSearchParams`):

| Field | Type | Purpose |
|---|---|---|
| `id` | string | Exact match on the internal Workspace id. |
| `key` | string | Exact match on the Workspace key (`portalId`, e.g. `cityofmobileal-test`). |
| `agencyTitle` | string | Exact match on the workspace's display title. |
| `organizationKey` | string | Restrict results to one Organization (its `customerId`). |
| `workspaceType` | string | Filter by type (e.g. `Production`, `NonProduction`). |
| `onPremTarget` | string | Filter by on-prem deployment target. |
| `excludeOrganizationKeys` | string[] | Skip workspaces belonging to these org keys. |
| `excludeWorkspaceKeys` | string[] | Skip these specific workspace keys. |
| `fullTextSearch` | string | Free-form query — see [Full-text search](#full-text-search-opensearch-query-string-syntax) below. |
| `skip`, `take` | integer | Page offset and page size. |
| `searchAfter` | object | Cursor for deep pagination. |

Response shape: `{ documents: Workspace[], total: number, searchAfter: WorkspaceSearchAfter | null }`. Each `Workspace` document includes `id`, `key`, `agencyTitle`, `organizationKey`, `workspaceType`, `onPremTarget`, `activeUserCount`, `activeProductCount`, and a `timestamp`.

### Full-text search (OpenSearch query string syntax) {#full-text-search-opensearch-query-string-syntax}

The `fullTextSearch` field on both endpoints is the most flexible way to find Organizations and Workspaces. The Search API is backed by **OpenSearch**, and the value is interpreted as an **OpenSearch query string** — see the OpenSearch query string query reference (`https://opensearch.org/docs/latest/query-dsl/full-text/query-string/`) for the full grammar (field-qualified terms, boolean operators, wildcards, ranges, required/excluded terms).

When `fullTextSearch` is combined with the structured fields above (e.g. `organizationKey` + `fullTextSearch`), the API ANDs them together — the structured filters narrow the candidate set, and the full-text query applies on top.

#### Fields available today for Organization search

For the `Search/organizations` endpoint, the following fields are queryable via `fullTextSearch` today using OpenSearch query string syntax:

| Field | Example |
|---|---|
| `Key` | `Key:cityofmobileal` · `Key:cityof*` |
| `Name` | `Name:"City of Mobile"` · `Name:Mobile*` |
| `Active` | `Active:true` · `Active:false` |
| `AllowTylerSupportAccess` | Customer-set: `true` = auto-approve Tyler Staff access requests; `false` = require manual approval per request. Example: `AllowTylerSupportAccess:true` |

These can be combined with boolean and grouping operators, e.g.:

```text
Active:true AND AllowTylerSupportAccess:true AND Name:City*
```

#### Fields planned for Organization search

The following attributes are planned to be added to the Organization search index in the near future. They will be sourced from the matching CRM account record so that deployment tools can correlate Ops Center Organizations with their CRM record and address metadata directly from a Search API call:

| Field | Source on the CRM account record | Example query |
|---|---|---|
| `tyl_id` | Tyler Id of the CRM account record. Numeric, up to 6 digits (e.g. `1`, `300`, `487790`). | `tyl_id:487790` · `tyl_id:[1 TO 999999]` |
| `state` | `address1_state` | `state:AL` |
| `city` | `address1_city` | `city:"Mobile"` |
| `county` | `address1_countyorparish` | `county:"Mobile County"` |
| `country` | `address1_country` | `country:"United States"` |
| `accountNumber` | Account number on the CRM record, when present directly on the record | `accountNumber:0012345` |
| `crmId` | GUID of the CRM account record | `crmId:00000000-0000-0000-0000-000000000000` |

Once the `crmId` is indexed, integrating tools can construct a direct deep link to the CRM account record using the value returned in search results:

```text
https://tylertech.crm.dynamics.com/main.aspx?appid=9dd3fdde-926b-41be-ad0f-b477ad88356b&forceUCI=1&newWindow=true&pagetype=entityrecord&etn=account&id={crmId}
```

Substitute `{crmId}` with the GUID returned in the Organization document.

### Pagination

For result sets larger than a single page, paginate with `skip`/`take` for shallow paging or with `searchAfter` (cursor) for deep paging. The `searchAfter` value returned in the response should be echoed back in the next request's `searchAfter` field unchanged.

### Autocomplete endpoints

For type-ahead UIs, the Search API also exposes prefix-matching endpoints:

- `GET /api/v1/Search/organizations/autocomplete/{search}`
- `GET /api/v1/Search/workspaces/autocomplete/{search}`

These return a lightweight match list and are intended for interactive lookups, not bulk enumeration.

### Alternative: Provisioning Service v2 (single-record lookups)

The **Provisioning Service v2** API also exposes Organization and Workspace data. It reads from the system-of-record directly rather than an index, which makes it **noticeably less performant than the Search API** — it is **not** recommended for list/enumeration workloads. It is appropriate when:

- You already know a single Organization key (`customerId`) or Workspace key (`urlPrefix`) and just need the canonical record details.
- You need to combine retrieval with a follow-up write (e.g. read the org, then create a workspace) and want to stay on the same API surface — see the [Creating Workspaces](#creating-workspaces) section below, which uses `POST /api/v2/Tenants` on this same API.

Reference:

- Swagger (v2): `https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-provisioning-service/?version=v2`
- Ingress: `{BASE_URL}/portal/provisioning`
- Auth: JWT — `read:organization` for Organization lookups, `read:workspace` for Tenant (Workspace) lookups.

#### Get Organization details

`GET /api/v2/Organization` — returns a paged list of Organizations (`PagedOrganizations`). Useful for a single-org lookup when combined with the filter parameters below.

| Query parameter | Type | Purpose |
|---|---|---|
| `organizationIdQueryFilter` | string | Filter on Organization **key** (`customerId`). Despite the parameter name, this matches against the key (not the internal id). |
| `organizationNameQueryFilter` | string | Filter on Organization display name. |
| `internalFilter` | enum | `None` (default), `Internal`, or `External` — restrict to internal or external organizations only. |
| `excludeInactive` | boolean | When `true`, omit inactive organizations. Defaults to `false`. |
| `sortBy` | enum | `CustomerId` (default) or `CrmId`. |
| `sortDirection` | enum | `ASC` (default) or `DESC`. |
| `offset`, `limit` | integer | Standard offset/limit paging. |

For a single org by **numeric internal id**, the dedicated record endpoint `GET /api/v2/Organization/{organizationId}` is also available. Note that `{organizationId}` is the **internal numeric** Organization id — it is **not** the same as the Organization key (`customerId`). Most adoption-tool callers should prefer the keyed list endpoint above with `organizationIdQueryFilter={orgKey}` rather than trying to construct a path with the numeric id.

The `Organization` document fields most useful for adoption-tool correlation are:

| Field | Type | Notes |
|---|---|---|
| `customerId` | string | The Organization key (e.g. `cityofmobileal`). |
| `name` | string | Display name. |
| `crmId` | string | GUID of the matching CRM account record. |
| `customerAccount` | string | Account number from CRM, when present. |
| `isInternal` | boolean | `true` for Tyler-internal / demo / test orgs. |
| `allowAdminCenterSupportAccess` | boolean | Same value as `allowTylerSupportAccess` on the Search API — the customer-set Tyler Staff auto-approve toggle (`true` = auto-approve, `false` = require manual approval). |
| `delegatedOrganizationKey` | string | Key of the parent Organization that maintains the Identity setup and user store for this org. Null when the org manages its own identity. |

Additional branding, contact, email-domain, and whitelisting fields are also returned — see the Swagger reference linked above for the full schema.

#### Get Workspace (Tenant) details

`GET /api/v2/Tenants` — returns an array of `TenantData`. Filter to a single org's workspaces using `customerId` (the org filter).

| Query parameter | Type | Purpose |
|---|---|---|
| `customerId` | string | Organization key — restricts results to workspaces belonging to this Organization. |
| `customerAccount` | uint64 | CRM account number, as an alternative org filter when the org key isn't known. |
| `query` | string | Wildcard filter on the workspace key (`urlPrefix`). Wildcard matching against workspace keys is the documented use today. |

For a single workspace by key, use `GET /api/v2/Tenants/{urlPrefix}`.

The `TenantData` fields most useful for adoption-tool correlation are:

| Field | Type | Notes |
|---|---|---|
| `urlPrefix` | string | The Workspace key / subdomain (e.g. `cityofmobileal-test`). |
| `agencyTitle` | string | Workspace display title. |
| `customerId` | string | Owning Organization key. |
| `customerAccount` | uint64 | Owning Organization's CRM account number. |
| `portalType` | string | Largely **legacy / deprecated**. Today only `Production` and `NonProduction` are used. By convention Production workspace keys equal `{orgKey}` and NonProduction keys follow `{orgKey}-{test`\|`train`\|`staging`\|`uat`\|`dev`\|`impl}` — though many existing workspace keys do not strictly follow this template. |
| `licensedProductRegistrationIds` | string[] | Registration IDs of products licensed to this workspace. |
| `availableProductRegistrationIds` | string[] | Registration IDs of products available to this workspace. |

Homepage link/title, business/technical contact details, and `usesCustomerLinks`/`usesCustomerContacts` flags are also returned — see the Swagger reference linked above. The `licensedProducts` and `availableProducts` arrays (product **names**) plus the `expirationDate` field are returned for backwards compatibility but are **deprecated** — use the `*RegistrationIds` arrays instead and ignore `expirationDate`.

## Licensing and Availability

**Use when:** entitling an Org to a product, or making a product usable on a workspace.

Ops Center models product adoption as a **two-stage** process:

| Stage | Scope | Meaning |
|---|---|---|
| **Licensing** | Organization | The Org's **entitlement** to a product. Licensing alone does not install the product anywhere — it just authorizes the Org to use it. |
| **Availability** | Workspace (Tenant) | Makes a licensed product **usable** on a specific workspace. Until a licensed product is made available on at least one of the Org's workspaces, the Org effectively does not have the product installed. |

It is valid (and common during onboarding) to license a product to an Org without making it available on any workspace yet. Conversely, you cannot make a product available on a workspace whose Org does not first hold a license for that product.

Both surfaces are exposed on the **Provisioning Service v2** API.

- Swagger (v2): `https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-provisioning-service/?version=v2`
- Ingress: `{BASE_URL}/portal/provisioning`

### Licensing (Organization level)

Licensing endpoints operate on the Organization. All product references are by **`productRegistrationId`** (not product name).

**Path parameter note:** `{organizationId}` in the table below is the **internal numeric** Organization id — **distinct from** the Organization key (`customerId`). See the [Terminology](#terminology) table above.

| Purpose | Method & Path | Permission | Response | Reference |
|---|---|---|---|---|
| List products licensed to an Org | `GET /api/v2/Organization/{organizationId}/products` | `read:product` | `200` — `PagedOrganizationProducts` | `Organization_GetProductsByCustomerId` |
| **Set** the Org's licensed product list (any currently-licensed product **not** in the body is unlicensed) | `POST /api/v2/Organization/{organizationId}/products` | `licenseproduct:organization`, `unlicenseproduct:organization` | `202 Accepted` | `Organization_LicenseProducts` |
| Unlicense a single product from an Org | `POST /api/v2/Organization/{organizationId}/unlicenseproduct/{productRegistrationId}` | `unlicenseproduct:organization` | `202 Accepted` | `Organization_UnLicenseProduct` |

**Set-style semantics on the bulk POST.** The `POST .../products` endpoint is **declarative** — the JSON body is the complete desired set of licensed `productRegistrationId`s. Anything currently licensed but missing from the body **will be unlicensed**. Callers that just want to add one product to an existing license set must first GET the current list, append, and PUT back the full set (or use the single-product endpoints).

**Asynchronous processing.** Both write endpoints return `202 Accepted` — the change is applied in the background. Integrating tools should not assume that a subsequent `GET .../products` immediately reflects the change; poll the GET until the desired state appears (or rely on the appropriate event/notification surface for licensing changes).

Request body for the bulk POST is a plain JSON array of registration ids:

```json
["financials-erp", "permitting", "civic-access"]
```

Response from the GET is `PagedOrganizationProducts`:

```json
{
  "products": [
    {
      "name": "Financials ERP",
      "registrationId": "financials-erp",
      "description": "…",
      "tylerComponentsWebIconName": "…"
    }
  ],
  "totalCount": 1
}
```

### Availability (Workspace level)

Availability endpoints operate on a specific workspace (identified by its `urlPrefix`). Like the bulk licensing POST, they are **declarative** — the body is the complete desired set, and any product currently available but missing from the body is made unavailable.

| Purpose | Method & Path | Body type | Permission | Response | Reference |
|---|---|---|---|---|---|
| Set available **products** on a workspace, by product **name** | `PUT /api/v2/Tenants/{urlPrefix}/products` | `string[]` of product **names** | `create:appavailability` | `204 No Content` | `Tenants_PostTenantAvailableProducts` |
| Set available **products** on a workspace, by **registration id** *(preferred)* | `PUT /api/v2/Tenants/{urlPrefix}/products/by-registrationid` | `string[]` of `productRegistrationId`s | `create:appavailability` | `204 No Content` | `Tenants_PostTenantAvailableProductsByRegistrationId` |
| Set available **apps** (sub-components of products) on a workspace | `PUT /api/v2/Tenants/{urlPrefix}/apps` | `string[]` of `appRegistrationId`s | `create:appavailability` | `204 No Content` | `Tenants_PostTenantAvailableApps` |

**Prefer `/products/by-registrationid`.** Both product endpoints have identical declarative semantics, but the by-registration-id variant aligns with the rest of this guide (and with the Org-level Licensing endpoints, which are always by registration id). The by-name variant is retained for legacy callers.

**Reading current availability.** There is no dedicated GET on the `/products` or `/apps` sub-paths. The current availability for a workspace is returned by the standard tenant lookup documented in the [Listing](#listing-ops-center-organizations-and-workspaces) section above:

- `GET /api/v2/Tenants/{urlPrefix}` → `TenantData.availableProductRegistrationIds`
- For licensed products on a workspace, `TenantData.licensedProductRegistrationIds` (the workspace's view of the Org's license list)

**Licensing prerequisite.** A product must be licensed to the workspace's owning Organization before it can be made available on that workspace. If the body of an availability PUT includes a product the Org is not licensed for, the call will fail (`400`).

Request body example for `PUT /api/v2/Tenants/cityofmobileal-test/products/by-registrationid`:

```json
["financials-erp", "permitting"]
```

This call makes exactly `financials-erp` and `permitting` available on the `cityofmobileal-test` workspace. Any other product previously available on that workspace will be set to unavailable.

## Creating Workspaces

**Use when:** an external deployment tool needs to provision a new workspace under a **Customer (External) Organization**. For Internal Orgs, see [Create Workspace (Internal Org)](#create-workspace-internal-org).

This section covers workspace creation on **Customer / External Organizations** (`isInternal == false`). For workspace creation, deletion, or any other lifecycle action against an **Internal Organization**, see [Internal Organization Lifecycle Management](#internal-organization-lifecycle-management) below — Internal and External flows are treated as independent concerns in this guide even though they share the same underlying API endpoints.

A **Workspace** represents a single business purpose for an Organization — for example *Production*, *Test*, *Training*, *Implementation*. The **workspace key** (`urlPrefix`) is Tyler's global tenant identifier: every product installed for a given business purpose must be associated with the appropriate workspace key, so that all product installations sharing a purpose share a single identity, license/availability context, and operational view.

### Reuse before create

Before creating a new workspace from an external deployment tool, **always check whether the Customer Organization already has a workspace for the intended business purpose** and associate the deployment with the existing workspace where possible. Use the listing endpoints documented earlier:

- Preferred: `GET /api/v2/Tenants?customerId={orgKey}` (Provisioning v2) — returns the full set of `TenantData` records for the Org, including each workspace's `portalType` (`Production` / `NonProduction`) and `agencyTitle`.
- Or the Search API workspace endpoint with `organizationKey={orgKey}` — see [Listing](#listing-ops-center-organizations-and-workspaces) above.

Only proceed with a create call if no suitable existing workspace is found.

### Endpoint

Workspace creation is a `POST /api/v2/Tenants` call on the Provisioning v2 API.

| Item | Value |
|---|---|
| Method & Path | `POST /api/v2/Tenants` |
| Body | `TenantDataCreate` |
| Permission | `create:workspace` |
| Response | `201 Created` — `PortalProvisionData` |
| Reference | `Tenants_Post` on `https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-provisioning-service/?version=v2` |

### Request body — `TenantDataCreate`

| Field | Required | Type / Constraints | Purpose |
|---|---|---|---|
| `urlPrefix` | **yes** | string, ≤ 50 chars; must satisfy the [workspace key rules](#workspace-key-rules) below | The workspace key (Tyler's global tenant identifier). |
| `agencyTitle` | **yes** | string, ≤ 255 chars | Display title for the workspace. |
| `customerId` | **yes** | string, ≤ 255 chars | The owning Customer Organization key. |
| `portalType` | **yes** | string — `Production` or `NonProduction` | The business-purpose category. Drives the hyphen rule on `urlPrefix`. |
| `customerAccount` | no | uint64 | CRM account number for the Org, when known. |
| `availableProductRegistrationIds` | no | string[] of `productRegistrationId`s | Products to make available on the new workspace at creation time. **Each must already be licensed** to `customerId` — see [Licensing and Availability](#licensing-and-availability). |
| `homePageLink`, `homePageTitle` | no | string, ≤ 255 chars each | Customer-supplied homepage link/title. |
| `businessContactName` / `Email` / `Phone` / `Extension` | no | string, ≤ 255 chars each | Business contact details. |
| `techContactName` / `Email` / `Phone` / `Extension` | no | string, ≤ 255 chars each | Technical contact details. |
| `usesCustomerLinks` | no | boolean | Whether the workspace surfaces customer-supplied links rather than Tyler defaults. |
| `usesCustomerContacts` | no | boolean | Whether the workspace surfaces customer-supplied contacts rather than Tyler defaults. |

Deprecated fields on the body: `licensedProducts` and `availableProducts` (string arrays of product **names**) — use `availableProductRegistrationIds` instead. `expirationDate` is also deprecated and can be omitted.

**Organization key prerequisite:** the `customerId` value must be alphanumeric and ≤ 50 characters. It is validated at Organization creation, and **re-validated against the same Organization on every workspace create** — a workspace cannot be created against an Org whose key fails these rules.

### Workspace key rules {#workspace-key-rules}

All rules below are **hard requirements** — the create call will be rejected if any rule is violated.

- **Full workspace key length** ≤ 63 characters.
- **If `portalType` is `Production`**: the workspace key must equal exactly `<orgKey>`.
  - At most **one Production workspace per Organization**.
- **If `portalType` is `NonProduction`**: the workspace key **must** use the format `<orgKey>-<suffix>`.
  - For internal orgs, the `<suffix>` must be `[a-z0-9]{1,20}` (alphanumeric up to 20 characters).
  - For customer orgs, the `<suffix>` must be one of an enumerated set `{test|train|staging|impl|uat|dev}`.
  - Suffix cannot be `admin` (case-insensitive) for either org type.

### Example payload

The following payload illustrates a non-production workspace creation against the External Org `cityofredmondwa`. Values in `{...}` indicate placeholder semantics; the inline `e.g.` comments show the concrete example:

```json
{
    "urlPrefix": "{workspace key rules}",                              // e.g. "cityofredmondwa-test"
    "agencyTitle": "{Production: Org Name; NonProduction: Org Name [Suffix]}", // e.g. "City of Redmond [Test]"
    "customerId": "{orgKey}",                                          // e.g. "cityofredmondwa"
    "portalType": "{Production | NonProduction}",                      // e.g. "NonProduction"
    "availableProductRegistrationIds": [
        "{product registration id to make available; array may be empty}"
    ],
    "homePageTitle": "{Org Name}",
    "usesCustomerLinks": true,
    "usesCustomerContacts": true
}
```

Conventions illustrated by this example:

- **`agencyTitle`**: for Production workspaces use the Organization's display name verbatim (e.g. `"City of Redmond"`); for Non-Production workspaces append a bracketed suffix label matching the business purpose (e.g. `"City of Redmond [Test]"`).
- **`availableProductRegistrationIds`** may be sent as an empty array (`[]`) — the workspace is then created with no products made available, and availability can be set later via `PUT /api/v2/Tenants/{urlPrefix}/products/by-registrationid`.
- **`usesCustomerLinks` / `usesCustomerContacts`**: set to `true` when the workspace should surface the customer's own links/contacts rather than Tyler defaults.

### Examples

| Org key | Workspace key | `portalType` | Valid? |
|---|---|---|---|
| `cityofmobileal` | `cityofmobileal` | `Production` | Yes |
| `cityofmobileal` | `cityofmobileal-test` | `NonProduction` | Yes |
| `cityofmobileal` | `cityofmobileal-staging` | `NonProduction` | Yes |
| `cityofmobileal` | `cityofmobileal-sandbox` | `NonProduction` | **No** — `sandbox` is not in the suffix enum |
| `cityofmobileal` | `cityofmobileal-test` | `Production` | **No** — Production keys cannot contain `-` |
| `cityofmobileal` | `cityofmobileal` | `NonProduction` | **No** — NonProduction keys must contain `-` |
| `cityofmobileal` | `mobile-test` | `NonProduction` | **No** — prefix must equal `<orgKey>` |

### Workspace deletion (Customer / External Orgs) {#workspace-deletion-customer--external-orgs}

External deployment tools **must not** call the Provisioning v2 DELETE Tenant endpoints against workspaces on Customer (External) Organizations. To deactivate or delete a Customer Organization's workspace, request the change through a **OneTyler support ticket** — Tyler operations performs the action through internal tooling on the customer's behalf. This restriction applies regardless of what permissions the calling client may otherwise hold.

### Response — `PortalProvisionData`

A successful create returns `201 Created` with a `PortalProvisionData` body:

| Field | Notes |
|---|---|
| `portalInformation` | A `PortalInfo` record with `urlPrefix` echoed back and a `portalConfiguration` (`Portal`) describing the newly-created workspace — `portalId`, `customerId`, `agencyTitle`, `type` (`PortalType` enum), `status` (`PortalStatus` enum, typically `Provisioning` → `Active`), `active`, contacts, etc. |
| `products` | The set of `Product` records made available at creation (matches the registration ids supplied in `availableProductRegistrationIds`). |
| `availableApps` | The corresponding `App` sub-components available on the workspace. |

`PortalStatus` values: `Unknown`, `Unprovisioned`, `Provisioning`, `Active`, `Error`. A freshly-created workspace will typically be returned in `Provisioning` and transition to `Active` once backend provisioning completes — integrating tools that depend on downstream readiness should poll `GET /api/v2/Tenants/{urlPrefix}` until the workspace reports `Active`.

### Post-create checklist for integrating tools

1. Verify `PortalStatus == Active` via `GET /api/v2/Tenants/{urlPrefix}` (or your subscribed event stream) before continuing.
2. If products were not provided at creation, license any required products at the Org level (see [Licensing](#licensing-and-availability)) and then make them available on the new workspace via `PUT /api/v2/Tenants/{urlPrefix}/products/by-registrationid`.
3. Record the returned workspace key (`urlPrefix`) as the canonical tenant identifier for the deployment — all subsequent product installations for the same business purpose must use this key.

## Internal Organization Lifecycle Management

**Use when:** creating, deactivating, activating, or deleting an Internal Org (or managing workspaces under one). For Customer/External Orgs, all lifecycle changes route through a OneTyler support ticket — none of these endpoints are available to external deployment tools against Customer Orgs.

This section is the home for everything **Internal Organization**-related on the Tyler Cloud Platform API surface — Org creation, deactivation, activation, and deletion, plus workspace creation, deactivation / reactivation, and deletion against Internal Orgs. **Customer / External Organization** operations are documented separately under [Listing](#listing-ops-center-organizations-and-workspaces), [Licensing and Availability](#licensing-and-availability), and [Creating Workspaces](#creating-workspaces). Internal and External flows are independent concerns even though they share the same underlying endpoints.

### Section-wide permission requirement

**Every operation in this section requires the calling client to hold the `manage:internalorganization` (Manage Internal Organization) permission on its JWT bearer token.** This is a hard prerequisite for the entire section, not a per-endpoint qualifier: without `manage:internalorganization`, **none** of the operations below — Org create / deactivate / activate / delete, workspace create / deactivate / activate / delete — are available to the caller, regardless of which underlying API the action routes through (Provisioning v2 or TCP Platform Service).

Per-endpoint tables below also list the **base CRUD permission** the underlying API enforces in addition (`create:organization`, `delete:organization`, `create:workspace`, `delete:workspace`, `update:workspace`). The `manage:internalorganization` requirement is in addition to these — both must be held.

**For Customer / External Organizations**, none of the operations below are available to external deployment tools. Org-level lifecycle changes and workspace deactivation / deletion for customer Organizations must always be routed through a **OneTyler support ticket**.

### Create Internal Organization

| Item | Value |
|---|---|
| Method & Path | `POST /api/v2/Organization` |
| Body | `CreateOrganizationRequest` |
| Required permissions | `create:organization` **and** `manage:internalorganization` |
| Response | `201 Created` — `CreateOrganizationResponse` |
| Reference | `Organization_CreateOrganization` on `https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-provisioning-service/?version=v2` |

#### Request body — `CreateOrganizationRequest`

The body has three top-level fields:

| Field | Required | Notes |
|---|---|---|
| `organization` | **yes** | The Organization payload — see [Organization fields](#organization-fields) below. |
| `identityType` | **yes** | Workforce identity strategy: **`Direct`** (default — self-managed identity) or **`Delegated`** (delegate authentication to an existing Org; **must also populate `organization.delegatedOrganizationKey`**). The `Managed` value exists in the `WorkforceIdentityType` enum but is **not selectable through this API** — see the warning below. |
| `orgAdmin` | no | Optional initial Org Admin (`OrgAdminConfiguration`). Adopters may omit this and add admins later through the dedicated Site Administrator endpoints. |

**Warning — `Managed` identityType is not API-provisionable:** The third `WorkforceIdentityType` enum value, **`Managed`** (an Internal Org backed by a pre-existing Okta tenant), is **only provisioned through a OneTyler Support ticket** and requires **strong business justification** to be approved. It cannot be selected through `POST /api/v2/Organization` or any other API path documented in this guide. External deployment tools must not attempt to send `identityType: Managed` — if a Managed-tenant Internal Org is required, raise a OneTyler Support ticket with the business case and Tyler operations will provision it through internal tooling.

##### Organization fields {#organization-fields}

The full `Organization` schema is shown below. Only `customerId`, `name`, and `isInternal: true` are strictly required for an Internal Org create — every other field is optional and can be set or updated post-create. When `identityType: Delegated` is used, `delegatedOrganizationKey` becomes conditionally required.

| Field | Type | Required at create | Notes |
|---|---|---|---|
| `customerId` | string | **yes** | The Internal Org key (e.g. `tylerdemo`). Alphanumeric, ≤ 50 chars. **Naming conventions:** Internal Org keys follow a structured `(3-char division/group code)(purpose code)(label)` format — see the Ops Center user guide section *Entering an Org Key* at `https://docs.tylerdev.io/app-guides/ops/ops-center/userguide/organizations/#entering-an-org-key`, which links to the authoritative naming convention reference. |
| `name` | string | **yes** | Display name. |
| `isInternal` | boolean | **yes** | Must be `true` for Internal Org creation in this section. |
| `delegatedOrganizationKey` | string | **when `identityType: Delegated`** | Org key of the parent Organization that maintains the Identity setup and user store for this Org. Leave null otherwise. |
| `crmId` | string (GUID) | no | GUID of the matching CRM account record, when applicable. |
| `customerAccount` | string | no | CRM account number, when applicable. |
| `allowAdminCenterSupportAccess` | boolean | no | Tyler Staff auto-approve toggle. |
| `usesWhitelisting` | boolean | no | Customer-set Okta IP allow-list opt-in (rarely set for Internal Orgs). |
| `customerEmailDomains` | string[] | no | Email domains belonging to the Org. |
| `organizationUrl`, `privacyUrl`, `termsUrl`, `portalContactUrl`, `homepageTitle` | string | no | Branding URLs / homepage title. |
| `contacts` | `CustomerContact[]` | no | Business / Technical contacts (`{ name, phone, email, type }`). |
| `created` | date-time | server-set | Populated by the server on create — do not send. |

##### `orgAdmin` fields (`OrgAdminConfiguration`)

When supplied, `orgAdmin` extends the basic `OrgAdmin` shape with optional magic-link configuration:

| Field | Type | Notes |
|---|---|---|
| `firstName`, `lastName`, `email`, `username` | string | Identifying details of the initial Org Admin. |
| `magicLinkConfiguration` | `CreateMagicLinkRequest` | Optional. `sendMagicLink: boolean` enables magic-link delivery; `creatorSub` / `creatorUsername` capture creator metadata. |

#### Example payloads

Minimal Internal Org create (`Direct` identity, no initial admin):

```json
{
  "organization": {
    "customerId": "tylerdemo",
    "name": "Tyler Demo",
    "isInternal": true
  },
  "identityType": "Direct"
}
```

Delegated identity (Identity setup lives on a parent Org):

```json
{
  "organization": {
    "customerId": "tylerdemo2",
    "name": "Tyler Demo 2",
    "isInternal": true,
    "delegatedOrganizationKey": "tylerdemo"
  },
  "identityType": "Delegated"
}
```

With an initial Org Admin and magic-link email:

```json
{
  "organization": {
    "customerId": "tylerdemo",
    "name": "Tyler Demo",
    "isInternal": true
  },
  "identityType": "Direct",
  "orgAdmin": {
    "firstName": "Alice",
    "lastName": "Operator",
    "email": "alice@tylertech.com",
    "username": "alice@tylertech.com",
    "magicLinkConfiguration": {
      "sendMagicLink": true
    }
  }
}
```

#### Response — `CreateOrganizationResponse` {#response--createorganizationresponse}

| Field | Notes |
|---|---|
| `id` | Internal numeric Organization id (see [Terminology](#terminology)). |
| `orgKey` | The Org key, echoed back. |
| `magicLinkUrl` | URL returned when a magic link was provisioned for the initial admin; null otherwise. |
| `tidCustomerId` | Numeric Tyler Identity customer id linked to the new Org. |
| `defaultProductionWorkspaceId` | Numeric id of the Production workspace provisioned alongside the Org. |

### Deactivate Internal Organization

| Item | Value |
|---|---|
| Method & Path | `POST /api/v2/Organization/deactivate/{organizationKey}` |
| Path parameter | `{organizationKey}` — the Org **key** (e.g. `tylerdemo`). |
| Body | A JSON string containing the deactivation **reason** (e.g. `"end of pilot"`). |
| Required permissions | `delete:organization` **and** `manage:internalorganization` |
| Response | `204 No Content` |
| Reference | `Organization_DeactivateOrganization` |

**Cascade behavior:** Deactivating the Organization also deactivates **all of its workspaces**. Adopters do not need to deactivate workspaces individually before calling this endpoint.

Example call:

```bash
curl -X POST "https://api.tcpci.com/portal/provisioning/api/v2/Organization/deactivate/tylerdemo" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '"end of pilot"'
```

### Activate Internal Organization

| Item | Value |
|---|---|
| Method & Path | `POST /api/v2/Organization/{organizationKey}/activate` |
| Path parameter | `{organizationKey}` — the Org key. |
| Body | A JSON string containing the reactivation **reason**. |
| Required permissions | `delete:organization` **and** `manage:internalorganization` |
| Response | `204 No Content` |
| Reference | `Organization_ActivateOrganization` |

**Cascade behavior:** Reactivating a previously-deactivated Organization also **reactivates the workspaces** that were deactivated when the Org was deactivated. (`delete:organization` is the controlling base permission for both deactivate and activate — it is not the same as `create:organization`.)

### Delete Internal Organization

| Item | Value |
|---|---|
| Method & Path | `DELETE /api/v2/Organization/{organizationKey}` |
| Path parameter | `{organizationKey}` — the Org key. |
| Query parameter | `deleteTidCustomer` (boolean, default `false`) — when `true`, the Org's data is also removed from Tyler Identity. |
| Body | None. |
| Required permissions | `delete:organization` **and** `manage:internalorganization` |
| Response | `204 No Content` |
| Reference | `Organization_DeleteOrganization` |

**Prerequisite — workspaces must be deleted first.** Unlike deactivation (which cascades to workspaces), **deletion does not cascade**. All of the Organization's workspaces must be deleted before the Org delete will succeed. Use the [Delete Workspace (Internal Org)](#delete-workspace-internal-org) endpoint below to remove each workspace first, then call this endpoint.

### Create Workspace (Internal Org)

Workspace creation on an Internal Organization uses the **same `POST /api/v2/Tenants` endpoint and `TenantDataCreate` request body** documented in [Creating Workspaces → Endpoint](#endpoint) and [Creating Workspaces → Request body](#request-body--tenantdatacreate). The reuse-before-create step, [Workspace key rules](#workspace-key-rules) (which already cover both Internal and Customer org variants), response shape (`PortalProvisionData`), and post-create checklist apply identically. The Internal-Org-specific example values are listed below.

**Permissions:** `create:workspace` (enforced by the Provisioning v2 endpoint) **and** `manage:internalorganization` (the section-wide governance gate documented at the top of this section). Both must be held.

#### Example payload (Internal) {#example-payload-internal}

The following payload illustrates a non-production workspace creation against the Internal Org `tylerdemo`:

```json
{
    "urlPrefix": "{workspace key rules}",                              // e.g. "tylerdemo-pilot"
    "agencyTitle": "{Production: Org Name; NonProduction: Org Name [Suffix]}", // e.g. "Tyler Demo [Pilot]"
    "customerId": "{orgKey}",                                          // e.g. "tylerdemo"
    "portalType": "{Production | NonProduction}",                      // e.g. "NonProduction"
    "availableProductRegistrationIds": [
        "{product registration id to make available; array may be empty}"
    ],
    "homePageTitle": "{Org Name}",
    "usesCustomerLinks": true,
    "usesCustomerContacts": true
}
```

The same `agencyTitle` / `availableProductRegistrationIds` / `usesCustomer*` conventions documented under [Creating Workspaces → Example payload](#example-payload) apply here.

#### Examples (Internal) {#examples-internal}

| Org key | Workspace key | `portalType` | Valid? |
|---|---|---|---|
| `tylerdemo` | `tylerdemo` | `Production` | Yes |
| `tylerdemo` | `tylerdemo-pilot` | `NonProduction` | Yes — Internal Orgs are not restricted to the External suffix enum |
| `tylerdemo` | `tylerdemo-sandbox` | `NonProduction` | Yes — any suffix matching the common rules is allowed |
| `tylerdemo` | `tylerdemo-test` | `NonProduction` | Yes |
| `tylerdemo` | `tylerdemo-admin` | `NonProduction` | **No** — suffix cannot be `admin` (case-insensitive) |
| `tylerdemo` | `tylerdemo-test` | `Production` | **No** — Production keys cannot contain `-` |
| `tylerdemo` | `tylerdemo` | `NonProduction` | **No** — NonProduction keys must contain `-` |

### Deactivate / Activate Workspace (Internal Org) {#deactivate-activate-workspace-internal-org}

Workspace-level deactivation and reactivation are **not** exposed on the Provisioning v2 Tenant endpoints. To temporarily disable a workspace on an Internal Org without deleting it (or to bring a previously-disabled workspace back online), use the workspace status endpoint on the **TCP Platform Service** — a separate API documented at `https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-platform-service/` with ingress `{BASE_URL}/portal/platformservice`.

| Item | Value |
|---|---|
| Method & Path | `PUT /api/v1/portals/{id}/status` |
| API | TCP Platform Service (distinct from Provisioning v2). |
| Path parameter | `{id}` — the **internal numeric workspace id**, not the workspace key. See [Terminology](#terminology). |
| Body | `UpdatePortalStatus` — `{ "active": bool?, "status": PortalStatus? }`. Properties left at their defaults are not modified. Send `{ "active": false }` to deactivate or `{ "active": true }` to reactivate. |
| Required permissions | `update:workspace` (base, enforced by Platform Service) **and** `manage:internalorganization` (governance gate for Internal-Org workspaces, same pattern as Internal-Org workspace deletion). |
| Response | `200` — the current `UpdatePortalStatus` reflecting the post-update state. |
| Reference | `UpdatePortalStatus` on the TCP Platform Service Swagger |

Obtaining the numeric workspace `id`:

- From the Platform Service workspace lookup: `GET /api/v1/portals?StringPortalId={urlPrefix}` returns the workspace record including `id`.
- For workspaces just provisioned alongside an Internal Org create, the `defaultProductionWorkspaceId` field of [`CreateOrganizationResponse`](#response--createorganizationresponse) carries the Production workspace's numeric id directly.

Example call (deactivate workspace id `123` in CI):

```bash
curl -X PUT "https://api.tcpci.com/portal/platformservice/api/v1/portals/123/status" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{ "active": false }'
```

For workspaces on Customer / External Organizations, this Platform Service endpoint **must not** be used by external deployment tools to deactivate or reactivate workspaces — route those requests through a OneTyler support ticket.

### Delete Workspace (Internal Org) {#delete-workspace-internal-org}

Workspaces on Internal Organizations may be deactivated and deleted via the Provisioning v2 Tenant DELETE endpoints. Both endpoints handle the deactivation-then-deletion lifecycle for the targeted workspace(s).

| Purpose | Method & Path | Body | Required permissions | Response | Reference |
|---|---|---|---|---|---|
| Delete a single workspace by key | `DELETE /api/v2/Tenants/{urlPrefix}` | none | `delete:workspace` **and** `manage:internalorganization` | `200` | `Tenants_Delete` |
| Delete a list of workspaces (bulk) | `DELETE /api/v2/Tenants` | `string[]` of `urlPrefix` values | `delete:workspace` **and** `manage:internalorganization` | `200` | `Tenants_BulkDelete` |

The `manage:internalorganization` permission is **required in addition to** `delete:workspace` whenever the target workspace belongs to an Internal Organization. Clients without this permission cannot delete Internal-Org workspaces through these endpoints.

For workspaces on Customer / External Organizations these DELETE endpoints **must not** be used by external tools — see [Workspace deletion (Customer / External Orgs)](#workspace-deletion-customer--external-orgs) above.

## Webhooks

**Use when:** an integrating tool needs to react to Org / Workspace / Product lifecycle changes without polling the Search or Provisioning APIs.

Ops Center publishes lifecycle events for Organizations, Workspaces, and Products through the **TCP Webhook API**. Integrating tools subscribe to the message types they care about and receive HTTP callbacks (or routed messages) when the corresponding events occur — avoiding the need to poll the Search or Provisioning APIs to detect changes.

Reference:

- Swagger: `https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-webhook-api/`
- Full schema catalog (all event types): `https://github.com/tyler-technologies/tcp-webhook-api/blob/main/docs/SCHEMAS.md`
- Ingress: `{BASE_URL}/api/tcp-webhook-api`
- Subscribe / unsubscribe / list registrations: see `POST /api/v1/Registrations/subscribe`, `POST /api/v1/Registrations/unsubscribe/{referenceId}`, `POST /api/v1/Registrations/search` in the Swagger reference linked above.

Only the webhook events most relevant to the core Ops Center API use cases — Organizations, Workspaces, and Products — are catalogued in this guide. Less frequently used Ops Center events, and events published by adjacent integrations such as Identity, are not enumerated here. For the complete, authoritative listing of every webhook event available across all message families, see the full TCP Webhook API schema reference at `https://github.com/tyler-technologies/tcp-webhook-api/blob/main/docs/SCHEMAS.md`. The companion file `GitHub-TCPWebhookApi.md` in this corpus distills all 25 event types.

### Message envelope conventions

Every Ops Center message shares the same envelope conventions:

- **Event type** — a fully-qualified string of the form `TCP.Webhook.Messages.V{n}.{Name}`. This is the value to subscribe against. Current Ops Center events are all `V1`.
- **`MessageType`** — a short kebab-case discriminator that appears on the payload (e.g. `organization-created`, `product-licensed`). Use this on the receiver side to fan out to per-event handlers.
- **Filter fields** — properties on the message that you can pin to specific values when subscribing (e.g. only deliver `WorkspaceCreated` events for `OrganizationKey == "cityofmobileal"`).
- **Custom filters** — predefined behavioural filters offered by the Webhook API. The `ProductLicensed` custom filter, where listed below, restricts delivery to events where the Org / Workspace currently holds at least one licensed product (and on workspace events, where that product is available on the workspace).
- **Workspace type** — wherever a `WorkspaceType` appears on the payload or as a filter, the value is `Production` or `NonProduction` (matching the `portalType` value used elsewhere in this guide).

### Organization messages

#### Organization Created

- **Event type**: `TCP.Webhook.Messages.V1.OrganizationCreated`
- **Description**: Organization created.
- **Filter fields**: `OrganizationKey`, `Internal`
- **Custom filters**: none
- **Source**: `https://github.com/tyler-technologies/tcp-webhook-api/blob/main/docs/ORGANIZATION-MESSAGES.md#organization-created`

Schema:

```json
{
  "messageType": { "type": "string", "readOnly": true },
  "organizationKey": { "type": "string" },
  "internal": { "type": "boolean" }
}
```

Example:

```json
{
  "MessageType": "organization-created",
  "OrganizationKey": "orgKey",
  "Internal": true
}
```

#### Organization Activated

- **Event type**: `TCP.Webhook.Messages.V1.OrganizationActivated`
- **Description**: Organization activated.
- **Filter fields**: `OrganizationKey`
- **Custom filters**: `ProductLicensed`
- **Source**: `https://github.com/tyler-technologies/tcp-webhook-api/blob/main/docs/ORGANIZATION-MESSAGES.md#organization-activated`

Schema:

```json
{
  "messageType": { "type": "string", "readOnly": true },
  "organizationKey": { "type": "string" },
  "productWorkspaceAvailabilities": {
    "description": "Product registration IDs of products licensed to this organization and the workspace keys of workspaces where they are available",
    "type": "object",
    "additionalProperties": { "type": "array", "items": { "type": "string" } }
  }
}
```

Example:

```json
{
  "MessageType": "organization-activated",
  "OrganizationKey": "orgKey",
  "ProductWorkspaceAvailabilities": {
    "product-registration-id1": ["workspaceKey1", "workspaceKey2"],
    "product-registration-id2": ["workspaceKey3"]
  }
}
```

#### Organization Deactivated

- **Event type**: `TCP.Webhook.Messages.V1.OrganizationDeactivated`
- **Description**: Organization deactivated.
- **Filter fields**: `OrganizationKey`
- **Custom filters**: `ProductLicensed`
- **Source**: `https://github.com/tyler-technologies/tcp-webhook-api/blob/main/docs/ORGANIZATION-MESSAGES.md#organization-deactivated`

Schema: same as `OrganizationActivated` above.

Example:

```json
{
  "MessageType": "organization-deactivated",
  "OrganizationKey": "orgKey",
  "ProductWorkspaceAvailabilities": {
    "product-registration-id1": ["workspaceKey1", "workspaceKey2"],
    "product-registration-id2": ["workspaceKey3"]
  }
}
```

#### Organization Deleted

- **Event type**: `TCP.Webhook.Messages.V1.OrganizationDeleted`
- **Description**: Organization deleted.
- **Filter fields**: `OrganizationKey`, `Internal`
- **Custom filters**: none
- **Source**: `https://github.com/tyler-technologies/tcp-webhook-api/blob/main/docs/ORGANIZATION-MESSAGES.md#organization-deleted`

Schema: same as `OrganizationCreated` above.

Example:

```json
{
  "MessageType": "organization-deleted",
  "OrganizationKey": "orgKey",
  "Internal": true
}
```

#### Workspace Created

- **Event type**: `TCP.Webhook.Messages.V1.WorkspaceCreated`
- **Description**: Workspace created.
- **Filter fields**: `OrganizationKey`, `WorkspaceKey`, `WorkspaceType`
- **Custom filters**: `ProductLicensed`
- **Source**: `https://github.com/tyler-technologies/tcp-webhook-api/blob/main/docs/ORGANIZATION-MESSAGES.md#workspace-created`

Schema:

```json
{
  "messageType": { "type": "string", "readOnly": true },
  "organizationKey": { "type": "string" },
  "workspaceKey": { "type": "string" },
  "workspaceType": {
    "type": "string",
    "description": "Workspace type will be either Production or NonProduction"
  }
}
```

Example:

```json
{
  "MessageType": "workspace-created",
  "OrganizationKey": "orgKey",
  "WorkspaceKey": "workspaceKey",
  "WorkspaceType": "Production"
}
```

#### Workspace Activated

- **Event type**: `TCP.Webhook.Messages.V1.WorkspaceActivated`
- **Description**: Workspace activated.
- **Filter fields**: `OrganizationKey`, `WorkspaceKey`, `WorkspaceType`
- **Custom filters**: `ProductLicensed`
- **Source**: `https://github.com/tyler-technologies/tcp-webhook-api/blob/main/docs/ORGANIZATION-MESSAGES.md#workspace-activated`

Schema: same as `WorkspaceCreated` above.

Example:

```json
{
  "MessageType": "workspace-activated",
  "OrganizationKey": "orgKey",
  "WorkspaceKey": "workspaceKey",
  "WorkspaceType": "Production"
}
```

#### Workspace Deactivated

- **Event type**: `TCP.Webhook.Messages.V1.WorkspaceDeactivated`
- **Description**: Workspace deactivated.
- **Filter fields**: `OrganizationKey`, `WorkspaceKey`, `WorkspaceType`
- **Custom filters**: `ProductLicensed`
- **Source**: `https://github.com/tyler-technologies/tcp-webhook-api/blob/main/docs/ORGANIZATION-MESSAGES.md#workspace-deactivated`

Schema: same as `WorkspaceCreated` above.

Example:

```json
{
  "MessageType": "workspace-deactivated",
  "OrganizationKey": "orgKey",
  "WorkspaceKey": "workspaceKey",
  "WorkspaceType": "Production"
}
```

#### Workspace Deleted

- **Event type**: `TCP.Webhook.Messages.V1.WorkspaceDeleted`
- **Description**: Workspace deleted.
- **Filter fields**: `OrganizationKey`, `WorkspaceKey`, `WorkspaceType`
- **Custom filters**: none
- **Source**: `https://github.com/tyler-technologies/tcp-webhook-api/blob/main/docs/ORGANIZATION-MESSAGES.md#workspace-deleted`

Schema: same as `WorkspaceCreated` above.

Example:

```json
{
  "MessageType": "workspace-deleted",
  "OrganizationKey": "orgKey",
  "WorkspaceKey": "workspaceKey",
  "WorkspaceType": "Production"
}
```

### Product messages

#### Product Licensed

- **Event type**: `TCP.Webhook.Messages.V1.ProductLicensed`
- **Description**: Product licensed to an Organization.
- **Filter fields**: `RegistrationId`, `OrganizationKey`
- **Custom filters**: none
- **Source**: `https://github.com/tyler-technologies/tcp-webhook-api/blob/main/docs/PRODUCT-MESSAGES.md#product-licensed`

Schema:

```json
{
  "messageType": { "type": "string", "readOnly": true },
  "registrationId": { "type": "string" },
  "organizationKey": { "type": "string" }
}
```

Example:

```json
{
  "MessageType": "product-licensed",
  "RegistrationId": "product-registration-id",
  "OrganizationKey": "orgKey"
}
```

#### Product Unlicensed

- **Event type**: `TCP.Webhook.Messages.V1.ProductUnlicensed`
- **Description**: Product unlicensed from an Organization.
- **Filter fields**: `RegistrationId`, `OrganizationKey`
- **Custom filters**: none
- **Source**: `https://github.com/tyler-technologies/tcp-webhook-api/blob/main/docs/PRODUCT-MESSAGES.md#product-unlicensed`

Schema: same as `ProductLicensed` above.

Example:

```json
{
  "MessageType": "product-unlicensed",
  "RegistrationId": "product-registration-id",
  "OrganizationKey": "orgKey"
}
```

#### Product Activated

- **Event type**: `TCP.Webhook.Messages.V1.ProductActivated`
- **Description**: Product made available to a workspace.
- **Filter fields**: `RegistrationId`, `OrganizationKey`, `WorkspaceKey`
- **Custom filters**: none
- **Source**: `https://github.com/tyler-technologies/tcp-webhook-api/blob/main/docs/PRODUCT-MESSAGES.md#product-activated`

Schema:

```json
{
  "messageType": { "type": "string", "readOnly": true },
  "registrationId": { "type": "string" },
  "organizationKey": { "type": "string" },
  "workspaceKey": { "type": "string" }
}
```

Example:

```json
{
  "MessageType": "product-activated",
  "RegistrationId": "product-registration-id",
  "OrganizationKey": "orgKey",
  "WorkspaceKey": "workspaceKey"
}
```

#### Product Deactivated

- **Event type**: `TCP.Webhook.Messages.V1.ProductDeactivated`
- **Description**: Product made unavailable on a workspace.
- **Filter fields**: `RegistrationId`, `OrganizationKey`, `WorkspaceKey`
- **Custom filters**: none
- **Source**: `https://github.com/tyler-technologies/tcp-webhook-api/blob/main/docs/PRODUCT-MESSAGES.md#product-deactivated`

Schema: same as `ProductActivated` above.

Example:

```json
{
  "MessageType": "product-deactivated",
  "RegistrationId": "product-registration-id",
  "OrganizationKey": "orgKey",
  "WorkspaceKey": "workspaceKey"
}
```

---

## Notes for the chatbot

1. **Audience.** This is Tyler-internal but publicly addressable engineering content. It is appropriate to share with Tyler engineering teams building integrating deployment tools. The URL `https://docs.tylerdev.io/app-guides/ops/ops-center/adoption/` is the canonical live source — surface it verbatim when the user wants the up-to-date page.
2. **Three different APIs.** This guide touches **four** API surfaces — TCP Search API, TCP Provisioning Service v2, TCP Platform Service, TCP Webhook API. Each has a distinct ingress path and Swagger reference. When a user asks "what endpoint do I call for X?", first establish *which* API the operation lives on (the [Quick lookup](#quick-lookup--use-when-routing) table maps intent → section, and each section names the API).
3. **Numeric id vs key — re-emphasize.** When a user shares a call that 404s or returns a wrong record, the first thing to check is whether they passed the **Org key (`customerId`)** or the **numeric Organization id** in the path. The Provisioning v2 licensing endpoints take the **numeric id**; everything else generally takes the key.
4. **Declarative POSTs.** When a user describes "adding" a product to an Org's license set or a workspace's availability set, **always remind them** that the bulk POST/PUT is set-style and they must first GET the current set and append. This is the most common integration bug.
5. **Don't volunteer Customer-Org delete/deactivate flows from this guide.** They are explicitly blocked for external tools. Route to `Knowledge-Shared/Conf-OneTylerTickets.md` for the OneTyler support ticket path instead.
6. **Webhook completeness.** This file enumerates Org / Workspace / Product events only. For Identity, Support Access, User Group, and other event families, route to `GitHub-TCPWebhookApi.md`.
7. **Companion routing.** If a user asks how to *do* something in Ops Center (the UI) — wizards, screens, AD Agent, federation — prefer `Docusaurus-OpsCenter.md`. **This** file is for *integrating via API* against the same underlying constructs.
8. **Permission naming.** Permissions in this guide are formatted `action:resource` (`read:product`, `create:workspace`, `delete:organization`, `update:workspace`, `licenseproduct:organization`, `unlicenseproduct:organization`, `create:appavailability`, `manage:internalorganization`). The JWT bearer token must carry all listed permissions for the given operation — never just one.
9. **Surface URLs verbatim.** Swagger URLs (`https://docs.tylerdev.io/architecture/cloud-platform-api/...`), GitHub schema URLs, and the CRM deep-link template should all be copied exactly. Do not paraphrase or rewrite them.
