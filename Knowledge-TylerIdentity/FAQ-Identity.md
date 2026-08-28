# FAQ — Tyler Identity

Source: **authored in this repo — no upstream document.** The rest of this folder is derived
from Tyler Blueprint `docs/identity/`. This file is the **home of record** for identity
answers that exist nowhere else.

Domain: Tyler Identity
Audience: Tyler product, engineering and identity-support staff.

**Deployed.** This file is in the `TCP-KB-Identity` Foundry collection as of 2026-08-24; this repo is its source of truth. Edit here and re-upload — never edit it in the Foundry UI.

**Companion:** for "which ticket do I file", use `Knowledge-Shared/Conf-OneTylerTickets.md`.

---

## What belongs here

- Answers given verbally by a subject-matter expert that are not written down anywhere.
- Behaviour learned by observation or testing that no document describes.
- Corrections to an upstream source the owner has not yet fixed.
- Disambiguation and phrasing guidance the agent needs but no doc states.
- Recurring questions from real transcripts whose answer had to be assembled from scratch.

## What does NOT belong here

- Anything already in Blueprint `docs/identity/` — it belongs in `Docusaurus-Identity.md`,
  so it is re-derived when Blueprint changes.
- Ticket forms — `Knowledge-Shared/Conf-OneTylerTickets.md`.
- Speculation. If nobody has confirmed it, leave it out; the agent will state it as fact.

## Entry format

```markdown
### Q: <the question, phrased the way a user would ask it>

**A:** <the answer>

- **Source:** <who said it / where it was observed — name a person or a verifiable check>
- **Added:** <YYYY-MM-DD> by <github username>
- **Confidence:** confirmed by owner | provisional — needs confirmation
- **Promote when:** <the upstream doc that should eventually carry this, if any>
```

Keep entries self-contained — retrievers chunk independently of headings.

---

## Entries

### Q: Someone said "client" — do they mean an identity client or a customer?

**A:** In an identity context "client" usually means a **registered OAuth/OIDC application**,
not a company. Treat it that way when the question sits near authentication vocabulary:
"identity client", OAuth, OIDC, SAML, scopes, tokens, claims, client credentials or CCF,
`client_id` / `client_secret`, redirect URI, PKCE, `application_type`, or a login or consent
error.

If instead it appears near **licensing, contracts, onboarding, org keys, CRM identifiers,
Admin Center**, or in phrases like "a client's Admin Center" or "client administrator", the
user means a **Tyler customer / organization** and the question belongs to Ops Center.

If the sense is genuinely unclear, **ask one clarifying question** rather than guessing —
e.g. "do you mean an identity client registration, or a Tyler customer?"

- **Source:** Vijay Venkataraman, 2026-08-23, in response to observed routing failures.
- **Added:** 2026-08-23 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** if Blueprint's identity glossary adds this distinction, move it there.

### Q: Which ticket enables Support Access Center on a Workforce Managed org?

**A:** **Not `group/3329/create/4149`**, despite what the Confluence page *Ops Center Related
Tickets and Permissions* says. That URL is verified live as the **Identity SKU Change** form,
a different request. Do not send SAC-enable requests there.

Until the Confluence page is corrected, direct the user to the OneTyler portal
(https://help.center.tylertech.com/servicedesk/customer/portal/3168) → **2. TCP -
Operations**, or have them file *Request or Share Functional Information*
(`group/3333/create/4141`) to be routed.

- **Source:** verified 2026-08-23 by opening the live form at that exact URL; it renders as
  "Identity SKU Change" with a READ-ME-FIRST about the org already existing in Ops Center.
- **Added:** 2026-08-23 by vijay-tylertech
- **Confidence:** confirmed — the live form is authoritative over the wiki page
- **Promote when:** the Confluence page is fixed. Then delete this entry; the corrected
  mapping belongs in `Knowledge-Shared/Conf-OneTylerTickets.md`.

### Q: How do I federate with Entra ID? What does the customer configure on the Entra side?

**A:** Federation has **two halves**, and answers that cover only the Tyler half are the
common failure here. The customer must first register an application in their own Entra ID
tenant, then hand the resulting client details to the Tyler side (Admin Center, or ticket
`4128` if Admin Center cannot be used).

**Use when:** the user asks how to federate with Entra / Azure AD, what to send a customer so
they can federate, or what the customer has to do in their own tenant. Applies to **Identity
Workforce** federation.

**Prerequisites:** the customer's Entra ID must be reachable from the public internet, support
OIDC or SAML 2.0, and be able to release the claims Email, Username, First name, Last name.

**Check which org you are federating first.** If the organization is **Workforce Delegated**,
federation belongs to its **Super** org and must be established there — these steps applied to
a Sub org will not work. Establish the Workforce model before handing out any of this; see
*Can the customer get into Admin Center before the federation is in place?* below.

**Client side — register the application in Entra ID:**

1. Sign in to the organization's Entra ID portal — https://entra.microsoft.com
2. In the left-hand navigation, expand **Identity → Applications** and select **App
   registrations**.
3. Click **+ New registration**.
4. On *Register an application*, set:
   - **Name:** `TylerIdentityWorkforceIntegration`
   - **Supported account type:** *Accounts in this organizational directory only*
   - **Redirect URI** platform: **Web**
   - **Redirect URI** value: `https://tyler-<customeridentifier>.okta.com/oauth2/v1/authorize/callback`
5. From the **Overview** page, copy the **Application (client) ID** and the **Directory
   (tenant) ID**.
6. Go to **Manage → Certificates & secrets**, select the **Client secrets** tab, and click
   **+ New client secret**:
   - **Description:** `TylerIdentityWorkforceIntegration`
   - **Expires:** 730 days (24 months). Tyler recommends the longest available expiry, to
     reduce how often the federation has to be reconfigured in TID-W when the secret expires —
     but the customer's own security posture governs this. Say both parts; do not present 730
     days as a requirement.
7. Click **Add**, then back on *Certificates & secrets* find the secret **Value** and copy it.

**What that produces, for the Tyler side of the configuration:** Application (client) ID,
Directory (tenant) ID, and the client secret **Value** — plus the endpoints and scopes the
Admin Center form asks for.

**Never put the client secret in a ticket.** It goes via Kiteworks, or the TID team collects it
in a follow-up. Same for any test-user password.

- **Source:** Confluence — *Federating using Entra ID through Admin Center*,
  https://tylernow.atlassian.net/wiki/spaces/KA/pages/950796345/Federating+using+Entra+ID+through+Admin+Center
  Supplied by Jon Olson from transcript review, 2026-08-28: the agent explained the Tyler side
  and the ticket route but gave no client-side procedure.
- **Added:** 2026-08-28 by jon-olson-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** Blueprint `docs/identity/` documents client-side IdP registration. Then move
  this to `Docusaurus-Identity.md` and delete the entry.

### Q: Can the customer get into Admin Center before the federation is in place?

**A:** **It depends on which Workforce deployment model the organization uses — establish that
before answering.** This is the trap: the bootstrap path differs by model, so a single
confident answer is wrong for at least one of them.

**Do this first.** Ask, or confirm the org's **Identity Tier** in Ops Center. There are
**four** Workforce models, and they are not interchangeable:

| Model | Initial Admin Center access | Where federation is established |
|---|---|---|
| **Workforce Direct** | **Magic link** | On the org itself |
| **Workforce Managed** | **Through Admin Center** | On the org itself |
| **Workforce Delegated** | **Through Admin Center** | **On the Super org** — never on the Sub |
| **Workforce Global** | Local user store **auto-creates the admin account** (Private Preview) | On the org itself |

If the user has not said which model, **ask** — do not assume Direct because it is the most
common. (This is the within-Workforce counterpart to the Workforce-vs-Community check in
`_START_HERE.md`.)

**Workforce Direct** — initial access is granted through a **magic link**, not through
credentials issued to the technical contact. If federation is broken or not yet in place, the
route back in is the *Reestablish Federation* process:
https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386625934/Tyler+Cloud+Platform+TCP+Reestablish+Federation+Demo

**Workforce Global** — **in Private Preview as of 2026-08-28**, and **distinct from Workforce
Delegated**; they are different models, not two names for one thing. Global integrates with a
local user store that **automatically creates the admin user's account**, so the bootstrap
problem does not arise the same way. Say that it is Private Preview whenever you mention it.

**Workforce Managed** — initial access is **through Admin Center**. Federation is established
on the org itself.

**Workforce Delegated** — initial access is **also through Admin Center**, but **all
federations are delegated to the Super org, so the federation must be established there, not
on the Sub org.** This is the one that produces wrong answers: someone asking "how do I
federate this org" about a Sub org needs to be pointed at its Super, and a set of Entra
details configured against the Sub will not work. If the org is Delegated, **establish which
org is the Super before giving any federation instructions.**

**Where the model definitions live:** `Knowledge-OpsCenter/Docusaurus-Terminology.md` defines
Direct, Managed and Delegated, including Delegated's Super/Sub structure, and states that the
Identity Tier **cannot be changed after the org is created**. That file predates Workforce
Global and does not mention it — so treat this entry as the current list and that file as the
authority on the first three.

**Do NOT give this as a single universal answer:** that the Customer Technical Contact named
during org creation "receives Admin Center access credentials", and that this is what solves
the chicken-and-egg problem. That was the answer given in a real conversation on 2026-08-25,
and it is wrong twice over — it is not how **Workforce Direct** bootstraps (the magic link is
the mechanism), and it presents one path as if it applied to every model. Naming a technical
contact during org creation and how that contact first authenticates are two different
things.

- **Source:** Jon Olson (Tyler Identity corpus owner), transcript review 2026-08-28, correcting
  the answer given in the 2026-08-25 conversation `9c230f8d`. Reestablish Federation demo page
  supplied in the same review.
- **Added:** 2026-08-28 by jon-olson-tylertech
- **Confidence:** confirmed by owner — all four models (Jon Olson, 2026-08-28): Direct's magic
  link; Managed and Delegated both via Admin Center; Delegated's federation belonging to the
  Super org; Global in Private Preview and a **different model from Delegated**.
- **Promote when:** Blueprint documents the per-model bootstrap paths, or Workforce Global
  leaves Private Preview — at which point this entry needs revisiting either way.

---

## Notes for the chatbot

- Entries here have **no upstream document**. State them plainly, but if challenged, say the
  answer comes from internal Tyler subject-matter guidance rather than published docs.
- An entry marked **provisional** has not been confirmed by an owner. Hedge accordingly.
- Where an entry exists to *correct* an upstream source, it says so in **Source** — in that
  case the entry wins over the document it corrects.
