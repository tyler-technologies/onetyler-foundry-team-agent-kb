# onetyler-foundry-team-agent-kb

Knowledge corpora for the **OneTyler Cloud Living** Foundry Team agent and its five
sub-agents. Each `Knowledge-<Domain>/` folder is a **deployment surface**: its files are
what the corresponding Foundry agent retrieves from its tenant knowledge-base
collection. Adding, removing, or renaming a file changes what that agent knows.

This README is the **team-level routing layer**. Each folder additionally has its own
`_START_HERE.md`, which is the routing guide *within* that corpus. The Team agent reads
this file to pick a sub-agent; the sub-agent reads its own `_START_HERE.md` to pick a file.

---

## New here?

| You are | Start with |
|---|---|
| A contributor setting up for the first time | [`contributor-initial-prompt.md`](contributor-initial-prompt.md) — the first prompt to give your AI agent. Clones the repo, orients the agent, starts the review UI. |
| A reviewer wanting the walkthrough | [`transcripts/ONBOARDING.md`](transcripts/ONBOARDING.md) |
| Looking for the process and field definitions | [`transcripts/README.md`](transcripts/README.md) |
| An AI agent working in this repo | [`CLAUDE.md`](CLAUDE.md) — read it in full before anything else |

**Who may change what.** Contributors own subject-matter content; admins own anything that
decides which agent answers. The authoritative list is
[`.github/admin-only-paths.txt`](.github/admin-only-paths.txt).

| Contributors may change | Admin-only |
|---|---|
| Knowledge content in any `Knowledge-<Domain>/` folder — the `Conf-`, `Docusaurus-`, `FAQ-`, `Misc-`, `Training-`, `GitHub-` files | `README.md` (this file — the team routing table), `team-config/`, **every `Knowledge-*/_START_HERE.md`** |
| Review verdicts under `transcripts/` | `CLAUDE.md`, `contributor-initial-prompt.md`, `transcripts/README.md`, `transcripts/ONBOARDING.md`, `scripts/`, `templates/`, `.github/`, `.gitignore`, `contributors.json` |

`_START_HERE.md` sits in a folder contributors can otherwise edit, but it carries
**cross-agent hand-off rules**, which is team-level routing — so it is admin-only.

Enforced by CODEOWNERS plus branch protection, a CI check, and a warning in
`start_review_session.sh`. Found a problem in an admin-only file? Say so in your PR
description rather than fixing it.

What no check catches: routing advice written *inside* a knowledge file. Human review is the
only control for that.

---

## Team composition

Foundry team: **OneTyler Cloud Living** — Amazon Bedrock, Claude 4.5 Sonnet, temperature 0.7.

| Sub-agent (Foundry name) | Corpus folder in this repo | Owner |
|---|---|---|
| **Ops Center** | `Knowledge-OpsCenter/` | this repo |
| **Support Access Center** | `Knowledge-SupportAccessCenter/` | this repo |
| **General Blueprint Docs Agent** | `Knowledge-BP-General/` | this repo |
| **Aligned Releases** | `Knowledge-AlignedReleases/` | this repo |
| **Tyler Identity Assistant** | `Knowledge-TylerIdentity/` | this repo |

> Tyler Identity was cut over to this repo on **2026-08-24**: its collection now holds
> `Docusaurus-Identity.md`, `_START_HERE.md`, `Conf-IdentityTickets.md`, `FAQ-Identity.md`
> and the shared ticket catalog. `Docusaurus-Identity.md` still reflects a Blueprint pull of
> 2026-05-20 — re-derive it when Blueprint moves.

In addition, **`Knowledge-Shared/`** holds content every agent needs and is uploaded to all
writable collections — currently the OneTyler ticket catalog. See its `_START_HERE.md`.

---

## Routing table — which sub-agent gets the question

Route on the **user's intent**, not on incidental keyword matches. A question that merely
*mentions* Ops Center while asking about identity federation belongs to Identity.

| Route to | When the question is about | Trigger keywords |
|---|---|---|
| **Ops Center** | Org/workspace lifecycle, product licensing & activation, org import/create, CRM customer identifiers, Ops Center permissions & telemetry, environments & allow-listing, TCP webhooks, WM→WD migration | "Ops Center", org key, workspace, licensing, availability, product registration, CRM identifier, allow-list |
| **Support Access Center** | Time-bound Tyler-staff access to customer installations, SAC groups, access request/approval/extension/revocation, SAC product integration (Security API + revoked webhook), access history & auditing | "SAC", "Support Access Center", support request, access approval, extend access, Support Council |
| **Tyler Identity Assistant** | Identity Workforce/Community, Gateway, Workforce Direct/Managed/Delegated configuration, federation, credential templates, login & token flows | "Identity", "Gateway", Workforce Direct/Managed/Delegated, federation, IdP, OIDC, SSO |
| **Aligned Releases** | **Release Manager** (the internal tool for authoring client-facing features), quarterly GA release model, feature lifecycle (Planned/Private Preview/Public Preview/GA), taking a feature GA, cohorts and cohort assignment, feature activation windows, release documentation and notes, versions like 2026.1, maintenance windows, the Aligned Releases API and SDK, client release notification emails | **"release manager"**, **"release management"**, "aligned release", "cohort", "feature", "feature activation", "feature flag", "release", "GA", **"private preview"**, **"public preview"**, "2026.1", release notes |
| **General Blueprint Docs Agent** | Everything else in Tyler Blueprint / TCP: platform orientation & glossary, client & ops applications, TCP/TID API catalog, service architecture, DevOps, platform security, Status Page & SLA | "Blueprint", `docs.tylerdev.io`, glossary/terminology, Admin Center, architecture, SLA |

### Routing rules

0. **Ticket questions always go to Ops Center.** Any "which ticket do I file / how do I
   request access or permissions" question — *including* Identity and Support Access Center
   tickets — is answered from `Knowledge-Shared/Conf-OneTylerTickets.md`, the single
   authoritative catalog. One copy, not three, so the copies cannot drift. Never invent a
   ticket URL.

1. **Definitions are not hand-offs.** Defining a term (e.g. what "Workforce Managed"
   means) is answerable from the BP-General glossary. Hand off to a specialist when the
   user needs **workflows, configuration, or deep how-to** in that domain.
2. **General Blueprint Docs Agent is the default.** If no specialist clearly owns the
   question, it goes here — this corpus is explicitly scoped as "the rest of Blueprint/TCP."
3. **Ops Center vs SAC.** Both touch customer access. Ops Center = provisioning and
   lifecycle of orgs/workspaces/products. SAC = time-bound *staff* access into an
   already-provisioned customer installation.
4. **Aligned Releases vs Ops Center.** Aligned Releases refers to `productRegistrationId`
   and `workspaceKey` constantly but does not own them. "What is a product registration" →
   Ops Center. "Assign this workspace to cohort 3" → Aligned Releases.

   **"Release Manager" is ALWAYS Aligned Releases.** It is the internal tool where Tyler staff
   author the features clients see, assign cohorts, and manage the feature lifecycle. The name
   invites two wrong guesses — that it is an Ops Center screen, or that "release manager" means
   a person's job title. Neither. Any question naming it, however phrased, goes to Aligned
   Releases. Same for "release management".

   Note the client-facing half lives in **Admin Center**, so a question about *what a client
   sees* about an upcoming release is still Aligned Releases even though Admin Center is
   normally a BP-General topic. Release Manager is internal; Admin Center is where clients see
   the result.

4a. **Disambiguating the broad keywords: "feature" and "release".** Both are Aligned Releases
   triggers and both appear constantly in unrelated questions, so use the sense, not the word:

   | Ask | Route |
   |---|---|
   | "What features does Ops Center have?" / "does this product support X?" | **not** Aligned Releases — product capability, so Ops Center or BP-General |
   | "How do I add a feature / take a feature GA / put it in public preview?" | Aligned Releases |
   | "When is the next release / which cohort activates when?" | Aligned Releases |
   | "How do I release my product to a new customer?" (licensing/activation) | Ops Center |

   The tell for Aligned Releases is the **release-train vocabulary** around the word —
   cohort, activation window, preview stage, GA date, Release Manager, release notes. Bare
   "feature" or "release" with none of that is usually somebody else's question.
5. **Ops Center vs Identity.** Ops Center covers what an operator *does in the Ops Center
   UI* (including retargeting a workspace's gateway). Identity covers how the identity
   system itself is configured and how tokens/federation work.

   **Technical and API questions about organizations, workspaces, licensing or availability go
   to Ops Center, not Identity** — including listing or searching them programmatically, where
   the answer is the **TCP Search API** (`Docusaurus-OpsCenterAdoption.md` → *Listing Ops
   Center Organizations and Workspaces*). Mentioning tokens or credentials for the call does
   **not** make it an Identity question: Identity owns how you authenticate, Ops Center owns
   what you call. Recorded after transcript `identity/2026-08-27--f4a25651`, where Identity
   answered "how do I get a list of workspaces for an organization using the api?" itself while
   the correct content sat indexed in the Ops Center corpus.
6. **Don't split one question across two agents.** Pick the owner of the user's actual
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
| `FAQ-` | **Authored here — no upstream source.** One per agent corpus. The home of record for answers that exist nowhere else: SME guidance given verbally, behaviour learned by observation, corrections an upstream owner has not yet made. Everything else in a corpus is re-derived from its source; these entries would be lost by that, so they live apart and carry their own provenance. |
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
