#!/usr/bin/env python3
"""
Local transcript review UI for the OneTyler Cloud Living knowledge repo.

Serves a browser interface on http://127.0.0.1:7777 for reading collected
transcripts, recording verdicts and corrections, and writing them straight back
into the repo's markdown files so the result is an ordinary reviewable diff.

Stdlib only — no pip install, no build step. Binds to loopback only.

    python3 scripts/review_server.py
    python3 scripts/review_server.py --port 7778 --no-browser

Everything it writes lands in transcripts/*.md. Commit and open a PR as normal,
or use the Git panel in the UI.
"""
import argparse, html, json, re, subprocess, sys, webbrowser
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from golive import GO_LIVE, EXCLUDE_NOTE, is_pre_go_live
from reviewtext import has_feedback, needs_triage
from urllib.parse import unquote

REPO = Path(__file__).resolve().parent.parent
TDIR = REPO / "transcripts"

STATUS = REPO / "scripts" / "review_status.py"

CONTRIB = REPO / "contributors.json"


def contributors():
    """GitHub usernames allowed in the `reviewer` field. Read fresh each request so
    adding someone to contributors.json takes effect without a server restart."""
    try:
        d = json.loads(CONTRIB.read_text(encoding="utf-8"))
        return [c["github"] for c in d.get("contributors", []) if c.get("github")]
    except Exception:
        return []


OWNERS = REPO / "agent-owners.json"


def agent_owners():
    """agent slug -> set of usernames who own it, from agent-owners.json.

    Hand-maintained, unlike contributors.json which is generated. Read fresh each request so
    editing the file takes effect without restarting the server. Returns ({}, default) on any
    problem rather than raising — a broken ownership file must not take the review UI down,
    since ownership is only a convenience for finding your own rows.
    """
    try:
        d = json.loads(OWNERS.read_text(encoding="utf-8"))
    except Exception:
        return {}, None
    def as_set(v):
        return {v} if isinstance(v, str) else set(v or [])
    by = {k: as_set(v) for k, v in (d.get("by_agent") or {}).items() if not k.startswith("_")}
    return by, d.get("default_owner") or None


# Foundry display name -> the agent slug used in `answered_by` and agent-owners.json.
# `delegated_to` carries display names, so ownership cannot be resolved without this.
DELEGATE_SLUG = {
    "Ops Center": "ops-center",
    "General Blueprint Docs Agent": "bp-general",
    "Support Access Center": "sac",
    "Tyler Identity Assistant": "identity",
    "Aligned Releases": "aligned-releases",
}


def admins():
    """Everyone on the admins team. Routing is admin territory, so a transcript whose ROUTING
    is in question belongs to all of them rather than to one area owner."""
    try:
        d = json.loads(CONTRIB.read_text(encoding="utf-8"))
        return {c["github"] for c in d.get("contributors", [])
                if c.get("github") and (c.get("role") == "maintainer"
                                        or "admins" in (c.get("team") or ""))}
    except Exception:
        return set()


def effective_agents(fm):
    """Which SUB-AGENT(S) a transcript really belongs to.

    `answered_by: team` means the router handled the conversation, not that the team "owns" it.
    Ownership follows the sub-agent that actually answered, which is in `delegated_to`. Keying
    on answered_by instead put every routed conversation on the default owner — so five Entra
    and Gateway questions that Identity answered showed as the Ops Center owner's area.

    Team routing decisions are themselves admin territory, so a transcript the router handled
    with no delegation recorded falls to the admins.
    """
    if (fm.get("answered_by") or "") != "team":
        return [fm.get("answered_by") or ""]
    names = [x.strip() for x in (fm.get("delegated_to") or "").split(",") if x.strip()]
    slugs = [DELEGATE_SLUG.get(x) for x in names]
    return [s for s in slugs if s] or ["__team__"]


def owners_of(agent):
    by, default = agent_owners()
    if agent in by:
        return by[agent]
    return {default} if default else set()


def whoami(override=None):
    """The current contributor, for highlighting their rows.

    Order: an explicit --me override, then the local `gh` identity. Returns None if neither
    works, in which case nothing is highlighted — which is the right failure mode: highlighting
    the WRONG person's rows is worse than highlighting nobody's.
    """
    if override:
        return override
    rc, out = git_cmd("gh", "api", "user", "--jq", ".login")
    return out.strip() or None


def git_cmd(*args):
    try:
        r = subprocess.run(list(args), cwd=REPO, capture_output=True, text=True, timeout=15)
        return r.returncode, r.stdout
    except Exception:
        return 1, ""


ME = None          # resolved once at startup; see main()

# Ordered so rewritten frontmatter keeps a stable, diff-friendly shape.
SOURCE_KEYS = ["conversation_id", "answered_by", "date", "exchanges",
               "dropped_sample_prompts", "foundry_feedback", "user_comments"]
REVIEW_KEYS = ["review_status", "reviewer", "suggested_by", "awaiting", "review_round",
               "routing_verdict", "reassign_to", "answer_verdict", "diagnosis", "fix_target",
               "kb_action", "kb_files", "action_status", "notes"]

# Fields constrained to a contributors.json `github` value. `reviewer` records who made the
# call; `suggested_by` records who drafted a suggestion they are NOT claiming as a verdict;
# `awaiting` names the area owner it is being handed to. All three must be real people, or
# the handoff has nobody to chase.
PEOPLE_KEYS = ("reviewer", "suggested_by", "awaiting")

# Most transcripts need no corpus change. Pre-selecting the "nothing wrong" answer means
# "Mark reviewed & next" on an untouched form records a deliberate no-change review rather
# than a blank one, so a reviewer can move through a clean batch at one click each.
NO_CHANGE_DEFAULTS = {
    "routing_verdict": "correct",
    "answer_verdict": "good",
    "diagnosis": "n-a",
    "fix_target": "none",
    "kb_action": "none",
    "action_status": "none-needed",
}

CHOICES = {
    "review_status":   ["pending", "suggested", "reviewed", "pushed", "excluded"],
    "routing_verdict": ["", "correct", "wrong-agent", "ambiguous"],
    "reassign_to":     ["", "ops-center", "bp-general", "sac", "identity", "team"],
    "answer_verdict":  ["", "good", "incomplete", "wrong", "stale", "refused"],
    "diagnosis":       ["", "n-a", "no-search", "search-empty", "search-irrelevant",
                        "retrieved-ok-answered-badly", "routing-only"],
    "fix_target":      ["", "none", "knowledge-file", "agent-instructions",
                        "team-routing", "sample-prompts"],
    "kb_action":       ["", "none", "add", "update", "split"],
    "action_status":   ["", "none-needed", "open", "applied", "wontfix"],
}
# Everything explanatory about a field lives HERE, behind its ⓘ icon — nothing is printed
# beside the field itself. The form is fourteen fields; a sentence of guidance next to each one
# turned the page into a wall of grey text that reviewers scrolled past, which is worse than no
# guidance at all. So the label carries the field name and the icon, and that is all.
#
# This used to be split: a one-line hint rendered inline plus this panel. The two said the same
# thing in different words, which is how they drift.
#
# `about` is prose: what the field is for, and what gets it wrong. `values` maps each allowed
# value to what choosing it commits you to — a reviewer guessing at `diagnosis` produces a
# confidently wrong knowledge-file change, so the cost of leaving this implicit is real.
# `flow` is an optional at-a-glance line rendered in monospace above the prose.
FIELD_DOC = {
    "review_status": {
        "flow": "pending → suggested → reviewed → pushed        (excluded = out of scope)",
        "about": "Where this transcript sits in the review lifecycle. You normally change this "
                 "with the buttons at the bottom rather than the dropdown. `suggested` is "
                 "optional — skip it for areas you own.",
        "values": {
            "pending": "Nobody has reached a conclusion yet. Saving with fields filled in and "
                       "leaving it here is a deliberate note-to-self — nobody else will act on it.",
            "suggested": "You worked it up but the call is not yours to make. Goes to the owner "
                         "named in `awaiting`; requires `suggested_by`. Claude will NOT act on it.",
            "reviewed": "Your verdict, on the record. This is the queue Claude works from, so "
                        "only set it when you are content for changes to be made on this basis.",
            "pushed": "Processed AND live in Foundry. Claude sets this after verifying the "
                      "upload — it is a claim about Foundry, not about the repo. Don't set it by hand.",
            "excluded": "Not real feedback, so it leaves the queue without counting as review "
                        "work. Used for pre-go-live internal testing (before 2026-08-19 19:42 UTC).",
        },
    },
    "reviewer": {
        "about": "Who made the call — set it when you mark this reviewed, NOT when you "
                 "suggest. Required for `reviewed` and `excluded`. Restricted to "
                 "contributors.json, which is generated from GitHub team membership — if your "
                 "name is missing, you are not on the team yet, and typing it in will not help.",
        "values": {},
    },
    "suggested_by": {
        "about": "Who drafted a suggestion they are explicitly NOT claiming as a verdict. "
                 "Required when review_status is `suggested`. The Suggest button fills this in "
                 "and clears `reviewer`, because those two fields answer different questions: "
                 "who wrote this, versus who decided it.",
        "values": {},
    },
    "awaiting": {
        "about": "The area owner a suggestion is handed to — the person who should accept or "
                 "override it. Optional: blank means anyone can pick it up. Naming someone is "
                 "what makes `--suggestions --for <user>` find it. Cleared once reviewed, "
                 "since it is no longer waiting on anybody.",
        "values": {},
    },
    "review_round": {
        "about": "Which pass over this transcript this is. Raising it is how you re-open "
                 "something already decided without overwriting the previous verdict — both end "
                 "up on the record. Use the Re-review button rather than editing the number; CI "
                 "rejects a second first-review at the same round.",
        "values": {},
    },
    "routing_verdict": {
        "about": "Whether the TEAM agent handed the question to the right sub-agent. This is "
                 "about routing only — a perfectly routed question can still get a bad answer, "
                 "and that is what `answer_verdict` is for. Check the Delegation table above.",
        "values": {
            "": "Not assessed.",
            "correct": "The right sub-agent handled it.",
            "wrong-agent": "The wrong one handled it. Name who should have in `reassign_to`.",
            "ambiguous": "The question genuinely spanned areas, or was too vague to route. "
                         "Usually a signal the router should have asked a clarifying question.",
        },
    },
    "reassign_to": {
        "about": "Which sub-agent SHOULD have handled it. Only meaningful when routing_verdict "
                 "is `wrong-agent`. Repeated reassignments to the same target are the strongest "
                 "evidence the team routing rules need changing.",
        "values": {
            "": "Not applicable.",
            "ops-center": "Ops Center — the Ops Center UI, orgs, workspaces, licensing, "
                          "product activation, Admin Center access.",
            "bp-general": "General Blueprint Docs — platform orientation, APIs, service "
                          "architecture, DevOps, product registration concepts.",
            "sac": "Support Access Center — support access requests and the SAC dashboard.",
            "identity": "Tyler Identity — Okta, federation, OIDC/OAuth, identity clients, "
                        "tokens, Gateway.",
            "team": "The team router itself should have handled or clarified it, rather than "
                    "delegating at all.",
        },
    },
    "answer_verdict": {
        "about": "Quality of the answer the user actually received. Judge it against what you "
                 "would have told them — not against whether the agent tried hard.",
        "values": {
            "": "Not assessed.",
            "good": "You would have been happy to send this.",
            "incomplete": "Correct as far as it goes, but missing something that matters. The "
                          "most common real verdict.",
            "wrong": "Materially incorrect — it would mislead someone who acted on it.",
            "stale": "Was true once; the world moved and the corpus did not.",
            "refused": "Declined or deflected a question it should have answered.",
        },
    },
    "diagnosis": {
        "about": "WHY it went wrong — the single most important field, because it decides who "
                 "fixes it. Read the 'Tools called' line on the exchange: it tells you what the "
                 "agent actually did, which four different failures all look identical in the "
                 "visible chat. Do not guess; if you cannot tell, say so in `notes`.",
        "values": {
            "": "Not assessed.",
            "n-a": "Nothing went wrong. This is the pre-filled default on a clean transcript.",
            "no-search": "Tools called: none — it answered from the model's own priors without "
                         "looking anything up. An AGENT PROMPT problem, not a content gap.",
            "search-empty": "It searched and found nothing. Content is MISSING or unretrievable "
                            "— a genuine knowledge-file gap.",
            "search-irrelevant": "It searched and got the wrong material. Content exists but is "
                                 "wrong, badly structured, or badly chunked.",
            "retrieved-ok-answered-badly": "It found the right material and still answered "
                                           "badly. An AGENT PROMPT problem — do not rewrite a "
                                           "knowledge file to paper over it.",
            "routing-only": "The answer was fine for whoever gave it; it just should not have "
                            "been them. A TEAM ROUTING problem.",
        },
    },
    "fix_target": {
        "about": "Where the fix belongs. This is what tells Claude whether to touch a corpus "
                 "file at all — only `knowledge-file` does. For the others the deliverable is a "
                 "concrete written proposal, because the thing needing the change lives in "
                 "Foundry, not in this repo.",
        "values": {
            "": "Not assessed.",
            "none": "Nothing needs to change anywhere.",
            "knowledge-file": "A file in a Knowledge-* folder must change. Name it in `kb_files`.",
            "agent-instructions": "The sub-agent's system prompt needs changing. Lives in "
                                  "Foundry — write the exact wording in Proposed fix; Claude "
                                  "cannot edit it from here.",
            "team-routing": "The team router's rules need changing — the routing table in "
                            "README.md, or hand-off guidance in a _START_HERE.md.",
            "sample-prompts": "The agent's canned starting questions need changing. Also lives "
                              "in Foundry.",
        },
    },
    "kb_action": {
        "about": "What must physically happen to the corpus. `none` is a valid and common "
                 "answer — plenty of bad answers are not content problems at all. A review with "
                 "`none` and a good Proposed fix is still a complete contribution.",
        "values": {
            "": "Not assessed.",
            "none": "No corpus change needed.",
            "add": "New content that exists nowhere. If it has no upstream source, it belongs "
                   "in that folder's FAQ-*.md file, not in a derived Conf-/Docusaurus- file.",
            "update": "Existing content is wrong, thin, or stale and needs editing in place.",
            "split": "One file is covering too much and retrieving badly; it needs breaking up.",
        },
    },
    "kb_files": {
        "about": "Which file(s) the change goes in, comma-separated, repo-relative — e.g. "
                 "Knowledge-OpsCenter/FAQ-OpsCenter.md. It must be a file that is actually "
                 "deployed to a collection: Knowledge-Shared/_START_HERE.md looks like a "
                 "knowledge file but is repo-only documentation, so a fix there reaches no "
                 "agent. If unsure, name the corpus in `notes` and let Claude place it.",
        "values": {},
    },
    "action_status": {
        "about": "Whether the change has actually been made. This is the field that stops open "
                 "work being quietly buried — a transcript cannot be closed out while this says "
                 "`open` and kb_action asks for something.",
        "values": {
            "": "Not assessed.",
            "none-needed": "Nothing had to change.",
            "open": "A change is required and has not been made yet. Claude's to-do list.",
            "applied": "The change has been made. Set by Claude, not by you.",
            "wontfix": "Decided against acting on it. Say why in `notes`.",
        },
    },
    # Not frontmatter fields — the two free-text boxes. Same treatment so the page reads
    # uniformly: a label, an icon, and nothing else.
    "correction": {
        "about": "What the agent SHOULD have said, in your own words. The single most valuable "
                 "thing you can write here — it is what Claude turns into content, so a vague "
                 "\"this is wrong\" produces a vague fix. Write it as you would have answered "
                 "the person. Leave it empty if the answer was fine.",
        "values": {},
    },
    "proposed_fix": {
        "about": "What should change so this answer is right next time. For a knowledge-file "
                 "fix, say what content is missing and roughly where it belongs. For an "
                 "instructions or routing fix, give the exact wording to add or reword — those "
                 "live in Foundry and Claude cannot edit them from the repo, so a precise "
                 "proposal is the whole deliverable. This is committed even when no knowledge "
                 "file changes: a PR of verdicts and proposals alone is a full contribution.",
        "values": {},
    },
    "notes": {
        "about": "One line, free text — long-form belongs in Proposed fix at the bottom of the "
                 "page. Context that does not fit the structured fields: who to "
                 "ask, why you are unsure, what you decided against. Long-form belongs in "
                 "Proposed fix at the bottom of the page. Claude appends its own processing "
                 "notes here after a '||' separator, so expect this to grow.",
        "values": {},
    },
}


# ---------------------------------------------------------------- file I/O
def is_transcript(p):
    """A transcript is identified by CONTENT, not by filename.

    This used to be a blocklist of ("INDEX.md", "README.md"), which broke the moment
    ONBOARDING.md was added to the folder: it was treated as a transcript, had no
    frontmatter, and failed CI. Any doc added here would have done the same. A transcript
    is a markdown file whose frontmatter carries a conversation_id; everything else in the
    folder is documentation and is skipped.
    """
    try:
        head = p.read_text(encoding="utf-8", errors="replace")[:1500]
    except OSError:
        return False
    return head.startswith("---") and "conversation_id:" in head


def tfiles():
    return sorted(f for f in TDIR.rglob("*.md") if is_transcript(f))


def parse(p):
    txt = p.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", txt, re.S)
    if not m:
        return None, txt
    fm = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm, m.group(2)


def exchanges_of(body):
    """[(n, tools, question, answer, review_text)] in document order."""
    out = []
    for m in re.finditer(r"## Exchange (\d+)\n(.*?)(?=\n## Exchange |\n---\n\n## Proposed fix|\Z)",
                         body, re.S):
        n, blk = m.group(1), m.group(2)
        tools = (re.search(r"\*\*Tools called:\*\* (.*)", blk) or [None, ""])[1].strip()
        q = (re.search(r"\*\*Q:\*\*\n\n((?:> .*\n?)+)", blk) or [None, ""])[1]
        q = re.sub(r"^> ?", "", q, flags=re.M).strip()
        a = (re.search(r"\*\*A:\*\*\n\n```markdown\n(.*?)\n```", blk, re.S) or [None, ""])[1]
        rv = (re.search(r"<!-- review:\d+ -->\n(.*?)<!-- /review:\d+ -->", blk, re.S) or [None, ""])[1]
        out.append((n, tools, q, a, rv.strip()))
    return out


def first_question(body, words=14):
    """Opening words of the first real question — the only reliable way to tell
    transcripts apart in a list, since filenames are just dates and hashes."""
    m = re.search(r"\*\*Q:\*\*\n\n((?:> .*\n?)+)", body)
    if not m:
        return ""
    q = re.sub(r"\s+", " ", re.sub(r"^> ?", "", m.group(1), flags=re.M)).strip()
    w = q.split()
    return " ".join(w[:words]) + ("…" if len(w) > words else "")


def proposed_of(body):
    m = re.search(r"<!-- proposed-fix -->\n(.*?)<!-- /proposed-fix -->", body, re.S)
    return m.group(1).strip() if m else ""


def save(p, fm_new, ex_reviews, proposed):
    fm, body = parse(p)
    if fm is None:
        raise ValueError("no frontmatter")
    fm.update({k: (v or "").replace("\n", " ").strip() for k, v in fm_new.items()})

    L = ["---"]
    for k in SOURCE_KEYS:
        if k in fm:
            L.append(f"{k}: {fm[k]}")
    L += ["", "# ---- review fields: edit these ----"]
    for k in REVIEW_KEYS:
        L.append(f"{k}: {fm.get(k, '')}".rstrip())
    for k, v in fm.items():                                  # keep anything unrecognised
        if k not in SOURCE_KEYS and k not in REVIEW_KEYS:
            L.append(f"{k}: {v}")
    L.append("---")

    for n, txt in ex_reviews.items():
        body = re.sub(rf"(<!-- review:{n} -->\n).*?(<!-- /review:{n} -->)",
                      lambda m: m.group(1) + (txt.strip() + "\n" if txt.strip() else "") + m.group(2),
                      body, flags=re.S)
    body = re.sub(r"(<!-- proposed-fix -->\n).*?(<!-- /proposed-fix -->)",
                  lambda m: m.group(1) + (proposed.strip() + "\n" if proposed.strip() else "") + m.group(2),
                  body, flags=re.S)
    p.write_text("\n".join(L) + "\n" + body, encoding="utf-8")


def set_fields(p, updates):
    """Rewrite ONLY frontmatter values, leaving the body byte-identical.

    Deliberately not save(): save() re-renders the body from its `ex_reviews` and `proposed`
    arguments, so calling it to touch one header field means either passing the body back
    (fragile) or passing empty strings, which WIPES the reviewer's correction and proposed
    fix. Passing None crashes on proposed.strip(). This does a line-level substitution and
    cannot touch prose.
    """
    txt = p.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    if not m:
        return
    head = m.group(1)
    for k, v in updates.items():
        if re.search(rf"^{re.escape(k)}:.*$", head, re.M):
            head = re.sub(rf"^{re.escape(k)}:.*$", f"{k}: {v}", head, count=1, flags=re.M)
        else:
            head += f"\n{k}: {v}"
    p.write_text("---\n" + head + "\n---\n" + txt[m.end():], encoding="utf-8")


def refresh_index():
    try:
        subprocess.run([sys.executable, str(STATUS)], cwd=REPO,
                       capture_output=True, timeout=60)
    except Exception:
        pass


def git(*args, timeout=60):
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=timeout)
    return r.returncode, (r.stdout + r.stderr).strip()


# ---------------------------------------------------------------- rendering
CSS = """
/* ---------------------------------------------------------------------------------------
   Tyler Forge light theme. Values lifted from the real forge.css light-theme block, not
   guessed, so this matches Ops Center rather than merely resembling it.

   Declared as --forge-* custom properties with the value inline. That way the names match
   Forge (so anyone who knows the system recognises them) while the page stays a single
   self-contained file with no build step and no library to import.
   --------------------------------------------------------------------------------------- */
:root{
  --forge-theme-brand:#283593;
  --forge-theme-primary:#3f51b5;
  --forge-theme-primary-container:#d1d5ed;
  --forge-theme-primary-container-low:#e8eaf6;
  --forge-theme-primary-container-minimum:#f7f8fc;
  --forge-theme-secondary:#ffc107;
  --forge-theme-surface:#ffffff;
  --forge-theme-surface-dim:#fafafa;
  --forge-theme-surface-container:#e0e0e0;
  --forge-theme-surface-container-low:#ebebeb;
  --forge-theme-surface-container-minimum:#f5f5f5;
  --forge-theme-text-high:rgba(0,0,0,.87);
  --forge-theme-text-medium:rgba(0,0,0,.6);
  --forge-theme-text-low:rgba(0,0,0,.38);
  --forge-theme-outline:#e0e0e0;
  --forge-theme-outline-low:#9e9e9e;
  --forge-theme-outline-medium:#757575;
  --forge-theme-success:#2e7d32;
  --forge-theme-error:#b00020;
  --forge-theme-warning:#d14900;
  --forge-theme-info:#1565c0;
  --forge-theme-info-container-low:#e3edf7;
  --forge-theme-warning-container-low:#f9e9e0;
  --forge-spacing-xsmall:4px; --forge-spacing-small:8px;
  --forge-spacing-medium:16px; --forge-spacing-large:24px;
  --nav-w:212px;
}
*{box-sizing:border-box}
body{margin:0;font:14px/1.55 Roboto,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
color:var(--forge-theme-text-high);background:var(--forge-theme-surface-dim)}
a{color:var(--forge-theme-primary)}

/* --- app bar --- */
header{background:var(--forge-theme-brand);color:#fff;padding:0 var(--forge-spacing-medium);
height:56px;display:flex;gap:var(--forge-spacing-medium);align-items:center;
position:sticky;top:0;z-index:30;box-shadow:0 1px 3px rgba(0,0,0,.24)}
header b{font-size:16px;font-weight:500;letter-spacing:.01em}
header .who{margin-left:auto;font-size:13px;opacity:.85}

/* --- SIDE NAV. The old top-bar links read as prose and people did not know they were
   navigation at all. A Forge-style rail with an icon, a label and a live count per item
   makes each one obviously a place you can go. --- */
.shell{display:flex;min-height:calc(100vh - 56px)}
nav.side{width:var(--nav-w);flex:0 0 var(--nav-w);background:var(--forge-theme-surface);
border-right:1px solid var(--forge-theme-outline);padding:var(--forge-spacing-small) 0;
position:sticky;top:56px;align-self:flex-start;max-height:calc(100vh - 56px);overflow:auto}
nav.side .grp{font:500 11px/1.6 Roboto,sans-serif;text-transform:uppercase;letter-spacing:.09em;
color:var(--forge-theme-text-low);padding:var(--forge-spacing-medium) var(--forge-spacing-medium) var(--forge-spacing-xsmall)}
nav.side a{display:flex;align-items:center;gap:10px;padding:10px var(--forge-spacing-medium);
color:var(--forge-theme-text-high);text-decoration:none;font-size:14px;
border-left:3px solid transparent}
nav.side a:hover{background:var(--forge-theme-primary-container-minimum)}
nav.side a.on{background:var(--forge-theme-primary-container-low);
border-left-color:var(--forge-theme-primary);color:var(--forge-theme-primary);font-weight:500}
nav.side a .ic{width:20px;text-align:center;font-size:15px;opacity:.8}
nav.side a .ct{margin-left:auto;font-size:12px;color:var(--forge-theme-text-medium);
background:var(--forge-theme-surface-container-low);border-radius:10px;padding:0 7px}
nav.side a.on .ct{background:#fff;color:var(--forge-theme-primary)}
nav.side .hint{font-size:11px;color:var(--forge-theme-text-medium);line-height:1.45;
padding:var(--forge-spacing-small) var(--forge-spacing-medium) var(--forge-spacing-medium)}
main.wrap{flex:1;min-width:0;padding:var(--forge-spacing-large);max-width:none}
/* the 12-column table scrolls INSIDE its card rather than stretching the page */
.tblcard{overflow-x:auto}

/* --- surfaces --- */
.bar,.card{background:var(--forge-theme-surface);border:1px solid var(--forge-theme-outline);
border-radius:4px;box-shadow:0 1px 2px rgba(0,0,0,.06)}
.bar{padding:12px var(--forge-spacing-medium);margin-bottom:var(--forge-spacing-medium)}
.card{padding:var(--forge-spacing-medium);margin-bottom:14px}
/* Sized to the Forge scale: heading4 for section titles, body2 (14px) as the body default
   which the Forge typography sheet also applies to <body>, label1 for field labels. */
h2.sec{font:400 24px/1.4 Roboto,sans-serif;letter-spacing:0;
margin:0 0 var(--forge-spacing-small);color:var(--forge-theme-text-high)}
h3.sub{font:500 16px/1.4 Roboto,sans-serif;margin:0 0 6px}
/* Data table, matching the Ops Center Activity table: no outer frame, no header fill,
   hairline row dividers, generous row height, grey sentence-case headers. The old dense
   bordered grid read as a spreadsheet; this reads as a list you scan. */
.tblcard{background:var(--forge-theme-surface);border:1px solid var(--forge-theme-outline);
border-radius:4px;padding:var(--forge-spacing-medium) var(--forge-spacing-large) var(--forge-spacing-small);
box-shadow:0 1px 2px rgba(0,0,0,.06)}
table{width:100%;border-collapse:collapse;background:transparent}
th,td{text-align:left;white-space:nowrap}
/* The question column takes the leftover width and wraps; everything else stays compact.
   Without this, eleven nowrap columns push the one column you actually read out of view. */
td.qcell,th.qcell{white-space:normal;min-width:260px;width:34%}
td.awcell{white-space:normal;max-width:190px}
td.awcell .owner{display:inline-block;max-width:170px;overflow:hidden;text-overflow:ellipsis;
white-space:nowrap;vertical-align:bottom}
th{padding:10px 14px 10px 0;font:500 13px/1.4 Roboto,sans-serif;
color:var(--forge-theme-text-medium);background:none;
border-bottom:1px solid var(--forge-theme-outline)}
th .caret{color:var(--forge-theme-text-low);font-size:10px;margin-left:5px}
td{padding:14px 14px 14px 0;font-size:14px;color:var(--forge-theme-text-high);
border-bottom:1px solid #f0f0f0}
tbody tr:last-child td,table tr:last-child td{border-bottom:0}
tr.row{cursor:pointer}
tr.row:hover td{background:var(--forge-theme-primary-container-minimum)}
tr.row:focus-visible{outline:2px solid var(--forge-theme-primary);outline-offset:-2px}
/* the question stays a real link for middle-click / open-in-new-tab, but loses the
   underline-blue treatment since the whole row is now the target */
td.qcell a{color:var(--forge-theme-text-high);text-decoration:none;font-weight:500}
tr.row:hover td.qcell a{color:var(--forge-theme-primary)}
/* search field above the table, Forge text-field shape */
.searchwrap{position:relative;margin-bottom:6px}
.searchwrap .mag{position:absolute;left:12px;top:50%;transform:translateY(-50%);
color:var(--forge-theme-text-medium);font-size:15px;pointer-events:none}
input.bigsearch{width:100%;padding:13px 14px 13px 38px;font-size:15px;
border:1px solid var(--forge-theme-outline-medium);border-radius:4px;
background:var(--forge-theme-surface)}
input.bigsearch:focus{outline:2px solid var(--forge-theme-primary);outline-offset:-1px}
.searchhelp{font-size:12px;color:var(--forge-theme-text-medium);margin:0 0 var(--forge-spacing-medium)}
.searchhelp code{background:var(--forge-theme-surface-container-minimum);padding:1px 5px;border-radius:3px}
#emptystate a{color:var(--forge-theme-primary);font-weight:500}
/* KPI row of stat tiles. Status colours, each with its own label, so identity is never
   colour-alone. The four coloured states were run through the palette validator: the first
   attempt paired #3f51b5 (ownership) with #1565c0 (pushed) at normal-vision deltaE 5.6 - a hard
   fail, two blues nobody can separate. Ownership was pulled out of the colour space entirely
   (it lives in the nav and in the row tint), leaving pending/suggested/reviewed/pushed, which
   pass every check. `excluded` is deliberately neutral grey - not a categorical slot. */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(126px,1fr));
gap:10px;margin-bottom:var(--forge-spacing-medium)}
.kpi{background:var(--forge-theme-surface);border:1px solid var(--forge-theme-outline);
border-radius:4px;padding:12px 14px;box-shadow:0 1px 2px rgba(0,0,0,.06);
border-top:3px solid var(--kc,var(--forge-theme-outline-low))}
.kpi .v{font:600 26px/1.15 Roboto,sans-serif;color:var(--kc,var(--forge-theme-text-high))}
.kpi .l{font:400 12px/1.4 Roboto,sans-serif;color:var(--forge-theme-text-medium);margin-top:2px}
.kpi.progress{grid-column:span 2}
.kpi .meter{height:6px;border-radius:3px;background:var(--forge-theme-primary-container-low);
margin-top:9px;overflow:hidden}
.kpi .meter i{display:block;height:100%;border-radius:3px;background:var(--kc)}
/* Column-header filter popovers, following the Ops Center Activity pattern: the caret on a
   heading opens a small panel with that column's control and Clear / Close / Update. This
   replaced a permanent filter row under the headings, which cost a whole row of vertical space
   on every screen to show controls that are mostly unused.
   The caret turns solid primary when that column is filtered - otherwise a hidden filter is
   invisible, which is the obvious failure mode of moving filters into popovers. */
th{position:relative}
th button.caretbtn{background:none;border:0;padding:2px 3px;margin-left:4px;cursor:pointer;
color:var(--forge-theme-text-low);font-size:10px;line-height:1;border-radius:2px}
th button.caretbtn:hover{background:var(--forge-theme-surface-container-low);filter:none}
th button.caretbtn.active{color:var(--forge-theme-primary);font-weight:700}
th button.caretbtn.active::after{content:'';position:absolute;top:6px;right:2px;width:5px;
height:5px;border-radius:50%;background:var(--forge-theme-primary)}
.fpop{position:absolute;z-index:45;top:100%;left:0;min-width:236px;
background:var(--forge-theme-surface);border:1px solid var(--forge-theme-outline-low);
border-radius:4px;box-shadow:0 4px 14px rgba(0,0,0,.18);padding:14px;text-align:left;
font-weight:400;white-space:normal}
.fpop[hidden]{display:none}
.fpop .ttl{font:500 13px/1.4 Roboto,sans-serif;color:var(--forge-theme-text-high);
margin-bottom:10px}
.fpop label{font:400 12px/1.4 Roboto,sans-serif;margin:8px 0 3px;text-transform:none}
.fpop .acts{display:flex;gap:6px;align-items:center;justify-content:flex-end;margin-top:14px}
.fpop .acts button{padding:7px 14px}
.fpop .acts .lnk{background:none;border:0;color:var(--forge-theme-primary);
font:500 13px/1 Roboto,sans-serif;cursor:pointer;padding:7px 10px}
.fpop .acts .lnk:hover{background:var(--forge-theme-primary-container-minimum);filter:none}
.youline{font:400 13px/1.5 Roboto,sans-serif;color:var(--forge-theme-text-medium);
margin:0 0 var(--forge-spacing-medium)}
.youline b{color:var(--forge-theme-text-high)}
.shown{font:italic 13px/1.4 Roboto,sans-serif;color:var(--forge-theme-text-medium);
margin:0 0 var(--forge-spacing-small)}
.pill{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;font-weight:500}
.pending{background:var(--forge-theme-warning-container-low);color:var(--forge-theme-warning)}
.reviewed{background:#e6f2e7;color:var(--forge-theme-success)}
.excluded{background:var(--forge-theme-surface-container-low);color:var(--forge-theme-text-medium)}
.pushed{background:var(--forge-theme-info-container-low);color:var(--forge-theme-info)}
.suggested{background:#ede4fb;color:#5b3ba8}
.bad{background:#f6e0e4;color:var(--forge-theme-error)}
.warn{background:var(--forge-theme-warning-container-low);color:var(--forge-theme-warning)}
.q{background:var(--forge-theme-info-container-low);border-left:3px solid var(--forge-theme-info);
padding:10px 12px;border-radius:4px;white-space:pre-wrap}
.a{background:var(--forge-theme-surface-dim);border:1px solid var(--forge-theme-outline);
border-radius:4px;padding:10px 12px;max-height:340px;overflow:auto;white-space:pre-wrap;
font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}
.tools{font-size:12px;color:var(--forge-theme-text-medium);margin:6px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:12px}
label{display:block;font:500 12px/1.4 Roboto,sans-serif;letter-spacing:.01em;
text-transform:none;color:var(--forge-theme-text-medium);margin-bottom:4px}
.hint{font-size:11px;color:var(--forge-theme-text-medium);font-weight:400;text-transform:none;letter-spacing:0}
select,input,textarea{width:100%;padding:7px 8px;border:1px solid var(--forge-theme-outline-medium);
border-radius:4px;font-size:13px;font-family:inherit;background:var(--forge-theme-surface)}
select:focus,input:focus,textarea:focus{outline:2px solid var(--forge-theme-primary);outline-offset:-1px}
textarea{min-height:88px;resize:vertical}
button{background:var(--forge-theme-primary);color:#fff;border:0;padding:9px 16px;border-radius:4px;
font-size:13px;font-weight:500;cursor:pointer;letter-spacing:.02em}
button:hover{filter:brightness(.92)}
button.sec{background:var(--forge-theme-surface);color:var(--forge-theme-primary);
border:1px solid var(--forge-theme-outline-medium)}
button.sec:hover{background:var(--forge-theme-primary-container-minimum);filter:none}
.toast{position:fixed;bottom:18px;right:18px;background:#323232;color:#fff;padding:12px 18px;
border-radius:4px;opacity:0;transition:.25s;z-index:50;box-shadow:0 3px 8px rgba(0,0,0,.3)}
.toast.on{opacity:1}
.nav{display:flex;justify-content:space-between;margin:var(--forge-spacing-medium) 0}
td.qcell{white-space:normal;max-width:430px;min-width:300px}
tr.filters th{background:none;padding:0 14px 10px 0;font-weight:400;border-bottom:1px solid var(--forge-theme-outline)}
tr.filters input,tr.filters select{width:100%;padding:5px 6px;font-size:12px;
border-color:var(--forge-theme-outline);color:var(--forge-theme-text-medium)}
tr.filters small{color:var(--forge-theme-text-low);font-weight:400}
#fbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
#fbar input[type=date]{width:auto;padding:4px 6px;font-size:12px}
td.nowrap,th.nowrap{white-space:nowrap}
tr.row[data-status=excluded] td{opacity:.5}
.deleg{font-size:11px;color:#5b3ba8;font-weight:500}
pre.out{background:#263238;color:#eceff1;padding:12px;border-radius:4px;font-size:12px;
overflow:auto;max-height:280px;line-height:1.5}
tr.row.mine-area td{background:var(--forge-theme-primary-container-minimum)}
tr.row.mine-area td:first-child{box-shadow:inset 3px 0 0 var(--forge-theme-primary)}
tr.row.mine-awaiting td{background:var(--forge-theme-warning-container-low)}
tr.row.mine-awaiting td:first-child{box-shadow:inset 3px 0 0 var(--forge-theme-warning)}
.pill.mineflag{background:var(--forge-theme-warning);color:#fff;margin-left:5px}
tr.row.mine-area .pill.mineflag{background:var(--forge-theme-primary);color:#fff}
span.owner{color:var(--forge-theme-text-medium);font-size:12px}
.fld{position:relative}
button.info{background:var(--forge-theme-primary-container);color:var(--forge-theme-primary);
border:0;border-radius:50%;width:16px;height:16px;padding:0;margin-left:5px;
font:700 11px/16px Roboto,sans-serif;cursor:pointer;vertical-align:middle;
text-transform:none;letter-spacing:0}
button.info:hover{background:var(--forge-theme-primary);color:#fff;filter:none}
.tip{position:absolute;z-index:40;top:100%;left:0;width:340px;max-width:78vw;
background:var(--forge-theme-surface);border:1px solid var(--forge-theme-outline-low);
border-radius:4px;box-shadow:0 4px 14px rgba(0,0,0,.18);padding:12px 14px;font-size:12px;
font-weight:400;text-transform:none;letter-spacing:0;color:var(--forge-theme-text-high)}
.tip[hidden]{display:none}
.tip b{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--forge-theme-text-medium)}
.tip p{margin:6px 0 8px}
.flow{margin:7px 0 0;padding:6px 8px;background:var(--forge-theme-surface-container-minimum);
border-radius:4px;font:11px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;
color:var(--forge-theme-text-medium);white-space:nowrap;overflow:auto}
table.dvt{border:0;border-radius:0;margin:0 0 8px}
table.dvt td{border-bottom:1px solid var(--forge-theme-surface-container-low);
padding:3px 6px 3px 0;font-size:12px;white-space:normal;vertical-align:top}
td.dv{white-space:nowrap;width:1%}
td.dv code{background:var(--forge-theme-surface-container-minimum);padding:1px 5px;
border-radius:3px;font-size:11px}
button.tipclose{padding:3px 10px;font-size:11px}

/* ---------------------------------------------------------------------------------------
   720p (1280x720) and other small laptop screens.

   The default layout needs about 1440px: a 212px rail, 24px padding either side and a
   1180px content column. On a 1280-wide screen that overflows, and on a 720-tall one the
   stacked search field, filter bar and count line push the first table row below the fold.
   Both axes are handled: WIDTH by narrowing the rail and letting the table scroll inside
   its own card, HEIGHT by tightening vertical rhythm rather than hiding anything.
   Nothing is removed at any size - a reviewer on a small screen sees the same data.
   --------------------------------------------------------------------------------------- */
@media (max-width:1439px){
  :root{--nav-w:184px}
  main.wrap{padding:var(--forge-spacing-medium)}
  .tblcard{padding:var(--forge-spacing-small) var(--forge-spacing-medium) var(--forge-spacing-xsmall)}
  th,td{padding-right:10px}
}
@media (max-width:1180px){
  :root{--nav-w:156px}
  nav.side a{padding:9px 10px;font-size:13px;gap:7px}
  nav.side .grp{padding:10px 10px 2px}
  nav.side .hint{display:none}          /* the nav explainer is the first thing to go */
  main.wrap{padding:var(--forge-spacing-small)}
  td{font-size:13px}
}
@media (max-height:820px){
  header{height:48px}
  nav.side{top:48px;max-height:calc(100vh - 48px)}
  .shell{min-height:calc(100vh - 48px)}
  input.bigsearch{padding:9px 12px 9px 36px;font-size:14px}
  .searchhelp{margin-bottom:var(--forge-spacing-small);font-size:11px}
  .bar{padding:8px var(--forge-spacing-medium);margin-bottom:var(--forge-spacing-small)}
  .shown{margin-bottom:var(--forge-spacing-xsmall)}
  th{padding-top:7px;padding-bottom:7px}
  td{padding-top:9px;padding-bottom:9px}   /* still comfortable, ~14 rows visible at 720p */
  .card{padding:12px;margin-bottom:10px}
  h2.sec{font-size:18px;margin-bottom:4px}
  .tip{max-height:60vh;overflow:auto}      /* help panels must not run off a short screen */
}
@media (max-height:700px){
  .searchhelp{display:none}                /* keep the search box, drop its explainer */
}
"""

JS = """
async function post(url,body){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},
body:JSON.stringify(body)});return r.json()}
// Field help. One open at a time, so the page never fills with overlapping panels.
function tip(btn){const w=btn.closest('.fld'); if(!w) return;
const t=w.querySelector('.tip'); const opening=t.hidden;
document.querySelectorAll('.tip').forEach(o=>o.hidden=true);
t.hidden=!opening;}
document.addEventListener('keydown',e=>{if(e.key==='Escape')
document.querySelectorAll('.tip').forEach(o=>o.hidden=true)});
// Click anywhere else closes it. Ignore clicks on the icon (tip() already toggled) and
// inside the panel, so selecting the text in it does not dismiss it.
document.addEventListener('click',e=>{
if(e.target.closest('.tip')||e.target.closest('button.info')) return;
document.querySelectorAll('.tip').forEach(o=>o.hidden=true)});
function toast(m,ok=true){const t=document.getElementById('toast');t.textContent=m;
t.style.background=ok?'#0f6b34':'#a11';t.classList.add('on');setTimeout(()=>t.classList.remove('on'),2600)}
async function saveDoc(path,then){const fields={},ex={};
const rv=document.querySelector('[data-fm=reviewer]');
if(rv&&rv.value){try{localStorage.setItem('lastReviewer',rv.value)}catch(e){}}
document.querySelectorAll('[data-fm]').forEach(e=>fields[e.dataset.fm]=e.value);
document.querySelectorAll('[data-ex]').forEach(e=>ex[e.dataset.ex]=e.value);
const proposed=(document.getElementById('proposed')||{}).value||'';
const r=await post('/save',{path,fields,exchanges:ex,proposed});
if(r.ok){toast('Saved to '+r.path);if(then)location.href=then}else toast(r.error||'Save failed',false)}
async function markAndNext(path,next){document.querySelector('[data-fm=review_status]').value='reviewed';
await saveDoc(path,next)}
// Suggest = "I worked this up but I am not the one who decides." The actor picker is the
// `reviewer` select, so move that name into suggested_by and BLANK reviewer: `reviewer`
// means "who made the call", and mark_pushed/validate_reviews both rely on that. The owner
// puts their own name in reviewer when they accept.
async function suggestAndNext(path,next){const rv=document.querySelector('[data-fm=reviewer]');
const sb=document.querySelector('[data-fm=suggested_by]');
const who=(sb.value||rv.value||'').trim();
if(!who){toast('Pick your name first',false);return}
// saveDoc remembers the actor from the `reviewer` select, which we are about to blank.
try{localStorage.setItem('lastReviewer',who)}catch(e){}
sb.value=who; rv.value='';
document.querySelector('[data-fm=review_status]').value='suggested';
await saveDoc(path,next)}
async function reReview(path){const r=document.querySelector('[data-fm=review_round]');
r.value=String((parseInt(r.value||'1',10)||1)+1);
document.querySelector('[data-fm=review_status]').value='reviewed';
await saveDoc(path)}
async function gitDo(action){const branch=(document.getElementById('branch')||{}).value||'';
const msg=(document.getElementById('cmsg')||{}).value||'';
const r=await post('/git',{action,branch,message:msg});
document.getElementById('gitout').textContent=r.output||'(no output)';toast(r.ok?action+' ok':action+' failed',r.ok)}

// ---- multi-select + bulk mark reviewed -------------------------------------------------
// The reviewer name comes from localStorage, set the first time you pick your name on any
// transcript. Bulk marking without a name is refused server-side; this keeps that visible in
// the UI rather than surfacing as an error after the click.
function ckWho(){let w=null;try{w=localStorage.getItem('lastReviewer')}catch(e){}return w||''}
function ckList(){return [...document.querySelectorAll('tr.row')].filter(tr=>
  tr.style.display!=='none').map(tr=>tr.querySelector('input.ck')).filter(c=>c&&!c.disabled)}
function ckSel(){return ckList().filter(c=>c.checked)}
function ckSync(){const n=ckSel().length;
 const bar=document.getElementById('bulkbar'); if(!bar) return;
 bar.style.display = n ? '' : 'none';
 document.getElementById('cknum').textContent=n;
 const w=document.getElementById('ckwho'); if(w) w.textContent = ckWho() || 'nobody — pick your name on a transcript first';
}
function clearCk(){ckList().forEach(c=>c.checked=false);
 const a=document.getElementById('ckall'); if(a)a.checked=false; ckSync()}
async function bulkReview(){
 const paths=ckSel().map(c=>c.value);
 if(!paths.length) return;
 const who=ckWho();
 if(!who){toast('Open any transcript and pick your name first',false);return}
 if(!confirm(`Mark ${paths.length} transcript(s) reviewed with NO changes needed, as ${who}?`)) return;
 const r=await post('/bulk',{paths,reviewer:who});
 if(!r.ok){toast(r.error||'failed',false);return}
 let m=`${r.done.length} marked reviewed`;
 if(r.skipped&&r.skipped.length){
   m+=` — ${r.skipped.length} skipped`;
   console.log('skipped:',r.skipped);
   alert('Skipped:\n'+r.skipped.map(s=>`• ${s[0]}\n    ${s[1]}`).join('\n'));
 }
 toast(m); location.reload();
}
// Whole-row click-through. Guarded so the controls inside a row still behave: the
// checkbox must toggle without navigating, links must keep their own behaviour (including
// middle-click and cmd-click), and a text selection must not be treated as a click.
document.addEventListener('click',e=>{
 const tr=e.target.closest&&e.target.closest('tr.row'); if(!tr) return;
 if(e.target.closest('input,button,a,label,select,textarea')) return;
 if(e.metaKey||e.ctrlKey||e.shiftKey||e.button!==0) return;
 const sel=window.getSelection&&window.getSelection().toString();
 if(sel&&sel.length>2) return;
 const href=tr.dataset.href; if(href) location.href=href;
});
document.addEventListener('keydown',e=>{
 if(e.key!=='Enter') return;
 const tr=document.activeElement&&document.activeElement.closest&&document.activeElement.closest('tr.row');
 if(tr&&tr.dataset.href&&!e.target.closest('input,button,a,select,textarea')) location.href=tr.dataset.href;
});
document.addEventListener('change',e=>{
 if(e.target.id==='ckall'){const v=e.target.checked;ckList().forEach(c=>c.checked=v);ckSync()}
 else if(e.target.classList&&e.target.classList.contains('ck')) ckSync();
});

// ---- column-header filter popovers ---------------------------------------------------
// Open/close, and mark the caret when that column is actually filtering. Without the marker a
// filter you set is invisible once the popover closes, and you are left wondering why rows are
// missing.
function fpopAll(){return [...document.querySelectorAll('.fpop')]}
function fpop(btn){const pop=btn.parentElement.querySelector('.fpop');const opening=pop.hidden;
 fpopAll().forEach(o=>o.hidden=true);
 pop.hidden=!opening;
 if(opening){const f=pop.querySelector('select,input'); if(f)f.focus()}}
function fpopClose(el){const pop=el.closest('.fpop'); if(pop)pop.hidden=true}
function fpopClear(el){const pop=el.closest('.fpop');
 pop.querySelectorAll('select').forEach(s=>s.value='');
 pop.querySelectorAll('input[type=date]').forEach(i=>i.value='');
 applyFilters(); fpopMarks(); pop.hidden=true}
function fpopUpdate(el){applyFilters(); fpopMarks(); fpopClose(el)}
function fpopMarks(){
 document.querySelectorAll('th button.caretbtn').forEach(b=>{
  const k=b.dataset.fkey; let on=false;
  if(k==='date'){on=!!((document.getElementById('dfrom')||{}).value
                     ||(document.getElementById('dto')||{}).value)}
  else{const e=document.getElementById(k);
       // "open" is the default Status view, so it does not count as a user filter
       on=!!(e&&e.value&&!(k==='f_status'&&e.value==='__open__'))}
  b.classList.toggle('active',on);
 });
}
document.addEventListener('click',e=>{
 if(e.target.closest('.fpop')||e.target.closest('button.caretbtn')) return;
 fpopAll().forEach(o=>o.hidden=true);
});
document.addEventListener('keydown',e=>{if(e.key==='Escape')fpopAll().forEach(o=>o.hidden=true)});

const FKEYS=['agent','ex','fb','status','awaiting','routing','answer','diag','fix'];
function fstate(){const g=i=>{const e=document.getElementById(i);return e?e.value:''};
const o={q:g('f_q'),dfrom:g('dfrom'),dto:g('dto')};
FKEYS.forEach(k=>o[k]=g('f_'+k));return o}
function applyFilters(){const f=fstate();let n=0;
const mineOnly=(document.getElementById('f_mine')||{}).checked;
document.querySelectorAll('tr.row').forEach(tr=>{let ok=true;
 if(mineOnly && !tr.dataset.mine) ok=false;
 if(f.q && !tr.dataset.q.includes(f.q.toLowerCase())) ok=false;
 FKEYS.forEach(k=>{const want=f[k]; if(!want) return;
  const have=tr.dataset[k]||'';
  // __open__ spans both not-yet-closed states. The default used to be status=pending, which
  // hid every suggestion handed to you — the one view an area owner most needs to see.
  if(want==='__open__'){ if(have!=='pending'&&have!=='suggested') ok=false }
  else if(want==='__blank__'){ if(have!=='') ok=false } else if(have!==want) ok=false});
 const d=tr.dataset.date||'';
 if(f.dfrom && (!d || d<f.dfrom)) ok=false;
 if(f.dto && (!d || d>f.dto)) ok=false;
 tr.style.display = ok?'':'none'; if(ok) n++});
const sh=document.getElementById('shown'); if(sh) sh.textContent=n;
// Empty states, worded for the reason. "No results" alone leaves someone stuck wondering
// whether the tool is broken, whether they filtered wrongly, or whether there is genuinely
// nothing for them.
const es=document.getElementById('emptystate'), em=document.getElementById('emptymsg'),
      ea=document.getElementById('emptyact'), tb=document.getElementById('tbl');
if(es&&em){
 if(n===0){
   es.style.display='';
   const others=(f.q||f.dfrom||f.dto||FKEYS.some(k=>f[k]&&f[k]!=='__open__'));
   if(mineOnly&&!others){
     em.textContent='There is nothing that is yours to review.';
     ea.innerHTML='<a href="/?all=1">Click on All transcripts to see all transcripts.</a>';
   } else if(mineOnly){
     em.textContent='Nothing of yours matches these filters.';
     ea.innerHTML='<button class=sec onclick="clearFilters()">Clear the filters</button>'
       +' &nbsp;<a href="/?all=1">or see all transcripts</a>';
   } else {
     em.textContent='No transcripts match these filters.';
     ea.innerHTML='<button class=sec onclick="clearFilters()">Clear the filters</button>';
   }
   if(tb) tb.style.display='none';
 } else { es.style.display='none'; if(tb) tb.style.display=''; }
}
try{sessionStorage.setItem('tfilters',JSON.stringify(f))}catch(e){}
if(window.ckSync)ckSync(); if(window.fpopMarks)fpopMarks();}
function clearFilters(){['f_q','dfrom','dto'].forEach(i=>{const e=document.getElementById(i);if(e)e.value=''});
FKEYS.forEach(k=>{const e=document.getElementById('f_'+k);if(e)e.value=''});
applyFilters()}
function initFilters(){let saved=null;
try{saved=JSON.parse(sessionStorage.getItem('tfilters'))}catch(e){}
const set=(id,v)=>{const e=document.getElementById(id); if(e&&v) e.value=v};
if(saved){set('f_q',saved.q);set('dfrom',saved.dfrom);set('dto',saved.dto);
 FKEYS.forEach(k=>set('f_'+k,saved[k]));}
else{set('f_status','__open__');}  // default view: everything still open (pending + suggested)
// Mine is the default landing view. The server sets data-default-mine on <body>; honour it
// unless the reviewer has already chosen otherwise in this browser session.
if(!saved){const dm=document.body.dataset.defaultMine==='1';
 const c=document.getElementById('f_mine'); if(c&&dm){c.checked=true}}
['f_q','dfrom','dto','f_mine'].concat(FKEYS.map(k=>'f_'+k)).forEach(id=>{
 const e=document.getElementById(id); if(!e)return;
 e.addEventListener((e.tagName==='SELECT'||e.type==='date'||e.type==='checkbox')?'change':'input',applyFilters)});
applyFilters()}

// This block is emitted at the END of the body, so the table above is already parsed.
// Do NOT call initFilters() from inside the table markup: that runs before these
// definitions exist and throws a ReferenceError, leaving the filters inert.
if(document.getElementById('tbl')) initFilters();

// Carry the reviewer between transcripts so a clean batch is one click each.
(function(){const rv=document.querySelector('[data-fm=reviewer]');
 if(!rv||rv.value) return;
 let last=null; try{last=localStorage.getItem('lastReviewer')}catch(e){}
 if(last&&[...rv.options].some(o=>o.value===last)) rv.value=last;})();
"""


def nav_counts():
    """Live counts for the side nav. Cheap enough to recompute per request, and a nav item
    with a number on it is the difference between a link and a to-do list."""
    open_n = mine_n = uncommitted = 0
    for f in tfiles():
        fm, _ = parse(f)
        if fm is None:
            continue
        st = fm.get("review_status", "pending") or "pending"
        if st in ("pending", "suggested"):
            open_n += 1
            if ME and (fm.get("awaiting") == ME
                       or ME in {o for a in effective_agents(fm) for o in owners_of(a)}):
                mine_n += 1
    _, st = git("status", "--porcelain", "--", "transcripts")
    uncommitted = len([l for l in st.splitlines() if l.strip()])
    return open_n, mine_n, uncommitted


def page(title, inner, active="", all_view=False):
    """Shell with a Forge-style SIDE NAV.

    The previous version put "All transcripts" and "Git & PR" as bare links in the app bar,
    where they read as body text - people did not realise they were navigation. A left rail
    with an icon, a label and a live count per item makes each one visibly a destination.
    """
    open_n, mine_n, uncommitted = nav_counts()

    def item(href, icon, label, count=None, key=""):
        on = " class=on" if key and key == active else ""
        badge = f"<span class=ct>{count}</span>" if count else ""
        return (f"<a href=\"{href}\"{on}><span class=ic>{icon}</span>"
                f"<span>{label}</span>{badge}</a>")

    who = (f"<span class=who>{html.escape(ME)}</span>" if ME
           else "<span class=who>not identified</span>")
    side = (
        "<nav class=side>"
        "<div class=grp>Review</div>"
        + (item("/", "&#9873;", "Mine", mine_n or None, "mine") if ME else "")
        + item("/?all=1", "&#9776;", "All transcripts", open_n or None, "all")
        + "<div class=grp>Publish</div>"
        + item("/git", "&#8593;", "Save &amp; share", uncommitted or None, "git")
        + "</nav>")
    return f"""<!doctype html><meta charset=utf-8><title>{html.escape(title)}</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<link rel=stylesheet href="https://cdn.forge.tylertech.com/v1/css/tyler-font.css">
<style>{CSS}</style><header><b>Transcript Review</b>{who}</header>
<body data-default-mine="{'1' if (ME and not all_view) else '0'}">
<div class=shell>{side}<main class=wrap>{inner}</main></div>
<div class=toast id=toast></div><script>{JS}</script>"""


def list_page(show_all=False):
    recs, counts = [], Counter()
    for f in tfiles():
        fm, body = parse(f)
        if fm is None:
            continue
        st = fm.get("review_status", "pending") or "pending"
        counts[st] += 1
        counts["total"] += 1
        deleg = fm.get("delegated_to", "")
        recs.append({
            "rel": f.relative_to(TDIR).as_posix(),
            "q": first_question(body), "qfull": first_question(body, 40),
            "agent": fm.get("answered_by", ""),
            "deleg": ", ".join(a.replace(" Assistant", "").replace(" Agent", "")
                               for a in deleg.split(", ") if a),
            "date": (fm.get("date", "") or "")[:10],
            "ex": fm.get("exchanges", ""),
            "fb": fm.get("foundry_feedback", "none"),
            "status": st,
            "routing": fm.get("routing_verdict", ""),
            "reassign": fm.get("reassign_to", ""),
            "answer": fm.get("answer_verdict", ""),
            "diag": fm.get("diagnosis", ""),
            "fix": fm.get("fix_target", ""),
            "reviewer": fm.get("reviewer", ""),
            "suggested_by": fm.get("suggested_by", ""),
            "awaiting": fm.get("awaiting", ""),
            "eff_agents": effective_agents(fm),
        })
    by_agent, default_owner = agent_owners()
    admin_set = admins()
    for r in recs:
        # A review that says the ROUTING was wrong is a routing problem, and routing belongs to
        # the admins - not to whichever area owner happens to be implicated by the delegation
        # that is being disputed. Assume the router was right until a human says otherwise.
        if r["routing"] == "wrong-agent":
            owners = set(admin_set)
            r["own_basis"] = "wrong-agent -> admins"
        else:
            eff = r["eff_agents"]
            if eff == ["__team__"]:
                owners = set(admin_set)
                r["own_basis"] = "team, no delegation -> admins"
            else:
                owners = set()
                for a in eff:
                    owners |= by_agent.get(a, {default_owner} if default_owner else set())
                r["own_basis"] = "sub-agent: " + ", ".join(eff)
        r["owners"] = sorted(o for o in owners if o)
        # Two DIFFERENT reasons a row is yours, deliberately kept apart:
        #   awaiting == you   -> handed to you personally. Strongest signal.
        #   you own the agent -> yours by area; nobody asked you specifically.
        # Collapsing them would hide the difference between "waiting on me" and "my patch".
        r["mine_awaiting"] = bool(ME and r["awaiting"] == ME)
        r["mine_area"] = bool(ME and ME in owners and not r["mine_awaiting"])

    # newest first — reviewers work the recent tail
    recs.sort(key=lambda r: (r["date"], r["rel"]), reverse=True)

    def opts(key, blank="any"):
        vals = sorted({r[key] for r in recs if r[key]})
        return (f"<option value=''>{blank}</option>"
                + "".join(f"<option>{html.escape(v)}</option>" for v in vals)
                + ("<option value='__blank__'>(blank)</option>" if any(not r[key] for r in recs) else ""))

    rows = []
    for r in recs:
        rows.append(
            "<tr tabindex=0 class='row"
            + (" mine-awaiting" if r["mine_awaiting"] else "")
            + (" mine-area" if r["mine_area"] else "")
            + "'"
            f" data-q=\"{html.escape((r['q'] + ' ' + r['rel']).lower())}\""
            f" data-agent=\"{html.escape(r['agent'])}\" data-date=\"{html.escape(r['date'])}\""
            f" data-ex=\"{html.escape(r['ex'])}\" data-fb=\"{html.escape(r['fb'])}\""
            f" data-status=\"{html.escape(r['status'])}\" data-routing=\"{html.escape(r['routing'])}\""
            f" data-answer=\"{html.escape(r['answer'])}\" data-diag=\"{html.escape(r['diag'])}\""
            f" data-fix=\"{html.escape(r['fix'])}\" data-reviewer=\"{html.escape(r['reviewer'])}\""
            f" data-awaiting=\"{html.escape(r['awaiting'])}\""
            f" data-owner=\"{html.escape(','.join(r['owners']))}\""
            f" data-eff=\"{html.escape(','.join(r['eff_agents']))}\""
            f" title=\"{html.escape(r.get('own_basis',''))}\""
            f" data-mine=\"{'awaiting' if r['mine_awaiting'] else ('area' if r['mine_area'] else '')}\""
            f" data-href=\"/t/{html.escape(r['rel'])}\">"
            f"<td class=nowrap><input type=checkbox class=ck value=\"{html.escape(r['rel'])}\""
            f"{' disabled' if r['status']!='pending' else ''}></td>"
            f"<td class=qcell title=\"{html.escape(r['qfull'])}\">"
            f"<a href='/t/{html.escape(r['rel'])}'>{html.escape(r['q'])}</a></td>"
            f"<td>{html.escape(r['agent'])}"
            f"{'<div class=deleg>&rarr; '+html.escape(r['deleg'])+'</div>' if r['deleg'] else ''}</td>"
            f"<td class=nowrap>{html.escape(r['date'])}</td>"
            f"<td>{html.escape(r['ex'])}</td>"
            f"<td>{'<span class=\'pill warn\'>'+html.escape(r['fb'])+'</span>' if r['fb'] not in ('none','') else ''}</td>"
            f"<td><span class='pill {r['status']}'>{html.escape(r['status'])}</span>"
            f"{'<div class=deleg>'+html.escape(r['suggested_by'])+' &rarr; '+html.escape(r['awaiting'] or 'anyone')+'</div>' if r['status']=='suggested' else ''}</td>"
            f"<td class=awcell>{awaiting_cell(r)}</td>"
            f"<td>{html.escape(r['routing'])}"
            f"{'&rarr;'+html.escape(r['reassign']) if r['reassign'] else ''}</td>"
            f"<td>{html.escape(r['answer'])}</td>"
            f"<td>{html.escape(r['diag'])}</td>"
            f"<td>{html.escape(r['fix'])}</td></tr>")

    tot = counts["total"]
    excl = counts["excluded"]
    done = counts["reviewed"]
    scope = tot - excl
    pct = (100 * done // scope) if scope else 0
    mine_a = sum(1 for r in recs if r["mine_awaiting"])
    mine_r = sum(1 for r in recs if r["mine_area"] and r["status"] in ("pending", "suggested"))

    # One quiet line for identity + the legend, instead of the amber banner that was doing
    # four jobs at once. The counts moved into the tiles; the legend is the only thing left
    # that has to be said in words.
    youline = ""
    if ME:
        bits = []
        if mine_a:
            bits.append(f"<b>{mine_a}</b> awaiting you")
        if mine_r:
            bits.append(f"<b>{mine_r}</b> open in your area")
        youline = ("<p class=youline>"
                   + (" &middot; ".join(bits) if bits else "Nothing open is yours right now.")
                   + " &nbsp;&mdash;&nbsp; amber rows were handed to you, blue rows are your "
                     "area.</p>")

    # (label, filter-kind, select-id). kind: "" = not filterable, "sel" = value dropdown,
    # "date" = From/To range. Order matches the columns rendered per row.
    HEADS = [("First question", "", ""), ("Handled by", "sel", "f_agent"),
             ("Date", "date", ""), ("Ex", "sel", "f_ex"),
             ("Foundry FB", "sel", "f_fb"), ("Status", "sel", "f_status"),
             ("Awaiting", "sel", "f_awaiting"), ("Routing", "sel", "f_routing"),
             ("Answer", "sel", "f_answer"), ("Diagnosis", "sel", "f_diag"),
             ("Fix target", "sel", "f_fix")]

    def hdr(label, kind, fid):
        """A column heading, with its filter tucked into a popover on the caret."""
        cls = " class=qcell" if label == "First question" else ""
        if not kind:
            return f"<th{cls}>{label}</th>"
        if kind == "date":
            inner = ("<div class=ttl>Date</div>"
                     "<label>From</label><input type=date id=dfrom>"
                     "<label>To</label><input type=date id=dto>")
            key = "date"
        else:
            src = fid[2:]
            extra = ("<option value='__open__'>open (pending+suggested)</option>"
                     if fid == "f_status" else "")
            inner = (f"<div class=ttl>{label}</div>"
                     f"<select id={fid}>{extra}{opts(src)}</select>")
            key = fid
        return (f"<th{cls}>{label}"
                f"<button type=button class=caretbtn data-fkey='{key}' "
                f"onclick='fpop(this)' aria-label='Filter by {label}'>&#9662;</button>"
                f"<div class=fpop hidden>{inner}"
                "<div class=acts><button type=button class=lnk onclick='fpopClear(this)'>Clear"
                "</button><button type=button class=lnk onclick='fpopClose(this)'>Close</button>"
                "<button type=button onclick='fpopUpdate(this)'>Update</button>"
                "</div></div></th>")

    def kpi(label, value, colour=None, span=False, meter=None):
        style = f" style='--kc:{colour}'" if colour else ""
        cls = "kpi progress" if span else "kpi"
        bar = (f"<div class=meter><i style='width:{meter}%'></i></div>"
               if meter is not None else "")
        return (f"<div class='{cls}'{style}><div class=v>{value}</div>"
                f"<div class=l>{label}</div>{bar}</div>")

    # Lifecycle states only, in lifecycle order. Ownership is deliberately absent - see the
    # CSS comment. No links on any tile.
    tiles = [kpi("Reviewed of in-scope", f"{done}/{scope}", "#2e7d32", span=True, meter=pct)]
    if counts["pending"]:
        tiles.append(kpi("Pending", counts["pending"], "#d14900"))
    if counts["suggested"]:
        tiles.append(kpi("Suggested", counts["suggested"], "#5b3ba8"))
    if counts["reviewed"]:
        tiles.append(kpi("Awaiting processing", counts["reviewed"], "#2e7d32"))
    if counts["pushed"]:
        tiles.append(kpi("Live in Foundry", counts["pushed"], "#1565c0"))
    tiles.append(kpi("Excluded (pre-go-live)", excl))
    tiles.append(kpi("Transcripts", tot))
    bar = youline + "<div class=kpis>" + "".join(tiles) + "</div>"

    # Search and the narrowing controls on ONE row. Previously the search field, its helper
    # paragraph, the date/mine/clear bar and the count line were four stacked blocks before
    # the table even started.
    search = ("<div class=bar id=fbar style='display:flex;gap:10px;align-items:center;"
              "flex-wrap:wrap'>"
              "<div class=searchwrap style='flex:1 1 260px;margin:0'>"
              "<span class=mag>&#128269;</span>"
              "<input class=bigsearch id=f_q placeholder='Search question or filename&hellip;'>"
              "</div>"
              "<label style='display:inline-flex;align-items:center;gap:5px;font-size:13px;"
              "text-transform:none;letter-spacing:0;font-weight:400;margin:0;white-space:nowrap'>"
              "<input type=checkbox id=f_mine style='width:auto;margin:0'>Only mine</label>"
              "<button class=sec onclick='clearFilters()'>Clear</button></div>"
              f"<p class=shown><b id=shown>0</b> of {tot} shown</p>")


    bulkbar = ("<div class=bar id=bulkbar style='display:none'>"
               "<b><span id=cknum>0</span> selected</b> &nbsp;"
               "<span class=hint>Pending rows only. Anything with a written correction is "
               "skipped and reported.</span>"
               "<div style='margin-top:10px;display:flex;gap:8px;align-items:center;flex-wrap:wrap'>"
               "<button onclick='bulkReview()'>Mark selected reviewed &mdash; no change needed</button>"
               "<button class=sec onclick='clearCk()'>Clear selection</button>"
               "<span class=hint>as <b id=ckwho>?</b></span></div></div>")
    return page("Transcripts", bulkbar + bar + search
                + "<div class=tblcard><table id=tbl><tr>"
                  "<th class=nowrap style='width:1%'>"
                  "<input type=checkbox id=ckall title='select all shown'></th>"
                  + "".join(hdr(*h) for h in HEADS)
                  + "</tr>"
                  + "".join(rows) + "</table>"
                  "<div id=emptystate style='display:none;padding:38px 8px 44px;text-align:center'>"
                  "<div style='font-size:32px;opacity:.35;margin-bottom:10px'>&#9776;</div>"
                  "<div id=emptymsg style='font-size:15px;color:var(--forge-theme-text-medium);"
                  "max-width:430px;margin:0 auto;line-height:1.6'></div>"
                  "<div id=emptyact style='margin-top:16px'></div>"
                  "</div></div>", active=("all" if show_all else "mine"), all_view=show_all)


def doc_popover(k):
    """The ⓘ icon and its hidden panel: what the field means, and what each value commits you
    to. Rendered for every field that has an entry, so a first-time reviewer never has to
    guess at a value they will be held to."""
    d = FIELD_DOC.get(k)
    if not d:
        return "", ""
    rows = "".join(
        f"<tr><td class=dv><code>{html.escape(v) if v else '(blank)'}</code></td>"
        f"<td>{html.escape(t)}</td></tr>"
        for v, t in d.get("values", {}).items())
    table = f"<table class=dvt>{rows}</table>" if rows else ""
    flow = f"<div class=flow>{html.escape(d['flow'])}</div>" if d.get("flow") else ""
    icon = (f"<button type=button class=info onclick=\"tip(this)\" "
            f"aria-label=\"What does {html.escape(k)} mean?\" title=\"What is this?\">i</button>")
    panel = (f"<div class=tip hidden><b>{html.escape(k.replace('_',' '))}</b>{flow}"
             f"<p>{html.escape(d['about'])}</p>{table}"
             f"<button type=button class='sec tipclose' onclick=\"tip(this)\">Close</button></div>")
    return icon, panel


def awaiting_cell(r):
    """Who a transcript is waiting on, plus why the row is highlighted.

    Shows `awaiting` when set. When it is not, falls back to the agent's owner in muted text —
    so a row is never blank in this column, and "nobody has been asked, but this is Jon's area"
    is visible at a glance rather than requiring you to know the mapping.
    """
    if r["awaiting"]:
        badge = " <span class='pill mineflag'>you</span>" if r["mine_awaiting"] else ""
        return f"<b>{html.escape(r['awaiting'])}</b>{badge}"
    if r["owners"]:
        who = ", ".join(r["owners"])
        tag = " <span class='pill mineflag'>your area</span>" if r["mine_area"] else ""
        return f"<span class=owner>{html.escape(who)}</span>{tag}"
    return "<span class=owner>—</span>"


def field(k, val):
    # Label = field name + ⓘ, nothing else. All guidance is in the panel; see FIELD_DOC.
    icon, panel = doc_popover(k)
    lab = f"<label>{k.replace('_',' ')}{icon}</label>"
    if k in PEOPLE_KEYS:
        people = contributors()
        if not people:
            return (f"<div class=fld>{lab}<input data-fm={k} value=\"{html.escape(val)}\" "
                    f"placeholder='contributors.json is empty or unreadable'>{panel}</div>")
        opts = "".join(f"<option{' selected' if o == val else ''}>{html.escape(o)}</option>"
                       for o in [""] + people)
        stale = ("<div class=hint style='color:#a11'>current value "
                 f"'{html.escape(val)}' is not in contributors.json</div>"
                 if val and val not in people else "")
        return f"<div class=fld>{lab}<select data-fm={k}>{opts}</select>{stale}{panel}</div>"
    if k in CHOICES:
        opts = "".join(f"<option{' selected' if o == val else ''}>{html.escape(o)}</option>"
                       for o in CHOICES[k])
        return f"<div class=fld>{lab}<select data-fm={k}>{opts}</select>{panel}</div>"
    return f"<div class=fld>{lab}<input data-fm={k} value=\"{html.escape(val)}\">{panel}</div>"


def detail_page(rel):
    p = (TDIR / rel).resolve()
    if not str(p).startswith(str(TDIR.resolve())) or not p.is_file():
        return None
    fm, body = parse(p)
    if fm is None:
        return page("error", "<div class=card>No frontmatter in this file.</div>")
    order = [f.relative_to(TDIR).as_posix() for f in tfiles()]
    i = order.index(rel) if rel in order else 0
    prev_ = f"/t/{order[i-1]}" if i > 0 else ""
    next_ = f"/t/{order[i+1]}" if i < len(order) - 1 else "/"

    head = (f"<div class=bar><b>{html.escape(fm.get('answered_by',''))}</b> · "
            f"{html.escape(fm.get('date',''))} · {html.escape(fm.get('exchanges','0'))} exchange(s)"
            + (f" · <span class='pill warn'>Foundry: {html.escape(fm['foundry_feedback'])}</span>"
               if fm.get("foundry_feedback") not in ("none", "", None) else "")
            + (f" · <i>{html.escape(fm['dropped_sample_prompts'])} canned prompt(s) omitted</i>"
               if fm.get("dropped_sample_prompts", "0") not in ("0", "") else "")
            + (f"<br><b>Delegated to:</b> {html.escape(fm['delegated_to'])}"
               + (f" <span class=hint>({html.escape(fm.get('orchestration',''))})</span>"
                  if fm.get("orchestration") else "")
               if fm.get("delegated_to") else "")
            + f"<br><small style='color:#6b7280'>{html.escape(rel)} · "
              f"conversation {html.escape(fm.get('conversation_id',''))}</small></div>")

    # A pending transcript renders pre-filled with the "nothing wrong" answer so an
    # untouched form + "Mark reviewed & next" is a deliberate no-change review.
    prefill = dict(fm)
    is_new = (fm.get("review_status", "pending") or "pending") == "pending"
    if is_new:
        for k, v in NO_CHANGE_DEFAULTS.items():
            if not prefill.get(k):
                prefill[k] = v
        prefill.setdefault("review_round", "") or None
        if not prefill.get("review_round"):
            prefill["review_round"] = "1"

    if is_new:
        banner = ("<div class=bar style='background:#eef7ee;border-color:#c6e3c6'>"
                  "Pre-filled as <b>no changes needed</b> — routing correct, answer good, "
                  "nothing to fix. If that is true, just pick your name and hit "
                  "<b>Mark reviewed &amp; next</b>."
                  "<br><b>If it is not true, you do not have to touch the dropdowns.</b> "
                  "Write what the answer <i>should</i> have said under the exchange, and/or "
                  "fill in <b>Proposed fix</b> at the bottom. That prose is the valuable part; "
                  "Claude reads it and fills the classification fields in for you."
                  "</div>")
    elif (fm.get("review_status") or "") == "suggested":
        # Nothing here is a verdict yet. Say so loudly, or the owner reads a filled-in form
        # as settled and rubber-stamps someone else's guess.
        banner = ("<div class=bar style='background:#f3ecfd;border-color:#cdb8f0'>"
                  f"<b>Suggestion from {html.escape(fm.get('suggested_by','?'))}</b>"
                  + (f", handed to <b>{html.escape(fm['awaiting'])}</b>"
                     if fm.get("awaiting") else " — no owner named")
                  + ". <b>Not a verdict.</b> Nothing has been accepted and Claude will not act "
                    "on it. Read the correction and the proposed fix, change what you disagree "
                    "with, then <b>Mark reviewed</b> to accept it under your own name — or "
                    "<b>Suggest</b> again to hand it on.</div>")
    else:
        banner = (f"<div class=bar style='background:#fff6e5;border-color:#e8d3a8'>"
                  f"Already <b>{html.escape(fm.get('review_status',''))}</b> by "
                  f"<b>{html.escape(fm.get('reviewer','?'))}</b> (round "
                  f"{html.escape(fm.get('review_round','1'))}). Saving edits keeps the same round; "
                  f"use <b>Re-review</b> to start a new one.</div>")

    parts = [head, banner, "<div class=card><div class=grid>"
             + "".join(field(k, prefill.get(k, "")) for k in REVIEW_KEYS) + "</div></div>"]

    ci, cp = doc_popover("correction")
    for n, tools, q, a, rv in exchanges_of(body):
        none_tools = "none" in tools.lower()
        parts.append(
            f"<div class=card><b>Exchange {n}</b>"
            f"<div class=tools>Tools called: "
            f"{'<span class=pill.bad>none — answered without searching</span>' if none_tools else html.escape(tools)}</div>"
            f"<div class=q>{html.escape(q)}</div>"
            f"<div style='margin:8px 0 4px;font-size:12px;color:#4a5260'><b>Answer given</b></div>"
            f"<div class=a>{html.escape(a)}</div>"
            f"<div class=fld><label style='margin-top:10px'>Correction{ci}</label>{cp}"
            f"<textarea data-ex={n}>{html.escape(rv)}</textarea></div></div>")

    pi, pp = doc_popover("proposed_fix")
    parts.append(f"<div class=card><div class=fld><label>Proposed fix{pi}</label>{pp}"
                 f"<textarea id=proposed style='min-height:130px'>{html.escape(proposed_of(body))}</textarea>"
                 f"</div></div>")

    parts.append(
        f"<div class=nav><div>{f'<a href=\"{prev_}\"><button class=sec>&larr; Previous</button></a>' if prev_ else ''}</div>"
        f"<div style='display:flex;gap:8px'>"
        f"<button class=sec onclick=\"saveDoc('{html.escape(rel)}')\">Save</button>"
        f"<button class=sec onclick=\"suggestAndNext('{html.escape(rel)}','{next_}')\" "
        f"title='Record this as a suggestion for the area owner, not as your verdict'>"
        f"Suggest &amp; next &rarr;</button>"
        f"<button class=sec onclick=\"reReview('{html.escape(rel)}')\">Re-review</button>"
        f"<button onclick=\"markAndNext('{html.escape(rel)}','{next_}')\">Mark reviewed &amp; next &rarr;</button>"
        f"</div></div>")
    return page(f"{fm.get('answered_by','')} {rel}", "".join(parts))


def git_page():
    """Send a finished batch of reviews in.

    Rewritten as a numbered sequence after a reviewer said plainly they did not understand it.
    The old version was four same-looking buttons with git vocabulary on them - "Create
    branch", "Stage & commit", "Push & open PR" - which assumes you already know what those
    do and in what order. It now reads as three steps, says what each will do BEFORE you
    click, shows what is about to be sent, and disables steps that are not applicable yet.
    """
    _, branch = git("rev-parse", "--abbrev-ref", "HEAD")
    _, st = git("status", "--porcelain", "--", "transcripts")
    changed = [l for l in st.splitlines() if l.strip()]
    n = len(changed)
    on_main = branch in ("main", "master")
    _, ahead = git("rev-list", "--count", "@{u}..HEAD")
    unpushed = (ahead.strip() or "0")

    if n:
        state = (f"<span class='pill pending'>{n} unsent</span> "
                 f"You have <b>{n}</b> reviewed file(s) not yet sent in.")
    elif unpushed != "0":
        state = (f"<span class='pill reviewed'>saved</span> Your work is saved but "
                 f"<b>{unpushed}</b> change(s) have not been shared yet — do step 3.")
    else:
        state = ("<span class='pill pushed'>all sent</span> Nothing waiting. "
                 "Everything you have reviewed has been sent in.")

    files = ("<ul style='margin:6px 0 0 18px;padding:0;font-size:13px'>"
             + "".join(f"<li>{html.escape(l[3:])}</li>" for l in changed[:12])
             + (f"<li>… and {n-12} more</li>" if n > 12 else "")
             + "</ul>") if changed else \
            "<div class=hint style='margin-top:6px'>Nothing changed under transcripts/ yet — " \
            "review something on <b>All transcripts</b> first.</div>"

    body = (
      f"<h2 class=sec>Save &amp; share your reviews</h2>"
      f"<div class=bar>{state}<br><span class=hint>You are working on "
      f"<b>{html.escape(branch)}</b>." + (" That is the shared copy, so step 1 will move you "
      "onto your own copy first." if on_main else "") + "</span></div>"

      "<div class=card><b>What is about to be sent</b>" + files + "</div>"

      "<div class=card><b>Step 1 — put your work on your own copy</b>"
      "<p class=hint style='margin:6px 0 10px'>A personal copy, so your changes cannot disturb "
      "anyone else's. Safe to click twice.</p>"
      "<label>Name for your copy<span class=hint> — anything; a date is fine</span></label>"
      f"<input id=branch value='review/{branch if branch.startswith('review/') else 'batch'}'>"
      "<div style='margin-top:10px'>"
      "<button class=sec onclick=\"gitDo('branch')\">1. Make my own copy</button></div></div>"

      "<div class=card><b>Step 2 — save your reviews</b>"
      "<p class=hint style='margin:6px 0 10px'>Records your reviews locally. Nothing is shared "
      "yet.</p>"
      "<label>What did you review?<span class=hint> — one line, for whoever reads it later</span></label>"
      "<input id=cmsg value='Review transcripts: verdicts and proposed fixes'>"
      "<div style='margin-top:10px;display:flex;gap:8px;flex-wrap:wrap'>"
      "<button class=sec onclick=\"gitDo('commit')\">2. Save my reviews</button>"
      "<button class=sec onclick=\"gitDo('diff')\">Show me exactly what changed</button>"
      "</div></div>"

      "<div class=card><b>Step 3 — send them in for review</b>"
      "<p class=hint style='margin:6px 0 10px'>Opens a <b>change request</b> for someone to check "
      "before it becomes official. This is the step that reaches the team. You get a link back.</p>"
      "<button onclick=\"gitDo('pr')\">3. Send my reviews in</button></div>"

      "<div class=card><b>What happened</b>"
      "<p class=hint style='margin:6px 0 8px'>Output from the last step. If something failed, "
      "paste this to your AI assistant.</p>"
      "<pre class=out id=gitout>"
      + html.escape("\n".join(changed) or "(nothing changed under transcripts/ yet)")
      + "</pre></div>"

      "<div class=card><b>Worth knowing</b><ul class=hint style='margin:6px 0 0 18px;padding:0'>"
      "<li>A review with nothing to fix is still worth sending.</li>"
      "<li>Writing what <i>should</i> have been said is the valuable part — a knowledge-file "
      "change is not required.</li>"
      "<li>Suggestions handed to someone else need sending in too; that is how they reach them.</li>"
      "<li>Only step 3 shares anything.</li>"
      "</ul></div>")
    return page("Save & share", body, active="git")


# ---------------------------------------------------------------- server
class H(BaseHTTPRequestHandler):
    server_version = "TranscriptReview/1.0"

    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        b = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            return self._send(200, list_page(show_all=("all=1" in self.path)))
        if self.path == "/git":
            return self._send(200, git_page())
        if self.path.startswith("/t/"):
            pg = detail_page(unquote(self.path[3:]))
            return self._send(200, pg) if pg else self._send(404, page("404", "Not found"))
        self._send(404, page("404", "Not found"))

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            data = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            return self._send(400, json.dumps({"ok": False, "error": "bad json"}),
                              "application/json")
        if self.path == "/save":
            try:
                rel = data["path"]
                p = (TDIR / rel).resolve()
                if not str(p).startswith(str(TDIR.resolve())) or not p.is_file():
                    raise ValueError("bad path")
                fields = data.get("fields", {})
                allowed = contributors()
                for k in PEOPLE_KEYS:
                    v = (fields.get(k) or "").strip()
                    if v and v not in allowed:
                        raise ValueError(f"{k} '{v}' is not in contributors.json — "
                                         f"add them to the GitHub team and re-run "
                                         f"sync_contributors.py")
                rv = (fields.get("reviewer") or "").strip()
                st = (fields.get("review_status") or "").strip()
                if st in ("reviewed", "excluded") and not rv:
                    raise ValueError("pick a reviewer before marking this reviewed or excluded")
                # A suggestion with nobody's name on it is the whole problem this state exists
                # to solve: the owner inherits a verdict-shaped edit and cannot ask who wrote
                # it or why. Refuse it here rather than letting CI catch it after a push.
                if st == "suggested" and not (fields.get("suggested_by") or "").strip():
                    raise ValueError("a suggestion needs suggested_by — pick your name, then "
                                     "use Suggest (it fills this in for you)")
                # Refuse to drag a pre-go-live conversation into the review queue. Without
                # this, one click of Suggest or Mark reviewed silently overwrote an `excluded`
                # verdict and put months-old internal testing back in front of a reviewer.
                cur_fm, _ = parse(p)
                if is_pre_go_live((cur_fm or {}).get("date", "")) and st in ("reviewed", "suggested"):
                    raise ValueError(
                        f"this conversation is from {(cur_fm or {}).get('date','?')}, before "
                        f"go-live ({GO_LIVE}) — it is internal testing, not user feedback. "
                        f"Leave it 'excluded'. Only post-go-live conversations get reviewed.")
                save(p, fields, data.get("exchanges", {}),
                     data.get("proposed", ""))
                # The reviewer may have written a correction and left the pre-filled
                # "nothing wrong" dropdowns alone — which is an expected way to work, not a
                # mistake. But the file would then assert kb_action: none while its body says
                # the answer was wrong, and the field-driven queries would skip it. Flip
                # action_status to `open` so the state is internally consistent and the work
                # is findable. Deliberately does NOT guess diagnosis/fix_target: that is a
                # judgement from the prose, and Claude records it with its reasoning.
                fm_after, body_after = parse(p)
                if (fm_after and (fm_after.get("review_status") in ("reviewed", "suggested"))
                        and needs_triage(fm_after, body_after or "")):
                    note = fm_after.get("notes", "")
                    mark = "needs-triage: written feedback, fields not classified"
                    upd = {"action_status": "open"}
                    if mark not in note:
                        upd["notes"] = (note + " || " if note else "") + mark
                    set_fields(p, upd)
                refresh_index()
                return self._send(200, json.dumps({"ok": True, "path": rel}), "application/json")
            except Exception as e:
                return self._send(200, json.dumps({"ok": False, "error": str(e)}),
                                  "application/json")
        if self.path == "/bulk":
            # Mark several transcripts reviewed at once. For a batch of thumbs-up
            # conversations that need no correction, one-at-a-time is pure friction.
            #
            # Refuses anything that is NOT a clean no-change review, rather than forcing it:
            #   - already reviewed/pushed/excluded  -> skip, do not silently re-stamp
            #   - pre-go-live                        -> skip, it must stay excluded
            #   - carries WRITTEN feedback           -> skip. A correction someone typed needs
            #     a real verdict, and bulk-stamping it "nothing wrong" would bury it.
            # Every skip is reported with its reason; nothing fails silently.
            try:
                rels = data.get("paths") or []
                who = (data.get("reviewer") or "").strip()
                if not who:
                    raise ValueError("pick your name first — the reviewer box on any "
                                     "transcript, or the filter bar")
                if who not in contributors():
                    raise ValueError(f"'{who}' is not in contributors.json")
                done, skipped = [], []
                for rel in rels:
                    f = (TDIR / rel).resolve()
                    if not str(f).startswith(str(TDIR.resolve())) or not f.is_file():
                        skipped.append((rel, "not found")); continue
                    fm, body = parse(f)
                    if fm is None:
                        skipped.append((rel, "no frontmatter")); continue
                    st = fm.get("review_status", "pending") or "pending"
                    if st not in ("pending",):
                        skipped.append((rel, f"already {st}")); continue
                    if is_pre_go_live(fm.get("date", "")):
                        skipped.append((rel, "pre-go-live — stays excluded")); continue
                    if has_feedback(body or ""):
                        skipped.append((rel, "has written feedback — review it properly")); continue
                    upd = dict(NO_CHANGE_DEFAULTS)
                    upd.update({"review_status": "reviewed", "reviewer": who,
                                "review_round": fm.get("review_round") or "1"})
                    note = fm.get("notes", "")
                    mark = "bulk no-change review"
                    if mark not in note:
                        upd["notes"] = (note + " || " if note else "") + mark
                    set_fields(f, upd)
                    done.append(rel)
                refresh_index()
                return self._send(200, json.dumps({"ok": True, "done": done,
                                                   "skipped": skipped}), "application/json")
            except Exception as e:
                return self._send(200, json.dumps({"ok": False, "error": str(e)}),
                                  "application/json")
        if self.path == "/git":
            act = data.get("action")
            br = (data.get("branch") or "").strip() or "review/batch"
            msg = (data.get("message") or "").strip() or "Review transcripts"
            try:
                if act == "branch":
                    rc, out = git("switch", "-c", br)
                elif act == "commit":
                    git("add", "--", "transcripts")
                    rc, out = git("commit", "-m", msg)
                elif act == "diff":
                    rc, out = git("diff", "--stat", "--", "transcripts")
                elif act == "pr":
                    _, cur = git("rev-parse", "--abbrev-ref", "HEAD")
                    rc, out = git("push", "-u", "origin", cur, timeout=180)
                    if rc == 0:
                        r = subprocess.run(["gh", "pr", "create", "--fill"], cwd=REPO,
                                           capture_output=True, text=True, timeout=180)
                        rc, out = r.returncode, out + "\n" + r.stdout + r.stderr
                else:
                    rc, out = 1, "unknown action"
                return self._send(200, json.dumps({"ok": rc == 0, "output": out}),
                                  "application/json")
            except FileNotFoundError as e:
                return self._send(200, json.dumps({"ok": False, "output": f"missing tool: {e}"}),
                                  "application/json")
            except Exception as e:
                return self._send(200, json.dumps({"ok": False, "output": str(e)}),
                                  "application/json")
        self._send(404, json.dumps({"ok": False}), "application/json")


def main():
    global ME
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=7777)
    ap.add_argument("--me", help="your GitHub username, for highlighting your own rows; "
                                 "defaults to whatever `gh api user` reports")
    ap.add_argument("--no-browser", action="store_true")
    a = ap.parse_args()
    ME = whoami(a.me)
    known = contributors()
    if ME and known and ME not in known:
        # flush=True throughout: stdout is block-buffered when redirected to a file, and
        # serve_forever() never returns, so an unflushed diagnostic is never seen at all.
        print(f"note: '{ME}' is not in contributors.json, so no rows will be marked "
              f"as yours. Pass --me with a registered name if that is wrong.", flush=True)
        ME = None
    if not ME:
        print("note: could not identify you, so no rows are highlighted as yours. "
              "Pass --me <your-github-username>, or check `gh auth status`.", flush=True)
    else:
        by, dflt = agent_owners()
        if not by and not dflt:
            print("note: agent-owners.json is missing or unreadable — no ownership "
                  "highlighting. Row colouring is a convenience; everything else works.",
                  flush=True)
        print(f"you are: {ME}", flush=True)
    if not TDIR.is_dir() or not tfiles():
        sys.exit("No transcripts found. Run: python3 scripts/fetch_transcripts.py")
    url = f"http://127.0.0.1:{a.port}/"
    print(f"Transcript review UI  →  {url}")
    print(f"  {len(tfiles())} transcripts in {TDIR.relative_to(REPO)}/   (Ctrl-C to stop)")
    if not a.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        # loopback only: never expose review data on the network
        ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    except OSError as e:
        sys.exit(f"Could not bind port {a.port}: {e}\nTry --port 7778")


if __name__ == "__main__":
    main()
