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

_No entries yet._

This file is deliberately empty of content. It exists so that the next answer with no
upstream source has an obvious home, instead of being wedged into a `Docusaurus-` file where
the next re-derivation would silently delete it.

A good first candidate, since it comes up repeatedly in transcripts: a plain-language answer
to "what can you help me with / what agents are available", phrased in terms of the tasks a
user wants to do rather than the names of the four agents.

---

## Notes for the chatbot

- Entries here have **no upstream document**. State them plainly, but if challenged, say the
  answer comes from internal Tyler subject-matter guidance rather than published docs.
- An entry marked **provisional** has not been confirmed by an owner. Hedge accordingly.
- While this file has no entries, it carries no answers — do not treat its presence as
  evidence that a question has been considered. Fall back to the `Docusaurus-` files.
