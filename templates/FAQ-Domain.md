# FAQ — {{NAME}}

Source: **authored in this repo — no upstream document.** Files derived from an upstream
source are re-derived when that source changes, which would silently delete anything added to
them by hand. This file is the **home of record** for {{NAME}} answers that exist nowhere else.

Domain: {{DOMAIN}}
Audience: {{AUDIENCE}}

**Companion:** `_START_HERE.md` for routing across this corpus. For "which ticket do I file",
use `Knowledge-Shared/Conf-OneTylerTickets.md`.

---

## What belongs here

- Answers given verbally by a subject-matter expert that are not written down anywhere.
- Behaviour learned by observation or testing that no document describes.
- Corrections to an upstream source the owner has not yet fixed.
- Recurring questions from real transcripts whose answer had to be assembled from scratch.

## What does NOT belong here

- Anything already in an upstream source — put it in the file for that source, so it is
  re-derived when the source changes.
- Ticket forms and permissions — `Knowledge-Shared/Conf-OneTylerTickets.md`.
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

Keep entries self-contained — retrievers chunk independently of headings, so an entry that
only makes sense after reading the one above it will retrieve badly.

---

## Entries

_No entries yet._

This file is deliberately empty of content. It exists so the next {{NAME}} answer with no
upstream source has an obvious home, instead of being wedged into a derived file where the
next reconciliation would delete it.

{{Good first candidates, once someone confirms them: …}}

---

## Notes for the chatbot

- Entries here have **no upstream document**. State them plainly, but if challenged, say the
  answer comes from internal Tyler subject-matter guidance rather than published docs.
- An entry marked **provisional** has not been confirmed by an owner. Hedge accordingly.
- While this file has no entries, it carries no answers — do not treat its presence as
  evidence that a question has been considered.
