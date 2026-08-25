# FAQ — Blueprint General

Source: **authored in this repo — no upstream document.** Every other file in this folder is
derived from Tyler Blueprint (`docs.tylerdev.io`) and is re-derived when Blueprint changes.
This file is the **home of record** for answers that exist nowhere else.

Domain: Blueprint General — platform orientation, client and ops applications, the TCP/TID
API catalog, service architecture, DevOps, platform security, Aligned Releases, Status Page
and SLA.
Audience: Tyler product engineering, platform engineering and operational staff.

**Companion:** `_START_HERE.md` for routing, including when to hand off to a specialized
agent. For "which ticket do I file", use `Knowledge-Shared/Conf-OneTylerTickets.md`.

---

## What belongs here

- Answers given verbally by a subject-matter expert that are not written down anywhere.
- Behaviour learned by observation or testing that no document describes.
- Corrections to a Blueprint page the owner has not yet fixed.
- Cross-cutting platform questions that no single Blueprint page answers.
- Recurring questions from real transcripts whose answer had to be assembled from scratch.

## What does NOT belong here

- Anything already on Blueprint — it belongs in the matching `Docusaurus-` file, so it is
  re-derived when Blueprint changes.
- Anything owned by a specialized agent (Ops Center, Support Access Center, Identity). Hand
  off instead — see `_START_HERE.md`.
- Ticket forms — `Knowledge-Shared/Conf-OneTylerTickets.md`.
- Glossary definitions — `Docusaurus-PlatformOverview.md` carries the Blueprint glossary.
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

### Q: Where do I post a product registration question?

**A:** **Two different Teams channels, split by whether the question is functional or
technical.** Sending a technical problem to the functional channel is the common mistake.

**Functional questions** — what registration is, whether you need it, how the model works,
approvals and policy. For example *"I want to register a new product"*, *"Why should I
register my product?"*, *"Do I need a second registration for this module?"*
→ **Product Registration Community**:
<https://teams.microsoft.com/l/channel/19%3AoVLpzEarOxFx-RwQc70RhkOA0xXbUS6R52LrTWKhIMQ1%40thread.tacv2/Product%20Registration%20Community?groupId=d9db441d-35fa-433c-8fe0-ff7fe5825d3c&tenantId=7cc5f0f9-ee5b-4106-a62d-1b9f7be46118&ngc=true&allowXTenantAccess=true>

**Technical questions** — something is broken, out of sync, not deploying, or behaving
unexpectedly. For example *"Our registration details are out of sync with the repo"*, a
pipeline that will not deploy a catalog change, Ops Center showing different JSON from the
YAML in `tcp-product-catalog`.
→ **Cloud Platform Community**:
<https://teams.microsoft.com/l/channel/19%3A1e6bcc02bd3242a193bf9171a51a0395%40thread.tacv2/Cloud%20Platform%20Community?groupId=d9db441d-35fa-433c-8fe0-ff7fe5825d3c&tenantId=7cc5f0f9-ee5b-4106-a62d-1b9f7be46118>

**This corrects an over-generalization in this corpus.**
`Docusaurus-ProductSystemReg.md` names the Product Registration Community channel as "the
correct escalation path for complex registration questions" without qualification, so a
technical problem gets routed there. Use the split above instead. Answering the substance of
the question first is still right — for a sync problem, `tcp-product-catalog` is the
authoritative source and the YAML in `master` should match the JSON in Ops Center Registration
Details — but the escalation pointer should be the Cloud Platform Community channel.

- **Source:** Vijay Venkataraman, reviewing transcript `team/2026-08-24--6d720e8a`, where
  "our tdsm registration details are out of sync with the repo" — a technical question — was
  answered correctly on substance but pointed at the functional channel.
- **Added:** 2026-08-25 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** Blueprint's product-registration pages state which channel serves which
  kind of question. At that point this entry should be replaced by the re-derived
  `Docusaurus-ProductSystemReg.md` content, and note 8 in that file's *Notes for the chatbot*
  corrected at the same time.

---

## Notes for the chatbot

- Entries here have **no upstream document**. State them plainly, but if challenged, say the
  answer comes from internal Tyler subject-matter guidance rather than published docs.
- An entry marked **provisional** has not been confirmed by an owner. Hedge accordingly.
- This file is **thin, not authoritative on everything**. Its presence is not evidence that a
  question has been considered — if there is no entry for it here, fall back to the
  `Docusaurus-` files.
- Where an entry says it **corrects** a `Docusaurus-` file in this folder, the entry wins.
  That is the one case where this file overrides a derived source, and the entry states it
  explicitly under *Source*.
