# Tyler Identity Knowledge Base

> **Source:** BluePrint documentation — `docs/identity/` (current docs only; Old Docs/Legacy section excluded)
> **Last updated:** 2026-05-20
> **Purpose:** RAG-optimized single-file reference for all Tyler Identity documentation

---

## TABLE OF CONTENTS

1. Tyler Identity Overview
2. Integration Checklists
3. Identity Workforce
   - Getting Started
   - Environments
   - Configuration
   - Login Context
   - Tokens
   - AMR Passthrough
   - Troubleshooting
   - Best Practices
   - Dynamic Auth (.NET)
4. Community Access
   - Getting Started
   - Configuration
   - Environments
   - Troubleshooting
   - Best Practices
5. Shared Guides
   - Client Operations
   - Credential Templates
   - Events
   - Miscellaneous
6. Glossary
7. Support

---

<!-- SOURCE: identity/key-concepts/overview -->

# 1. Tyler Identity Overview

Tyler Identity provides Single Sign-On (SSO) authentication for Tyler products through two distinct solutions, each designed for different user types and integration patterns.

## Choose Your Integration Path

### Identity Workforce — Enterprise & Back-Office Applications

**For**: Employee-facing, back-office, and enterprise applications

**Architecture**: Connects directly to customer-owned Identity Providers (IdPs) via the Identity Gateway

**Key Features**:
- Federates with customer's existing IdP (Entra ID, Google Workspace, Ping, etc.)
- Single Gateway authority for all Tyler workforce applications
- Customer maintains full control of user identities
- Built on OpenID Connect standard
- Zero-trust cloud identity strategy

**Use When**:
- Building back-office or administrative applications
- Users are government employees or staff
- Customer requires enterprise SSO integration
- Need to connect to customer-managed identity systems

### Community Access — Citizen & Public Applications

**For**: Citizen-facing, resident, and public-facing applications

**Architecture**: Single Tyler-managed Okta tenant with branded login experiences

**Key Features**:
- Single identity across all Tyler community applications
- Branded login pages per jurisdiction
- Self-service registration for citizens
- Built on OpenID Connect standard
- PKCE required for public client security

**Use When**:
- Building public-facing or citizen-facing applications
- Users are residents, citizens, or general public
- Need branded login experience per jurisdiction
- Require self-service account creation

## Quick Comparison

| Feature | Identity Workforce | Community Access |
| ------- | ------------------ | ---------------- |
| **User Type** | Employees, staff | Citizens, residents |
| **IdP** | Customer-owned (Entra, Google, etc.) | Tyler-managed Okta |
| **Authority** | Identity Gateway | Okta tenant |
| **Routing** | `organizationKey` parameter | `workspace` parameter |
| **Client Type** | Confidential or Public | Public (PKCE required) |
| **Branding** | Managed by customer IdP | Configured per jurisdiction |
| **Registration** | Managed by customer IT | Self-service for citizens |

## Integration Approach

Both solutions use **OpenID Connect (OIDC)** for authentication, but with different configuration parameters and flows:

- **Workforce**: Uses Identity Gateway with `organizationKey` parameter to route to customer IdPs
- **Community**: Uses Okta with `workspace` parameter for branded experiences

## Understanding Customer Identifiers

Both Identity Workforce and Community Access use customer identifiers to route requests and provide branded experiences:

- **organizationKey** (Workforce): A unique identifier for each customer organization, used to route authentication requests to the correct customer IdP through the Identity Gateway
- **workspace** (Community): A unique identifier for each jurisdiction/workspace, used to display the correct branded login experience in Community Access

These identifiers are obtained from Ops Center and are essential for proper routing and branding.

---

<!-- SOURCE: identity/integration-checklists/workforce-checklist -->

# 2. Integration Checklists

## Identity Workforce Integration Checklist

Use this checklist to track your integration with Identity Workforce and the Identity Gateway for enterprise/back-office applications.

### Prerequisites

- [ ] Reviewed Cloud Ecosystem Terminology
- [ ] Understanding of OpenID Connect (OIDC) fundamentals
- [ ] Product registered in Tyler Cloud Platform
- [ ] Access to Ops Center (for organization keys)

### Product Registration

- [ ] Determined deployment model (single-tenant vs. multi-tenant)
- [ ] For multi-tenant: Submitted Identity Client Service Desk ticket
- [ ] For single-tenant/on-premise: Created Credential Template
- [ ] Obtained client ID and secret for dev environment
- [ ] Registered redirect URIs (exact match required)
- [ ] Registered post-logout redirect URIs
- [ ] Completed Product Registration documentation

### OIDC Implementation

- [ ] Chosen certified OIDC library for your tech stack
- [ ] Implemented Authorization Code Flow with PKCE (strongly recommended)
- [ ] Configured Gateway authority URL for environment
- [ ] Added required scopes: `openid`, `profile`, `email`
- [ ] Added product-specific scope (e.g., `yourproduct.api`)
- [ ] Implemented `organizationKey` parameter injection in /authorize request
- [ ] Implemented state parameter (CSRF protection)
- [ ] Implemented nonce parameter (replay attack protection)

### Dynamic Auth (Optional — .NET Only)

If using TCP Dynamic Auth for .NET applications:

- [ ] Installed `Tyler.Platform.DynamicAuth` NuGet package
- [ ] Configured `AddTcpAuthentication` in startup
- [ ] Verified automatic `organizationKey` handling
- [ ] Tested workspace-based authority resolution

### Token Management

- [ ] Implemented token validation (issuer, expiration, signature)
- [ ] Configured audience validation to accept `api://tylerapps` or disabled
- [ ] Implemented refresh token flow (if using `offline_access` scope)
- [ ] Secure token storage (httpOnly cookies for server-side, sessionStorage for SPA)
- [ ] Token expiration handling
- [ ] Extract and validate `organizationKey` claim

### API Security

- [ ] APIs validate Gateway-issued access tokens
- [ ] JWT Bearer authentication configured
- [ ] Token signature verification using Gateway JWKS endpoint
- [ ] JWKS key caching implemented (recommended)
- [ ] Authorization based on `organizationKey` claim
- [ ] Scope-based authorization implemented (if needed)
- [ ] Implemented Client Credentials Flow for service-to-service (if needed)
- [ ] Dual trust implementation (if migrating from legacy IdP)

### Configuration

- [ ] Gateway authority URLs configured per environment:
  - Dev: `https://idgw.tcpci.com/tg`
  - QA: `https://idgw.tcpqa.com/tg`
  - Prod: `https://idgw.tylerportico.com/tg`
- [ ] Client secrets stored securely (Key Vault, environment variables)
- [ ] Organization keys obtained from Ops Center
- [ ] Redirect URIs use HTTPS (except localhost)
- [ ] Session management configured

### Testing

- [ ] Tested login flow with Gateway in dev environment
- [ ] Tested with at least 3 different organizations
- [ ] Verified `organizationKey` claim in tokens matches expected value
- [ ] Tested organization switching (multi-tenant apps)
- [ ] Tested token refresh flow
- [ ] Tested logout and session termination
- [ ] Tested error scenarios (invalid org key, expired tokens, etc.)
- [ ] Tested in TCPCI environment
- [ ] Tested in TCPQA environment
- [ ] **Required**: Operational testing with `tylertownwa` in production

### Security & Best Practices

- [ ] Client secrets never committed to source control
- [ ] Client secrets stored in secure vaults (Key Vault, Secrets Manager)
- [ ] Tokens never logged or exposed in URLs
- [ ] Never store tokens in localStorage (use httpOnly cookies or sessionStorage)
- [ ] Proper clock skew tolerance (5 minutes recommended)
- [ ] HTTPS enforced for all redirect URIs (except localhost for dev)
- [ ] Token validation on every protected request
- [ ] Implemented proper error handling with user-friendly messages
- [ ] Health checks for Gateway connectivity
- [ ] Audit logging for authentication events

### Production Readiness

- [ ] All environments (dev, qa, prod) configured
- [ ] Monitoring and alerting configured (authentication success/failure rates, token validation failures, token refresh success rates)
- [ ] Authentication Error tracking implemented
- [ ] Support procedures documented
- [ ] Load testing completed (if applicable)

---

<!-- SOURCE: identity/integration-checklists/community-checklist -->

## Community Access Integration Checklist

Use this checklist to track your integration with Community Access (Okta) for citizen/public-facing applications.

### Prerequisites

- [ ] Understanding of OpenID Connect (OIDC) fundamentals
- [ ] Understanding of PKCE (required for all Community apps)
- [ ] Product registered in Tyler Cloud Platform
- [ ] Access to Ops Center (for customer identifiers)

### Product Registration

- [ ] Determined deployment model (single-tenant vs. multi-tenant)
- [ ] For multi-tenant: Submitted Identity Client Service Desk ticket
- [ ] For single-tenant: Created Credential Template
- [ ] Obtained client ID for dev environment (no client secret for public clients)
- [ ] Registered redirect URIs (exact match required)
- [ ] Registered post-logout redirect URIs
- [ ] Specified customer identifier for branding

### OIDC Implementation with PKCE

- [ ] Chosen certified OIDC library for your tech stack
- [ ] **PKCE implemented (MANDATORY for Community Access)**
  - [ ] Code verifier generation (43-128 random characters)
  - [ ] Code challenge generation (SHA256 hash of verifier)
  - [ ] Code challenge sent in /authorize request
  - [ ] Code verifier sent in /token request
- [ ] Implemented Authorization Code + PKCE Flow
- [ ] Configured Okta authority URL for environment
- [ ] Added required scopes: `openid`, `profile`, `email`
- [ ] Added workspace parameter: `workspace={workspace_id}` (for branding)
- [ ] Implemented state parameter (CSRF protection)
- [ ] Implemented nonce parameter (replay attack protection)

### Token Management

- [ ] Implemented token validation (issuer, audience, expiration, signature)
- [ ] Audience validation checks client ID
- [ ] Nonce validation in ID token
- [ ] Implemented refresh token flow (with `offline_access` scope if needed)
- [ ] **Secure token storage** (sessionStorage or httpOnly cookies, NEVER localStorage)
- [ ] Token expiration handling

### Security & Privacy

- [ ] **PKCE mandatory implementation verified**
- [ ] HTTPS enforced for all redirect URIs (except localhost)
- [ ] Tokens never stored in localStorage
- [ ] Tokens never logged or exposed in URLs
- [ ] State parameter prevents CSRF
- [ ] Nonce parameter prevents replay attacks

### Testing

- [ ] Tested login flow
- [ ] Tested logout flow
- [ ] Tested new user registration
- [ ] Tested across multiple jurisdictions (if applicable)
- [ ] Tested in all environments (dev, qa, prod)

### Production Readiness

- [ ] All environments (dev, qa, prod) configured
- [ ] Monitoring and analytics configured
- [ ] Support team trained on citizen-facing issues and Community Access Profile Manager

---

<!-- SOURCE: identity/workforce/getting-started -->

# 3. Identity Workforce

## Getting Started with Identity Workforce

Identity Workforce is Tyler's cloud Identity-as-a-Service (IDaaS) solution for back-office and enterprise applications. It provides a single sign-on experience for workforce users by connecting directly to your organization's identity provider (IdP) through the **Identity Gateway**.

Identity Workforce is built on the OpenID Connect (OIDC) standard, which defines how applications authenticate users, obtain basic profile information, and acquire access tokens for protected resources.

### Identity Gateway Overview

Central to the Identity Workforce solution is the Identity Gateway. The Gateway acts as an identity federation router and single authority for all Tyler back-office applications and services, eliminating the complexity of integrating with multiple customer IdPs.

The Gateway sits between your Tyler product and the customer's IdP and handles:
- **Authorization Server/STS**: Issues and validates tokens
- **IdP Routing**: Routes authentication requests based on `organizationKey` parameter or global domain registration
- **Token Issuance and Validation**: Manages JWT tokens for secure authentication
- **Session Management**: Handles user sessions across Tyler applications
- **IdP Configuration**: Configuration is managed through Admin Center

### Prerequisites

Before integrating with Identity Workforce, ensure you understand:

1. **Core Concepts**: Organization, Workspace, and Product as defined in the Cloud Ecosystem terminology
2. **OIDC Fundamentals**: Basic understanding of OpenID Connect authentication flows
3. **Customer IdP Requirements**: Customer must have a publicly accessible IdP supporting OIDC or SAML2

### Integration Steps

#### 1. Review Core Concepts

Familiarize yourself with the Tyler Cloud Platform terminology and architecture.

#### 2. Register Your Product

Product registration differs based on deployment model:

**Single-Tenant Applications** (deployed per customer):
- Create a Credentials Template
- Template is applied during deployment to automatically register your application with the Gateway
- Gateway returns client ID and secret for your application

**Multi-Tenant Applications** (deployed once for all customers):
- Submit an Identity Client Ticket for each environment
- Engineering Services team will create the client registration
- Start with Dev environment and progress through QA to Production

#### 3. Obtain Development Credentials

Request a client for development work through the Service Desk (https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3329/create/4153).

#### 4. Implement OIDC Authentication

The Gateway requires **Authorization Code Flow** or **Authorization Code Flow + PKCE** (preferred).

**Recommended Libraries**:
- Use certified OIDC libraries for your technology stack
- Tyler provides accelerators:
  - TCP Web Accelerator (https://github.com/tyler-technologies/tcpweb-accelerator-core)
  - TCP Dynamic Auth (for ASP.NET applications)
  - Gateway Login Examples (https://github.com/tyler-technologies/tid-gateway-login-examples)

**OIDC Configuration Parameters:**

- **Authority**: The url to the gateway instance you are logging in through
  - Dev: `https://idgw.tcpci.com/tg`
  - QA: `https://idgw.tcpqa.com/tg`
  - Prod: `https://idgw.tylerportico.com/tg`
- **Scopes**: Start with: `openid`, `profile`, `email`
- **Client ID**: client_id value generated for your app
- **Client Secret**: if you are not using PKCE, you will be assigned a client secret value

Since the audience value is static, we recommend turning off audience validation in your library.

#### 5. Gateway-Specific Parameters

The gateway accepts custom parameters to specify organizational context during login. Most applications are tenant-forward. When applicable, include one of the following parameters when redirecting to the `/authorize` endpoint:

- `workspaceKey` — **(preferred)** the specific workspace for an organization
- `organizationKey` — the organization's identifier

#### 6. Implement OAuth2 for Service-to-Service Communication

When your backend services need to communicate with other APIs without a user context, use the **Client Credentials Flow (CCF)**.

**When to Use CCF:**
- Backend API to API communication
- Scheduled jobs and batch processes
- Service accounts — applications acting on their own behalf, not on behalf of a user
- System-to-system integration

**Do not use CCF for:**
- User-facing authentication (use Authorization Code Flow instead)
- Scenarios where you need user identity or `organizationKey` context

**Request an access token:**

```http
POST https://idgw.tcpci.com/tg/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id={your_ccf_client_id}
&client_secret={your_ccf_client_secret}
&scope={your_api_scope}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "scope": "your-api-scope"
}
```

**C# Example:**

```csharp
public async Task<string> GetAccessTokenAsync(string scope)
{
    var requestBody = new FormUrlEncodedContent(new[]
    {
        new KeyValuePair<string, string>("grant_type", "client_credentials"),
        new KeyValuePair<string, string>("client_id", _clientId),
        new KeyValuePair<string, string>("client_secret", _clientSecret),
        new KeyValuePair<string, string>("scope", scope)
    });

    var response = await _httpClient.PostAsync($"{_authority}/oauth2/token", requestBody);
    response.EnsureSuccessStatusCode();
    var content = await response.Content.ReadAsStringAsync();
    var tokenResponse = JsonSerializer.Deserialize<TokenResponse>(content);
    return tokenResponse.AccessToken;
}
```

**Important Notes for CCF:**
- No user context: CCF tokens do not contain `organizationKey`, `preferred_username`, or other user-specific claims
- Token lifetime: Access tokens are valid for 1 hour
- Scope strategy: Use product-specific scopes (e.g., `yourproduct.api`) or the platform scope `tyler-cloud-platform-api-access`

**Securing APIs against CCF tokens:**

```csharp
services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.Authority = "https://idgw.tcpci.com/tg";
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = false, // Gateway uses static audience
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true
        };
    });
```

#### 7. Create Credential Templates (if applicable)

For on-premise or Lift & Shift deployments, create Credential Templates to automate client provisioning.

#### 8. Test Your Integration

Test thoroughly across **at least 3 different organizations**:

**Available Development Organizations in TCPCI/TCPQA:**

| Organization | OrganizationKey |
| ------------ | --------------- |
| dev | `dev` |
| test | `test` |
| uat | `uat` |
| impl | `impl` |
| demo | `demo` |

**Note**: Cloud environments automatically redirect users with `@tylertech.com` email addresses to the `sso.tylertech.com` IdP. You **must** create manual test users in different organizations to properly test organization switching.

**Production Operational Testing with tylertownwa** (Required):

Before production deployment, you must complete operational testing with the `tylertownwa` organization in the **production environment**.

- **Organization**: `tylertownwa`
- **OrganizationKey**: `tylertownwa`
- **Environment**: Production (`https://idgw.tylerportico.com/tg`)

**Primary Test User:**
- **Username**: `amelia.brady@tylertownwa.org`
- **Password**: `W#lcome123$`

**Additional Test User (no mailbox):**
- **Username**: `joel.enlow@tylertownwa.org`
- **Password**: `W#lcome123$`

**Important**: Use non-Tyler Tech email accounts for testing, as special functionality is enabled for `@tylertech.com` email addresses.

#### 9. Complete Gateway Rollout Documentation

Fill out all required information in the Gateway Rollout doc (Coda).

---

<!-- SOURCE: identity/workforce/environments -->

## Identity Workforce Environments

The following environments can be utilized for the Gateway. **Note**: Customers are only allowed in the production environment.

| Environment | Usage | Authority | Well-known endpoint |
| ---- | ---- | ----------- | ----------------- |
| `tcpci` | development | https://idgw.tcpci.com/tg | https://idgw.tcpci.com/tg/.well-known/openid-configuration |
| `tcpqa` | quality assurance | https://idgw.tcpqa.com/tg | https://idgw.tcpqa.com/tg/.well-known/openid-configuration |
| `tylerportico` | Production | https://idgw.tylerportico.com/tg | https://idgw.tylerportico.com/tg/.well-known/openid-configuration |

All changes to the Gateway flow from `tcpci` -> `tcpqa` -> `tylerportico` via automated continuous deployment. All new features are previewed in the `tcpci` environment.

### Local Development

The Corpdev team provides an entire local development environment (https://github.com/tyler-technologies/platform-dev-environment-compose) that can be utilized for testing integrations with the ecosystem, including the Gateway. This environment utilizes a mock IdP, allowing for login with any user, but exhibits the same authentication behavior as the cloud environments.

---

<!-- SOURCE: identity/workforce/configuration -->

## Identity Workforce Configuration

### Gateway Endpoints

| Environment | Authority URL | Description |
| ----------- | ------------- | ----------- |
| **TCPCI** | `https://idgw.tcpci.com/tg` | Development/CI environment |
| **TCPQA** | `https://idgw.tcpqa.com/tg` | QA environment |
| **Production** | `https://idgw.tylerportico.com/tg` | Production environment |

### Customer IdP Requirements

For customers who want to federate their own Identity Provider with the Gateway, the IdP must meet the following requirements:

**Technical Requirements:**
- Must be externally accessible from the public internet
- Must support either OIDC or SAML2 protocols
- Must be highly redundant and scalable
- Must be from a trusted industry vendor

**Example Identity Providers:**
- Microsoft Entra ID (formerly Azure AD)
- Ping Identity
- Rapid Identity
- Duo SSO
- Google Workspace
- OneLogin
- Thales SafeNet Trusted Access
- ForgeRock

### Standard OIDC Endpoints

The Gateway exposes standard OpenID Connect discovery at `{authority}/.well-known/openid-configuration`.

Common endpoints:
- **Authorization**: `{authority}/oauth2/authorize`
- **Token**: `{authority}/oauth2/token`
- **UserInfo**: `{authority}/oauth2/userinfo`
- **JWKS**: `{authority}/oauth2/v1/keys`
- **End Session**: `{authority}/oauth2/v1/logout`

### Client Registration

**Multi-Tenant Applications:**
1. Submit an Identity Client Service Desk ticket
2. Provide required information
3. Receive client credentials from Engineering Services team
4. Register in each environment (Dev → QA → Prod)

**Single-Tenant Applications:**
1. Create a Credential Template
2. Template is applied during deployment
3. Client ID and secret returned via Apply Template API
4. Automated provisioning per customer instance

**Required Client Information:**
- **Application Name**: Human-readable name for your application
- **Redirect URIs**: Must use HTTPS (except localhost); exact match required; wildcards not supported
- **Post-Logout Redirect URIs**: Where to redirect after sign-out
- **Application Type**: Web, SPA, Native, or Service
- **Grant Types**: `authorization_code`, `refresh_token` (client_credentials for service accounts)
- **Scopes**: `openid profile email` (minimum required)
- **Environment**: Dev, QA, or Production

### OIDC Configuration

**Authorization Request Parameters:**

```http
GET {authority}/oauth2/authorize?
  response_type=code
  &client_id={your_client_id}
  &redirect_uri={your_redirect_uri}
  &scope=openid%20profile%20email
  &organizationKey={customer_org_key}
  &state={random_state}
  &nonce={random_nonce}
  &code_challenge={pkce_challenge}
  &code_challenge_method=S256
```

**Key Parameters:**
- `organizationKey`: **Required** — Routes request to correct customer IdP
- `state`: Random value to prevent CSRF attacks
- `nonce`: Random value to prevent replay attacks
- `code_challenge`: Base64-URL-encoded SHA256 hash of code_verifier (PKCE)
- `code_challenge_method`: Must be `S256`

**Organization Key Parameter:**

The `organizationKey` is **critical** for Gateway routing:
- Obtained from Ops Center for each customer
- Routes authentication to the customer's configured IdP
- Must be included in every authorization request
- Replaces deprecated `crmId` parameter

**Token Exchange:**

```http
POST {authority}/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
&code={authorization_code}
&redirect_uri={same_redirect_uri}
&client_id={your_client_id}
&client_secret={your_client_secret}
&code_verifier={pkce_verifier}
```

**Refresh Token Flow:**

```http
POST {authority}/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
&refresh_token={refresh_token}
&client_id={your_client_id}
&client_secret={your_client_secret}
&scope=openid%20profile%20email
```

### ASP.NET Core Example

```csharp
services.AddAuthentication(options =>
{
    options.DefaultScheme = CookieAuthenticationDefaults.AuthenticationScheme;
    options.DefaultChallengeScheme = OpenIdConnectDefaults.AuthenticationScheme;
})
.AddCookie()
.AddOpenIdConnect(options =>
{
    options.Authority = "https://idgw.tylerportico.com/tg";
    options.ClientId = Configuration["OIDC:ClientId"];
    options.ClientSecret = Configuration["OIDC:ClientSecret"];
    options.ResponseType = "code";
    options.SaveTokens = true;
    options.GetClaimsFromUserInfoEndpoint = true;

    options.Scope.Clear();
    options.Scope.Add("openid");
    options.Scope.Add("profile");
    options.Scope.Add("email");

    options.TokenValidationParameters = new TokenValidationParameters
    {
        ValidateIssuer = true,
        ValidIssuer = "https://idgw.tylerportico.com/tg",
        ValidateAudience = false, // Gateway uses static audience
        ValidateLifetime = true,
        ClockSkew = TimeSpan.FromMinutes(5)
    };

    // Add organizationKey to authorization request
    options.Events = new OpenIdConnectEvents
    {
        OnRedirectToIdentityProvider = context =>
        {
            var orgKey = // Get from your context/session/config
            context.ProtocolMessage.Parameters.Add("organizationKey", orgKey);
            return Task.CompletedTask;
        }
    };
});
```

### Scopes

| Scope | Description | Required |
| ----- | ----------- | -------- |
| `openid` | Indicates OIDC flow, returns ID token | Yes |
| `profile` | Returns profile claims (name, etc.) | Yes |
| `email` | Returns email claim | Yes |
| `offline_access` | Returns refresh token | Optional |

**Important**: The Gateway does **NOT** include group information in tokens. User group memberships are not available via the `groups` scope or any other scope. Applications must implement their own authorization logic and user-to-role mappings.

### Token Validation

**ID Token Claims:**

```json
{
  "iss": "https://idgw.tylerportico.com/tg",
  "sub": "00u123abc456def",
  "aud": "api://tylerapps",
  "exp": 1734567890,
  "iat": 1734564290,
  "preferred_username": "john.doe@cityofseattle.gov",
  "email": "john.doe@cityofseattle.gov",
  "name": "John Doe",
  "organizationKey": "cityofseattle",
  "crmId": "cityofseattle"
}
```

**Validation Checklist:**
- **Issuer** (`iss`): Must match Gateway authority
- **Expiration** (`exp`): Token must not be expired
- **Issued At** (`iat`): Token must not be issued in the future
- **Signature**: Verify using JWKS from Gateway
- **Organization Key** (`organizationKey`): Use for tenant/org context
- **Audience** (`aud`): Gateway uses static `api://tylerapps` — do NOT validate specific audience

**Access Token Validation (C#):**

```csharp
services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.Authority = "https://idgw.tylerportico.com/tg";
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidIssuer = "https://idgw.tylerportico.com/tg",
            ValidateAudience = false, // Gateway uses static audience
            ValidateLifetime = true,
            ValidateIssuerSigningKey = true
        };
    });
```

### Client Credentials Flow

```http
POST {authority}/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id={your_client_id}
&client_secret={your_client_secret}
&scope={requested_scopes}
```

**Note**: Client Credentials tokens do not contain user information or `organizationKey` claims.

### Logout Configuration

```http
GET {authority}/oauth2/v1/logout?
  id_token_hint={user_id_token}
  &post_logout_redirect_uri={your_post_logout_uri}
```

The Gateway supports front-channel logout notifications to participating applications within a session.

### Security Considerations

**PKCE:**
1. Generate random `code_verifier` (43-128 characters)
2. Create `code_challenge` = BASE64URL(SHA256(code_verifier))
3. Send `code_challenge` and `code_challenge_method=S256` in authorize request
4. Send `code_verifier` in token request

**State Parameter:** Always include a random `state` parameter to prevent CSRF attacks.

**Nonce Parameter:** Include a random `nonce` to prevent token replay attacks.

### TCP Dynamic Auth (.NET)

For ASP.NET applications:

```csharp
services.AddTcpDynamicAuth(Configuration, options =>
{
    options.Authority = "https://idgw.tylerportico.com/tg";
    options.ClientId = Configuration["OIDC:ClientId"];
    options.ClientSecret = Configuration["OIDC:ClientSecret"];
});
```

---

<!-- SOURCE: identity/workforce/faq -->

## Identity Workforce FAQ

**Does a customer have to have a cloud identity provider?**
Yes, the customer must have an IdP that is publicly accessible from the internet.

**How does the Gateway provide authentication and single sign-on?**
The gateway utilizes standard OIDC protocols and flows for product integration.

**What federation protocols does the Gateway support for customer IdPs?**
The Gateway supports both **OIDC (OpenID Connect)** and **SAML 2.0** for federating with customer Identity Providers. Your Tyler application integrates with the Gateway using OIDC, and the Gateway handles the federation to the customer's IdP using either OIDC or SAML as configured in Admin Center.

**How many identity clients are required if a product has multiple applications?**
Normally, the product only needs a single identity client per environment. The Gateway supports wildcard redirects:
- `*.tylerportico.com/portal/enterpriselauncher`
- `*.tylerportico.com/notify/*`
- `hub.tylerapp.com/*`

**Does the Gateway support OAuth2 flows for securing APIs?**
Yes, the gateway has full support for confidential clients, token creation, and introspection. The gateway also supports security of scopes by client.

**How many CCF clients are needed?**
1. **Multi-tenant cloud product**: Only need a single CCF client per product
2. **Cloud product deployed per customer**: Need a CCF client per customer and/or environment
3. **On-premise**: Recommend a client per product per environment

**Does the Gateway support rolling client secrets?**
Yes, the Gateway supports client secret rotation. See Client Operations for details.

**What is a Credentials Template?**
A credentials template is utilized by on-premise products for the generation of identity clients that will be utilized to authenticate via the gateway.

**What is the strategy for the use of scopes?**
Recommend at least 1 scope defined by your product. Default scope for any platform related service calls via CCF: `tyler-cloud-platform-api-access`.

**What is the lifetime of a token issued by the Gateway?**
The maximum lifetime is 60 minutes. Your applications should respect this time limit and only run a token refresh at the time of expiration.

**Does the Gateway support Federated Logout?**
Yes, the Gateway does support federated logout. **Note**: Not all IdPs support federated logout.

**Does the Gateway support back-channel logout?**
Contact the Identity team for current support status.

**Can I brand the login page?**
No. The login page only implements standard Tyler branding. The login page load time is critical to providing a good user experience.

**How can I tell what organization context a particular user is operating under by the token?**
Both the identity and access tokens issued by the Gateway contain the `organizationKey` claim. `organizationKey` has replaced `crmId` (still included for backward compatibility).

**Does the Gateway include user group memberships in tokens?**
No. Group information is not available via the `groups` scope or any other scope. Applications must implement their own authorization logic and user-to-role mappings.

**Can I extend or customize claims in tokens issued by the Gateway?**
No. The Gateway does not support custom claim mapping or claim extensions. Applications that need custom claims should retrieve them from their own data stores or use Platform Events to synchronize user data.

**Does the Gateway support Dynamic Client Registration?**
No. Clients must be registered manually via Service Desk or through Credential Templates.

---

<!-- SOURCE: identity/workforce/login-context -->

## Login Context with Identity Workforce

### Background

The TCP platform is structured by _organizations_ and _workspaces_. Organizations represent a customer or agency; workspaces correlate to environments like "test", "stage", and "production". Products are licensed to organizations and software is made available to workspaces.

Tyler applications can operate in either an **organization-forward** or **user-forward** fashion. Most operate as organization-forward:
- A SaaS product where the organization or workspace is indicated in the URL (subdomain)
- On-Prem application deployed into a specific customer environment
- A product deployed onto a cloud server dedicated to a single customer or environment

Applications that are organization-forward need a way to pass context to TID Gateway during login.

### Indicating Context

Include a custom query parameter when redirecting to the `/authorize` endpoint:

- `workspaceKey` — **(preferred)** the specific workspace for an organization
- `organizationKey` — the organization's identifier

Passing in the workspace is preferred as it allows resolution of the customer as well, resulting in better security practices.

### Context in id_tokens

When login context is supplied, the OIDC `id_token` will reflect that context:

```json
{
  "organizationKey": "demo",
  "workspaceKey": "demo-test"
}
```

When only `workspaceKey` is supplied, the `organizationKey` claim is automatically resolved and included.

### Context in access_tokens

Context is represented by scopes using patterns: `org:<organizationKey>` and `wks:<workspaceKey>`.

Example `scope` claim from an `access_token`:
```json
{
  "scope": "app-read-scope org:demo wks:demo-test"
}
```

These are permissive scopes available to every client.

**Token Refresh Behavior:** When an `access_token` is refreshed using a `refresh_token`, the new `access_token` will include the appropriate context scopes based on the original login context. Each token chain maintains its original context independently.

### Session Management and Context Switching

User sessions in TID Gateway are **not tied to login context**:
- A user can log in with different organizational contexts without triggering a new authentication session
- Switching between contexts does not require the user to re-authenticate
- Multiple active token sets can exist for the same user, each with different context scopes

### Context with CCF Tokens

Include context scopes in client credentials flow requests. These are permissive scopes, and all clients will have access to them by default. The primary use case is request-level context, not authorization.

**Token Caching Note:** If you include a context scope in a token, you have limited the usability of that token to a specific context. You may need to cache hundreds of tokens (one per context) rather than a single cached token.

**Limiting Context:** To constrain a client to only being able to acquire tokens with a specific scope, include the workspace scope at time of client creation. Once explicitly assigned, the client is limited to that scope. All other token requests will fail with `invalid_scope`.

---

<!-- SOURCE: identity/workforce/tokens -->

## Identity Workforce Token Examples

### Identity Token

```json
{
  "iss": "https://idgw.tcpci.com/tg",
  "nbf": 1725990472,
  "iat": 1725990472,
  "exp": 1725990772,
  "auth_time": 1725990471,
  "nonce": "638615872623901000.NWV...",
  "at_hash": "z2GsnugcGzgYn5sLGr0B5w",
  "sid": "44A2D98725F184754A0456F21A61A1AC",
  "aud": "lAjmONb9F0w80y6C",
  "sub": "00uz5pj5m5JswzW3G0h7",
  "preferred_username": "jason.howard@tylertech.com",
  "home_org": "demo",
  "crmid": "demo",
  "idp": "demo",
  "amr": [ "pwd" ],
  "acr": "urn:tidg:password"
}
```

| Claim | Description |
|-------|-------------|
| `iss` | Issuer — Gateway URL |
| `nbf` | Not Before — time before which the token must not be accepted |
| `iat` | Issued At |
| `exp` | Expiration Time |
| `auth_time` | Authentication Time |
| `at_hash` | Access Token Hash |
| `nonce` | Nonce — mitigates replay attacks |
| `sid` | Session ID |
| `aud` | Audience — client ID of the application |
| `sub` | Subject — unique identifier for the authenticated user |
| `preferred_username` | Username of the user |
| `home_org` | Tyler organizationKey identifier for the user's organization |
| `crmid` | (deprecated — use home_org) Tyler organizationKey identifier |
| `idp` | (deprecated) Tyler organizationKey identifier |
| `amr` | Authentication Methods References |
| `acr` | Authentication Context Class Reference |

### Interactive Access Token

```json
{
  "iss": "https://idgw.tcpci.com/tg",
  "nbf": 1725990472,
  "iat": 1725990472,
  "exp": 1725994072,
  "auth_time": 1725990471,
  "sid": "44A2D98725F184754A0456F21A61A1AC",
  "aud": "api://tylerapps",
  "scope": "openid profile email",
  "sub": "e3rzCgLyMuT84ukC",
  "preferred_username": "jason.howard@tylertech.com",
  "home_org": "demo",
  "client_id": "lAjmONb9F0w80y6C",
  "cid": "lAjmONb9F0w80y6C",
  "crmid": "demo",
  "idp": "demo"
}
```

### User Info Endpoint

```json
{
  "sub": "00uz5pj5m5JswzW3G0h7",
  "preferred_username": "jason.howard@tylertech.com",
  "home_org": "demo",
  "given_name": "Jason",
  "family_name": "Howard",
  "email": "jason.howard@tylertech.com",
  "name": "Jason Howard",
  "crmid": "demo"
}
```

To retrieve the full set of claims for login, you must include these three scopes: `openid`, `email`, `profile`. Enable "get claims from UserInfo endpoint" in your OIDC configuration.

### CCF Access Token

```json
{
  "iss": "https://idgw.tcpci.com/tg",
  "nbf": 1706808837,
  "iat": 1706808837,
  "exp": 1706812437,
  "aud": "api://tylerapps",
  "scope": "scope1, scope2",
  "client_id": "sampleclient14i7z98",
  "sub": "samplesub1adf81",
  "cid": "sampleclient14i7z98"
}
```

---

<!-- SOURCE: identity/workforce/tokens/amr-passthrough -->

## AMR Passthrough

TID Gateway acts as a federation broker by abstracting federated login details from Tyler applications. The gateway does not store credentials or handle MFA duties directly. Instead, the federated identity providers handle this functionality and then send signals about the involved factors back to the gateway during login.

### AMR Claim

The `amr` claim — Authentication Methods References — is a list of the authentication methods used during login (e.g., password, SMS, OTP).

When a federated identity provider provides an AMR value during login, the gateway automatically includes that same `amr` claim as well as an `acr` claim in the `id_token`.

### ACR Claim

The `acr` claim (Authentication Context Class Reference) is an interpretation of the `amr` claims.

| Value | Description |
|-------|-------------|
| `<none>` | If no AMR information comes through the federated login, the `acr` claim will not be included |
| `urn:tidg:password` | User logged in with only password as a factor |
| `urn:tidg:mfa` | User logged in with some form of MFA |
| `urn:tidg:aal2` | User logged in with NIST AAL2 compliant factors |

**Recommendation**: Rely on the `acr` claim over interpreting the `amr` values directly. This allows your applications to receive a predictable set of claims, while the gateway acts as an adapter to accommodate variations across different identity providers.

### Federated Complications

Complications arise when a federation "bounces through" one or more IDPs, because not all IDPs support passing the `amr` claim through their system.

**Standard managed Okta setup for tylertech.com users:**
```
tid-gateway --OIDC--> Managed Okta Tenant --SAML--> tide-broker (Okta) --OIDC--> sso.tylertech.com (Okta)
```

This works seamlessly while also limiting the TID team's access to the corporate-managed Okta tenant.

### Known Outliers

**Google Workspace**: Tokens do not include the `amr` claim. `amr` will not be available when a customer federates to Google, either directly or via chaining.

**Auth0**: Will only include the `amr` claim if it is the one to challenge a user. Federated users will not include the claim.

---

<!-- SOURCE: identity/workforce/troubleshooting -->

## Troubleshooting Identity Workforce

### Debugging Gateway Errors with DataDog

When an error occurs during Gateway authentication, the error page displays a **Request ID**. To view detailed logs in DataDog:

**DataDog URL Pattern:**
```
https://app.datadoghq.com/logs?query=service%3Atid-gateway-w%20env%3A{ENVIRONMENT}%20%40Properties.RequestId%3A%22{REQUEST_ID}%22
```

**Environment Values:**
- `tcpci` → `tcpci-1`
- `tcpqa` → `tcpqa-1`
- `tylerportico` (Production) → `tcpprod-1`

### Authentication Issues

**"Organization not found" or "Invalid organizationKey"**
- Verify `organizationKey` is included in the `/authorize` request
- Confirm the organization key value in Ops Center
- Check that the organization has an IdP configured in Admin Center
- Verify you're testing in the correct environment

**"redirect_uri_mismatch"**
- Ensure exact match including protocol, domain, port, path, and trailing slash
- For local development: Use `http://localhost:port/callback` (localhost allows http)

**"Invalid client_id" or "Client not found"**
- Verify client ID matches registration exactly
- Confirm you're using the correct environment's client ID
- Check for leading/trailing whitespace

**"invalid_grant" on Token Exchange**
- Authorization code has expired (5-minute lifetime)
- Authorization code already used
- Code verifier doesn't match code challenge (PKCE)
- Wrong client credentials

### Token Validation Issues

**"Signature verification failed"**
- Verify JWKS endpoint: `https://idgw.tylerportico.com/tg/.well-known/openid-configuration/jwks`
- Allow for clock skew (5 minutes recommended): `ClockSkew = TimeSpan.FromMinutes(5)`
- Ensure key cache refresh is working

**"Invalid audience"**
- Gateway uses a static audience `api://tylerapps`
- **Disable audience validation** or set it to accept `api://tylerapps`:

```csharp
TokenValidationParameters = new TokenValidationParameters
{
    ValidateAudience = false,  // Recommended
    // OR
    ValidAudiences = new[] { "api://tylerapps" }
};
```

**"Token expired"**
- Token lifetime exceeded (typically 1 hour)
- Use refresh tokens to obtain new access tokens
- Verify system clocks are synchronized (NTP)

**Missing or Incorrect `organizationKey` Claim**
- Verify `organizationKey` parameter was included in authorization request
- For Tyler employees: `organizationKey` will be `tylertechnologiestx` (expected behavior)
- For client credentials tokens: These don't have organization context
- Extract from both `organizationKey` and `crmId` claims (legacy support):
```csharp
var orgKey = claims.FirstOrDefault(c => c.Type == "organizationKey")?.Value
          ?? claims.FirstOrDefault(c => c.Type == "crmId")?.Value;
```

### IdP Federation Issues

**"IdP not configured for organization"**
- Verify IdP configuration exists in Admin Center for the organization
- Check IdP metadata URL is accessible
- Confirm organization is enabled for Workforce Direct

**User Stuck in Authentication Loop**
- Check browser console for cookie/CORS errors
- Verify state parameter is being validated correctly
- Test with browser in incognito/private mode
- Ensure session cookies are being set (SameSite, Secure attributes)

**User Cannot Logout / Immediately Logged Back In**

How this happens:
1. User clicks logout → Application calls Gateway logout endpoint
2. Gateway logs out the session and redirects back to application
3. Application's landing page requires authentication → immediately redirects back to Gateway
4. Gateway redirects to customer IdP → IdP still has an active session → automatically logs user back in

Solutions:
1. After Gateway logout, redirect to a **public page that doesn't require authentication**
2. Use the `post_logout_redirect_uri` parameter in logout requests
3. Note that **Google Workspace does NOT support federated logout**; this is an IdP limitation
4. Set expectations with users that closing the browser may be needed for complete logout

**SAML/OIDC Protocol Errors at IdP**
- Verify IdP metadata in Admin Center matches customer's current configuration
- Check required SAML attributes/OIDC claims are configured (Email, Username, First name/Last name)
- Validate IdP certificate is current

### Configuration Issues

**Dynamic Auth Library Not Finding Authority**
- Verify network connectivity to provisioning service
- Check organization exists in Ops Center
- Ensure Dynamic Auth is configured with correct base URL

**Refresh Token Not Working**
- Include `offline_access` scope in initial authorization request
- Check refresh token expiration (typically 90 days)
- Verify client secret is correct

### Debugging Tools

**Decode JWT Tokens:** Use jwt.io or jwt-decode library

**Test OAuth Flow Manually:**
```bash
curl -X POST https://idgw.tcpci.com/tg/oauth2/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=...&client_id=...&client_secret=..."
```

**Enable Detailed Logging (ASP.NET Core):**
```json
{
  "Logging": {
    "LogLevel": {
      "Microsoft.AspNetCore.Authentication": "Debug",
      "IdentityModel": "Debug"
    }
  }
}
```

---

<!-- SOURCE: identity/workforce/best-practices -->

## Identity Workforce Best Practices

### Security Best Practices

**Always Use PKCE** — Required for SPAs and mobile apps; strongly recommended for all applications.

**Validate All Token Claims:**
```csharp
var validationParameters = new TokenValidationParameters
{
    ValidateIssuer = true,
    ValidIssuer = "https://idgw.tylerportico.com/tg",
    ValidateAudience = false, // Gateway uses static audience
    ValidateLifetime = true,
    ClockSkew = TimeSpan.FromMinutes(5),
    ValidateIssuerSigningKey = true,
    RequireExpirationTime = true,
    RequireSignedTokens = true
};
```

**Protect Client Secrets — Never:**
- Commit secrets to source control
- Store secrets in client-side code
- Log secrets in application logs
- Hardcode secrets in configuration files

**Always:**
- Use environment variables or secure vaults (Azure Key Vault, AWS Secrets Manager)
- Rotate secrets periodically
- Use different secrets per environment

**Use HTTPS Everywhere:** All production redirect URIs must use HTTPS. Only localhost can use HTTP.

**Implement Secure Session Management:**
```csharp
services.AddSession(options =>
{
    options.IdleTimeout = TimeSpan.FromHours(1);
    options.Cookie.HttpOnly = true;
    options.Cookie.SecurePolicy = CookieSecurePolicy.Always;
    options.Cookie.SameSite = SameSiteMode.Lax;
});
```

### Organization Key Management

**Obtaining the Organization Key:**
1. Retrieved from Ops Center for each customer/organization
2. Stored in your application's tenant/organization context
3. Passed in every authorization request to the Gateway

**Multi-Tenant Applications — Manual Session-Based Approach:**
```csharp
HttpContext.Session.SetString("organizationKey", selectedOrgKey);

options.Events = new OpenIdConnectEvents
{
    OnRedirectToIdentityProvider = context =>
    {
        var orgKey = context.HttpContext.Session.GetString("organizationKey");
        if (string.IsNullOrEmpty(orgKey))
        {
            context.HandleResponse();
            context.Response.Redirect("/select-organization");
            return Task.CompletedTask;
        }
        context.ProtocolMessage.Parameters.Add("organizationKey", orgKey);
        return Task.CompletedTask;
    }
};
```

**Using Finbuckle.MultiTenant Library:** Provides comprehensive multi-tenancy capabilities for ASP.NET Core applications, including authentication per tenant. See Finbuckle.MultiTenant documentation for details.

### Testing Practices

**Required:**
- Test with at least 3 different organizations
- Use actual test user accounts (not Tyler employees)
- Test in all environments (Dev → QA → Prod)
- Verify `organizationKey` claim is correctly populated
- Test organization switching scenarios

**Operational Testing Requirements:**
1. Complete integration testing in TCPCI
2. Complete QA testing in TCPQA
3. **Required:** Operational testing with `tylertownwa` tenant in production

### Performance Optimization

- **Cache JWKS Keys:** Token validation requires fetching JWKS keys; JWKS are automatically cached by most libraries (default ~24 hours)
- **Minimize Token Validation Overhead:** Cache validated tokens; use in-memory token caches; implement proper key rotation handling
- **Use Token Introspection Sparingly:** JWT validation (signature + claims) is preferred over introspection

### Architecture Patterns

**Backend-for-Frontend (BFF) Pattern** — Recommended for SPAs:
- Keeps tokens server-side (more secure)
- Simplifies token management
- Reduces SPA complexity

**API Security with Gateway Tokens:**
```csharp
services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options =>
    {
        options.Authority = "https://idgw.tylerportico.com/tg";
        options.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = false, // Gateway uses static audience
            ValidateLifetime = true
        };
    });

[Authorize]
public IActionResult GetData()
{
    var orgKey = User.FindFirst("organizationKey")?.Value;
    return Ok(dataService.GetByOrganization(orgKey));
}
```

**Dual Trust for Migration:**
```csharp
services.AddAuthentication()
    .AddJwtBearer("Gateway", options =>
    {
        options.Authority = "https://idgw.tylerportico.com/tg";
    })
    .AddJwtBearer("Legacy", options =>
    {
        options.Authority = "https://legacy-idp.com";
    });

services.AddAuthorization(options =>
{
    options.DefaultPolicy = new AuthorizationPolicyBuilder()
        .RequireAuthenticatedUser()
        .AddAuthenticationSchemes("Gateway", "Legacy")
        .Build();
});
```

**User Just-In-Time Provisioning Flow:**

When a user logs in:
1. Does the `sub` match the user's sub in application? → Yes: Update profile and username from Id token
2. No: Does the username match a username and organizationKey in the application? → Yes: Update User sub in application, then update profile
3. No: Does the application have an on-board process for new users? → Yes: User is authenticated; No: Deny Access

### Common Anti-Patterns to Avoid

**Don't:**
- Store tokens in localStorage (XSS risk for SPAs)
- Skip token validation
- Hardcode organization keys
- Ignore token expiration
- Use implicit flow (deprecated)
- Validate audience claim strictly (Gateway uses static value)
- Implement custom crypto (use standard libraries)
- Trust client-side organization selection without server validation

**Do:**
- Use httpOnly cookies for tokens
- Validate all token claims
- Fetch organization keys from secure configuration
- Implement token refresh
- Use Authorization Code + PKCE flow
- Disable or accommodate static audience value
- Use vetted OIDC libraries
- Validate organization context server-side

---

<!-- SOURCE: identity/workforce/dynamic-auth/overview -->

## Dynamic Auth Overview (.NET)

**TCP Dynamic Auth** is an optional .NET library that simplifies Identity Gateway integration for ASP.NET applications. This library is **not required** to integrate with the Gateway — you can use any certified OIDC library.

**This library is only available for .NET applications.**

### When to Use Dynamic Auth

**Use Dynamic Auth if:**
- You're building an ASP.NET / ASP.NET Core application
- You want simplified configuration with automatic `organizationKey` handling
- Your application is multi-tenant (same deployment serves multiple organizations)
- You want built-in session management and token refresh handling

**Don't use Dynamic Auth if:**
- You're using a non-.NET technology stack
- You prefer direct control over OIDC configuration

### Benefits

1. **Automatic organizationKey Handling**: Automatically includes the `organizationKey` parameter in authorization requests based on the workspace context
2. **Session Cookie Management**: Pre-configured secure cookie policies for TCP environments
3. **Automatic Token Refresh**: Built-in token refresh logic
4. **Simplified Multi-Tenant Configuration**: Handles complexity of determining which organization's identity configuration to use

### How It Works

1. **Application Registration**: Your application is registered in TCP with a unique `AppRegistrationId`
2. **Configuration Lookup**: Dynamic Auth queries the provisioning service with your app registration ID, environment, and workspace
3. **Configuration Resolution**: The service returns the client credentials and `organizationKey` for the current workspace
4. **OIDC Flow**: Dynamic Auth configures ASP.NET authentication middleware with the resolved settings

### Alternatives to Dynamic Auth

- **Standard OIDC Libraries**: Use Microsoft.AspNetCore.Authentication.OpenIdConnect directly with static Gateway configuration
- **Other Technology Stacks**: Use certified OIDC libraries for your platform
- **Single-Tenant Deployments**: Use Credential Templates with static configuration

---

<!-- SOURCE: identity/workforce/dynamic-auth/using -->

## Using Dynamic Auth (.NET) — Installation and Configuration

**Prerequisites:** ASP.NET Core 6.0 or later; product must be registered; application must have a unique registration ID.

### 1. Add NuGet Package

```bash
dotnet add package Tyler.Platform.DynamicAuth
```

### 2. Configure Application Registration ID

Add to `appsettings.json`:
```json
{
  "AppRegistrationId": "YourApp-Name"
}
```

The `AppRegistrationId` must match the registration ID used when registering your product with TCP (from `registrationId` or `title` field in product registration JSON).

### 3. Add Services

**For ASP.NET Core 6+ minimal hosting (Program.cs):**
```csharp
builder.Services.AddTcpAuthentication(builder.Configuration);
builder.Services.AddTidIdentityConfigurationService(builder.Configuration);
```

### 4. Add Middleware

```csharp
app.UseTcpCookiePolicy(app.Configuration);
app.UseRouting();
app.UseTcpAuthentication();
```

### 5. Cookie Policy Extension Method

```csharp
public static IApplicationBuilder UseTcpCookiePolicy(
    this IApplicationBuilder app,
    IConfiguration configuration)
{
    var envDomainProtocol = configuration.GetValue<string>("EnvironmentDomainProtocol");
    var useHttp = envDomainProtocol == "http";

    app.UseCookiePolicy(new CookiePolicyOptions
    {
        MinimumSameSitePolicy = useHttp ? SameSiteMode.Lax : SameSiteMode.None,
        Secure = useHttp ? CookieSecurePolicy.SameAsRequest : CookieSecurePolicy.Always
    });

    return app;
}
```

### Usage in Controllers

```csharp
[Authorize]
public class SecureController : Controller
{
    public IActionResult Index()
    {
        var username = User.FindFirst("preferred_username")?.Value;
        var orgKey = User.FindFirst("organizationKey")?.Value;
        return View();
    }
}
```

### Required Configuration

```json
{
  "AppRegistrationId": "YourApp-Name",
  "EnvironmentDomainProtocol": "https"
}
```

### Troubleshooting

**Authority Resolution Fails**: Verify `AppRegistrationId` in `appsettings.json` matches your product registration; product is registered in the target environment; application is running in a valid TCP workspace context.

**organizationKey Not Found**: Ensure your application is accessed via a valid workspace subdomain; workspace has identity configuration in the provisioning service.

**Cookie Issues**: Ensure `UseTcpCookiePolicy()` is called before `UseTcpAuthentication()`; `EnvironmentDomainProtocol` is set correctly.

---

<!-- SOURCE: identity/workforce/diagrams/auth-code-flow-pkce -->

## Authorization Code Flow with PKCE (Sequence)

```
Workforce User → Your Application → Identity Gateway → Customer IdP

1. User clicks "Sign In"
2. Application generates PKCE parameters:
   - code_verifier (random)
   - code_challenge = SHA256(verifier)
   - stores code_verifier in session
3. Application builds authorization request (state, nonce, organizationKey)
4. Application redirects to /authorize with:
   - client_id, redirect_uri, scope
   - organizationKey
   - code_challenge, state, nonce
5. Gateway routes to Customer IdP using organizationKey
6. Customer's login page displayed; user enters credentials
7. IdP validates credentials, returns authentication response to Gateway
8. Gateway creates authorization code, redirects to callback with authorization code + state
9. Application verifies state, retrieves code_verifier from session
10. Application POSTs /token with: authorization code + code_verifier + client_id, client_secret
11. Gateway verifies code_challenge matches SHA256(code_verifier), validates authorization code
12. Gateway returns ID token + Access token + Refresh token (optional)
13. Application validates tokens (signature, nonce, issuer, audience), extracts organizationKey claim
14. User authenticated — redirect to application
```

**Security Notes:**
- PKCE is **strongly recommended** for all applications, **required** for SPAs and mobile apps
- The `code_verifier` never leaves the application
- The `code_challenge` is sent in the authorization request
- Gateway verifies the verifier matches the challenge during token exchange

---

<!-- SOURCE: identity/community/getting-started -->

# 4. Community Access

## Getting Started with Community Access

Community Access is Tyler's single sign-on solution for citizen and resident-facing applications. Built on Okta, Community Access provides a consistent, branded authentication experience for all public-facing Tyler applications.

Community Access is built on the OpenID Connect (OIDC) standard.

### Overview

Community Access serves as the foundation for Tyler's Citizen Experience (CX) strategy by providing:
- **Single Identity**: One account for residents across all Tyler applications and jurisdictions
- **Branded Experience**: Customizable login pages reflecting local government branding
- **Shared Authentication**: Single Okta tenant shared across all Tyler community applications
- **Standards-Based**: Built on OpenID Connect and OAuth 2.0 protocols

Unlike Identity Workforce (which connects to customer-managed IdPs via the Gateway), Community Access uses a **centralized Okta tenant managed by Tyler**.

### Architecture

Community Access supports two authentication models:

**Standard Authentication (Tyler-Managed Okta):** For most jurisdictions, citizens authenticate directly with Tyler's Okta tenant.

**Federated Authentication (State-Managed IdP):** For state-level or jurisdictional tenants, citizens authenticate with their state's IdP, which is federated with Tyler's Okta.

Benefits of Federated Authentication:
- Citizens use their existing state credentials
- Compliance with state identity requirements
- State maintains control of user directory
- Single sign-on across state services

### Integration Steps

#### 1. Register Your Application

**Single-Tenant Applications** (deployed per customer):
- Create a Credentials Template
- Template is applied during deployment
- Okta client credentials are automatically provisioned

**Multi-Tenant Applications** (deployed once for all customers):
- Submit an Identity Client Ticket for each environment
- Start with Dev environment and progress through QA to Production

#### 2. Implement OIDC Authentication with PKCE

Community Access requires **Authorization Code Flow + PKCE**.

**Why PKCE is Required:**
- Public-facing applications cannot securely store client secrets
- PKCE prevents authorization code interception attacks
- Industry best practice for SPAs and mobile apps

**Tyler provides:** Community Dynamic Auth (https://github.com/tyler-technologies/tidc-dynamic-auth) — .NET library for simplified Community Access integration.

#### 3. Configure Routing Parameters

**Workspace Parameter (Standard Routing):** For jurisdictions using Tyler-managed Okta authentication:
```
&workspace={WorkspaceIdentifier}
```
The `WorkspaceIdentifier` is the platform workspace identifier obtained from Ops Center.

**IdpId Parameter (Federated Routing):** For state-level or jurisdictional tenants with their own federated identity provider:
```
&idp={IdpId}
```
The `IdpId` is the Okta identity provider ID obtained from Ops Center or via Service Desk.

**When to use each:**

| Scenario | Parameter | Example |
| -------- | --------- | ------- |
| City/County managed by Tyler Okta | `workspace` | `&workspace=cityofaustin` |
| State with federated IdP | `idp` | `&idp=0oaXXXXXXXXXXXXXX` |
| Multiple jurisdictions in same app | Both (conditional) | Use workspace or idp based on jurisdiction |

**Federated State Identity Providers — Citizen Experience:**
1. Citizen clicks login in Tyler application
2. Application redirects to Okta with `idp` parameter
3. Okta immediately redirects to state IdP (no Okta login screen)
4. Citizen logs in with state credentials
5. State IdP authenticates and returns to Okta
6. Okta issues tokens to Tyler application
7. Citizen is logged into Tyler application

**Key Differences:**

| Aspect | Standard Okta | Federated State IdP |
| ------ | ------------- | ------------------- |
| **User Directory** | Tyler's Okta | State's IdP |
| **Login Screen** | Tyler branded Okta | State's login page |
| **User Accounts** | Citizens create Tyler accounts | State-managed accounts |
| **Password Management** | Tyler/Okta handles | State handles |
| **Self-Registration** | Supported in Tyler Okta | Managed by state |

#### 4. Handle User Registration

Community Access supports self-service user registration:
- Users can create new accounts during login flow
- Account is created in Tyler's Okta tenant
- Same account works across all Tyler community applications

### Token Validation

Validate ID and access tokens for:
- **Issuer** (`iss`): Verify token is from Tyler's Okta tenant
- **Expiration** (`exp`): Check token hasn't expired
- **Scopes**: Verify required scopes are present
- **Audience** (`aud`):
  - ID tokens: Audience is your client ID
  - Access tokens: Audience is `api://default`

**Example ID Token:**
```json
{
  "sub": "00u5pq6ggCymihPpl1d6",
  "name": "Joe Citizen",
  "email": "joe.citizen@mailinator.com",
  "iss": "https://tylercitizen.oktapreview.com/oauth2/default",
  "aud": "0oa22ws7yz5OlwyZI1d7",
  "preferred_username": "joe.citizen@mailinator.com",
  "workspaceId": "cityoftyler"
}
```

**Example Access Token:**
```json
{
  "iss": "https://tylercitizen.oktapreview.com/oauth2/default",
  "aud": "api://default",
  "sub": "00u5pq6ggCymihPpl1d6",
  "scp": ["openid", "email", "profile"],
  "preferred_username": "joe.citizen@mailinator.com",
  "given_name": "Joe",
  "family_name": "Citizen",
  "email": "joe.citizen@mailinator.com"
}
```

### Generate PKCE Parameters

```javascript
function generateCodeVerifier() {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return base64URLEncode(array);
}

async function generateCodeChallenge(verifier) {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return base64URLEncode(hash);
}

sessionStorage.setItem('code_verifier', codeVerifier);
```

### Authorization Request

**Standard routing with workspace parameter:**
```http
GET {okta_authority}/oauth2/authorize?
  response_type=code
  &client_id={your_client_id}
  &redirect_uri={your_redirect_uri}
  &scope=openid%20profile%20email
  &workspace={workspace_id}
  &state={random_state}
  &nonce={random_nonce}
  &code_challenge={code_challenge}
  &code_challenge_method=S256
```

**Federated routing with idp parameter:**
```http
GET {okta_authority}/oauth2/authorize?
  response_type=code
  &client_id={your_client_id}
  &redirect_uri={your_redirect_uri}
  &scope=openid%20profile%20email
  &idp={state_idp_id}
  &state={random_state}
  &nonce={random_nonce}
  &code_challenge={code_challenge}
  &code_challenge_method=S256
```

Do not use both `workspace` and `idp` parameters in the same request.

### Token Exchange

```http
POST {okta_authority}/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
&code={authorization_code}
&redirect_uri={same_redirect_uri}
&client_id={your_client_id}
&code_verifier={code_verifier_from_session}
```

---

<!-- SOURCE: identity/community/configuration -->

## Community Access Configuration

### Okta Endpoints

| Environment | Purpose |
| ----------- | ------- |
| **Dev** | Development and initial integration testing |
| **QA** | Quality assurance and pre-production testing |
| **Production** | Live citizen-facing applications |

Standard OIDC discovery: `{okta_authority}/.well-known/openid-configuration`

Common endpoints:
- **Authorization**: `{okta_authority}/oauth2/authorize`
- **Token**: `{okta_authority}/oauth2/token`
- **UserInfo**: `{okta_authority}/oauth2/userinfo`
- **JWKS**: `{okta_authority}/oauth2/v1/keys`
- **End Session**: `{okta_authority}/oauth2/v1/logout`
- **Registration**: `{okta_authority}/oauth2/v1/register` (if self-registration enabled)

### Scopes

| Scope | Description | Required |
| ----- | ----------- | -------- |
| `openid` | Indicates OIDC flow | Yes |
| `profile` | Returns profile claims | Yes |
| `email` | Returns email claim | Yes |
| `offline_access` | Returns refresh token | Optional |

**Branding** is controlled via the `workspace` parameter (not a scope).

### Token Validation

**ID Token validation checklist:**
- **Issuer** (`iss`): Must match your Okta tenant
- **Audience** (`aud`): Must match your client ID (NOT `api://default`)
- **Expiration** (`exp`): Token must not be expired
- **Signature**: Verify using JWKS from Okta
- **Nonce**: Must match nonce from authorization request

**Access Token validation:**
- **Audience** (`aud`): Always `api://default` for access tokens
- **Client ID** (`cid`): The client that requested the token

**Access Token Validation Example (Node.js):**
```javascript
const oktaJwtVerifier = new OktaJwtVerifier({
  issuer: 'https://your-okta-domain.okta.com/oauth2/default',
  clientId: '{your_client_id}'
});

app.use(async (req, res, next) => {
  const token = req.headers.authorization?.replace('Bearer ', '');
  const jwt = await oktaJwtVerifier.verifyAccessToken(token, 'api://default');
  req.jwt = jwt;
  next();
});
```

### Application Configuration Examples

**React SPA:**
```javascript
const oktaAuth = new OktaAuth({
  issuer: 'https://your-okta-domain.okta.com/oauth2/default',
  clientId: process.env.REACT_APP_CLIENT_ID,
  redirectUri: window.location.origin + '/callback',
  scopes: ['openid', 'profile', 'email'],
  pkce: true,  // Required
  tokenManager: {
    storage: 'sessionStorage'  // More secure than localStorage
  }
});
```

### Branding Configuration

Branding is configured via Admin Center for the organization.

**Supported Branding Options:**
- **Logo**: PNG or SVG, recommended 200x50px, transparent background
- **Primary Color**: Main brand color (buttons, links)
- **Secondary Color**: Accent color

### User Registration Flow

**Directing Users to Registration:**
```javascript
const returnUri = encodeURIComponent(window.location.origin + '/callback');
const registrationUrl = `${oktaAuthority}/signin/register?fromURI=${returnUri}`;
window.location.href = registrationUrl;
```

**Important:** After registration completes, the user is redirected back to your application but **is NOT automatically authenticated**. Your application must initiate the login flow.

**Registration Flow:**
1. User clicks "Sign Up"
2. Application stores intended destination
3. Application redirects to Okta registration
4. User completes registration in Okta (email verification, password creation)
5. Okta redirects back to application (user NOT yet authenticated)
6. Application initiates login flow
7. User completes login
8. User is authenticated and redirected to original destination

---

<!-- SOURCE: identity/community/environments -->

## Community Access Environments

The following environments can be utilized for Community Access. **Note**: Customers are only allowed in the production environment.

| Environment | Usage | Authority | Well-known endpoint |
| ---- | ---- | ----------- | ----------------- |
| `tcpci` | development | https://identity.tcpci.com/oauth2/default | https://identity.tcpci.com/oauth2/default/.well-known/openid-configuration |
| `tcpqa` | quality assurance | https://identity.tcpqa.com/oauth2/default | https://identity.tcpqa.com/oauth2/default/.well-known/openid-configuration |
| `tylerportico` | Production | https://identity.tylerportico.com/oauth2/default | https://identity.tylerportico.com/oauth2/default/.well-known/openid-configuration |

All changes flow from `tcpci` -> `tcpqa` -> `tylerportico` via automated continuous deployment.

### Local Development

The Corpdev team provides a local development environment (https://github.com/tyler-technologies/platform-dev-environment-compose) that can be utilized for testing integrations with Community Access. This environment utilizes a mock IdP, allowing for login with any user, but exhibits the same authentication behavior as the cloud environments.

---

<!-- SOURCE: identity/community/troubleshooting -->

## Troubleshooting Community Access

### Authentication Issues

**"PKCE verification failed"**
- Ensure code verifier is stored securely (sessionStorage or secure cookie)
- Verify code challenge generation: `base64URLEncode(sha256(verifier))`
- Confirm code_verifier is sent in token request
- Ensure `code_challenge_method=S256` is in authorization request

**"invalid_client" or "Client authentication failed"**
- For SPAs and mobile apps: Remove `client_secret` from token request (public clients don't use secrets)
- Verify client ID matches Okta registration

**"redirect_uri_mismatch"**
- Ensure exact match including protocol, domain, port, path, trailing slash
- For localhost: Register `http://localhost:3000/callback` (port must match exactly)

**Branded Login Page Not Appearing**
- Verify authorization request includes workspace parameter: `&workspace=cityofseattle`
- Confirm workspace identifier is correct (from Ops Center)
- Check branding has been configured in Admin Center

**User Stuck in Login Loop**
- Check browser console for cookie errors
- Test in incognito/private mode
- Verify state parameter validation
- Ensure cookies are being set with correct attributes: `httpOnly: true, secure: true, sameSite: 'lax'`

### Token Validation Issues

**"Signature verification failed"**
- Verify JWKS endpoint matches Okta tenant: `https://your-okta-domain.okta.com/oauth2/default/v1/keys`
- Allow for clock skew: `clockTolerance: 300` (seconds)

**"Token expired"**
- Refresh tokens before expiration (5 minutes recommended buffer)
- Use refresh tokens with `offline_access` scope

**"Invalid audience"**
- ID tokens: Audience is your client ID
- Access tokens: Audience is always `api://default`

**Nonce Mismatch**
- Generate and store nonce before authorization: `sessionStorage.setItem('oauth_nonce', nonce)`
- Include in authorization request: `&nonce={generated_nonce}`
- Validate on return: `idToken.nonce !== storedNonce`

### User Registration Issues

**Self-Service Registration Not Available**
- Verify self-registration is enabled via Service Desk
- Check registration URL: `${oktaUrl}/oauth2/v1/register?client_id=${clientId}`

**Email Verification Not Working**
- Check spam/junk folders
- Test with different email providers
- Contact Service Desk for email delivery logs

---

<!-- SOURCE: identity/community/best-practices -->

## Community Access Best Practices

### Always Use PKCE

**PKCE is MANDATORY for all Community Access applications.** Public-facing applications cannot securely store client secrets.

**Proper Implementation:**
```javascript
// 1. Generate secure code verifier
function generateCodeVerifier() {
  const array = new Uint8Array(64);
  crypto.getRandomValues(array);
  return base64URLEncode(array);
}

// 2. Create code challenge
async function generateCodeChallenge(verifier) {
  const encoder = new TextEncoder();
  const data = encoder.encode(verifier);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return base64URLEncode(new Uint8Array(hash));
}

// 3. Store verifier securely
sessionStorage.setItem('pkce_code_verifier', codeVerifier);
```

### Secure Token Storage

**NEVER:**
- Store tokens in localStorage (vulnerable to XSS)
- Store tokens in URL parameters
- Log tokens to console in production
- Send tokens over unencrypted connections

**DO:**
- SPAs: Use `sessionStorage` (cleared when browser closes) or in-memory storage
- Server-side: Use httpOnly, secure cookies
- Mobile: Use platform-specific secure storage (iOS Keychain, Android Keystore)

### Token Refresh Strategies

**Proactive Token Refresh:**
```javascript
async function ensureValidToken() {
  const expiresAt = getTokenExpiry();
  if (Date.now() >= expiresAt - 300000) {  // 5 min before expiration
    await refreshAccessToken();
  }
}
```

**Silent Token Renewal (SPAs):** Uses a hidden iframe with `prompt=none` to request new tokens without disrupting the user.

**Automatic Token Management with Okta Auth SDK:**
```javascript
const oktaAuth = new OktaAuth({
  tokenManager: {
    autoRenew: true,
    expireEarlySeconds: 300,  // Refresh 5 minutes early
    storage: 'sessionStorage'
  }
});
```

### Tyler Application Integration

**Calling Other Community Applications:** Use the `signin` parameter when linking between Tyler Community Access applications.

```javascript
// Build URL to another Tyler community application
function buildCommunityAppUrl(baseUrl, params = {}) {
  const url = new URL(baseUrl);
  if (isAuthenticated) {
    params.signin = 'true';
  }
  Object.entries(params).forEach(([key, value]) => {
    url.searchParams.set(key, value);
  });
  return url.toString();
}
// Result: https://permits.cityofseattle.gov?signin=true&application=building-permit
```

**Handling the signin Parameter (receiving application):**
```javascript
const shouldSignIn = urlParams.get('signin') === 'true';
if (shouldSignIn && !isAuthenticated) {
  oktaAuth.signInWithRedirect({ originalUri: window.location.pathname });
}
```

### Common Anti-Patterns to Avoid

**Don't:**
- Skip PKCE
- Store client secrets in frontend code
- Use implicit flow (deprecated)
- Ignore token expiration
- Use localStorage for tokens
- Hard-code jurisdiction identifiers
- Log tokens or PII

**Do:**
- Always use PKCE for public clients
- Keep authentication logic server-side where possible
- Use Authorization Code + PKCE flow
- Implement proactive token refresh
- Use sessionStorage or in-memory storage for tokens
- Make jurisdiction selection dynamic
- Validate all token claims

---

<!-- SOURCE: identity/shared/client-operations/overview -->

# 5. Shared Guides

## Client Operations

The **client-operations** endpoint enables basic management of manually created clients. This is primarily intended for teams that have **manually** created a **tid-gateway** client — clients not automatically provisioned by the platform. **Okta clients are not supported.**

### Available Operations

**Rotate Secret:** Generates a new secret for your client (CCF clients only). When rotating:
- A new secret is added to the client
- The existing secret is scheduled to expire in **3 days** (grace period)
- Use Expunge Old Secrets to immediately remove expired secrets

**Update Redirects:** Updates redirect URIs and post-logout redirect URIs for login clients. Wildcard subdomains and routes are supported. Useful for cloud applications with custom domains without a predictable pattern.

**Expunge Old Secrets:** Deletes all secrets except the most recent one. Most effective when paired with Rotate Secret.

### Endpoint Security

Security is enforced using:
1. An OAuth2 token with the `tidgateway:client-operations` scope
2. A one-time-use operations token unique to each client

When client operations are enabled:
- A **one-time operations token** is issued to the client
- Each successful request returns a **new operations token**

### Expected Usage

Applications should **not** be allowed to manage or rotate their own secrets directly. Instead, use a secure provisioning or orchestrator service to:
- Store each client's operations token securely
- Manage secret rotation
- Distribute updated configurations to your applications

This reinforces **Separation of Duties** and **Least Privilege**.

### Getting Started

1. Identify the manually created `tid-gateway` client you wish to manage
2. Enable client operations by submitting a ticket to the Tyler Identity Team with:
   - `Identity Client Name` field: your existing client name
   - `Identity Client Request Type`: set to `Enable Client Operations`
3. Wait for first operations token to be sent via Kiteworks
4. Review the API specification for implementation details

---

<!-- SOURCE: identity/shared/client-operations/api-spec -->

## Client Operations API Specification

### 1. Introduction

An owner of an OIDC or OAuth client needs the capability to rotate credentials or update client redirects. This endpoint supports:
- Rotate Secret
- Update Redirects
- Expunge Old Secrets

All requests must be accompanied by an Access Token that includes the `tidgateway:client-operations` scope in the Authorization header. All requests require an operations token that is consumed upon use — every successful request returns a new operations token.

### 2. Rotate Secret

**Request:**
```json
POST /client_operations HTTP/1.1
Host: server.example.com
Content-Type: application/json

{
  "operation_type": "rotate_secret",
  "client_id": "PEFzc2VydGl",
  "operations_token": "tGzv3JOkF0XG5Qx2TlKWIA"
}
```

**Successful Response:**
```json
HTTP/1.1 200 OK
{
  "client_secret": "KUwv30vbqwtYnmOhP",
  "operations_token": "jsd923490UnEJHA7890fds"
}
```

### 3. Update Redirects

The values of `redirect_uris` and `post_logout_redirect_uris` must be comprehensive. Any existing redirects not included in the list will be removed.

**Request:**
```json
POST /client_operations HTTP/1.1
{
  "operation_type": "update_redirects",
  "client_id": "LA9fx09A",
  "operations_token": "sLjiskI923lJ08Q8asjIBP",
  "redirect_uris": [
    "http://example.com/callback1",
    "http://example.com/callback2"
  ],
  "post_logout_redirect_uris": [
    "http://example.com/post-logout-callback1"
  ]
}
```

**Successful Response:**
```json
HTTP/1.1 200 OK
{
  "operations_token": "jsd923490UnEJHA7890fds"
}
```

### 4. Expunge Old Secrets

**Request:**
```json
POST /client_operations HTTP/1.1
{
  "operation_type": "expunge_old_secrets",
  "client_id": "LA9fx09A",
  "operations_token": "sLjiskI923lJ08Q8asjIBP"
}
```

### 5. Error Codes

| Error Code | Description |
|------------|-------------|
| `invalid_content` | The content type is invalid or cannot be parsed |
| `operation_type_required` | The parameter `operation_type` is not present |
| `client_id_required` | The parameter `client_id` is not present |
| `operations_token_required` | The parameter `operations_token` is not present |
| `invalid_operation_type` | The `operation_type` parameter is not one of the defined operation values |
| `client_not_found` | No client exists with the specified `client_id` |
| `redirect_uri_required` | Parameter `redirect_uri` is not present but required |
| `redirect_uris_not_allowed` | `redirect_uris` parameter is not allowed for the specified operation |
| `invalid_uri` | At least one of the supplied redirect URIs is not valid |
| `invalid_client` | The client does not support the specific operation being requested |
| `operations_not_supported` | The client does not support management via Client Operations endpoint |
| `invalid_operations_token` | The supplied `operations_token` is not valid for the client |

---

<!-- SOURCE: identity/shared/credential-templates/overview -->

## Credential Templates Overview

Credential Templates were made as a structured way to define the type of OAuth credentials your software needs upfront. This prevents people from needing to add or remove extra permissions, causing a security hole or your integrations to break. By ingesting these templates via GitHub, you get the benefits of your PR review process for being able to catch that extra step of too many privileges.

### System Design

There are 2 main points of contact with this feature: the development side and deployment side.
- The **development side** defines the templates
- The **deployment side** "applies" the templates to produce the corresponding credentials needed for runtime

---

<!-- SOURCE: identity/shared/credential-templates/github_app -->

## Credential Templates — GitHub App Overview

There are three instances of the GitHub App, one for each TCP environment. The primary operation of the GitHub app is to ingest your credential template definitions into the backing cluster service so your templates can be accessible and validated early on in the dev process.

The credential-config files must be in the default branch of the repository.

### Modes of Operation

**Credential Config Example:**
```yaml
# credential-config.tcpci.yaml
templateFolder: templates/tcpci
branches:
  - main
  - developers-branch

# credential-config.tcpqa.yaml
templateFolder: templates/tcpqa
branches:
  - main
```

**On Push (Ingest):** When a commit is pushed to a branch that matches a branch name in the credential config file. If someone pushes a change to `templates/tcpci` in `main` or `developers-branch`, the template files will be ingested into the TCPCI environment.

**On PR (Validation):** Occurs when a PR is opened where the base branch matches a branch name in the credential config file. The GitHub App requires the default branch to have at least 1 reviewer enforced via branch protections.

**On Check Rerun:** Occurs when the re-run button is clicked on the check run or check suite.

---

<!-- SOURCE: identity/shared/credential-templates/provisioning_sdk -->

## Credential Templates — Provisioning SDK

The Provisioning SDK is available as a dotnet NuGet package. Install with:
```bash
dotnet add package tcp-provisioningservice-sdk
```

### Construction

Build an `SdkConfiguration` object with:
- `BaseUrl`: Base URL of the TCP Provisioning service (typically ends with `/portal/provisioning`)
- `HttpClientFactory`: From IOC container after registering with `.AddHttpClient()`
- `AuthTokenAuthority`: Authority for Client Credential Flow credential (likely the TID Gateway address)
- `AuthTokenClientId`: Client ID for authenticating with `AuthTokenAuthority`
- `AuthTokenClientSecret`: Client secret
- `AuthTokenScopes`: Typically only `tyler-cloud-platform-api-access`

Pass the `SdkConfiguration` object into `tcp_provisioningservice_client.V2.CredentialTemplateClient` constructor.

### Using the Client

```csharp
// Generic Usage
var newClient = new tcp_provisioningservice_client.V2.CredentialTemplateClient(
    new TCP.NSwag.SDK.Base.TokenClient.SdkConfiguration
    {
        BaseUrl = "https://domain/portal/provisioning",
        HttpClientFactory = new YourFavoriteClientFactory(),
        AuthTokenAuthority = "https://idgw.domain.com/tg",
        AuthTokenClientId = "clientId",
        AuthTokenClientSecret = "clientSecret",
        AuthTokenScopes = new[] { "tyler-cloud-platform-api-access" }
    });

var applyResponse = await newClient.ApplyTemplateAsync(
    new tcp_provisioningservice_client.V2.ApplyTemplateContext
    {
        RegistrationId = "your platform registration id",
        TemplateVersion = "version to implement",
        TcpEnvKey = "localdev",
        WorkspaceKey = "your workspace",
        Variables = new()
        {
            { "variable1", "value of variable1" }
        }
    });
```

**Via Dependency Injection with Minimal API ASP.NET:**
```csharp
builder.Services.AddScoped<tcp_provisioningservice_client.V2.ICredentialTemplateClient>((provider) => {
    var configuration = provider.GetRequiredService<IConfiguration>();
    var httpClientFactory = provider.GetRequiredService<IHttpClientFactory>();

    return new tcp_provisioningservice_client.V2.CredentialTemplateClient(
        new TCP.NSwag.SDK.Base.TokenClient.SdkConfiguration {
            BaseUrl = configuration.GetValue<string>("Provisioning:BaseURL"),
            HttpClientFactory = httpClientFactory,
            AuthTokenAuthority = configuration.GetValue<string>("Provisioning:TokenAuthority"),
            AuthTokenClientId = configuration.GetValue<string>("Provisioning:ClientId"),
            AuthTokenClientSecret = configuration.GetValue<string>("Provisioning:ClientSecret"),
            AuthTokenScopes = new[] { "tyler-cloud-platform-api-access" }
        }
    );
});
```

---

<!-- SOURCE: identity/shared/credential-templates/recipes -->

## Credential Templates — Recipes Overview

The credential template system was designed to be flexible. Two choices: "Which repository you put those templates in?" and "How do I organize the templates in the repository?"

### Repository Organization for Ingest

**Templates per Repo:** Works if each team manages their own service, deployment pipeline, and repos. Pairs well with Single file per environment. PROS: Extremely great for properly separated services; can update templates in the same PR. CONS: Hard to maintain with poorly separated service boundaries.

**Templates in a Provisioning Repository:** Works if you have a single service that manages provisioning across the entire product. PROS: Easier to maintain, probably follows patterns in use today. CONS: Must be kept in sync with integration updates; may get unruly with multiple services.

**Templates in a Mono Repo:** Works if your entire solution is a monolithic repo. PROS: Probably follows patterns in use today; can be updated with integration updates. CONS: May get unruly to manage with multiple versions.

### Template Organization for Apply

**File Per Service:** Nice if you have multiple services associated with your product and use a single repository. Pairs well with Mono Repo and Provisioning Repo options.

**File Per Environment Separated by Branch:** Nice if you are planning on progressing the templates through branches tied to environments.

**Single File per Environment:** Incredibly simplistic. Pairs well with the Templates Per Repo option. Just a single file in each folder per environment.

**Most Common Example:** Combination of "Templates in Provisioning Repo" and "File per service option."

---

<!-- SOURCE: identity/shared/credential-templates/schemas/credentialconfig -->

## Credential Templates — Schema: `credential-config.<environment>.yaml`

Contains the configuration per environment for the GitHub App to know where and which branch it can find the credential template files.

**Example:**
```yaml
templateFolder: reporoot/templatefolder
branches:
- main
```

Replace `<environment>` in the file name with: `tcpci`, `tcpqa`, or `tcpprod`.

### Required Fields

**`templateFolder`** (string): Folder relative to the repo root containing the credential template files.

**`branches`** (string[]): Branches which this environment will consume the credential templates from.

---

<!-- SOURCE: identity/shared/credential-templates/schemas/credentialtemplate -->

## Credential Templates — Schema: `<filename>.clients.yaml`

Contains the configuration for a particular template.

**Example:**
```yaml
registrationId: registered tcp product
version: 2035.10.1-prerelease
clients:
  - name: FirstClient
```

Replace `<filename>` with whatever valid file name makes sense for your team.

### Required Fields

**`registrationId`** (string): Registration ID of the product this template is associated with. Product must be a registered product on the cloud platform.

**`version`** (string): The version of the template corresponding to the product.

**`clients`** (Client[]): List of clients to be produced when this template is applied.

### Client Fields

**`name`** (string, max 100 chars, no spaces): Human-readable name for the client. Always required.

**`clientType`** (string): Required if `remove` is `false`. Can be one of:
- `LoginPKCE` — Auth Code flow with PKCE
- `LoginACF` — Auth Code Flow (has client secret)
- `ServiceCCF` — Client Credential Flow (has client secret)

Implicit Flow credentials are NOT supported.

**`configStrategy`** (string, default `OnPrem`): Can be `TCP` or `OnPrem` (use `OnPrem`).

**`scopes`** (string[]): Required if `remove` is `false`. Defines which scopes are accessible to this credential.

**`redirectUris`** (string[], supports Handlebars): Required if `clientType` is `LoginPKCE` or `LoginACF`. Defines post-login redirect URLs.

**`postLogoutRedirectUris`** (string[], supports Handlebars): Required if `clientType` is `LoginPKCE` or `LoginACF`. Defines post-logout redirect URLs.

**`authorityOverride`** (string, default `None`): Can be `None` or `Gateway`. Meant to force a specific Authority to be returned instead of the current authority of the workspace.

### About Handlebars in Template

The `redirectUris` and `postLogoutRedirectUris` fields support Handlebars template system with mustache syntax. For example, `{{example}}/hello` transforms into `https://example.com/hello` when the variable `example=https://example.com` is passed into the apply request's variables dictionary.

If an item in either URI array doesn't resolve to a proper URI during the "apply" template call, or if all variable values aren't passed in, the call will error out.

---

<!-- SOURCE: identity/shared/events/overview -->

## Identity Events Overview

Events provide asynchronous integration with the SaaS control plane. This describes the events available for integration with **Tyler's Identity systems**.

### Use Cases

- Synchronize user data between the platform and other systems
- Trigger workflows based on user changes
- Update user data in downstream systems
- Sync user group data between the control plane and other systems

These use cases are part of the *Unified User* experience for *Cloud Living* and a *One Tyler* experience.

**Use Case 1:** When a new person is hired, subscribe to `workforce-user-created` to automate adding them to other systems.
**Use Case 2:** When a user is disabled, subscribe to `workforce-user-disabled` to trigger disable in other systems.
**Use Case 3:** When a user's profile changes (e.g., name change), subscribe to `workforce-user-profile-changed`.
**Use Case 4:** When a user is added/removed from a group, subscribe to `user-added-to-group` or `user-removed-from-group` to map group membership onto product roles.

**Note:** Workforce events are only published for Organizations that are using **Workforce Direct**.

### Event Types

| Event | Description | messageType |
| ------------ | ---------- | ------------ |
| Workforce User Created | New workforce user created via Admin Center or Ops Center | workforce-user-created |
| Workforce User Disabled | Workforce user is disabled in Admin Center | workforce-user-disabled |
| Workforce User Enabled | Workforce user is enabled in Admin Center | workforce-user-enabled |
| Workforce User Profile Changed | Workforce user attributes modified in backing IdP | workforce-user-profile-changed |
| Workforce User Deleted | Workforce user removed from Admin Center | workforce-user-deleted |
| Community Profile Email Changed | Email address of the community user has changed | community-profile-email-changed |
| Community Profile Deleted | Community user is removed from the platform | community-profile-deleted |
| User added to group | Workforce user added into a user group | user-added-to-group |
| User removed from group | Workforce user removed from a user group | user-removed-from-group |
| User group created | A new user group is created via Admin Center | user-group-created |
| User group deleted | A new user group is deleted via Admin Center | user-group-deleted |
| User group updated | An existing user group is updated via Admin Center | user-group-updated |

### Subscribing to Events

To start utilizing events, subscribe to the events you are interested in. You will need to obtain an identity client for the Gateway. Each environment will require a new client.

---

<!-- SOURCE: identity/shared/events/examples -->

## Identity Events — Example Payloads

### Workforce User Created
```json
{
  "messageType": "workforce-user-created",
  "sub": "5xieRMfpq3ha7Z8PjIoTD8tS",
  "organizationKey": "mycivicid",
  "username": "test.two@mycivicid.com",
  "givenName": "Test",
  "familyName": "Two",
  "email": "test.two@mycivicid.com"
}
```

### Workforce User Disabled
```json
{
  "messageType": "workforce-user-disabled",
  "sub": "5xieRMfpq3ha7Z8PjIoTD8tS",
  "organizationKey": "mycivicid",
  "username": "test.two@mycivicid.com",
  "givenName": "Test",
  "familyName": "Two",
  "email": "test.two@mycivicid.com"
}
```

### Workforce User Profile Changed
```json
{
  "messageType": "workforce-user-profile-changed",
  "sub": "5xieRMfpq3ha7Z8PjIoTD8tS",
  "organizationKey": "mycivicid",
  "username": "test.two@mycivicid.com",
  "givenName": "Test",
  "familyName": "Two New",
  "email": "test.twonew@mycivicid.com",
  "old_familyName": "Two"
}
```

### Workforce User Deleted
```json
{
  "messageType": "workforce-user-deleted",
  "sub": "CQMWoOQn9ToNIdXQAgFwEtqB",
  "organizationKey": "mycivicid",
  "username": "test.two@mycivicid.com",
  "givenName": "Test",
  "familyName": "Two",
  "email": "test.two@mycivicid.com"
}
```

### Community Profile Email Changed
```json
{
  "MessageType": "community-profile-email-changed",
  "Sub": "00ui8botttNriAzSl1d7",
  "ProfileId": "066fe167-e692-46f6-bbc7-3fc7fbc1e281",
  "PreviousEmailAddress": "test5555@mailinator.com",
  "NewEmailAddress": "test55555@mailinator.com"
}
```

### Community Profile Deleted
```json
{
  "MessageType": "community-profile-deleted",
  "Sub": "00ui8botttNriAzSl1d7",
  "ProfileId": "066fe167-e692-46f6-bbc7-3fc7fbc1e281",
  "EmailAddress": "test55555@mailinator.com"
}
```

### User Group Created
```json
{
  "organizationKey": "howardcountytx",
  "id": 24,
  "name": "Finance",
  "description": "Finance Directors",
  "messageType": "user-group-created"
}
```

### User Group Updated
```json
{
  "organizationKey": "howardcountytx",
  "id": 24,
  "name": "Finance Directors",
  "description": "Finance Directors group",
  "old_name": "Finance",
  "old_description": "Finance Directors",
  "messageType": "user-group-updated"
}
```

### User Added to Group
```json
{
  "organizationKey": "howardcountytx",
  "sub": "OtHJC47f3pN2x73rD92wYYMm",
  "groupId": 24,
  "groupName": "Finance",
  "username": "jsnhoward@outlook.com",
  "messageType": "user-added-to-group"
}
```

### User Removed from Group
```json
{
  "organizationKey": "howardcountytx",
  "sub": "OtHJC47f3pN2x73rD92wYYMm",
  "groupId": 24,
  "groupName": "Finance Directors",
  "username": "jsnhoward@outlook.com",
  "messageType": "user-removed-from-group"
}
```

---

<!-- SOURCE: identity/shared/miscellaneous/k8s-authn -->

## Kubernetes Authentication

Kubernetes has a built-in Authentication and Authorization system that can be used to authenticate calls between Kubernetes services in-cluster.

### Service Accounts

Service Accounts are the fundamental resource type that assigns an identity to a pod. Service account JWTs contain a `sub` claim formatted as `system:serviceaccount:<namespace>:<service_account_name>`.

### Tyler.Platform.TokenRequest Library

The `Tyler.Platform.TokenRequest` library contains a `K8sServiceAccountTokenRequester` that will:
- Pull the token via an Environment Variable or explicit token file location
- Manage rotation by caching the token in the runtime space

Use `K8sServiceAccountTokenRequestOptions.TryFromEnvironment("servicename", out var options)` to verify the client is running in Kubernetes. If all pre-requirements are met, use the `K8sServiceAccountTokenRequester` to obtain tokens. If not, fall back to the default CCF token requester.

### Trusting K8s Auth Tokens

The k8s API has implemented `.well-known/openid-configuration` and JWKS endpoints. You can use an existing library that authenticates JWT Bearer tokens. For the authority, in EKS, use the OIDC endpoint advertised. You'll also need to validate Audience and token expiration.

### Alternative: Token Review API

A separate method — the Token Review API — validates a Kubernetes Service Account Token (similar to OAuth introspection but not the same). Useful if you want to use the K8s RBAC system in your service for authorization.

### Benefits of Kubernetes Authentication

- Service account JWTs are automatically rotated and managed by Kubernetes
- You don't have to manage credentials for the service's identity
- Removes dependency on external identity system

### Downsides

- Any pod assigned to the service account assumes the identity of the service account — if you don't have controls over namespace/deployment permissions, a malicious actor can produce a malicious pod with that identity
- Service account tokens are scoped via the audience claim, not the scopes claim as expected from the OAuth spec

---

<!-- SOURCE: identity/shared/miscellaneous/filtered-user-audit-logs -->

## Filtered User Audit Logs for Cybersecurity Product

The Cybersecurity product requires access to Tyler Identity Workforce gateway user audit logs to fulfill active monitoring contracts for Madison City School District, AL and Huntsville City Schools, AL.

Gateway logs are filtered by these 2 tenants and copied into a dedicated S3 bucket: `arn:aws:s3:::tid-tcpprod-gateway-workforce-audit-user-filtered-us-east-1`. The Cybersecurity product is granted read-only cross-account access to this bucket. Only logs for licensed tenants are exposed.

**Read data only from tenant-specific prefixes:**
- `/madisoncsdal/`
- `/huntsvillecityschoolsal/`

**IAM Policy Required:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::tid-tcpprod-gateway-workforce-audit-user-filtered-us-east-1",
        "arn:aws:s3:::tid-tcpprod-gateway-workforce-audit-user-filtered-us-east-1/*"
      ]
    }
  ]
}
```

Provide the Tyler Identity team with the ARN for the IAM Role for cross-account access setup.

---

<!-- SOURCE: identity/shared/miscellaneous/ops-app -->

## Convert a Web Accelerator App to an Ops App

An **Ops App** is an application on the platform used only by Tyler employees to perform operational activities for one or more products, organizations, or workspaces.

**Quirks and features of an Ops App:**
- Only Tyler employees are allowed to login
- May be associated with either a product, an organization, or a workspace in Ops Center
- User access is generally controlled by Tyler Ops Users

### Application Changes

**1. Use Static Login Configuration:**

Change in `Startup.cs`:
```csharp
// Before:
services.AddTcpAuthentication(configuration);
services.AddTidIdentityConfigurationService(configuration);

// After:
services.AddTcpAuthentication(configuration);
services.AddAppSettingsLoginConfigStore(configuration);
```

**2. Update appsettings.json — Disable Centralized Callback Flow:**
```json
"oidcLogin": {
    "authority": "http://idp.localdev.tcpci.com:6300",
    "clientId": "armadillo-app",
    "useCentralizedCallbackFlow": false,
    "centralizedCallbackSubdomain": "sso"
}
```

**3. App Availability — Remove workspace-based availability check:**
Since Ops Apps don't function at the workspace level, replace the standard `IsAppAvailableAsync` call with `IsAppAvailable = true`.

### App Registration

Set the authentication model to external in your registration JSON:
```json
"authenticationModel": "ExternalWorkforce"
```

Include Ops Center link configurations so your Ops app can be discovered. An Ops app should utilize a static subdomain that is NOT `admin` (reserved for platform applications).

**Example registration:**
```json
{
  "registrationId": "ExternalOpsCenterLinkTestProduct",
  "apps": [
    {
      "title": "External-Ops-Center-Links",
      "authenticationModel": "ExternalWorkforce",
      "opsCenterProductConfigurations": [
        {
          "url": "https://eocl.tylerportico.com/myproduct/operations",
          "label": "My Product Ops"
        }
      ]
    }
  ]
}
```

### Obtaining Credentials

Submit a Service Desk ticket requesting new credentials. You will need one set for each TCP env.

- **Identity Client Type:** Authorization Code Flow with PKCE
- **Identity Provider:** Ops App IdP
- **Offline Access Required:** Allow
- **Sign-In Redirect URIs:** `https://admin.tylerportico.com/myproduct/operations/signin-callback-default-oidc`
- **Sign-Out Redirect URIs:** `https://admin.tylerportico.com/myproduct/operations/signout-callback-default-oidc`

---

<!-- SOURCE: identity/glossary/glossary -->

# 6. Glossary

**Access Token**: A JWT that represents the authorization to access protected resources. Issued by the Identity Gateway or Okta. Contains claims about the authenticated user and their permissions. Typically valid for 1 hour. Audience: `api://tylerapps` (Gateway) or `api://default` (Community).

**Admin Center**: Tyler's administrative portal for managing workspace and product settings, including configuring Identity Providers (IdPs) for workforce authentication.

**Attribute Mapping**: The process of mapping user attributes from a customer's IdP to claims in tokens issued by the Identity Gateway.

**Audience (aud)**: A JWT claim identifying the intended recipient.
- Gateway access tokens: `api://tylerapps` (static; disable strict validation)
- Community ID tokens: Your client ID
- Community access tokens: `api://default` (static)

**Authorization Code**: A temporary, one-time-use code returned after successful user authentication. Exchanges for tokens at the token endpoint. Codes expire after 5 minutes.

**Authorization Code Flow**: An OAuth 2.0 authentication flow where the application receives an authorization code after user authentication and exchanges it for tokens. Recommended for both server-side and client-side applications when combined with PKCE.

**Authorization Server**: For workforce applications, this is the Identity Gateway. For community applications, this is Tyler's managed Okta tenant.

**Branded Login**: A customized authentication experience displaying a customer's logo and colors on the login page. Community Access provides branded login pages using the `workspace` parameter.

**Bearer Token**: HTTP authentication where access tokens are sent in the `Authorization` header as `Bearer {token}`.

**CCF (Client Credentials Flow)**: An OAuth 2.0 grant type for service-to-service authentication where no user is involved. Applications use their client ID and secret to obtain an access token directly.

**Citizen**: A public user or resident accessing Tyler community applications. Citizens authenticate using Community Access (Okta).

**Claim**: A piece of information asserted about a user or client within a JWT. Common claims: `sub` (Subject/user ID), `preferred_username`, `organizationKey`, `iss` (Issuer), `exp` (Expiration).

**Client ID**: A public identifier for your application registered with the Identity Gateway or Okta.

**Client Secret**: A confidential value known only to your application and the authorization server. Never commit to source control.

**Code Challenge**: SHA256 hash of the `code_verifier`, sent in the authorization request as part of PKCE. Generation: `code_challenge = BASE64URL(SHA256(code_verifier))`.

**Code Verifier**: A cryptographically random string (43-128 characters) generated by the application as part of PKCE. Stored securely and sent during token exchange. Never send in the authorization request, only the `code_challenge`.

**Community Access**: Tyler's identity solution for citizen-facing applications. Uses a single Tyler-managed Okta tenant with branded login experiences and self-service registration. Use for public portals, citizen applications, resident services.

**Credential Template**: A declarative configuration that defines how Tyler products provision identity clients during deployment. Used for single-tenant or customer-specific deployments.

**CrmId**: A legacy claim name for the organization identifier, replaced by `organizationKey`. Both claims are currently included in Gateway tokens for backward compatibility.

**Discovery Endpoint**: A well-known URL providing metadata about an OIDC provider.
- Dev: `https://idgw.tcpci.com/tg/.well-known/openid-configuration`
- QA: `https://idgw.tcpqa.com/tg/.well-known/openid-configuration`
- Prod: `https://idgw.tylerportico.com/tg/.well-known/openid-configuration`

**Dual Trust**: An API security pattern allowing APIs to validate tokens from both the Identity Gateway and a legacy identity provider during a migration period.

**Dynamic Auth**: Tyler-provided .NET libraries simplifying authentication integration.
- **Community Dynamic Auth**: For Community Access (Okta) integration. Repository: `tidc-dynamic-auth`
- **TCP Dynamic Auth**: For Identity Workforce (Gateway) integration. Handles organization key routing.

**Entra ID**: Microsoft's cloud-based identity and access management service (formerly Azure AD). One of the most common customer IdPs federated with the Identity Gateway.

**Federation**: The process of connecting external Identity Providers to the Identity Gateway or Okta.

**FromURI Parameter**: Used in Community Access registration URLs to specify where to redirect after completing registration. Value must be URL-encoded. Important: users are NOT authenticated after registration and must go through the login flow.

**HttpOnly Cookie**: A browser cookie with `httpOnly` flag set, inaccessible to JavaScript. Recommended for storing tokens in server-side web applications.

**ID Token**: A JWT containing identity information about the authenticated user. Contains claims like name, email, and username. Typically valid for 5 minutes.

**Identity Gateway**: Tyler's central identity federation router and authorization server for workforce applications. Provides a single authority for all Tyler back-office and enterprise applications.
- Dev: `https://idgw.tcpci.com/tg`
- QA: `https://idgw.tcpqa.com/tg`
- Prod: `https://idgw.tylerportico.com/tg`

**Identity Provider (IdP)**: The authoritative source for user authentication. For workforce: customer's own IdP (Entra ID, Google Workspace, Ping Identity). For community: Tyler's managed Okta tenant.

**IdP Entity ID**: A globally unique identifier (URI) for a SAML Identity Provider.

**IdP Metadata**: An XML file or URL containing configuration information for a SAML IdP. Uploaded to Admin Center when configuring customer IdP connections.

**IdP Parameter**: Used in Community Access authorization requests to route users directly to a federated state or jurisdictional Identity Provider, bypassing the Okta login screen. Usage: `&idp=0oa1b2c3d4e5f6g7h8i9`. Obtain from Ops Center.

**Issuer (iss)**: A JWT claim identifying who issued the token. Token validation must verify the issuer matches the expected authority.

**JWKS (JSON Web Key Set)**: A set of public keys published by the authorization server at a well-known endpoint. Applications use JWKS to validate JWT token signatures.
- Gateway JWKS: `https://idgw.tylerportico.com/tg/.well-known/openid-configuration/jwks`

**JWT (JSON Web Token)**: A compact, URL-safe token format for access tokens and ID tokens. Structure: `header.payload.signature`.

**Nonce**: A random value included in the authorization request and verified in the ID token to prevent replay attacks.

**OAuth 2.0**: An authorization framework enabling applications to obtain limited access to user resources without exposing passwords.

**OIDC (OpenID Connect)**: An identity layer built on top of OAuth 2.0 that adds authentication and user identity features. Both Identity Workforce and Community Access use OIDC.

**Okta**: A cloud-based Identity-as-a-Service platform that powers Tyler's Community Access solution.

**Ops Center**: Tyler's operational portal for managing organizations, workspaces, products, and deployments. Developers use Ops Center to retrieve organization keys and workspace information.

**Organization**: A customer entity in the Tyler Cloud Platform, typically representing a government agency. Each organization has a unique `organizationKey`.

**OrganizationKey**: A unique identifier for a customer organization, required as a parameter in Gateway authorization requests to route users to their organization's Identity Provider. Replaces the legacy `crmId` parameter. Obtain from Ops Center.

**PKCE (Proof Key for Code Exchange)**: A security extension to the authorization code flow that protects against authorization code interception attacks. Required for public clients (SPAs, mobile apps); strongly recommended for all applications. How it works: Application generates random `code_verifier`, sends SHA256 hash as `code_challenge` in authorization request, then sends original verifier when exchanging code for tokens.

**Redirect URI**: The URL where users are sent after authentication. Must be pre-registered and must match exactly (protocol, domain, port, path). Must use HTTPS in production (localhost can use HTTP).

**Refresh Token**: A long-lived token used to obtain new access tokens without requiring the user to re-authenticate. Only issued when `offline_access` scope is requested. Typically valid for 90 days.

**SAML (Security Assertion Markup Language)**: An XML-based standard for exchanging authentication data. The Identity Gateway supports SAML 2.0 for federating with customer IdPs.

**Scope**: A mechanism in OAuth 2.0/OIDC to request specific permissions or user information. Required scopes for Gateway: `openid`, `profile`, `email`. The Gateway does NOT support a `groups` scope.

**Self-Service Registration**: A feature in Community Access that allows citizens to create their own accounts. URL Pattern: `https://{oktaDomain}/signin/register?fromURI={returnUri}`. After registration, users must go through the login flow to become authenticated.

**SessionStorage**: A browser storage mechanism that stores data for the duration of the browser session (cleared when tab closes). Recommended for storing tokens in SPAs.

**Signin Parameter**: Used when linking between Tyler Community Access applications. `signin=true` causes the receiving application to prompt for sign-in if user is not authenticated.

**Silent Token Renewal**: A technique for refreshing tokens in SPAs without disrupting the user experience. Uses a hidden iframe with `prompt=none`.

**Single Sign-On (SSO)**: An authentication method that allows users to authenticate once and access multiple applications without re-entering credentials.

**State Parameter**: A random value included in authorization requests and verified in the callback to prevent CSRF attacks.

**Subject (sub)**: A JWT claim containing a unique identifier for the authenticated user. Stable across sessions.

**TCP (Tyler Cloud Platform)**: Tyler's unified cloud ecosystem and control plane for managing organizations, products, workspaces, and shared services.

**Token Validation**: The process of verifying a JWT's authenticity and claims. Check: signature (via JWKS), issuer, expiration, audience.

**Webhook**: An HTTP callback used to receive event notifications from the Tyler Cloud Platform. Subscribe to identity events to synchronize user data.

**Workforce Direct**: Customer-facing terminology for Tyler's workforce identity solution powered by the Identity Gateway. Used in sales and support contexts.

**Workspace**: A logical grouping within a Tyler organization containing products, users, and configuration. Workspaces represent deployments or environments for a customer's Tyler applications.

**Workspace Parameter**: Used in Community Access authorization requests to provide a branded login experience for a specific jurisdiction. Usage: `&workspace=cityofseattle`. Effect: Displays custom logo, colors, and branding for the specified jurisdiction.

**WorkspaceId Claim**: A claim included in Community Access ID tokens identifying the jurisdiction or workspace for the authenticated user. Example: `"workspaceId": "cityoftyler"`. Included in ID tokens, not access tokens.

---

<!-- SOURCE: identity/support -->

# 7. Support

There are 2 avenues for obtaining support related to Tyler Identity:

## Help Desk Requests

The most common and effective means is using the Tyler Cloud Platform (TCP) service desk: https://help.center.tylertech.com/servicedesk/customer/portal/3168

Common requests include:
- Requesting a Client Credentials Flow (CCF) client and secret for service-to-service authentication
- Requesting a Web or Mobile Client for login authentication
- Requesting the creation of a new organization for a customer
- Requesting assistance with authentication issues
- Requesting assistance with integration issues
- Requesting the creation of a new federation between the Gateway and an external IDP

## Teams Channels

All channels are located under the **Corpdev Collaboration** team.

**Cloud Platform Community**: Channel for discussions or help on anything related to the cloud ecosystem.

**Identity Workforce**: Channel utilized for questions or assistance with integration, status, or issues.

**Identity Community**: General Identity channel for questions about the Community Access identity solution.

**TID Announcements**: Centralized channel for general announcements, such as policy changes, infrastructure modifications, or planned outages.
