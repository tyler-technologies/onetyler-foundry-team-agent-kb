# START HERE — Routing Guide for the Status Page & SLA Knowledge Corpus

This file is **the chatbot's first read** for the Status Page and SLA domain. It is a
**routing guide**, not a tutorial.

Domain: Status Pages and SLAs — service-status communication (incident lifecycle, component
modelling, subscriptions) and service level agreements (availability commitments, how uptime
is measured, exclusions, remedies).

Audience: Tyler operations, support, product and communications staff.

> ⛔ **SCAFFOLD — no content, no agent, no Foundry collection.** As of **2026-08-23** the
> upstream Blueprint source is **seven stub pages** ("This is a stub, content coming soon"),
> 63 lines in total. There is nothing to distil yet.
>
> Until that changes, these questions are answered by the **General Blueprint Docs Agent**
> from `Knowledge-BP-General/Docusaurus-StatusPageAndSLA.md`, which is currently the best
> content that exists anywhere — it carries a glossary and concept descriptions and labels
> each live upstream page as a stub.

---

## Why one corpus and not two

Status Pages and SLAs are separate ideas — a status page reports **what happened**, an SLA
states **what was promised** — but they are two halves of one conversation, they share a
single upstream Blueprint section (`docs/status-page-and-sla`), and neither has enough
material to support an agent alone. They get one corpus and, eventually, one agent.

Keep the distinction sharp inside the corpus even so:

| | Status Page | SLA |
|---|---|---|
| Answers | "Is it down? What happened? When will it be fixed?" | "What were we obliged to deliver? Do we owe a credit?" |
| Nature | Operational, real-time, public-facing | Contractual, retrospective, commercial |
| Typical asker | Support, ops, a customer mid-incident | Product, sales support, a customer after the fact |

---

## File catalog at a glance

| File | One-liner — what's in it |
|---|---|
| `FAQ-StatusPageAndSLA.md` | **Authored answers with no upstream source.** Empty of entries today. |

_No distilled source files yet — the upstream is all stubs._

---

## Scope — what will belong here

**Status Page:** which page serves which audience and its URL · incident lifecycle (open,
update, resolve, post-incident) · how components and services are modelled · subscriptions
and notification channels · who may post, and the expected tone and cadence of updates.

**SLA:** availability commitments per product or tier · how uptime is measured, over what
window, and what counts as downtime · exclusions (planned maintenance, customer-caused,
third-party) · remedies and service credits, and how a customer claims one · which
commitments are contractual versus aspirational.

## What does NOT belong here

- **Incident *response* runbooks, P1 process, on-call** →
  `Knowledge-BP-General/Docusaurus-DevOps.md`. This corpus is about *communicating* an
  incident, not resolving one.
- **DR objectives (RPO/RTO) and failover mechanics** → `Knowledge-BP-General/`.
- **Release and maintenance-window announcements** → `Knowledge-AlignedReleases/`.
- **Support response-time expectations for staff access** →
  `Knowledge-SupportAccessCenter/`.
- **Contract negotiation.** Record what the standard commitment *is*; never state or imply a
  bespoke commitment for a named customer.
- Ticket questions → `Knowledge-Shared/Conf-OneTylerTickets.md`.

---

## ⚠️ Care required: SLA answers read as commitments

An SLA answer can be taken as a contractual statement about what Tyler owes a customer. So:

- Never quote an availability figure that is not in a distilled file or a confirmed FAQ entry.
- Never infer a commitment from an observed uptime number.
- Never state a bespoke commitment for a named customer — those live in contracts, not here.
- If an entry is marked `provisional`, hedge explicitly.

---

## Becoming a real corpus

Readiness is checked automatically — `python3 scripts/check_freshness.py` reports whether the
upstream source has grown past the stub stage (source id `status-page-and-sla-blueprint`).

When it reports **READY**, follow this order. Doing it out of order removes content from a
live agent with nowhere for it to go:

1. **Distil** the upstream into `Docusaurus-*.md` files here, splitting Status Page from SLA
   if the material supports it.
2. **Create the Foundry agent** and its `OT-StatusPageAndSLA` collection.
3. **Record the IDs** in the *Constants* table in `CLAUDE.md` and the team-composition table
   in `README.md`.
4. **Add the routing block** for this domain to `team-config/team-routing-prompt.md`, push it
   to Foundry, and verify — plus a team sample prompt above "I need help with other topics".
5. **Upload** the new files, then **move** `Docusaurus-StatusPageAndSLA.md` out of
   `Knowledge-BP-General/` — upload here first, delete from `OT-BPD` second, and re-upload
   BP-General's start page with its catalog row removed.
6. **Rewrite this file** — drop the scaffold warning, fill in the catalog, add a
   *Common query → file* table.

---

## Operating principles for the chatbot

1. While this corpus is empty, **do not treat its existence as evidence** that a question has
   been considered. Fall back to `Knowledge-BP-General/Docusaurus-StatusPageAndSLA.md`.
2. Say plainly that the upstream documentation is still under construction rather than
   filling gaps from model priors. This is a domain where a confident invented answer is
   actively harmful.
3. Keep the status-page/SLA distinction explicit when a question straddles both.

---

## Index hygiene

Update this file when a file is added here, and rewrite it entirely when this corpus
graduates. Also update `README.md` if team-level routing changes.
