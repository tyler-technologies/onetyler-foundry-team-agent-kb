# START HERE — Routing Guide for the Aligned Releases Knowledge Corpus

This file is **the chatbot's first read** for the Aligned Releases domain. It is a **routing
guide**, not a tutorial: its job is to pick the right file and section before answering, and
to know what this corpus does not cover.

Domain: Aligned Releases — Tyler's single system of record for quarterly GA releases: the
feature lifecycle (Planned → Private Preview → Public Preview → GA), cohort-based rollout,
release documentation, and the Aligned Releases API.

Audience: Tyler product-team engineers and platform integrators building against the API,
plus product and release managers who need to understand the model.

> ⚠️ Blueprint marks the Aligned Releases **Overview** and **Integration Checklist** as
> *UNDER CONSTRUCTION*. Treat the concepts and API as current; when asked about the checklist,
> say it is incomplete upstream rather than inventing steps.

---

## File catalog at a glance

| File | One-liner — what's in it |
|---|---|
| `Docusaurus-AlignedReleases.md` | **The substance.** Glossary of the business objects, key concepts, the feature lifecycle with five worked scenarios, how to request API credentials (Identity Client ticket + the exact permission set), the integration guide end to end, the API reference, and the integration checklist. |
| `FAQ-AlignedReleases.md` | **Authored answers with no upstream source** — verbal SME guidance, observed behaviour, corrections upstream owners have not yet made. |

---

## The two things people get wrong

Lead with these; they cause most bad answers in this domain.

**1. You do not set a feature to General Availability.** There is a `GeneralAvailability`
state and a `PUT /feature/{id}/state/{state}` endpoint, so it looks settable — but every
feature assigned to a release is promoted to GA **in bulk** by the scheduled job when that
release's **cohort 1 window opens**. The way to take a feature GA is to **assign it to a
release**. Use `state/{state}` only for `Planned`, `Private`, `Public`.

**2. Deployment and activation are separate.** Product lines may deploy code at any time.
*Impactful features* are **activated** by cohort during a GA window. "Release" here means a
client-communication and activation event, not a deploy.

Two supporting distinctions worth stating early:

- **Feature vs Feature Flag** — a Feature is the client-facing unit with a lifecycle stage; a
  Feature Flag is the divisional technical control gating activation, 1:many with a Feature.
  Flags express targeting and rollout, not lifecycle.
- **Who creates what** — **releases and release cohorts are created by the internal OneTyler
  team.** Product-team integrators *query* for them.

---

## Common query → where to go

| The user asks… | Go to |
|---|---|
| "What is Aligned Releases / why does it exist?" | *What Problem Are We Solving* + *Key Concepts* |
| "What does *cohort* / *feature* / *release* / *version* mean?" | **Glossary** — the canonical definitions of every business object |
| "What are the release stages?" | *Feature lifecycle*, then the five **lifecycle scenarios** for non-linear cases |
| "How do I get API credentials?" | **Requesting API Access** — the Identity Client ticket, the exact field values, and the permission set |
| "Which environment / base URL?" | **Requesting API Access** → environments table (one client per environment) |
| "How do I create a feature / update it / query features?" | *Integration Guide* → the matching operation |
| "How do I put a feature in preview?" | *Change the Feature Stage* + *Activating Features Pre-release* |
| "How do I take a feature GA?" | **The GA warning section** — assign it to a release; do not set the state |
| "How do I assign a workspace to a cohort?" | *Assigning Customer Cohorts* |
| "What endpoints exist?" | *API Reference* |
| "Is there an SDK?" | `Tyler.AlignedReleases.Sdk` (C#, on Artifactory) — see *Requesting API Access* |
| "Which ticket do I file?" | `Knowledge-Shared/Conf-OneTylerTickets.md` — the authoritative catalog for every domain |
| Something no document states | `FAQ-AlignedReleases.md` |

---

## Disambiguation pairs

| Confusable | Which is which |
|---|---|
| **Release** vs **deploy** | A release is a named quarterly client-communication and activation window (Feb, May, Aug, Nov). Deploying code is unrelated and can happen any time. |
| **Release** vs **Release Notes** | The four named quarterly releases carry Release Documentation. *Release Notes* are for non-quarterly changes — minor fixes and lower-risk enhancements. |
| **Feature** vs **Feature Flag** | Client-facing unit with a lifecycle stage, vs the divisional technical control that gates it. 1:many. |
| **Cohort** vs **Preview** | Cohorts are the four GA rollout weeks and apply to **GA only**. Preview participation is separate, optional, and managed in divisional tooling. |
| **Public Preview** vs **GA** | Public Preview = selected/opted-in workspaces, limited support, **no SLA**. GA = all workspaces, full support, **with SLA**. |
| **Private** vs **Public Preview** | Private = specific workspaces, **no support, no SLA**. Public = available to all clients who opt in, limited support, no SLA. |
| **Version** vs **Release** | A workspace "versioned 2027.1" is one that has *activated* the first quarterly release of 2027. |

---

## Cross-domain pointers

- **Product registration, `productRegistrationId`, workspaces and `workspaceKey`** →
  `Knowledge-OpsCenter/` and `Knowledge-BP-General/Docusaurus-ProductSystemReg.md`. Aligned
  Releases uses these identifiers constantly but does not own them.
- **Identity Client credentials, CCF, scopes, tokens** → `Knowledge-TylerIdentity/`. This
  corpus tells you *which* client to request; Identity explains how CCF works.
- **Platform Service API conventions, auth in general** →
  `Knowledge-BP-General/Docusaurus-CloudPlatformAPI.md`.
- **The event-driven architecture AR uses to propagate state** →
  `Knowledge-BP-General/Docusaurus-ServiceArchitecture.md`.
- **Status pages and incident communication** → `Knowledge-StatusPages/` (scaffold).
- **SLAs and availability commitments** → `Knowledge-SLAs/` (scaffold). Note GA carries an
  SLA and preview stages do not — the *commitment* itself lives there.
- **Any ticket question** → `Knowledge-Shared/Conf-OneTylerTickets.md`.

---

## What this corpus does NOT cover

- **Feature-flag implementation.** Flags are owned by divisional product groups; AR only
  references them. Flag tooling and targeting are out of scope.
- **Deployment pipelines, Harness, CI/CD** → `Knowledge-BP-General/Docusaurus-DevOps.md`.
- **The client-facing UI of the AR applications.** This corpus documents the model and the
  API, not screen-by-screen navigation.
- **The Integration Checklist detail** — upstream is still a placeholder.
- **Anything newer than the source pull.** Derived from the Blueprint repo at
  `docs/aligned-releases` on **2026-08-23**. For anything time-sensitive prefer the live page
  and say the file may be behind.

---

## Naming convention legend

| Prefix | Source | Authority |
|---|---|---|
| `Docusaurus-` | Tyler Blueprint (`docs.tylerdev.io`) | Published source of truth; re-derived when Blueprint changes |
| `FAQ-` | **Authored here, no upstream source** | Home of record for answers that exist nowhere else. Carries `Source` / `Added` / `Confidence` / `Promote when` per entry |

---

## Operating principles for the chatbot

1. **Never tell anyone to set a feature to `GeneralAvailability`.** Assigning it to a release
   is what takes it GA.
2. **Never invent an endpoint or a permission.** Both are enumerated in the reference; if
   something is not listed, say so.
3. **Never invent a ticket URL** — use the shared ticket catalog.
4. **Say which environment you mean.** Base URLs and Identity Clients are per-environment and
   not interchangeable.
5. **Distinguish deploy from activate** whenever timing comes up.
6. **Flag the under-construction sections** rather than filling the gap.
7. Hand off when the question is really about product registration, identity, or deployment.

---

## Index hygiene

Update this file whenever a file is added, renamed or removed from this folder, and whenever
`Docusaurus-AlignedReleases.md` is re-derived — check the routing tables above still match its
headings. A stale start page actively misleads the agent.
