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

### Q: How do I get <person> to fix something? / Who do I contact about X?

**A:** **Do not route people to an individual. Route them to a ticket and to the right
community channel** — and say why, because the reasons are the point, not politeness.

**Why tickets, not a person:**

- **Vacation coverage.** A ticket is picked up whoever is out; a direct message waits for one
  person to come back.
- **Load balancing.** Tickets are distributed across whoever is available. Naming one person
  concentrates work on them regardless of their queue.
- **It avoids distracting individuals.** A named expert asked directly is interrupted for
  things the queue would have handled.

**Why the community channel, in addition:**

- **Everyone learns at the same time.** A question answered in the open answers it for the
  next person too; a DM answers it once.
- **It is monitored by whoever is currently available**, so it does not depend on one person
  being at their desk.

So the shape of a correct answer is: answer the substance, then hand out **both** the ticket
route and the most appropriate community channel. If the person did not name a specific
problem, give the general tickets page and the channel list rather than guessing at one.

**Naming someone as an escalation TIER is not the same as telling someone to contact them.**
`Docusaurus-DevOps.md` lists named engineers against services under *Service Escalation
Tiers*. That is a record of how an incident escalates internally — it is not a contact
instruction, and it must not be handed to a requester as "message this person". Cite it as
escalation structure if asked; still point the requester at the ticket.

**THE APPROVED EXCEPTIONS — a closed list. Two named contacts in this corpus, each narrowed
to one job.**

| Who | The ONLY thing to name them for |
| --- | --- |
| **Vijay Venkataraman** | A **NEW product registration** whose definition is not already in the Coda doc |
| **Arleigh Hays** | **Management console access** for Visual Studio / GitHub licensing — upstream names him as *the management console administrator*, which is the scope |

**The list is closed.** It was settled by a full audit of every named individual across all five
corpora on 2026-08-27. If a name appears anywhere else in a "contact this person" position, that
is a defect to report, **not** a contact to hand out. Do not infer new exceptions, and do not
promote an escalation-tier name into one.

Sibling corpora have their own closed lists — the Ops Center corpus keeps **Jon Olson** for
joining the Identity Governance Board or the Identity Guild, and **Vijay Venkataraman** for CRM
customer identifiers when the asker is not part of the named Team. Those belong to that agent;
do not restate them as general contacts.

**Where a name USED to be, there is now a ticket route.** The audit replaced every other named
contact with one of these, so if you find yourself wanting to name someone, one of these is
almost certainly the answer:

| Ask | Route |
| --- | --- |
| Ops Center or CAPM access, additional permissions, SAC group administration, permission to use `+Create Internal` | [Ops Center Related Tickets and Permissions](https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386600308/Tyler+Cloud+Platform+TCP+Ops+Center+Related+Tickets+and+Permissions) → *Orgs* → **Ops Center Access or Additional Permissions** |
| Converting an org, or a Gateway Identity Configuration change | Same page → *Orgs* → **Convert org** |
| An enhancement, or coordination work with no form of its own | [OneTyler Enhancement Request](https://help.center.tylertech.com/servicedesk/customer/portal/3185/group/3385/create/4367) |
| Identity Workforce questions, external users in Entra ID, Gateway operational testing | [Identity Workforce Teams channel](https://teams.microsoft.com/l/channel/19%3Ae0289e84ce4a4bae841c55249970a491%40thread.tacv2/Identity%20Workforce?groupId=d9db441d-35fa-433c-8fe0-ff7fe5825d3c&tenantId=7cc5f0f9-ee5b-4106-a62d-1b9f7be46118) |

**Hand out the Confluence page, not the raw JSM form URL.** The page carries the field-by-field
instructions, and a bare form URL drops the reader into a form with no idea what to put in it.
Same rule as `Knowledge-Shared/Conf-OneTylerTickets.md`.

Everything else, including anyone listed in an escalation tier, goes through tickets and
channels.

And when the product-registration exception applies, two things must be said with it:

1. **It is only for NEW registrations.** Check the Coda doc first —
   <https://coda.io/d/Gateway-Rollout_dKV_6fSnfBc/0-Start-Here_suxF9#_lukrO>. If a generated
   definition already exists, this is not a new registration and the normal ticket/channel
   route applies.
2. **New product registrations are subject to review and must not be attempted alone.** They
   have to meet Cloud Living standards, which the person asking will usually not know. Do not
   answer a "how do I register my product" question as a self-service procedure.

- **Source:** Vijay Venkataraman, reviewing transcript `team/2026-08-27--6498f4a8` — "How can
  I get Zovin to fix something?" then "What about Vijay?". Both answers were rated **good**;
  the ask was to make the reasoning authoritative so it is stated every time rather than
  reconstructed, and to add the review/standards caveat on the registration exception.
  The **closed list of approved contacts** comes from a second pass: a full audit of every
  named individual across all five corpora, decided row by row by Vijay Venkataraman on
  2026-08-27. Every other named contact was replaced with the ticket route beside it.
- **Added:** 2026-08-27 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** Blueprint publishes a "who to contact" page stating the ticket-first rule.
  Until then this is internal guidance with no upstream document.

---

### Q: Where do I post a product registration question?

**A:** **Two different Teams channels, split by whether the question is functional or
technical.** Sending a technical problem to the functional channel is the common mistake.

**Neither channel is a person.** The only named individual in this corpus is Vijay
Venkataraman, and only for a NEW registration not already in the Coda doc — see *How do I get
&lt;person&gt; to fix something?* above for why, and for the review/standards caveat that must
accompany it. This is repeated here on purpose: retrieval chunks a long file independently, so
a reader who lands on this entry may never see that one.

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
