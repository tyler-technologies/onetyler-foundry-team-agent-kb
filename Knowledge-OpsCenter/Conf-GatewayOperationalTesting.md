# Gateway Operational Testing — Validating Gateway-Ready Products Under Real-World Conditions

Source: Confluence — *Tyler Cloud Platform (TCP) | Gateway Operational Testing* (https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386600150) — last updated Feb 23.
Domain: Ops Center
Audience: Tyler product engineering and operational team members validating that their product's **Gateway-ready** version works under real-world deployment conditions before being deployed to customers.

This document covers what "Gateway readiness" means, the four integration components, the difference between Core compliance and Full compliance, how to plan testing using the **`tylertownwa`** real-world test organization (with test user credentials), the Tyler Deploy-specific addendum, how to mark a product as validated, and what to do for net-new customers whose product mix has mixed Gateway readiness.

**Companion documents in this same Knowledge folder:**
- `Docusaurus-Terminology.md` — see *Identity Workforce* (Workforce Direct / Managed / Delegated) for the canonical terminology and the **"Gateway" disambiguation** below.
- `Docusaurus-OpsCenter.md` — for the Org Creation flow and Identity Tier details.
- `Knowledge-Shared/Conf-OneTylerTickets.md` — for the **Org Creation ticket** referenced in the net-new-customers section.
- `Misc-Links.md` — for the live link to this Confluence page and related bookmarks.

---

## How to use this guide (quick decision guide)

| If the user wants to… | Go to section |
|---|---|
| Know what "Gateway" means in this context (and the customer-facing terminology rule) | **Terminology — Gateway vs Identity Workforce** |
| See the 4 components of Gateway integration | **The 4 Gateway integration components** |
| Know what "Core compliance" vs "Full compliance" means | **Core vs Full compliance** |
| Find the test organization (`tylertownwa`) URLs | **Test org: `tylertownwa`** |
| Get test user credentials for validation | **Test credentials** |
| Plan a real-world testing pass for a Core-Gateway-ready product | **Testing plan — Core Gateway readiness** |
| Test a Tyler Deploy-based product | **Addendum — Tyler Deploy-based products** |
| Mark a product as successfully validated | **Marking your product as validated on `tylertownwa`** |
| Decide identity setup for a NET-NEW customer with mixed-readiness products | **Net-new customers — operational considerations** |
| Track product Gateway readiness across Tyler | **Coda tracker** |

---

## Terminology — Gateway vs Identity Workforce

**"Gateway"** is an **internal code name** for the latest iteration of Tyler's Identity Workforce engine. It provides the Single Sign-On experience for customer back-office users.

### Customer-facing rule

In **customer-facing conversations**, ONLY use the terms:

- **Identity Workforce** — the umbrella product name.
- **Workforce Direct** — federation-only customers (customer brings their own IdP).
- **Workforce Managed** — customers paying for and requesting a Tyler-managed user store.

**Do NOT say "Gateway" to customers.** Tyler is strongly encouraging customers to use **Workforce Direct**, which is a new option made possible by the Gateway engine.

(See `Docusaurus-Terminology.md` → *Identity Workforce* for the full canonical glossary entry.)

---

## The 4 Gateway integration components

Integrating with Gateway has four distinct components. Each product team evaluates which apply to their product:

| # | Component | Compliance level |
|---|---|---|
| 1 | **Gateway user login** | Core gateway readiness |
| 2 | **Dual Auth APIs** | Core gateway readiness |
| 3 | **CCF Transitions** | Full gateway readiness |
| 4 | **Credentials Template** | Full gateway readiness |

Not all products need to adopt all four constructs. Each product team determines which apply based on their architecture.

## Core vs Full compliance

- **Core compliance** — Achieved when a product has either **adopted or determined it does NOT need to adopt** the first 2 constructs (Gateway user login + Dual Auth APIs), excluding CCF Transitions and Credentials Template. **This level allows a product/solution to be deployed to customer environments.**
- **Full compliance** — Achieved when a product also incorporates **CCF Transitions** and **Credentials Template**. **Not an absolute requirement to start deploying Gateway-ready versions of the product** — you can ship at Core compliance.

## Coda tracker

The progress of all Tyler products through Gateway readiness is tracked in Coda. The **"Core gateway readiness"** column is where the gateway-readiness signal lives:

- https://coda.io/d/Gateway-Rollout_dKV_6fSnfBc/4-Gateway-Readiness_suJSq#_lurEf

(See **Marking your product as validated** below for the related Coda page where you mark `tylertownwa` validation.)

---

## Test org: `tylertownwa`

OneTyler maintains a **"real-world"-like Workforce Direct (Gateway) configured organization** called **`tylertownwa`** in production. This is the canonical org for Gateway operational testing. The Ops Center links are:

| Environment | URL |
|---|---|
| **CI (Dev)** | https://admin.tcpci.com/portal/ops-center/manage-organizations/tylertownwa/details |
| **QA** | https://admin.tcpqa.com/portal/ops-center/manage-organizations/tylertownwa/details |
| **Production** | https://admin.tylerportico.com/portal/ops-center/manage-organizations/tylertownwa/details |

## Test credentials

Two synthetic end-user accounts exist in `tylertownwa` for Gateway login testing. **The
shared password is deliberately NOT reproduced in this knowledge file** — retrieve it from
the source Confluence page:

> 🔑 **Get the password here:** *Tyler Cloud Platform (TCP) | Gateway Operational Testing* →
> **Test credentials** section — https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386600150
>
> Requires Tyler SSO. Do not copy the password into tickets, chat, code, or any other
> document — link to the Confluence page instead.

| Account | Email | Email inbox? |
|---|---|---|
| **User 1** | `amelia.brady@tylertownwa.org` | **Yes** — accessible at https://outlook.office.com/mail/ |
| **User 2** | `joel.enlow@tylertownwa.org` | No |

Both accounts share the same password (see the Confluence page above).

**Important for the email inbox:** open https://outlook.office.com/mail/ in an **Incognito / Private browsing window**, otherwise the browser will use your own Tyler credentials and you'll end up in your own inbox instead of the test account's.

---

## Testing plan — Core Gateway readiness

For all products that have Core Gateway readiness, treat the testing exercise **as a real-world client deployment**. Steps:

1. **Update operational documentation** (if necessary) to reflect any special considerations for the Gateway-ready version of your product.
2. **Have a real operational team member** — someone who is nominally responsible for a customer deployment/implementation — actually follow the instructions you'd normally hand to a customer.
3. **Test with the customer accounts above** (see *Test credentials*). The whole point is to validate using **non-Tyler-Tech credentials** — there is special functionality in effect for `@tylertech.com` email ids, so testing only with TT accounts will not reflect real customer behavior.
4. **Additionally test with Tyler Tech email ids** to ensure any deployment / implementation / support scenarios that would normally involve Tyler staff also work.
5. **For any issues, post in the [**Identity Workforce** Teams channel](https://teams.microsoft.com/l/channel/19%3Ae0289e84ce4a4bae841c55249970a491%40thread.tacv2/Identity%20Workforce?groupId=d9db441d-35fa-433c-8fe0-ff7fe5825d3c&tenantId=7cc5f0f9-ee5b-4106-a62d-1b9f7be46118).**

---

## Addendum — Tyler Deploy-based Core Gateway-ready products

If your product uses **Tyler Deploy** to deploy part or all of your solution, there are extra steps.

### Related technical reference

See the Confluence page **Configure Tyler Identity Workforce Client** (`/wiki/spaces/TOD/pages/357302785/`) — covers how your Gateway-ready product should be able to read the **"Gateway"** and **"Organization ID"** values and switch between legacy and gateway modes depending on the "Gateway" value.

### Test in External Tyler Deploy

Use the **"Tyler Town - WA 999999990126"** tenant in **External Tyler Deploy** to deploy your product(s)/solution(s) as you would for any customer environment.

### Backwards-compatibility rule

**Gateway-ready versions on Tyler Deploy must be backwards-compatible** during the transition period. They must be installable in BOTH legacy AND gateway modes depending on the product config generated in Tyler Deploy. So you do want to test **both organization types**:

- **Gateway testing:** `Tyler Town - WA 999999990126` tenant (OneTyler supplies only this one for Gateway testing).
- **Legacy testing:** Use your current testing environments (e.g., **Echo**) — OneTyler does not supply a OneTyler-side legacy testing tenant.

---

## Marking your product as validated on `tylertownwa`

After successful validation, search for your product on the Coda Gateway-Readiness page and mark it under the **`tylertownwa validated`** column:

- https://coda.io/d/Gateway-Rollout_dKV_6fSnfBc/5-Gateway-Readiness_suzLsJSq#_luC72rEf

This is how your team signals to the rest of Tyler that your Gateway-ready product is now ready to be deployed to real customers.

---

## Net-new customers — operational considerations

When a **net-new customer** (one for whom OneTyler has not previously provisioned an org — verifiable in Ops Center) licenses or subscribes to multiple products / a product suite, the products may have **mixed Gateway readiness**. Use these steps to decide identity setup:

1. **Identify all products the customer has licensed/subscribed** in CRM via **"Active Customer Product Items"**.
2. **Compare each product's Gateway readiness** against the **"Core gateway readiness"** column in Coda:
   https://coda.io/d/Gateway-Rollout_dKV_6fSnfBc/4-Gateway-Readiness_suJSq#_lurEf
3. **Decision rules** based on what you find:

| Finding | Action |
|---|---|
| **One or more products listed as "Not Ready"** | Request the Org be created as **Workforce Managed** using the **"Core"** selection when filing the *Org Creation* ticket (see `Knowledge-Shared/Conf-OneTylerTickets.md`). **Note:** If the customer is an *explicit* "Workforce Managed" customer, select the appropriate **tier listed in CRM** instead of "Core". |
| **All products listed as "Ready: <version>"** AND the customer is **directly federating** | Request the Org as **Workforce Direct** (or Direct Federation) on the *Org Creation* ticket. |

---

## Notes for the chatbot

- **"Gateway" is internal code; "Identity Workforce" is the customer-facing brand.** When a user mentions "Gateway" in a customer-facing context, gently redirect to "Identity Workforce / Workforce Direct / Workforce Managed." When discussing internally with engineering, "Gateway" is fine.
- **Core compliance ≠ Full compliance.** Products can ship at Core compliance — Full is not required to start deploying. When a product team asks "are we ready to ship?", check Core readiness first.
- **Always send users to the Coda tracker** (https://coda.io/d/Gateway-Rollout_dKV_6fSnfBc/4-Gateway-Readiness_suJSq#_lurEf) for the live readiness status — it changes over time and is the authoritative source.
- **The `tylertownwa` test org lives in production (`tylerportico.com`)** — but copies exist in CI and QA. For a customer-realistic test, prefer the production URL since that's where customers will encounter the real behavior.
- **You do not have the test password and must not guess one.** The shared password for `amelia.brady` / `joel.enlow` is deliberately excluded from this corpus. When a user asks for it, point them to the **Test credentials** section of the source Confluence page (https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386600150), which requires Tyler SSO. Tell them not to copy it into tickets, chat, or code. The account emails above are safe to give out.
- **The Outlook inbox needs Incognito** — repeat this whenever a user is testing User 1 email flows. Without Incognito they'll see their own inbox.
- **Test with a non-Tyler-Tech account.** `@tylertech.com` accounts trigger special functionality and won't reflect real customer behavior — this is the whole point of providing the `amelia.brady@tylertownwa.org` and `joel.enlow@tylertownwa.org` accounts.
- **For Tyler Deploy-based products, BOTH legacy and gateway modes must be tested.** OneTyler only supplies `Tyler Town - WA 999999990126` for the gateway side; the product team is responsible for sourcing their own legacy test env (Echo, etc.).
- **Net-new customers with mixed-readiness products go to Workforce Managed (Core)** — even if the customer wanted Workforce Direct. The "Not Ready" product blocks WD adoption. Make sure this is clearly communicated to the customer expectation-wise. Once all their products reach Ready status, a conversion path is possible (see the WM→WD Retargeting and Migration runbook referenced in `Knowledge-Shared/Conf-OneTylerTickets.md`).
- **Issues with the test plan or the test org itself: post in the [**Identity Workforce** Teams channel](https://teams.microsoft.com/l/channel/19%3Ae0289e84ce4a4bae841c55249970a491%40thread.tacv2/Identity%20Workforce?groupId=d9db441d-35fa-433c-8fe0-ff7fe5825d3c&tenantId=7cc5f0f9-ee5b-4106-a62d-1b9f7be46118).**
