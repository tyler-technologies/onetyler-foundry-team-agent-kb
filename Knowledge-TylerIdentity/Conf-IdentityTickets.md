# Identity — CorpDev Ticket Reference

Source: Tyler CorpDev Support portal — *Tyler Identity Cloud* group
(https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3329), harvested
from the live JSM forms 2026-08-23, cross-checked against Confluence
*Tyler Cloud Platform (TCP) | Ops Center Related Tickets and Permissions*
(https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386600308).

Domain: Tyler Identity
Audience: Tyler staff who need to file an Identity-related request against CorpDev.

**⚠ NOT YET DEPLOYED.** This file exists in the repo only. It has deliberately **not** been
uploaded to the `TCP-KB-Identity` Foundry collection, because that collection's on-disk
structure differs from the repo's and the switchover needs agreement with the corpus owner.
See Hard Rule 1 in `CLAUDE.md`.

**⚠ DERIVED FILE — do not edit directly.** This is an identity-scoped extract of
`Knowledge-Shared/Conf-CorpDevTickets.md`, kept separate only because the Identity corpus is
a single monolithic document whose owner may prefer a small identity-only addition to the
whole cross-domain catalog. When the shared catalog changes, re-derive this file from it.

**Companion:** the authoritative full ticket catalog — covering Ops Center, Support Access
Center, infrastructure and general-inquiry tickets as well as these — is
`Knowledge-Shared/Conf-CorpDevTickets.md`. The team router also sends *all* "which ticket do
I file" questions to the Ops Center agent, which holds a copy. This file exists so the Identity
agent can answer identity-ticket questions directly without a hand-off.

---

## Quick lookup

| If the user needs to… | Ticket |
|---|---|
| Federate a client's IdP (or it won't work in Admin Center) | `4128` Federate Identity Provider |
| Report a login / email-verification failure | `4138` Authentication Issues |
| Change a customer's Identity Workforce SKU | `4149` Identity SKU Change |
| Get access to a TID Okta tenant | `4152` Okta Access Request |
| Add / modify / inspect an OAuth client | `4153` Identity Client |
| Get a non-standard custom IdP vetted | `4159` Custom IdP Investigation |
| Request a new Okta tenant | ❌ superseded — use Org Creation `3333/create/4158` |
| Get permission to manage federations *inside Ops Center* | ❌ not here — Ops Center form `3333/create/4133` |

URL pattern: `https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3329/create/ID`

---

## `4128` — Federate Identity Provider

**Use when:** a client's identity provider needs federating and it cannot be set up in Admin
Center, or you need an IdP added/modified in TID-W.

**Prerequisites / fields:**
- The description **must state what prevented using Admin Center** for the federation.
- **CRM Customer Identifier** is required.
- For adding or modifying a client's IdP, the description must list: a **client ID** on the
  provider, **scopes**, **issuer endpoint**, **authorization endpoint**, **token endpoint**,
  **JWKS endpoint**, **userinfo endpoint**, and a **test user account** on the provider for
  validation.

**🔐 Configuration settings must be provided securely via Kiteworks — never in the ticket.**
The TID team will contact you separately for the client secret and the test user password.

Related: Federation FAQ.

---

## `4138` — Authentication Issues

**Use when:** inability to log in, failure of email verification, or similar auth failures.

**Include:**
- Which solution is affected — **Identity Workforce** or **Community Access**.
- The **Organization Key** or **Okta tenant** with the issue, if known.
- A detailed description of the problem.
- Any **login error code**, pasted verbatim into the description.

---

## `4149` — Identity SKU Change

**Use when:** a customer's Identity Workforce SKU has changed and their TID deployment needs
updating to match.

**READ ME FIRST:**
- The **org must already exist in Ops Center**. If it does not, file *Org Creation*
  (`.../group/3333/create/4158`) instead — that request covers the SKU.
- Provide the correct **CRM Customer Identifier**. See *TID - Finding the CRM Customer
  Identifier (and other information in Dynamics CRM)*.
- Provide the **new Identity SKU level**, which is verified against current records.

> ⚠ **Known documentation error.** The Confluence page cited above lists this URL
> (`group/3329/create/4149`) as the *"Enable Support Access Center on Workforce Managed Org
> that has OnPrem Target=Gateway"* request. That is wrong — the live form is Identity SKU
> Change. Do not send SAC-enable requests here. For SAC enablement, direct the user to the
> **2. TCP - Operations** group on the portal, or file *Request or Share Functional
> Information* (`group/3333/create/4141`) to be routed.

---

## `4152` — Okta Access Request

**Use when:** you need access to a TID Okta tenant.
**Include:** the organization key **or** the Okta tenant URL.

---

## `4153` — Identity Client

**Use when:** adding, modifying, or requesting details of **OAuth clients** for applications.

**Terminology trap:** "Identity Client" means a **registered OAuth/OIDC application**, not a
Tyler customer. If the user says "client" meaning a customer or organization, they want an
Ops Center ticket instead — see `Knowledge-Shared/Conf-CorpDevTickets.md`.

Follow the on-form header instructions.

---

## `4159` — Custom IdP Investigation

**Use when:** a customer is requesting a **non-standard** custom IdP for federation and it
needs vetting before commitment.

Tyler Identity reviews the request and concludes whether that IdP type will be supported
going forward. Required fields include **Customer Name** and **Vendor Name**.

Reference: *Non-Standard IdP Verification Process* (Confluence).

---

## `4154` — TID Okta Tenant Request — SUPERSEDED, do not use

The form's own text: *"This request type has been superseded by the Org Creation request for
TCP - Operations. Unless you have a pre-approved reason to use this form, please use the Org
Creation request instead."*

→ https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3333/create/4158

**Unapproved requests filed here are auto-closed.**

---

## Identity requests that are NOT Identity-group tickets

Two common asks look like Identity tickets but are filed elsewhere:

| Ask | Correct ticket |
|---|---|
| Permission to **manage federations inside Ops Center** | Ops Center access/permissions form `3333/create/4133`, Notes: *"Please provide me additional permissions to be able to manage federations"* |
| **Setup/Reset AD Agent User Account** or **Reestablish Federation** permissions | Same form `3333/create/4133`, with the matching Notes wording |
| A new org (which provisions the Okta tenant and SKU) | Org Creation `3333/create/4158` |

---

## Notes for the chatbot

- **Never invent a ticket URL.** If the right form is not listed here, point the user at the
  portal root (https://help.center.tylertech.com/servicedesk/customer/portal/3168) and name
  the group, or at *Request or Share Functional Information* (`3333/create/4141`).
- **Secrets never go in a ticket.** For `4128`, configuration goes via **Kiteworks**; the TID
  team collects the client secret and test-user password out of band. Say this explicitly
  whenever federation config comes up.
- **`4149` is Identity SKU Change, not SAC enablement**, despite what the Confluence page
  says. This is the single most likely wrong answer in this area.
- **`4154` is superseded** and auto-closes. Redirect to Org Creation.
- **Feature requests are a different portal entirely** — `3185`
  (https://help.center.tylertech.com/servicedesk/customer/portal/3185), not `3168`. That
  covers Identity Workforce and Community Access feature requests too.
- Resolve "client" before answering: an **identity client** is a registered application; a
  **client** in the customer sense is an organization and belongs to Ops Center.
