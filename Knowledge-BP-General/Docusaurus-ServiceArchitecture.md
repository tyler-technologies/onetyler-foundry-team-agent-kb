# TCP Service Architecture: Authorization, Search, Webhooks, TCP Eventing, and Community Service Directory

Source: Tyler Blueprint Docusaurus — https://docs.tylerdev.io/platform-architecture/service-architecture/overview/
Domain: Blueprint General — Tyler Cloud Platform / Blueprint docs not served by a specialized Foundry agent
Audience: Tyler platform and service engineers building services that integrate with the Tyler Cloud Platform (TCP)

**Companion documents:**
- `_START_HERE.md` — corpus routing guide
- `Docusaurus-PlatformOverview.md` — TCP platform concepts and high-level architecture
- `Docusaurus-CloudPlatformAPI.md` — API reference companion to these architecture guides (Swagger docs, endpoint catalog)
- `Docusaurus-ClientApps.md` — frontend / BFF application patterns
- `Docusaurus-OpsApps.md` — Ops Center and platform operations apps
- `Docusaurus-DevOps.md` — CI/CD, Harness, Terraform, container builds
- `Docusaurus-Security.md` — security posture, scanning, secrets management
- `Docusaurus-ProductSystemReg.md` — product and app registration in TCP
- `Docusaurus-AlignedReleases.md` — release coordination across TCP services
- `Docusaurus-StatusPageAndSLA.md` — platform SLA and status page

> **Dedicated-agent pointer:** Three areas have their own Foundry agents — send queries there instead of answering from this file:
> - **Ops Center** → https://docs.tylerdev.io/app-guides/ops/ops-center/overview/
> - **Support Access Center (SAC)** → https://docs.tylerdev.io/ops/support-access-center/
> - **Identity** → https://docs.tylerdev.io/identity

---

## How to use this guide

| User intent | Go to section |
|---|---|
| "Does this permission exist? How do I add one?" | [Authorization — Adding Permissions](#1-authorization) |
| "How do I set up a service account for my new service?" | [Authorization — Registering Service Accounts](#registering-a-service-account) |
| "What permission does endpoint X require?" | [Authorization — Permissions per Endpoint](#permissions-per-endpoint) |
| "How does TCP Search work? Why not SQL?" | [Search — Architecture](#2-search) |
| "How do I hook into EF Core to trigger indexing?" | [Search — EF Core Interceptor](#adding-an-ef-core-interceptor) |
| "How do I write a search event handler?" | [Search — Search Event Handler](#adding-a-search-event-handler) |
| "How do I reindex all records?" | [Search — Reindex Handler](#adding-a-reindex-handler) |
| "How do I add a search endpoint with facets/aliases?" | [Search — Search Endpoint](#adding-a-search-endpoint) |
| "How does TCP send webhooks to external consumers?" | [Webhooks — Architecture](#3-webhooks) |
| "How do I create a new webhook event type?" | [Webhooks — Developing a Webhook](#developing-a-webhook-event) |
| "How does a consumer subscribe to webhooks?" | [Webhooks — Subscribing](#subscribing-to-a-webhook) |
| "Where are all the webhook message type schemas?" | [Webhooks — Message Types](#webhook-message-types) |
| "How does TCP internal eventing work (SQS + EventBridge)?" | [TCP Eventing — Architecture](#4-tcp-eventing) |
| "How do I add a new event type?" | [TCP Eventing — Adding Events](#adding-event-types) |
| "How do I set up my service to publish events?" | [TCP Eventing — Publisher Setup](#setting-up-an-event-publisher) |
| "How do I set up my service to subscribe to events?" | [TCP Eventing — Subscriber Setup](#setting-up-an-event-subscriber) |
| "What happens when a message fails to publish or handle?" | [TCP Eventing — Failed Messages](#handling-failed-messages) |
| "What is CSD and why is it the reference project?" | [Community Service Directory — Introduction](#5-community-service-directory-csd) |
| "How does CSD's architecture fit together?" | [CSD — Architecture Overview](#csd-architecture-overview) |
| "How does CSD handle incoming TCP webhook events?" | [CSD — Webhook Handler](#csd-webhook-handler) |
| "How does CSD's event handler work?" | [CSD — Event Handler](#csd-event-handler) |
| "How does CSD branding work?" | [CSD — Branding](#csd-branding) |

---

## Glossary

| Term | Meaning |
|---|---|
| TCP | Tyler Cloud Platform — the core platform all Tyler web products integrate with |
| TID / Tyler Identity | Tyler's identity provider system; TID Gateway Workforce handles service-to-service (CCF) tokens |
| CCF | Client Credential Flow — service-to-service authentication using clientId + clientSecret |
| Styra DAS | The OPA-based authorization system TCP uses to enforce fine-grained permissions |
| CQRS | Command Query Responsibility Segregation — pattern separating writes (SQL) from reads (OpenSearch) |
| SQS | AWS Simple Queue Service — backbone of TCP Eventing and CSD internal eventing |
| EventBridge | AWS EventBridge — routes internal events from the input SQS queue to subscriber SQS queues |
| OpenSearch Serverless | AWS-managed OpenSearch used as TCP's search index store |
| BFF | Backend-for-Frontend — a backend service exclusively serving one frontend application |
| DLQ | Dead-letter queue — receives messages that have exhausted retry attempts |
| CRD | Kubernetes Custom Resource Definition — used to register event schemas |
| Consul | Distributed key-value store used for live, hot-reloadable configuration in Kubernetes |
| git2consul | Tool that syncs GitHub config repos to Consul automatically on PR merge |
| CSD | Community Service Directory — TCP's reference product for divisional developer integration patterns |
| HPA | Kubernetes Horizontal Pod Autoscaler |
| Forge | Tyler's open-source Angular component library and design system |
| tcp-cli | Tyler Cloud Platform CLI — used for service account registration and platform data queries |

---

## 1. Authorization

Live doc: https://docs.tylerdev.io/platform-architecture/service-architecture/Authorization/adding-permissions/

TCP uses Styra DAS (Open Policy Agent) for fine-grained service authorization. Every service-to-service call in the platform is gated by a permission. Permissions are assigned directly to **service accounts** (not roles).

### Permissions per Endpoint

**Use when:** You need to know what permission a specific TCP API endpoint requires.

A CSV file is auto-generated from the codebase listing every TCP service endpoint and its required permission(s):

- Download CSV: https://docs.tylerdev.io/authz-permissions.csv

This is the authoritative lookup for building a service account's permission list.

---

### Adding a Permission

**Use when:** The permission you need does not exist in the authorization system.

**Prerequisites:** If the permission already exists, skip to [Registering a Service Account](#registering-a-service-account).

**Steps:**
1. Add the permission following the instructions in the [TCP.Authorization README.md](https://github.com/tyler-technologies/TCP.Authorization/blob/main/README.md#adding-new-permissions).
2. Seek PR approvals — consistency in the authorization system requires peer review.
3. Merge the PR. Merging automatically propagates the permission to Styra DAS in all environments.

---

### Registering a Service Account

**Use when:** You are writing a new service (API or BFF) that calls upstream TCP services secured by the authorization system.

**Prerequisites:**
- Know which upstream API calls your service makes.
- Look each call up in the [permissions CSV](https://docs.tylerdev.io/authz-permissions.csv) to build your required permissions list.
- Have `tcp-cli` installed and configured (see [tcp-cli README](https://github.com/tyler-technologies/tcp-cli/blob/main/README.md)).

**Key concepts:**
- Every service in TCP owns its own unique **service account per environment** (tcpci, tcpqa, tcpprod).
- A service account has a `clientId` (like a username) and a `clientSecret` (like a password).
- Assign permissions directly to service accounts. **Do not assign roles to service accounts.**
- ClientIds for TCP services are always named identically to their Kubernetes service name (e.g., `tcp-support-accounts-api`).

**Step 1 — Generate gateway clients.**
You need one gateway client per environment. Contact the API team or the Identity team to create clients in the Tyler Identity Workforce Gateway (`tid-gateway-workforce`).

**Step 2 — Create the service account JSON definition.**

```json
{
    "clientId": "tcp-new-api-service",
    "description": "tcp-new-api-service",
    "permissions": [
        { "action": "create", "resource": "userprofile" },
        { "action": "read",   "resource": "userprofile" },
        { "action": "update", "resource": "userprofile" }
    ]
}
```

To list all available permissions: `tcp-cli list permissions`

If a permission you need does not exist, see [Adding a Permission](#adding-a-permission) first.

**Step 3 — Register the service account in each environment.**

```bash
tcp-cli config use tcpci
tcp-cli register serviceaccount -f ./path/to/tcpci.json

tcp-cli config use tcpqa
tcp-cli register serviceaccount -f ./path/to/tcpqa.json

tcp-cli config use tcpprod
tcp-cli register serviceaccount -f ./path/to/tcpprod.json
```

You may register environments individually — you are not required to do all three at once.

---

## 2. Search

Live doc: https://docs.tylerdev.io/platform-architecture/service-architecture/Search/search-architecture/

TCP Search replaces SQL-based filtered list views with OpenSearch Serverless. It enables search on any indexed field, wildcard searches, faceted aggregations, and faster retrieval for paged views — capabilities where SQL performs poorly.

### Architecture

TCP Search implements the **CQRS (Command Query Responsibility Segregation)** pattern:

- **Writes** — SQL (RDS) remains responsible for create, update, and delete.
- **Reads (search)** — OpenSearch Serverless serves search queries; SQL is not used for search.

**How the index stays current:**

1. An Entity Framework Core (EF Core) interceptor detects changes (create/update/delete) in the API that fronts RDS.
2. The interceptor publishes a slim event via TCP Eventing.
3. A search event handler picks up the event, enriches the payload with any additional data needed, and writes to OpenSearch.

**Full implementation flow:**

EF Core interceptor → TCP Eventing (SQS/EventBridge) → Search event handler → OpenSearch Serverless → Search endpoint queries OpenSearch

Repos: [TCP.Search (tcp-search-api and tcp-search-api-event-handler)](https://github.com/tyler-technologies/TCP.Search)

---

### Adding an EF Core Interceptor

**Use when:** You want an API that fronts RDS to automatically publish an event whenever a relevant entity is saved.

**Prerequisites:** The service must already be set up for TCP Eventing publishing. See [Setting Up an Event Publisher](#setting-up-an-event-publisher).

**Step 1 — Add the interceptor to `DbContextPool`.**

In `ServiceCollectionExtensions.cs` (where `AddDbContext` / `AddDbContextPool` is called):

```csharp
services.AddDbContextPool<ApplicationDbContext>((sp, options) =>
    options.UseMySql(...)
        .AddTcpEventingInterceptors(
            new EventingSaveChangesInterceptor(
                sp.GetRequiredService<ILoggerFactory>(),
                sp.GetRequiredService<ITcpSqsPublisher>())
        )
);
```

**Step 2 — Create the `EventingSaveChangesInterceptor` class.**

Define `EntityDefinition[]` — one per entity type and state combination. Each definition specifies:
- `EntityType` — the EF entity class
- `State` — `EntityState.Added`, `EntityState.Modified`, or `EntityState.Deleted`
- `EntityEventMapper` — delegate that maps the entity to a slim event (include only the id/key needed to reload in the handler)

Example (watches `Portal` and `Customer` entities):

```csharp
public class EventingSaveChangesInterceptor(ILoggerFactory loggerFactory = null, ITcpSqsPublisher sqsPublisher = null)
    : EventingSaveChangesInterceptorBase(loggerFactory, sqsPublisher)
{
    protected override EntityDefinition[] EntityDefinitions =>
    [
        new()
        {
            EntityType = typeof(Portal),
            State = EntityState.Added,
            EntityEventMapper = e =>
            {
                var entity = e.Entry.Entity as Portal;
                return [new WorkspaceCreated { WorkspaceId = entity.Id, WorkspaceKey = entity.PortalId }];
            },
        },
        // ... Modified and Deleted variants for Portal, Added/Modified/Deleted for Customer
    ];
}
```

**Keep event payloads as small as possible** — only include what the handler needs to look up the full record. The interceptor runs inline during saves; slow event publishing will slow down the save operation.

**Step 3 — Declare publishers in `Startup.cs`.**

```csharp
services.SetupTCPEventing(Configuration, true, (b, opts) =>
{
    b
        .AddSQSPublisher<WorkspaceCreated>(opts)
        .AddSQSPublisher<WorkspaceUpdated>(opts)
        .AddSQSPublisher<WorkspaceDeleted>(opts)
        .AddSQSPublisher<OrganizationCreated>(opts)
        .AddSQSPublisher<OrganizationUpdated>(opts)
        .AddSQSPublisher<OrganizationDeleted>(opts);
});
```

**Step 4 — Add event types if needed.** See [Adding Event Types](#adding-event-types).

**Step 5 — Apply Terraform.** See [Setting Up an Event Publisher](#setting-up-an-event-publisher) for the required Terraform infrastructure (SQS IAM permissions, DynamoDB failed-messages table permissions).

---

### Adding a Search Event Handler

**Use when:** You need to handle the slim events published by the EF Core interceptor and write enriched data to OpenSearch.

**Prerequisites:** EF Core interceptor is in place (see above). You are working in the [tcp-search-api-event-handler](https://github.com/tyler-technologies/TCP.Search/tree/main/tcp-search-api-event-handler) project.

**Step 1 — Add a handler class** in the `Handlers` folder. Inherit from `EventHandlerBase<TMessage>`:

```csharp
public class OrganizationCreatedHandler(
    ILogger<OrganizationCreatedHandler> logger,
    IIndexService indexService)
    : EventHandlerBase<OrganizationCreated>(logger)
{
    public override async Task<MessageProcessStatus> HandleMessage(
        OrganizationCreated message,
        CancellationToken cancellationToken)
    {
        await indexService.IndexOrganizations(message.OrganizationKey, cancellationToken);
        return MessageProcessStatus.Success();
    }
}
```

**Step 2 — Enrich the payload.** Load additional data required for the search page from other services. Everything displayed on the search page must already be in the OpenSearch index — do not enrich at query time.

**Trap — entity-not-found on update events:** It is normal to receive an `entity-updated` event for an entity that was subsequently deleted. In the update handler, if the entity does not exist, log a warning and return without throwing — the corresponding delete event will arrive shortly.

If an exception is thrown, TCP Eventing will retry the message (see [Handling Failed Messages](#handling-failed-messages)).

---

### Adding a Reindex Handler

**Use when:** You need to bulk-replace the OpenSearch index for an entity type (e.g., after a data migration, schema change, or to recover from a corrupted index).

**Recommended approach — single handler / single thread** (avoids database and service contention from high concurrency).

**Reindexing algorithm:**
1. Load all entities requiring reindexing in batches from the API that fronts RDS.
2. Enrich each batch with any additional data from other services (same enrichment as the per-entity event handler).
3. Write each batch to OpenSearch; accumulate the set of entity IDs written.
4. Delete all OpenSearch records whose ID is not in the accumulated set. This handles records that were deleted in SQL but not yet removed from the index.

**Step 1 — Create a reindex event type.** See [Adding Event Types](#adding-event-types).

**Step 2 — Create the handler class.** Same pattern as any other search event handler (see above).

**Step 3 — Add a reindex endpoint** in the [ReindexController.cs](https://github.com/tyler-technologies/TCP.Search/blob/main/tcp-search-api/Server/Controllers/api/ReindexController.cs) in the `tcp-search-api`:

```csharp
[Authorize(Policy = Permissions.Policy.REINDEX_ORGANIZATION)]
[HttpPost("organizations")]
[ProducesResponseType(StatusCodes.Status500InternalServerError)]
[ProducesResponseType(typeof(DateTime), StatusCodes.Status202Accepted)]
public async Task<IActionResult> ReindexOrganizations()
{
    await _publisher.Publish(new ReindexOrganizations());
    return Accepted(DateTime.UtcNow);
}
```

The endpoint publishes a reindex event and returns 202 Accepted immediately. The actual work happens asynchronously in the event handler.

---

### Adding a Search Endpoint

**Use when:** You want to expose user-facing search over an OpenSearch index.

**Use when with facets/aggregations:** Check with product management to determine which fields users can search and whether faceted filtering is needed.

Reference implementations: [SearchController.cs](https://github.com/tyler-technologies/TCP.Search/blob/main/tcp-search-api/Server/Controllers/api/SearchController.cs) (with facets), [audit search](https://github.com/tyler-technologies/tcp-audit-opensearch/blob/main/tcp-audit-opensearch/Server/Controllers/api/SearchController.cs) (without facets).

**Setting up field aliases** (so users can search by friendlier names):

In the `SetupAliases()` method inside `SearchService.cs` in the `tcp-search-api`:

```csharp
if (!(await _client.Indices.ExistsAsync(_organizationIndex)).Exists)
    await _client.Indices.CreateAsync(_organizationIndex, c => c.Map(m =>
        m.AutoMap<Organization>()
         .Properties<Organization>(p => p.AddOrganizationAliases())));
else
    await _client.Indices.PutMappingAsync<Organization>(s => s
        .Index(_organizationIndex)
        .AutoMap()
        .Properties(p => p.AddOrganizationAliases()));
```

Alias helper example — maps `Key` to three searchable aliases:

```csharp
public static PropertiesDescriptor<Organization> AddOrganizationAliases(
    this PropertiesDescriptor<Organization> descriptor)
{
    descriptor
        .AddAlias(x => x.Key, "OrganizationId", "OrgId", "CustomerId")
        .AddAlias(x => x.AllowTylerSupportAccess, "TylerAccess");
    return descriptor;
}
```

If the index does not exist at startup, `CreateAsync` creates it with aliases. If it exists, `PutMappingAsync` applies aliases without data loss.

---

## 3. Webhooks

Live doc: https://docs.tylerdev.io/platform-architecture/service-architecture/Webhooks/architecture/

TCP Webhooks send outbound HTTPS messages to **external** subscribers (other Tyler teams, organizations, or customers) when platform events occur. External subscribers cannot directly access TCP's internal SQS/EventBridge infrastructure — webhooks are the sanctioned integration surface.

Repo: [tcp-webhook-api](https://github.com/tyler-technologies/tcp-webhook-api)

### Architecture

**Three-step flow from internal event to external webhook call:**

**Step 1 — Publish an internal event.**
Every outbound webhook originates from an internal TCP event published to the SQS input queue, which flows to EventBridge.

**Step 2 — Webhook Event Relay Service** ([tcp-webhook-event-relay](https://github.com/tyler-technologies/tcp-webhook-api/tree/main/csharp/tcp-webhook-event-relay)) subscribes to relevant internal events and:
- Translates the internal message schema to the external webhook message schema.
- Enriches the outbound message with any additional data not in the internal event.
- Stores the outbound message payload in a DynamoDB in-transit table (keeps SQS messages small).
- Loads the list of subscribers for this message type.
- Publishes one `SendWebhook` message per subscriber.

**Step 3 — Webhook Event Handler** ([tcp-webhook-event-handler](https://github.com/tyler-technologies/tcp-webhook-api/tree/main/csharp/tcp-webhook-event-handler)) listens for `SendWebhook` events and:
- Loads the full payload from DynamoDB.
- Loads authentication credentials for the subscription.
- Sends the webhook payload over HTTPS to the subscriber's registered URL.

---

### Developing a Webhook Event

**Use when:** You need to create a new externally-facing webhook event type.

**Prerequisites:** Understand TCP Eventing (see [TCP Eventing section](#4-tcp-eventing)), since webhooks are driven by internal events.

**Overview of steps:**
1. Create an internal event type (if one does not already exist).
2. Publish the internal event from an internal TCP service.
3. Create an external webhook message type.
4. Create a relay handler in `tcp-webhook-event-relay`.
5. Register the new message and configure Terraform.

**Step 1 — Create internal event type** (if needed): See [Adding Event Types](#adding-event-types).

**Step 2 — Publish the internal event**: See [Setting Up an Event Publisher](#setting-up-an-event-publisher).

**Step 3 — Create the webhook message type** in [TCP.Webhook.Messages](https://github.com/tyler-technologies/tcp-webhook-api/tree/main/csharp/TCP.Webhook.Messages). Messages must:
- Inherit from `WebhookMessageBase` and implement `IWebhookMessage`.
- Be placed in the `V1` folder (new messages) or the next version folder (revisions).
- Carry class-level attributes: `[Category(...)]`, `[MessageType("kebab-case-name")]`.
- Use `[Filterable]` on properties subscribers may filter on.
- Optionally use `[AllowedCustomFilters(CustomFilterTypes.ProductLicensed)]` for the Product Licensed custom filter.

```csharp
[Category(MessageCategory.IdentityWorkforce)]
[MessageType("workforce-user-deleted")]
[AllowedCustomFilters(CustomFilterTypes.ProductLicensed)]
public class WorkforceUserDeleted : WebhookMessageBase, IWebhookMessage
{
    [Required, Filterable] public string Sub { get; set; }
    [Required, Filterable] public string OrganizationKey { get; set; }
    [Required, Filterable] public string Username { get; set; }
    [Required, Filterable] public string GivenName { get; set; }
    [Required, Filterable] public string FamilyName { get; set; }
    [Required, Filterable] public string Email { get; set; }
}
```

**Critical:** Add a `[JsonDerivedType]` attribute on `IWebhookMessage` for your new message:

```csharp
[JsonDerivedType(typeof(WorkforceUserDeleted), "workforce-user-deleted")]
```

Skipping this step causes serialization exceptions at runtime.

Then register the message in `ApplicationBaseDbContext.cs` (add a row to the `Messages` table, increment `MessageId`) and generate a migration.

**Step 4 — Create the relay handler** in the [Handlers folder](https://github.com/tyler-technologies/tcp-webhook-api/tree/main/csharp/tcp-webhook-event-relay/Handlers). Inherit from `PublishWebhookMessageBase<TInternalEvent, TWebhookMessage>` and implement `BuildWebhookMessage`:

```csharp
public class ProductUnlicensedHandler(
    ILoggerFactory loggerFactory,
    IWebhookPublisher publisher,
    IWebhookFilterService filterService,
    IPlatformDataApiSDK platformSdk)
    : PublishWebhookMessageBase<InternalEvents.ProductUnlicensed, WebhookEvents.ProductUnlicensed>(
        loggerFactory.CreateLogger<ProductUnlicensedHandler>(), publisher, filterService)
{
    protected override async Task<WebhookEvents.ProductUnlicensed> BuildWebhookMessage(
        InternalEvents.ProductUnlicensed message,
        CancellationToken cancellationToken)
    {
        var org = await _platformSdk.GetCustomerByIdAsync(message.OrganizationId, cancellationToken);
        return new WebhookEvents.ProductUnlicensed
        {
            RegistrationId = message.RegistrationId,
            OrganizationKey = org.CustomerId,
        };
    }
}
```

If you have a custom filter (e.g., `ProductLicensed`), also override `CanPublish` — and always call `base.CanPublish` first:

```csharp
protected override async Task<bool> CanPublish(IWebhookMessage message, Registration registration) =>
    await base.CanPublish(message, registration) &&
    await _filter.ProductIsLicensed(registration, ((WorkforceProfileEmailChanged)message).Organization);
```

**Step 5 — Register and configure:**
- Register the handler in [Program.cs](https://github.com/tyler-technologies/tcp-webhook-api/blob/main/csharp/tcp-webhook-event-relay/Program.cs).
- Add the internal event to the `message_types` variable in [main.tf](https://github.com/tyler-technologies/tcp-webhook-api/blob/main/csharp/tcp-webhook-event-relay/infrastructure/main.tf) so EventBridge routes it to the relay.

---

### Subscribing to a Webhook

**Use when:** An external consumer (Tyler team, customer-adjacent service) needs to receive outbound webhook messages from TCP.

**Prerequisites:** Know the message type you want and your endpoint URL (must be HTTPS in AWS; HTTP only allowed locally). TCP currently has no subscription UI — you call the API directly.

**Step — POST to the Registrations controller** ([RegistrationsController](https://github.com/tyler-technologies/tcp-webhook-api/blob/main/csharp/tcp-webhook-api/tcp-webhook-api/Server/Controllers/api/RegistrationsController.cs)):

**Registration fields:**

| Field | Description |
|---|---|
| `ExternalReferenceId` | Subscriber-assigned unique identifier for this subscription |
| `MessageType` | The webhook message type in kebab-case (e.g., `product-licensed`) |
| `ContactName` | Person TCP can contact if webhook delivery fails |
| `ContactEmail` | Email for failure contact |
| `Url` | Subscriber endpoint; must be HTTPS in AWS |
| `Authorization` | Authentication method: `Jwt`, `ApiKey`, or `None` (local dev only) |
| `Filter` | Optional: filter deliveries by a `Filterable` property value |
| `ProductLicensedFilter` | Optional: only deliver for orgs that have specified product(s) licensed |

**Authentication methods:**

*JWT (Client Credential Flow):*
```json
{
  "Authorization": {
    "Type": "Jwt",
    "Authority": "https://authority.url/token/endpoint",
    "ClientId": "ccf-client-id",
    "ClientSecret": "ccf-client-secret"
  }
}
```

*API Key:*
```json
{
  "Authorization": {
    "Type": "ApiKey",
    "APIKey": "some-api-key-value",
    "APIKeyHeader": "X-API-KEY"
  }
}
```

*None — local development only. Services in AWS will fail to send without credentials.*

**Filtering examples:**

Filter on a single value (only receive `ProductLicensed` events for `StateOfKansas`):
```json
{
  "Filter": {
    "Field": "OrganizationKey",
    "Operator": "Equals",
    "Value": "StateOfKansas"
  }
}
```

Filter on a list of values (`OneOf` operator):
```json
{
  "Filter": {
    "Field": "OrganizationKey",
    "Operator": "OneOf",
    "Values": ["StateOfKansas", "CityOfLasVegas"]
  }
}
```

`ProductLicensedFilter` — only receive events for orgs that have specific products licensed:
```json
{
  "ProductLicensedFilter": {
    "ProductRegistrationIds": ["TylerPetRegistration"]
  }
}
```

**Warning:** Combining `ProductLicensedFilter` with an `OrganizationKey` filter that refers to an org that doesn't have the specified product licensed will result in zero deliveries.

**Unsubscribing:** Call the `DELETE` endpoint on the [Registrations controller](https://github.com/tyler-technologies/tcp-webhook-api/blob/main/csharp/tcp-webhook-api/tcp-webhook-api/Server/Controllers/api/RegistrationsController.cs).

---

### Webhook Message Types

**Use when:** You need to see what message types are available and their field schemas.

Message type schema documentation is auto-generated by a GitHub Actions workflow each time a message type is added, updated, or deleted in [TCP.Webhook.Messages](https://github.com/tyler-technologies/tcp-webhook-api/tree/main/csharp/TCP.Webhook.Messages).

Reference the generated docs in the [docs folder of tcp-webhook-api](https://github.com/tyler-technologies/tcp-webhook-api/tree/main/docs).

---

## 4. TCP Eventing

Live doc: https://docs.tylerdev.io/platform-architecture/service-architecture/tcp-eventing/architecture/

TCP Eventing is the internal asynchronous messaging system for the Tyler Cloud Platform. It uses **AWS SQS** as the transport and **AWS EventBridge** as the router. Services publish events when data changes; other services subscribe and react asynchronously.

Repo: [TCP.Eventing](https://github.com/tyler-technologies/TCP.Eventing)
NuGet: `TCP.Eventing.AmazonSqs`

### Architecture

**Event lifecycle:**
1. Publisher validates the message against its JSON schema (stored in DynamoDB via schema registry).
   - Validation failure → message stored in DynamoDB failure outbox.
2. Publisher sends the validated JSON to the **input SQS queue**.
   - SQS unavailable → message stored in DynamoDB failure outbox.
3. EventBridge picks up the event from the input queue, matches it to routing rules, and delivers it to the appropriate subscriber SQS queues.
   - EventBridge failure → message goes to the input dead-letter queue.
4. Event handler(s) poll their subscriber SQS queue, process the message, call APIs, and optionally publish additional events.
   - Handler exception → retried 3 times, then dead-lettered to the handler's DLQ.

**Key infrastructure:**
- One shared input SQS queue (all publishers use the same queue).
- Per-subscriber SQS queues + dead-letter queues, provisioned via Terraform.
- DynamoDB table for failed messages (publisher failures).
- DynamoDB table for the schema registry.

---

### Adding Event Types

**Use when:** The event type you need does not exist in TCP.Eventing, or you need to evolve an existing event type.

**Steps:**
1. Add the event class under `TCP.Eventing.Messages/V{VersionNumber}` in the [TCP.Eventing repo](https://github.com/tyler-technologies/TCP.Eventing).
   - New event: use `V1`.
   - Evolving an existing event: copy to the next version folder (e.g., `V1 → V2`) and modify the copy.
2. The event class must:
   - Be in namespace `TCP.Eventing.Messages.V{VersionNumber}`
   - Descend from `EventBase`
   - Use [Json.Schema.Generation](https://docs.json-everything.net/schema/schemagen/schema-generation/#schema-schemagen-best-practices) attributes for validation rules (`[Required]`, `[MinLength]`, etc.)
3. A GitHub Actions workflow auto-generates a Kubernetes CRD (EventSchemaRegistration) containing the schema definition and deploys it to the CI environment on PR merge.
4. To promote to QA: copy the schema YAML from `templates/value-overrides/tcpci/events` → `tcpqa/events`.
5. To promote to Prod: copy from `tcpqa/events` → `tcpprod/events`.
6. Seek PR approvals — consistency in the eventing system requires peer review.
7. Any service publishing the new event must update to the new version of the `TCP.Eventing.Messages` NuGet.

---

### Schema Validation

All events are validated at publish time against the JSON schema stored in DynamoDB. Automation handles schema generation and registration:

- Developer creates a new message type in [TCP.Eventing](https://github.com/tyler-technologies/tcp.eventing) and opens a PR.
- GitHub Actions generates a Kubernetes CRD containing the schema definition.
- On PR merge, the [TCP Registration Operator](https://github.com/tyler-technologies/tcp-registration-operator) deploys the schema to each environment and stores it in DynamoDB.
- At runtime, `TCP.Eventing.AmazonSqs` fetches the schema from DynamoDB and validates outgoing messages before they are sent.

---

### Setting Up an Event Publisher

**Use when:** Your service needs to publish events into the TCP eventing pipeline.

**Prerequisites:** Define the event type first (see [Adding Event Types](#adding-event-types)).

**Step 1 — Add the NuGet.**
```
dotnet add package TCP.Eventing.AmazonSqs
```

**Step 2 — Register publishers in `Startup.cs` / `Program.cs`.**
Pass `true` for `includePublisher`. Declare every message type this service will publish:

```csharp
services.SetupTCPEventing(Configuration, true, (b, opts) =>
{
    b
        .AddSQSPublisher<ProfileCreated>(opts)
        .AddSQSPublisher<ProfileUpdated>(opts)
        .AddSQSPublisher<ProfileDeleted>(opts);
});
```

**Step 3 — Add schema registry permission to service account.**
The publisher must be able to call the `tcp-eventing-schema-registry` API to fetch schemas at runtime:

```json
{ "action": "read", "resource": "eventschema" }
```

Add this to the service account via the TCP CLI or the authorization config UI (`https://admin.<site>.com/platform/authorization-config`).

**Step 4 — Add Terraform resources.**

SQS publish permissions (IAM policy document — apply to the service's IAM role):
```hcl
data "aws_iam_policy_document" "sqs" {
  statement {
    actions   = ["sqs:SendMessage", "sqs:GetQueueAttributes", "sqs:GetQueueUrl"]
    resources = [<ARN_OF_INPUT_QUEUE>]
  }
}
```

KMS permissions for SQS encryption:
```hcl
data "aws_iam_policy_document" "kms_sqs" {
  statement {
    actions   = ["kms:Decrypt", "kms:GenerateDataKey", "kms:Encrypt*"]
    resources = var.kms_sqs_arn_list
  }
}
```

DynamoDB failed-messages table permissions (for SQS outage fallback):
```hcl
data "aws_iam_policy_document" "dynamodb" {
  statement {
    actions   = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DescribeTable"]
    resources = [<ARN_OF_FAILED_MESSAGES_TABLE>]
  }
}
```

Contact the infrastructure team if you need help with Terraform.

---

### Setting Up an Event Subscriber

**Use when:** Your service needs to consume events from the TCP eventing pipeline.

**Step 1 — Add the NuGet.**
```
dotnet add package TCP.Eventing.AmazonSqs
```

**Step 2 — Register handlers in `Startup.cs` / `Program.cs`.**
Pass `false` for `includePublisher` (or `true` if the service also publishes). Add an `SQSPoller` and declare each message type and its handler:

```csharp
builder.Services.SetupTCPEventing(builder.Configuration, false, (b, opts) =>
{
    b.AddSQSPoller(opts.SubscriberQueue);
    b.AddMessageHandler<CreateProfileHandler, ProfileCreated>();
    b.AddMessageHandler<DeleteOrganizationHandler, OrganizationDeleted>();
    b.AddMessageHandler<DeleteProfileHandler, ProfileDeleted>();
    b.AddMessageHandler<UpdateProfileHandler, ProfileUpdated>();
});
```

**Step 3 — Add Terraform resources.**

Use the [tcp-authorization-api's event-router Terraform](https://github.com/tyler-technologies/tcp-authorization-api/blob/main/infrastructure/authorization-event-router/main.tf) as a reference. The `event-handler` Terraform module creates:
- Subscriber SQS queue
- Dead-letter SQS queue
- EventBridge routing rule for specified message types
- CloudWatch integration and EventBridge IAM permissions

```hcl
locals {
  message_types = [
    "TCP.Eventing.Messages.V1.ProfileCreated",
    "TCP.Eventing.Messages.V1.ProfileDeleted",
    "TCP.Eventing.Messages.V1.ProfileUpdated",
    "TCP.Eventing.Messages.V1.OrganizationDeleted"
  ]
}

module "event_handler" {
  source              = "app.terraform.io/tyler-corp/event-handler/tcp"
  version             = "0.2.2"
  context             = module.migrated_context.context
  enabled             = var.platform_eventing_enabled
  kms_key_arn         = var.primary_eventbridge_kms_arn
  eventbridge_bus_arn = var.primary_eventbridge_bus_arn
  message_types       = local.message_types
}
```

SQS read permissions (IAM policy document):
```hcl
data "aws_iam_policy_document" "sqs" {
  statement {
    actions   = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:GetQueueAttributes",
      "sqs:GetQueueUrl",
      "sqs:ChangeMessageVisibility"
    ]
    resources = [<ARN_OF_SUBSCRIBER_QUEUE>]
  }
}
```

---

### TCP Eventing Configuration

Top-level platform eventing configuration lives in [tcp-platform-configuration](https://github.com/tyler-technologies/tcp-platform-configuration).

| Key | Description |
|---|---|
| `TCPEventing.PublisherQueue` | ARN/name of the shared input SQS queue |
| `TCPEventing.Region` | AWS region for input queue and failure outbox |
| `TCPEventing.UseSqs` | Feature flag; set `false` to disable eventing |
| `TCPEventing.SchemaRegistry.Table` | DynamoDB table name for schema storage |
| `TCPEventing.FailedMessage.Table` | DynamoDB table name for failed messages |

---

### Handling Failed Messages

**Use when:** You need to understand what happens when publishing or handling a message fails, or you need to retry/redrive failed messages.

**Publisher failures:**
- Retry policy: 2 retries → 3 total attempts.
- After 3 failures: message written to the **DynamoDB failure outbox**.
- Retry tool: [Eventing Retry API](https://github.com/tyler-technologies/tcp-eventing-retry-api)

Failure outbox record fields: `MessageId` (Datadog traceId), `EventType`, `Message` (JSON body), `Exception`, `Stack`, `Created` (UTC Unix ms)

**Subscriber/handler failures:**
- Retry policy: 3 retries → 4 total attempts.
- After 4 failures: message moved to the handler's **SQS dead-letter queue**.
- Retry tool: [Eventing Retry API](https://github.com/tyler-technologies/tcp-eventing-retry-api)

**SQS → EventBridge handoff failures:**
- Message goes to the **input dead-letter queue** for manual retry when the connection issue resolves.

**Eventing Retry API capabilities:**
- Inspect failure outbox count by `TraceId`, `EventType`, `StartDate`, `EndDate`.
- Replay messages from the failure outbox.
- Get DLQ message count.
- Redrive all messages in a DLQ.
- Purge a DLQ.

**Example redrive:** To redrive the availability DLQ: `GET /Queue/availability-dead-letter/count` then `POST /Queue/redrive/availability-dead-letter`.

---

## 5. Community Service Directory (CSD)

Live doc: https://docs.tylerdev.io/platform-architecture/service-architecture/community-service-directory/introduction/

CSD is the **TCP reference application** for divisional developers integrating with TCP. It intentionally uses no TCP-internal dependencies — only the `Tyler.Platform.Sdk` NuGet, the same tooling any external division would use. It replaces the older Pet Registration reference project.

CSD replaces the **TCP Community Launcher**: customers can now select which links to display, add custom product names/descriptions, choose icons, associate departments and functions, add search tags, and import Tyler product link URLs.

### CSD Repositories

| Repo | Purpose |
|---|---|
| [tcp-community-service-directory](https://github.com/tyler-technologies/tcp-community-service-directory) | Directory frontend (Angular) |
| [tcp-community-service-administration](https://github.com/tyler-technologies/tcp-community-service-administration) | Administration frontend |
| [tcp-community-service-configuration](https://github.com/tyler-technologies/tcp-community-service-configuration) | Configuration frontend |
| [tcp-community-service-operations](https://github.com/tyler-technologies/tcp-community-service-operations) | Operations frontend |
| [tcp-community-services-api](https://github.com/tyler-technologies/tcp-community-services-api) | Backend API, event handler, webhook handler |
| [tcp-community-service-dev-compose](https://github.com/tyler-technologies/tcp-community-service-dev-compose) | Local development Docker Compose |
| [corpdev-csd-tf-workspace-management](https://github.com/tyler-technologies/corpdev-csd-tf-workspace-management) | Terraform workspace management |

---

### CSD Architecture Overview

Live doc: https://docs.tylerdev.io/platform-architecture/service-architecture/community-service-directory/architecture-overview/

**BFF Pattern:** Every frontend app communicates only with its own dedicated BFF service in the backend. The BFF calls the CSD API for data.

**Microservice isolation:** CSD runs in its own Kubernetes namespace, isolated from core TCP services.

**Internal eventing over direct webhook handling:** When TCP sends a webhook call to CSD, the webhook handler does not process it directly. Instead:
1. The webhook handler translates the incoming TCP webhook message to a CSD internal message.
2. It publishes the CSD message to an internal SQS queue.
3. The event handler polls that queue and processes the message asynchronously.

This design ensures CSD never depends on TCP to retry failed messages — if CSD's SQS publish fails, `AWS.Messaging` retries twice, then stores the message in a DynamoDB failure outbox. If the event handler fails, `AWS.Messaging` retries twice, then dead-letters to the queue's DLQ. CSD controls its own retry and redrive operations.

**Internal eventing NuGet:** [tcp-community-services-eventing class library](https://github.com/tyler-technologies/tcp-community-services-api/tree/main/tcp-community-services-eventing) (wraps `AWS.Messaging`)

**Database:** Aurora MySQL. API uses the write endpoint for mutations, the RDS read replica for reads. The frontend optimistically updates the UI on 2xx responses to avoid blocking on read-replica lag.

**Configuration:** Live, hot-reloadable via Consul + git2consul. git2consul syncs GitHub config changes to Consul automatically on PR merge. Consul is not for secrets — use Harness secrets, Kubernetes secrets, or AWS Secrets Manager.

**RDS authentication:** CSD uses the [TCP.RdsIAMAuth](https://github.com/tyler-technologies/TCP.RdsIAMAuth/blob/master/README.md) NuGet for IAM-based RDS access (no stored database password in AWS). In local development, specify a password in the connection string; in AWS, omit it.

---

### CSD Webhook Handler

Live doc: https://docs.tylerdev.io/platform-architecture/service-architecture/community-service-directory/community-services-webhook-handler/

**Use when:** Understanding how CSD receives incoming TCP webhook calls.

The Webhook Handler is an ASP.NET Core API with one controller endpoint per subscribed webhook type. Each endpoint:
1. Maps the incoming TCP webhook message to a CSD internal message (using AutoMapper).
2. Publishes the CSD message to an internal SQS queue.
3. Returns `202 Accepted` immediately.

A `ProductLicensedFilter` on CSD's webhook subscription ensures TCP only sends messages for workspaces owned by organizations that have CSD licensed — no filtering needed in the handler.

**Authentication/Authorization:** Uses Tyler Workforce Gateway for CCF token validation. Scope-based:
- `tcp-community-services-webhook-handler.AdminScope` — required by TCP when delivering webhook messages.

**Scaling:** CPU-based HPA — scales independently when message volume spikes.

---

### CSD Event Handler

Live doc: https://docs.tylerdev.io/platform-architecture/service-architecture/community-service-directory/community-services-event-handler/

The Event Handler is a .NET Core console application that polls a single SQS queue. It:
- Processes platform-driven events (forwarded from the Webhook Handler).
- Executes long-running tasks broken into per-item messages (e.g., user role recalculation).

**Long-task decomposition pattern:** Instead of blocking a web request with a multi-second or multi-minute operation, the API saves data, then publishes one message to start the long task. The handler processes that message, breaks it into per-record sub-messages, and the handler processes each sub-message individually.

**Scaling:** SQS queue depth-based HPA. A [QueueMetricsService](https://github.com/tyler-technologies/tcp-community-services-api/blob/main/tcp-community-services-eventing/Services/QueueMetricsService.cs) publishes a custom DataDog metric for approximate queue depth, and the [HPA](https://github.com/tyler-technologies/tcp-community-services-api/blob/main/continuous-deployment/tcp-community-services-event-handler/service-definition/templates/hpa.yaml) uses that metric to scale up or down.

---

### CSD Eventing Bootstrapper

Live doc: https://docs.tylerdev.io/platform-architecture/service-architecture/community-service-directory/community-services-eventing-bootstrapper/

The Eventing Bootstrapper is a Kubernetes job (runs once at deploy time, then stops). It calls the TCP webhook registration API to subscribe CSD to the following webhook events:

- `UserAddedToGroup`, `UserRemovedFromGroup`, `UserGroupUpdated`, `UserGroupDeleted`
- `ProductLicensed`
- `WorkforceProfileUpdated`, `WorkforceProfileDeleted`
- `WorkforceUserAddedAsOrgAdmin`, `WorkforceUserRemovedAsOrgAdmin`
- `WorkspaceCreated`

Subscription config lives in: [configmap.yaml](https://github.com/tyler-technologies/tcp-community-services-api/blob/main/continuous-deployment/tcp-community-services-eventing-bootstrapper/service-definition/templates/configmap.yaml)

---

### CSD API

Live doc: https://docs.tylerdev.io/platform-architecture/service-architecture/community-service-directory/community-services-api/

Manages all data in and out of the Aurora RDS instance. All BFFs call this API.

**Swagger docs:** https://docs.tylerdev.io/architecture/cloud-platform-api/tcp-community-services-api/ (requires Tyler login)

**Authorization:** Scope-based (not Styra DAS — intentionally uses the model most Tyler divisions would adopt):
- `tcp-community-services-api.ReadScope` — read-only (Directory BFF)
- `tcp-community-services-api.AdminScope` — write access (Administration and Configuration BFFs)
- `tcp-community-services-api.EventingScope` — dead-letter redrive and failure outbox replay

**Scaling:** CPU-based HPA.

---

### CSD Branding

Live doc: https://docs.tylerdev.io/platform-architecture/service-architecture/community-service-directory/community-services-branding/

TCP's new branding solution provides:
- Hero/banner images and logo images served as `.webp` for performance.
- Customer-selected theme colors exposed as CSS tokens.
- Enhanced security on image upload.

Branding repo and full docs: [tcp-branding-api README](https://github.com/tyler-technologies/tcp-branding-api/blob/main/README.md)

**Branding NuGet:** Available to simplify adoption. Package ref and setup code: [CSD Startup.cs](https://github.com/tyler-technologies/tcp-community-service-directory/blob/main/tcp-community-service-directory/Startup.cs).

**Dark theme gotcha:** Customer branding colors must NOT be applied when the dark theme is active. Override the relevant CSS tokens to the default theme values in `.dark-theme {}`:

```css
.dark-theme {
  @include theme-dark.theme-properties;
  --forge-app-bar-background: var(--forge-theme-brand);
  --forge-app-bar-foreground: var(--forge-theme-on-brand);
  --tcp-brand-on-primary-color: var(--forge-theme-on-primary);
  --tcp-brand-primary-color: var(--forge-theme-primary);
}
```

Customers configure branding via Admin Center. The colors are exposed through two auto-loaded CSS stylesheets.

---

### CSD Frontend

Live doc: https://docs.tylerdev.io/platform-architecture/service-architecture/community-service-directory/community-services-front-end/

**Template:** Generated from [tcpweb-accelerator-core](https://github.com/tyler-technologies/tcpweb-accelerator-core).

**Component library:** [Tyler Forge](https://forge.tylertech.com/) — all TCP platform applications must use Forge.
- [Forge Storybook (open source)](https://forge.tylerdev.io/main/?path=/docs/home--docs)
- [Forge Internal Storybook (Tyler-specific components)](https://tyler-technologies.github.io/forge-internal/main/?path=/story/components-app-launcher--default)

**State management:** [NgRx Signal Stores](https://ngrx.io/guide/signals/signal-store) (not NgRx Redux Stores).

**Accessibility:** WCAG 2.1 AA target. Forge provides a foundation; teams must still follow semantic HTML and accessibility principles.

**Responsiveness:**
- Directory app: full range from phones to wide monitors (community-facing)
- Administration, Configuration, Operations: small tablets to wide monitors

**i18n:** In progress — targeting en-US, ca-FR (Canadian French), us-XA (pseudo-locale for testing). Uses Angular i18n with automated extraction/translation.

---

### CSD Monitoring and Alerts

Live doc: https://docs.tylerdev.io/platform-architecture/service-architecture/community-service-directory/monitoring-and-alerts/

Once eventing is in place, observability is critical. Dead-letter queues and failure outboxes that fill up silently are hard to triage retroactively.

**DataDog CSD Eventing Dashboard:** https://app.datadoghq.com/dashboard/hpd-cet-9nk/tcp-community-services-eventing-csd

Shows: message counts by type, monitor health summary, handler trace list, DLQ depth, failure outbox depth.

**DataDog CSD Monitors (production):** https://app.datadoghq.com/monitors/manage?q=tag%3Aproject%3Acsd%20env%3Atcpprod-1

Alerts fire when:
- Any item lands in the dead-letter queue.
- Any item lands in the DynamoDB message failure table.
- Any item has remained in the main or dead-letter queue for more than 45 minutes.

Monitors are defined per environment (tcpci, tcpqa, tcpprod).

---

## Notes for the chatbot

1. **Cite the live doc URL** for every section when handing off to a user — the live docs may have code updates not reflected here.

2. **Authorization vs. Identity:** Authorization questions (Styra DAS, permissions, service accounts, tcp-cli) belong in this file. Identity questions (OAuth flows, Okta, TID Gateway, token validation, interactive login) belong at https://docs.tylerdev.io/identity.

3. **TCP Eventing vs. Webhooks:** TCP Eventing is the internal SQS/EventBridge system — service-to-service, inside the platform. Webhooks are the outbound HTTPS mechanism for external consumers. A webhook event always starts as an internal TCP event. If a user asks about external integrations receiving platform events, direct them to Webhooks; if the question is about internal service communication, direct them to TCP Eventing.

4. **CSD as reference:** When a divisional developer asks "how do I integrate with TCP?", CSD is the canonical reference. Point them to the CSD repos and documentation. CSD deliberately avoids TCP-internal libraries, so its patterns are directly applicable to non-TCP teams.

5. **Service accounts vs. users:** Service accounts are for machine-to-machine auth. Permissions are assigned directly to service accounts; never assign roles to service accounts. Human users get roles. The chatbot should reinforce this distinction clearly.

6. **Permission lookup workflow:** Always direct users to the permissions CSV (`https://docs.tylerdev.io/authz-permissions.csv`) as the first step when determining what permissions a service account needs — do not guess at permission names.

7. **Event payloads should be slim:** A recurring architectural principle: events published by EF Core interceptors and search handlers should carry only the minimum data (an ID or key) needed to reload the full record in the handler. Warn users who describe fat event payloads.

8. **Reindexing is single-threaded by design:** Do not suggest parallelizing the reindex handler — the docs explicitly recommend the single-thread model to avoid database/service contention.

9. **Missing `JsonDerivedType` in webhooks is a runtime trap:** Always remind developers adding a new webhook message type to add the `[JsonDerivedType]` attribute on `IWebhookMessage`. It is easy to miss and causes silent serialization failures.

10. **Dark theme + branding is a gotcha:** When helping with branding integration, always call out that customer branding colors must be suppressed in dark theme via CSS token overrides.

11. **Index hygiene:** If files are added, removed, or substantially restructured in this Knowledge folder, `_START_HERE.md` must be updated.
