# FAQ — Aligned Releases

Source: **authored in this repo — no upstream document.** Files derived from an upstream
source are re-derived when that source changes, which would silently delete anything added to
them by hand. This file is the **home of record** for Aligned Releases answers that exist nowhere else.

Domain: Tyler Aligned Releases — the coordinated release program: release trains and cadence, version alignment across products, release status lifecycle, and the Aligned Releases API.
Audience: Tyler product managers, release managers, and product engineering teams coordinating a release.

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

All of the entries below come from one source: the **Release Manager Tool Walkthrough**
recording, a ~40-minute internal session presented by **Kyle Hall** and **Nate Hanna** with
questions from divisional release/product staff. Each entry is a question someone actually
asked, phrased the way they asked it, with the answer the presenters gave.

Several are "no, that does not exist" answers to enhancement requests. Those are kept
deliberately — without them the agent invents capabilities, which is worse than admitting a
gap.

**Timeline context for every entry:** at the time of the recording the 2027 releases were
loaded, the spring 2027 activation dates were 4 / 11 / 18 / 25 February, and a November pilot
was being prepared. The client-facing Admin Center view was still being built.

### Q: If I set a feature's stage to Private or Public Preview, what is that actually controlling?

**A:** **Nothing about activation. Feature stage and activation are independent states, by
design.**

- **Feature (lifecycle) stage** — `Planned`, `Private Preview`, `Public Preview`, `GA` — is a
  **communication and awareness signal**. It tells users of Aligned Releases where the feature
  sits in its release lifecycle, for the benefit of Support, Client Success, customers and
  anyone else who needs to know what is coming. That is all it does.
- **Activation** — whether the feature is actually switched on — is tracked **at the workspace
  level** and is a separate thing entirely.

**Aligned Releases does not orchestrate or control the underlying feature flag.** That belongs
to the product team. The product team activates the feature through their own feature-flag
platform, then **reflects that activation state back into Release Manager** — either by hand or
through the optional API integration.

So setting a stage does not turn anything on, and turning something on does not move the stage.

**In one line:** *feature stage = lifecycle/communication status; activation = whether it is
actually on for a workspace.*

**The one exception, and it is still not activation.** Setting a feature to **Public Preview**
does have a customer-facing effect: it makes the feature visible in the **Admin Center**
experience, where customers can indicate that they are interested in opting in early. Even
then, **Tyler or the product team performs the actual activation** — the customer is raising a
hand, not enabling anything. (The Admin Center experience was still being built when this was
recorded.)

**Why this is worth being careful about.** The stage names describe audiences, so they read like
switches — "Public Preview" sounds like it exposes the feature to the public, and "GA" sounds
like it turns it on for everyone. `Docusaurus-AlignedReleases.md`'s *Feature Lifecycle* table
reinforces that reading with an "Audience" column ("GA — All clients by cohort assignment"),
which describes **who the stage is communicating about**, not who has it switched on. Read
literally as activation, it is wrong.

A feature can sit at `GA` with no workspace activated, and a feature can be live in a workspace
while its stage still says `Planned`. Neither is a bug.

- **Source:** Nate Hanna, 2026-08-27, answering "to me 'stage' comes across as a feature
  activation stage per cohort and not a feature level setting — if I set it to Private or Public
  Preview what is it really controlling?" Consistent with Kyle Hall's Release Manager
  walkthrough on the Public Preview / Admin Center behaviour.
- **Added:** 2026-08-27 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** Blueprint states the stage/activation independence explicitly. The closest
  existing statement is in `Docusaurus-AlignedReleases.md` — "AR provides visibility but does
  not drive preview activation" — which is narrower: it covers preview only, and does not say
  that stage never drives activation, that activation is tracked per workspace, or that the
  product team owns the flag and reports back.

### Q: Does the documentation link have to be added per feature, or can I add it once per release?

**A:** **Per feature.** If every feature in your release points at the same release-notes URL,
you copy that link onto each one. There is no per-release or per-product link.

Two reasons the presenters gave, and the second is the load-bearing one:

1. Clients are expected to arrive at a *specific feature* rather than backing out to the full
   release detail, so each feature has to be self-describing.
2. **A feature can reach clients outside the context of a release.** Any feature can be put
   into private or public preview independently of the release schedule, so its description
   and documentation must stand alone — there may be no release for it to inherit a link from.

Nate Hanna acknowledged the repetition and judged copy-paste acceptable. The requirement is a
core Aligned Releases rule: every feature carries documentation or release communication.

- **Source:** Release Manager Tool Walkthrough recording — question from a divisional release
  lead; answered by Nate Hanna and Kyle Hall.
- **Added:** 2026-08-26 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** Blueprint documents the per-feature documentation requirement and the
  preview-independent-of-release rationale.

### Q: Cohorts look like they are assigned per client. If I have 400 clients, do I really have to do that for every release?

**A:** **No — the assignment is durable, not per-release.** This is the most common
misunderstanding about cohorts. Assign a client's workspace to a cohort once and it stays
there until someone changes it. You do not re-add clients each release.

Two other things that make the number smaller than it looks:

- **Participation is opt-in.** You are not expected to enrol all 400 clients in the spring
  window — the presenters suggested starting with something like 1–10. Whether it ever flips
  to opt-out has explicitly **not** been decided.
- **There is a bulk API.** The UI is intended for ongoing modifications, not initial loading.
  Kyle Hall offered to help put together a script for a large batch; ask rather than clicking
  400 times.

Changes after that are expected to be exceptions — a client raising a support ticket to move
environments, for example. A typical shape is test workspaces in cohort 1 and production in
cohort 3 or 4, so the client sees features in test before production.

- **Source:** Release Manager Tool Walkthrough recording — question from a divisional release
  lead; answered by Nate Hanna and Kyle Hall.
- **Added:** 2026-08-26 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** Blueprint states that cohort assignment persists across releases. Note
  `Docusaurus-AlignedReleases.md` covers the cohort *API* in depth but not this policy.

### Q: Does the feature name have to match a code artifact? Does it matter if I misspell it?

**A:** **No, and no.** The feature name and description are **client-facing communication**,
not a technical identifier. Misspelling it has no technical effect — you would just be
showing clients a typo.

The presenters called this a feature of the model rather than a gap, and it is the part people
find hardest to accept: **one feature as a client understands it may be delivered by dozens of
feature flags.** An ERP change spanning several modules might have a different technical
implementation per team, yet it is one item of value to the client, so it is one feature in
Release Manager.

The system generates a separate **feature ID** as the permanent unique identifier — numeric at
the time of the recording, visible in the feature's URL, not shown on the add-feature form.
Use that, not the name, to correlate with anything technical.

- **Source:** Release Manager Tool Walkthrough recording — question from a divisional
  engineering lead; answered by Kyle Hall and Nate Hanna.
- **Added:** 2026-08-26 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** Blueprint states plainly that a feature is a client-communication object
  and may span many feature flags.

### Q: Can I use a human-readable tag instead of a numeric feature ID to correlate with my feature flags?

**A:** **Not in Release Manager — do the correlation on your feature-flag platform instead.**
Release Manager gives you a numeric feature ID (e.g. `28`). The recommended pattern is to
attach that ID as one tag on your flag in Harness Splits or LaunchDarkly, alongside whatever
human-readable metadata your own reporting needs. Those platforms support multiple tags or
segments per flag.

This was raised as an enhancement request — a human-readable identifier being easier to debug,
monitor and correlate than a number or GUID — and was noted for follow-up rather than
accepted. Do not describe a human-readable Release Manager tag as available.

- **Source:** Release Manager Tool Walkthrough recording — enhancement request from a
  divisional engineering lead; answered by Nate Hanna ("noted, we can take that offline").
- **Added:** 2026-08-26 by vijay-tylertech
- **Confidence:** confirmed by owner — accurate as of the recording; the enhancement was
  taken away for discussion, so re-check before repeating the "not available" part.
- **Promote when:** a decision is made on human-readable feature identifiers.

### Q: Is Release Manager access all-or-nothing, or can it be restricted?

**A:** **Three levels, and the granularity is per product, not per module.**

| Level | Scope |
|---|---|
| Read | Any onboarded Tyler employee can read **everything**. None of this data is considered sensitive. Access still has to be requested — being a Tyler employee does not put you in the system automatically. |
| Edit features | Per product: change feature titles and descriptions, but not create features. Intended for marketing, sales and customer-success staff who review the client-facing language. |
| Edit and create features | Per product: the product/development role. Also the level that can assign cohorts. |

There is no per-module permission breakdown. You get edit rights on the products you work on —
a Citizen Connect product manager cannot add features to Enterprise ERP.

- **Source:** Release Manager Tool Walkthrough recording — question from a divisional lead;
  answered by Kyle Hall with a correction from Nate Hanna about onboarding being required for
  read access.
- **Added:** 2026-08-26 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** Blueprint documents the Release Manager permission model.

### Q: Can we lock down who is allowed to assign cohorts?

**A:** **Not separately — cohort assignment is bundled with the create-features permission.**
Anyone who can add features to a product can also change that product's cohort assignments.
There is no distinct cohort-assignment role.

The compensating control is the **audit tab**, present on every product: it records who
changed what and when, so an unexpected cohort change can be traced and discussed. Both
presenters invited feedback if finer-grained control turns out to be needed, so this may
change.

- **Source:** Release Manager Tool Walkthrough recording — question from a divisional lead;
  answered by Kyle Hall, with Nate Hanna pointing at the audit tab.
- **Added:** 2026-08-26 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** a separate cohort permission is introduced, or Blueprint documents the
  bundling.

### Q: When do clients get emailed, and does the timing depend on their cohort?

**A:** **The first email does not depend on cohort — everyone gets it four weeks before the
cohort 1 date.** This was explicitly asked and corrected during the walkthrough: it is *not*
four weeks before each client's own cohort date.

The cadence per quarterly release:

| When | Email |
|---|---|
| 4 weeks before the **cohort 1** date | "Your next quarterly release is coming" — sent to all participating clients regardless of cohort. Links to Admin Center rather than carrying detail. |
| The day before **each** activation window where the client has an eligible workspace | "This workspace is going to be upgraded tomorrow" |

**Maximum five emails per quarterly release** — the four-week notice plus up to four
day-before notices, if a client has workspaces in all four cohorts.

Emails go to the **org admins as identified in Admin Center**. Separately, an
Aligned-Releases-wide message from marketing and communications was being prepared to precede
the first window so clients know to expect these.

- **Source:** Release Manager Tool Walkthrough recording — Kyle Hall, with Nate Hanna
  clarifying the recipients and the cohort-independence of the first email.
- **Added:** 2026-08-26 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** the notification schedule is published. Verify before repeating: the
  Admin Center screens the emails link to were still being built.

### Q: Where do clients actually see this? Is Release Manager client-facing?

**A:** **No. Release Manager is internal only; clients see this in Admin Center.** Tyler staff
author features and manage cohorts in Release Manager, and that feeds the client-facing view.

In Admin Center a client is intended to see their workspaces and environments, the features
coming, the dates each environment will be activated, and the documentation links. Clients
also see a **preview features** section listing features in public preview for products they
own, where they can express interest in enabling one early — the opt-in itself still goes
through Tyler.

Note for the chatbot: at the time of the recording these Admin Center screens were **still
being built**, and the presenters flagged that many clients had never used Admin Center at
all. Do not describe the client experience as finished.

- **Source:** Release Manager Tool Walkthrough recording — Kyle Hall, confirmed back by a
  divisional release lead ("this is the internal tool, this feeds into Admin Center").
- **Added:** 2026-08-26 by vijay-tylertech
- **Confidence:** confirmed by owner — but the Admin Center side was in progress; re-check.
- **Promote when:** the Admin Center Aligned Releases view ships and is documented.

### Q: Can I bulk-import features from JIRA or a spreadsheet?

**A:** **Yes, via the API — not through the UI.** There is no file-import button. Everything
the UI does is available over the API: cohort assignment, feature creation, associating
features with releases. Some product teams never open the UI at all and auto-create features
from JIRA tags.

**One strong caution from the presenters:** JIRA tickets are not written in client-facing
language. An automated JIRA-to-Release-Manager pipeline will push developer phrasing in front
of clients, so keep a human review step on the wording.

Also worth knowing: **not every feature belongs here.** The expectation is significant or
impactful features — the bare minimum, in Nate Hanna's words. You may list more, but the
system is not meant to mirror every change.

- **Source:** Release Manager Tool Walkthrough recording — request from a divisional release
  lead; answered by Nate Hanna and Kyle Hall.
- **Added:** 2026-08-26 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** `Docusaurus-AlignedReleases.md` covers the API surface — if it gains the
  "which features belong here" guidance and the client-language caution, move those there.

### Q: Can I add a screenshot or GIF to a feature description?

**A:** **No.** Feature name, description, module and documentation link are the available
fields; there is no image or media support. This was raised as an enhancement request and
called reasonable, but it does not exist. Point clients at the documentation link for
anything visual.

- **Source:** Release Manager Tool Walkthrough recording — enhancement request from a
  divisional lead; answered by Kyle Hall.
- **Added:** 2026-08-26 by vijay-tylertech
- **Confidence:** confirmed by owner — accurate as of the recording.
- **Promote when:** media support is added or formally declined.

### Q: Can an account manager see just their own clients?

**A:** **Not in Release Manager.** The organizations list is not filterable to a personal
portfolio, and there is no favouriting. This was raised as an enhancement request and
acknowledged as an interesting idea, not a commitment.

Two existing routes to something similar:

- Customer-success staff already using **Admin Center** get a per-client view there.
- All the underlying Release Manager data is being pumped to **Tyler Data Store** with an
  **interactive reporting** interface, where someone can build their own portfolio view. The
  presenters were explicit that they do not intend to build robust reporting into Release
  Manager itself — reporting belongs in that reporting layer.

- **Source:** Release Manager Tool Walkthrough recording — enhancement request from a
  divisional lead; answered by Kyle Hall and Nate Hanna.
- **Added:** 2026-08-26 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** the interactive reporting environment ships and is documented.

### Q: Where does the organizations list come from?

**A:** **From CRM, filtered to active contracts.** It is a subset of CRM client IDs, called
**orgs** in the platform's own vocabulary. So a client missing from Release Manager is usually
a CRM contract question, not a Release Manager one.

This connects to two other things the walkthrough covered: the **product registration** list
(the central source of truth for what Tyler offers — 156 registered products at the time,
which many people know as Ops Center registration), and **product licensing**, managed in the
CTO's office, which maps which clients have which products. Cohort assignment sits on top of
that licensing data.

- **Source:** Release Manager Tool Walkthrough recording — Nate Hanna, prompted by a question
  about the orgs list.
- **Added:** 2026-08-26 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** Blueprint documents the CRM-to-org relationship. See also the Ops Center
  corpus for product registration.

### Q: What are modules, "requires setup", and capability sharing for?

**A:** Three descriptive fields on a feature, none of them technical. All three exist to shape
what the client reads.

- **Modules** are **tagging**, so features can be grouped in client-facing release notes.
  Enterprise ERP is registered as a single product, but clients want to know whether a feature
  is financials, HR or utilities. Naming modules is a **communication exercise, not a technical
  one** — expect internal discussion about how to describe them to clients.
- **Requires setup** flags whether a feature turns on automatically or needs configuration
  first. The client-facing view groups features by module and separates them on this flag.
- **Capability sharing** lets one product publish a feature as shareable so another product
  team can pull down its language and documentation link as a starting point. Intended for
  products clients experience as components rather than separate purchases — Tyler Content
  Manager, Tyler Interactive Reporting, Tyler Identity. Example given: Content Manager
  publishes a feature; Enterprise ERP pulls it into its own client communication when ERP
  makes it available.

- **Source:** Release Manager Tool Walkthrough recording — Kyle Hall.
- **Added:** 2026-08-26 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** Blueprint documents these three fields. `Docusaurus-AlignedReleases.md`
  mentions modules in the API context but not their communication purpose, and covers neither
  "requires setup" nor capability sharing.

---

## Notes for the chatbot

- Entries here have **no upstream document**. State them plainly, but if challenged, say the
  answer comes from internal Tyler subject-matter guidance rather than published docs.
- An entry marked **provisional** has not been confirmed by an owner. Hedge accordingly.
- Every entry currently here comes from **one** source: the Release Manager Tool Walkthrough
  recording. It is strong on the Release Manager UI, the permission model, client notification
  and policy, and weak on everything else in Aligned Releases. Absence of an entry is not
  evidence a question has been considered — fall back to `Docusaurus-AlignedReleases.md`,
  which is far deeper on the API and integration mechanics.
- **Several answers describe work in progress** as of that recording: the client-facing Admin
  Center view, the interactive reporting environment, and marketing communications were all
  unfinished, and the opt-in-to-opt-out question was undecided. Where an entry says so, say so
  — do not present those as shipped.
- **The "no, that does not exist" answers are load-bearing.** They are recorded precisely so
  the agent does not invent screenshot support, human-readable feature tags, a personal
  portfolio view, or a per-cohort permission. If asked for one of those, say it is not
  available and give the workaround in the entry.
