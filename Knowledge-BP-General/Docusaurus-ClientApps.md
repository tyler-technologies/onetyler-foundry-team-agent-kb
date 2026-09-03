# Client Applications — Admin Center, App Directory, Profiles, and Community Services Directory

**Source:** Docusaurus — Tyler Blueprint (`docs.tylerdev.io`), paths:
`app-guides/client/`, `app-guides/client/admin-center/`, `app-guides/client/csd/`

**Domain:** Blueprint General — Tyler Cloud Platform / Blueprint docs not served by a specialized Foundry agent.

**Audience:** Tyler implementation staff, Tyler support staff, and customer IT/admin personnel (Org Admins, Identity Admins, User Admins) who configure and manage Tyler cloud solutions. The Tyler-internal sections (get-started, sandbox-tenants) are for Tyler product engineers and QA staff integrating with Admin Center.

**Companion documents:**
- `_START_HERE.md` — routing guide for the full BP-General corpus
- `Docusaurus-PlatformOverview.md` — platform concepts (orgs, workspaces, products, identity tiers)
- `Docusaurus-OpsApps.md` — Ops-side applications (Audit Center, Authorization Config, Ops Center pointer)
- `Docusaurus-ProductSystemReg.md` — product/app registration mechanics
- `Docusaurus-Security.md` — security architecture and data handling
- **Identity agent** — for deep questions about Identity Workforce, Identity Community, Gateway, or credential templates: https://docs.tylerdev.io/identity
- **Ops Center agent** — for provisioning, org/workspace lifecycle, implementation tasks: https://docs.tylerdev.io/app-guides/ops/ops-center/overview/

---

## How to use this guide (quick decision guide)

| User intent | Go to section |
|---|---|
| How does a customer sign in to Admin Center? | [Signing in to Admin Center](#signing-in-to-admin-center) |
| How do I give a user access to Admin Center? | [Roles: granting Admin Center access](#roles-granting-admin-center-access) |
| How do I give a user access to a workspace application? | [Access control lists: granting application access](#access-control-lists-granting-application-access) |
| How do I set up federation (Entra ID, ADFS, Okta, Google)? | [Identity Workforce configuration](#identity-workforce-configuration) |
| How do I add or import users? | [Users: adding and managing workforce users](#users-adding-and-managing-workforce-users) |
| How do I control whether Tyler staff can access our Admin Center? | [Tyler support access setting](#tyler-support-access-setting) |
| What are the Admin Center pages / features? | [Admin Center feature reference](#admin-center-feature-reference) |
| What is App Directory? | [App Directory](#app-directory) |
| What is Community Access Profile Manager (CAPM)? | [Community Access Profile Manager (CAPM)](#community-access-profile-manager-capm) |
| What is Community Launcher? | [Community Launcher](#community-launcher) |
| What is Community Profile / Workforce Profile? | [Community Profile and Workforce Profile](#community-profile-and-workforce-profile) |
| How do I set up or use Community Services Directory (CSD)? | [Community Services Directory (CSD)](#community-services-directory-csd) |
| Sandbox/test Admin Centers for Tyler engineers | [Tyler-internal: sandbox tenants](#tyler-internal-sandbox-tenants) |
| How to integrate a new product with Admin Center | [Tyler-internal: integrating with Admin Center](#tyler-internal-integrating-with-admin-center) |

---

## Glossary

| Term | Meaning |
|---|---|
| Admin Center | The customer-facing IT/admin application for Tyler cloud solutions. URL pattern: `https://<orgKey>-admin.tylerportico.com/org/admin-center/` |
| Org Admin | Organization Admin — the Admin Center role with full permissions |
| Identity Admin | Admin Center role limited to identity-related features |
| User Admin | Admin Center role limited to managing users and user groups |
| Workspace | A cloud environment for Tyler solutions (Production or NonProduction). Provisioned by Tyler. |
| ACL | Access Control List — a named list of users + applications in a Workspace that controls who can access what |
| Identity Workforce | Tyler's cloud authentication solution for workforce (employee-type) users |
| Identity Workforce Managed | Identity tier that includes a Tyler-managed Okta tenant |
| Identity Workforce Direct | Identity tier with no Tyler-managed Okta tenant; customer supplies their own IDP |
| IDP / Identity Provider | External authentication system (ADFS, Entra ID/Azure AD, Google Cloud Identity, Okta) |
| AD Agent | Active Directory synchronization agent |
| Federated user | User authenticated through an external IDP federation |
| Local user | User authenticated through a Tyler-managed Okta tenant (credentials stored there) |
| CAPM | Community Access Profile Manager — tool to find/support Identity Community accounts |
| CSD | Community Services Directory — public-facing directory of government/municipal services |
| MFA | Multi-factor authentication |
| VTL | Velocity Templating Language — used in Okta email templates |
| App Directory | Application showing a user the apps they can access |

---

## Signing in to Admin Center

**Use when:** A customer or Tyler staff cannot find or access their Admin Center.

**Admin Center URL pattern:**
```
https://<your-customer-identifier>-admin.tylerportico.com/org/admin-center/dashboard
```
or equivalently:
```
https://<your-customer-identifier>-admin.tylerportico.com/org/admin-center/
```

Replace `<your-customer-identifier>` with the organization key. The URL is also included in the "Welcome to the Admin Center" email sent to Org Admins (from `tylerportico.com`).

**Live doc:** https://docs.tylerdev.io/your-admin-center

**First-time access:** Tyler implementers provide initial access. A "Welcome to Admin Center" email contains the username and Admin Center URL.

**Username vs. email:** The username used to sign in is stated in the invitation email. Username and email are separate fields and can differ. Use the username from the email, not the email address itself.

**Password:**
- If you received a separate "Welcome to Okta!" email from `noreply@okta.com`, follow that to set your Okta account password.
- Otherwise, use your usual workplace credentials.

**Allow email domains:** For enterprise spam filtering, allow `okta.com` and `tylerportico.com` — these domains send necessary administrative emails.

**Contact for access issues:** Contact your Tyler implementation or support representative.

---

## Roles: granting Admin Center access

**Prerequisites:** You must be an Org Admin to assign roles. The person must have a user profile in Users.

**Admin Center roles:**

| Role | Permissions |
|---|---|
| Organization Admin (Org Admin) | Full permissions across all Admin Center features |
| Identity Admin | Identity-related features only (Identity Workforce, Domains, Identity Providers) |
| User Admin | Manage users and user groups only |

**To grant access:**
1. Confirm the person has a Workforce user profile in **Users** (add if missing).
2. Go to **Admin Center > Roles**.
3. Assign the person to the appropriate role.
4. Status shows `pending` while the authorization system updates — this can take several minutes. The user has no role access during this period.
5. Status changes to `active` when updated.

**Removing a role:** Role removal also takes several minutes. The user retains permissions of the removed role until the process completes. A dialog confirms completion.

**Access control lists do NOT control access to Admin Center** — ACLs govern access to workspace applications, not to Admin Center itself.

---

## Access control lists: granting application access

**Source:** https://docs.tylerdev.io/app-guides/client/admin-center/authorization

An **access control list (ACL)** is a named list of users + applications within a Workspace. Users in an ACL can access the applications in that ACL. ACLs grant baseline access — not fine-grained permissions. Applications manage their own internal authorization.

**Three conditions for a user to access a workspace application:**
1. The user must be able to authenticate (valid credentials in an IDP associated with your org — see Identity Workforce section).
2. The application must be available in the Workspace (not unavailable — contact Tyler support to change status).
3. The user must be in an ACL that contains that application on that Workspace.

**Note:** Not all applications require ACLs. Only products that use the ACL model require this step. These applications are listed in **Workspace > Apps** tab.

### Creating an ACL

1. Go to **Admin Center > Access Control** or **Workspaces > [Workspace] > Access Control**.
2. Click "Create a new access control list".
3. Enter a name and description.
4. Select one or more Workspaces. Selecting multiple Workspaces creates independent ACLs in each — they share initial name/users/apps but are not linked after creation.
5. Select zero or more applications (filterable by name or product). Applications shown are those available on the selected Workspace(s).
6. Select zero or more users. Users must already exist in **Users**; add them there first if missing.
7. Review (shows activation status of each app per Workspace) and Save.

### Modifying an ACL

- Select an ACL in **Access Control** or **Workspace > Access control lists** tab; use the detail pane to add/remove users or applications.
- Modifying one ACL never affects any other ACL, even if they share a name.

### Org Admins and ACLs

Org Admins are not automatically in ACLs — they must be added to an ACL containing the applications they need. This includes seeing applications in **Admin Apps**.

---

## Identity Workforce configuration

**Source:** https://docs.tylerdev.io/app-guides/client/admin-center/authentication

**Hand-off note:** This section covers the Admin Center UI for configuring Identity Workforce. For deep identity protocol questions, credential templates, or the Identity product itself, hand off to the Identity agent: https://docs.tylerdev.io/identity

### Identity tier types

| Type | Behavior |
|---|---|
| Workforce Managed | Has a Tyler-managed Okta tenant. No initial setup needed to authenticate, but federation/AD sync can be added. |
| Workforce Direct | No Tyler-managed Okta tenant. Must establish a federation to an IDP before users can sign in. |
| Delegated | Another organization's IT group manages the IDP setup. The delegated org cannot modify its own identity providers. |

### How username domains determine the IDP

The domain portion of the username (the part after `@`) determines which IDP is used:
- Domain is associated with a federated IDP → that IDP authenticates the user.
- Domain is associated with an AD Agent sync → AD authenticates the user.
- Domain has no IDP association → Tyler-managed Okta tenant authenticates the user (local user).

**You must list username domains** in **Identity Workforce > Domains** for any users to authenticate. Domains associated with federated IDPs must be linked to that IDP.

### Adding username domains

1. Go to **Identity Workforce > Domains**.
2. Enter the domain without `@` (e.g., `example.com`, not `@example.com`) and press Enter.

### Adding an identity provider federation

**Prerequisites:** Gather required credentials from your IDP first (see IDP-specific info below).

Steps:
1. Go to **Identity Workforce > Identity Providers**.
2. Click "Add a new provider".
3. Select the IDP type.
4. Follow the 3-step flow:
   - **Configure:** Enter IDP credentials. The IDP appears "inactive" until domains are added.
   - **Test (optional):** Opens a sign-in screen for that IDP to verify credentials work.
   - **Domains:** Associate one or more domains. Domains labeled "in use" are already associated with another IDP — you can move them.

### IDP-specific credential requirements

**ADFS:**
- Token-signing certificate
- Metadata URL path (usually `https://<FQDN>/FederationMetadata/2007-06/FederationMetadata.xml`)
- From Admin Center: retrieve the TID-W metadata file to complete setup in ADFS (add Relying Party Trust, Access Control Policy, Claims Issuance Policy with LDAP attributes)

**Entra ID (Azure AD):**
- Client ID (Application ID) — from an App Registration in Entra ID
- Client Secret Value (not the Secret ID)
- Secret expiration date (set as long as possible)
- Tenant ID (Directory ID)

**Google Cloud Identity:**
- Client ID
- Client Secret
- (Requires an OAuth Consent screen and OAuth Client ID Credentials in Google)

**Okta:**
- Client ID
- Client Secret
- Base URL for your Okta tenant
- (Requires an App Integration with OIDC sign-in method and Web Application type)

### Federation expiration

If a federation has an expiration date, enter it in the configuration. Tyler sends Org Admins an email warning **30 days before expiration**. An expired federation prevents users from signing in.

### Editing or deleting a federation

**Edit:** Go to **Identity Workforce > Identity Providers**, click the chevron icon on the IDP row, then Edit. Save when done.

**Delete (irreversible):** Must remove all associated domains first. Ensure an alternative IDP is configured for affected users. Then click "Delete this idp federation". This can significantly disrupt user access.

### AD Agent integration

AD Agent sync requires Tyler support to set up initially. Once set up, the AD Agent service account and pool(s) are visible. Use the AD Agent service account to access the Okta Admin Console. Reset Password generates a temporary password for the service account. An email address can be added to the service account for AD integration notifications.

### Session management (Workforce Managed only)

Configures session limits for your Tyler-managed Okta tenant — separate from IDP session limits and application session limits.

- **Maximum Session Lifetime:** Absolute maximum time before re-authentication required.
- **Idle Session Lifetime:** Time before session expires due to inactivity.

### Password policy (Workforce Managed / local users only)

Applies only to accounts stored in the Tyler-managed Okta tenant. Federated user passwords are governed by their IDP.

### Networking (Workforce Managed)

- **Proxy:** If using an outbound proxy, configure the IP/CIDR so Identity Workforce processes traffic headers correctly.
- **Allow list:** Check the allow-listing box to alert the Identity support contact of future Okta IP allow-list updates.
- **Threat Insight:** Configure your outbound gateway IP/CIDR so Okta Threat Insight does not flag it. Threat Insight blocks credential-based attacks (password spraying, credential stuffing, brute-force).

### Multifactor authentication (Workforce Managed)

Configures MFA for your Tyler-managed Okta tenant — separate from any MFA in a federated IDP. Both can operate simultaneously. Contact your Tyler sales team to activate MFA if not currently enabled.

### Email templates (Workforce Managed, optional feature)

Customizable HTML email templates using Velocity Templating Language (VTL). Available templates: User activation, Forgot password, Forgot password denied, Password reset by admin, AD/LDAP user activation, AD/LDAP forgot password, AD/LDAP forgot password denied. Contact Tyler sales to activate this feature. Reference: https://developer.okta.com/docs/guides/custom-email/main/#use-customizable-email-templates

### Identity Workforce history log (Workforce Managed)

Logged event types visible under **Identity Workforce > History**:
AD Agent Account Reset/Created, Allowed List Updated, Federation Added/Deleted/Domain Updated/Updated, Password Policy Updated, Proxy Updated, Session Updated, Threat Insight Updated, Tier Changed.

---

## Users: adding and managing workforce users

**Source:** https://docs.tylerdev.io/app-guides/client/admin-center/users

**Admin Center > Users** lists Workforce users (not Community/public-facing application users).

**User record fields:** username (email-format, e.g. `jay.mac@example.com`), email (can be the same or different from username), first name, last name, phone (optional).

**User types:**
- **Local:** Credentials stored in the Tyler-managed Okta tenant. Created via Add/Import in Users. User receives Okta activation email to set password.
- **Federated:** Credentials in an external IDP. Admin Center cannot reset their passwords — do that in the IDP.

**Prerequisites before adding users:** The username's domain must be listed in **Identity Workforce > Domains**.

### Adding a single user

1. Click "Add user" (top right of Users page).
2. Enter First name, Last name, Username, Email. Username domain must already be in Identity Workforce > Domains.
3. Optionally enter Phone. Click Next.
4. Optionally assign to existing ACLs. Click Next.
5. Review, then "Save & close".

Local users receive emails from Okta to activate and set up their account password and MFA.

### Adding multiple users (import)

CSV format: `firstname,lastname,email` — no header row, no spaces between values, one user per line. Encapsulate in double quotes to handle special characters.

1. Click "Import users".
2. Select or drag-drop the CSV file.
3. Click Import.
4. Users added in background. View status via 3-dot menu > Import history.
5. After import, separately assign imported users to ACLs.

### User actions

Select a user (click chevron) to reach the detail page. Available actions via "User Actions" button:
- Resend activation email
- Send password reset email
- Deactivate or suspend user
- Delete (previously deactivated users only) or reactivate

Available actions vary by user status and type (local vs. federated).

### Viewing user authentication activity

Select a user → "View identity activity" in the User Actions dropdown. Shows Okta system log events for that user.

### Note: Community users are not in Users

Community (public-facing) application users authenticate through Identity Community and are managed separately — not in Admin Center > Users. Use Community Access Profile Manager (CAPM) for Community user support.

---

## Tyler support access setting

**Source:** https://docs.tylerdev.io/app-guides/client/admin-center/support

Default: **Full** — Tyler staff can access your Admin Center via an internal tool without your involvement.

Changed to **Limited**: Tyler staff cannot use the internal tool to access your Admin Center. Only current Org Admins (including Tyler Org Admins) can grant additional access by assigning the Org Admin role.

**To fully block Tyler access:**
1. Change Tyler's access setting to "Limited".
2. Remove the Org Admin role from any Tyler employees listed in **Admin Center > Roles**.

**Important:** Do NOT delete Tyler employees' Workforce user profiles — that removes their access to other Tyler solutions where you may need them (support, implementation, etc.).

This setting is visible on the Admin Center dashboard. Only client Org Admins (not Tyler employees) can change it.

---

## Admin Center feature reference

**Source:** https://docs.tylerdev.io/app-guides/client/admin-center/overview/overview

Full URL for Admin Center app-guides: https://docs.tylerdev.io/app-guides/client/admin-center/

| Feature / Page | Purpose |
|---|---|
| **Dashboard** | Landing page showing: Tyler access setting, org record name, contacts, and workspace list |
| **Users** | Manage Workforce user profiles; add, import, deactivate, reset passwords for local users |
| **Roles** | Assign/unassign Org Admin, Identity Admin, User Admin roles |
| **Access Control** | Create and manage ACLs across all workspaces; filter by workspace, app, or user |
| **Workspaces** | View and configure workspaces; manage ACLs, apps, links, contacts, non-prod banners |
| **Products** | View licensed Tyler products registered with Admin Center; see application types |
| **Admin Apps** | Access (and copy URLs to) administrative applications for products; requires ACL membership |
| **Sign-in Logs** | Authentication events logged by Identity Workforce (actor, event, time, result) |
| **Settings** | Org contacts, branding (logo, banner, colors), links for community app footers, allowed domains |
| **Identity Workforce** | Configure IDP federations, AD Agent, password policy, session, networking, MFA, email templates |

### Products page

Lists products licensed to your org that are fully integrated with Admin Center. Each product shows applications by type:
- **Admin:** Administrative configuration app
- **Workforce:** For internal (authenticated) users
- **Community:** For public/constituent users

Live doc: https://docs.tylerdev.io/app-guides/client/admin-center/products

### Workspaces

Workspaces are provisioned by Tyler — customers cannot create new ones through Admin Center.

**How a workspace actually gets created:** Tyler staff create it in **Ops Center** (organization details → **Manage workspaces** → **+ Add a workspace**), or it is created through **Ops Center APIs** called by a deployment tool such as **Tyler Deploy** or **Cloud Provisioner**. A customer who needs a new workspace, or finds one missing, asks Tyler — they have no Admin Center path to it. Do **not** answer "contact Tyler Support" as though no mechanism existed; name the mechanism.

**What Admin Center can and cannot do here.** Admin Center is where a customer **views** workspace details and edits presentation-level settings (title, links, contacts, banner, ACLs). It **cannot create a workspace, and cannot change licensing or product availability** — both of those are Ops Center, and therefore Tyler staff. Ops Center is the tool for creating organizations and workspaces, licensing products to an organization, and activating them on a workspace.

**Workspace > Overview:** Shows type (production/non-production), status (enabled/disabled). Workspace ID, title (controls Community App Directory banner text and nav rail), and a "Danger Zone: Disable Workspace" section. Disabling a workspace affects all applications within it — contact Tyler Support first.

**Workspace > Access control lists:** Create/manage ACLs on that workspace. Creating one ACL across multiple workspaces creates independent copies.

**Workspace > Apps:** Lists apps that require ACL-based access (apps that need ACLs for access AND are from products registered with Admin Center).

**Workspace > Links:** Override org-level link text/URLs for community-facing application footers.

**Workspace > Contacts:** Override org-level Business and Technical contact defaults.

**NonProduction Workspace > Banner:** Set a banner (text + color scheme) visible in participating apps (App Directory, CSD) to distinguish non-prod from prod. Disabled by default.

### Settings page

- **Contacts:** Add org-level contacts. Contacts must have a Workforce user profile in Users. Can use email aliases.
- **Branding:** Upload Logo and Banner image; set login page theme colors for Identity Workforce. Logo used in both Workforce and Community Identity login pages.
- **Links:** Set links that appear in community-facing application footers.
- **Domains:** Specify allowed username domains (e.g. `example-county.com`). Only usernames with these domains can be added in Admin Center.

---

## App Directory

**Source:** https://docs.tylerdev.io/app-guides/client/app-directory

App Directory shows a user the applications they can access. It does not show all applications — only those from Tyler products that have integrated with App Directory.

- **Workforce App Directory:** Shows workforce applications accessible to the authenticated user (based on ACL membership and authenticated access).
- **Community App Directory:** Starting page for community-facing applications available to public users. Accessible from a workspace's Overview links.

Note: Some applications (e.g. Employee Access) do not appear in App Directory until the user has a Workforce profile in Admin Center > Users. Users can still access those apps directly by URL, but not through App Directory, until a profile exists.

---

## Community Access Profile Manager (CAPM)

**Source:** https://docs.tylerdev.io/app-guides/client/capm

Community Access Manager (CAPM) is a client-facing application that allows authorized Tyler customers to find and look up a public user's **Identity Community** account.

Use when: A community (public) user needs support with their Identity Community account and a customer IT admin needs to locate that account.

Note: CAPM is separate from Admin Center. It addresses Identity Community users, not Workforce users. For deep Identity Community questions, see the Identity agent: https://docs.tylerdev.io/identity

---

## Community Launcher

**Source:** https://docs.tylerdev.io/app-guides/client/community-launcher

Community Launcher is a client application in the Tyler platform's client app family. (Source file is a stub — detailed content not yet published in Blueprint docs.)

---

## Community Profile and Workforce Profile

**Sources:**
- https://docs.tylerdev.io/app-guides/client/community-profile
- https://docs.tylerdev.io/app-guides/client/workforce-profile

**Workforce Profile:** The profile application for workforce (internal/employee) users showing a workforce user basic information about themselves.

**Community Profile:** The profile application for community (public-facing) users.

Both are client applications in the Tyler platform's app family. Detailed content beyond these descriptions is not yet fully published in Blueprint docs.

For community and workforce user identity-related questions, see the Tyler Community group: https://tylercommunity.tylertech.com/admin-center-identity/

---

## Community Services Directory (CSD)

**Sources:**
- Admin app: https://docs.tylerdev.io/app-guides/client/csd/admin
- Configuration app (Services Manager): https://docs.tylerdev.io/app-guides/client/csd/services-manager
- Services Directory (public-facing): https://docs.tylerdev.io/app-guides/client/csd/services-directory

CSD is a suite of three applications for managing and displaying a public directory of government/municipal services.

### CSD application overview

| App | Audience | Purpose |
|---|---|---|
| CSD Admin app | Org Admins + users with Community Services Admin role | Set up authorization, manage roles/groups, manage departments |
| CSD Configuration app (Services Manager) | Authorized staff (Contributor+) | Create and publish service listings |
| CSD Services Directory | Public/community users | Browse and search published services |

### CSD Admin app

**Access:** Organization Admins (implicit full Admin role) + users in user groups assigned a CSD role.

**Authorization model:** User Groups (managed in Admin Center) + Roles. Assign CSD roles to User Groups. Users in those groups inherit the role permissions.

**CSD Roles:**

| Role | Capability |
|---|---|
| Admin | Full admin including configuring authorization |
| Contributor | Create and edit service entries |
| Publisher | Publish service entries to the public directory |
| Viewer | View service library; cannot publish |

**Assign Groups:** Use "Assign Groups" dialog to assign unassigned User Groups (from Admin Center) to one or more CSD roles.

**Departments:** Used for search categorization. A default list is provided on provisioning. Add, edit, or remove departments from the Admin app. A department assigned to a service cannot be removed.

### CSD Configuration app (Services Manager)

**Use when:** You need to add, edit, or publish services in the Community Services Directory.

**Prerequisites:** Contributor, Publisher, or Admin role in CSD; access to the Configuration app via Admin Center ACL.

**Service Library:** Centralized list of all services (Tyler-provided and custom). From here you can:
- Add a custom service entry
- Import a Tyler application's service (uses that product's default title, description, icon, and URL)
- Publish or feature a service
- Filter by Featured / Published / Unpublished

**Service entry attributes:**

| Attribute | Notes |
|---|---|
| Title | Required. Editable for all service types. |
| Description | Required. Editable for all service types. |
| Icon | Required. Editable for all service types. |
| Department | One department per service. Appears as a badge in the directory. |
| Functions | Zero or more. Predefined: Appointment, Bill/Invoice, Fee, Fine, Form, License, Other, Permit, Rental, Subscription, Tax. Used for filtering. |
| Tags | Zero or more keywords. Used for search matching (e.g., tag "pets" matches search for "pets"). Not shared across listings. |
| URL | Editable for custom services. **Not editable for Tyler services** — Tyler controls the URL. |
| Published | Makes the service visible in the public directory. |
| Featured | Makes the service appear on the main/landing page of the directory as a featured card. |
| Send to Sign In | Appends `signin=true` to the URL. The target application must implement this behavior to send the user to sign-in. |

**Accessing the Community Services Directory URL:**
```
https://<CLIENT_IDENTIFIER>.tylerportico.com/community-service-directory/directory/featured-services
```

Also accessible via: Services Manager > Service Library > "View Service Directory" button, or via Admin Center > Products > Community Services Directory > App Links.

### CSD Services Directory (public-facing)

Two main pages:
- **Featured Services:** Highlights selected published services as cards. Includes a search box for all published services.
- **Directory Search (All Services):** All published services, searchable and filterable by function.

Clicking a card navigates to the service's URL.

---

## Tyler-internal: integrating with Admin Center

**Source:** https://docs.tylerdev.io/app-guides/client/admin-center/tyler-internal/get-started

**Audience:** Tyler product engineers integrating a product or feature with Admin Center.

Integrating with Admin Center means connecting with Admin Center's platform services so that administrative actions in Admin Center have the expected effects across the customer's Tyler solutions. Example: an Admin Center approval of a Tyler employee support request results in that employee getting appropriate access in the relevant solution.

For full integration guidance, see the Blueprint docs at the source URL above.

---

## Tyler-internal: sandbox tenants

**Source:** https://docs.tylerdev.io/app-guides/client/admin-center/tyler-internal/sandbox-tenants

**Audience:** Tyler engineers and QA staff who need test Admin Centers.

**Workforce Direct sandbox:** Provision via Ops Center in CI, QA, or prod environments.

**Workforce Managed sandboxes (limited availability — Okta tenant cost):**

| Environment | Org key | Admin Center URL | Ops Center link |
|---|---|---|---|
| CI | `demo` | https://demo-admin.tcpci.com/org/admin-center | https://admin.tcpci.com/portal/ops-center/manage-organizations/demo/details |
| QA | `demo` | https://demo-admin.tcpqa.com/org/admin-center | https://admin.tcpqa.com/portal/ops-center/manage-organizations/demo/details |
| Prod | `demo` | https://demo-admin.tylerportico.com/org/admin-center | https://admin.tylerportico.com/portal/ops-center/manage-organizations/demo/details |

---

## Getting support

- **Tyler support:** https://www.tylertech.com/client-support — select the relevant Tyler product.
- **Community group (Admin Center & Identity):** https://tylercommunity.tylertech.com/admin-center-identity/ — forums, blogs, video guides. Also covers Workforce Profile, Identity Community Profile, and CAPM.
- **Okta system log event types:** https://developer.okta.com/docs/reference/api/event-types/

---

## Notes for the chatbot

1. **Audience split:** Admin Center is a customer-facing app. The Tyler-internal sections (sandbox tenants, get-started) are for Tyler engineers — distinguish when routing.

2. **Identity hand-off:** This file covers Admin Center UI for Identity Workforce configuration (adding domains, setting up IDP federations, AD Agent status). For questions about Identity protocols, credential templates, Gateway, or Identity Community, hand off to the Identity agent: https://docs.tylerdev.io/identity

3. **Ops Center hand-off:** Workspace provisioning, org creation, and implementation workflows are in Ops Center, not Admin Center. Hand off to Ops Center agent: https://docs.tylerdev.io/app-guides/ops/ops-center/overview/

4. **ACLs vs. Roles:** These are distinct concepts. Roles (Org Admin, Identity Admin, User Admin) control access to Admin Center itself. ACLs control access to workspace applications. Do not conflate them.

5. **ACL independence:** ACLs created across multiple workspaces in a single flow are independent after creation. Modifying one does not affect others.

6. **Community users not in Users:** Admin Center > Users only shows Workforce users. Community (public) users are managed separately; direct community user support queries to CAPM or the Identity agent.

7. **Workspaces are Tyler-provisioned:** Customers cannot create workspaces from Admin Center. Creation happens in **Ops Center** (**Manage workspaces** → **+ Add a workspace**) or through **Ops Center APIs** driven by a deployment tool (**Tyler Deploy**, **Cloud Provisioner**). Name that mechanism rather than answering only "contact Tyler Support". (Repeated from the Workspaces section on purpose — retrieval returns whichever chunk matches the question.)

8. **Products page vs. Admin Apps page:** Products shows licensed products and their app links. Admin Apps shows only apps the signed-in user can access via ACLs — an empty Admin Apps page means the user has no ACL with admin apps.

9. **CSD roles use Admin Center User Groups:** CSD authorization depends on User Groups that live in Admin Center. Changes to User Groups must happen in Admin Center, not within CSD itself.

10. **What this file does NOT cover:** Deep Identity Workforce protocols, Ops Center workflows, Support Access Center (SAC), product-specific authorization (each product manages its own), billing/licensing, workspace provisioning. For Ops Center: https://docs.tylerdev.io/app-guides/ops/ops-center/overview/ | For SAC: https://docs.tylerdev.io/ops/support-access-center/
