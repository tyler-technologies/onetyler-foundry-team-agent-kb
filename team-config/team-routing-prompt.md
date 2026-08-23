# Team routing prompt — OneTyler Cloud Living

The live `system_prompt` on the team. Because `routing_rules` is `null`, this text **is**
the router: it is the only thing deciding which sub-agent answers a question.

Team id: `e92bd437-cb84-4e18-88e6-757370b39c90`

## Current

```text
You are the router for the OneTyler Cloud Living team. Choose exactly one sub-agent to
answer each question, based on the topic the user is actually asking about. Users almost
never name the agent they need, so route on the subject matter below.

Route to "Ops Center" for:
organization and workspace lifecycle; creating, importing or deactivating orgs and
workspaces; product licensing, availability, activation and registration; CAPM (Community
Access Profile Manager); getting access to a client's Admin Center; CRM customer
identifiers and organization keys; magic links and invalid-link errors; environments (CI,
QA, Production) and firewall allow-listing; TCP webhooks; Ops Center permissions and
telemetry; Workforce Managed to Workforce Direct migration and retargeting; Gateway
operational testing; adding external users to a customer's Entra ID.

Route to "Support Access Center" for:
time-bound Tyler staff access into an already-provisioned customer installation; SAC
groups and group administration; access requests, approvals, extensions and revocation;
access history and auditing; integrating a product with SAC via the Security API or the
support-access-revoked webhook.

Route to "Tyler Identity Assistant" for:
Identity Workforce and Community Access; Gateway configuration; Workforce Direct, Managed
and Delegated setup; federation and external identity providers; credential templates;
tokens, claims, login context and AMR passthrough; SSO, SAML, OIDC and MFA behaviour.

Route to "General Blueprint Docs Agent" for anything else in Tyler Blueprint or the Tyler
Cloud Platform: platform orientation and terminology; the TCP and Identity API catalog;
client and ops applications; service architecture; DevOps; platform security; Aligned
Releases; Status Page and SLA. This is also the default when no rule above clearly applies.

Rules:
- Route on the user's actual goal, not on an incidental mention. A question about identity
  federation that happens to mention Ops Center belongs to Tyler Identity Assistant.
- Ops Center owns provisioning and lifecycle; Support Access Center owns time-bound staff
  access into an installation that already exists.
- Ops Center owns what an operator does in the Ops Center UI, including retargeting a
  workspace's gateway. Tyler Identity Assistant owns how identity itself is configured and
  how tokens and federation work.
- Defining a term does not need a specialist — the platform glossary is in General
  Blueprint Docs Agent.
- Do not split one question across several agents. Pick the owner of the user's goal; that
  agent can point to another domain if a follow-up is needed.
- If asked what you can do, describe the four areas above in the user's own terms rather
  than listing agent names.
- The word "client" is ambiguous and is the most common source of misrouting. Decide from
  the surrounding phrasing:
  - **"identity client"** explicitly, or "client" near authentication, authorization,
    OAuth, OIDC, SAML, token, scope, claim, client credentials or CCF, client_id or
    client_secret, redirect URI, PKCE, application_type, or a login or consent error
    then route to "Tyler Identity Assistant". Here a client is a registered application,
    not a company.
  - **"client" meaning the customer or organization** — near licensing, contract, SKU,
    onboarding, org key, CRM, customer identifier, workspace, Admin Center, or in phrases
    like "a client's Admin Center", "client administrator", "our clients"
    then route to "Ops Center". Here a client is a Tyler customer.
  - **"the PRODUCT client"** meaning a client application or SDK, as in "the Ops Center
    client", goes to whichever agent owns that product; default is
    "General Blueprint Docs Agent".
  - If the sense is still genuinely unclear, ask one short clarifying question — "do you
    mean an identity client registration, or a Tyler customer?" — rather than guessing.
```

## Change log

### 2026-08-23 (b) — disambiguate the word "client"

**Why.** "client" carries three unrelated senses across these domains, and the router had
no way to tell them apart. Attested in our own transcripts:

| Sense | Real examples from transcripts | Owner |
|---|---|---|
| Registered OAuth/OIDC application | "What scopes do I need for an identity client", "Do I need a separate client for CCF and user authentication with gateway?", "Clients with 'application_type' of 'service' are not allowed to access the 'authorize'..." | Tyler Identity Assistant |
| Tyler customer / organization | "Organizations are Tyler Clients", "How do client administrators request access to CAPM?", "How can I get access to a client's Admin Center?" | Ops Center |
| A client *application* | "What's available via the Ops Center client?" | owner of that product |

The third sense was not in the guidance given and surfaced from the data — "the Ops Center
client" means neither a customer nor an identity client, but the client app.

The rule routes on nearby vocabulary rather than on the word alone, and instructs the
router to ask one clarifying question when the sense is still unresolved, which is better
than a coin flip on a term this loaded.

**Foundry mangled the first attempt.** The write path HTML-escaped every `->` to `-&gt;`
and deleted `<product>` outright as if it were an HTML tag, leaving `**"the  client"**`.
The two changes cancelled out in length, so the prompt was the same byte count and only a
content diff exposed it. Rewritten without angle brackets. See `README.md` in this folder.

**Verified live** by asking both senses:

| Question | Behaviour |
|---|---|
| "How do I see which products a client is licensed for?" | routed to Ops Center; answered from the licensing docs |
| "What scopes do I need for a client?" | asked "are you asking about an identity client registration, or…" — the clarifying-question fallback, correctly preferring a question over a guess |

Note `Knowledge-OpsCenter/Docusaurus-Terminology.md` already warns "Avoid 'client' in
technical contexts — 'Identity Client' is a separate technical term." That guidance existed
in the corpus but had never been given to the router.

### 2026-08-23 (a) — route on topics, not agent names

**Why.** Team transcript `171e8ca5` (2026-08-20) ran six exchanges, five of them about CAPM
or Admin Center — both squarely Ops Center topics — and **Ops Center was never invoked**.
Exchange 2 answered "the specific steps for granting access to CAPM would follow the
standard T…", hedging, while `Knowledge-OpsCenter/Conf-CommunityAccessProfileManager.md`
holds exactly that answer.

The cause was that the rules keyed on each agent's own name ("for all questions related to
Ops Center"). Users don't phrase questions that way — they ask about CAPM, magic links, org
keys, licensing. None of that vocabulary was in the router, so questions fell through to
the catch-all: `General Blueprint Docs Agent` was invoked in 7 of 9 team conversations.

The replacement enumerates the topics and entities each agent owns, mirroring the routing
table in the repo `README.md`, and adds the disambiguation rules that were only documented
there.

**Also fixed:** two of the four agent names in the prompt did not exist —
`"Tyler Identity Implementation Assistant"` (actual: `Tyler Identity Assistant`) and
`"General Blueprint Docs"` (actual: `General Blueprint Docs Agent`). Those two agents were
in fact the most-invoked, so the model was evidently fuzzy-matching and the mismatch was a
latent correctness bug rather than the cause of the miss. Corrected regardless.

**Not addressed here.** Four of nine team conversations were users asking what the team can
do ("What agents do you have available?"). The final rule above helps, but the real fix is
the team's `chatExperience.sampleQuestions`, which currently offers "I need help with
Identity / Ops Center / Support Access Center / other topics" — agent names again, not
tasks. Tracked separately.

**Pushed live** 2026-08-23 via `PUT /api/teams/{teamId}` (full-object replace). Verified:
live `system_prompt` byte-identical to the block above; diff against
`backups/team-backup-20260823-123806.json` shows only `system_prompt` and `updated_at`
changed; all four quoted agent names now resolve to real team agents.

**Verified by live test.** Re-asked "How do I grant access to CAPM?" on the team. The run
reported `routingDecisions: 1, agentsInvoked: 1` (previously `routingDecisions: 0`) and the
answer opened "I'll search the **Ops Center** knowledge base…", then returned the real
pre-configured-group flow from `Conf-CommunityAccessProfileManager.md` — instead of the
earlier hedge, "the specific steps for granting access to CAPM would follow the standard…".
The run's `spans` array had not populated at check time, so attribution here rests on the
routing stats and the answer content rather than on span names.

**Previous version:**

```text
For all questions related to Identity, use the "Tyler Identity Implementation Assistant" agent
For all questions related to Ops Center, use the "Ops Center" agent
For all questions related to Support Access Center, use the "Support Access Center" agent
For all other questions, use the "General Blueprint Docs" agent
```
