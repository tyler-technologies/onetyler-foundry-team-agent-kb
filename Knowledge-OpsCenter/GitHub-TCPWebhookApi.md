# TCP Webhook API — Schemas and Event Reference

Source: GitHub — `tyler-technologies/tcp-webhook-api` repository. Primary index: https://github.com/tyler-technologies/tcp-webhook-api/blob/main/docs/SCHEMAS.md (private Tyler repo). Per-domain schema files cited per-event.
Domain: Ops Center (webhooks emit events about Organizations, Workspaces, Products, Users, Groups, and Support Access — all core Ops Center concepts).
Audience: Tyler product engineering teams that want to **subscribe to TCP webhook events** to react to changes in Organizations, Workspaces, Products, Users/Groups, or Identity profiles — and platform engineers maintaining the webhook subsystem itself.

This document covers what the TCP Webhook API is, how to subscribe, the three authentication methods, and the **full catalog of webhook event types** with their schemas, example payloads, and filter options.

**Companion documents in this same Knowledge folder:**
- `Docusaurus-Terminology.md` — see *Organization*, *Workspace*, *Workforce User / Profile*, *Community User / Profile*, *Identity Workforce*, *Community Access* — the constructs these events describe.
- `Docusaurus-OpsCenter.md` — context for the org / workspace lifecycle events (Created / Activated / Deactivated / Deleted) and product Licensing / Activation events.
- `Docusaurus-ProductRegistration.md` — context for the App Created / Updated / Deleted events.
- `Misc-Links.md` → *Platform Architecture > Webhooks* — the Blueprint Docusaurus pages on webhook architecture, developing a webhook, subscribing to webhooks, and message types.
- `Knowledge-SupportAccessCenter/Docusaurus-SupportAccessCenter.md` — references the `support-access-revoked` event documented here as the canonical revocation signal for SAC subscribers.

---

## How to use this guide (quick decision guide)

| If the user wants to… | Go to section |
|---|---|
| Understand what TCP webhooks ARE and the delivery model | **Architecture and delivery model** |
| Know the three authentication methods for subscription | **Authentication methods** |
| Find the list of all event types at a glance | **Event catalog index** |
| Look up a specific event's schema and example payload | **Event reference** (find the category section) |
| Understand filter fields and custom filters (especially `ProductLicensed`) | **Subscription filters** |
| Know where the message C# library lives | **Architecture and delivery model** |
| Get the link to architecture / development guides | **Related Blueprint docs** |

---

## Architecture and delivery model

The **TCP Webhook API** is the platform subsystem that delivers **asynchronous event notifications** related to topics defined by the Tyler Cloud Platform team.

### How subscribers consume webhooks

Subscribers do **NOT** need to host any additional infrastructure. The flow is:

1. A subscriber calls the `tcp-webhook-api` (hosted in TCP Kubernetes environments) to **subscribe to a specific message type**.
2. The subscription includes:
   - The **message type** (e.g., `TCP.Webhook.Messages.V1.OrganizationCreated`).
   - The **URL** that should be called when a message of that type is published — must be **HTTPS** (TLS). Do not provide HTTP URLs.
   - The **authentication method** the webhook system should use when calling the subscriber's URL.
   - Optional **filter values** (see *Subscription filters* below) to narrow the events the subscriber will receive.
3. When a relevant event occurs, the TCP Webhook subsystem makes an HTTPS POST to the subscriber's URL with the JSON payload.

### Components (for platform engineers)

The repo contains three runtime components and supporting infrastructure:

- **`tcp-webhook-api`** (C#) — public API for creating new message types, managing subscriptions, and rebuilding the subscribers cache.
- **`tcp-webhook-event-handler`** (C#) — runs an `SqsPollingService` (`IHostedService`) that polls SQS for messages sent by services like `tcp-identity-events-api` via SNS.
- **`tcp-webhook-event-relay`** (C#) — transforms an internal message into a webhook message for delivery.
- **`TCP.Webhook.Messages`** (C# library) — the **shared library of message types**, located at `csharp/TCP.Webhook.Messages/`. Versioned (currently all `V1`).
- A `dummy-webhook-api` is included for local testing; it represents a consumer-team's receiver.

### Versioning

All current message types live in the `V1` namespace. Future breaking changes would land in `V2`+ as separate types — existing subscribers to `V1` are not silently broken.

---

## Authentication methods

When subscribing, you specify one of **three** authentication methods the webhook subsystem will use when invoking your URL:

| Method | Required fields | When to use |
|---|---|---|
| **JWT** | `authority`, `clientId`, `clientSecret`, optional `scopes` | A Client Credential Flow (CCF) JSON Web Token (JWT) from an identity provider. **Preferred for Tyler-owned APIs.** |
| **API Key** | `apiKey` value, `apiKeyHeader` (the HTTP header name to send it in) | When the receiver authenticates via a static API key in a header. |
| **None** | (no auth fields) | **Only valid for external, third-party APIs** like the Slack API. For Tyler-owned-and-operated APIs you MUST provide an authentication method. |

---

## Subscription URLs

The webhook URL you subscribe with **must use HTTPS (TLS)**. The webhook subsystem will refuse HTTP URLs.

---

## Subscription filters

Each event type exposes a set of **Filter field options** — fields from the event payload that the subscriber can use to narrow which event instances they receive. A subscriber can filter on any combination of those fields. For example, an `OrganizationCreated` subscription can filter by `OrganizationKey` and/or `Internal`.

In addition, many events also support a **Custom filter** called **`ProductLicensed`**. This is a higher-level filter that limits delivery to events related to organizations / workspaces where a specific product is licensed — useful for products that only care about events from orgs that have licensed them.

If no filters are specified, the subscriber receives **all** instances of that event type.

---

## Event catalog index

The TCP Webhook API exposes **25 event types** across 6 domains. All are at Version 1.

| Domain | Event types |
|---|---|
| **Identity Community** | Community Profile Changed · Community Profile Created · Community Profile Deleted · Community Profile Email Changed · Community Profile Updated |
| **Identity Workforce** | Workforce Profile Deleted · Workforce Profile Email Changed · Workforce Profile Updated · Workforce User Added As Org Admin · Workforce User Created · Workforce User Deleted · Workforce User Disabled · Workforce User Enabled · Workforce User Profile Changed · Workforce User Removed As Org Admin |
| **Organization** | Organization Activated · Organization Created · Organization Deactivated · Organization Deleted · Workspace Activated · Workspace Created · Workspace Deactivated · Workspace Deleted |
| **Product** | App Created · App Deleted · App Updated · Product Activated · Product Deactivated · Product Licensed · Product Unlicensed |
| **Support Access** | Support Access Revoked |
| **User Group** | User Added To Group · User Group Created · User Group Deleted · User Group Updated · User Removed From Group |

---

# Event reference

For each event below: the **Event type** (the canonical C# class name, used in subscriptions), the wire **`MessageType`** value used in payloads, the description, available filter fields, custom filter availability, the schema, and an example payload.

**Wire format note:** The C# class names use `PascalCase`. The schema definitions show `camelCase` field names, but the **actual JSON payload delivered to subscribers uses `PascalCase`** as shown in the Example sections below. Treat the Example as authoritative for the wire format.

---

## Identity Community Messages

### Community Profile Changed (V1)

- **Event type:** `TCP.Webhook.Messages.V1.CommunityProfileChanged`
- **`MessageType`:** `community-profile-changed`
- **Description:** Community profile changed.
- **Filter fields:** `Sub`, `ProfileId`, `ChangeCategory`
- **Custom filters:** None

**Schema:**
```json
{
  "MessageType": { "type": "string", "readOnly": true },
  "Sub": { "type": "string" },
  "ProfileId": { "type": "string" },
  "ChangeCategory": { "type": "string" }
}
```

**Example:**
```json
{
  "MessageType": "community-profile-changed",
  "Sub": "identity-sub",
  "ProfileId": "1",
  "ChangeCategory": "some category"
}
```

### Community Profile Created (V1)

- **Event type:** `TCP.Webhook.Messages.V1.CommunityProfileCreated`
- **`MessageType`:** `community-profile-created`
- **Description:** Community profile created.
- **Filter fields:** `OrganizationKey`, `WorkspaceKey`
- **Custom filters:** None

**Schema:** Includes `sub`, `profileId`, a nested `profile` object (`firstName`, `middleName`, `lastName`, `suffix`, `email`, `phoneNumber`, `organization`), a nested `address` object (`addressLine1`, `addressLine2`, `addressCity`, `addressZipCode`, `addressCountry`), `organizationKey`, `workspaceKey`.

**Example:**
```json
{
  "MessageType": "community-profile-created",
  "Sub": "okta-sub",
  "ProfileId": "{guid}",
  "Profile": {
    "FirstName": "John",
    "MiddleName": "M",
    "LastName": "Doe",
    "Suffix": "Jr.",
    "Email": "",
    "PhoneNumber": "555-555-1234",
    "Organization": "Acme Corp"
  },
  "Address": {
    "AddressLine1": "123 Main St",
    "AddressLine2": "Apt 4B",
    "AddressCity": "Springfield",
    "AddressZipCode": "12345",
    "AddressCountry": "USA"
  },
  "OrganizationKey": "may-be-blank?",
  "WorkspaceKey": "may-be-blank?"
}
```

> Note: `OrganizationKey` and `WorkspaceKey` may be blank in some scenarios (per the example comment in the source spec).

### Community Profile Deleted (V1)

- **Event type:** `TCP.Webhook.Messages.V1.CommunityProfileDeleted`
- **`MessageType`:** `community-profile-deleted`
- **Description:** Community profile deleted.
- **Filter fields:** `Sub`, `ProfileId`, `EmailAddress`
- **Custom filters:** None

**Schema:** `MessageType`, `Sub`, `ProfileId`, `EmailAddress` (all strings).

**Example:**
```json
{
  "MessageType": "community-profile-deleted",
  "Sub": "identity-sub",
  "ProfileId": "1",
  "EmailAddress": "email@example.com"
}
```

### Community Profile Email Changed (V1)

- **Event type:** `TCP.Webhook.Messages.V1.CommunityProfileEmailChanged`
- **`MessageType`:** `community-profile-email-changed`
- **Description:** Community profile email changed.
- **Filter fields:** `Sub`, `ProfileId`, `PreviousEmailAddress`, `NewEmailAddress`
- **Custom filters:** None

**Schema:** `MessageType`, `Sub`, `ProfileId`, `PreviousEmailAddress`, `NewEmailAddress` (all strings).

**Example:**
```json
{
  "MessageType": "community-profile-email-changed",
  "Sub": "identity-sub",
  "ProfileId": "1",
  "PreviousEmailAddress": "old.email@example.com",
  "NewEmailAddress": "new.email@example.com"
}
```

### Community Profile Updated (V1)

- **Event type:** `TCP.Webhook.Messages.V1.CommunityProfileUpdated`
- **`MessageType`:** `community-profile-updated`
- **Description:** Community profile updated.
- **Filter fields:** `OrganizationKey`, `WorkspaceKey`
- **Custom filters:** None

**Schema:** Same shape as **Community Profile Created** — `sub`, `profileId`, `profile` (firstName, middleName, lastName, suffix, email, phoneNumber, organization), `address` (addressLine1/2, city, zipCode, country), `organizationKey`, `workspaceKey`.

**Example:** Same shape as Community Profile Created with `"MessageType": "community-profile-updated"`.

---

## Identity Workforce Messages

### Workforce Profile Deleted (V1)

- **Event type:** `TCP.Webhook.Messages.V1.WorkforceProfileDeleted`
- **`MessageType`:** `workforce-profile-deleted`
- **Description:** Workforce user profile deleted.
- **Filter fields:** `ProfileId`, `Subject`, `OrganizationKey`, `Username`
- **Custom filters:** `ProductLicensed`

**Schema:** `messageType`, `profileId` (integer), `subject`, `organizationKey`, `username`.

**Example:**
```json
{
  "MessageType": "workforce-profile-deleted",
  "ProfileId": 1,
  "Subject": "identity-sub",
  "OrganizationKey": "orgKey",
  "Username": "username"
}
```

### Workforce Profile Email Changed (V1)

- **Event type:** `TCP.Webhook.Messages.V1.WorkforceProfileEmailChanged`
- **`MessageType`:** `workforce-profile-email-changed`
- **Description:** Workforce profile email changed.
- **Filter fields:** `Organization`, `Sub`, `ProfileId`, `PreviousEmailAddress`, `NewEmailAddress`
- **Custom filters:** `ProductLicensed`

**Schema:** `MessageType`, `Organization`, `Sub`, `ProfileId` (nullable integer), `PreviousEmailAddress`, `NewEmailAddress`.

**Example:**
```json
{
  "MessageType": "workforce-profile-email-changed",
  "Organization": "orgKey",
  "Sub": "identity-sub",
  "ProfileId": 1,
  "PreviousEmailAddress": "old.email@example.com",
  "NewEmailAddress": "new.email@example.com"
}
```

### Workforce Profile Updated (V1)

- **Event type:** `TCP.Webhook.Messages.V1.WorkforceProfileUpdated`
- **`MessageType`:** `workforce-profile-updated`
- **Description:** Workforce user profile updated.
- **Filter fields:** `ProfileId`, `Subject`, `OrganizationKey`, `Username`
- **Custom filters:** `ProductLicensed`

**Schema:** `messageType`, `profileId` (integer), `subject`, `organizationKey`, `username`.

**Example:**
```json
{
  "MessageType": "workforce-profile-updated",
  "ProfileId": 1,
  "Subject": "identity-sub",
  "OrganizationKey": "orgKey",
  "Username": "username"
}
```

### Workforce User Added As Org Admin (V1)

- **Event type:** `TCP.Webhook.Messages.V1.WorkforceUserAddedAsOrgAdmin`
- **`MessageType`:** `workforce-user-added-as-org-admin`
- **Description:** Workforce user added as organization administrator.
- **Filter fields:** `ProfileId`, `OrganizationKey`, `Subject`, `Username`
- **Custom filters:** `ProductLicensed`

**Schema:** `messageType`, `profileId` (integer), `organizationKey`, `subject`, `username`, `givenName`, `familyName`.

**Example:**
```json
{
  "MessageType": "workforce-user-added-as-org-admin",
  "ProfileId": 1,
  "OrganizationKey": "orgKey",
  "Subject": "identity-sub",
  "Username": "username",
  "GivenName": "First",
  "FamilyName": "Last"
}
```

### Workforce User Created (V1)

- **Event type:** `TCP.Webhook.Messages.V1.WorkforceUserCreated`
- **`MessageType`:** `workforce-user-created`
- **Description:** Workforce user created.
- **Filter fields:** `Sub`, `OrganizationKey`, `Username`, `GivenName`, `FamilyName`, `Email`
- **Custom filters:** `ProductLicensed`

**Schema:** `messageType`, `sub`, `organizationKey`, `username`, `givenName`, `familyName`, `email`.

**Example:**
```json
{
  "MessageType": "workforce-user-created",
  "Sub": "identity-sub",
  "OrganizationKey": "orgKey",
  "Username": "username",
  "GivenName": "First",
  "FamilyName": "Last",
  "Email": "email@example.com"
}
```

### Workforce User Deleted (V1)

- **Event type:** `TCP.Webhook.Messages.V1.WorkforceUserDeleted`
- **`MessageType`:** `workforce-user-deleted`
- **Description:** Workforce user deleted.
- **Filter fields:** `Sub`, `OrganizationKey`, `Username`, `GivenName`, `FamilyName`, `Email`
- **Custom filters:** `ProductLicensed`

**Schema:** Same as Workforce User Created.

**Example:** Same shape as Workforce User Created with `"MessageType": "workforce-user-deleted"`.

### Workforce User Disabled (V1)

- **Event type:** `TCP.Webhook.Messages.V1.WorkforceUserDisabled`
- **`MessageType`:** `workforce-user-disabled`
- **Description:** Workforce user disabled.
- **Filter fields:** `Sub`, `OrganizationKey`, `Username`, `GivenName`, `FamilyName`, `Email`
- **Custom filters:** `ProductLicensed`

**Schema:** Same as Workforce User Created.

**Example:** Same shape as Workforce User Created with `"MessageType": "workforce-user-disabled"`.

### Workforce User Enabled (V1)

- **Event type:** `TCP.Webhook.Messages.V1.WorkforceUserEnabled`
- **`MessageType`:** `workforce-user-enabled`
- **Description:** Workforce user enabled.
- **Filter fields:** `Sub`, `OrganizationKey`, `Username`, `GivenName`, `FamilyName`, `Email`
- **Custom filters:** `ProductLicensed`

**Schema:** Same as Workforce User Created.

**Example:** Same shape as Workforce User Created with `"MessageType": "workforce-user-enabled"`.

### Workforce User Profile Changed (V1)

- **Event type:** `TCP.Webhook.Messages.V1.WorkforceUserProfileChanged`
- **`MessageType`:** `workforce-user-profile-changed`
- **Description:** Workforce user profile changed.
- **Filter fields:** `Sub`, `OrganizationKey`, `Username`, `GivenName`, `FamilyName`, `Email`, `OldUsername`, `OldGivenName`, `OldFamilyName`, `OldEmail`
- **Custom filters:** `ProductLicensed`

**Schema:** Same as Workforce User Created PLUS `old_username`, `old_givenName`, `old_familyName`, `old_email` for delta-tracking.

**Example:**
```json
{
  "MessageType": "workforce-user-profile-changed",
  "Sub": "identity-sub",
  "OrganizationKey": "orgKey",
  "Username": "username",
  "GivenName": "First",
  "FamilyName": "Last",
  "Email": "email@example.com",
  "old_username": "old-username",
  "old_givenName": "OldFirst",
  "old_familyName": "OldLast",
  "old_email": "old.email@example.com"
}
```

### Workforce User Removed As Org Admin (V1)

- **Event type:** `TCP.Webhook.Messages.V1.WorkforceUserRemovedAsOrgAdmin`
- **`MessageType`:** `workforce-user-removed-as-org-admin`
- **Description:** Workforce user removed as organization administrator.
- **Filter fields:** `ProfileId`, `OrganizationKey`, `Subject`, `Username`
- **Custom filters:** `ProductLicensed`

**Schema:** Same as Workforce User Added As Org Admin.

**Example:** Same shape as Workforce User Added As Org Admin with `"MessageType": "workforce-user-removed-as-org-admin"`.

---

## Organization Messages

### Organization Activated (V1)

- **Event type:** `TCP.Webhook.Messages.V1.OrganizationActivated`
- **`MessageType`:** `organization-activated`
- **Description:** Organization activated.
- **Filter fields:** `OrganizationKey`
- **Custom filters:** `ProductLicensed`

**Schema:** `messageType`, `organizationKey`, `productWorkspaceAvailabilities` (object whose keys are product registration IDs and values are arrays of workspace keys where the product is available).

**Example:**
```json
{
  "MessageType": "organization-activated",
  "OrganizationKey": "orgKey",
  "ProductWorkspaceAvailabilities": {
    "product-registration-id1": [ "workspaceKey1", "workspaceKey2" ],
    "product-registration-id2": [ "workspaceKey3" ]
  }
}
```

### Organization Created (V1)

- **Event type:** `TCP.Webhook.Messages.V1.OrganizationCreated`
- **`MessageType`:** `organization-created`
- **Description:** Organization created.
- **Filter fields:** `OrganizationKey`, `Internal`
- **Custom filters:** None

**Schema:** `messageType`, `organizationKey`, `internal` (boolean).

**Example:**
```json
{
  "MessageType": "organization-created",
  "OrganizationKey": "orgKey",
  "Internal": true
}
```

### Organization Deactivated (V1)

- **Event type:** `TCP.Webhook.Messages.V1.OrganizationDeactivated`
- **`MessageType`:** `organization-deactivated`
- **Description:** Organization deactivated.
- **Filter fields:** `OrganizationKey`
- **Custom filters:** `ProductLicensed`

**Schema:** Same as Organization Activated (includes `productWorkspaceAvailabilities` so subscribers can see what was activated against this org at deactivation time).

**Example:** Same shape as Organization Activated with `"MessageType": "organization-deactivated"`.

### Organization Deleted (V1)

- **Event type:** `TCP.Webhook.Messages.V1.OrganizationDeleted`
- **`MessageType`:** `organization-deleted`
- **Description:** Organization deleted.
- **Filter fields:** `OrganizationKey`, `Internal`
- **Custom filters:** None

**Schema:** Same as Organization Created.

**Example:**
```json
{
  "MessageType": "organization-deleted",
  "OrganizationKey": "orgKey",
  "Internal": true
}
```

### Workspace Activated (V1)

- **Event type:** `TCP.Webhook.Messages.V1.WorkspaceActivated`
- **`MessageType`:** `workspace-activated`
- **Description:** Workspace activated.
- **Filter fields:** `OrganizationKey`, `WorkspaceKey`, `WorkspaceType`
- **Custom filters:** `ProductLicensed`

**Schema:** `messageType`, `organizationKey`, `workspaceKey`, `workspaceType` (string — `Production` or `NonProduction`).

**Example:**
```json
{
  "MessageType": "workspace-activated",
  "OrganizationKey": "orgKey",
  "WorkspaceKey": "workspaceKey",
  "WorkspaceType": "Production"
}
```

### Workspace Created (V1)

- **Event type:** `TCP.Webhook.Messages.V1.WorkspaceCreated`
- **`MessageType`:** `workspace-created`
- **Description:** Workspace created.
- **Filter fields:** `OrganizationKey`, `WorkspaceKey`, `WorkspaceType`
- **Custom filters:** `ProductLicensed`

**Schema:** Same as Workspace Activated.

**Example:** Same shape as Workspace Activated with `"MessageType": "workspace-created"`.

### Workspace Deactivated (V1)

- **Event type:** `TCP.Webhook.Messages.V1.WorkspaceDeactivated`
- **`MessageType`:** `workspace-deactivated`
- **Description:** Workspace deactivated.
- **Filter fields:** `OrganizationKey`, `WorkspaceKey`, `WorkspaceType`
- **Custom filters:** `ProductLicensed`

**Schema:** Same as Workspace Activated.

**Example:** Same shape with `"MessageType": "workspace-deactivated"`.

### Workspace Deleted (V1)

- **Event type:** `TCP.Webhook.Messages.V1.WorkspaceDeleted`
- **`MessageType`:** `workspace-deleted`
- **Description:** Workspace deleted.
- **Filter fields:** `OrganizationKey`, `WorkspaceKey`, `WorkspaceType`
- **Custom filters:** None

**Schema:** Same as Workspace Activated.

**Example:** Same shape with `"MessageType": "workspace-deleted"`.

---

## Product Messages

### App Created (V1)

- **Event type:** `TCP.Webhook.Messages.V1.AppCreated`
- **`MessageType`:** `app-created`
- **Description:** App created.
- **Filter fields:** `RegistrationId`
- **Custom filters:** None

**Schema:** `messageType`, `id` (integer), `registrationId`.

**Example:**
```json
{
  "MessageType": "app-created",
  "Id": 1,
  "RegistrationId": "app-registration-id"
}
```

### App Deleted (V1)

- **Event type:** `TCP.Webhook.Messages.V1.AppDeleted`
- **`MessageType`:** `app-deleted`
- **Description:** App deleted.
- **Filter fields:** `RegistrationId`
- **Custom filters:** None

**Schema:** Same as App Created.

**Example:** Same shape with `"MessageType": "app-deleted"`.

### App Updated (V1)

- **Event type:** `TCP.Webhook.Messages.V1.AppUpdated`
- **`MessageType`:** `app-updated`
- **Description:** App updated.
- **Filter fields:** `RegistrationId`
- **Custom filters:** None

**Schema:** Same as App Created.

**Example:** Same shape with `"MessageType": "app-updated"`.

### Product Activated (V1)

- **Event type:** `TCP.Webhook.Messages.V1.ProductActivated`
- **`MessageType`:** `product-activated`
- **Description:** Product made available to a workspace.
- **Filter fields:** `RegistrationId`, `OrganizationKey`, `WorkspaceKey`
- **Custom filters:** None

**Schema:** `messageType`, `registrationId`, `organizationKey`, `workspaceKey`.

**Example:**
```json
{
  "MessageType": "product-activated",
  "RegistrationId": "product-registration-id",
  "OrganizationKey": "orgKey",
  "WorkspaceKey": "workspaceKey"
}
```

> Maps to the **Availability** concept in Ops Center: product is made available on a workspace after being licensed at the org level.

### Product Deactivated (V1)

- **Event type:** `TCP.Webhook.Messages.V1.ProductDeactivated`
- **`MessageType`:** `product-deactivated`
- **Description:** Product made unavailable on a workspace.
- **Filter fields:** `RegistrationId`, `OrganizationKey`, `WorkspaceKey`
- **Custom filters:** None

**Schema:** Same as Product Activated.

**Example:** Same shape with `"MessageType": "product-deactivated"`.

### Product Licensed (V1)

- **Event type:** `TCP.Webhook.Messages.V1.ProductLicensed`
- **`MessageType`:** `product-licensed`
- **Description:** Product licensed to an organization.
- **Filter fields:** `RegistrationId`, `OrganizationKey`
- **Custom filters:** None

**Schema:** `messageType`, `registrationId`, `organizationKey`.

**Example:**
```json
{
  "MessageType": "product-licensed",
  "RegistrationId": "product-registration-id",
  "OrganizationKey": "orgKey"
}
```

> Maps to the **Licensing** concept in Ops Center: the org becomes eligible to use the product. Note: licensing is at the **org** level; activation (Availability) is at the **workspace** level.

### Product Unlicensed (V1)

- **Event type:** `TCP.Webhook.Messages.V1.ProductUnlicensed`
- **`MessageType`:** `product-unlicensed`
- **Description:** Product unlicensed from an organization.
- **Filter fields:** `RegistrationId`, `OrganizationKey`
- **Custom filters:** None

**Schema:** Same as Product Licensed.

**Example:** Same shape with `"MessageType": "product-unlicensed"`.

---

## Support Access Messages

### Support Access Revoked (V1)

- **Event type:** `TCP.Webhook.Messages.V1.SupportAccessRevoked`
- **`MessageType`:** `support-access-revoked`
- **Description:** Support access revoked.
- **Filter fields:** `OrganizationKey`, `Sub`, `Username`
- **Custom filters:** None

**Schema:** `messageType`, `organizationKey`, `sub`, `username`, `productRegistrationIds` (array of strings), `workspaceKeys` (array of strings).

**Example:**
```json
{
  "MessageType": "support-access-revoked",
  "OrganizationKey": "orgKey",
  "Sub": "sub",
  "Username": "username",
  "ProductRegistrationIds": [ "product-registration-id1", "product-registration-id2" ],
  "WorkspaceKeys": [ "workspaceKey1", "workspaceKey2" ]
}
```

> **This is THE webhook for Support Access Center (SAC) adopters.** When a Tyler-staff user's SAC access expires or is revoked, products subscribed to this event must use the combination of `Sub`, `ProductRegistrationIds`, and `WorkspaceKeys` to terminate any active sessions. See `Knowledge-SupportAccessCenter/Docusaurus-SupportAccessCenter.md` → *Engineering requirements* and *Support Access Revoked Webhook* — adopting this webhook is a SAC engineering requirement.

---

## User Group Messages

### User Added To Group (V1)

- **Event type:** `TCP.Webhook.Messages.V1.UserAddedToGroup`
- **`MessageType`:** `user-added-to-group`
- **Description:** User added to group.
- **Filter fields:** `OrganizationKey`
- **Custom filters:** `ProductLicensed`

**Schema:** `messageType`, `organizationKey`, `sub`, `groupId` (integer), `groupName`, `username`.

**Example:**
```json
{
  "MessageType": "user-added-to-group",
  "OrganizationKey": "orgKey",
  "Sub": "identity-sub",
  "GroupId": 1,
  "GroupName": "group",
  "Username": "username"
}
```

### User Group Created (V1)

- **Event type:** `TCP.Webhook.Messages.V1.UserGroupCreated`
- **`MessageType`:** `user-group-created`
- **Description:** User group created.
- **Filter fields:** `OrganizationKey`
- **Custom filters:** `ProductLicensed`

**Schema:** `messageType`, `organizationKey`, `id` (integer), `name`, `description`.

**Example:**
```json
{
  "MessageType": "user-group-created",
  "OrganizationKey": "orgKey",
  "Id": 1,
  "Name": "group",
  "Description": "description of the group"
}
```

### User Group Deleted (V1)

- **Event type:** `TCP.Webhook.Messages.V1.UserGroupDeleted`
- **`MessageType`:** `user-group-deleted`
- **Description:** User group deleted.
- **Filter fields:** `OrganizationKey`
- **Custom filters:** `ProductLicensed`

**Schema:** Same as User Group Created.

**Example:** Same shape with `"MessageType": "user-group-deleted"`.

### User Group Updated (V1)

- **Event type:** `TCP.Webhook.Messages.V1.UserGroupUpdated`
- **`MessageType`:** `user-group-updated`
- **Description:** User group updated.
- **Filter fields:** `OrganizationKey`
- **Custom filters:** `ProductLicensed`

**Schema:** Same as User Group Created PLUS `old_name`, `old_description` for delta tracking.

**Example:**
```json
{
  "MessageType": "user-group-updated",
  "OrganizationKey": "orgKey",
  "Id": 1,
  "Name": "group",
  "Description": "description of the group",
  "old_name": "old-group",
  "old_description": "old description of the group"
}
```

### User Removed From Group (V1)

- **Event type:** `TCP.Webhook.Messages.V1.UserRemovedFromGroup`
- **`MessageType`:** `user-removed-from-group`
- **Description:** User removed from group.
- **Filter fields:** `OrganizationKey`
- **Custom filters:** `ProductLicensed`

**Schema:** Same as User Added To Group.

**Example:** Same shape with `"MessageType": "user-removed-from-group"`.

---

## Related Blueprint docs

For architecture and how-to:

- **Webhook Architecture:** `https://docs.tylerdev.io/architecture/Webhooks/architecture/`
- **Developing a Webhook (subscriber-side guide):** `https://docs.tylerdev.io/architecture/Webhooks/developing-a-webhook/`
- **Subscribing to a Webhook:** `https://docs.tylerdev.io/platform-architecture/service-architecture/Webhooks/subscribing-to-a-webhook/`
- **Message Types (canonical list — same data as this file):** see the **Platform Architecture > Webhooks** entries in `Misc-Links.md`.

For the source code:

- **Repo:** `https://github.com/tyler-technologies/tcp-webhook-api`
- **Schemas index (this file's source):** `https://github.com/tyler-technologies/tcp-webhook-api/blob/main/docs/SCHEMAS.md`
- **C# message library:** `csharp/TCP.Webhook.Messages/` in the same repo.

---

## Notes for the chatbot

- **Webhook URLs MUST be HTTPS.** Reject any user proposal that uses HTTP.
- **Three auth methods: JWT (CCF), API Key, None.** "None" is **only** for external third-party APIs (e.g., Slack). For any Tyler-owned-and-operated API, the subscriber must provide JWT or API Key.
- **All current events are V1.** When a user asks "is there a version 2?", the answer (as of this snapshot) is no — but the namespace pattern (`TCP.Webhook.Messages.V<n>.*`) makes future versioning explicit.
- **Wire format is PascalCase** as shown in Example sections, despite the schema definitions sometimes using camelCase. When a user is building a subscriber, point them at the **Example** for actual field names on the wire.
- **`ProductLicensed` custom filter** appears on most Org/Workspace/Workforce User / User Group events. This filter lets a product subscriber receive only events for orgs that have licensed *their* product — extremely useful to avoid noise. When a user asks "how do I only get events for orgs that have my product?", direct them to subscribe with the `ProductLicensed` custom filter set to their product registration ID.
- **`support-access-revoked` is the SAC engineering requirement.** When a user is adopting SAC (see SAC docs), subscribing to this webhook is one of the two engineering requirements (the other being adopting `tcp-login-security-api` v1). It is **NOT** optional for SAC-adopting products.
- **Org Licensed / Activated mapping:** `Product Licensed` event corresponds to the **org-level licensing** Ops Center step; `Product Activated` corresponds to the **workspace-level availability** Ops Center step. These are separate events because they happen at separate times and at different scopes (org vs workspace).
- **`Organization Activated` / `Organization Deactivated` events include `ProductWorkspaceAvailabilities`** — a map of product registration IDs to workspace keys. Subscribers can use this to understand the org's full product/workspace footprint at the moment of the activation/deactivation event.
- **`Workforce User Profile Changed` and `User Group Updated` include `old_*` fields** for delta tracking. When a subscriber needs to know "what changed?", these are the canonical sources for previous values.
- **The `Community Profile Created` / `Updated` events may have blank `OrganizationKey` and `WorkspaceKey`** — the source spec's example explicitly marks them as "may-be-blank?". Subscribers must tolerate empty values for those fields.
- **The repo is private** (`tyler-technologies/tcp-webhook-api`) — Tyler engineers can access it via `gh` CLI or browser auth. Customers cannot. When discussing webhooks with customers, point to the Blueprint public docs page on webhook architecture instead of the GitHub link.
- **The `tcp-login-security-api` (Security API) and webhooks are complementary** — webhooks notify the subscriber of changes; the Security API answers "does this user currently have access?" at query time. SAC adopters use both: the webhook to terminate sessions on revocation, and the Security API to check on each login.
