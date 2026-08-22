# Aligned Releases — Key Concepts, Integration Guide, and API Reference

Source: Tyler Blueprint Docusaurus — https://docs.tylerdev.io/aligned-releases
Domain: Blueprint General — Tyler Cloud Platform / Blueprint docs not served by a specialized Foundry agent
Audience: Tyler product-team engineers and platform integrators building against the Aligned Releases system

**Companion documents:**
- `_START_HERE.md` — corpus routing guide
- `Docusaurus-PlatformOverview.md` — TCP platform overview and service landscape
- `Docusaurus-CloudPlatformAPI.md` — authentication and Platform Service API general reference
- `Docusaurus-ProductSystemReg.md` — product and workspace registration (productRegistrationId, workspaceKey)
- `Docusaurus-ServiceArchitecture.md` — event-driven service architecture that AR uses for state propagation
- `Docusaurus-StatusPageAndSLA.md` — SLA tracking and status-page integration (sibling platform service)

---

## How to use this guide

| User intent | Go to section |
|---|---|
| "What is Aligned Releases / AR System?" | Key Concepts → What Problem Are We Solving |
| "What are cohorts / releases / features / GA?" | Key Concepts → Glossary |
| "What are the feature lifecycle stages?" | Key Concepts → Feature Lifecycle |
| "How do I authenticate to the AR API?" | Integration Guide → Authentication |
| "What environments / base URLs do I use?" | Integration Guide → Available Environments |
| "How do I create a release and cohorts?" | Integration Guide → Creating New Releases |
| "How do I create / update / query a feature?" | Integration Guide → Adding a Feature |
| "How do I move a feature through preview to GA?" | Integration Guide → Managing a Feature Lifecycle |
| "How do I assign a workspace to a cohort?" | Integration Guide → Assigning Customer Cohorts |
| "How do I trigger GA rollout for a cohort?" | Integration Guide → Taking a Feature GA |
| "Full end-to-end code example?" | Integration Guide → Full Exercise Examples |
| "What API endpoints exist?" | API Reference → Endpoint Catalog |
| "Where is the C# SDK?" | API Reference → SDKs and Tools |
| "Is there an integration checklist?" | Integration Checklist section |

---

## Glossary

| Term | Definition |
|---|---|
| AR System | Aligned Releases System — the applications, APIs, and processes Tyler uses to define, document, schedule, activate, and release code to client-facing products. |
| Release | A quarterly delivery window (February, May, August, November). Named as `YYYY.Q` (e.g., `2026.1`). |
| Cohort | A set of (client workspace, product) tuples assigned to one of four GA weeks. Cohort 1 = GA date; Cohorts 2–4 = 1, 2, 3 weeks later. |
| Feature | A client-facing enhancement tied to a quarterly release. Progresses through lifecycle stages: Planned → Private Preview → Public Preview → GA. |
| Feature Flag (FF) | The technical gate (owned by the product team) that activates a capability for a client. A Feature can map to zero or many flags. Flags express targeting/rollout; Feature stage is the AR lifecycle record. |
| Feature Stage | `Planned` / `Private` (Private Preview) / `Public` (Public Preview) / `GA` (General Availability). |
| GA | General Availability — feature enabled for all clients in a cohort, with full support and SLA. |
| Private Preview | Feature enabled for specific selected workspaces; no support, no SLA. |
| Public Preview | Feature available to any client who opts in; limited support, no SLA. |
| Module | A sub-grouping of product features by functional area (e.g., Financials, HCM within EERP). |
| Version | A product workspace is "versioned" to a quarterly release (e.g., `2027.1`) once that release's features are activated. |
| Maintenance Window | Platform-defined windows for product maintenance; defined at the rock-group level (quarterly) and product/module level. |
| productRegistrationId | The registration identifier for a Tyler product (e.g., `"Corrections"`, `"Virtual Court"`). Defined in Product Registration. |
| workspaceKey | The unique key for a client workspace instance (e.g., `"rentonwa"`). |
| Release Documentation | Name, description, and documentation link for each feature — communicated to clients around a quarterly release. |

---

## Key Concepts

### What Problem Are We Solving

Tyler product teams historically had disparate processes and tools for releasing software and communicating about it to clients. The result was a slower, inconsistent, and fragmented experience. The **Aligned Releases Cloud Living initiative** establishes a single, consistent release system so clients can understand the "what" and "when" of coming releases and prepare for newly released features.

The AR System is the **system of record** representing the desired state of clients' quarterly releases. Product teams use their own software activation processes to react to state changes communicated by the AR System, keeping actual client software states consistent with what the AR System shows.

### Feature Lifecycle

Features move through four discrete stages:

```
Planned → Private Preview → Public Preview → General Availability (GA)
```

| Stage | Audience | Support | SLA |
|---|---|---|---|
| Planned | Internal only — feature is being developed | — | — |
| Private Preview (`private`) | Selected client workspaces (invitation only) | None | None |
| Public Preview (`public`) | Any client who opts in | Limited | None |
| GA (`ga`) | All clients by cohort assignment | Full | Yes |

**Cohorts apply to GA only.** Preview participation is optional and managed within divisional tooling; AR provides visibility but does not drive preview activation.

### Representative Lifecycle Scenarios

- **Simple path:** Feature planned → added to quarterly release before communication cutoff → GA by cohort on release date.
- **Private-then-public preview:** Feature enters private preview with selected clients → broadened to public preview → added to quarterly release → GA for remaining clients by cohort.
- **Rollback mid-GA:** Feature enters cohort 1 GA but a bug is found for some configurations → feature removed from release, returned to Preview state → bug fixed → re-added to next quarterly release.
- **Preview-first, late to release:** Feature completes after communication cutoff → made available as Public Preview immediately → added to the following quarterly release → GA in that release.

### Key Business Objects

| Object | Description |
|---|---|
| Products | Defined in Product Registration; the deployed-software definition of what a client has purchased. |
| Module | A subset of product features by functional area. |
| Workspaces | Instances of a product deployed for a client (Test, Train, Production). |
| Cohort | Set of (workspace, product) tuples assigned to one of the four GA weeks in a quarterly release. |
| Releases | Four quarterly GA windows per year (Feb, May, Aug, Nov). |
| Release Documentation | Feature names, descriptions, and doc links communicated to clients. |
| Release Notes | Documentation for non-quarterly releases (bug fixes, low-risk enhancements). |
| Feature Flag | Technical control gating a capability for a client; separate from Feature stage. |
| Maintenance Windows | Consistent windows for product maintenance (platform-level and product-level). |

---

## Integration Guide

### Prerequisites

- OAuth 2.0 client credentials from **Tyler Identity Gateway**
- Scope: `tyler-cloud-platform-api-access`
- `productRegistrationId` for your product (from Product Registration)

### Authentication

The AR API uses **OAuth 2.0 client credentials** flow. The authentication authority is Tyler Identity Gateway.

**HTTP (curl) — obtain a token:**
```bash
getToken() {
    out=$(curl -sSL -XPOST "https://idgw.tcpci.com/tg/connect/token" \
        -d 'client_id=<your-client-id>&client_secret=<your-secret>&grant_type=client_credentials&scope=tyler-cloud-platform-api-access')
    echo "$out" | jq -r '.access_token'
}
token=$(getToken)
```

**C# SDK — configure `AlignedReleasesSdk`:**
```csharp
builder.Services.AddScoped<IAlignedReleasesSdk>(provider =>
    new AlignedReleasesSdk(new SdkConfiguration
    {
        HttpClientFactory = httpClientFactory,
        LoggerFactory    = loggerFactory,
        AllowAuthTokenHttpAuthority = false,          // true in localdev only
        AuthTokenAuthority   = configuration.GetValue<string>("oauth2:tcp_platform_api:authority"),
        AuthTokenClientId    = configuration.GetValue<string>("oauth2:tcp_platform_api:clientId"),
        AuthTokenClientSecret = configuration.GetValue<string>("oauth2:tcp_platform_api:clientSecret"),
        AuthTokenScopes = ["tyler-cloud-platform-api-access"],  // do not change
        BaseUrl = configuration.GetValue<string>("internal_endpoints:Platform"),
    }));
```

### Available Environments

| Environment | Base URL |
|---|---|
| TCPCI (dev) | `https://api.tcpci.com/portal/platformservice/` |
| TCPQA (QA, mirrors prod) | `https://api.tcpqa.com/portal/platformservice/` |
| TCPPROD (production) | `https://api.tylerportico.com/portal/platformservice/` |

**Identity Gateway hosts:**
- TCPCI: `https://idgw.tcpci.com/tg`
- TCPQA: `https://idgw.tcpqa.com/tg`
- TCPPROD: `https://idgw.tcpprod.com/tg` (or `https://idgw.tylerportico.com/tg` per Platform Service config)

---

### Creating New Releases

> Use when: You need to create a new quarterly release and define its four cohort windows. This is typically done by the OneTyler/platform team, not individual product teams. Product teams usually start at "Adding a Feature."

**Step 1 — Create the release:**

```bash
# HTTP
curl -sSlL -XPOST https://api.tcpci.com/portal/platformservice/api/v1/release \
  -H "Authorization: Bearer $token" \
  -H 'Content-Type: application/json' \
  -d '{"name": "2026.1", "year": 2026, "quarter": 1, "notes": "2026 Q1 Release"}'
# Returns: {"id": 1, "name": "2026.1", "year": 2026, "quarter": 1, "notes": "..."}
```

```csharp
// C# SDK
var createdRelease = await alignedReleasesSdk.CreateRelease(new Release
{
    Name = "2026.1", Year = 2026, Quarter = 1, Notes = "2026 Q1 Release"
});
```

Request parameters: `name` (string, required), `year` (int, required), `quarter` (1–4, required), `notes` (string, optional).

**Step 2 — Create four cohorts for the release:**

```bash
# HTTP — repeat for cohorts 1–4 with appropriate windowStart/windowEnd dates
curl -sSlL -XPOST https://api.tcpci.com/portal/platformservice/api/v1/release-cohort \
  -H "Authorization: Bearer $token" \
  -H 'Content-Type: application/json' \
  -d '{"releaseId": 1, "cohort": 1, "windowStart": "1/5/2026", "windowEnd": "1/9/2026", "notes": "2026.1.1"}'
```

```csharp
// C# SDK
var createdCohort = await alignedReleasesSdk.CreateReleaseCohort(new ReleaseCohort
{
    ReleaseId = releaseId, Cohort = 1,
    WindowStart = new DateTimeOffset(new DateTime(2026, 1, 5)),
    WindowEnd   = new DateTimeOffset(new DateTime(2026, 1, 9)),
    Notes = "2026.1.1"
});
```

Cohort parameters: `releaseId` (int, required), `cohort` (1–4, required), `windowStart` (datetime, required), `windowEnd` (datetime, required), `notes` (optional).

---

### Adding a Feature

> Use when: Your product team is beginning work on a new client-facing feature that will appear in a quarterly release.

**Create feature** (starts in `Planned` state):

```bash
curl -sSlL -XPOST https://api.tcpci.com/portal/platformservice/api/v1/feature \
  -H "Authorization: Bearer $token" -H 'Content-Type: application/json' \
  -d '{
    "name": "My Feature Name",
    "description": "Client-facing description of the feature",
    "productRegistrationId": "YourProductId",
    "metadata": "Internal notes",
    "releaseNotes": [{"title": "My Feature", "url": "https://docs.example.com/feature"}]
  }'
# Returns: integer feature ID
```

```csharp
var featureId = await alignedReleasesSdk.CreateFeature(new FeatureCreate
{
    Name = "My Feature Name",
    Description = "Client-facing description",
    ProductRegistrationId = "YourProductId",
    Metadata = "Internal notes",
    ReleaseNotes = [new() { Title = "My Feature", Url = "https://docs.example.com/feature" }]
});
```

Parameters:
- `name` (string, required) — display name shown to clients
- `description` (string, required) — client-facing description
- `productRegistrationId` (string, required) — product this feature belongs to
- `metadata` (string, optional) — internal notes
- `releaseNotes` (array, optional) — `[{title, url}]` documentation links

**Update feature** (`PUT /api/v1/feature/{id}`): Updates name, description, metadata, releaseNotes. Returns `204 No Content`.

**Get feature** (`GET /api/v1/feature/{id}`): Returns full feature record including `state`, `releaseId`, `releaseName`.

**Query features** (`GET /api/v1/feature`):

| Query param | Description |
|---|---|
| `product` | Filter by `productRegistrationId` |
| `state` | `Planned`, `Private`, `Public`, or `GA` |
| `releaseId` | Filter by release |
| `name` | Partial name match |
| `offset` / `limit` | Pagination (default limit: 25) |

---

### Managing a Feature Lifecycle

> Use when: You need to advance a feature through its stages (Private Preview, Public Preview, GA) or activate it for specific workspaces before GA.

**Transition feature stage** (`PUT /api/v1/feature/{id}/state/{state}`):

Valid target states: `planned`, `private`, `public`, `ga`

```bash
# Move to Public Preview
curl -sSlL -XPUT https://api.tcpci.com/portal/platformservice/api/v1/feature/1/state/public \
  -H "Authorization: Bearer $token"
```

```csharp
await alignedReleasesSdk.UpdateFeatureState(featureId, Feature.State.Public);
```

**Activate feature for a specific workspace (pre-GA):**

```bash
# Enable for workspace "rentonwa"
curl -sSlL -XPUT https://api.tcpci.com/portal/platformservice/api/v1/feature/1/workspace/rentonwa/true \
  -H "Authorization: Bearer $token"
```

```csharp
await alignedReleasesSdk.ChangeFeatureActivationOnWorkspace(id: featureId, workspaceKey: "rentonwa", activated: true);
```

Path parameters: `id` (feature ID), `workspaceKey`, `activated` (true/false).

**Activate feature for all workspaces in a cohort** (`PUT /api/v1/feature/{id}/cohort/{cohort}/{activated}`): Enables or disables a feature for every workspace assigned to a specific cohort number.

**Get feature activation details** (`POST /api/v1/feature/{id}/activations`): Returns workspace-level activation status for a feature.

---

### Assigning Customer Cohorts

> Use when: Before GA rollout, workspaces must be assigned to one of the four cohorts for a product. Typically managed by customer success or product operations.

**Assign a single workspace to a cohort:**

```bash
curl -sSlL -XPUT https://api.tcpci.com/portal/platformservice/api/v1/cohort-assignment/product/Corrections/workspace/rentonwa/cohort/4 \
  -H "Authorization: Bearer $token"
```

```csharp
await alignedReleasesSdk.SetProductWorkspaceCohort(
    productRegistrationId: "Corrections", workspaceKey: "rentonwa", cohort: 4);
```

**Batch assign workspaces to cohorts** (`PUT /api/v1/cohort-assignment/product/{productRegistrationId}/batch`): Atomically sets cohort assignments for many workspaces of a single product.

**Query cohort assignments:**
- `GET /api/v1/cohort-assignment/product/{productRegistrationId}` — all assignments for a product
- `GET /api/v1/cohort-assignment/workspace/{workspaceKey}` — all assignments for a workspace
- `GET /api/v1/cohort-assignment/product/{productRegistrationId}/workspace/{workspaceKey}` — specific workspace+product

---

### Taking a Feature GA with Releases and Cohorts

> Use when: You are ready to include a feature in a quarterly release for client communication, and to trigger the GA activation rollout by cohort.

**Step 1 — Assign feature to a release:**

```bash
curl -sSlL -XPUT https://api.tcpci.com/portal/platformservice/api/v1/feature/1/release/1 \
  -H "Authorization: Bearer $token"
```

```csharp
await alignedReleasesSdk.AssignFeatureToRelease(id: featureId, releaseId: releaseId);
```

**Step 2 — Move feature state to GA** (see Managing a Feature Lifecycle → transition to `ga`).

**Step 3 — Trigger GA rollout for a cohort** (three equivalent endpoints; choose one):

```bash
# Option A: by release cohort ID + product
curl -sSlL -XPUT https://api.tcpci.com/portal/platformservice/api/v1/execute/by-releasecohort/1/product/Corrections \
  -H "Authorization: Bearer $token"

# Option B: by release ID + cohort number + product
curl -sSlL -XPUT "https://api.tcpci.com/portal/platformservice/api/v1/execute/by-release/1/cohort/1/product/Corrections" \
  -H "Authorization: Bearer $token"

# Option C: by feature ID + cohort number
curl -sSlL -XPUT https://api.tcpci.com/portal/platformservice/api/v1/execute/by-feature/1/cohort/1 \
  -H "Authorization: Bearer $token"
```

```csharp
// Option A (most common)
await alignedReleasesSdk.MarkProductReleasedByReleaseCohort(
    releaseCohortId: releaseCohortId, productRegistrationId: "Corrections");
```

**Remove feature from a release** (`DELETE /api/v1/feature/{id}/release`): Use when reverting a feature back to preview mid-cycle.

**Auto-promote features to GA** (`POST /api/v1/release/set-features-ga`): Promotes all non-GA features to GA for releases whose cohort 1 window starts today or tomorrow (UTC), or for a specific release when `releaseId` is supplied.

---

### Full End-to-End Workflow Summary

```
1. Create release (POST /api/v1/release)
2. Create 4 cohorts (POST /api/v1/release-cohort) x4
3. Create feature (POST /api/v1/feature) → returns featureId
4. Move feature to Private Preview (PUT /api/v1/feature/{id}/state/private)
5. Activate for selected workspaces (PUT /api/v1/feature/{id}/workspace/{key}/true)
6. Move feature to Public Preview (PUT /api/v1/feature/{id}/state/public)
7. Assign workspaces to cohorts (PUT /api/v1/cohort-assignment/product/{product}/workspace/{key}/cohort/{n})
8. Move feature to GA (PUT /api/v1/feature/{id}/state/ga)
9. Assign feature to release (PUT /api/v1/feature/{id}/release/{releaseId})
10. Trigger GA rollout per cohort (PUT /api/v1/execute/by-releasecohort/{id}/product/{product})
```

---

## API Reference

Live specification: https://docs.tylerdev.io/aligned-releases/api-reference/specification

### Resource Groups and Endpoint Catalog

**Releases** — manage quarterly release records

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/release` | List all releases |
| POST | `/api/v1/release` | Create a new release |
| GET | `/api/v1/release/{id}` | Get a single release |
| PUT | `/api/v1/release/{id}` | Update a release |
| DELETE | `/api/v1/release/{id}` | Delete a release |
| GET | `/api/v1/release/{id}/features` | Get features for a release |
| GET | `/api/v1/release/{id}/products` | Get products for a release |
| POST | `/api/v1/release/set-features-ga` | Auto-promote non-GA features for imminent cohort 1 releases |
| POST | `/api/v1/release/{id}/product/{productId}/activations` | Feature activations for all features in a release for a product |
| POST | `/api/v1/release/{id}/product/{productId}/product-releases` | Product-release status per workspace for a release and product |

**Release Cohorts** — define the four weekly GA windows per release

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/release-cohort` | List all release cohorts |
| POST | `/api/v1/release-cohort` | Create a release cohort |
| GET | `/api/v1/release-cohort/{id}` | Get a single cohort |
| PUT | `/api/v1/release-cohort/{id}` | Update a cohort |
| DELETE | `/api/v1/release-cohort/{id}` | Delete a cohort |
| GET | `/api/v1/release-cohort/{id}/products` | Products associated with a release cohort |

**Features** — manage feature lifecycle records

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/feature` | Query features (filter by product, state, release, name) |
| POST | `/api/v1/feature` | Create a feature |
| GET | `/api/v1/feature/{id}` | Get a single feature |
| PUT | `/api/v1/feature/{id}` | Update feature metadata |
| DELETE | `/api/v1/feature/{id}` | Delete a feature |
| PUT | `/api/v1/feature/{id}/state/{state}` | Transition feature lifecycle stage |
| PUT | `/api/v1/feature/{id}/release/{releaseId}` | Assign feature to a release |
| DELETE | `/api/v1/feature/{id}/release` | Remove feature from its release |
| PUT | `/api/v1/feature/{id}/workspace/{workspaceKey}/{activated}` | Activate/deactivate feature for a workspace |
| PUT | `/api/v1/feature/{id}/cohort/{cohort}/{activated}` | Activate/deactivate feature for all workspaces in a cohort |
| POST | `/api/v1/feature/{id}/activations` | Get activation details for a feature |
| PUT | `/api/v1/feature/{id}/modules` | Replace module tags on a feature |

**Cohort Assignments** — manage which cohort each workspace belongs to per product

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/cohort-assignment/product/{productRegistrationId}` | All cohort assignments for a product |
| GET | `/api/v1/cohort-assignment/workspace/{workspaceKey}` | All cohort assignments for a workspace |
| GET | `/api/v1/cohort-assignment/product/{productRegistrationId}/workspace/{workspaceKey}` | Cohort for a specific product+workspace |
| PUT | `/api/v1/cohort-assignment/product/{productRegistrationId}/workspace/{workspaceKey}/cohort/{cohort}` | Set cohort for a workspace |
| PUT | `/api/v1/cohort-assignment/product/{productRegistrationId}/batch` | Batch set cohorts for many workspaces |

**Execute / GA Trigger** — trigger GA activation events

| Method | Path | Description |
|---|---|---|
| PUT | `/api/v1/execute/by-releasecohort/{releaseCohortId}/product/{productRegistrationId}` | Mark product released for a release cohort |
| PUT | `/api/v1/execute/by-release/{releaseId}/cohort/{cohort}/product/{productRegistrationId}` | Mark product released for release+cohort, trigger async feature activation |
| PUT | `/api/v1/execute/by-feature/{featureId}/cohort/{cohort}` | Mark product released for a feature's cohort |
| POST | `/api/v1/execute/by-release/{releaseId}/cohort/{cohort}/product/{productRegistrationId}/activate-features` | Activate features for specific workspaces in a release cohort (can be called independently or async after execute) |

**Modules** — manage functional sub-groupings of features

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/module` | List modules |
| POST | `/api/v1/module` | Create a module |
| GET | `/api/v1/module/{id}` | Get a module |
| PUT | `/api/v1/module/{id}` | Update a module |
| DELETE | `/api/v1/module/{id}` | Delete a module |

### SDKs and Tools

| Resource | Link |
|---|---|
| C# SDK (GitHub) | https://github.com/tyler-technologies/Tyler.AlignedReleases.Sdk |
| C# SDK (Artifactory NuGet) | https://tylertech.jfrog.io/ui/packages/nuget:%2F%2FTyler.AlignedReleases.Sdk |
| Platform Service GitHub Repo | https://github.com/tyler-technologies/platformservice |
| Teams Channel (Cloud Platform Community) | https://teams.microsoft.com/l/channel/19%3a1e6bcc02bd3242a193bf9171a51a0395%40thread.tacv2/Cloud%2520Platform%2520Community?groupId=d9db441d-35fa-433c-8fe0-ff7fe5825d3c&tenantId=7cc5f0f9-ee5b-4106-a62d-1b9f7be46118 |

### Access Summary

| Property | Value |
|---|---|
| Externally available | Yes |
| Usable by app teams | Yes |
| API ingress | `{BASE_URL}/portal/platformservice` |
| Auth | OAuth 2.0 client credentials, scope `tyler-cloud-platform-api-access` |
| SDK package | `Tyler.AlignedReleases.Sdk` (NuGet) |

---

## Integration Checklist

> Note: The official integration checklist page (https://docs.tylerdev.io/aligned-releases/integration-checklists/aligned-releases-checklist) is currently under construction. Use the workflow steps below as a practical substitute until the official checklist is published.

**Prerequisites**
- [ ] Obtain OAuth 2.0 `client_id` and `client_secret` from Tyler Identity Gateway for your target environment
- [ ] Confirm your `productRegistrationId` in Product Registration
- [ ] Identify all workspace keys (`workspaceKey`) your product deploys to
- [ ] Determine which quarterly release your features target

**Feature Setup**
- [ ] Create feature record via `POST /api/v1/feature` with client-facing name, description, and documentation links
- [ ] Confirm feature is in `Planned` state

**Preview Phases (if applicable)**
- [ ] Transition feature to `Private` preview (`PUT /api/v1/feature/{id}/state/private`)
- [ ] Activate feature for selected Private Preview workspaces (`PUT /api/v1/feature/{id}/workspace/{key}/true`)
- [ ] Gather feedback; when ready, transition to `Public` preview (`PUT /api/v1/feature/{id}/state/public`)

**GA Preparation**
- [ ] Assign all relevant workspaces to cohorts (`PUT /api/v1/cohort-assignment/product/{product}/workspace/{key}/cohort/{n}`)
- [ ] Assign feature to target quarterly release (`PUT /api/v1/feature/{id}/release/{releaseId}`)
- [ ] Move feature state to `GA` (`PUT /api/v1/feature/{id}/state/ga`)

**GA Execution**
- [ ] Confirm release cohort IDs and window dates for your release
- [ ] Trigger GA rollout for each cohort as its window opens (`PUT /api/v1/execute/by-releasecohort/{id}/product/{product}`)
- [ ] Verify activations via `POST /api/v1/feature/{id}/activations`

---

## Notes for the Chatbot

1. **Section is under construction.** The official Blueprint docs for Aligned Releases are marked "under construction / work in progress." The content in this file is drawn from all available source material as of the knowledge cutoff; direct users to the live docs or Teams channel for the latest updates.
2. **Cohort ≠ Feature Flag.** A cohort is a scheduling concept in AR (which week clients receive GA). A Feature Flag is the technical gating mechanism owned by the product team. AR records the desired state; product teams' flag tooling implements the actual activation.
3. **GA-only cohorts.** Cohort assignments apply only to GA features. Preview participation is managed outside the cohort mechanism.
4. **Creating releases is OneTyler's job.** Product teams typically start at the "Adding a Feature" step. Releases and cohort windows are pre-created by the platform team.
5. **`productRegistrationId` values.** These come from Product Registration, not from AR itself. If a user asks "what is my productRegistrationId?" refer them to `Docusaurus-ProductSystemReg.md`.
6. **Three execute endpoints.** The GA trigger has three equivalent entry points (`by-releasecohort`, `by-release+cohort`, `by-feature+cohort`). Steer users to `by-releasecohort` as the most explicit and commonly documented form.
7. **Dedicated Foundry agents.** For questions about Ops Center → https://docs.tylerdev.io/app-guides/ops/ops-center/overview/ | For Support Access Center (SAC) → https://docs.tylerdev.io/ops/support-access-center/ | For Identity/authentication → https://docs.tylerdev.io/identity
