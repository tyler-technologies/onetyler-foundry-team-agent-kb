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
import argparse, html, json, os, re, subprocess, sys, webbrowser
from collections import Counter
from datetime import datetime
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


def contributor_map():
    """Full contributor records by github login, for avatars and display names."""
    try:
        d = json.loads(CONTRIB.read_text(encoding="utf-8"))
        return {c["github"]: c for c in d.get("contributors", []) if c.get("github")}
    except Exception:
        return {}


def avatar(login, size=22):
    """A round avatar for a github login: Gravatar when they have one, GitHub otherwise.

    Two sources, in that order, because neither covers everyone:
      - Gravatar needs an email, and most GitHub emails are private (2 of 3 here).
      - GitHub's avatar needs only the numeric id, which is always known.

    `d=404` makes Gravatar 404 rather than serving its generic fallback, which is what lets
    the `onerror` hand off to GitHub instead of silently showing a default for someone who
    does have a real GitHub picture. Initials are the last resort so a row is never blank.

    NOTE: these are remote images, so the browser fetches gravatar.com /
    avatars.githubusercontent.com. Nothing about the transcripts leaves the machine - the
    request carries only an avatar hash or a public user id - but this page is not fully
    offline while avatars are on. Start with --no-avatars to keep it strictly local.
    """
    if not login:
        return ""
    ini = html.escape(login[:2].upper())
    box = (f"width:{size}px;height:{size}px;border-radius:50%;flex:0 0 auto;"
           f"vertical-align:middle;object-fit:cover")
    fallback = (f"<span class=av style=\"{box};display:inline-flex;align-items:center;"
                f"justify-content:center;background:var(--av-fallback-bg);color:var(--av-fallback-fg);"
                f"font-size:{max(8, size // 2 - 2)}px;font-weight:600\">{ini}</span>")
    if NO_AVATARS:
        return fallback
    c = contributor_map().get(login) or {}
    gid, gh_hash = c.get("gh_id"), c.get("gravatar")
    urls = []
    if gh_hash:
        urls.append(f"https://www.gravatar.com/avatar/{gh_hash}?s={size * 2}&d=404")
    if gid:
        urls.append(f"https://avatars.githubusercontent.com/u/{gid}?s={size * 2}&v=4")
    if not urls:
        return fallback
    # Chain the sources through onerror so a dead first choice degrades instead of breaking.
    nxt = urls[1] if len(urls) > 1 else ""
    onerr = (f"this.onerror=null;this.src='{nxt}'" if nxt
             else "this.onerror=null;this.style.display='none'")
    return (f"<img class=av src=\"{urls[0]}\" alt=\"\" loading=lazy "
            f"title=\"{html.escape(login)}\" style=\"{box}\" onerror=\"{onerr}\">")


ASSETS = Path(__file__).resolve().parent / "assets"

# The Tyler "talking Ts", borrowed byte-for-byte from the Ops Center repo so this tool wears
# the same mark as the product it reviews. Served from disk rather than inlined: it is 3 KB
# on every page otherwise, and as a separate file the browser caches it once.
LOGO = ASSETS / "tyler-brand-dark-theme.svg"   # white — the app bar is dark


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


def is_admin(login=None):
    """Admins see across every agent; contributors see their own patch.

    This scopes the UI, and that is ALL it does - it is not an access control. A contributor
    has every transcript on disk in their own git checkout, so hiding the view does not hide
    the data and must never be described as if it did. What it buys is a queue that shows a
    contributor their own work instead of 59 rows that are mostly somebody else's.
    """
    return (login or ME) in admins()


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
# Avatars are the one thing on this page that talks to the internet. Off-switch provided
# so "loopback-only, nothing leaves the machine" stays literally true when it matters.
NO_AVATARS = False

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


def porcelain_path(line):
    """The path out of one `git status --porcelain` line, without counting columns.

    `git()` strips its whole output, which removes the leading space from the FIRST line
    only - so ` M transcripts/x.md` arrives as `M transcripts/x.md`. A fixed `line[3:]`
    then eats a real character and the UI showed `ranscripts/team/...`, missing its `t`.
    Only ever the first row, which is why it reads as a typo rather than a bug.

    Parsing the status code instead of assuming its width fixes it for stripped and
    unstripped lines alike, and handles renames, where porcelain writes `old -> new` and the
    interesting half is the new name.
    """
    s = re.sub(r"^\s*[MADRCU?!]{1,2}\s+", "", line)
    return s.split(" -> ")[-1].strip().strip('"')


# ---------------------------------------------------------------- rendering
# RAW string, for the same reason as JS below. CSS carries backslash escapes too - a
# `content:"\25B8"` disclosure triangle - and Python ate `\25` as an OCTAL escape, producing
# chr(21) + "B8". The page rendered a literal "B" before the heading, which is how it was
# spotted; the triangle simply never appeared. Nothing in CSS wants Python's escapes.
CSS = r"""
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

  /* Tokens beyond Forge's set. Every one of these had been a literal hex somewhere, which is
     what made dark mode a rewrite rather than a switch. */
  --row-line:#f0f0f0;
  --fb-none-fg:#c3c7cc;
  --fb-down-bg:#c0341d;
  --tint-success:#e6f2e7;
  --tint-purple:#ede4fb;
  --tint-error:#f6e0e4;
  --accent-purple:#5b3ba8;
  --av-fallback-bg:#d8dbe0;
  --av-fallback-fg:#41474e;
  --meta-fg:#6b7280;
  --danger-fg:#a11100;
  --shadow-card:0 1px 2px rgba(0,0,0,.06);
  --shadow-pop:0 4px 14px rgba(0,0,0,.18);
  --brand-edge:transparent;
  /* Ink to place ON a filled accent (button, badge, pill). It MUST be a token, because the
     accents inverse between modes: Forge's light primary #3f51b5 is dark and takes white
     text, while its dark primary #8c9eff is LIGHT and does not.
     MEASURED white-on-dark-accent, all of them unreadable:
       primary #8c9eff 2.49:1 · warning #e3c069 1.75:1 · success #5fce8f 1.96:1 · error
       #f0a3a0 2.01:1     (4.5:1 required)
     Dark ink on the same fills: primary 7.10:1, warning 10.08:1.
     This is the failure ops-tools' notes call out twice - a control rendering
     white-on-white or black-on-dark - and it is invisible to anyone reading the CSS,
     because `color:#fff` looks obviously right next to a `background:var(--primary)`. */
  --on-accent:#ffffff;
  /* Pill INK, separate from the accent it derives from. A pill is dark-text-on-pale-tint,
     which is a different contrast problem from white-on-solid-accent, and the accent value
     that works for the latter is too pale for the former.
     FOUND BY scripts/check_contrast.py, which is the whole reason that file exists - these
     three had been shipping under threshold and nobody had measured them:
       .pending/.warn  #d14900 on #f9e9e0 = 3.81:1   -> #a83a00 = 5.43:1
       .reviewed       #2e7d32 on #e6f2e7 = 4.45:1   -> #206b26 = 5.71:1  (4.45 LOOKS fine,
                       which is exactly why it survived; it is still a fail)
     Pill text is 11px, so 4.5:1 applies - the 3:1 large-text allowance does not. */
  --bnr-ok-bg:#eef7ee;    --bnr-ok-bd:#c6e3c6;    --bnr-ok-fg:#1c3d1f;
  --bnr-sug-bg:#f3ecfd;   --bnr-sug-bd:#cdb8f0;   --bnr-sug-fg:#33215c;
  --bnr-done-bg:#fff6e5;  --bnr-done-bd:#e8d3a8;  --bnr-done-fg:#4a3610;
  --pill-warn-fg:#a83a00;
  --pill-ok-fg:#206b26;

  /* KPI tile colours. RE-VALIDATED 2026-08-27 with the dataviz palette validator, which
     rejected what was here before: green #2e7d32 against orange #d14900 was protan ΔE 5.1,
     under the floor of 8 - red-green colourblindness collapses that pair. Fixed by separating
     the two on LIGHTNESS rather than hue, since protanopia preserves lightness and discards
     hue. Now protan ΔE 15.6.
       node scripts/validate_palette.js "#206b26,#f57c00,#5b3ba8" --mode light   -> ALL PASS
     Blue was REMOVED from the space rather than re-stepped: blue against purple was protan
     ΔE 1.4 and no amount of nudging fixed it, so "Closed out" is now neutral - which suits
     it, being the one tile that is finished work and does not need to shout.
     The contrast WARN both palettes carry is discharged by every tile having a visible text
     label; colour here reinforces a label, it is never the only encoding. */
  --kpi-green:#206b26;
  --kpi-amber:#f57c00;
  --kpi-purple:#5b3ba8;
}
/* ------------------------------------------------------------------------------------------
   DARK MODE. Same shape as ops-tools (`/Users/.../tcp-cli/ops-tools/style.css`): the CSS is
   variable-driven, so dark overrides SURFACES, TEXT and ACCENTS only and every rule below is
   written once. `[data-mode]` is set on <html> pre-paint by an inline script, so there is no
   flash of the light theme.

   `color-scheme:dark` is not decoration - it is what makes the browser's own chrome follow:
   scrollbars, the date pickers in the Date filter popover, select dropdowns, and the focus
   ring. Without it those stay light and the page looks half-converted.

   Borrowed and re-measured from ops-tools where it had already solved the same problem, most
   usefully its warning that a DARK BRAND BAR needs a hairline edge: on a dark page the app
   bar and the page beneath it are close enough in luminance that the bar stops reading as a
   bar. Hence --brand-edge.
   ------------------------------------------------------------------------------------------ */
[data-mode="dark"]{
  color-scheme:dark;
  --forge-theme-brand:#1a237e;
  --forge-theme-primary:#8c9eff;
  --forge-theme-primary-container:#2c3560;
  --forge-theme-primary-container-low:#252c4a;
  --forge-theme-primary-container-minimum:#1f2436;
  --forge-theme-surface:#22262c;
  --forge-theme-surface-dim:#16191d;
  --forge-theme-surface-container:#39404a;
  --forge-theme-surface-container-low:#2b313a;
  --forge-theme-surface-container-minimum:#262b32;
  --forge-theme-text-high:#e6e8eb;
  --forge-theme-text-medium:#a3aab4;
  --forge-theme-text-low:#7c838d;
  --forge-theme-outline:#39404a;
  --forge-theme-outline-low:#59616b;
  --forge-theme-outline-medium:#79828e;
  --forge-theme-success:#5fce8f;
  --forge-theme-error:#f0a3a0;
  --forge-theme-warning:#e3c069;
  --forge-theme-info:#8fb6f2;
  --forge-theme-info-container-low:#172742;
  --forge-theme-warning-container-low:#322916;

  --row-line:#2b313a;
  --fb-none-fg:#5b6270;
  /* Kept RED rather than lightened. A thumbs-down badge is a verdict, not a label, and the
     white glyph on it needs a dark fill - the same reasoning ops-tools uses for leaving its
     verdict pills un-overridden in dark. Given a hairline so it defines against the panel. */
  --fb-down-bg:#c0341d;
  --tint-success:#17301f;
  --tint-purple:#261c3a;
  --tint-error:#3a1e1e;
  --accent-purple:#c4a9ef;
  --av-fallback-bg:#39404a;
  --av-fallback-fg:#c3c7cc;
  --meta-fg:#8b929c;
  --danger-fg:#f0a3a0;
  /* Dark conveys elevation with a DEEPER shadow, not a lighter one - a .06 alpha shadow is
     invisible on #16191d. */
  --shadow-card:0 1px 3px rgba(0,0,0,.5);
  --shadow-pop:0 6px 20px rgba(0,0,0,.6);
  --brand-edge:#39404a;
  --on-accent:#16191d;
  /* Dark needs no separate ink: the accents are already light and the tints already dark, so
     the accent IS the right pill colour. Measured on the dark tints - warn 8.20:1,
     success 7.24:1, error 7.55:1, suggested 7.84:1, pushed 7.22:1. */
  --bnr-ok-bg:#17301f;    --bnr-ok-bd:#2f5d40;    --bnr-ok-fg:#c8e6d2;
  --bnr-sug-bg:#261c3a;   --bnr-sug-bd:#443463;   --bnr-sug-fg:#ddccf5;
  --bnr-done-bg:#322916;  --bnr-done-bd:#574727;  --bnr-done-fg:#f0e0bd;
  --pill-warn-fg:var(--forge-theme-warning);
  --pill-ok-fg:var(--forge-theme-success);

  /* Re-stepped for the dark surface, not the light values dimmed - the dataviz validator's
     dark lightness band is L 0.48-0.67 where light's is 0.43-0.77, so the light palette is
     literally out of range. Same lightness-separation trick to keep green and orange apart
     under red-green CVD:
       node scripts/validate_palette.js "#137738,#ce7c22,#9163d5" --mode dark \
            --surface "#22262c"     -> ALL PASS, worst adjacent protan dE 9.3 */
  --kpi-green:#137738;
  --kpi-amber:#ce7c22;
  --kpi-purple:#9163d5;
}

*{box-sizing:border-box}
body{margin:0;font:14px/1.55 Roboto,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
color:var(--forge-theme-text-high);background:var(--forge-theme-surface-dim)}
a{color:var(--forge-theme-primary)}

/* --- app bar --- */
header{background:var(--forge-theme-brand);color:#fff;padding:0 var(--forge-spacing-medium);
height:56px;display:flex;gap:var(--forge-spacing-medium);align-items:center;
position:sticky;top:0;z-index:30;box-shadow:0 1px 3px rgba(0,0,0,.24)}
/* The mark is 12 dots with no bounding box, so it reads as smaller than its box and
   needs less gap to the title than the header's default. Fixed size - it must not
   shrink with the title at narrow widths, or it turns to mush. */
header .brand{flex:0 0 auto;display:block}
/* See --brand-edge in the dark block: transparent in light, a hairline in dark. */
header{border-bottom:1px solid var(--brand-edge)}
/* Mode switch. Sits left of the username - it is chrome, not content, so it belongs with the
   identity block rather than in the page. */
/* margin-left:auto lives on the WRAPPER, not on the control - with it on the control, the
   control was pushed right but the username then sat further right still, leaving it
   stranded mid-bar looking like it belonged to the title. */
.hdrright{margin-left:auto;display:flex;align-items:center;gap:var(--forge-spacing-small);
flex:0 0 auto}
header .who{margin-left:var(--forge-spacing-small)}

/* Display theme: icon button in the bar + a dialog. Geometry and colours copied from
   ops-tools/forge.css rather than approximated, so this matches Ops Center instead of merely
   resembling it: 394px dialog, 36px controls, a bordered toggle group with 2px inset, and a
   RAISED (filled + elevated) Close. */
.fg-iconbtn{display:inline-flex;align-items:center;justify-content:center;width:36px;
height:36px;padding:0;border:0;border-radius:50%;background:transparent;color:#fff;
cursor:pointer;flex:0 0 auto}
.fg-iconbtn:hover{background:rgba(255,255,255,.14);filter:none}
.fg-iconbtn:active{background:rgba(255,255,255,.22)}
.fg-iconbtn:focus-visible{outline:2px solid #fff;outline-offset:2px}
/* fill:currentColor is LOAD-BEARING. These are fill-drawn Material paths with no fill of
   their own, and an unfilled path defaults to black - invisible on the dark app bar. */
.fg-iconbtn svg{width:22px;height:22px;display:block;fill:currentColor}
.fg-dialog-scrim{position:fixed;inset:0;z-index:60;background:rgba(0,0,0,.45);
display:flex;align-items:center;justify-content:center;padding:var(--forge-spacing-large)}
.fg-dialog-scrim[hidden]{display:none}
.fg-dialog{width:394px;max-width:100%;background:var(--forge-theme-surface);
color:var(--forge-theme-text-high);border-radius:4px;
box-shadow:0 8px 10px rgba(0,0,0,.2),0 6px 30px rgba(0,0,0,.12),0 16px 24px rgba(0,0,0,.14);
overflow:hidden}
.fg-dialog h2{margin:0;padding:var(--forge-spacing-large) var(--forge-spacing-large) 0;
font:400 20px/1.4 Roboto,sans-serif;letter-spacing:normal}
.fg-dialog-body{padding:var(--forge-spacing-medium) var(--forge-spacing-large)
var(--forge-spacing-large);text-align:center}
.fg-dialog-body p{margin:0 0 var(--forge-spacing-large);font-size:16px;line-height:22px;
color:var(--forge-theme-text-high);text-align:left}
.fg-toggle-group{display:inline-flex;gap:2px;padding:2px;
border:1px solid var(--forge-theme-outline-low);border-radius:4px}
.fg-toggle{display:inline-flex;align-items:center;gap:2px;height:36px;padding:2px 8px;
border:0;border-radius:2px;background:transparent;color:var(--forge-theme-text-medium);
font:500 14px/1.4 Roboto,sans-serif;cursor:pointer}
.fg-toggle:hover{background:var(--forge-theme-surface-container-low);filter:none}
.fg-toggle.is-selected{background:var(--forge-theme-primary-container-low);
color:var(--forge-theme-primary)}
.fg-toggle-icon{width:18px;height:18px;fill:currentColor}
.fg-dialog-foot{display:flex;justify-content:flex-end;
padding:var(--forge-spacing-xsmall) var(--forge-spacing-medium) var(--forge-spacing-medium)}
.fg-dialog-close{height:36px;padding:0 var(--forge-spacing-medium);
border:1px solid var(--forge-theme-primary);border-radius:4px;
background:var(--forge-theme-primary);color:var(--on-accent);
font:500 14px/1.4 Roboto,sans-serif;letter-spacing:.07em;cursor:pointer;
box-shadow:0 3px 1px -2px rgba(0,0,0,.2),0 2px 2px 0 rgba(0,0,0,.14)}
header{gap:10px}
header b{font-size:16px;font-weight:500;letter-spacing:.01em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
header .who{margin-left:auto;font-size:13px;opacity:.85;white-space:nowrap;flex:0 0 auto}

/* --- SIDE NAV. The old top-bar links read as prose and people did not know they were
   navigation at all. A Forge-style rail with an icon, a label and a live count per item
   makes each one obviously a place you can go. --- */
.shell{display:flex;min-height:calc(100vh - 56px);align-items:stretch}
/* The rail's right-hand rule runs the FULL viewport height, not just as far as the last nav
   item. Sizing it to the viewport (rather than letting it shrink-wrap its content) is what
   makes the boundary continuous - with align-self:flex-start it stopped under "Save & share"
   and left the divider dangling in mid-page. overflow-y:auto keeps a long nav usable if it
   ever outgrows a short screen. */
nav.side{width:var(--nav-w);flex:0 0 var(--nav-w);background:var(--forge-theme-surface);
border-right:1px solid var(--forge-theme-outline);
padding:var(--forge-spacing-small) var(--forge-spacing-small);
position:sticky;top:56px;height:calc(100vh - 56px);overflow-y:auto}
nav.side .grp{font:500 11px/1.6 Roboto,sans-serif;text-transform:uppercase;letter-spacing:.09em;
color:var(--forge-theme-text-low);padding:var(--forge-spacing-medium) var(--forge-spacing-medium) var(--forge-spacing-xsmall)}
nav.side a{display:flex;align-items:center;gap:11px;font-size:14.5px;
padding:11px var(--forge-spacing-medium);border-radius:4px;
color:var(--forge-theme-text-high);text-decoration:none;font-size:14px}
nav.side a:hover{background:var(--forge-theme-primary-container-minimum)}
nav.side a.on{background:var(--forge-theme-primary-container-low);
color:var(--forge-theme-primary);font-weight:500}
nav.side a .ic{width:20px;text-align:center;font-size:15px;opacity:.8}
nav.side a .ct{margin-left:auto;font-size:12px;color:var(--forge-theme-text-medium);
background:var(--forge-theme-surface-container-low);border-radius:10px;padding:0 7px}
nav.side a.on .ct{background:var(--forge-theme-surface);color:var(--forge-theme-primary)}
nav.side .hint{font-size:12.5px;color:var(--forge-theme-text-medium);line-height:1.45;
padding:var(--forge-spacing-small) var(--forge-spacing-medium) var(--forge-spacing-medium)}
main.wrap{flex:1;min-width:0;max-width:none;
padding:var(--forge-spacing-large) var(--forge-spacing-large)
        var(--forge-spacing-large) var(--forge-spacing-large)}
/* the 12-column table scrolls INSIDE its card rather than stretching the page */
.tblcard{overflow-x:auto}

/* --- surfaces --- */
.bar,.card{background:var(--forge-theme-surface);border:1px solid var(--forge-theme-outline);
border-radius:4px;box-shadow:var(--shadow-card)}
.bar{padding:14px 18px;margin-bottom:20px;font-size:13.5px}
/* Card padding and gap, sized against Foundry's own pages rather than chosen. Forge is
   generous here and it is most of what makes the difference between "calm" and "busy": the
   same content in a 16px-padded card with a 14px gap reads as a stack of strips, and in a
   24px-padded card with a 20px gap reads as a panel. */
.card{padding:var(--forge-spacing-large);margin-bottom:20px}
/* A card TITLE has to outrank the body text, or nothing on the page is an entry point. The
   old heading was 14px bold - the same size as body copy and only a weight apart, which is
   why seven cards all looked equally important. 17px/500 with a grey subtitle under it is
   the pattern Foundry uses. */
.card>h3{font:500 17px/1.35 Roboto,sans-serif;margin:0;color:var(--forge-theme-text-high)}
.card>h3+.sub{margin:4px 0 0}
.sub{font:400 13.5px/1.5 Roboto,sans-serif;color:var(--forge-theme-text-medium);margin:0}
.sub li{margin-bottom:5px}

/* Numbered steps INSIDE one card. Previously three separate cards, which made each step a
   peer of the section rather than a part of it. The number is the ordering signal, so the
   headings no longer have to carry "Step 1 -" and the buttons no longer have to carry "1." */
.step{display:flex;gap:14px;padding:20px 0 0;margin-top:20px;
border-top:1px solid var(--row-line)}
.stepnum{flex:0 0 24px;height:24px;border-radius:50%;
background:var(--forge-theme-primary-container-low);color:var(--forge-theme-primary);
font:600 12px/24px Roboto,sans-serif;text-align:center}
.stepbody{flex:1;min-width:0}
.stepbody h4{font:500 15px/1.4 Roboto,sans-serif;margin:0 0 3px;
color:var(--forge-theme-text-high)}
.stepbody .sub{margin-bottom:12px}
.stepacts{margin-top:12px;display:flex;gap:10px;flex-wrap:wrap}
/* The list of saves. A recessed panel, like "About to be sent" - it is a record of what has
   happened, not a control, and giving it a card border would make it compete with the steps. */
.saves{margin-top:14px;background:var(--forge-theme-surface-container-minimum);
border-radius:4px;padding:12px 16px}
details.saves>summary{cursor:pointer;list-style:none;display:flex;align-items:center;
gap:8px;font-weight:500;font-size:13px}
details.saves>summary::-webkit-details-marker{display:none}
details.saves>summary .hint{font-weight:400}
details.saves>summary .chev{margin-left:auto}
.saves>b{font-weight:500;font-size:13px;color:var(--forge-theme-text-medium)}
.saves table{width:100%;border-collapse:collapse;margin-top:8px;font-size:13px}
.saves td{padding:4px 0;vertical-align:top;border:0}
.saves td.swhen{white-space:nowrap;color:var(--forge-theme-text-medium);
font-variant-numeric:tabular-nums;padding-right:12px;width:1%}
.saves td.sstate{text-align:right;white-space:nowrap;width:1%}
/* DIRECT child only. As a descendant selector this also hit the hint inside <summary>,
   pushing it 8px down so the count sat below the heading's baseline instead of on it. */
.saves>.hint{margin-top:8px}
/* Stage list for step 3. Each stage carries a STATE, because the useful information is not
   "here are four things" but "which of them is still owed, and which is not mine to do".
   Merge and Upload are deliberately shown as stages even though neither happens from this
   button - leaving them out is what made people think step 3 finished the job. */
ol.prog{list-style:none;margin:4px 0 0;padding:0}
ol.prog li{position:relative;padding:7px 0 7px 26px;font-size:13.5px;
color:var(--forge-theme-text-high)}
ol.prog li::before{position:absolute;left:0;top:8px;width:16px;height:16px;
border-radius:50%;text-align:center;font:700 10px/16px Roboto,sans-serif}
ol.prog li span{display:block;font-size:12.5px;color:var(--forge-theme-text-medium)}
ol.prog li.wait::before{content:"";border:1.5px solid var(--forge-theme-outline-low);
box-sizing:border-box}
ol.prog li.run::before{content:"";border:1.5px solid var(--forge-theme-primary);
border-top-color:transparent;box-sizing:border-box;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
ol.prog li.done::before{content:"\2713";background:var(--forge-theme-success);
color:var(--on-accent)}
ol.prog li.fail::before{content:"!";background:var(--forge-theme-error);color:var(--on-accent)}
/* A stage that does not apply is greyed and struck, not hidden: "no Foundry upload needed"
   is a useful answer, and hiding the row leaves the question open. */
ol.prog li.none{color:var(--forge-theme-text-low)}
ol.prog li.none b{text-decoration:line-through}
ol.prog li.none::before{content:"\2013";color:var(--forge-theme-text-low)}
ol.prog li.fdry::before{content:"";border:1.5px dashed var(--forge-theme-warning);
box-sizing:border-box}
/* The file list is context for the steps, not a step - a recessed panel says that without
   needing another bordered card. */
.whatsent{background:var(--forge-theme-surface-container-minimum);border-radius:4px;
padding:12px 16px;margin-top:16px;font-size:13.5px}
.whatsent>b{font-weight:500;font-size:13px;color:var(--forge-theme-text-medium)}
.whatsent ul{margin:6px 0 0 18px;padding:0}

/* Reference material, collapsed. It was a permanently-open card competing with the controls
   on every visit; behind a summary it is still one click away and no longer part of the
   page's visual weight. */
details.card>summary{cursor:pointer;list-style:none;display:flex;align-items:center;gap:8px}
details.card>summary::-webkit-details-marker{display:none}
details.card>summary h3{display:inline}
/* The blue circled "i" reuses button.info's treatment so the affordance means the same thing
   here as it does beside every review field - this is explanatory, click it. It is a <span>,
   not a <button>: a button inside a <summary> swallows the click that should toggle it. */
span.info{background:var(--forge-theme-primary-container);color:var(--forge-theme-primary);
border-radius:50%;width:18px;height:18px;flex:0 0 auto;display:inline-flex;
align-items:center;justify-content:center;font:700 12px/1 Roboto,sans-serif}
/* Chevron AFTER the text, not before it: the icon opens the row, the chevron reports its
   state, and they are different jobs that should not sit on top of each other. */
.chev{width:16px;height:16px;flex:0 0 auto;color:var(--forge-theme-text-medium);
font:400 11px/16px Roboto,sans-serif;text-align:center}
.chev::before{content:"\25B8"}
details.card[open]>summary .chev::before{content:"\25BE"}
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
box-shadow:var(--shadow-card)}
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
border-bottom:1px solid var(--row-line)}
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
.kpi[title]{cursor:help}
td.fbcell,th.fbcell{width:1%;text-align:center;padding-left:6px;padding-right:6px}
.fb{font-size:15px;line-height:1;cursor:help}
.fb-none{color:var(--fb-none-fg);cursor:help}
/* The thumbs-down signal lives in its own CELL, not on the row. A row tint or a left bar
   would compete with the amber/blue "this row is yours" highlighting below, and on a row that
   is both, one has to lose - it would be the thumbs-down, since the ownership rules are
   declared later and win on equal specificity. A badge in its own column always shows. */
/* Review banners. These were inline styles, which is why they broke in dark: an inline
   style cannot see [data-mode], so the panel stayed light green while the text went light
   grey with the mode - measured near-invisible on the detail page. The `color` is stated
   explicitly rather than inherited, which is the actual lesson: a tinted panel must own its
   ink, or the ink follows the mode while the panel does not. */
.bar.bnr-ok{background:var(--bnr-ok-bg);border-color:var(--bnr-ok-bd);color:var(--bnr-ok-fg)}
.bar.bnr-sug{background:var(--bnr-sug-bg);border-color:var(--bnr-sug-bd);color:var(--bnr-sug-fg)}
.bar.bnr-done{background:var(--bnr-done-bg);border-color:var(--bnr-done-bd);
color:var(--bnr-done-fg)}
.fb.down{background:var(--fb-down-bg);border-radius:50%;padding:2px 3px 3px;box-shadow:0 0 0 2px var(--forge-theme-surface)}
.who{display:inline-flex;align-items:center;gap:7px}
.whocell{display:inline-flex;align-items:center;gap:6px}
.whocell .av+.av{margin-left:-7px;box-shadow:0 0 0 2px var(--forge-theme-surface)}
.kpi{background:var(--forge-theme-surface);border:1px solid var(--forge-theme-outline);
border-radius:4px;padding:12px 14px;box-shadow:var(--shadow-card);
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
border-radius:4px;box-shadow:var(--shadow-pop);padding:14px;text-align:left;
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
.pending{background:var(--forge-theme-warning-container-low);color:var(--pill-warn-fg)}
.reviewed{background:var(--tint-success);color:var(--pill-ok-fg)}
.excluded{background:var(--forge-theme-surface-container-low);color:var(--forge-theme-text-medium)}
.pushed{background:var(--forge-theme-info-container-low);color:var(--forge-theme-info)}
.suggested{background:var(--tint-purple);color:var(--accent-purple)}
.bad{background:var(--tint-error);color:var(--forge-theme-error)}
.warn{background:var(--forge-theme-warning-container-low);color:var(--pill-warn-fg)}
.q{background:var(--forge-theme-info-container-low);border-left:3px solid var(--forge-theme-info);
padding:10px 12px;border-radius:4px;white-space:pre-wrap}
.a{background:var(--forge-theme-surface-dim);border:1px solid var(--forge-theme-outline);
border-radius:4px;padding:10px 12px;max-height:340px;overflow:auto;white-space:pre-wrap;
font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}
.tools{font-size:12px;color:var(--forge-theme-text-medium);margin:6px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:12px}
label{display:block;font:500 13px/1.5 Roboto,sans-serif;letter-spacing:.01em;
text-transform:none;color:var(--forge-theme-text-medium);margin-bottom:4px}
.hint{font-size:11px;color:var(--forge-theme-text-medium);font-weight:400;text-transform:none;letter-spacing:0}
select,input,textarea{width:100%;padding:7px 8px;border:1px solid var(--forge-theme-outline-medium);
border-radius:4px;font-size:13px;font-family:inherit;background:var(--forge-theme-surface)}
select:focus,input:focus,textarea:focus{outline:2px solid var(--forge-theme-primary);outline-offset:-1px}
textarea{min-height:88px;resize:vertical}
button{background:var(--forge-theme-primary);color:var(--on-accent);border:0;padding:9px 16px;border-radius:4px;
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
.deleg{font-size:11px;color:var(--accent-purple);font-weight:500}
pre.out{background:#263238;color:#eceff1;padding:16px;border-radius:4px;font-size:12.5px;margin-top:14px;
overflow:auto;max-height:520px;line-height:1.55;white-space:pre-wrap;word-break:break-word}
/* Diff tinting. The panel is dark in both display modes, so these need no mode variant.
   Measured against #263238: 8.01 / 6.12 / 7.05 / 5.08 : 1. */
pre.out .dadd{color:#a5d6a7}
pre.out .ddel{color:#ef9a9a}
pre.out .dhunk{color:#80cbc4}
pre.out .dmeta{color:#90a4ae}
tr.row.mine-area td{background:var(--forge-theme-primary-container-minimum)}
tr.row.mine-area td:first-child{box-shadow:inset 3px 0 0 var(--forge-theme-primary)}
tr.row.mine-awaiting td{background:var(--forge-theme-warning-container-low)}
tr.row.mine-awaiting td:first-child{box-shadow:inset 3px 0 0 var(--forge-theme-warning)}
.pill.mineflag{background:var(--forge-theme-warning);color:var(--on-accent);margin-left:5px}
tr.row.mine-area .pill.mineflag{background:var(--forge-theme-primary);color:var(--on-accent)}
span.owner{color:var(--forge-theme-text-medium);font-size:12px}
.fld{position:relative}
button.info{background:var(--forge-theme-primary-container);color:var(--forge-theme-primary);
border:0;border-radius:50%;width:16px;height:16px;padding:0;margin-left:5px;
font:700 11px/16px Roboto,sans-serif;cursor:pointer;vertical-align:middle;
text-transform:none;letter-spacing:0}
button.info:hover{background:var(--forge-theme-primary);color:var(--on-accent);filter:none}
.tip{position:absolute;z-index:40;top:100%;left:0;width:340px;max-width:78vw;
background:var(--forge-theme-surface);border:1px solid var(--forge-theme-outline-low);
border-radius:4px;box-shadow:var(--shadow-pop);padding:12px 14px;font-size:12px;
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
  header b{font-size:14px}
  :root{--nav-w:156px}
  nav.side a{padding:10px 12px;font-size:13px;gap:8px}
  nav.side .grp{padding:12px 12px 2px}
  nav.side .hint{display:none}          /* the nav explainer is the first thing to go */
  main.wrap{padding:var(--forge-spacing-medium) var(--forge-spacing-medium)}
  td{font-size:13px}
}
@media (max-height:820px){
  header{height:48px}
  nav.side{top:48px;height:calc(100vh - 48px)}
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

# RAW string, deliberately. This block is JavaScript, so JS must own its own escapes: in a
# plain """...""" Python eats them first, and `alert('Skipped:\n')` became a real newline inside
# a single-quoted JS literal - a SyntaxError that killed the ENTIRE script block, so every
# filter, popover, checkbox and row-click on the page was inert. Introduced 7459127 and not
# caught because the row counts it appeared to prove are rendered server-side.
# Keep `node --check` in the test below; it is what found this.
JS = r"""
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
// Stage states for step 3's progress list. Only `push` and `pr` are driven from here,
// because they are the only two this button performs; `merge` and `foundry` stay as they were
// rendered, which is the honest picture - they are somebody's next action, not this click's.
// The output panel's heading tracks what is in it: the pending diff before any step runs,
// a step's output afterwards. One heading for both would be wrong half the time.
function setOutHead(action){
 const h=document.getElementById('outhead'), s=document.getElementById('outsub');
 if(!h||!s)return;
 if(action==='diff'){h.textContent='Your changes';
   s.textContent='Every edit you have made and not yet sent in. Green is added, red is removed.';
 } else {h.textContent='Output';
   s.textContent='From the step you just ran. If something failed, paste this to your AI '
     +'assistant.';}
}
function stage(name,state){const el=document.querySelector('#prog li[data-stage='+name+']');
 if(!el||el.classList.contains('none'))return;
 el.classList.remove('wait','run','done','fail'); el.classList.add(state);}
// No `branch` field any more — the branch is chosen server-side per sitting and never shown.
async function gitDo(action){const msg=(document.getElementById('cmsg')||{}).value||'';
if(action==='pr'){stage('push','run')}
const r=await post('/git',{action,message:msg});
if(action==='pr'){
 // One request does both the push and the PR, so the push is only knowable as "it got far
 // enough to try the PR". Read that off the output rather than claiming both succeeded.
 const madePr=/pull\/\d+|already exists|https:\/\/github\.com/.test(r.output||'');
 stage('push', r.ok||madePr ? 'done':'fail');
 stage('pr', r.ok&&madePr ? 'done' : (r.ok?'done':'fail'));
}
const el=document.getElementById('gitout');
// Prefer the server's tinted markup (escaped in diff_html) so a diff shown by the
// button reads the same as the one rendered on load; fall back to text.
setOutHead(action);
if(r.html){el.innerHTML=r.html}else{el.textContent=r.output||'(no output)'}
el.scrollTop=0;toast(r.ok?action+' ok':action+' failed',r.ok)}

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
const SHOW_ALL_LINK=document.body.dataset.showAll==='1';
const FKEY_STORE='tfilters:'+(document.body.dataset.defaultMine==='1'?'mine':'all');
function fstate(){const g=i=>{const e=document.getElementById(i);return e?e.value:''};
const o={q:g('f_q'),dfrom:g('dfrom'),dto:g('dto')};
FKEYS.forEach(k=>o[k]=g('f_'+k));return o}
function applyFilters(){const f=fstate();let n=0;
// The server already removed everyone else's rows on the My Transcripts view, so there is no
// row-level mine test left to do here. This flag only picks the right empty-state wording.
const mineOnly=document.body.dataset.defaultMine==='1';
document.querySelectorAll('tr.row').forEach(tr=>{let ok=true;
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
   // Which empty is this? Three of them, and they need different advice:
   //   nothing pending  -> ONE filter is hiding your rows; say which, and offer to drop it
   //   nothing matching  -> your own filters; offer to clear them
   //   nothing yours     -> the scope itself is empty; nothing you can do here
   const dflt=document.body.dataset.defaultStatus||'';
   const onlyDefaultStatus=(f.f_status===dflt&&dflt&&!f.q&&!f.dfrom&&!f.dto
     &&!FKEYS.some(k=>k!=='f_status'&&f[k]));
   const anyFilter=(f.q||f.dfrom||f.dto||FKEYS.some(k=>f[k]));
   const total=document.querySelectorAll('tr.row').length;
   const seeAll=SHOW_ALL_LINK
     ? ' &nbsp;<a href="/?all=1">or see All Transcripts</a>' : '';
   if(mineOnly&&total===0){
     em.textContent='There is nothing assigned to you \u2014 no transcript is waiting on you '
       +'by name, and none of the agents you own has an open conversation.';
     ea.innerHTML=SHOW_ALL_LINK
       ? '<a href="/?all=1">Click on All Transcripts to see all transcripts.</a>'
       : '<button class=sec onclick="syncNow()">Sync transcripts</button>';
   } else if(mineOnly&&onlyDefaultStatus){
     em.innerHTML='Nothing of yours is <b>'+dflt.replace(/__/g,'')+'</b>. '
       +'You have '+total+' transcript(s) in total \u2014 remove the <b>Status</b> filter to '
       +'see them all.';
     ea.innerHTML='<button onclick="dropStatus()">Show all '+total+' of my transcripts</button>';
   } else if(mineOnly&&anyFilter){
     em.textContent='Nothing of yours matches these filters.';
     ea.innerHTML='<button class=sec onclick="clearFilters()">Clear the filters</button>'+seeAll;
   } else {
     em.textContent='No transcripts match these filters.';
     ea.innerHTML='<button class=sec onclick="clearFilters()">Clear the filters</button>';
   }
   if(tb) tb.style.display='none';
 } else { es.style.display='none'; if(tb) tb.style.display=''; }
}
try{sessionStorage.setItem(FKEY_STORE,JSON.stringify(f))}catch(e){}
if(window.ckSync)ckSync(); if(window.fpopMarks)fpopMarks();}
// Sync pulls new conversations from Foundry. Long-running (it walks every agent), so the
// button reports progress rather than appearing dead, and the page only reloads on success -
// a failure that reloaded away its own error message would be untraceable.
function syncNow(){const b=document.getElementById('syncbtn'),m=document.getElementById('syncmsg');
 if(!b||b.disabled)return; b.disabled=true; b.textContent='Syncing\u2026';
 m.textContent='pulling from Foundry, this can take a minute';
 fetch('/sync',{method:'POST'}).then(r=>r.json()).then(d=>{
  if(d.ok){m.textContent=d.added?('added '+d.added+' new \u2014 reloading'):'no new transcripts';
   if(d.added){location.reload();return}
   b.disabled=false;b.innerHTML='\u21bb Sync transcripts';
  } else {m.innerHTML='<span style="color:var(--danger-fg)">sync failed: '
    +(d.error||'see the terminal for details').replace(/</g,'&lt;')+'</span>';
   b.disabled=false;b.innerHTML='\u21bb Sync transcripts';}
 }).catch(e=>{m.innerHTML='<span style="color:var(--danger-fg)">sync failed: '+e+'</span>';
  b.disabled=false;b.innerHTML='\u21bb Sync transcripts';});}
// Drop just the Status filter, leaving everything else. The one-click version of the advice
// the empty state gives, because "remove the Status filter" means finding a caret in a column
// header you were not looking at.
function showStatus(v){const e=document.getElementById('f_status');
 if(e){e.value=v;applyFilters()}}
function dropStatus(){const e=document.getElementById('f_status');
 if(e){e.value='';applyFilters()}}
function clearFilters(){['f_q','dfrom','dto'].forEach(i=>{const e=document.getElementById(i);if(e)e.value=''});
FKEYS.forEach(k=>{const e=document.getElementById('f_'+k);if(e)e.value=''});
applyFilters()}
function initFilters(){let saved=null;
try{saved=JSON.parse(sessionStorage.getItem(FKEY_STORE))}catch(e){}
const set=(id,v)=>{const e=document.getElementById(id); if(e&&v) e.value=v};
if(saved){set('f_q',saved.q);set('dfrom',saved.dfrom);set('dto',saved.dto);
 FKEYS.forEach(k=>set('f_'+k,saved[k]));}
else{set('f_status',document.body.dataset.defaultStatus||'__open__');}
// My Transcripts opens on `pending` — the work still to start. Clearing the Status filter
// widens it to everything of yours, which is the point: the filter is removable, the
// ownership scope is not.
['f_q','dfrom','dto'].concat(FKEYS.map(k=>'f_'+k)).forEach(id=>{
 const e=document.getElementById(id); if(!e)return;
 e.addEventListener((e.tagName==='SELECT'||e.type==='date'||e.type==='checkbox')?'change':'input',applyFilters)});
applyFilters()}

// This block is emitted at the END of the body, so the table above is already parsed.
// Do NOT call initFilters() from inside the table markup: that runs before these
// definitions exist and throws a ReferenceError, leaving the filters inert.
if(document.getElementById('tbl')) initFilters();

// ---- display theme ----------------------------------------------------------------------
// The <head> script already applied the mode; this wires the icon button, the dialog and the
// OS listener. Structure follows ops-tools/forge-shell.js.
(function(){
 const root=document.documentElement;
 const btn=document.getElementById('themebtn'), scrim=document.getElementById('themescrim');
 const osDark=()=>window.matchMedia('(prefers-color-scheme: dark)').matches;
 const ICON={};  // filled from the markup, so the paths live in exactly one place
 document.querySelectorAll('.fg-toggle').forEach(t=>{
   const pth=t.querySelector('path'); if(pth) ICON[t.dataset.modeSet]=pth.getAttribute('d');
 });
 function paint(){
   const pref=root.dataset.modePref||'auto';
   root.dataset.mode = pref==='auto' ? (osDark()?'dark':'light') : pref;
   // THE BAR ICON SHOWS THE RESOLVED THEME, NOT THE SETTING — so under Automatic the bar
   // still answers "which am I in?", which is the question you have when looking at it.
   const shown=root.dataset.mode==='dark'?'dark':'light';
   if(btn&&ICON[shown]){
     const svg=btn.querySelector('path'); if(svg) svg.setAttribute('d',ICON[shown]);
     const lbl='Display theme ('+pref+')'; btn.title=lbl; btn.setAttribute('aria-label',lbl);
   }
   document.querySelectorAll('.fg-toggle').forEach(t=>{
     const on=t.dataset.modeSet===pref;
     t.classList.toggle('is-selected',on); t.setAttribute('aria-pressed',String(on));
   });
 }
 function open(){ if(scrim){scrim.hidden=false;
   const s=scrim.querySelector('.fg-toggle.is-selected')||scrim.querySelector('.fg-toggle');
   if(s)s.focus();} }
 function close(){ if(scrim){scrim.hidden=true; if(btn)btn.focus();} }
 if(btn) btn.addEventListener('click',()=>{paint();open()});
 if(scrim) scrim.addEventListener('click',e=>{
   const tg=e.target.closest('.fg-toggle');
   if(tg){ root.dataset.modePref=tg.dataset.modeSet;
     try{localStorage.setItem('foundry-review-mode',tg.dataset.modeSet)}catch(err){}
     paint(); return; }
   // The scrim itself or Close dismisses. The group is always populated, so there is no
   // "off" state to handle.
   if(e.target.closest('.fg-dialog-close')||e.target===scrim) close();
 });
 document.addEventListener('keydown',e=>{
   if(e.key==='Escape'&&scrim&&!scrim.hidden) close();
 });
 // Automatic follows the OS, so repaint when the OS flips - without a reload. A stale Auto
 // that only updates on navigation is the bug people report as "dark mode doesn't work".
 try{
  window.matchMedia('(prefers-color-scheme: dark)')
    .addEventListener('change',()=>{ if((root.dataset.modePref||'auto')==='auto') paint(); });
 }catch(e){}
 paint();
})();

// Carry the reviewer between transcripts so a clean batch is one click each.
(function(){const rv=document.querySelector('[data-fm=reviewer]');
 if(!rv||rv.value) return;
 let last=null; try{last=localStorage.getItem('lastReviewer')}catch(e){}
 if(last&&[...rv.options].some(o=>o.value===last)) rv.value=last;})();
"""


# Display theme, built the way ops-tools/forge-shell.js builds it, because that was checked
# against the live Ops Center rather than invented: Forge does NOT put a theme control in the
# app bar. It puts a single ICON there - a sun or a moon - which opens a "Display theme"
# dialog holding a three-way Light / Dark / Automatic toggle group and a raised Close.
#
# The first cut here was a three-button strip sitting in the bar. It worked, but it is not the
# pattern, and it put a persistent tri-state control in the busiest 40px of the page.
#
# Two details from that file that are easy to get wrong and worth keeping:
#   - THE BAR ICON SHOWS THE RESOLVED THEME, NOT THE SETTING. Under "Automatic" it shows a
#     moon at night and a sun by day, so the bar still answers "which am I in?" - which is the
#     question you actually have when looking at it.
#   - The icon paths are Material glyphs lifted from Forge (wb_sunny,
#     moon_waning_crescent, settings_brightness), drawn as FILLS. They carry
#     fill="currentColor" via CSS; a path with no fill defaults to BLACK, which is invisible
#     on a dark bar - a bug ops-tools' notes call out explicitly.
THEME_ICONS = {
    "light": ("M6.76 4.84 4.96 3.05 3.55 4.46l1.79 1.79zM4 10.5H1v2h3zm9-9.95h-2V3.5h2zm7.45 "
              "3.91-1.41-1.41-1.79 1.79 1.41 1.41zm-3.21 13.7 1.79 1.8 1.41-1.41-1.8-1.79zM20 "
              "10.5v2h3v-2zm-8-5c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6-2.69-6-6-6m-1 "
              "16.95h2V19.5h-2zm-7.45-3.91 1.41 1.41 1.79-1.8-1.41-1.41z"),
    "dark": "M2 12a10 10 0 0 0 13 9.54 10 10 0 0 1 0-19.08A10 10 0 0 0 2 12",
    "auto": ("M21 3H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2m0 "
             "16.01H3V4.99h18zM8 16h2.5l1.5 1.5 1.5-1.5H16v-2.5l1.5-1.5-1.5-1.5V8h-2.5L12 "
             "6.5 10.5 8H8v2.5L6.5 12 8 13.5zm4-7c1.66 0 3 1.34 3 3s-1.34 3-3 3z"),
}
THEME_MODES = [("light", "Light", "light", "Use light theme"),
               ("dark", "Dark", "dark", "Use dark theme"),
               ("auto", "Automatic", "auto", "Use your browser's setting")]


def _svg(path, cls):
    return (f"<svg class={cls} viewBox='0 0 24 24' aria-hidden=true>"
            f"<path d='{path}'/></svg>")


MODE_SWITCH = (
    "<button type=button class=fg-iconbtn id=themebtn aria-haspopup=dialog "
    "aria-label='Display theme'>" + _svg(THEME_ICONS["light"], "fg-icon") + "</button>"
    "<div class=fg-dialog-scrim id=themescrim hidden>"
    "<div class=fg-dialog role=dialog aria-modal=true aria-labelledby=themetitle>"
    "<h2 id=themetitle>Display theme</h2>"
    "<div class=fg-dialog-body>"
    "<p>Choose what theme you would like to use for this application.</p>"
    "<div class=fg-toggle-group role=group aria-label='Display theme'>"
    + "".join(
        f"<button type=button class=fg-toggle data-mode-set={v} aria-pressed=false "
        f"title=\"{tip}\">{_svg(THEME_ICONS[icon], 'fg-toggle-icon')}"
        f"<span>{label}</span></button>"
        for v, label, icon, tip in THEME_MODES)
    + "</div></div>"
      "<div class=fg-dialog-foot>"
      "<button type=button class=fg-dialog-close>Close</button>"
      "</div></div></div>")


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

    who = (f"<span class=who>{avatar(ME, 24)}<span>{html.escape(ME)}</span></span>" if ME
           else "<span class=who>not identified</span>")
    side = (
        "<nav class=side>"
        "<div class=grp>Review</div>"
        + (item("/", "&#9873;", "My Transcripts", mine_n or None, "mine") if ME else "")
        # Admins only. For a contributor the item would be a link to other people's work they
        # cannot push to - an invitation to a dead end. An unidentified user gets it too,
        # because with no `me` there is no "mine" to fall back to and an empty app is worse.
        + (item("/?all=1", "&#9776;", "All Transcripts", open_n or None, "all")
           if (is_admin() or not ME) else "")
        + "<div class=grp>Save &amp; Publish</div>"
        + item("/git", "&#8593;", "Save &amp; Share", uncommitted or None, "git")
        + "</nav>")
    return f"""<!doctype html><meta charset=utf-8><title>{html.escape(title)}</title>
<meta name=viewport content="width=device-width,initial-scale=1">
<!-- Set the mode BEFORE the stylesheet, so the first paint is already correct. Deferring this
     to the main script at the bottom of the page gives a visible white flash on every
     navigation in dark mode, which is worse than not having dark mode at all. Same approach as
     ops-tools/index.html. Wrapped in try/catch because a browser with storage disabled must
     still render - it just falls back to following the OS. -->
<script>
(function(){{try{{
  var m=localStorage.getItem("foundry-review-mode")||"auto";
  document.documentElement.dataset.modePref=m;
  document.documentElement.dataset.mode = m==="auto"
    ? (window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light") : m;
}}catch(e){{document.documentElement.dataset.mode="light";
  document.documentElement.dataset.modePref="auto";}}}})();
</script>
<link rel=stylesheet href="https://cdn.forge.tylertech.com/v1/css/tyler-font.css">
<link rel=icon type="image/svg+xml" href="/logo.svg">
<style>{CSS}</style><header><img class=brand src="/logo.svg" alt="Tyler Technologies" width=28 height=28><b>OneTyler Foundry Team Agent Transcript Review</b><div class=hdrright>{MODE_SWITCH}{who}</div></header>
<body data-default-mine="{'1' if (ME and not all_view) else '0'}" data-default-status="{'pending' if (ME and not all_view) else '__open__'}" data-show-all="{'1' if (is_admin() or not ME) else '0'}">
<div class=shell>{side}<main class=wrap>{inner}</main></div>
<div class=toast id=toast></div><script>{JS}</script>"""


def list_page(show_all=False):
    recs = []
    for f in tfiles():
        fm, body = parse(f)
        if fm is None:
            continue
        st = fm.get("review_status", "pending") or "pending"
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

    # My Transcripts is a HARD filter, applied here rather than by a checkbox in the browser.
    # The nav item IS the filter: two views that differ only by a tickbox you have to find are
    # two views that look identical, which is exactly how this read before. So under My
    # Transcripts the other rows are not present at all - clearing the column filters widens
    # the view within your own rows and never reveals someone else's.
    # Everything owed to me: handed to me by name, plus everything my agents own - which for
    # an admin includes every routing-level row, since those belong to all admins.
    mine_only = bool(ME) and not show_all
    total_all = len(recs)
    if mine_only:
        recs = [r for r in recs if r["mine_awaiting"] or r["mine_area"]]

    counts = Counter()
    for r in recs:
        counts[r["status"]] += 1
        counts["total"] += 1

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
            f"<td class=fbcell>{fb_glyph(r['fb'])}</td>"
            f"<td class=qcell title=\"{html.escape(r['qfull'])}\">"
            f"<a href='/t/{html.escape(r['rel'])}'>{html.escape(r['q'])}</a></td>"
            f"<td>{html.escape(r['agent'])}"
            f"{'<div class=deleg>&rarr; '+html.escape(r['deleg'])+'</div>' if r['deleg'] else ''}</td>"
            f"<td class=nowrap>{html.escape(r['date'])}</td>"
            f"<td>{html.escape(r['ex'])}</td>"
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
    # "Reviewed" here means "a human has ruled on it" - which a closed-out transcript also
    # satisfies. Counting only `reviewed` made a fully-processed queue read as 0% done.
    done = counts["reviewed"] + counts["pushed"]
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
            bits.append(f"<a href='#' onclick='showStatus(\"\");return false'>"
                        f"<b>{mine_a}</b> awaiting you</a>")
        if mine_r:
            bits.append(f"<b>{mine_r}</b> open in your area")
        youline = ("<p class=youline>"
                   + (" &middot; ".join(bits) if bits else "Nothing open is yours right now.")
                   + " &nbsp;&mdash;&nbsp; amber rows were handed to you, blue rows are your "
                     "area.</p>")

    # (label, filter-kind, select-id). kind: "" = not filterable, "sel" = value dropdown,
    # "date" = From/To range. Order matches the columns rendered per row.
    # Feedback sits FIRST, left of the question: a thumbs-down is the strongest signal on the
    # page about which row to open, and it was buried five columns in where you had to already
    # be reading the row to find it. Rare, too - 2 of 59 - so it has to be findable by scanning
    # one narrow column rather than by reading.
    HEADS = [("&#128077;&#128078;", "sel", "f_fb"),
             ("First question", "", ""), ("Handled by", "sel", "f_agent"),
             ("Date", "date", ""), ("Ex", "sel", "f_ex"),
             ("Status", "sel", "f_status"),
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
            # The feedback column's heading is a pair of glyphs, which makes a poor popover
            # title - name it in words there.
            ttl = "Foundry feedback" if fid == "f_fb" else label
            inner = (f"<div class=ttl>{ttl}</div>"
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

    def kpi(label, value, colour=None, span=False, meter=None, why=""):
        style = f" style='--kc:{colour}'" if colour else ""
        cls = "kpi progress" if span else "kpi"
        bar = (f"<div class=meter><i style='width:{meter}%'></i></div>"
               if meter is not None else "")
        tip = f" title=\"{html.escape(why)}\"" if why else ""
        return (f"<div class='{cls}'{style}{tip}><div class=v>{value}</div>"
                f"<div class=l>{label}</div>{bar}</div>")

    # Lifecycle states only, in lifecycle order. Ownership is deliberately absent - see the
    # CSS comment. No links on any tile.
    # The progress tile is deliberately wider than the rest: it is the only one carrying a
    # bar, and a 2px-tall bar in a 150px tile is unreadable. It spans two columns to earn the
    # bar its width. When there is nothing in scope there is no progress to draw, so it drops
    # to a plain tile rather than rendering an empty trough.
    tiles = [kpi("Reviewed of in-scope" + (" (yours)" if mine_only else ""),
                 f"{done}/{scope}", "var(--kpi-green)", span=bool(scope),
                 meter=pct if scope else None,
                 why=("Of the transcripts in this view that are in scope, how many carry a "
                      "human verdict. In scope means everything except pre-go-live testing. "
                      "Wider than the other tiles because it is the only one with a bar."
                      + (" This view is filtered to your rows only." if mine_only else "")))]
    if counts["pending"]:
        tiles.append(kpi("Awaiting review", counts["pending"], "var(--kpi-amber)",
                         why="Nobody has looked at these yet."))
    if counts["suggested"]:
        tiles.append(kpi("Suggested", counts["suggested"], "var(--kpi-purple)",
                         why="Someone worked these up but left the decision to the area "
                             "owner. Not yet a verdict."))
    if counts["reviewed"]:
        tiles.append(kpi("Reviewed, not yet actioned", counts["reviewed"], "var(--kpi-green)",
                         why="A human verdict is recorded and Claude has not yet processed "
                             "it. This is the queue work comes from."))
    if counts["pushed"]:
        # "Live in Foundry" read as though the TRANSCRIPTS were in Foundry. They are not - the
        # knowledge-file changes they caused are. Renamed to describe the transcript's own
        # state, with the Foundry part explained in the tooltip.
        tiles.append(kpi("Closed out", counts["pushed"],
                         why="Fully done: reviewed, processed, and any resulting knowledge "
                             "change is live in Foundry and verified. Nothing further owed."))
    tiles.append(kpi("Excluded", excl,
                     why="Pre-go-live internal testing - conversations from before the chatbot "
                         "shipped on 2026-08-19. Not real user feedback, so out of scope."))
    tiles.append(kpi("Transcripts", tot, why="Every conversation collected, in scope or not."))
    # Sync sits at the top of both list views: it is the first thing you want when you sit
    # down, and burying it behind the terminal defeats the point of a UI.
    title = "My Transcripts" if (ME and not show_all) else "All Transcripts"
    head = ("<div style='display:flex;align-items:center;gap:12px;flex-wrap:wrap;"
            "margin-bottom:var(--forge-spacing-medium)'>"
            f"<h2 class=sec style='margin:0'>{title}</h2>"
            "<button class=sec id=syncbtn onclick='syncNow()' style='margin-left:auto'>"
            "&#8635; Sync transcripts</button>"
            "<span class=hint id=syncmsg style='font-size:12px'></span></div>")
    bar = head + youline + "<div class=kpis>" + "".join(tiles) + "</div>"

    # Search and the narrowing controls on ONE row. Previously the search field, its helper
    # paragraph, the date/mine/clear bar and the count line were four stacked blocks before
    # the table even started.
    search = ("<div class=bar id=fbar style='display:flex;gap:10px;align-items:center;"
              "flex-wrap:wrap'>"
              "<div class=searchwrap style='flex:1 1 260px;margin:0'>"
              "<span class=mag>&#128269;</span>"
              "<input class=bigsearch id=f_q placeholder='Search question or filename&hellip;'>"
              "</div>"
              "<button class=sec onclick='clearFilters()'>Clear</button></div>"
              f"<p class=shown><b id=shown>0</b> of {tot} shown"
              + (f" &middot; <span class=hint>{total_all - tot} other row(s) hidden &mdash; "
                 "this view is only yours</span>" if mine_only and total_all > tot else "")
              + "</p>")


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


def fb_glyph(fb):
    """The user's own rating, as one scannable character.

    "THUMBS_DOWN" in a pill was 11 characters of shouting for something that occurs twice in
    59 rows, and it pushed the question column right. A glyph keeps the column narrow enough
    to scan and puts the wording in the tooltip, where it is still available.

    Colour is NOT the only encoding: the two glyphs differ in shape, so this survives
    colourblindness and a greyscale print.
    """
    if fb == "THUMBS_UP":
        return ("<span class='fb up' title='The user gave this answer a thumbs up in Foundry'>"
                "&#128077;</span>")
    if fb == "THUMBS_DOWN":
        return ("<span class='fb down' title='The user gave this answer a thumbs DOWN in "
                "Foundry - read this one first'>&#128078;</span>")
    # No rating is the norm, and an icon for it would drown the two that matter.
    return "<span class=fb-none title='The user did not rate this answer'>&middot;</span>"


def awaiting_cell(r):
    """Who a transcript is waiting on, plus why the row is highlighted.

    Shows `awaiting` when set. When it is not, falls back to the agent's owner in muted text —
    so a row is never blank in this column, and "nobody has been asked, but this is Jon's area"
    is visible at a glance rather than requiring you to know the mapping.
    """
    if r["awaiting"]:
        badge = " <span class='pill mineflag'>you</span>" if r["mine_awaiting"] else ""
        return (f"<span class=whocell>{avatar(r['awaiting'], 20)}"
                f"<b>{html.escape(r['awaiting'])}</b></span>{badge}")
    if r["owners"]:
        faces = "".join(avatar(o, 20) for o in r["owners"])
        tag = " <span class='pill mineflag'>your area</span>" if r["mine_area"] else ""
        return (f"<span class=whocell>{faces}"
                f"<span class=owner>{html.escape(', '.join(r['owners']))}</span></span>{tag}")
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
        stale = ("<div class=hint style='color:var(--danger-fg)'>current value "
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
            + f"<br><small style='color:var(--meta-fg)'>{html.escape(rel)} · "
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
        banner = ("<div class='bar bnr-ok'>"
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
        banner = ("<div class='bar bnr-sug'>"
                  f"<b>Suggestion from {html.escape(fm.get('suggested_by','?'))}</b>"
                  + (f", handed to <b>{html.escape(fm['awaiting'])}</b>"
                     if fm.get("awaiting") else " — no owner named")
                  + ". <b>Not a verdict.</b> Nothing has been accepted and Claude will not act "
                    "on it. Read the correction and the proposed fix, change what you disagree "
                    "with, then <b>Mark reviewed</b> to accept it under your own name — or "
                    "<b>Suggest</b> again to hand it on.</div>")
    else:
        banner = (f"<div class='bar bnr-done'>"
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
            f"<div style='margin:8px 0 4px;font-size:12px;color:var(--forge-theme-text-medium)'><b>Answer given</b></div>"
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


# The branch for this sitting, remembered for the lifetime of the server process.
#
# It is just a git branch, and there is nothing in it for a reviewer to decide: the name is
# generated, the timing is forced, and the answer is always "yes, do it". So it is no longer a
# step on the page - it happens on the first save of a sitting and is reported afterwards.
#
# "Per sitting" == per server run, which is the honest boundary: the server is started when
# someone sits down to review ("get me set up for reviewing") and every save in that session
# should land on one branch, not one branch per click. A sitting resumed after a restart is
# recognised by already BEING on a review/ branch.
SITTING_LANE = None


def lane_name():
    """A fresh lane name: username for whose it is, timestamp because a name must be unique.

    `git switch -c` is the one git call in this whole flow that can collide - it fails
    outright if the branch exists, where a commit is always a new commit and `gh pr create`
    refuses rather than overwriting. Hence the timestamp: the username alone collides the
    second time the same person sits down.
    """
    who = ME or "batch"
    return f"review/{who}/{datetime.now().strftime('%m%d%Y-%H%M%S')}"


def current_lane():
    """The branch a save would land on right now, without creating anything.

    Returns (name, is_shared). `is_shared` means "we are on a branch reviews must not land
    on", which is what triggers auto-creation on save.
    """
    _, cur = git("rev-parse", "--abbrev-ref", "HEAD")
    cur = cur.strip()
    if cur.startswith("review/"):
        return cur, False
    if SITTING_LANE:
        return SITTING_LANE, False
    return cur, True


def ensure_lane():
    """Put us on this sitting's review branch, creating it if needed. Returns (name, created).

    Called from the save action rather than from a button. Idempotent: once a sitting has a
    lane, every later save in that sitting goes to the same one.
    """
    global SITTING_LANE
    name, shared = current_lane()
    if not shared:
        # Already on the right branch, or on a remembered lane we have drifted off.
        _, cur = git("rev-parse", "--abbrev-ref", "HEAD")
        if cur.strip() != name:
            git("switch", name)
        SITTING_LANE = name
        return name, False
    name = lane_name()
    # Branch from origin/main, NOT from wherever HEAD happens to be. `git switch -c <name>`
    # with no start point inherits every commit on the current branch, so a reviewer who
    # happened to be sitting on somebody's feature branch would open a change request
    # containing that person's unmerged work alongside their own three review edits. That is
    # the "the PR is a revert in disguise" failure, and it is invisible in the UI because the
    # page only ever shows the reviewer's own diff.
    #
    # Uncommitted work follows a switch, so the reviewer's edits come along; only the history
    # is left behind.
    git("fetch", "origin", "main", timeout=120)
    rc, out = git("switch", "-c", name, "origin/main")
    if rc != 0:
        # A dirty file that differs between the two branches blocks the switch. Falling back
        # to HEAD is better than refusing to save, but say which happened - the resulting
        # change request will carry more than the reviewer expects.
        rc2, out2 = git("switch", "-c", name)
        if rc2 != 0:
            raise RuntimeError(f"could not set your work aside: {out}\n{out2}")
        SITTING_LANE = name
        return name, True
    SITTING_LANE = name
    return name, True


# `git commit` returns 1 both for "nothing to commit" and for a real failure. They need
# telling apart: sending in reviews that were already saved is normal, a broken commit is not.
NOTHING_TO_SAVE = 99


def save_reviews(msg):
    """Put this sitting on its own branch if needed, then commit the reviewer's work.

    This is "Save my reviews", and it is also the first thing "Send my reviews in" does. The
    branch part is invisible: it happens here rather than as a step on the page, because it is
    just a git branch with no decision in it.

    Stages BOTH the trees a contributor legitimately edits. Staging only `transcripts` was a
    silent data-loss trap: a reviewer whose feedback led them to fix a Knowledge-* file got
    "saved ok" with the knowledge edit left out, to be lost at the next branch switch.
    Deliberately NOT `git add -A` - scripts/, .github/ and CLAUDE.md are admin-only (hard rule
    6), and sweeping them into a review commit is how a contributor would accidentally ship an
    instruction change. Anything dirty outside the two trees is reported, not staged.
    """
    lane, created = ensure_lane()
    lines = []
    if created:
        # Said in plain terms, without the word "branch": the reviewer did not ask for this
        # and should not have to know what it is, but silence about it would be worse.
        lines.append("Your work has been set aside from everyone else's, so it cannot "
                     "disturb the shared copy while it is being checked.")
    paths = ["transcripts"] + sorted(d.name for d in REPO.iterdir()
                                     if d.is_dir() and d.name.startswith("Knowledge-"))
    git("add", "--", *paths)
    rc, out = git("commit", "-m", msg)
    if rc != 0 and "nothing to commit" in out.lower():
        rc, out = NOTHING_TO_SAVE, "Nothing new to save — everything is already saved."
    lines.append(out)
    _, left = git("status", "--porcelain")
    skipped = [porcelain_path(l) for l in left.splitlines()
               if l.strip() and not l.strip().startswith("??")]
    if skipped:
        lines.append("NOT saved — outside transcripts/ and Knowledge-*/, so not part of a "
                     "review:\n" + "\n".join(f"  {s}" for s in skipped))
    return rc, "\n\n".join(x for x in lines if x)


def unsent_saves():
    """Saves that have NOT been sent in yet - nothing else.

    Deliberately not "every save since the last request". Once a save is inside a change
    request there is no longer an action attached to it, so listing it is history for its own
    sake; the only reason to read this list is to answer "is there anything of mine still
    sitting on this laptop?" Filtering to that makes the list short enough to be read at a
    glance and makes an EMPTY list meaningful.

    No fetch here: this runs on every page render and a network call would make the page hang
    on a bad connection. It compares against the last-known origin/main, which is what the
    rest of the page does too.
    """
    _, cur = git("rev-parse", "--abbrev-ref", "HEAD")
    cur = cur.strip()
    rc, _ = git("rev-parse", "--verify", "--quiet", "origin/main")
    if rc != 0:
        return []
    rc, out = git("log", "--format=%h%x09%ad%x09%s", "--date=format:%m/%d %H:%M",
                  "origin/main..HEAD")
    if rc != 0 or not out.strip():
        return []
    # Which of them are already on the remote, i.e. already inside a change request.
    sent = set()
    rc2, _ = git("rev-parse", "--verify", "--quiet", f"origin/{cur}")
    if rc2 == 0:
        _, pushed = git("log", "--format=%h", f"origin/main..origin/{cur}")
        sent = {l.strip() for l in pushed.splitlines() if l.strip()}
    rows = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[0] not in sent:
            rows.append({"h": parts[0], "when": parts[1], "subject": parts[2]})
    return rows


def auto_commit_message():
    """Used when the reviewer leaves the label box empty, which is the expected case.

    Carries the git user and a timestamp. Git records both itself, so this is redundant in
    `git log` - but it is NOT redundant where it actually gets read: "Send my reviews in" runs
    `gh pr create --fill`, which takes the change request's TITLE from the first commit. A
    generic title makes a list of open requests from several reviewers unreadable, and the
    timestamp separates one sitting from the same person's next one.

    Prefers git's configured name over the GitHub login, since that is the identity actually
    recorded on the commit; falls back to the login, then to something rather than nothing.
    """
    _, who = git("config", "user.name")
    who = who.strip() or ME or "unknown reviewer"
    return f"Reviews by {who} — {datetime.now().strftime('%m%d%Y-%H%M%S')}"


# A diff can be long, so it is capped - but the cap is STATED on the page rather than
# silently truncating, because a diff that stops early without saying so reads as "that is
# everything that changed", which is the one thing it must never imply.
DIFF_MAX_LINES = 1200


def diff_html(text):
    """A git patch as tinted, escaped HTML for the output panel.

    Colour carries the same information git's own terminal output does: an unstyled patch is
    a wall of monospace where +/- have to be read character by character. The panel is dark
    in BOTH display modes (it is a terminal, not a surface), so one palette serves both.
    MEASURED against the panel #263238: added 8.01:1, removed 6.12:1, hunk 7.05:1, meta
    5.08:1 - all over 4.5:1.
    """
    lines = (text or "").splitlines()
    clipped = len(lines) - DIFF_MAX_LINES
    out = []
    for ln in lines[:DIFF_MAX_LINES]:
        e = html.escape(ln)
        # Order matters: +++/--- are FILE HEADERS and must be tested before +/-, or they get
        # tinted as though they were an added and a removed line.
        if ln.startswith(("+++", "---", "diff --git", "index ", "new file", "deleted file",
                          "similarity index", "rename ")):
            cls = "dmeta"
        elif ln.startswith("@@"):
            cls = "dhunk"
        elif ln.startswith("+"):
            cls = "dadd"
        elif ln.startswith("-"):
            cls = "ddel"
        else:
            cls = ""
        out.append(f"<span class={cls}>{e}</span>" if cls else e)
    if clipped > 0:
        out.append(f"<span class=dmeta>… {clipped} more line(s) not shown — run "
                   f"`git diff -- transcripts` for the rest</span>")
    return "\n".join(out)


def review_diff():
    """What the reviewer has actually changed, as a patch.

    `git diff` covers tracked edits, which is what a review IS - verdicts and prose typed into
    existing transcript files. Untracked files are NOT diffed, only named: an untracked file
    under transcripts/ is a conversation `fetch_transcripts.py` just pulled, so its whole body
    would render as one enormous addition and bury the three lines the reviewer typed. They
    still need to know it is there, hence the list.
    """
    # Same scope as step 2 stages, or the panel would show a reviewer less than the button
    # is about to save - which is how the transcripts-only staging bug stayed invisible.
    scope = ["transcripts"] + sorted(d.name for d in REPO.iterdir()
                                     if d.is_dir() and d.name.startswith("Knowledge-"))
    _, patch = git("diff", "--", *scope)
    _, st = git("status", "--porcelain", "--", *scope)
    new = [porcelain_path(l) for l in st.splitlines() if l.strip().startswith("??")]
    parts = []
    if new:
        parts.append("# new transcript file(s), not yet saved — pulled by Sync, "
                     "nothing typed by you:\n"
                     + "\n".join(f"#   {f}" for f in new))
    if patch.strip():
        parts.append(patch)
    if not parts:
        return "(nothing changed under transcripts/ yet)"
    return "\n\n".join(parts)


# Which corpus folder feeds which Foundry collection. Same table as
# scripts/check_foundry_drift.py; kept here so the page can name the collections a batch will
# affect rather than saying "Foundry" vaguely.
FOLDER_COLLECTION = {
    "Knowledge-OpsCenter": "OT-OpsCenter",
    "Knowledge-BP-General": "OT-BPD",
    "Knowledge-SupportAccessCenter": "OT-SAC",
    "Knowledge-AlignedReleases": "OT-AlignedReleases",
    "Knowledge-TylerIdentity": "TCP-KB-Identity",
    "Knowledge-Shared": "all five collections",
}


def pending_foundry_uploads():
    """Collections this batch will need uploading to, or [] if none.

    "Push to Foundry" is NOT part of step 3 and must not be wired into it. Two rules make that
    a design constraint rather than a preference:
      - hard rule 5: a Foundry write is a production change, confirmed with the user, never a
        side effect of another action;
      - nothing reaches Foundry until it is MERGED to main - and step 3 is the thing that
        opens the pull request, so at that instant the change is by definition unmerged.
    So the page's job is to say honestly what is owed and when, which is also the answer to
    "is there any push to Foundry at all?" - most review batches touch only transcripts and
    owe nothing.
    """
    _, committed = git("diff", "--name-only", "origin/main...HEAD")
    _, working = git("status", "--porcelain")
    paths = [l.strip() for l in committed.splitlines() if l.strip()]
    paths += [porcelain_path(l) for l in working.splitlines() if l.strip()]
    cols = []
    for path in paths:
        folder = path.split("/")[0]
        col = FOLDER_COLLECTION.get(folder)
        if col and col not in cols:
            cols.append(col)
    return cols


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
             + "".join(f"<li>{html.escape(porcelain_path(l))}</li>" for l in changed[:12])
             + (f"<li>… and {n-12} more</li>" if n > 12 else "")
             + "</ul>") if changed else \
            "<div class=hint style='margin-top:6px'>Nothing changed under transcripts/ yet — " \
            "review something on <b>All transcripts</b> first.</div>"

    # SEVEN stacked cards of identical weight is what made this page read as busy: every block
    # had the same border, the same 14px bold heading and the same padding, so nothing looked
    # more important than anything else and the eye had no entry point. Restructured to three
    # cards, matching how Foundry's own pages group content - a card is a CATEGORY, and the
    # steps within it are steps, not peers of it.
    #
    #   before                                  after
    #   status bar                              status bar  (absorbs "about to be sent")
    #   What is about to be sent   -----------> Publish your reviews
    #   Step 1  ------------------------------>   step 1 / 2 / 3 inside it
    #   Step 2  ------------------------------>
    #   Step 3  ------------------------------>
    #   What happened             -----------> What happened
    #   Worth knowing             -----------> Worth knowing  (collapsed <details>)
    #
    # "Worth knowing" is now collapsed: it is reference material that was competing with the
    # controls every single visit.
    fdry = pending_foundry_uploads()
    saves = unsent_saves()
    if saves:
        # COLLAPSED by default. It is a record of what already happened, so it is the last
        # thing anyone needs on arrival - and left open it pushes the two actual buttons down
        # the page, which is the "busy" problem this page was rewritten to fix. The count sits
        # in the summary so the section answers its own question without being opened.
        saves_html = (
            "<details class=saves><summary>See progress history"
            f"<span class=hint> &mdash; <b>{len(saves)}</b> save(s) not sent in yet</span>"
            "<span class=chev aria-hidden=true></span></summary>"
            "<table>" + "".join(
                f"<tr><td class=swhen>{html.escape(s['when'])}</td>"
                f"<td>{html.escape(s['subject'])}</td></tr>"
                for s in saves)
            + "</table>"
            "<div class=hint>Sending them in covers all of these at once. A save drops off "
            "this list as soon as it has been sent.</div></details>")
    else:
        saves_html = ("<div class=saves><span class=hint>Nothing saved and unsent — either "
                      "you have not saved yet this sitting, or everything is already sent "
                      "in.</span></div>")

    def step(num, title, desc, inner):
        return (f"<div class=step><div class=stepnum>{num}</div><div class=stepbody>"
                f"<h4>{title}</h4><p class=sub>{desc}</p>{inner}</div></div>")

    body = (
      f"<h2 class=sec>Save &amp; Share your reviews</h2>"
      # NO BRANCH NAME HERE, deliberately. This line used to read "You are working on
      # feature/owner-highlighting", which is git vocabulary a reviewer has no use for and
      # cannot act on. The branch is handled entirely server-side now - see ensure_lane().
      f"<div class=bar>{state}</div>"

      "<div class=card>"
      "<h3>Publish your reviews</h3>"
      "<p class=sub>Nothing leaves your machine until you send it in. The first step is "
      "optional.</p>"
      "<div class=whatsent><b>About to be sent</b>" + files + "</div>"
      # There used to be a step before these two: name a branch and click a button to create
      # it. It is gone. It was just a git branch, there was no decision in it - the name was
      # generated, the timing forced, and the answer always "yes" - and the owner of this repo
      # could not tell from the page what it did, which is decisive evidence no contributor
      # would. It now happens on the first save of a sitting and is never mentioned.
      # "Save progress", not "Save your reviews". It IS a local git commit, and "progress" is
      # the word that carries the two things a reviewer needs to know about it: it is a
      # checkpoint, and it is not finished. "Save your reviews" sounded like it did something
      # WITH the reviews. Optional, too - step 2 saves first, so nobody is stuck by skipping
      # this.
      + step(1, "Save progress",
             "A checkpoint on this machine (local git commit) you can go back to. Optional — "
             "sending them in saves first anyway. Nothing is shared yet; if the laptop died "
             "now, the work would go with it.",
             # Empty by DEFAULT, not prefilled. A prefilled box asks to be read, edited and
             # worried about; an empty one labelled "optional" asks for nothing. Blank is
             # handled server-side by auto_commit_message().
             "<label>Optional label for your changes<span class=hint> — leave blank and your "
             "name and the time are used</span></label>"
             "<input id=cmsg value='' placeholder='e.g. identity transcripts, first pass'>"
             "<div class=stepacts>"
             "<button class=sec onclick=\"gitDo('commit')\">Save progress</button>"
             "<button class=sec onclick=\"gitDo('diff')\">Show me exactly what changed</button>"
             "</div>" + saves_html)
      + step(2, "Send them in — and on to Foundry",
             "The first point your work exists anywhere other than this laptop, and the step "
             "that reaches the team (PR into Repo). What follows depends on what you changed, "
             "so the stages below say exactly what is still owed.",
             "<ol class=prog id=prog>"
             "<li data-stage=push class=wait><b>Upload to GitHub</b>"
             "<span>your work, kept apart from everyone else's until it is checked "
             "(git push of your own branch)</span></li>"
             "<li data-stage=pr class=wait><b>Create the change request</b>"
             "<span>someone checks it before it becomes official (a GitHub pull "
             "request)</span></li>"
             "<li data-stage=merge class=wait><b>Merge</b>"
             "<span>done by a reviewer, not from here (merged into main)</span></li>"
             + ("<li data-stage=foundry class='wait fdry'><b>Upload to Foundry</b>"
                f"<span>{html.escape(', '.join(fdry))} &mdash; only after the merge, and "
                "only with your say-so. Nothing reaches the live agents before then.</span>"
                "</li>"
                if fdry else
                "<li data-stage=foundry class=none><b>Upload to Foundry</b>"
                "<span>not needed &mdash; this batch changes transcript reviews only, and "
                "reviews are not agent knowledge</span></li>")
             + "</ol>"
             "<div class=stepacts>"
             "<button onclick=\"gitDo('pr')\">Send my reviews in</button></div>")
      + "</div>"

      # The heading FOLLOWS the content, because this panel shows two different things.
      # "What happened" was wrong from the moment the panel started rendering a diff on load:
      # nothing has happened yet at that point, it is showing your pending edits. "Output" is
      # right after a step runs and wrong before one. So it starts as "Your changes" and
      # gitDo() switches it to "Output" - see setOutHead() in the JS.
      "<div class=card>"
      "<h3 id=outhead>Your changes</h3>"
      "<p class=sub id=outsub>Every edit you have made and not yet sent in. Green is added, "
      "red is removed.</p>"
      "<pre class=out id=gitout>" + diff_html(review_diff()) + "</pre></div>"

      "<details class=card><summary>"
      "<span class=info aria-hidden=true>i</span>"
      "<h3>Worth knowing</h3>"
      "<span class=chev aria-hidden=true></span></summary>"
      "<ul class=sub style='margin:10px 0 0 20px;padding:0'>"
      "<li>A review with nothing to fix is still worth sending.</li>"
      "<li>Writing what <i>should</i> have been said is the valuable part — a knowledge-file "
      "change is not required.</li>"
      "<li>Suggestions handed to someone else need sending in too; that is how they reach "
      "them.</li>"
      "<li>Only step 3 shares anything.</li>"
      "</ul></details>")
    return page("Save & Share", body, active="git")


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
            # Honour the same rule as the nav: a hand-typed ?all=1 from a contributor
            # lands on their own view rather than silently working. Not a security control
            # (see is_admin) - just refusing to have two answers to the same question.
            want_all = "all=1" in self.path
            return self._send(200, list_page(show_all=want_all and (is_admin() or not ME)))
        if self.path == "/logo.svg":
            # Cache hard: it is a brand mark that changes when Tyler rebrands, and it is on
            # every page. An immutable response keeps it out of the request log entirely.
            try:
                body = LOGO.read_bytes()
            except OSError:
                return self._send(404, page("404", "Not found"))
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "public, max-age=86400")
            self.end_headers()
            return self.wfile.write(body)
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
        if self.path == "/sync":
            # Pull new conversations from Foundry. Read-only against Foundry; it only ever
            # ADDS transcript files and never overwrites an existing one, so a stray click
            # cannot lose review work.
            try:
                if not os.environ.get("FOUNDRY_API_KEY"):
                    raise ValueError("FOUNDRY_API_KEY is not set in the environment this "
                                     "server was started from — start it from a shell where "
                                     "the key is available, then try again")
                r = subprocess.run([sys.executable, str(REPO / "scripts" / "fetch_transcripts.py")],
                                   cwd=REPO, capture_output=True, text=True, timeout=600)
                out = (r.stdout or "") + (r.stderr or "")
                # The line is "added: 2 new | untouched (already present): 56 | ...", so take
                # the first integer after the label - not the whole field, which is "2 new".
                added = 0
                m = re.search(r"^added:\s*(\d+)", out, re.M)
                if m:
                    added = int(m.group(1))
                refresh_index()
                return self._send(200, json.dumps({"ok": r.returncode == 0, "added": added,
                                                   "output": out[-4000:]}), "application/json")
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
            # Blank is the normal case, so it resolves to the generated label rather than
            # to a generic one - "Review transcripts" as a change-request title told a
            # reviewer nothing about whose it was or when.
            msg = (data.get("message") or "").strip() or auto_commit_message()
            try:
                if act == "commit":
                    rc, out = save_reviews(msg)
                elif act == "diff":
                    rc, out = 0, review_diff()
                elif act == "pr":
                    # Save FIRST, always. "Send my reviews in" used to push and open a PR
                    # without committing, so a reviewer who never clicked Save sent an empty
                    # change request and was told it worked. Save is a checkpoint a reviewer
                    # may want; it must not be a prerequisite they can forget.
                    rc, out = save_reviews(msg)
                    if rc not in (0, NOTHING_TO_SAVE):
                        raise RuntimeError(out)
                    _, cur = git("rev-parse", "--abbrev-ref", "HEAD")
                    prc, pout = git("push", "-u", "origin", cur.strip(), timeout=180)
                    out = (out + "\n\n" + pout).strip()
                    rc = prc
                    if prc == 0:
                        r = subprocess.run(["gh", "pr", "create", "--fill"], cwd=REPO,
                                           capture_output=True, text=True, timeout=180)
                        rc = r.returncode
                        out = (out + "\n" + r.stdout + r.stderr).strip()
                else:
                    rc, out = 1, "unknown action"
                return self._send(200, json.dumps(
                    # `html` is pre-escaped by diff_html, so the browser can innerHTML it. It
                    # is sent alongside `output` rather than instead of it, so a client that
                    # ignores it still shows the plain text.
                    # NOTHING_TO_SAVE means "already saved", which is a fine thing to have happened -
                    # reporting it as a failure would train people to ignore the toast.
                    {"ok": rc in (0, NOTHING_TO_SAVE), "output": out,
                     "html": diff_html(out)}),
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
    ap.add_argument("--no-avatars", action="store_true",
                    help="draw initials instead of fetching faces from gravatar.com / "
                         "github.com — keeps the page fully offline")
    a = ap.parse_args()
    global NO_AVATARS
    NO_AVATARS = a.no_avatars
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
