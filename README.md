# onetyler-foundry-team-agent-kb

Knowledge corpora for the **OneTyler Cloud Living** Foundry Team agent and its four
sub-agents. Each `Knowledge-<Domain>/` folder is a **deployment surface**: its files are
what the corresponding Foundry agent retrieves from its tenant knowledge-base
collection. Adding, removing, or renaming a file changes what that agent knows.

This README is the **team-level routing layer**. Each folder additionally has its own
`_START_HERE.md`, which is the routing guide *within* that corpus. The Team agent reads
this file to pick a sub-agent; the sub-agent reads its own `_START_HERE.md` to pick a file.

---

## Team composition

Foundry team: **OneTyler Cloud Living** — Amazon Bedrock, Claude 4.5 Sonnet, temperature 0.7.

| Sub-agent (Foundry name) | Corpus folder in this repo | Owner |
|---|---|---|
| **Ops Center** | `Knowledge-OpsCenter/` | this repo |
| **Support Access Center** | `Knowledge-SupportAccessCenter/` | this repo |
| **General Blueprint Docs Agent** | `Knowledge-BP-General/` | this repo |
| **Tyler Identity Assistant** | `Knowledge-TylerIdentity/` | maintained separately — **read-only snapshot** |

> ⚠️ `Knowledge-TylerIdentity/` is a point-in-time copy pulled from the `TCP-KB-Identity`
> collection on 2026-08-21. Its owner maintains it outside this repo, so it will drift.
> **Do not push to that collection** — see Hard Rule 1 in `CLAUDE.md`. Re-pull before
> trusting it.

---

## Routing table — which sub-agent gets the question

Route on the **user's intent**, not on incidental keyword matches. A question that merely
*mentions* Ops Center while asking about identity federation belongs to Identity.

| Route to | When the question is about | Trigger keywords |
|---|---|---|
| **Ops Center** | Org/workspace lifecycle, product licensing & activation, org import/create, CRM customer identifiers, Ops Center permissions & telemetry, environments & allow-listing, TCP webhooks, WM→WD migration | "Ops Center", org key, workspace, licensing, availability, product registration, CRM identifier, allow-list |
| **Support Access Center** | Time-bound Tyler-staff access to customer installations, SAC groups, access request/approval/extension/revocation, SAC product integration (Security API + revoked webhook), access history & auditing | "SAC", "Support Access Center", support request, access approval, extend access, Support Council |
| **Tyler Identity Assistant** | Identity Workforce/Community, Gateway, Workforce Direct/Managed/Delegated configuration, federation, credential templates, login & token flows | "Identity", "Gateway", Workforce Direct/Managed/Delegated, federation, IdP, OIDC, SSO |
| **General Blueprint Docs Agent** | Everything else in Tyler Blueprint / TCP: platform orientation & glossary, client & ops applications, TCP/TID API catalog, service architecture, DevOps, platform security, Aligned Releases, Status Page & SLA | "Blueprint", `docs.tylerdev.io`, glossary/terminology, Admin Center, architecture, SLA |

### Routing rules

1. **Definitions are not hand-offs.** Defining a term (e.g. what "Workforce Managed"
   means) is answerable from the BP-General glossary. Hand off to a specialist when the
   user needs **workflows, configuration, or deep how-to** in that domain.
2. **General Blueprint Docs Agent is the default.** If no specialist clearly owns the
   question, it goes here — this corpus is explicitly scoped as "the rest of Blueprint/TCP."
3. **Ops Center vs SAC.** Both touch customer access. Ops Center = provisioning and
   lifecycle of orgs/workspaces/products. SAC = time-bound *staff* access into an
   already-provisioned customer installation.
4. **Ops Center vs Identity.** Ops Center covers what an operator *does in the Ops Center
   UI* (including retargeting a workspace's gateway). Identity covers how the identity
   system itself is configured and how tokens/federation work.
5. **Don't split one question across two agents.** Pick the owner of the user's actual
   goal; the answering agent can name the other domain if a follow-up is needed.

---

## Naming conventions

Filename prefixes encode the **source system**, which signals authority and freshness:

| Prefix | Source |
|---|---|
| `Conf-` | Confluence (`tylertech.atlassian.net/wiki/`) |
| `Docusaurus-` | Tyler Blueprint (`docs.tylerdev.io`) — the published source of truth |
| `Training-` | Distilled from official training assets (videos, decks, PDFs) |
| `GitHub-` | GitHub repo content (`github.com/tyler-technologies/...`) |
| `Misc-` | Curated bookmark catalog spanning multiple source systems |
| `_START_HERE.md` | Per-corpus routing guide; leading underscore sorts it first |

Files are the **GPT-optimized** form, not raw scrape output: clean markdown, a decision
guide near the top, a glossary where relevant, self-contained sections (RAG retrievers
chunk independently of headings), and direct URLs preserved verbatim.

---

## Deploying to Foundry

Knowledge files are uploaded to the tenant knowledge base as **plain text/markdown**.
There is no update-in-place endpoint — updating content means upload new, delete old,
then sync.

Non-obvious constraints that will bite you:

- **`ingestionStatus: "ingested"` proves nothing.** Always verify with a scoped
  retrieval probe (`POST /api/tenant-knowledge-base/retrieve` with
  `filterCollectionNames`). Markdown avoids the silent-failure classes that affect PDFs.
- **Uploads cap at 10 files per request and each request auto-triggers a sync.** Bedrock
  runs one ingestion job at a time and only indexes files present when its scan starts.
  Upload **all** batches first, then trigger **one** consolidated sync.
- **Re-sync cannot repair an already-indexed file.** Delete and re-upload instead.
- Metadata tags support **exact-match, AND-combined** filters only — no ranges,
  substrings, or OR.

---

## Index hygiene

When you add, rename, or remove a file:

1. Update that folder's `_START_HERE.md` (file catalog + routing table). A stale start
   page actively misleads the agent.
2. Update this README if the change affects **team-level** routing or adds a corpus.
3. Re-upload the changed files and re-verify retrieval.
