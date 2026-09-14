# FAQ — Ops Center

Source: **authored in this repo — no upstream document.** Every other file in this folder is
distilled from something external (Confluence, Blueprint, training, GitHub) and is
re-derived when that source changes. This file is the opposite: it is the **home of record**
for answers that exist nowhere else.

Domain: Ops Center
Audience: Tyler product, deployment, implementation and operational staff.

**Companion:** `_START_HERE.md` for routing across this corpus. For "which ticket do I file",
use `Knowledge-Shared/Conf-OneTylerTickets.md` — not this file.

---

## What belongs here

- Answers given verbally by a subject-matter expert that are not written down anywhere.
- Behaviour learned by observation or testing that no document describes.
- Corrections to an upstream source that the source owner has not yet fixed.
- Disambiguation and phrasing guidance the agent needs but no doc states.
- Recurring questions from real transcripts whose answer had to be assembled from scratch.

## What does NOT belong here

- Anything already in an upstream source — put it in the file for that source, so it is
  re-derived when the source changes.
- Ticket forms and permissions — `Knowledge-Shared/Conf-OneTylerTickets.md`.
- Glossary definitions — `Docusaurus-Terminology.md` is the canonical glossary.
- Speculation. If nobody has confirmed it, do not write it here; the agent will state it as
  fact.

## Entry format

Copy this block. Every field earns its place: without **Source** and **Added** a future
reader cannot judge whether the answer is still true, and without **Promote when** entries
silently become permanent shadow documentation.

```markdown
### Q: <the question, phrased the way a user would ask it>

**A:** <the answer>

- **Source:** <who said it / where it was observed — name a person or a verifiable check>
- **Added:** <YYYY-MM-DD> by <github username>
- **Confidence:** confirmed by owner | provisional — needs confirmation
- **Promote when:** <the upstream doc that should eventually carry this, if any>
```

Keep each entry self-contained — retrievers chunk independently of headings, so an entry
that only makes sense after reading the one above it will retrieve badly.

---

## Entries

### Q: Someone said "client" — do they mean a customer or an identity client?

**A:** It depends entirely on the surrounding words, and getting it wrong sends the question
to the wrong place. In an Ops Center / operational context, "client" almost always means the
**customer or organization**: licensing, contracts, onboarding, org keys, CRM identifiers,
"a client's Admin Center", "client administrator". Answer from the Ops Center corpus.

If the word appears near **authentication vocabulary** — "identity client", OAuth, OIDC,
scopes, tokens, client credentials or CCF, `client_id` / `client_secret`, redirect URI,
PKCE, `application_type` — it means a **registered application**, and the question belongs to
Tyler Identity.

A third sense appears occasionally: "the *product* client", as in "what's available via the
Ops Center client", meaning the client application or SDK.

If the sense is genuinely unclear, **ask one clarifying question** rather than guessing.

- **Source:** Vijay Venkataraman, 2026-08-23, in response to observed routing failures. The
  third sense was found in transcript `2026-08-10--d6f2ea37` ("What's available via the Ops
  Center client?").
- **Added:** 2026-08-23 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** `Docusaurus-Terminology.md` already warns "avoid 'client' in technical
  contexts", but does not give this routing rule. If the glossary is expanded to cover it,
  move this there.

### Q: Is there a way to see all the Admin Center instances I have access to?

**A:** **No — there is currently no single place** that lists every Admin Center instance a
user has access to.

Once a product has adopted **Support Access Center**, Tyler users will be able to see all of
their access requests — to Admin Center *and* to products — on the **SAC Dashboard**. That is
the closest thing to a consolidated view, and it only covers products that have adopted SAC.

Do not offer a workaround that implies a consolidated list exists.

- **Source:** Vijay Venkataraman, reviewing transcript `team/2026-08-21--e7510651`, where the
  team routed this to Tyler Identity and the answer was wrong. Diagnosis was `search-empty` —
  nothing in any corpus answered it.
- **Added:** 2026-08-24 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** if Blueprint documents a consolidated access view, move it there.

### Q: I need to be an Org Admin / I need access to a customer's Admin Center — how do I get it?

**A:** **There are three paths, and the right one depends on how often you need access and on
whether you already hold the self-promotion permission.** Present the one that fits; do not
send someone down the manager's-guide route when a single ticket would do, and do not send
someone who *already* has self-promotion rights to raise anything at all.

**Occasional access to one customer's Admin Center** — use the **Client Admin Center access
request** ticket. **Give the user the Confluence page, not the raw form URL** — it carries the
field-by-field instructions the form does not:
<https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386600308/Tyler+Cloud+Platform+TCP+Ops+Center+Related+Tickets+and+Permissions>

(The underlying form is `.../portal/3168/group/3333/create/4165`, on the JSM portal. Mention it
as supporting detail if asked, but lead with the Confluence page.)

This is the normal path, and it is what most people asking this question want. Being granted
it makes you an Org Admin for that one organization. Requirements: the org must already exist
in Ops Center in that environment, and you must not already have access. Allow up to five
minutes after approval.

**Frequent access, and you ALREADY have self-promotion permission** — just do it yourself, in
product. No ticket. Ops Center -> **Organization Details -> Admins**, then
**+ Promote me as admin**. OneTyler grants this elevated *Promote / Remove yourself as Org
Admin* right to select Ops users whose roles require routine customer access, so a good number
of people asking this question can already self-serve and do not know it. **Check whether the
user has the permission before routing them anywhere** — if the menu action is there, that is
the whole answer.

Please also **remove your own Org Admin rights when you no longer need them**, using the
**- Remove me as admin** action on that same screen. Tyler-staff Org Admins can self-remove
this way, and cleaning up is expected rather than optional. Permission changes take a little
time to propagate.

**Frequent access, and you do NOT yet have that permission** — this is the only case that
needs the **Manager's Guide**: *Tyler Cloud Platform (TCP) | Org Admin promotions (Admin Center
access) - a Manager's guide* (`/wiki/spaces/TTI/pages/386629479/`)

It is a manager-driven workflow, and there is **no single ticket URL** for it — a manager
requests it directly, and it covers two distinct capabilities: **(a)** adding a customer's user
as an Org Admin themselves, and **(b)** granting their own direct reports the self-promotion
permission described above, so those reports can add themselves going forward without going
through their manager each time. Prerequisites: the user already has Ops Center access, and
does not already have self-promotion rights. Once (b) is granted, they are in the case above
permanently and never need this route again.

None of the three paths uses the generic "Ops Center additional permissions" form (`4133`).

**Why this entry exists:** asked as "need to add myself as an org admin for product add", the
team agent returned only the Manager's Guide. That answer is not wrong, but for a one-off
request it sends the user into a manager-approval process when ticket `4165` would have
settled it. The routes are catalogued separately in
`Knowledge-Shared/Conf-OneTylerTickets.md`; what was missing everywhere was the rule for
choosing between them.

**Why it says three paths and not two:** asked again as plain "how to add myself as an admin",
the agent described the ticket route and the Manager's Guide but presented the manager's guide
as the way to get access, when for someone who already holds the self-promotion permission the
answer is a single in-product action and no request at all. Collapsing "use the permission you
have" and "obtain the permission" into one branch is what made the answer incomplete. Treat
them as separate outcomes.

- **Source:** Vijay Venkataraman, reviewing transcript `team/2026-08-24--53d51e27`, and again
  on `team/2026-09-08--4125fbd2` for the three-path split, and again on `team/2026-09-11--5893b8c0`
  for the explicit "- Remove me as admin" button name and the manager's-guide (a)/(b) split.
  Ticket numbers and prerequisites cross-checked against `Knowledge-Shared/Conf-OneTylerTickets.md`
  (*Client Admin Center access request*, and *Add an Org Admin, or self-promote as Org Admin*),
  and the in-product self-promote screen against `Docusaurus-OpsCenter.md` -> *Organization
  Details - Admins*.
- **Added:** 2026-08-24, three-path split added 2026-09-09, button name and manager (a)/(b)
  split added 2026-09-13, by vijay-tylertech
- **Confidence:** confirmed by owner
- **Added:** 2026-08-25 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** the Confluence ticket page or the Manager's Guide itself states the
  occasional-vs-frequent rule. The form details belong in
  `Knowledge-Shared/Conf-OneTylerTickets.md`, which is re-derived from upstream — only the
  choice-between-them rule lives here.

### Q: How do I add a new org email domain?

**A:** **It depends on whether the org has been initialized yet — the two routes are
completely different, and there is no single answer.** Check the org in Ops Center for an
existing domain before answering.

**Case 1 — no domain exists yet (uninitialized org).** The first domain cannot be added
directly. It arrives as a side effect of adding the first Org Admin, in one flow:

1. Go to the organization in Ops Center and open **Organization Details**.
2. Go to **Organization Details > Admins** and add an Org Admin, using the **"Use as
   technical contact"** option.
3. That Org Admin's **userid domain is automatically set as the org domain**.

This needs the privileged Org Admin functionality, which is granted to **Managers** via
*Tyler Cloud Platform (TCP) | Org Admin promotions (Admin Center access) - a Manager's guide*
(`/wiki/spaces/TTI/pages/386629479/`). So if the requester is not a manager with that
permission, the first step is getting it — not attempting the domain.

**Case 2 — the org already has domains.** Additional domains are **not** added in Ops Center
at all. They go through **Admin Center → Identity Workforce → Domains**.

Getting this wrong wastes real time: someone sent to Admin Center for an uninitialized org
finds nothing to work with, and someone sent through the Org Admin flow for an already-live
org is being asked for a manager permission they do not need.

- **Source:** Vijay Venkataraman, reviewing transcript `team/2026-08-25--5760409c`, where the
  answer given did not distinguish the two cases.
- **Added:** 2026-08-27 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** Blueprint or the Ops Center Confluence documentation states the
  initialized-vs-uninitialized split. `Docusaurus-OpsCenter.md` and `Docusaurus-OrgAdminInfo.md`
  both mention "Use as technical contact" but neither explains that it is how the *first*
  domain is set.

### Q: How do I rename or delete a workspace?

**A:** **Workspaces cannot be renamed — at all.** The only route to a different name is delete
and recreate, and even that is constrained. Do not offer a rename path.

**Customer orgs — you cannot do this yourself.** Deleting a workspace is restricted to
**OneTyler Support Staff**; it is not available to others through either the UI or the API.
Request it via *Other non-product assistance with Organizations and Workspaces* on the
tickets page.

One prerequisite that catches people: **no products may be available on the workspace.** If
products are still available there, the workspace will not be deleted — product availability
applies across all products and is not removed just because one product was decommissioned.
Clear that first, or the request will bounce.

**Internal orgs — self-service.** Delete and recreate through the Ops Center UI or the API. If
you lack permission to manage internal organizations, request the deletion via the same *Other
non-product assistance with Organizations and Workspaces* option so you can recreate it. Note
that on recreation **only the suffix part of the name can be set** to a custom value.

**Also worth stating up front:** workspace creation is highly restricted — only **7 standard
workspaces** can be created by default, so "delete and recreate" is not a free action to spend
casually.

For the ticket, give the **Confluence page** rather than a raw JSM form URL — see *Which link
to hand out* in `Knowledge-Shared/Conf-OneTylerTickets.md`:
<https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386600308/Tyler+Cloud+Platform+TCP+Ops+Center+Related+Tickets+and+Permissions>

- **Source:** Vijay Venkataraman, reviewing transcript `team/2026-08-25--7b3dc870`
  ("how can i remove or rename a workspace").
- **Added:** 2026-08-27 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** Blueprint states that workspaces cannot be renamed and documents the
  7-workspace default limit. `Conf-OneTylerTickets.md` carries the ticket itself; the
  rename-impossibility, the products-must-be-clear prerequisite and the workspace limit are
  recorded nowhere else.

### Q: Is the team still called CorpDev?

**A:** No — the team is **OneTyler**. "CorpDev" is the former name, but it is still used
verbatim in live systems, so treat the two as the same team: the JSM portals are titled
"CorpDev Support" and "CorpDev Feature Requests", some ticket forms still say "CorpDev
maintained applications", the Teams space is "CorpDev Collaboration", and GitHub and
infrastructure identifiers keep the `corpdev-` prefix (`corpdev-tf-docs`,
`corpdev_db_admin`, the `orgs/CorpDev/` Harness path). Answer as though the user said
OneTyler, but quote system names exactly as they appear in that system.

- **Source:** Vijay Venkataraman, 2026-08-23.
- **Added:** 2026-08-23 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** also recorded in `Docusaurus-Terminology.md` under *OneTyler (formerly
  CorpDev)*. Keep here only while the rename is still in flight.

### Q: How do I access audit logs in Ops Center? / Where do I see who licensed a product for a workspace?

**A:** **Ops Center does not have audit logs today. It has *authentication* logs, and they are
a different thing.** This is the trap in the question: searching for "audit logs" lands on the
**Authentication logs** section, which looks like an answer and is not one. Say the distinction
out loud before describing either.

| | **Authentication logs** | **Activity / audit logs** |
|---|---|---|
| In Ops Center today? | **Yes** | **No** |
| What they cover | User **sign-in** activity | Operational **actions** — who licensed a product, who changed a setting |
| How to get them | Ops Center -> **Organizations** -> select the org -> **Organization Details** -> *Authentication logs*. Behaviour differs sharply by Identity Workforce tier — see the comparison table in `Docusaurus-OpsCenter.md` -> *Authentication logs*. | **Not in Ops Center at all.** Held in **Audit Center**, which is OneTyler-staff-only. Everyone else files a request: use the Confluence ticket page -> *Other non-product assistance with Organizations and Workspaces*: <https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386600308/Tyler+Cloud+Platform+TCP+Ops+Center+Related+Tickets+and+Permissions> — state the activity you need. |

**Authentication logs will not answer "who licensed this product".** They track logins, not
operational changes. Do not offer them as a substitute; that is the specific way this question
gets answered wrongly.

**There is no Tyler-wide audit/activity tool at all.** Authentication logs in Ops Center are
the **only** log surface available across Tyler. Audit and activity data does exist, in
**Audit Center** — but Audit Center is a **OneTyler-staff-only** tool, so it is not an answer
you can hand to a general Tyler audience. That restriction is precisely *why* the route for
everyone else is to file a request: the request is how you reach data held in a tool you
cannot open yourself. Never tell a user to "check the audit logs" without establishing that
they are OneTyler staff.

**Activity logs in Ops Center are planned, not shipped.** Ops Center is expected to gain
Activity logs against a **product in the Product Registry** and against an **organization**.
Describe this as coming, never as available, and do not promise a date.

**What to do about "who licensed a product for a workspace" in the meantime:**

1. **File the request** above — that is the supported route for anyone who is not OneTyler
   staff, and it is the right first answer in almost every case.
2. **Ops telemetry (AWS QuickSight)** gives you licensing *counts and current state*, not
   attribution. It will tell you a product **is** licensed, never **who** licensed it. Path:
   <https://sso.tylertech.com/app/UserHome> -> **Tyler Cloud Insights Center** -> **TCP Prod
   Stats** dashboard. See `Docusaurus-OpsCenter.md` -> *Ops telemetry (AWS QuickSight)*.
3. **Ask the OneTyler team** for a specific attribution question that cannot wait.
4. **If the user is OneTyler staff**, the answer is in **Audit Center**, which records the
   acting user against product-licensing events. Do not offer this branch otherwise.

Also worth separating: **licensing is org-level, availability is workspace-level** (see
`Docusaurus-OpsCenter.md` -> *Product licensing (organization) and availability (workspace)*).
A question phrased "licensed a product **for a workspace**" is usually really about
availability/activation on that workspace, so check which one the user means before answering.

- **Source:** Vijay Venkataraman, reviewing transcript `team/2026-09-04--f4fc1c8a` — the team
  agent answered "how do i access audit logs in ops center" with the authentication-logs
  material, which is the wrong log type, and did not mention that activity data requires a
  ticket today. The Audit Center scoping is his correction on 2026-09-09: "TCP Audit log
  currently only exists in Audit Center that is only for OneTyler staff. There is no Tyler
  wide tool that gives Audit/Activity logs excepting Authentication logs which is available
  in Ops Center."
- **Note:** `Knowledge-BP-General/Docusaurus-OpsApps.md` owns Audit Center and its upstream
  Blueprint page is a **stub**, so that file cannot currently say who Audit Center is for.
  This entry is the only place that restriction is written down.
- **Added:** 2026-09-09 by vijay-tylertech
- **Confidence:** confirmed by owner
- **Promote when:** Activity logs ship in Ops Center and Blueprint documents them — at which
  point this entry needs rewriting, not just re-confirming, and the "planned" wording must go.
  **Vijay Venkataraman will flag when that lands** (confirmed 2026-09-09: expected soon, no
  date available). Until he does, do not go looking for a ship date and do not soften the
  "not shipped" wording — the absence of a date is the known state, not missing research.

---

## Notes for the chatbot

- Entries here have **no upstream document**. State them plainly, but if a user pushes back,
  say the answer comes from internal Tyler subject-matter guidance rather than published
  documentation.
- An entry marked **provisional** has not been confirmed by an owner. Hedge accordingly.
- If an entry contradicts a `Docusaurus-` or `Conf-` file in this folder, the upstream file
  usually wins — **unless** the entry exists precisely because it corrects that source, in
  which case it says so in **Source**.
