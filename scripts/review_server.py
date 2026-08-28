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
import argparse, html, json, os, re, shutil, subprocess, sys, time, webbrowser
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


def _foundry_get(path, timeout=60):
    """GET from Foundry with the two headers it insists on.

    The User-Agent is not optional: a request without one is refused by the WAF with a 403 that
    looks exactly like an auth failure.
    """
    import urllib.request
    base = os.environ.get("FOUNDRY_API_URL", "https://foundry.tylertechai.com").rstrip("/")
    req = urllib.request.Request(base + path)
    req.add_header("X-API-Key", os.environ.get("FOUNDRY_API_KEY", ""))
    req.add_header("User-Agent", "claude-code-foundry-kb/1.0")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace") or "null")


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
    # Via scripts/owners.py so this is not a THIRD implementation of "read agent-owners.json".
    # This one happened to be correct about lists while gen_codeowners.py and
    # check_folder_ownership.py were not, which is the worst version of that split: the UI
    # showed a two-person corpus working while CODEOWNERS granted approval to nobody.
    try:
        from owners import load_owners
        by_list, default = load_owners()
    except Exception:
        return {}, None
    by = {k: set(v) for k, v in by_list.items()}
    # The rest of this file treats the default as a single name. Several defaults would be a
    # different feature - the default is "who owns everything nobody claimed" - so the first is
    # used and the file's own comment says to name one.
    return by, (default[0] if default else None)


# Foundry display name -> the agent slug used in `answered_by` and agent-owners.json.
# `delegated_to` carries display names, so ownership cannot be resolved without this.
DELEGATE_SLUG = {
    "Ops Center": "ops-center",
    "General Blueprint Docs Agent": "bp-general",
    "Support Access Center": "sac",
    "Tyler Identity Assistant": "identity",
    "Aligned Releases": "aligned-releases",
}


# Collection -> the local folder its files come from. The inverse of FOLDER_COLLECTION, which
# is one-to-many (Knowledge-Shared uploads to all five) and so cannot be inverted mechanically.
BK_COLLECTION_FOLDER = {
    "OT-OpsCenter":       "Knowledge-OpsCenter",
    "OT-BPD":             "Knowledge-BP-General",
    "OT-SAC":             "Knowledge-SupportAccessCenter",
    "OT-AlignedReleases": "Knowledge-AlignedReleases",
    "TCP-KB-Identity":    "Knowledge-TylerIdentity",
}

BK_AGENT_ID = {
    "ops-center":       "5b3efdff-921a-4131-be81-b7a4be427d9b",
    "bp-general":       "bd1c5d91-8234-486e-9f5a-2f1b7a947426",
    "sac":              "55444576-1fa3-4d12-a738-6ba83b17e6a7",
    "aligned-releases": "b0544224-b120-469a-8f39-c4a7b14c17c0",
    "identity":         "3f5e586f-0d0f-4638-9839-bebe45a6cb47",
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
  /* Stat-tile tints. Pale enough that ordinary text sits on them at full contrast - the
     numeral is NOT tinted, so the tint carries the state and the digit stays legible. */
  --t-red-bg:#fdecea;     --t-red-bd:#f3c9c4;
  --t-yellow-bg:#fff8e1;  --t-yellow-bd:#eddfb0;
  --t-green-bg:#e9f5ea;   --t-green-bd:#c3e0c6;
  --t-grey-bg:#f1f3f4;    --t-grey-bd:#dcdfe2;
  --bnr-ok-bg:#eef7ee;    --bnr-ok-bd:#c6e3c6;    --bnr-ok-fg:#1c3d1f;
  --bnr-sug-bg:#f3ecfd;   --bnr-sug-bd:#cdb8f0;   --bnr-sug-fg:#33215c;
  --bnr-done-bg:#fff6e5;  --bnr-done-bd:#e8d3a8;  --bnr-done-fg:#4a3610;
  /* Neutral informational banner. Used since the Backups tab shipped and never defined,
     so those panels rendered as bare .bar with no tint at all - the styling was silently
     absent rather than wrong, which is why nobody noticed. */
  --bnr-note-bg:#eef2f7;  --bnr-note-bd:#c9d4e2;  --bnr-note-fg:#26333f;
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
  /* Dark: the same four states, re-stepped for a dark surface rather than the light tints
     darkened - a dimmed pastel goes muddy and stops reading as a colour at all. */
  --t-red-bg:#3a1e1e;     --t-red-bd:#5e2f2f;
  --t-yellow-bg:#322916;  --t-yellow-bd:#574727;
  --t-green-bg:#17301f;   --t-green-bd:#2f5d40;
  --t-grey-bg:#2b313a;    --t-grey-bd:#444b56;
  --bnr-ok-bg:#17301f;    --bnr-ok-bd:#2f5d40;    --bnr-ok-fg:#c8e6d2;
  --bnr-sug-bg:#261c3a;   --bnr-sug-bd:#443463;   --bnr-sug-fg:#ddccf5;
  --bnr-done-bg:#322916;  --bnr-done-bd:#574727;  --bnr-done-fg:#f0e0bd;
  --bnr-note-bg:#1b2430;  --bnr-note-bd:#33465c;  --bnr-note-fg:#cddced;
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
nav.side a .ic{width:20px;text-align:center;font-size:15px;line-height:1;
/* No opacity here: these are colour emoji, and dimming them washes the hue out so they
   read as faded rather than muted. Font-size does the visual-weight job instead. */
font-family:'Apple Color Emoji','Segoe UI Emoji','Noto Color Emoji',sans-serif}
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
/* Confirmation for a destructive action. In the page, not a native modal - a browser confirm()
   is the dialog people dismiss without reading, and it cannot show which files are at stake. */
.confirmbox{margin-top:10px;background:var(--tint-error);border:1px solid var(--t-red-bd);
border-radius:4px;padding:12px 14px;max-width:560px}
.confirmbox>b{font-weight:500}
.confirmbox .cdetail{margin-top:6px;font-size:13px;line-height:1.55;
color:var(--forge-theme-text-high)}
.confirmbox .cdetail code{font-size:12px;background:var(--forge-theme-surface);
padding:1px 4px;border-radius:2px}
.confirmbox .cacts{margin-top:12px;display:flex;gap:8px}
button.danger{background:var(--forge-theme-error);color:var(--on-accent);border:0}
button.danger:hover{filter:brightness(.92)}
/* The escape hatch at the foot of the page. Tinted rather than bordered-and-loud: it has to
   read as "not for today" while staying findable on the day it matters. */
.card.dangerzone{background:var(--t-red-bg);border-color:var(--t-red-bd)}
.card.dangerzone>h3{font-size:16px}
.dzrow{display:flex;gap:20px;align-items:flex-start;margin-top:14px}
.dzrow>div:first-child{flex:1;min-width:0}
.dzrow b{font-weight:500}
.dzrow .sub{margin-top:3px}
.dzact{flex:0 0 auto}
.prpills{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}
/* Analytics groups. A plain heading above each tile row, quieter than a card title - the tiles
   are the content, the heading only says which measure they are. */
h3.angroup{font:500 14px/1.4 Roboto,sans-serif;text-transform:uppercase;letter-spacing:.07em;
color:var(--forge-theme-text-medium);margin:26px 0 10px}
h3.angroup:first-of-type{margin-top:8px}
.antables{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:20px;
margin-top:26px}
table.antab{width:100%;border-collapse:collapse;margin-top:10px;font-size:14px}
table.antab th{text-align:left;font:500 12px/1.4 Roboto,sans-serif;text-transform:uppercase;
letter-spacing:.06em;color:var(--forge-theme-text-medium);padding:0 0 6px;
border-bottom:1px solid var(--row-line)}
table.antab td{padding:6px 0;border-bottom:1px solid var(--row-line)}
table.antab td:last-child,table.antab th:last-child{text-align:right}
/* Amber, matching "not finished yet" elsewhere on the page rather than red: an outstanding
   request is not an error, it is work in flight. */
.prbadge{margin-top:3px;font-size:11px}
/* Freshness readout. Quiet when the data is current, amber when it is not - the amber is the
   whole point, because "stale" has to be noticeable without being read. */
.fresh{font-size:12px;color:var(--forge-theme-text-medium);white-space:nowrap}
.fresh.stale{background:var(--t-yellow-bg);border:1px solid var(--t-yellow-bd);
color:var(--forge-theme-text-high);padding:2px 8px;border-radius:10px;font-weight:500}
.prbadge a{display:inline-block;padding:1px 6px;border-radius:3px;
background:var(--t-yellow-bg);border:1px solid var(--t-yellow-bd);
color:var(--forge-theme-text-high);text-decoration:none;font-weight:500}
.prbadge a:hover{text-decoration:underline}
/* Amber, because it is an obligation rather than a warning: this one is not finished when it
   merges. */
.fdrynote{margin-top:8px;padding:8px 12px;border-radius:4px;
background:var(--t-yellow-bg);border:1px solid var(--t-yellow-bd);
color:var(--forge-theme-text-high)}
.fdrynote code{font-size:12px}
.card>h3 a{text-decoration:none}
#prout{margin-top:20px}
/* Hand-off line at the end of a step: where responsibility passes to someone else. */
.handoff{margin-top:14px;padding:10px 14px;border-radius:4px;
background:var(--forge-theme-surface-container-minimum);
color:var(--forge-theme-text-medium);font-size:13.5px}
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

/* ------------------------------------------------------------------------------------------
   Save & Share only: everything one step larger. SCOPED, not global - the transcript list is
   a dense 12-column table where the smaller scale is what makes it fit at 720p, while this
   page is prose and form controls and reads as cramped at the same sizes.
   The page title is deliberately NOT bumped: at 24px it is already the largest thing here,
   and raising it with everything else would only re-open the gap.
   ------------------------------------------------------------------------------------------ */
.lg{font-size:15px}
.lg .card>h3{font-size:19px}
.lg .sub{font-size:15px;line-height:1.55}
.lg .stepbody h4{font-size:16.5px}
.lg label{font-size:14px}
.lg .hint{font-size:13.5px}
.lg ol.prog li{font-size:15px}
.lg ol.prog li span{font-size:13.5px}
.lg .whatsent{font-size:15px}
.lg .whatsent>b{font-size:14px}
.lg .saves table{font-size:14px}
.lg details.saves>summary{font-size:14px}
.lg .bar{font-size:15px}
.lg pre.out{font-size:13.5px}
.lg input{font-size:15px}
.lg button{font-size:15px}
/* The number bubbles and the stage dots have to grow with the text they sit beside, or they
   drift out of line with the first row of the heading. */
.lg .stepnum{flex-basis:26px;height:26px;font-size:13px;line-height:26px}
.lg ol.prog li{padding-left:28px}
.lg ol.prog li::before{width:17px;height:17px;line-height:17px;top:9px}
.lg span.info{width:20px;height:20px;font-size:13px}

/* More air between the title and the first note. They were 12px apart, which read as one
   block rather than a heading and its content. */
.lg h2.sec{margin-bottom:22px}
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
/* The assistant stage. Marked out because it is categorically different from the others: not
   waiting on this button, and not something the page can do at all. */
ol.prog li.ai{background:var(--bnr-sug-bg);border-radius:4px;padding:12px 12px 12px 30px;
margin:6px 0}
ol.prog li.ai::before{content:"\2726";background:none;color:var(--accent-purple);
font-size:13px;left:8px;top:13px}
ol.prog li.ai b{color:var(--bnr-sug-fg)}
ol.prog li.ai span{color:var(--bnr-sug-fg);opacity:.9}
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
/* EQUAL WIDTH, auto-fitting to the window. `1fr` columns from auto-fit means every tile is
   the same width and the count per row follows the viewport - six across on a wide screen,
   folding to three then two as it narrows, with no tile ever wider than another. Nothing spans
   any more, which is what made equal width possible. */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
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
.bar.bnr-note{background:var(--bnr-note-bg);border-color:var(--bnr-note-bd);
color:var(--bnr-note-fg)}
.bar.bnr-done{background:var(--bnr-done-bg);border-color:var(--bnr-done-bd);
color:var(--bnr-done-fg)}
.fb.down{background:var(--fb-down-bg);border-radius:50%;padding:2px 3px 3px;box-shadow:0 0 0 2px var(--forge-theme-surface)}
.who{display:inline-flex;align-items:center;gap:7px}
.whocell{display:inline-flex;align-items:center;gap:6px}
.whocell .av+.av{margin-left:-7px;box-shadow:0 0 0 2px var(--forge-theme-surface)}
.kpi{background:var(--t-grey-bg);border:1px solid var(--t-grey-bd);
border-radius:4px;padding:12px 14px;box-shadow:var(--shadow-card);}
.kpi .v{font:600 26px/1.15 Roboto,sans-serif;color:var(--forge-theme-text-high)}
.kpi.t-red{background:var(--t-red-bg);border-color:var(--t-red-bd)}
.kpi.t-yellow{background:var(--t-yellow-bg);border-color:var(--t-yellow-bd)}
.kpi.t-green{background:var(--t-green-bg);border-color:var(--t-green-bd)}
.kpi.t-grey{background:var(--t-grey-bg);border-color:var(--t-grey-bd)}
.kpi .l{font:400 12px/1.4 Roboto,sans-serif;color:var(--forge-theme-text-medium);margin-top:2px}
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
/* pointer-events:none IS THE POINT, not a nicety.
   This div lives at bottom-right permanently at opacity:0 - it is never removed, only faded -
   and an invisible element still receives clicks. "Mark reviewed & next" is the bottom-right
   button in the action bar, so the two overlapped and the toast swallowed clicks aimed at the
   button. MEASURED: toast 865-911px vertical, button 894-929 - a 17px dead band across the top
   of the primary action, present from page load whether or not a toast had ever shown.
   It was intermittent, which is why it read as "the button doesn't work" rather than as an
   overlap: whether your click landed depended on where in the button you hit and how far the
   page was scrolled.
   A toast is a notification. It should never be a target. */
.toast{position:fixed;bottom:18px;right:18px;background:#323232;color:#fff;padding:12px 18px;
border-radius:4px;opacity:0;transition:.25s;z-index:50;box-shadow:0 3px 8px rgba(0,0,0,.3);
pointer-events:none}
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
/* Links inside the dark output panel need their own colour - the page's link
   colour is tuned for a light surface and disappears on #263238. */
pre.out a{color:#90caf9;text-decoration:underline}
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
// Copy the assistant prompt. navigator.clipboard needs a secure context, and http://127.0.0.1
// counts as one in Chrome and Firefox - but not everywhere, and not if permission is refused.
// The textarea fallback is the reason this is more than one line: a copy button that silently
// does nothing is worse than no button, because the reviewer walks away believing they have it.
// ---- destructive actions ------------------------------------------------------------------
// Every destructive action goes through this, and it deliberately does NOT use confirm():
// a native modal blocks the page and is the one dialog you dismiss on reflex. This shows the
// consequence in the page, requires a second, differently-placed click, and times out - so an
// abandoned prompt cannot be completed by a stray click ten minutes later.
function confirmThen(btn, title, detail, run){
 const host=btn.parentNode;
 const old=host.querySelector('.confirmbox');
 if(old){old.remove(); btn.style.display=''; return}      // second click on the trigger cancels
 btn.style.display='none';
 const box=document.createElement('div');
 box.className='confirmbox';
 box.innerHTML='<b>'+title+'</b><div class=cdetail>'+detail+'</div>'
   +'<div class=cacts><button type=button class=danger>Yes, do it</button>'
   +'<button type=button class=sec>Cancel</button></div>';
 host.appendChild(box);
 const close=()=>{box.remove(); btn.style.display=''};
 const timer=setTimeout(close, 30000);
 box.querySelector('.danger').addEventListener('click',()=>{
   clearTimeout(timer); close(); run();
 });
 box.querySelector('.sec').addEventListener('click',()=>{clearTimeout(timer); close()});
}

function resetUnsaved(btn){
 const files=[...document.querySelectorAll('#gitfiles li')].map(l=>l.textContent);
 if(!files.length){toast('Nothing to reset',false);return}
 confirmThen(btn,'Reset '+files.length+' unsaved file(s)?',
   'These go back to their last saved state:<br>'
   +files.slice(0,8).map(f=>'<code>'+f+'</code>').join('<br>')
   +(files.length>8?'<br>… and '+(files.length-8)+' more':'')
   +'<br><br>Undoable — the edits are set aside, not deleted.',
   ()=>gitDo('reset'));
}

function discardSave(btn,hash,when,newer){
 confirmThen(btn,'Discard the save from '+when+(newer?' and '+newer+' newer?':'?'),
   (newer?'This rewinds past <b>'+(newer+1)+'</b> saves. Discarding cannot take one out of '
        +'the middle, so everything newer goes too.':'This rewinds one save.')
   +'<br><br>A recovery point is created first, and the output tells you how to use it.',
   ()=>gitDo('discard',{hash}));
}

// ---- change requests ----------------------------------------------------------------------
function prOut(txt, ok){
 let box=document.getElementById('prout');
 if(!box){box=document.createElement('pre');box.className='out';box.id='prout';
   document.querySelector('main.wrap').appendChild(box)}
 box.textContent=txt; box.scrollIntoView({block:'nearest'});
 toast(ok?'done':'failed',ok);
}
async function prDo(btn,action,number,extra){
 const label=btn.textContent; btn.disabled=true; btn.textContent='Working\u2026';
 try{
   const r=await post('/pr',Object.assign({action,number},extra||{}));
   prOut(r.output||'(no output)',r.ok);
   // Reload only on success. A failure message is the thing you need to read, and reloading
   // would replace it with a fresh page listing the same unmerged request.
   if(r.ok) setTimeout(()=>location.reload(),1500);
 } finally { btn.disabled=false; btn.textContent=label; }
}
// Merge is outward-facing and awkward to walk back, so it goes through the same gate as the
// destructive actions - and the gate names the checks state, because "merge anyway" on a
// failing build is exactly the mistake worth interrupting.
function prMerge(btn,number,title,checks){
 const warn = checks==='failing' ? '<b>Checks are failing on this one.</b><br>'
            : checks==='running' ? 'Checks are still running.<br>' : '';
 confirmThen(btn,'Merge #'+number+'?',
   warn+'<code>'+title+'</code><br><br>Rebases onto main and deletes the branch; if the '
   +'branch is behind main it is brought up to date first. Anything merged is live in the '
   +'repo for everyone.',
   ()=>prDo(btn,'merge',number));
}
function prOverride(btn,number,title,checks){
 const warn = checks==='failing' ? '<b>Checks are failing on this one.</b><br>'
            : checks==='running' ? 'Checks are still running.<br>' : '';
 confirmThen(btn,'Merge #'+number+' bypassing review?',
   warn+'<code>'+title+'</code><br><br>This skips the required approval \u2014 the one action '
   +'here that removes a safety gate rather than passing through it, and reasonable only on '
   +'your own work.<br><br>Rebases onto main and deletes the branch. If the branch is behind '
   +'main it is brought up to date first.',
   ()=>prDo(btn,'merge-override',number));
}
// Sending in is where the batch leaves this machine, and the assistant step sits BEFORE it in
// Part 2 for a reason: the knowledge edits and the verdicts belong in the same change request.
// Send without having run the assistant and you get a request carrying verdicts and no fix -
// which reads as complete, merges, and leaves the agent still giving the answer that was
// reviewed. This gate exists because that failure is silent and only shows up weeks later in a
// repeat transcript.
//
// It ASKS rather than blocks: whether the assistant work was needed at all is a judgement
// (plenty of batches are no-change reviews), and a hard block would be wrong for those. The
// wording changes with the count so it is a real question, not a rubber stamp.
function sendReviews(btn){
 const n = parseInt(btn.dataset.aiPending||'0',10)||0;
 const detail = n
   ? '<b>'+n+' reviewed transcript(s)</b> are still waiting on the knowledge-file update in '
     +'Part 2.<br><br>If you have not run the assistant prompt yet, the change request will '
     +'carry your verdicts with no fix behind them \u2014 it will look complete, merge, and the '
     +'agents will keep giving the answers you just reviewed.<br><br>Have the assistant '
     +'instructions been completed?'
   : 'No transcript in this batch is waiting on a knowledge update, so there is nothing for '
     +'the assistant to have done.<br><br>Send it in?';
 confirmThen(btn, n ? 'Has the assistant finished the knowledge updates?' : 'Send these in?',
   detail, ()=>gitDo('pr'));
}
function copyPrompt(btn){
 const text=window.AI_PROMPT||'';
 const done=ok=>{btn.textContent = ok ? '\u2713 Copied — paste it to your assistant'
                                      : 'Could not copy — select the text below instead';
   if(!ok){const ta=document.createElement('textarea');ta.value=text;
     ta.style.cssText='width:100%;margin-top:8px;font:inherit';ta.rows=4;
     btn.parentNode.appendChild(ta);ta.select()}
   else setTimeout(()=>{btn.textContent='Copy the prompt for my assistant'},4000);};
 if(navigator.clipboard&&window.isSecureContext){
   navigator.clipboard.writeText(text).then(()=>done(true),()=>done(false));
 } else {
   const ta=document.createElement('textarea');ta.value=text;
   ta.style.position='fixed';ta.style.opacity='0';document.body.appendChild(ta);
   ta.select();
   let ok=false; try{ok=document.execCommand('copy')}catch(e){ok=false}
   document.body.removeChild(ta); done(ok);
 }
}
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
async function gitDo(action,extra){const msg=(document.getElementById('cmsg')||{}).value||'';
if(action==='pr'){stage('push','run')}
const r=await post('/git',Object.assign({action,message:msg},extra||{}));
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
// Patch the parts that just went stale. Reloading would be simpler and wrong: it would throw
// away the output the reviewer clicked for.
if(r.refresh){
 const put=(id,v)=>{const e=document.getElementById(id); if(e&&v!=null)e.innerHTML=v};
 put('gitstate', r.refresh.state);
 put('gitfiles', r.refresh.files);
 const hist=document.getElementById('githist');
 if(hist&&r.refresh.saves!=null){
   // Keep it CLOSED unless the reviewer had opened it themselves. A section that pops open
   // on every save moves the buttons under the cursor.
   const wasOpen=!!hist.querySelector('details[open]');
   hist.innerHTML=r.refresh.saves;
   const d=hist.querySelector('details');
   if(d&&wasOpen)d.open=true;
 }
 // The nav badge counts the same thing as the status line, so it has to move with it.
 const badge=document.querySelector('nav.side a[href="/git"] .ct');
 if(badge){const n=r.refresh.unsent;
   if(n){badge.textContent=n;badge.style.display=''}else{badge.style.display='none'}}
}
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
// Publish the VISIBLE rows, in the order the table is showing them. The detail view walks
// this instead of the filesystem, so Previous/Next and "Mark reviewed & next" stay inside the
// filter you were looking at. Rewritten on every filter change, so it is always the list on
// screen - not the list at page load.
try{
 const order=[...document.querySelectorAll('tr.row')]
   .filter(tr=>tr.style.display!=='none')
   .map(tr=>(tr.dataset.href||'').replace(/^\/t\//,''))
   .filter(Boolean);
 sessionStorage.setItem('torder',JSON.stringify({view:document.body.dataset.defaultMine==='1'
   ?'mine':'all', order}));
}catch(e){}
if(window.ckSync)ckSync(); if(window.fpopMarks)fpopMarks();}
// Sync pulls new conversations from Foundry. Long-running (it walks every agent), so the
// button reports progress rather than appearing dead, and the page only reloads on success -
// a failure that reloaded away its own error message would be untraceable.
// ---- freshness ---------------------------------------------------------------------------
// THE GUARANTEE IS ABOUT WHAT YOU ARE LOOKING AT, not about a background schedule. Nobody
// keeps this open all day, so the useful promise is "whatever is on screen was refreshed
// within the last 30 minutes" - which means the check happens WHEN YOU ARRIVE, not 60 seconds after
// a timer starts.
//
// So: on load, and again whenever the tab comes back to the foreground, if the data is older
// than an hour it syncs immediately. The interval only matters for a tab that stays open.
//
// The first cut had this backwards - it waited for a timer tick and paused while hidden, which
// saved API calls but left you looking at possibly-stale data with nothing on screen saying
// so. Being hidden is now only a reason not to sync WHILE hidden; it never delays the sync you
// need on arrival.
// 30 minutes, at the owner's call. Cheap: one `gh`-free HTTP round trip to Foundry per
// window, per open tab. If it ever feels slow, this is the single number to raise.
const AUTO_MS = 30*60*1000;
let autoBusy = false;

// The server owns the timestamp, so every tab agrees and a reload does not lose it. Held as
// (age-at-a-known-instant, that instant) rather than a single number, because the age has to
// keep ticking between updates AND reset cleanly when a sync reports a new one. Adding
// "elapsed since page load" to a freshly-reported age would double-count the time the page
// had already been open - which is what the first version did.
let ageBaseSec = null;
let ageBaseAt = Date.now();

function setAge(sec){ ageBaseSec = (typeof sec==='number' && sec>=0) ? sec : null;
                      ageBaseAt = Date.now(); }
function dataAgeMs(){
 if(ageBaseSec===null) return null;
 return ageBaseSec*1000 + (Date.now()-ageBaseAt);
}

function paintFreshness(){
 const el=document.getElementById('freshness'); if(!el) return;
 const ms=dataAgeMs();
 if(ms===null){ el.textContent='never synced here'; el.classList.add('stale'); return }
 const min=Math.floor(ms/60000);
 el.textContent = min<1 ? 'up to date — synced just now'
                : min===1 ? 'synced 1 minute ago'
                : min<60 ? `synced ${min} minutes ago`
                : `synced ${Math.floor(min/60)}h ${min%60}m ago`;
 el.classList.toggle('stale', ms >= AUTO_MS);
}

async function autoTick(reason){
 paintFreshness();
 if(autoBusy) return;
 // Do not START a sync while hidden - but arriving at the tab is not "hidden", so this never
 // delays the on-arrival check.
 if(document.hidden && reason!=='arrive') return;
 const ms=dataAgeMs();
 if(ms!==null && ms<AUTO_MS) return;              // already fresh enough
 // ONE mechanism, two pages. Which action to take is decided by what is on the page, and the
 // timer for both is driven by the SERVER-side age of that page's own data - not by a
 // per-tab clock, which would reset every time the PRs page navigated to refresh itself.
 const el=document.getElementById('freshness');
 const kind = el ? (el.dataset.kind||'transcripts') : null;
 if(kind==='transcripts' && document.getElementById('syncbtn')){
   autoBusy=true;
   try{ await syncNow(true) } finally { autoBusy=false }
 } else if(kind==='prs'){
   location.href='/prs?refresh=1';
 } else if(kind==='analytics'){
   location.href='/analytics?refresh=1';
 }
}

setInterval(paintFreshness, 30*1000);       // keep the readout honest as time passes
setInterval(()=>autoTick('interval'), 60*1000);
document.addEventListener('visibilitychange', ()=>{ if(!document.hidden) autoTick('arrive') });
// Seed from what the server rendered, then keep it ticking client-side.
(function(){
 const el=document.getElementById('freshness');
 const s = el ? parseInt(el.dataset.age||'-1',10) : -1;
 setAge(s >= 0 ? s : null);
})();

// ON ARRIVAL. This is the line that makes the promise true for someone who opens the page
// once a day rather than leaving it open.
autoTick('arrive');

// RETURNS the promise, so autoTick can await it and the busy guard actually holds.
function syncNow(auto){const b=document.getElementById('syncbtn'),m=document.getElementById('syncmsg');
 if(!b||b.disabled)return Promise.resolve(); b.disabled=true; b.textContent='Syncing\u2026';
 m.textContent = auto ? 'data was over 30 minutes old \u2014 refreshing'
                      : 'pulling from Foundry, this can take a minute';
 return fetch('/sync',{method:'POST'}).then(r=>r.json()).then(d=>{
  if(d.ok){
   setAge(typeof d.age==='number' ? d.age : 0);
   paintFreshness();
   const ch=(d.added||0)+(d.updated||0);
   m.textContent = !ch ? 'no changes'
     : ((d.added?d.added+' new':'') + (d.added&&d.updated?', ':'')
        + (d.updated?d.updated+' updated':'') + ' \u2014 reloading');
   // Reload on ANY change. Reloading only for new files left corrected states - a thumbs-down
   // that arrived on an existing transcript - sitting invisible until the next navigation.
   if(ch){location.reload();return}
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

// ---- detail-view navigation follows the TABLE, not the filesystem --------------------------
// The server renders Previous/Next from the full transcript list on disk, which is the only
// order it can know. That sent "Mark reviewed & next" out of the filtered set and backwards
// into months-old transcripts - it walked every file in the repo, not the 12 pending rows on
// screen.
//
// A SNAPSHOT, deliberately, taken when the list was last rendered. Re-filtering live would
// drop each row out of the sequence the moment you marked it reviewed (the default filter is
// `pending`), so "next" would jump unpredictably. The snapshot means the batch you started is
// the batch you walk.
(function(){
 const cur=document.body.dataset.rel; if(!cur) return;
 let snap=null; try{snap=JSON.parse(sessionStorage.getItem('torder'))}catch(e){}
 const order=(snap&&Array.isArray(snap.order))?snap.order:null;
 if(!order||!order.length) return;
 const i=order.indexOf(cur);
 if(i<0) return;                    // arrived by direct link; leave the server's links alone
 const prev=i>0?order[i-1]:'';
 const next=i<order.length-1?order[i+1]:'';
 const back=snap.view==='all'?'/?all=1':'/';
 const url=r=>r?('/t/'+r):back;
 // Previous is a link; Next and the two verdict buttons carry the target as an argument.
 const pa=document.querySelector('.nav a[href^="/t/"], .nav a[href="/"]');
 if(pa){ if(prev){pa.setAttribute('href',url(prev))} else {pa.remove()} }
 document.querySelectorAll('[onclick]').forEach(el=>{
   const on=el.getAttribute('onclick')||'';
   if(/^(markAndNext|suggestAndNext)\(/.test(on)){
     el.setAttribute('onclick', on.replace(/,'[^']*'\)/, ",'"+url(next)+"')"));
   }
 });
 const na=[...document.querySelectorAll('.nav a')].find(a=>/Next/i.test(a.textContent));
 if(na) na.setAttribute('href',url(next));
 // Say where you are in the batch. Without it there is no way to tell whether "next" is about
 // to run out, which is the moment people assume something broke.
 const pos=document.querySelector('#batchpos');
 if(pos) pos.textContent=`${i+1} of ${order.length} in this list`;
})();

// Carry the reviewer between transcripts so a clean batch is one click each.
(function(){const rv=document.querySelector('[data-fm=reviewer]');
 if(!rv||rv.value) return;
 let last=null; try{last=localStorage.getItem('lastReviewer')}catch(e){}
 if(last&&[...rv.options].some(o=>o.value===last)) rv.value=last;})();

// ---- Backups: the two restore actions ------------------------------------------------------
// These are the ONLY buttons in this app that write to production, so both go through
// confirmThen and both say what they will do rather than just asking "are you sure".
function bkPost(btn, payload, label){
 const out=document.getElementById('bkout');
 const was=btn.textContent; btn.disabled=true; btn.textContent=label+'…';
 if(out){out.style.display='block'; out.textContent=label+'…';}
 fetch('/bk',{method:'POST',headers:{'Content-Type':'application/json'},
              body:JSON.stringify(payload)})
  .then(r=>r.json()).then(d=>{
    if(out){out.style.display='block'; out.textContent=d.output||'(no output)';}
    toast(d.ok?'Done':'Failed — see the output below');
    btn.disabled=false; btn.textContent=was;
    // Re-read the page on success so the field diff reflects what is now live. Leaving a
    // stale diff on screen after a write invites a second click that would do nothing.
    if(d.ok) setTimeout(()=>location.reload(), 2500);
  })
  .catch(e=>{
    if(out){out.style.display='block'; out.textContent='Request failed: '+e;}
    btn.disabled=false; btn.textContent=was;
  });
}

function bkKb(btn, slug, date){
 confirmThen(btn,'Restore '+slug+'’s knowledge-base binding?',
   'Writes <code>collectionConfigs</code> and <code>dataSourceConfigs</code> from the '
   +date+' snapshot. It cannot touch instructions, model, tools or guardrails — those go '
   +'through a different endpoint.<br><br>A Foundry restore point is taken first, so this is '
   +'reversible.<br><br><b>This changes what a live agent reads.</b>',
   ()=>bkPost(btn,{action:'kb',slug:slug,date:date},'Restoring binding'));
}

function bkFields(btn, slug, date){
 const picked=[...document.querySelectorAll('input.bkfield:checked')].map(c=>c.value);
 if(!picked.length){ toast('Tick at least one field first'); return; }
 confirmThen(btn,'Roll back '+picked.length+' field(s) on '+slug+'?',
   '<code>'+picked.join('</code>, <code>')+'</code><br><br>The payload is built from the '
   +'<b>live</b> agent with only these fields taken from the '+date+' snapshot, so nothing '
   +'else moves.<br><br>A Foundry restore point is taken first.<br><br><b>This changes what a '
   +'live agent reads.</b>',
   ()=>bkPost(btn,{action:'fields',slug:slug,date:date,fields:picked},'Rolling back'));
}
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


# The nav badge needs a PR count on EVERY page, and `gh pr list` is a network call - so
# without a cache, opening any page waits on GitHub. Measured: it made the PRs page slow enough
# that a screenshot timed out twice.
#
# 60 seconds, and deliberately not longer: the number changes when you merge something, and a
# badge that lags a merge by minutes is worse than one that lags by seconds. The PRs page
# refreshes the cache from the list it already fetched, so acting on a request updates the
# badge immediately.
_PR_CACHE = {"at": 0.0, "n": 0, "ok": False}
_PR_TTL = 60.0


def pr_count(force=False):
    now = time.monotonic()
    if not force and _PR_CACHE["ok"] and (now - _PR_CACHE["at"]) < _PR_TTL:
        return _PR_CACHE["n"]
    if not shutil.which("gh"):
        _PR_CACHE.update(at=now, n=0, ok=True)
        return 0
    try:
        # Short timeout on purpose: this is decoration on a nav item, and a page must not hang
        # waiting for it. A stale or zero badge is a fine outcome; a frozen page is not.
        r = subprocess.run(["gh", "pr", "list", "--state", "open", "--limit", "50",
                            "--json", "number"],
                           cwd=REPO, capture_output=True, text=True, timeout=8)
        n = len(json.loads(r.stdout or "[]")) if r.returncode == 0 else _PR_CACHE["n"]
    except Exception:                                          # noqa: BLE001
        n = _PR_CACHE["n"]
    _PR_CACHE.update(at=now, n=n, ok=True)
    return n


def page(title, inner, active="", all_view=False, rel=""):
    """Shell with a Forge-style SIDE NAV.

    The previous version put "All transcripts" and "Git & PR" as bare links in the app bar,
    where they read as body text - people did not realise they were navigation. A left rail
    with an icon, a label and a live count per item makes each one visibly a destination.
    """
    open_n, mine_n, uncommitted = nav_counts()
    open_pr_count = pr_count() if is_admin() else 0

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
        + (item("/", "&#128681;", "My Transcripts", mine_n or None, "mine") if ME else "")
        # Admins only. For a contributor the item would be a link to other people's work they
        # cannot push to - an invitation to a dead end. An unidentified user gets it too,
        # because with no `me` there is no "mine" to fall back to and an empty app is worse.
        + (item("/?all=1", "&#128203;", "All Transcripts", open_n or None, "all")
           if (is_admin() or not ME) else "")
        # MONITOR sits above SAVE & PUBLISH and is visible to everyone. Foundry's own sidebar
        # groups Analytics under MONITOR, so the vocabulary matches the tool it mirrors.
        + "<div class=grp>Monitor</div>"
        + item("/analytics", "&#128202;", "OT Analytics", None, "analytics")
        + "<div class=grp>Save &amp; Publish</div>"
        + item("/git", "&#128228;", "Save &amp; Share", uncommitted or None, "git")
        # Admins only, same rule as All Transcripts: a contributor cannot merge, so the item
        # would be a link to a page of buttons that all refuse.
        + (item("/prs", "&#128256;", "PRs", open_pr_count or None, "prs")
           if is_admin() else "")
        # Its own section rather than under Monitor: Monitor is visible to everyone, and this
        # is not. Admin-only for the same reason the backup repo is - snapshots carry agent
        # instructions, tenant storage paths, and per-file IDs that are direct DELETE handles.
        + ("<div class=grp>Backups</div>"
           + item("/backups", "&#128190;", "Config Backups", None, "backups")
           if is_admin() else "")
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
<body data-default-mine="{'1' if (ME and not all_view) else '0'}" data-default-status="{'pending' if (ME and not all_view) else '__open__'}" data-show-all="{'1' if (is_admin() or not ME) else '0'}" data-rel="{html.escape(rel)}">
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
            "openpr": None,          # filled in below from transcript_pr_map()
        })
    tpr = transcript_pr_map()
    for r in recs:
        r["openpr"] = tpr.get(r["rel"])

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
            f" data-openpr=\"{r['openpr']['number'] if r['openpr'] else ''}\""
            f" data-href=\"/t/{html.escape(r['rel'])}\">"
            f"<td class=nowrap><input type=checkbox class=ck value=\"{html.escape(r['rel'])}\""
            # Disabled when it is inside an open request as well as when it is not pending.
            # Bulk-marking is precisely the "acting on it automatically" this badge exists to
            # prevent, so the badge alone would have been advice without a guard behind it.
            f"{' disabled' if (r['status']!='pending' or r['openpr']) else ''}"
            f"{' title=\'Inside an unmerged change request — open it instead\'' if r['openpr'] else ''}"
            "></td>"
            f"<td class=fbcell>{fb_glyph(r['fb'])}</td>"
            f"<td class=qcell title=\"{html.escape(r['qfull'])}\">"
            f"<a href='/t/{html.escape(r['rel'])}'>{html.escape(r['q'])}</a></td>"
            f"<td>{html.escape(r['agent'])}"
            f"{'<div class=deleg>&rarr; '+html.escape(r['deleg'])+'</div>' if r['deleg'] else ''}</td>"
            f"<td class=nowrap>{html.escape(r['date'])}</td>"
            f"<td>{html.escape(r['ex'])}</td>"
            f"<td><span class='pill {r['status']}'>{html.escape(r['status'])}</span>"
            f"{'<div class=deleg>'+html.escape(r['suggested_by'])+' &rarr; '+html.escape(r['awaiting'] or 'anyone')+'</div>' if r['status']=='suggested' else ''}"
            # Already inside an unmerged change request. Says so on the row, because the
            # alternative is someone re-reviewing work that is already done - a sync from main
            # re-creates these as fresh `pending` stubs, since fetch_transcripts.py decides
            # "new" from the working tree alone and cannot see a branch.
            + (f"<div class=prbadge><a href=\"{html.escape(r['openpr']['url'])}\" "
               f"target=_blank rel=noopener onclick='event.stopPropagation()'>"
               f"outstanding PR #{r['openpr']['number']}</a></div>"
               if r["openpr"] else "")
            + "</td>"
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

    def kpi(label, value, tone="grey", why=""):
        """One stat tile. `tone` picks a tinted background, not a text colour.

        Colour is a BACKGROUND here rather than the old coloured numeral, because a tint
        groups the row at a glance - the two reds read as one problem - while a coloured digit
        reads as decoration. The numeral stays in ordinary ink so it is legible in both display
        modes; the tints are what carry the state.
        """
        tip = f" title=\"{html.escape(why)}\"" if why else ""
        return (f"<div class='kpi t-{tone}'{tip}><div class=v>{value}</div>"
                f"<div class=l>{label}</div></div>")

    # Lifecycle states only, in lifecycle order. Ownership is deliberately absent - see the
    # CSS comment. No links on any tile.
    # The progress tile is deliberately wider than the rest: it is the only one carrying a
    # bar, and a 2px-tall bar in a 150px tile is unreadable. It spans two columns to earn the
    # bar its width. When there is nothing in scope there is no progress to draw, so it drops
    # to a plain tile rather than rendering an empty trough.
    # Six tiles, fixed set, in lifecycle order. Specified by the repo owner, and the pair in
    # the middle is the point of the redesign: "Reviewed, Not saved" versus "Reviewed, Saved
    # locally" is the distinction a reviewer actually worries about, and no tile expressed it
    # before - both used to fall under one "Reviewed" count.
    #
    # The progress meter that used to lead this row is gone with it. It spanned two columns,
    # which is incompatible with all-equal-width, and it measured "reviewed of in scope" - a
    # number the six tiles now give you directly.
    dirty, saved_ahead = saved_state()
    rev_unsaved = rev_saved = 0
    for r in recs:
        if r["status"] != "reviewed":
            continue
        rel = "transcripts/" + r["rel"]
        if rel in dirty:
            rev_unsaved += 1
        else:
            rev_saved += 1

    tiles = [
        kpi("Pending", counts["pending"], tone="red",
            why="Nobody has looked at these yet. This is the queue to work through."),
        kpi("Reviewed, Not saved", rev_unsaved, tone="red",
            why="You have ruled on these but the verdict is only in a file on this laptop. "
                "Nothing protects it yet — Save progress on the Save & Publish page does."),
        kpi("Reviewed, Saved locally", rev_saved, tone="yellow",
            why="Ruled on and checkpointed, but not finished: the knowledge change either has "
                "not been written yet or is not live in Foundry. Includes anything already "
                "merged but not yet closed out."),
        kpi("Closed out", counts["pushed"], tone="green",
            why="Fully done: reviewed, processed, and any resulting knowledge change is live "
                "in Foundry and verified. Nothing further owed."),
        kpi("Excluded", excl, tone="grey",
            why="Pre-go-live internal testing — conversations from before the chatbot shipped "
                "on 2026-08-19. Not real user feedback, so out of scope."),
        kpi("Total transcripts", tot, tone="grey",
            why="Every conversation collected in this view, in scope or not."),
    ]
    # Sync sits at the top of both list views: it is the first thing you want when you sit
    # down, and burying it behind the terminal defeats the point of a UI.
    age = last_sync_age()
    title = "My Transcripts" if (ME and not show_all) else "All Transcripts"
    head = ("<div style='display:flex;align-items:center;gap:12px;flex-wrap:wrap;"
            "margin-bottom:var(--forge-spacing-medium)'>"
            f"<h2 class=sec style='margin:0'>{title}</h2>"
            "<button class=sec id=syncbtn onclick='syncNow()' style='margin-left:auto' "
            "title='Runs by itself when the data is more than 30 minutes old'>"
            "&#8635; Sync transcripts</button>"
            # The reassurance itself. Without this the page could be an hour stale or five
            # minutes stale and look identical, which is the actual problem - nobody should
            # have to keep the tool open to trust what it is showing them.
            f"<span class=fresh id=freshness data-age='{age if age is not None else -1}'></span>"
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
        # Default `reviewer` to the person using the tool. They opened the transcript; they are
        # the reviewer. Leaving it blank made the commonest action - open, agree, mark reviewed -
        # fail on its first click for every new contributor, and the error it produced was about
        # a field they had no reason to think was theirs to fill.
        #
        # ONLY when blank, so it never overwrites a name already recorded, and only for
        # `reviewer` - `suggested_by` and `awaiting` are deliberate choices about other people
        # and must stay empty until someone makes them.
        if k == "reviewer" and not val and ME and ME in contributors():
            val = ME
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
    # Fallback order for someone who arrived by direct link with no table snapshot. Sorted the
    # SAME WAY the table sorts - date descending, then filename descending - so the two never
    # disagree about which way "next" goes. tfiles() alone is filesystem order, which is how
    # "next" used to walk backwards into months-old transcripts.
    order = sorted((f.relative_to(TDIR).as_posix() for f in tfiles()),
                   key=lambda r: (r.split("/")[-1][:10], r), reverse=True)
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
        f"<div class=nav><div style='display:flex;gap:12px;align-items:center'>"
        f"{f'<a href=\"{prev_}\"><button class=sec>&larr; Previous</button></a>' if prev_ else ''}"
        # Filled in by the detail-nav script from the table's snapshot. Without it there is no
        # way to tell whether "next" is about to run out of rows, which is exactly when people
        # assume the button is broken.
        f"<span class=hint id=batchpos></span></div>"
        f"<div style='display:flex;gap:8px'>"
        f"<button class=sec onclick=\"saveDoc('{html.escape(rel)}')\">Save</button>"
        f"<button class=sec onclick=\"suggestAndNext('{html.escape(rel)}','{next_}')\" "
        f"title='Record this as a suggestion for the area owner, not as your verdict'>"
        f"Suggest &amp; next &rarr;</button>"
        f"<button class=sec onclick=\"reReview('{html.escape(rel)}')\">Re-review</button>"
        f"<button onclick=\"markAndNext('{html.escape(rel)}','{next_}')\">Mark reviewed &amp; next &rarr;</button>"
        f"</div></div>")
    return page(f"{fm.get('answered_by','')} {rel}", "".join(parts), rel=rel)


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
    """Saves that have NOT been sent anywhere yet - nothing else.

    `git log HEAD --not --remotes`, which is the exact question: commits on HEAD that no remote
    ref can reach. Everything else is an approximation of it and each one has a hole:

      - `origin/main..HEAD` counts commits that ARE already pushed, just under a different
        branch name. Measured 2026-08-27: a reviewer's lane sat on top of 18 pushed commits and
        the page reported 19 unsent saves when the true answer was 1.
      - `@{u}..HEAD` needs an upstream, and a lane created locally has none, so it errors.
      - comparing against `origin/<current branch>` fails for the same reason, and silently -
        the missing ref just makes the "already sent" set empty and everything looks unsent.

    Deliberately not filtered to this branch either. If a save was made on one lane and the
    reviewer has since moved, it is still their unsent work and still needs sending.

    No fetch: this runs on every page render, and a network call would hang the page on a bad
    connection. It uses the last-known remote state, like the rest of the page.
    """
    rc, out = git("log", "--format=%h%x09%ad%x09%s", "--date=format:%m/%d %H:%M",
                  "HEAD", "--not", "--remotes")
    if rc != 0 or not out.strip():
        return []
    rows = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) == 3:
            rows.append({"h": parts[0], "when": parts[1], "subject": parts[2]})
    return rows


def reset_unsaved():
    """Return edited transcript files to their last saved state. Returns (rc, message).

    STASHED, NOT DELETED - and that is the whole design. This is the only action on the page
    with no other safety net: unsaved edits exist nowhere but the working tree, so a plain
    `git checkout --` or `reset --hard` here is unrecoverable. On 2026-08-27 that exact command
    destroyed a reviewer's verdicts in this repo. `git stash` does the same visible thing while
    leaving the content retrievable, so the worst case is an inconvenience instead of a lost
    afternoon.

    Untracked files are deliberately left alone. An untracked file under transcripts/ is a
    conversation Sync just pulled, not an edit - deleting it would throw away data the reviewer
    never touched, and re-fetching it is not free.
    """
    _, dirty = git("status", "--porcelain", "--", *review_scope())
    rows = [l for l in dirty.splitlines() if l.strip()]
    tracked = [porcelain_path(l) for l in rows if not l.strip().startswith("??")]
    if not tracked:
        return 1, "Nothing to reset — there are no unsaved edits."

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    rc, out = git("stash", "push", "-m", f"reset-unsaved {stamp}", "--", *review_scope())
    if rc != 0:
        return 1, f"Could not reset, so nothing was changed:\n{out}"

    lines = [f"Reset {len(tracked)} file(s) to their last saved state:"]
    lines += [f"  {f}" for f in tracked[:20]]
    if len(tracked) > 20:
        lines.append(f"  … and {len(tracked) - 20} more")
    lines.append("")
    lines.append("NOT deleted — the edits were set aside, so this is undoable:")
    lines.append("  git stash list          see them")
    lines.append("  git stash pop           put them back")
    return 0, "\n".join(lines)


def discard_saves(target):
    """Undo the save `target` and every save made after it. Returns (rc, message).

    ONE DIRECTION ONLY, by design and at the owner's instruction: you cannot pull one save out
    of the middle. Git history is a chain - removing a link from the middle means rewriting
    every save above it, and the result is a history nobody can reason about. So discarding
    means "rewind to just before this one".

    Three guards, and the middle one exists because of a real incident:

    1. ONLY UNSENT SAVES. If a save has reached any remote it is somebody else's history too,
       and rewinding past it would rewrite shared history. Refused.

    2. REFUSES WITH UNSAVED WORK IN THE TREE. `git reset --hard` destroys uncommitted changes,
       and on 2026-08-27 exactly that destroyed a reviewer's verdicts in this repo -
       unrecoverably, because they had never been committed. Anything not yet saved has no
       recovery path, so this will not run until the tree is clean. Save first, then discard;
       that way everything being thrown away is recoverable.

    3. LEAVES A RECOVERY TAG. Before rewinding, the current tip is tagged. The commits also
       survive in the reflog for ~90 days, but a named tag is something you can act on without
       knowing what a reflog is - and the message says how.
    """
    saves = unsent_saves()
    hashes = [s["h"] for s in saves]
    if target not in hashes:
        return 1, ("That save cannot be discarded — it has already been sent in, so it is part "
                   "of the shared history now. Only saves that have not left this machine can "
                   "be discarded.")

    _, dirty = git("status", "--porcelain", "--", *review_scope())
    if dirty.strip():
        n = len([l for l in dirty.splitlines() if l.strip()])
        return 1, (f"You have {n} edited file(s) that are not saved yet. Discarding rewinds the "
                   "files on disk, which would destroy those edits with no way back — they "
                   "have never been saved anywhere.\n\n"
                   "Save progress first, then discard. Everything saved is recoverable.")

    # Everything from `target` up to the tip, newest first, so the message can name it.
    idx = hashes.index(target)
    doomed = saves[:idx + 1]

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    tag = f"discarded/{stamp}"
    rc, out = git("tag", tag)
    if rc != 0:
        return 1, f"Could not create the recovery point, so nothing was discarded:\n{out}"

    rc, out = git("reset", "--hard", f"{target}~1")
    if rc != 0:
        git("tag", "-d", tag)
        return 1, f"Could not rewind, so nothing was discarded:\n{out}"

    lines = [f"Discarded {len(doomed)} save(s):"]
    lines += [f"  {s['when']}  {s['subject']}" for s in doomed]
    lines.append("")
    lines.append(f"Recovery point: {tag}")
    lines.append(f"To undo this, run:  git reset --hard {tag}")
    return 0, "\n".join(lines)


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
        # Linkify URLs. `gh pr create` answers with the change request's address, and the
        # whole point of that address is to be opened - to merge, or to send to a reviewer.
        # Leaving it as text in a <pre> means selecting it by hand from a wall of monospace.
        # Applied after escaping, so the href is built from already-escaped text.
        e = re.sub(r"(https?://[^\s&<]+)",
                   r"<a href='\1' target=_blank rel=noopener>\1</a>", e)
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
# LISTS, not strings. They were strings, and `for c in FOLDER_COLLECTION[folder]` then
# iterated characters - the PRs page rendered a collection name as "O, T, -, A, l, i, g, n,
# e, d, R, a, s". Same shape as publish_to_foundry.py's COLLECTIONS now, and Knowledge-Shared
# names its five targets rather than saying "all five collections", which was prose masquerading
# as data.
FOLDER_COLLECTION = {
    "Knowledge-OpsCenter": ["OT-OpsCenter"],
    "Knowledge-BP-General": ["OT-BPD"],
    "Knowledge-SupportAccessCenter": ["OT-SAC"],
    "Knowledge-AlignedReleases": ["OT-AlignedReleases"],
    "Knowledge-TylerIdentity": ["TCP-KB-Identity"],
    "Knowledge-Shared": ["OT-OpsCenter", "OT-BPD", "OT-SAC", "OT-AlignedReleases",
                         "TCP-KB-Identity"],
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
        for col in FOLDER_COLLECTION.get(path.split("/")[0], []):
            if col not in cols:
                cols.append(col)
    return cols


def review_scope():
    """The trees a save covers: transcripts plus every knowledge corpus.

    Used by the file list, the diff and the staging itself. They MUST agree - when the list
    was scoped to `transcripts` and the staging to both, the page showed a reviewer less than
    the button was about to save.
    """
    return ["transcripts"] + sorted(d.name for d in REPO.iterdir()
                                    if d.is_dir() and d.name.startswith("Knowledge-"))


def awaiting_analysis():
    """Reviewed transcripts whose feedback has not been turned into knowledge changes yet.

    This is the count that makes the assistant step honest. A reviewer's verdict is not the
    deliverable - the deliverable is the knowledge file that stops the agent giving that answer
    again - and nothing on this page could previously tell you whether that work had been done.
    """
    n = 0
    for f in tfiles():
        fm, body = parse(f)
        if fm is None:
            continue
        if (fm.get("review_status") or "") != "reviewed":
            continue
        # Either an unresolved action, or prose nobody has classified yet. Both are work.
        if (fm.get("action_status") or "") in ("open", "", "needs-triage") or needs_triage(fm, body):
            n += 1
    return n


def analysis_prompt(n):
    """The exact words to hand an assistant. Generated, not written by the reviewer.

    Deliberately short and deliberately NOT a description of the mechanics. The instructions an
    assistant needs are already in CLAUDE.md, which it reads on its own; repeating them here
    would create a second copy to drift. What it cannot know is that a batch is ready and what
    the human wants out of it.
    """
    return (f"I have finished reviewing {n} transcript(s) in this repo. "
            "Read all of my feedback as one body before changing anything, then update the "
            "knowledge files so the agents stop giving those answers. Summarise what you "
            "changed, per transcript, so I can follow my own feedback through. "
            "Do not change my verdicts, and ask me rather than guessing if any of my feedback "
            "is ambiguous.")


def saved_state():
    """Which transcript files are unsaved, and which are saved but not finished.

    Lets the tiles distinguish "reviewed but the verdict is still only in a file on this
    laptop" from "reviewed and checkpointed". That difference is the one a reviewer actually
    loses sleep over, and no tile expressed it before.

    Returns (dirty, saved_ahead) as sets of repo-relative paths.
    """
    _, st = git("status", "--porcelain", "--", "transcripts")
    dirty = {porcelain_path(l) for l in st.splitlines() if l.strip()}
    # Committed here but not yet on the shared copy. `--not --remotes` for the same reason
    # unsent_saves() uses it: a lane has no upstream and no matching remote branch.
    rc, out = git("diff", "--name-only", "origin/main...HEAD", "--", "transcripts")
    ahead = {l.strip() for l in out.splitlines() if l.strip()} if rc == 0 else set()
    return dirty, ahead - dirty


# When the transcript sync last actually ran, as an epoch second. SERVER-side on purpose: it
# is a fact about the DATA, not about this browser. Two tabs, or a reload, must not disagree
# about how fresh the transcripts are, and localStorage would give a per-browser answer to a
# question about the repo.
#
# Written to a file so it survives a server restart - the whole point is to be able to say "the
# data you are looking at is N minutes old", and a number that resets to "unknown" every time
# the server bounces cannot say that.
# One stamp per sync kind. SERVER-side, because these are facts about the DATA rather than
# about a browser: two tabs and a reload must agree, and the PRs page navigates on refresh so a
# per-tab clock would reset every time it did its job.
SYNC_STAMPS = {"transcripts": REPO / ".last-transcript-sync",
               "prs": REPO / ".last-pr-sync",
               "analytics": REPO / ".last-analytics-sync"}


def last_sync_age(kind="transcripts"):
    """Seconds since that sync last ran, or None if it never has in this checkout."""
    try:
        return max(0, int(time.time() - float(SYNC_STAMPS[kind].read_text().strip())))
    except Exception:                                          # noqa: BLE001
        return None


def note_sync(kind="transcripts"):
    try:
        SYNC_STAMPS[kind].write_text(str(time.time()))
    except OSError:
        pass                        # a read-only checkout should not break the sync itself


TEAM_ID = "e92bd437-cb84-4e18-88e6-757370b39c90"          # OneTyler Cloud Living
TEAM_NAME = "OneTyler Cloud Living"

# What Foundry's own Analytics tab shows for this team, recomputed from the transcripts API.
#
# WHY RECOMPUTED RATHER THAN PROXIED. Foundry builds that dashboard from
# /api/analytics/advanced/summary-statistics, which returns 403 for a normal API key -
# "User lacks required permissions for this action". So the numbers cannot be fetched; they
# have to be derived. The transcripts API is the same source the review queue uses, which has
# the side benefit that these totals agree with the transcript list rather than being a second,
# differently-derived set.
#
# WHAT CANNOT BE DERIVED, and is therefore shown as unavailable rather than guessed:
# identified subjects, authenticated users and anonymous identities. A team transcript carries
# only {conversationId, teamName, conversation[]}, and an exchange carries only
# {question, response, feedback, thumbsDownTextFeedback} - there is no subject, email or user id
# anywhere in the payload. Foundry has that data server-side; this key cannot see it. Inventing
# a proxy for it (unique first questions, say) would put a number on screen that looks like an
# identity count and is not one.
_AN_CACHE = {"at": 0.0, "data": None}
_AN_TTL = 30 * 60.0


def ot_analytics(force=False):
    """Team-scoped usage figures. Returns (data, error). Cached; `force` refetches."""
    now = time.monotonic()
    if not force and _AN_CACHE["data"] and (now - _AN_CACHE["at"]) < _AN_TTL:
        return _AN_CACHE["data"], None
    if not os.environ.get("FOUNDRY_API_KEY"):
        return None, ("FOUNDRY_API_KEY is not set in the environment this server was started "
                      "from, so Foundry cannot be reached.")
    try:
        lst = _foundry_get(f"/api/transcripts/team_conversation_ids?team_id={TEAM_ID}"
                           "&startDate=01/01/2020")
    except Exception as e:                                     # noqa: BLE001
        return None, f"could not list team conversations: {e}"
    if not isinstance(lst, list):
        return None, "unexpected response listing team conversations"

    # Message counts need one fetch per conversation. Threaded because serially this is ~30
    # round trips; measured 1.3s for 31 conversations at 8 workers against 0.34s for the list.
    import concurrent.futures as cf

    def detail(c):
        try:
            d = _foundry_get(f"/api/transcripts/team/{c['conversationId']}")
            return c, (d[0] if isinstance(d, list) and d else None)
        except Exception:                                      # noqa: BLE001
            return c, None

    pairs = []
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        pairs = list(ex.map(detail, lst))

    per_day_conv, per_day_q = {}, {}
    total_q = 0
    sessions = []
    fb = {"total": 0, "pos": 0, "neg": 0}
    missing = 0
    for c, d in pairs:
        day = (c.get("conversationDate") or "")[:10]
        per_day_conv[day] = per_day_conv.get(day, 0) + 1
        ft = (c.get("feedbackType") or "").upper()
        if ft in ("THUMBS_UP", "POSITIVE"):
            fb["total"] += 1; fb["pos"] += 1
        elif ft in ("THUMBS_DOWN", "NEGATIVE"):
            fb["total"] += 1; fb["neg"] += 1
        if d is None:
            missing += 1
            continue
        n = len(d.get("conversation") or [])
        total_q += n
        per_day_q[day] = per_day_q.get(day, 0) + n
        sessions.append({"id": c["conversationId"], "date": day, "messages": n})

    days = sorted(per_day_conv)
    span = 1
    if days:
        from datetime import date
        try:
            a = date.fromisoformat(days[0]); b = date.fromisoformat(days[-1])
            span = max(1, (b - a).days + 1)
        except ValueError:
            span = max(1, len(days))

    def peak(dd):
        if not dd:
            return 0, ""
        k = max(dd, key=lambda x: dd[x])
        return dd[k], k

    pq, pqd = peak(per_day_q)
    pc, pcd = peak(per_day_conv)
    data = {
        "conversations": len(lst),
        "questions": total_q,
        "q_per_day": round(total_q / span, 1),
        "c_per_day": round(len(lst) / span, 1),
        "peak_q": pq, "peak_q_day": pqd,
        "peak_c": pc, "peak_c_day": pcd,
        "feedback": fb,
        "active_days": len(days),
        "span_days": span,
        "first_day": days[0] if days else "",
        "last_day": days[-1] if days else "",
        "top_days": sorted(per_day_conv.items(), key=lambda x: (-x[1], x[0]))[:5],
        "top_sessions": sorted(sessions, key=lambda s: (-s["messages"], s["date"]))[:5],
        "detail_missing": missing,
    }
    _AN_CACHE.update(at=now, data=data)
    note_sync("analytics")
    return data, None


def git_fragments():
    """The parts of Save & Share that go stale the moment you click something.

    Returned to the browser after every action so it can patch them in place. The alternative -
    reloading the page - would throw away the output panel the reviewer just asked for, which
    is the one thing they are looking at.
    """
    _, st = git("status", "--porcelain", "--", *review_scope())
    changed = [l for l in st.splitlines() if l.strip()]
    n = len(changed)
    # NOT `@{u}..HEAD`. A lane created locally has no upstream, so that errors with
    # "fatal: no upstream configured" - and the raw git error was being interpolated straight
    # into the status line the reviewer reads. Same primitive as unsent_saves(): commits no
    # remote can reach.
    unpushed = str(len(unsent_saves()))

    if n:
        state = (f"<span class='pill pending'>{n} unsent</span> "
                 f"You have <b>{n}</b> edited file(s) not yet saved.")
    elif unpushed != "0":
        state = (f"<span class='pill reviewed'>saved</span> Saved, but "
                 f"<b>{unpushed}</b> change(s) have not been sent in yet — do Part 2.")
    else:
        state = ("<span class='pill pushed'>all sent</span> Nothing waiting. "
                 "Everything you have reviewed has been sent in.")

    files = ("<ul style='margin:6px 0 0 18px;padding:0'>"
             + "".join(f"<li>{html.escape(porcelain_path(l))}</li>" for l in changed[:12])
             + (f"<li>… and {n - 12} more</li>" if n > 12 else "")
             + "</ul>") if changed else \
            "<div class=hint style='margin-top:6px'>Nothing edited yet — review something on " \
            "<b>My Transcripts</b> first.</div>"

    saves = unsent_saves()
    if saves:
        # Collapsed. It is a record of what already happened, so it is the last thing anyone
        # needs on arrival, and left open it pushes the two actual buttons down the page. The
        # count sits in the summary so the section answers its own question unopened. The
        # browser re-applies the reviewer's own open/closed state after a refresh.
        saves_html = (
            "<details class=saves><summary>See progress history"
            f"<span class=hint> &mdash; <b>{len(saves)}</b> save(s) not sent in yet</span>"
            "<span class=chev aria-hidden=true></span></summary>"
            "<table>" + "".join(
                f"<tr><td class=swhen>{html.escape(s['when'])}</td>"
                f"<td>{html.escape(s['subject'])}</td>"
                # "and everything newer" is stated on every row, because the one-directional
                # rule is the thing people will not expect. Git history is a chain: pulling a
                # link out of the middle rewrites everything above it, so the only coherent
                # discard is a rewind.
                f"<td class=sstate><button type=button class=sec "
                f"onclick=\"discardSave(this,'{s['h']}','{html.escape(s['when'])}',{i})\" "
                f"title='Discard this save and every save newer than it'>"
                f"Discard this{' and ' + str(i) + ' newer' if i else ''}</button></td></tr>"
                for i, s in enumerate(saves))
            + "</table>"
            "<div class=hint>Sending them in covers all of these at once. A save drops off "
            "this list as soon as it has been sent.<br>Discarding rewinds to just before the "
            "save you pick — it cannot remove one from the middle, and it always leaves a "
            "recovery point.</div></details>")
    else:
        saves_html = ("<div class=saves><span class=hint>Nothing saved and unsent — either "
                      "you have not saved yet this sitting, or everything is already sent "
                      "in.</span></div>")
    return {"state": state, "files": files, "saves": saves_html, "unsent": n}


def gh(*args, timeout=180):
    """Run gh with the admin's own credentials. There is deliberately no shared token in this
    repo: a PAT in a repo secret is readable by any write-access contributor's PR."""
    r = subprocess.run(["gh", *args], cwd=REPO, capture_output=True, text=True,
                       timeout=timeout)
    return r.returncode, (r.stdout + r.stderr).strip()


def _is_behind(out):
    """Did GitHub refuse because the branch is behind main, rather than for a real problem?

    This repo sets `required_status_checks.strict`, so a branch behind main cannot merge until
    it is brought up to date. GitHub words that as:

        Pull request ...#31 is not mergeable: the head branch is not up to date with the
        base branch.

    Worth its own test because the phrase "not mergeable" also appears on genuine conflicts,
    and the two need opposite handling - this one is fixed by updating the branch, that one
    needs a human in an editor. `_needs_override` used to lump them together and return False
    for both, so a behind-main refusal produced the raw gh error with no guidance attached.
    Observed 2026-08-28 on #31.
    """
    low = (out or "").lower()
    return "not up to date with the base branch" in low or "head branch is not up to date" in low


def _needs_override(out):
    """Did GitHub refuse purely for a missing approval, as opposed to a real problem?

    Matters because the two need different answers: a missing approval is something an admin
    may legitimately override on their own work, while failing checks or a conflict are not.

    Note the behind-main case is deliberately NOT here - it is handled before this is called,
    by updating the branch. Leaving it to fall through to "conflict" wording was the bug.
    """
    low = (out or "").lower()
    if _is_behind(out):
        return False
    if any(k in low for k in ("conflict", "not mergeable", "check", "failing")):
        return False
    return any(k in low for k in ("review", "approv", "protected", "required"))


def behind_main():
    """How many commits origin/main is ahead of this checkout, and on which branch.

    Returns (count, branch, err). Reads refs only - no fetch - so it is cheap enough to call
    on a page render. Something else has to do the fetching.
    """
    rc, cur = git("rev-parse", "--abbrev-ref", "HEAD")
    if rc != 0:
        return 0, "", cur
    cur = cur.strip()
    rc, out = git("rev-list", "--count", "origin/main", f"^{cur}")
    if rc != 0:
        return 0, cur, out
    try:
        return int(out.strip() or 0), cur, ""
    except ValueError:
        return 0, cur, out


def pull_main():
    """Bring the checkout up to date with origin/main after something merged.

    WHY THIS EXISTS. Merging only changes the REMOTE - `gh pr merge` and the GitHub web UI
    both leave the working tree exactly as it was. The review UI reads the working TREE, so
    the moment a merge lands, every file it touched is stale on disk and the app is out of
    date because of its own action. Observed 2026-08-28: a transcript reviewed, merged and
    closed out reappeared in the pending queue, because the checkout was one commit behind and
    the file on disk was still the pre-review copy. That reads as "my verdict was thrown away",
    which is the worst possible way for staleness to present.

    FAST-FORWARD ONLY, deliberately. `--ff-only` REFUSES when there is local work rather than
    moving it, and git refuses outright if the update would overwrite a modified file. Both
    matter here: a `git reset --hard` earlier in this repo's history destroyed a reviewer's
    unsaved verdicts, and nothing in an auto-action after a merge is worth risking that again.
    A refusal is reported; it is never forced.

    On a review lane the tree is NOT touched. The lane is someone's sitting in progress, and
    rebasing it under them mid-review could conflict halfway through. The local `main` ref is
    advanced without a checkout (`fetch origin main:main`, itself fast-forward-only) so the
    next return to main is already correct, and the caller is told the tree is still behind.
    """
    rc, out = git("fetch", "--prune", "origin", timeout=120)
    if rc != 0:
        return False, "Could not fetch from origin, so the checkout may be stale:\n" + out

    _, cur = git("rev-parse", "--abbrev-ref", "HEAD")
    cur = cur.strip()
    behind, _, _ = behind_main()

    if cur.startswith("review/"):
        # Not checked out, so this cannot touch the working tree; still fast-forward-only.
        git("fetch", "origin", "main:main")
        if behind:
            return True, ("Your in-progress work is left exactly as it is, so "
                          + (f"{behind} changes" if behind > 1 else "1 change")
                          + " other people sent in is not on your copy yet. It arrives on its "
                          "own once this batch is sent in.")
        return True, ""

    if cur != "main":
        return True, ""

    if not behind:
        return True, ""

    rc, out = git("merge", "--ff-only", "origin/main", timeout=120)
    if rc != 0:
        # NOT reported as a failure. Having unsaved verdicts on main is the normal state
        # before the first save of a sitting, and the sync runs on a timer - so calling this
        # an error would put a red banner in front of every reviewer every half hour for
        # doing exactly what they are supposed to be doing. It is a note, and it resolves
        # itself the moment they save. The raw git text is dropped on purpose: "Updating
        # 16fe4c1..bc889c2" is not something anyone here should have to read.
        return True, ("You have unsaved edits, so the newest copies of a few files are not in "
                      f"yet ({behind} waiting). Nothing was changed or discarded. They come in "
                      "on their own once you save.")
    return True, (f"Brought in {behind} updates from the shared copy." if behind > 1
                  else "Brought in 1 update from the shared copy.")


def merge_pr(num, override):
    """Merge a change request, bringing the branch up to date first if that is what is needed.

    Why the retry rather than a separate "Update branch" button. The reviewer asked for the
    merge action to handle this itself, and the state machine cannot reliably decide up front:
    `mergeStateStatus` holds ONE value, so when a request both needs an approval and is behind
    main, GitHub reports only one of them. #31 on 2026-08-28 was BLOCKED, then #30 merged, then
    it was BEHIND - and the card had been rendered from data where the field was empty
    altogether, which is how a plain Merge button appeared on a request that needed an
    override. Attempting the merge and reacting to the actual refusal is the only version of
    this that cannot be wrong about the state, because it asks GitHub instead of guessing.

    One retry, not a loop: if it is still refused after being brought up to date, the reason is
    something else and repeating will not help.
    """
    args = ["pr", "merge", num, "--rebase", "--delete-branch"]
    if override:
        args.insert(3, "--admin")
    rc, out = gh(*args)
    if rc == 0 or not _is_behind(out):
        return rc, out, False

    rcu, outu = gh("pr", "update-branch", num, "--rebase")
    if rcu != 0:
        return rcu, ("The branch is behind main, and bringing it up to date failed, so nothing "
                     "was merged:\n\n" + outu), True
    # GitHub recomputes mergeability asynchronously after a rebase; without this the retry
    # races the recompute and reports the same "not up to date" it just fixed.
    time.sleep(4)
    rc, out = gh(*args)
    return rc, ("Brought the branch up to date with main first (rebased).\n\n" + out), True


PR_FIELDS = ("number,title,author,isDraft,headRefName,reviewDecision,mergeable,"
             "mergeStateStatus,statusCheckRollup,createdAt,url,additions,deletions,"
             "changedFiles,files")

# `mergeable` only reports CONFLICTS. `mergeStateStatus` reports POLICY, and it is the field
# that decides which button can actually work:
#
#   CLEAN     nothing in the way - a plain merge succeeds
#   BLOCKED   a required review is missing - a plain merge is REFUSED, only --admin works
#   BEHIND    main has moved and this repo requires branches to be up to date
#             (required_status_checks.strict = True), so it must be updated first
#   DIRTY     real conflicts - not mergeable from here at all
#   UNSTABLE  checks failing or pending, but mergeable
#
# Measured 2026-08-27: all four open requests were BLOCKED, which is why a plain "Merge"
# button on them could never have worked - the repo requires an approval and the sole code
# owner cannot approve his own.
MERGE_STATE = {
    "CLEAN": ("ready to merge", "reviewed"),
    "BLOCKED": ("needs approval", "excluded"),
    "BEHIND": ("behind main", "pending"),
    "DIRTY": ("conflicts", "bad"),
    "UNSTABLE": ("checks not green", "pending"),
    "UNKNOWN": ("state unknown", "excluded"),
    "HAS_HOOKS": ("ready to merge", "reviewed"),
}


def open_prs():
    """Open and draft change requests, newest first. Returns (list, error).

    Shells out to `gh` rather than calling the API directly: gh already holds the reviewer's
    own credentials, and this repo deliberately has no shared token - a PAT in a repo secret
    would be readable by any write-access contributor's PR.
    """
    if not shutil.which("gh"):
        return [], ("The GitHub CLI (gh) is not installed, so change requests cannot be listed "
                    "from here. Install it, or use the link on the Save & Publish page.")
    r = subprocess.run(["gh", "pr", "list", "--state", "open", "--limit", "50",
                        "--json", PR_FIELDS],
                       cwd=REPO, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return [], (r.stderr or r.stdout).strip()[:400]
    try:
        prs = json.loads(r.stdout or "[]")
    except json.JSONDecodeError:
        return [], "gh returned something that is not JSON"
    prs.sort(key=lambda x: x["number"], reverse=True)
    return prs, None


# Transcripts that are already inside an open change request.
#
# WHY THIS EXISTS. `fetch_transcripts.py` decides "is this new?" with `p.exists()` - the
# WORKING TREE and nothing else. It has no idea about branches or open requests. So a
# transcript reviewed on a branch, committed, and sitting in an unmerged request does not
# exist on main, and a sync from main happily re-creates it as a fresh `pending` stub.
#
# Measured 2026-08-27 on a clean main checkout: `--dry-run` reported "would add: 4 new", of
# which THREE were transcripts already reviewed inside PR #18. Someone would then have
# re-reviewed work that was already done, and the merge would collide.
#
# Pulling them anyway is the right call - the alternative is a sync that silently withholds
# conversations - so instead the row says so and links to the request.
_TPR_CACHE = {"at": 0.0, "map": {}, "ok": False}
_TPR_TTL = 60.0


def transcript_pr_map(force=False):
    """{rel -> {"number", "url"}} for transcripts touched by an open change request.

    `rel` is relative to transcripts/, matching the review UI's own keys.
    """
    now = time.monotonic()
    if not force and _TPR_CACHE["ok"] and (now - _TPR_CACHE["at"]) < _TPR_TTL:
        return _TPR_CACHE["map"]
    out = {}
    if shutil.which("gh"):
        try:
            r = subprocess.run(["gh", "pr", "list", "--state", "open", "--limit", "50",
                                "--json", "number,url,files"],
                               cwd=REPO, capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                for pr in json.loads(r.stdout or "[]"):
                    for f in pr.get("files") or []:
                        path = f.get("path", "")
                        if not (path.startswith("transcripts/") and path.endswith(".md")):
                            continue
                        rel = path[len("transcripts/"):]
                        # Only real transcripts. INDEX.md and README.md live in this folder
                        # and change on nearly every request, so without this the badge
                        # appeared against docs. Matching on the SHAPE of the path rather
                        # than a blocklist, for the reason is_transcript() gives: a blocklist
                        # broke the moment ONBOARDING.md was added.
                        if "/" not in rel or not re.match(r"^\d{4}-\d{2}-\d{2}--",
                                                          rel.split("/")[-1]):
                            continue
                        if True:
                            # Lowest PR number wins only for stability of display; a
                            # transcript in two requests is itself worth noticing, and the
                            # badge links to one of them rather than pretending there is one.
                            out.setdefault(rel, {"number": pr["number"], "url": pr["url"]})
        except Exception:                                          # noqa: BLE001
            out = _TPR_CACHE["map"]
    _TPR_CACHE.update(at=now, map=out, ok=True)
    return out


def pr_kind(pr):
    """What a change request is MADE of, and therefore what merging it obliges.

    The distinction the page exists to surface: a request that touches Knowledge-* files owes a
    Foundry upload after merging, and one that does not owes nothing. Getting that wrong in
    either direction is expensive - a missed upload leaves the live agents answering from old
    text while the repo looks correct, and an unnecessary one is a production write for no
    reason.

    `files` comes back in the same `gh pr list` call as everything else, so this costs no extra
    network round-trip.
    """
    paths = [f.get("path", "") for f in (pr.get("files") or [])]
    kb = sorted({x.split("/")[0] for x in paths if x.startswith("Knowledge-")})
    tr = [x for x in paths if x.startswith("transcripts/")]
    other = [x for x in paths if not x.startswith(("Knowledge-", "transcripts/"))]
    cols = []
    for folder in kb:
        for c in FOLDER_COLLECTION.get(folder, []):
            if c not in cols:
                cols.append(c)
    bits = []
    if kb:
        bits.append(f"<b>{len([x for x in paths if x.startswith('Knowledge-')])}</b> "
                    "knowledge file(s)")
    if tr:
        bits.append(f"<b>{len(tr)}</b> transcript(s)")
    if other:
        bits.append(f"<b>{len(other)}</b> tooling/doc file(s)")
    return {"cols": cols, "summary": " &middot; ".join(bits) or "no files",
            "kb": bool(kb)}


def pr_checks(pr):
    """Reduce the check rollup to one word. `gh` reports per-check rows; what a human wants is
    whether it is safe to merge."""
    rows = pr.get("statusCheckRollup") or []
    if not rows:
        return "none", "No checks ran on this one."
    states = [(c.get("conclusion") or c.get("state") or "").upper() for c in rows]
    if any(s in ("FAILURE", "ERROR", "TIMED_OUT", "CANCELLED") for s in states):
        return "failing", "At least one check failed — do not merge without looking."
    if any(s in ("PENDING", "IN_PROGRESS", "QUEUED", "") for s in states):
        return "running", "Checks are still running."
    return "passing", f"All {len(rows)} check(s) passed."


def pr_page(force=False):
    """Approve and merge change requests without leaving the tool. ADMINS ONLY.

    Exists because merging was the one step in the loop that always meant leaving for GitHub,
    and on a repo where one person is both author and sole code owner that is a lot of
    round-trips for something with two possible answers.

    It does NOT try to be GitHub. There is no diff view, no comments, no file browser - the
    change request itself is one click away for all of that. What is here is the decision:
    what is open, is it safe, and merge it.
    """
    # Every render of this page IS a PR fetch - open_prs() is uncached - so the age shown here
    # is the age of what you are looking at, not of some earlier background job.
    note_sync("prs")
    if force:
        # A merge or an approval done elsewhere (the GitHub UI, a teammate) is invisible until
        # something re-asks. `open_prs()` is uncached so it is always current, but the nav
        # badge and the transcript badges are cached for 60s - this drops both so the whole
        # page agrees rather than the cards being fresh and the badges a minute behind.
        transcript_pr_map(force=True)
        pr_count(force=True)
    prs_age = last_sync_age("prs") or 0
    prs, err = open_prs()
    if not err:
        # Seed the badge from the list we just fetched, so merging something updates the nav
        # on the next render instead of up to a minute later.
        _PR_CACHE.update(at=time.monotonic(), n=len(prs), ok=True)
    body = ["<div style='display:flex;align-items:center;gap:12px;flex-wrap:wrap;"
            "margin-bottom:22px'>"
            "<h2 class=sec style='margin:0'>Change Requests</h2>"
            "<a href='/prs?refresh=1' style='margin-left:auto;text-decoration:none' "
            "title='Runs by itself when this is more than 30 minutes old'>"
            "<button class=sec>&#8635; Refresh PRs</button></a>"
            f"<span class=fresh id=freshness data-age='{prs_age}' data-kind=prs></span></div>"
            "<p class=sub style='margin:-14px 0 20px'>Refreshes by itself when it is more "
            "than 30 minutes stale, and whenever you come back to this tab.</p>"]
    if err:
        body.append(f"<div class='bar bnr-done'>{html.escape(err)}</div>")
    if not prs and not err:
        body.append("<div class=card><h3>Nothing open</h3>"
                    "<p class=sub>Every change request has been merged or closed.</p></div>")
    for pr in prs:
        cls, why = pr_checks(pr)
        kind = pr_kind(pr)
        mine = pr["author"]["login"] == (ME or "")
        draft = pr.get("isDraft")
        decision = pr.get("reviewDecision") or ""
        mergeable = (pr.get("mergeable") or "").upper()
        age = (pr.get("createdAt") or "")[:10]

        pill = ("<span class='pill suggested'>draft</span>" if draft
                else "<span class='pill pending'>open</span>")
        chk = {"passing": "<span class='pill reviewed'>checks passed</span>",
               "failing": "<span class='pill bad'>checks failed</span>",
               "running": "<span class='pill pending'>checks running</span>",
               "none": "<span class='pill excluded'>no checks</span>"}[cls]
        approved = decision == "APPROVED"
        # Only when it says something the merge-state pill does not. REVIEW_REQUIRED and
        # mergeStateStatus=BLOCKED are the same fact, and rendering both put "needs approval"
        # on the card twice.
        rev = ("<span class='pill reviewed'>approved</span>" if approved
               else "<span class='pill bad'>changes requested</span>"
               if decision == "CHANGES_REQUESTED" else "")
        st_label, st_cls = MERGE_STATE.get(
            (pr.get("mergeStateStatus") or "UNKNOWN").upper(), ("state unknown", "excluded"))
        conflict = f"<span class='pill {st_cls}'>{st_label}</span>"

        state = (pr.get("mergeStateStatus") or "UNKNOWN").upper()
        acts = []
        if draft:
            acts.append(f"<button class=sec onclick=\"prDo(this,'ready',{pr['number']})\">"
                        "Mark ready for review</button>")
        if not mine and not approved:
            acts.append(f"<button class=sec onclick=\"prDo(this,'approve',{pr['number']})\">"
                        "Approve</button>")

        # EXACTLY ONE merge button, and WHOSE REQUEST IT IS decides which one - not
        # mergeStateStatus. That was the original ask ("show either Merge or Merge anyway
        # depending on if it is my PR"), and keying off the state got it wrong twice on
        # 2026-08-28:
        #
        #   * The field holds ONE value. #31 needed an approval AND was behind main; GitHub
        #     reported only BEHIND, so the "needs approval" fact vanished and with it the
        #     override button.
        #   * When the field came back EMPTY, state fell to UNKNOWN and dropped through to the
        #     else-branch, putting a plain "Merge" on a request that could only ever merge with
        #     the override. It failed, and the label had silently changed under the reviewer.
        #     GitHub computes mergeability ASYNCHRONOUSLY and reports the field empty until it
        #     finishes - and it restarts that work on every push to the base. So the blank
        #     window opens the moment another request merges, which is exactly when someone is
        #     looking at the next one. Any button chosen from this field is racing a recompute.
        #
        # Author identity does not fluctuate, so the label no longer moves around. Being behind
        # main is handled inside the merge action now, so it needs no button of its own.
        if state == "DIRTY":
            pass                       # conflicts need a human in a editor, not a button here
        elif mine:
            acts.append(f"<button onclick=\"prOverride(this,{pr['number']},"
                        f"'{html.escape(pr['title'][:60])}','{cls}')\" "
                        "title='Merge using your admin override, which skips the required "
                        "approval you cannot give yourself'>Merge anyway</button>")
        else:
            acts.append(f"<button onclick=\"prMerge(this,{pr['number']},"
                        f"'{html.escape(pr['title'][:60])}','{cls}')\">Merge</button>")

        # Why Approve is missing on your own change request. GitHub refuses it outright, so a
        # button here would only ever produce an error - saying so is more use than hiding it
        # silently. Admins can merge without an approval anyway, which is what makes the repo
        # workable with one code owner.
        if mine:
            behind = (" Main has also moved since this branch was cut; the merge brings it up "
                      "to date first, so there is nothing to do by hand."
                      if state == "BEHIND" else "")
            selfnote = ("<div class=hint style='margin-top:8px'>This is your own change "
                        "request, so a plain merge is refused: an approval is required and "
                        "GitHub does not let anyone approve their own. <b>Merge anyway</b> "
                        "uses your admin override, which skips that gate &mdash; reasonable on "
                        "your own work, and the only way through on a repo with one code "
                        f"owner.{behind}</div>")
        elif state == "BLOCKED":
            selfnote = ("<div class=hint style='margin-top:8px'>Needs an approval before a "
                        "plain merge will go through. <b>Approve</b> it first.</div>")
        elif state == "BEHIND":
            selfnote = ("<div class=hint style='margin-top:8px'>Main has moved and this repo "
                        "requires branches to be up to date. <b>Merge</b> brings it up to date "
                        "first, so there is nothing to do by hand &mdash; but the required "
                        "checks re-run after that, so it may need a second press once they "
                        "are green.</div>")
        elif state == "DIRTY":
            selfnote = ("<div class=hint style='margin-top:8px'>Real conflicts with main. They "
                        "have to be resolved in the branch &mdash; there is no button for "
                        "that.</div>")
        else:
            selfnote = ""

        body.append(
            "<div class=card>"
            f"<h3><a href=\"{html.escape(pr['url'])}\" target=_blank rel=noopener>"
            f"#{pr['number']}</a> {html.escape(pr['title'][:110])}</h3>"
            f"<p class=sub>{html.escape(pr['author']['login'])} &middot; {age} &middot; "
            f"<code>{html.escape(pr['headRefName'])}</code> &middot; "
            f"+{pr['additions']} &minus;{pr['deletions']} across {pr['changedFiles']} file(s)"
            "</p>"
            f"<div class=prpills>{pill}{chk}{rev}{conflict}</div>"
            f"<p class=sub style='margin-top:8px'>{kind['summary']}</p>"
            f"<p class=sub>{html.escape(why)}</p>"
            + (f"<div class='hint fdrynote'>Merging this obliges a Foundry upload to "
               f"<b>{html.escape(', '.join(kind['cols']))}</b>. Afterwards:<br>"
               "<code>python3 scripts/publish_to_foundry.py</code></div>"
               if kind["kb"] else
               "<div class=hint>No Foundry upload needed — this one does not touch knowledge "
               "files.</div>")
            + f"{selfnote}"
            f"<div class=stepacts>{''.join(acts)}"
            f"<a href=\"{html.escape(pr['url'])}\" target=_blank rel=noopener>"
            "<button class=sec>Open on GitHub</button></a></div>"
            "</div>")
    return page("Change Requests", "<div class=lg>" + "".join(body) + "</div>", active="prs")


# ---------------------------------------------------------------------------------------------
# Config backups (read-only)
#
# The snapshots live in a SEPARATE private repo, onetyler-foundry-config-backups, and are read
# here over `gh` rather than from a local clone. Two reasons:
#
#   * Nobody should need a second checkout to answer "did the backup run?".
#   * The backup repo is admin-only. A local clone in a contributor's tree would put agent
#     instructions, tenant s3Key paths and per-file DELETE handles on their disk, which is
#     exactly the access decision that repo exists to enforce.
#
# READ-ONLY, DELIBERATELY. There is no restore button and no write path of any kind. Restoring
# an agent config is an unverified operation - PUT semantics for /api/configurable-agents are
# undocumented and have never been exercised - so the first time anyone runs it should be a
# considered act at a terminal, not a button click on a dashboard during an incident.
BACKUP_REPO = "tyler-technologies/onetyler-foundry-config-backups"
_BK_CACHE = {"at": 0.0, "data": None}
_BK_TTL = 5 * 60.0

# Every path served by the file browser must start with one of these. Not because a reviewer is
# a threat, but because `gh api contents/<path>` will happily fetch anything in the repo if the
# query string says so, and a browser that can read arbitrary paths is a different feature from
# one that shows backups.
BK_ROOTS = ("snapshots/", "CHANGES.md", "README.md")


def _bk_file(relpath):
    """Raw text of one file in the backup repo. Returns (text, err)."""
    import base64
    rc, out = gh("api", f"repos/{BACKUP_REPO}/contents/{relpath}", "-q", ".content", timeout=45)
    if rc != 0:
        return None, out.strip()[:300]
    try:
        return base64.b64decode(out).decode("utf-8", "replace"), None
    except Exception as e:                                            # noqa: BLE001
        return None, str(e)


def _bk_ls(relpath):
    """Directory listing. Returns (rows, err) where a row is (name, type, size)."""
    rc, out = gh("api", f"repos/{BACKUP_REPO}/contents/{relpath}",
                 "-q", r'.[] | [.name, .type, (.size|tostring)] | @tsv', timeout=45)
    if rc != 0:
        return None, out.strip()[:300]
    rows = [tuple(l.split("\t")) for l in out.splitlines() if l.strip()]
    return [r for r in rows if len(r) == 3], None


def backups(force=False):
    """Everything the Backups page shows, in one cached bundle.

    Cached for 5 minutes because this is 5 `gh` calls against a remote repo and the page is a
    status board, not a live feed. The snapshot it describes only changes once a day.
    """
    now = time.time()
    if not force and _BK_CACHE["data"] and (now - _BK_CACHE["at"]) < _BK_TTL:
        return _BK_CACHE["data"], None

    if not shutil.which("gh"):
        return None, ("The GitHub CLI (gh) is not installed, so the backup repo cannot be read "
                      "from here.")

    d = {"repo": BACKUP_REPO, "last_run": None, "dates": [], "manifest": None,
         "changes": [], "runs": [], "releases": [], "notes": []}

    txt, err = _bk_file("snapshots/LAST_RUN")
    if err:
        # The most likely cause by far is no access, and saying so beats a raw gh error.
        return None, (f"Could not read {BACKUP_REPO}. This is admin-only, so the usual cause is "
                      f"that your `gh` account is not on the onetyler-tcp-pm-admins team.\n\n{err}")
    d["last_run"] = txt.strip()

    rows, err = _bk_ls("snapshots")
    if rows:
        d["dates"] = sorted((n for n, ty, _ in rows if ty == "dir"), reverse=True)
    elif err:
        d["notes"].append(f"snapshot list unavailable: {err}")

    if d["dates"]:
        txt, err = _bk_file(f"snapshots/{d['dates'][0]}/MANIFEST.json")
        if txt:
            try:
                d["manifest"] = json.loads(txt)
            except json.JSONDecodeError:
                d["notes"].append("latest MANIFEST.json did not parse")

    txt, _ = _bk_file("CHANGES.md")
    if txt:
        d["changes"] = [l.strip() for l in txt.splitlines()
                        if l.strip().startswith("- **")][::-1][:12]

    rc, out = gh("run", "list", "--repo", BACKUP_REPO, "--limit", "8", "--json",
                 "name,status,conclusion,createdAt,event", timeout=60)
    if rc == 0:
        try:
            d["runs"] = json.loads(out)
        except json.JSONDecodeError:
            pass

    rc, out = gh("release", "list", "--repo", BACKUP_REPO, "--limit", "20",
                 "--json", "tagName,createdAt", timeout=60)
    if rc == 0:
        try:
            d["releases"] = [r for r in json.loads(out)
                             if str(r.get("tagName", "")).startswith("mirror-")]
        except json.JSONDecodeError:
            pass

    _BK_CACHE.update(at=now, data=d)
    return d, None


# ---------------------------------------------------------------------------------------------
# Restore actions. THE ONLY PLACE THIS APP WRITES TO PRODUCTION.
#
# Everything else in this UI writes to git. These three change what live agents tell customers,
# so each one is shaped around what was actually MEASURED on 2026-08-28 rather than around what
# the API docs imply:
#
#   POST /api/configurable-agents/{id}/versions          201. Needs {"type":"full","name":...}.
#                                                        Provably non-destructive - creates a
#                                                        restore point, leaves the agent alone.
#   PUT  /api/configurable-agents/{id}/tenant-kb-config  200. CONTENT-IDEMPOTENT: PUTting the
#                                                        existing value changed only
#                                                        metadata.updatedAt. Touches nothing
#                                                        else about the agent.
#   PUT  /api/configurable-agents/{id}                   200. Full replace, 12 required fields.
#                                                        Built from the LIVE object with one
#                                                        field swapped, ONLY that field moved -
#                                                        verified field-by-field, nothing wiped.
#   POST .../versions/{vid}/restore                       200 - but ONLY with
#                                                        `Content-Type: application/json`.
#                                                        Without it: 400 "Content-Type must be
#                                                        application/json" despite having no
#                                                        body. Same trap as POST /sync. This
#                                                        cost a real failed restore during
#                                                        testing, with the agent left modified
#                                                        until the retry.
#
# The full round trip was exercised end to end on the SAC agent: version -> kb PUT -> config PUT
# with one field changed -> restore -> compared byte for byte against the pre-test capture.
# Identical. So these are tested paths, not hopeful ones.


def _foundry_write(method, path, payload=None, timeout=120):
    """Write to Foundry. Returns (status, parsed_or_text).

    Content-Type is ALWAYS sent, including when there is no body. `POST /versions/{id}/restore`
    takes no body and still rejects the request without the header - a 400 that reads like a
    malformed payload when the payload is the thing that does not exist.
    """
    import urllib.request
    import urllib.error
    base = os.environ.get("FOUNDRY_API_URL", "https://foundry.tylertechai.com").rstrip("/")
    body = json.dumps(payload if payload is not None else {}).encode()
    req = urllib.request.Request(base + path, method=method, data=body)
    req.add_header("X-API-Key", os.environ.get("FOUNDRY_API_KEY", ""))
    req.add_header("User-Agent", "claude-code-foundry-kb/1.0")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            try:
                return r.status, json.loads(raw or "null")
            except json.JSONDecodeError:
                return r.status, raw[:400]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:400]
    except Exception as e:                                            # noqa: BLE001
        return 0, str(e)


# Fields never sent back on a PUT. They are server-owned, and echoing them either does nothing
# or is rejected. `version` in particular is Foundry's own counter.
BK_READONLY_FIELDS = ("tenant_id", "project_id", "creation_source", "origin", "canTest",
                      "version")
BK_TIMESTAMPS = ("updated_at", "updatedAt", "modifiedAt", "createdAt", "created_at")


def _bk_strip_ts(o):
    """Drop timestamps at every depth, so a comparison reports content rather than clock."""
    if isinstance(o, dict):
        return {k: _bk_strip_ts(v) for k, v in o.items() if k not in BK_TIMESTAMPS}
    if isinstance(o, list):
        return [_bk_strip_ts(x) for x in o]
    return o


def bk_take_version(slug, label):
    """Create a native restore point for an agent. Returns (ok, message).

    Called before every write here. It is one call, it is provably non-destructive, and it is
    the difference between a reversible action and a one-way one.
    """
    aid = BK_AGENT_ID.get(slug)
    if not aid:
        return False, f"unknown agent slug {slug!r}"
    code, out = _foundry_write("POST", f"/api/configurable-agents/{aid}/versions",
                               {"type": "full", "name": label[:80]})
    if code not in (200, 201):
        return False, f"could not create a restore point (HTTP {code}): {str(out)[:200]}"
    n = out.get("version_number") if isinstance(out, dict) else "?"
    vid = out.get("id") if isinstance(out, dict) else "?"
    return True, f"restore point created: v{n} ({vid})"


def bk_agent_field_diff(slug, date):
    """Per-field differences between the live agent and a snapshot. Returns (rows, err).

    A row is (field, live_value, snapshot_value). Flattened to dotted paths so the picker can
    offer one checkbox per actual field rather than per top-level blob.
    """
    aid = BK_AGENT_ID.get(slug)
    if not aid:
        return None, f"unknown agent {slug!r}"
    saved, err = _bk_file(f"snapshots/{date}/agents/{slug}.json")
    if err:
        return None, f"snapshot unavailable: {err}"
    try:
        snap = _bk_strip_ts(json.loads(saved))
    except json.JSONDecodeError as e:
        return None, f"snapshot did not parse: {e}"
    try:
        live = _bk_strip_ts(_foundry_get(f"/api/configurable-agents/{aid}"))
    except Exception as e:                                            # noqa: BLE001
        return None, f"could not read the live agent: {e}"

    rows = []
    for k in sorted(set(live) | set(snap)):
        if k in BK_READONLY_FIELDS:
            continue
        a, b = live.get(k), snap.get(k)
        if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True):
            rows.append((k, a, b))
    return rows, None


def bk_restore_fields(slug, date, fields):
    """Roll back CHOSEN fields of an agent to a snapshot. Returns (ok, message).

    THE PAYLOAD IS BUILT FROM THE LIVE OBJECT, with only the chosen fields replaced.
    
    PUTting the snapshot wholesale is the obvious implementation and the wrong one: a snapshot
    from three days ago also reverts every legitimate change made since, which looks surgical
    and is not. Measured on the SAC agent: a live-derived payload with one field swapped moved
    ONLY that field.
    """
    aid = BK_AGENT_ID.get(slug)
    if not aid:
        return False, f"unknown agent {slug!r}"
    if not fields:
        return False, "no fields were selected, so nothing was written"

    saved, err = _bk_file(f"snapshots/{date}/agents/{slug}.json")
    if err:
        return False, f"snapshot unavailable: {err}"
    try:
        snap = json.loads(saved)
        live = _foundry_get(f"/api/configurable-agents/{aid}")
    except Exception as e:                                            # noqa: BLE001
        return False, f"could not read live or snapshot: {e}"

    missing = [f for f in fields if f not in snap]
    if missing:
        return False, (f"the {date} snapshot has no value for {', '.join(missing)} — refusing "
                       "rather than sending a null for a field that may be required")

    ok, msg = bk_take_version(slug, f"pre-field-restore-{date}")
    if not ok:
        return False, msg + "\n\nNothing was written — a restore without an undo is not worth it."

    body = {k: v for k, v in live.items() if k not in BK_READONLY_FIELDS}
    for f in fields:
        body[f] = snap[f]
    code, out = _foundry_write("PUT", f"/api/configurable-agents/{aid}", body)
    if code != 200:
        return False, f"{msg}\n\nPUT failed (HTTP {code}): {str(out)[:300]}"

    # Verify by re-reading, not by trusting the 200. And check that ONLY the chosen fields
    # moved - the whole risk of a full-replace PUT is collateral change.
    try:
        now = _bk_strip_ts(_foundry_get(f"/api/configurable-agents/{aid}"))
    except Exception as e:                                            # noqa: BLE001
        return True, f"{msg}\n\nWritten, but could not re-read to verify: {e}"
    before = _bk_strip_ts(live)
    moved = [k for k in set(before) | set(now)
             if k not in BK_READONLY_FIELDS
             and json.dumps(before.get(k), sort_keys=True)
             != json.dumps(now.get(k), sort_keys=True)]
    unexpected = sorted(set(moved) - set(fields))
    lines = [msg, "",
             f"Restored {len(fields)} field(s) on {slug} from the {date} snapshot: "
             + ", ".join(fields)]
    if unexpected:
        lines += ["", "⚠ These fields ALSO changed and were not selected: "
                      + ", ".join(unexpected),
                  "  The restore point above is how you undo this."]
    else:
        lines += ["", "Verified: only the selected field(s) changed."]
    lines += ["", "Now ask the agent a question it should answer from this config. Text landing "
                  "in a field is not the same as behaviour being restored."]
    return True, "\n".join(lines)


def bk_restore_kb(slug, date):
    """Roll back one agent's knowledge-base bindings. Returns (ok, message).

    The safest write available here. `PUT /{id}/tenant-kb-config` takes only collectionConfigs
    and dataSourceConfigs, with no required fields, so it cannot disturb instructions, model,
    tools or guardrails. Measured content-idempotent: PUTting the existing value changed only
    metadata.updatedAt.
    """
    aid = BK_AGENT_ID.get(slug)
    if not aid:
        return False, f"unknown agent {slug!r}"
    saved, err = _bk_file(f"snapshots/{date}/agents/{slug}.json")
    if err:
        return False, f"snapshot unavailable: {err}"
    try:
        kb = (json.loads(saved).get("tenantKBConfig") or {})
    except json.JSONDecodeError as e:
        return False, f"snapshot did not parse: {e}"
    if not kb.get("collectionConfigs"):
        return False, (f"the {date} snapshot has no collectionConfigs for {slug} — refusing, "
                       "since writing an empty binding would leave the agent with no knowledge "
                       "base at all")

    ok, msg = bk_take_version(slug, f"pre-kb-restore-{date}")
    if not ok:
        return False, msg + "\n\nNothing was written."

    code, out = _foundry_write(
        "PUT", f"/api/configurable-agents/{aid}/tenant-kb-config",
        {"collectionConfigs": kb.get("collectionConfigs") or [],
         "dataSourceConfigs": kb.get("dataSourceConfigs") or []})
    if code != 200:
        return False, f"{msg}\n\nPUT failed (HTTP {code}): {str(out)[:300]}"
    cols = ", ".join(c.get("name", "?") for c in (kb.get("collectionConfigs") or []))
    nfiles = sum(len(c.get("files") or []) for c in (kb.get("collectionConfigs") or []))
    return True, (f"{msg}\n\nRestored the knowledge-base binding for {slug} from the {date} "
                  f"snapshot: {cols}.\n\n"
                  f"The config's embedded file list holds {nfiles} entr(ies). That is EXPECTED "
                  "to be fewer than the collection contains — it is a stale cache, and the "
                  "collection endpoint is authoritative. Retrieval is scoped to the "
                  "COLLECTION, so a short list here does not mean the agent has lost access to "
                  "anything. Do not treat it as a problem to fix.")


def bk_compare_file(collection, filename):
    """Live Foundry content vs the repo, plus when the hash last changed. Returns (info, err).

    Content is NOT in the snapshots - only hashes - so this compares live against the WORKING
    TREE, which is the practical question ("is what the agent reads what we think it reads?").
    The snapshot hashes then answer the second question: which day did it change.
    """
    folder = None
    for f, cols in FOLDER_COLLECTION.items():
        if collection in cols and (REPO / f / filename).is_file():
            folder = f
            break
    if folder is None:
        for f in list(FOLDER_COLLECTION):
            if (REPO / f / filename).is_file():
                folder = f
                break
    local = (REPO / folder / filename) if folder else None

    try:
        files = _foundry_get(
            f"/api/tenant-knowledge-base/collections/{collection}/files")
    except Exception as e:                                            # noqa: BLE001
        return None, f"could not list {collection}: {e}"
    rec = next((f for f in (files or []) if f.get("fileName") == filename), None)
    if rec is None:
        return None, f"{filename} is not in {collection}"

    import urllib.request
    base = os.environ.get("FOUNDRY_API_URL", "https://foundry.tylertechai.com").rstrip("/")
    req = urllib.request.Request(
        f"{base}/api/tenant-knowledge-base/collections/{collection}/files/{rec['id']}/download")
    req.add_header("X-API-Key", os.environ.get("FOUNDRY_API_KEY", ""))
    req.add_header("User-Agent", "claude-code-foundry-kb/1.0")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            remote = r.read()
    except Exception as e:                                            # noqa: BLE001
        return None, f"could not download {filename}: {e}"

    import hashlib
    info = {"collection": collection, "filename": filename, "folder": folder,
            "remote_bytes": len(remote), "remote_sha": hashlib.sha256(remote).hexdigest(),
            "local_bytes": None, "local_sha": None, "same": None, "diff": [], "hash_days": []}
    if local and local.is_file():
        lb = local.read_bytes()
        info["local_bytes"] = len(lb)
        info["local_sha"] = hashlib.sha256(lb).hexdigest()
        info["same"] = lb == remote
        if not info["same"]:
            import difflib
            info["diff"] = list(difflib.unified_diff(
                remote.decode("utf-8", "replace").splitlines(),
                lb.decode("utf-8", "replace").splitlines(),
                "foundry (live)", f"repo ({folder}/{filename})", n=2, lineterm=""))[:220]

    # Which day did the hash change? Reads the most recent snapshots' hashes files. Capped at
    # 10 because each is a `gh` call and the answer is almost always in the last few days.
    d, _ = backups()
    for date in (d or {}).get("dates", [])[:10]:
        txt, e2 = _bk_file(f"snapshots/{date}/collections/{collection}.hashes.json")
        if e2 or not txt:
            continue
        try:
            h = json.loads(txt).get(filename) or {}
        except json.JSONDecodeError:
            continue
        if h.get("sha256"):
            info["hash_days"].append((date, h["sha256"], h.get("bytes")))
    return info, None


def bk_drift_table(date):
    """Snapshot hash vs the local file, for every file in every collection. (rows, err).

    NO DOWNLOADS. The snapshot's hashes.json already holds the SHA-256 of what Foundry was
    serving when the snapshot was taken, so comparing it against the working tree's hash gives
    the whole drift picture from data already on disk. Downloading 43 files to render a page
    would make it too slow to look at, and this is the page people should be able to glance at.

    The trade is that it is as fresh as the snapshot, not as fresh as now - which is why each
    row links to a live comparison.
    """
    import hashlib
    rows = []
    for col, folder in BK_COLLECTION_FOLDER.items():
        txt, err = _bk_file(f"snapshots/{date}/collections/{col}.hashes.json")
        if err or not txt:
            continue
        try:
            hashes = json.loads(txt)
        except json.JSONDecodeError:
            continue
        for name, h in sorted(hashes.items()):
            local = REPO / folder / name
            if not local.is_file():
                local = REPO / "Knowledge-Shared" / name
            if local.is_file():
                lsha = hashlib.sha256(local.read_bytes()).hexdigest()
                same = lsha == h.get("sha256")
                rows.append((col, name, same, h.get("bytes"), local.stat().st_size))
            else:
                rows.append((col, name, None, h.get("bytes"), None))
    return rows, None


def bk_head():
    return ("<div style='display:flex;align-items:center;gap:12px;flex-wrap:wrap;"
            "margin-bottom:6px'>"
            "<h2 class=sec style='margin:0'>Backups</h2>"
            "<a href='/backups?refresh=1' style='margin-left:auto;text-decoration:none'>"
            "<button class=sec>&#8635; Refresh</button></a></div>")


def bk_compare_view(spec):
    """One file: live Foundry content against the working tree, with a diff.

    Compares against the WORKING TREE rather than a snapshot, because content is not in the
    snapshots - only hashes. That is the right comparison anyway: the practical question is "is
    what the agent reads what we think it reads?". The snapshot hashes then answer the second
    question, which day it changed.
    """
    col, _, name = spec.partition("/")
    if col not in BK_COLLECTION_FOLDER or not name:
        return page("Backups", "<div class=lg>" + bk_head()
                    + "<div class='bar bnr-done'>Not a file in a known collection.</div>"
                    "<p><a href='/backups'>Back to backups</a></p></div>", active="backups")
    info, err = bk_compare_file(col, name)
    if err:
        return page("Backups", "<div class=lg>" + bk_head()
                    + "<div class='bar bnr-done'>" + html.escape(err) + "</div>"
                    "<p><a href='/backups'>Back to backups</a></p></div>", active="backups")

    same = info["same"]
    if same:
        banner = ("<div class='bar bnr-ok'>Live Foundry content is <b>identical</b> to the "
                  "repo.</div>")
    elif same is False:
        banner = ("<div class='bar bnr-done'>Live Foundry content <b>differs</b> from the repo. "
                  "The repo is the source of truth, so the fix is a re-upload &mdash; "
                  "<code>python3 scripts/publish_to_foundry.py</code>, which refuses anything "
                  "not merged to main.</div>")
    else:
        banner = ("<div class='bar bnr-sug'>This file is in Foundry but has no counterpart in "
                  "the repo.</div>")

    rows = ["<tr><th>Where</th><th>Bytes</th><th>SHA-256</th></tr>",
            "<tr><td>Foundry (live)</td><td>" + format(info["remote_bytes"], ",") + "</td>"
            "<td><code>" + info["remote_sha"][:32] + "</code></td></tr>"]
    if info["local_sha"]:
        rows.append("<tr><td>Repo &mdash; <code>" + html.escape(info["folder"]) + "/</code></td>"
                    "<td>" + format(info["local_bytes"], ",") + "</td>"
                    "<td><code>" + info["local_sha"][:32] + "</code></td></tr>")

    body = [bk_head(),
            "<p class=sub><a href='/backups'>Backups</a> / compare / <b>"
            + html.escape(col) + "/" + html.escape(name) + "</b></p>",
            banner,
            "<div class=tblcard><table>" + "".join(rows) + "</table></div>"]

    if same is False and info["remote_bytes"] == info["local_bytes"]:
        body.append("<div class='bar bnr-sug'>Note the sizes are <b>equal</b>. This is exactly "
                    "the drift a size comparison cannot see, which is why the snapshots store "
                    "a hash per file.</div>")

    if info["diff"]:
        body.append("<h3 class=angroup>Difference</h3>"
                    "<p class=sub style='margin:0 0 8px'>Lines marked <code>-</code> are what "
                    "Foundry is serving; <code>+</code> is what the repo says.</p>"
                    "<pre class=out>")
        for line in info["diff"]:
            if line.startswith("@@"):
                cls = "dhunk"
            elif line.startswith(("---", "+++")):
                cls = "dmeta"
            elif line.startswith("-"):
                cls = "ddel"
            elif line.startswith("+"):
                cls = "dadd"
            else:
                cls = ""
            esc = html.escape(line)
            body.append("<span class=" + cls + ">" + esc + "</span>\n" if cls else esc + "\n")
        body.append("</pre>")

    if info["hash_days"]:
        body.append("<h3 class=angroup>Hash history</h3>"
                    "<p class=sub style='margin:0 0 8px'>What Foundry was serving on each "
                    "snapshot day. A change between consecutive rows is the day the content "
                    "moved.</p><div class=tblcard><table>"
                    "<tr><th>Snapshot</th><th>SHA-256</th><th>Bytes</th></tr>")
        prev = None
        for d, sha, nb in info["hash_days"]:
            mark = ""
            if prev is not None and prev != sha:
                mark = " <span class='pill warn'>changed</span>"
            body.append("<tr><td>" + html.escape(d) + mark + "</td><td><code>" + sha[:32]
                        + "</code></td><td>" + format(nb or 0, ",") + "</td></tr>")
            prev = sha
        body.append("</table></div>")
        if len(info["hash_days"]) == 1:
            body.append("<p class=sub>Only one snapshot exists so far, so there is no history "
                        "to compare against yet. This becomes useful once the nightly job has "
                        "run a few times.</p>")

    body.append("<div class='bar bnr-note'><b>Read-only, deliberately.</b> There is no restore "
                "button for file content: the repo already holds every version, so the correct "
                "fix is a re-upload from a MERGED commit &mdash; which "
                "<code>publish_to_foundry.py</code> enforces and a button here could not.</div>")
    return page("Backups", "<div class=lg>" + "".join(body) + "</div>", active="backups")


def bk_agent_view(slug, date):
    """One agent against one snapshot: field diff, a field picker, and the two write actions."""
    if slug not in BK_AGENT_ID:
        return page("Backups", "<div class=lg>" + bk_head()
                    + "<div class='bar bnr-done'>Unknown agent.</div>"
                    "<p><a href='/backups'>Back to backups</a></p></div>", active="backups")

    rows, err = bk_agent_field_diff(slug, date)
    body = [bk_head(),
            "<p class=sub><a href='/backups'>Backups</a> / "
            "<a href='/backups?browse=snapshots/" + html.escape(date) + "'>"
            + html.escape(date) + "</a> / <b>" + html.escape(slug) + "</b></p>"]
    if err:
        body.append("<div class='bar bnr-done'>" + html.escape(err) + "</div>")
        return page("Backups", "<div class=lg>" + "".join(body) + "</div>", active="backups")

    # ---- the safe write comes first ------------------------------------------------------
    body.append(
        "<h3 class=angroup>Restore the knowledge-base binding</h3>"
        "<p class=sub style='margin:0 0 10px'>Writes only <code>collectionConfigs</code> and "
        "<code>dataSourceConfigs</code>, through the endpoint dedicated to them, so it cannot "
        "disturb this agent's instructions, model, tools or guardrails. Measured "
        "content-idempotent. A restore point is taken first.</p>"
        "<button onclick=\"bkKb(this,'" + html.escape(slug) + "','" + html.escape(date)
        + "')\">Restore KB binding from " + html.escape(date) + "</button>"
        "<div class='bar bnr-note' style='margin-top:10px'>Order matters: a binding names "
        "specific files. If any no longer exist in the collection, re-upload the files first, "
        "or the agent ends up pointing at something that is not there.</div>")

    # ---- field-level revert -------------------------------------------------------------
    body.append("<h3 class=angroup>Roll back individual fields</h3>")
    if not rows:
        body.append("<div class='bar bnr-ok'>The live agent is <b>identical</b> to the "
                    + html.escape(date) + " snapshot. Nothing to roll back.</div>")
    else:
        body.append(
            "<p class=sub style='margin:0 0 10px'>" + str(len(rows)) + " field(s) differ. Tick "
            "only what you want reverted &mdash; the payload is built from the <b>live</b> "
            "agent with those fields swapped in, so nothing else moves. Restoring a whole "
            "snapshot would also undo every legitimate change made since it was taken, which "
            "looks surgical and is not.</p>"
            "<div class=tblcard><table>"
            "<tr><th style='width:1%'></th><th>Field</th><th>Live now</th>"
            "<th>Snapshot " + html.escape(date) + "</th></tr>")
        for field, live_v, snap_v in rows:
            lv = live_v if isinstance(live_v, str) else json.dumps(live_v)
            sv = snap_v if isinstance(snap_v, str) else json.dumps(snap_v)
            body.append(
                "<tr><td><input type=checkbox class=bkfield value=\"" + html.escape(field)
                + "\"></td><td><code>" + html.escape(field) + "</code></td>"
                "<td class=qcell><small>" + html.escape(lv[:220]) + "</small></td>"
                "<td class=qcell><small>" + html.escape(sv[:220]) + "</small></td></tr>")
        body.append("</table></div>"
                    "<p style='margin-top:12px'><button onclick=\"bkFields(this,'"
                    + html.escape(slug) + "','" + html.escape(date)
                    + "')\">Roll back the ticked field(s)</button></p>")

    body.append(
        "<div class='bar bnr-note'>Both actions take a native Foundry version first, and that "
        "version is the undo. Verified on this agent on 2026-08-28: create version &rarr; "
        "config PUT with one field changed &rarr; restore returned it <b>byte-for-byte "
        "identical</b>. <b>After any restore, ask the agent a question</b> &mdash; text landing "
        "in a field is not the same as behaviour being restored.</div>"
        "<pre class=out id=bkout style='display:none'></pre>")
    return page("Backups", "<div class=lg>" + "".join(body) + "</div>", active="backups")


def backups_page(force=False, browse="", compare="", agent="", date=""):
    """Read-only view of the config backup repo, and a file browser over the snapshots.

    Admins only. The snapshots contain agent instructions, tenant s3Key paths and per-file IDs
    that are direct DELETE handles - the same reasoning that keeps contributors off the backup
    repo itself keeps them off this page.
    """
    if not is_admin():
        return page("Backups",
                    "<div class=lg><h2 class=sec>Backups</h2>"
                    "<div class='bar bnr-note'>This is admin-only. The snapshots carry agent "
                    "instructions, tenant storage paths and per-file identifiers, so access "
                    "matches the backup repo itself &mdash; the "
                    "<code>onetyler-tcp-pm-admins</code> team.</div></div>",
                    active="backups")

    if compare:
        return bk_compare_view(compare)
    if agent:
        d0, _ = backups()
        return bk_agent_view(agent, date or ((d0 or {}).get("dates") or [""])[0])

    d, err = backups(force=force)
    head = bk_head()

    if err:
        return page("Backups", "<div class=lg>" + head
                    + f"<div class='bar bnr-done'>{html.escape(err)}</div></div>",
                    active="backups")

    # ---- file browser ---------------------------------------------------------------------
    if browse:
        if ".." in browse or not browse.startswith(BK_ROOTS):
            return page("Backups", "<div class=lg>" + head
                        + "<div class='bar bnr-done'>That path is outside the snapshots.</div>"
                        "<p><a href='/backups'>Back to backups</a></p></div>", active="backups")
        crumbs, acc = [], ""
        for part in browse.split("/"):
            acc = f"{acc}/{part}" if acc else part
            crumbs.append(f"<a href='/backups?browse={html.escape(acc)}'>{html.escape(part)}</a>")
        bar = ("<p class=sub><a href='/backups'>Backups</a> / " + " / ".join(crumbs) + "</p>")

        if browse.endswith(".json") or browse.endswith(".md") or browse.endswith("LAST_RUN"):
            txt, ferr = _bk_file(browse)
            if ferr:
                inner = f"<div class='bar bnr-done'>{html.escape(ferr)}</div>"
            else:
                inner = (f"<p class=sub>{len(txt.encode())} bytes &middot; read-only</p>"
                         f"<pre class=out>{html.escape(txt)}</pre>")
            return page("Backups", "<div class=lg>" + head + bar + inner + "</div>",
                        active="backups")

        rows, ferr = _bk_ls(browse)
        if ferr:
            return page("Backups", "<div class=lg>" + head + bar
                        + f"<div class='bar bnr-done'>{html.escape(ferr)}</div></div>",
                        active="backups")
        body = ["<div class=tblcard><table><tr><th>Name</th><th>Type</th>"
                "<th style='text-align:right'>Size</th></tr>"]
        for name, ty, size in sorted(rows, key=lambda r: (r[1] != "dir", r[0])):
            link = f"/backups?browse={html.escape(browse)}/{html.escape(name)}"
            icon = "&#128193;" if ty == "dir" else "&#128196;"
            sz = "" if ty == "dir" else f"{int(size):,} B"
            body.append(f"<tr><td>{icon} <a href=\"{link}\">{html.escape(name)}</a></td>"
                        f"<td>{ty}</td><td style='text-align:right'>{sz}</td></tr>")
        body.append("</table></div>")
        return page("Backups", "<div class=lg>" + head + bar + "".join(body) + "</div>",
                    active="backups")

    # ---- overview -------------------------------------------------------------------------
    def tile(label, value, tone="grey", why="", sub=""):
        tip = f" title=\"{html.escape(why)}\"" if why else ""
        s = (f"<div class=l style='color:var(--forge-theme-text-low)'>{sub}</div>"
             if sub else "")
        return (f"<div class='kpi t-{tone}'{tip}><div class=v>{value}</div>"
                f"<div class=l>{label}</div>{s}</div>")

    m = d["manifest"] or {}
    cap = m.get("captured", {})
    agents_n, cols_n = cap.get("agents", 0), cap.get("collections", 0)
    exp = m.get("expected", {})
    complete = (agents_n == exp.get("agents") and cols_n == exp.get("collections"))
    warn_n = len(m.get("warnings") or [])

    # Age of the newest snapshot, in days. The single most useful number on the page: a backup
    # that stopped three weeks ago looks identical to a working one in every other respect.
    stale_days, tone_age = None, "grey"
    if d["dates"]:
        try:
            # UTC, NOT local. Snapshot directories are named from the runner's UTC date, and
            # comparing them against a local date is wrong by a day for most of the working day
            # in the Americas. Measured: at 04:06 UTC this read "-1 day(s) old", which is both
            # impossible and the wrong direction - it would have made a stale backup look fresh
            # rather than the reverse.
            from datetime import datetime as _dtm, timezone as _tz
            today = _dtm.now(_tz.utc).date()
            stale_days = (today - _dtm.strptime(d["dates"][0], "%Y-%m-%d").date()).days
            stale_days = max(0, stale_days)
            tone_age = "green" if stale_days <= 1 else "yellow" if stale_days <= 3 else "red"
        except ValueError:
            pass

    last_run = next((r for r in d["runs"] if r.get("name") == "snapshot"), None)
    concl = (last_run or {}).get("conclusion") or (last_run or {}).get("status") or "unknown"

    body = [head,
            f"<p class=sub style='margin:0 0 22px'>Read-only view of "
            f"<code>{html.escape(d['repo'])}</code>. Nightly snapshots of the team router, the "
            "five agent configs and the collection file records. "
            "<b>There is no restore action here</b> &mdash; see below.</p>"]

    body.append("<h3 class=angroup>Freshness</h3><div class=kpis>"
                + tile("Newest snapshot",
                       html.escape(d["dates"][0]) if d["dates"] else "none", tone_age,
                       "The most recent snapshot in the repo. Anything older than a day or two "
                       "means the nightly job has stopped.",
                       ("today" if stale_days == 0 else
                        "1 day old" if stale_days == 1 else
                        f"{stale_days} days old") if stale_days is not None else "")
                + tile("Snapshots retained", len(d["dates"]), "grey",
                       "Live directories after retention: 14 daily, 8 weekly, 12 monthly, "
                       "yearly kept forever. Pruned days remain in git history.")
                + tile("Last job", html.escape(str(concl)),
                       "green" if concl == "success" else "red" if concl == "failure" else "yellow",
                       "Conclusion of the most recent `snapshot` workflow run.",
                       html.escape(((last_run or {}).get("createdAt") or "")[:16].replace("T", " ")))
                + tile("Mirror bundles", len(d["releases"]), "grey",
                       "Weekly full git bundles of the knowledge repo, kept as release assets. "
                       "Zero is expected until MAIN_REPO_READ_TOKEN is set.")
                + "</div>")

    body.append("<h3 class=angroup>What the newest snapshot captured</h3><div class=kpis>"
                + tile("Agent configs", f"{agents_n}/{exp.get('agents', 5)}",
                       "green" if complete else "red",
                       "The reason this backup exists: Foundry keeps NO version history for "
                       "agents, so a misedited agent config is recoverable from nowhere else.")
                + tile("Collections", f"{cols_n}/{exp.get('collections', 5)}",
                       "green" if complete else "red",
                       "File records - id, fileName, fileSize, s3Key, ingestion status.")
                + tile("Team restore points", m.get("team_native_versions", "?"), "grey",
                       "Foundry's own versions of the team router, which are the preferred "
                       "restore path for it.")
                + tile("Size", f"{m.get('bytes', 0):,} B", "grey",
                       "Uncompressed. A drop past 40% against the previous day fails the run "
                       "rather than committing a shrinking backup.")
                + tile("Warnings", warn_n, "grey" if not warn_n else "yellow",
                       "Recorded at capture time. High-entropy strings warn; an actual "
                       "credential fails the run outright.")
                + "</div>")

    if m.get("unchanged_from"):
        body.append(f"<div class='bar bnr-note'>The newest snapshot is identical to "
                    f"<b>{html.escape(str(m['unchanged_from']))}</b> &mdash; nothing in the "
                    "Foundry config changed. Quiet is the expected state.</div>")

    if d["last_run"]:
        body.append("<h3 class=angroup>Heartbeat</h3>"
                    "<p class=sub style='margin:0 0 8px'>Written on every run, including days "
                    "when nothing changed &mdash; so &ldquo;did it actually run?&rdquo; is "
                    "answerable without reading Actions history, which expires.</p>"
                    f"<pre class=out>{html.escape(d['last_run'])}</pre>")

    if d["changes"]:
        body.append("<h3 class=angroup>Config changes</h3>"
                    "<p class=sub style='margin:0 0 8px'>Appended only when a snapshot differs "
                    "from the one before it.</p><div class=tblcard><table>")
        for line in d["changes"]:
            body.append(f"<tr><td>{html.escape(line.lstrip('- '))}</td></tr>")
        body.append("</table></div>")

    if d["runs"]:
        body.append("<h3 class=angroup>Recent runs</h3><div class=tblcard><table>"
                    "<tr><th>Workflow</th><th>Trigger</th><th>When (UTC)</th>"
                    "<th>Result</th></tr>")
        for r in d["runs"]:
            c = r.get("conclusion") or r.get("status") or "?"
            cls = ("reviewed" if c == "success" else "bad" if c == "failure" else "pending")
            body.append(f"<tr><td>{html.escape(str(r.get('name')))}</td>"
                        f"<td>{html.escape(str(r.get('event') or ''))}</td>"
                        f"<td>{html.escape(str(r.get('createdAt') or '')[:16].replace('T', ' '))}</td>"
                        f"<td><span class='pill {cls}'>{html.escape(str(c))}</span></td></tr>")
        body.append("</table></div>")

    # ---- file drift, from hashes: no downloads --------------------------------------------
    if d["dates"]:
        drows, _ = bk_drift_table(d["dates"][0])
        bad = [r for r in drows if r[2] is False]
        orphan = [r for r in drows if r[2] is None]
        body.append("<h3 class=angroup>Files: Foundry vs the repo</h3>"
                    "<p class=sub style='margin:0 0 8px'>Every file in every collection, "
                    "compared by content hash. Uses the "
                    + html.escape(d["dates"][0]) + " snapshot's hashes against your working "
                    "tree, so it costs no downloads &mdash; click a row for a live comparison "
                    "and a diff.</p>")
        if not bad and not orphan:
            body.append("<div class='bar bnr-ok'>All " + str(len(drows)) + " files match the "
                        "repo exactly.</div>")
        else:
            body.append("<div class='bar bnr-done'><b>" + str(len(bad)) + " of "
                        + str(len(drows)) + "</b> file(s) differ from the repo"
                        + (", " + str(len(orphan)) + " not in the repo" if orphan else "")
                        + ". The repo is the source of truth, so the fix is a re-upload.</div>")
        body.append("<div class=tblcard><table><tr><th>Collection</th><th>File</th>"
                    "<th>Foundry</th><th>Repo</th><th></th></tr>")
        for col, name, same, rb, lb in (bad + orphan):
            body.append("<tr><td>" + html.escape(col) + "</td>"
                        "<td><a href='/backups?compare=" + html.escape(col) + "/"
                        + html.escape(name) + "'>" + html.escape(name) + "</a></td>"
                        "<td>" + (format(rb, ",") + " B" if rb else "?") + "</td>"
                        "<td>" + (format(lb, ",") + " B" if lb else "&mdash;") + "</td>"
                        "<td><span class='pill "
                        + ("bad'>differs" if same is False else "warn'>not in repo")
                        + "</span></td></tr>")
        body.append("</table></div>")
        if bad:
            body.append("<p class=sub>Equal byte counts with different content is the case a "
                        "size comparison cannot see &mdash; which is why these hashes exist.</p>")

    # ---- per-agent restore entry points ---------------------------------------------------
    if d["dates"]:
        newest = d["dates"][0]
        body.append("<h3 class=angroup>Agents</h3>"
                    "<p class=sub style='margin:0 0 8px'>Compare each agent's live config "
                    "against the " + html.escape(newest) + " snapshot, and roll back "
                    "individual fields or just its knowledge-base binding.</p>"
                    "<div class=tblcard><table><tr><th>Agent</th><th>Restore points</th>"
                    "<th></th></tr>")
        nav = (m.get("agent_native_versions") or {})
        for slug in sorted(BK_AGENT_ID):
            n_ver = nav.get(slug, "?")
            pill = ("<span class='pill reviewed'>" + str(n_ver) + "</span>" if n_ver
                    else "<span class='pill warn'>none yet</span>")
            body.append("<tr><td><code>" + html.escape(slug) + "</code></td>"
                        "<td>" + pill + "</td>"
                        "<td><a href='/backups?agent=" + html.escape(slug) + "&date="
                        + html.escape(newest) + "'>Compare &amp; restore &rarr;</a></td></tr>")
        body.append("</table></div>"
                    "<p class=sub>Restore points are Foundry's own agent versions, which are "
                    "the undo for any write here. Creating one is non-destructive.</p>")

    body.append("<h3 class=angroup>Browse the snapshots</h3>"
                "<p class=sub style='margin:0 0 8px'>Every file, read-only. Newest first.</p>"
                "<div class=tblcard><table><tr><th>Snapshot</th><th></th></tr>")
    for date in d["dates"][:20]:
        body.append(f"<tr><td>&#128193; <a href='/backups?browse=snapshots/{html.escape(date)}'>"
                    f"{html.escape(date)}</a></td><td class=sub>"
                    f"team &middot; 5 agents &middot; 5 collections</td></tr>")
    body.append("</table></div>")
    if len(d["dates"]) > 20:
        body.append(f"<p class=sub>{len(d['dates']) - 20} older snapshot(s) not listed. "
                    "Pruned days are still in git history.</p>")

    body.append(
        "<h3 class=angroup>What can and cannot be restored from here</h3>"
        "<div class=tblcard><table>"
        "<tr><th>Asset</th><th>From this page</th><th>Why</th></tr>"
        "<tr><td>An agent's <b>KB binding</b></td>"
        "<td><span class='pill reviewed'>yes</span></td>"
        "<td>Dedicated endpoint taking only the binding, measured content-idempotent. The "
        "safest write available.</td></tr>"
        "<tr><td>An agent's <b>individual fields</b></td>"
        "<td><span class='pill reviewed'>yes</span></td>"
        "<td>Payload built from the live agent with only the chosen fields swapped in, so "
        "nothing else moves. A native version is taken first.</td></tr>"
        "<tr><td><b>Knowledge file content</b></td>"
        "<td><span class='pill excluded'>compare only</span></td>"
        "<td>Git already holds every version, so the correct fix is a re-upload from a MERGED "
        "commit &mdash; which <code>publish_to_foundry.py</code> enforces and a button here "
        "could not.</td></tr>"
        "<tr><td><b>Team router</b></td>"
        "<td><span class='pill excluded'>no</span></td>"
        "<td>Foundry versions it natively, which is a better path. "
        "<code>scripts/restore.py</code> in the backup repo prints the exact calls.</td></tr>"
        "<tr><td><b>Collection file records</b></td>"
        "<td><span class='pill excluded'>no</span></td>"
        "<td>There is no write API for a file record at all &mdash; only upload and delete. The "
        "snapshot is descriptive: it tells you what should exist.</td></tr>"
        "</table></div>"
        "<div class='bar bnr-note'>Every write here takes a Foundry version first, and that "
        "version is the undo. The full round trip &mdash; version, config PUT, restore &mdash; "
        "was exercised on the SAC agent on 2026-08-28 and returned it byte-for-byte identical, "
        "so these are tested paths rather than hopeful ones.</div>")

    return page("Backups", "<div class=lg>" + "".join(body) + "</div>", active="backups")


def analytics_page(force=False):
    """OT Analytics — the OneTyler Cloud Living team's usage, mirroring Foundry's Analytics tab.

    Visible to everyone. It is read-only usage data about the team's own agent, with no verdicts
    and no permissions attached, so there is nothing here a contributor should be kept from -
    and knowing whether anyone is actually using the thing they review is part of the job.
    """
    data, err = ot_analytics(force=force)
    age = last_sync_age("analytics")

    head = ("<div style='display:flex;align-items:center;gap:12px;flex-wrap:wrap;"
            "margin-bottom:6px'>"
            "<h2 class=sec style='margin:0'>OT Analytics</h2>"
            "<a href='/analytics?refresh=1' style='margin-left:auto;text-decoration:none'>"
            "<button class=sec>&#8635; Refresh</button></a>"
            f"<span class=fresh id=freshness data-age='{age if age is not None else -1}' "
            "data-kind=analytics></span></div>"
            f"<p class=sub style='margin:0 0 22px'>Usage for the <b>{html.escape(TEAM_NAME)}</b> "
            "team agent. Recomputed from the transcripts API each refresh.</p>")

    if err:
        return page("OT Analytics",
                    "<div class=lg>" + head +
                    f"<div class='bar bnr-done'>{html.escape(err)}</div></div>",
                    active="analytics")

    d = data
    fb = d["feedback"]

    def tile(label, value, tone="grey", why="", sub=""):
        tip = f" title=\"{html.escape(why)}\"" if why else ""
        s = f"<div class=l style='color:var(--forge-theme-text-low)'>{sub}</div>" if sub else ""
        return (f"<div class='kpi t-{tone}'{tip}><div class=v>{value}</div>"
                f"<div class=l>{label}</div>{s}</div>")

    def group(title, tiles):
        return (f"<h3 class=angroup>{title}</h3><div class=kpis>" + "".join(tiles) + "</div>")

    body = [head]
    body.append(group("Questions", [
        tile("Total questions", d["questions"], "grey",
             "Every question asked of the team agent, all time."),
        tile("Average per day", d["q_per_day"], "grey",
             f"Across the {d['span_days']} days from {d['first_day']} to {d['last_day']}, "
             "including days with no activity."),
        tile("Peak-day questions", d["peak_q"], "yellow",
             "The busiest single day.", d["peak_q_day"]),
        tile("Active days", d["active_days"], "grey",
             f"Days with at least one conversation, out of {d['span_days']}."),
    ]))
    body.append(group("Conversations", [
        tile("Total conversations", d["conversations"], "grey",
             "Distinct conversations with the team agent."),
        tile("Average per day", d["c_per_day"], "grey",
             "Over the same span, including quiet days."),
        tile("Peak-day conversations", d["peak_c"], "yellow",
             "The busiest single day.", d["peak_c_day"]),
        tile("Questions per conversation", round(d["questions"] / d["conversations"], 1)
             if d["conversations"] else 0, "grey",
             "How many turns a typical conversation runs to."),
    ]))
    body.append(group("Feedback", [
        tile("Total feedback", fb["total"], "grey",
             "Conversations where someone rated the answer."),
        tile("Positive", fb["pos"], "green" if fb["pos"] else "grey", "Thumbs up."),
        tile("Negative", fb["neg"], "red" if fb["neg"] else "grey",
             "Thumbs down. These are the transcripts worth reading first."),
        tile("Rated", f"{round(100*fb['total']/d['conversations'])}%"
             if d["conversations"] else "0%", "grey",
             "Share of conversations carrying any rating. Expect this to be low; most people "
             "do not rate."),
    ]))

    rows = "".join(
        f"<tr><td class=swhen>{html.escape(day)}</td><td>{n}</td></tr>"
        for day, n in d["top_days"])
    srows = "".join(
        f"<tr><td class=swhen>{html.escape(s['date'])}</td>"
        f"<td><code>{html.escape(s['id'][:8])}</code></td>"
        f"<td><a href='/?all=1'>{s['messages']}</a></td></tr>"
        for s in d["top_sessions"])
    body.append(
        "<div class=antables>"
        "<div class=card><h3>Busiest days (Top 5)</h3>"
        "<p class=sub>Conversations per day.</p>"
        f"<table class=antab><tr><th>Date</th><th>Conversations</th></tr>{rows}</table></div>"
        "<div class=card><h3>Longest sessions (Top 5)</h3>"
        "<p class=sub>Most exchanges in one conversation.</p>"
        f"<table class=antab><tr><th>Date</th><th>Conversation</th><th>Exchanges</th></tr>"
        f"{srows}</table></div></div>")

    if d["detail_missing"]:
        body.append(f"<div class=hint style='margin-top:14px'>{d['detail_missing']} "
                    "conversation(s) could not be fetched, so the question counts are a "
                    "floor rather than a total.</div>")
    return page("OT Analytics", "<div class=lg>" + "".join(body) + "</div>", active="analytics")


def git_page():
    """Send a finished batch of reviews in.

    Rewritten as a numbered sequence after a reviewer said plainly they did not understand it.
    The old version was four same-looking buttons with git vocabulary on them - "Create
    branch", "Stage & commit", "Push & open PR" - which assumes you already know what those
    do and in what order. It now reads as three steps, says what each will do BEFORE you
    click, shows what is about to be sent, and disables steps that are not applicable yet.
    """
    frag = git_fragments()
    state, files, saves_html = frag["state"], frag["files"], frag["saves"]

    fdry = pending_foundry_uploads()
    n_ai = awaiting_analysis()
    if n_ai:
        # A stage with its own state, `ai`, because it is neither waiting on this button nor
        # something the page can do. The prompt is a copy button rather than text to retype:
        # the words matter (read all the feedback as one body, ask rather than guess) and
        # nobody should have to remember them.
        ai_stage = (
            "<li data-stage=ai class='wait ai'><b>Update the knowledge files</b>"
            f"<span><b>{n_ai}</b> reviewed transcript(s) are waiting on this. It needs an AI "
            "assistant — it is judgement and writing, not a command: which file, where in it, "
            "and worded so the retriever finds it.<br>"
            "<button type=button class=sec id=aiprompt onclick='copyPrompt(this)' "
            "style='margin-top:8px'>Copy the prompt for my assistant</button>"
            "</span></li>")
    else:
        ai_stage = (
            "<li data-stage=ai class=none><b>Update the knowledge files</b>"
            "<span>nothing to update — no review in this batch asked for a change</span></li>")

    prompt_json = json.dumps(analysis_prompt(n_ai))

    def step(num, title, desc, inner):
        return (f"<div class=step><div class=stepnum>{num}</div><div class=stepbody>"
                f"<h4>{title}</h4><p class=sub>{desc}</p>{inner}</div></div>")

    body = (
      f"<h2 class=sec>Save &amp; Share Your Reviews</h2>"
      # NO BRANCH NAME HERE, deliberately. This line used to read "You are working on
      # feature/owner-highlighting", which is git vocabulary a reviewer has no use for and
      # cannot act on. The branch is handled entirely server-side now - see ensure_lane().
      f"<div class=bar id=gitstate>{state}</div>"

      "<div class=card>"
      "<h3>Publish your reviews</h3>"
      # The honest division of labour, stated at the top because it is the thing people get
      # wrong about this repo: a verdict is not the deliverable. The knowledge file that stops
      # the agent repeating that answer is, and writing it is the ONE job here that needs an
      # assistant. Everything else on this page is a button.
      "<p class=sub>Parts 1 and 2 are yours. Part 3 needs an assistant for one step — "
      "updating the knowledge files — and buttons for the rest.</p>"
      "<div class=whatsent><b>About to be sent</b><div id=gitfiles>" + files + "</div></div>"
      + step("1", "Part 1 — Save progress (recommended)",
             "A checkpoint on this machine (local git commit) you can go back to. "
             "Optional in the strict sense — Part 2 saves first anyway. Nothing is shared yet; if the laptop died "
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
             "</div>" + "<div id=githist>" + saves_html + "</div>")
      + step("2", "Part 2 — Publish",
             "Your verdicts are not the deliverable — the knowledge files that stop the agents "
             "repeating those answers are. Updating them is the one step here that needs an "
             "assistant; the rest is this button and a merge.",
             "<ol class=prog id=prog>"
             + ai_stage +
             "<li data-stage=push class=wait><b>Upload to GitHub</b>"
             "<span>your work and the knowledge updates together, kept apart from everyone "
             "else's until they are checked (git push of your own branch)</span></li>"
             "<li data-stage=pr class=wait><b>Create the change request</b>"
             "<span>someone checks it before it becomes official (a GitHub pull "
             "request)</span></li>"
             + "</ol>"
             "<div class=stepacts>"
             f"<button onclick='sendReviews(this)' data-ai-pending='{n_ai}'>"
             "Send my reviews in</button></div>"
             # Part 2 ENDS here. Merging and the Foundry upload are decisions ABOUT a request
             # that already exists, not steps in submitting one, and they live on the PRs tab
             # where the request can be seen next to its checks. Listing them here as
             # greyed-out stages implied this button was somehow responsible for them.
             + ("<div class=handoff>What happens next is on <a href='/prs'><b>PRs</b></a>: "
                "approving, merging, and the Foundry upload if knowledge files changed."
                if is_admin() else
                "<div class=handoff>An admin approves and merges it from there. Once it is "
                "sent, you are done.")
             + "</div>")
      + "</div>"
      f"<script>window.AI_PROMPT={prompt_json};</script>"

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
      "<li>Only Part 2 shares anything.</li>"
      "</ul></details>"

      # NOT a numbered Part, and last on the page. It is an EXCEPTION to the workflow, not a
      # stage of it - numbering it first implied you were meant to pass through it every time,
      # and made the first thing on the publish page a way to throw work away.
      "<div class='card dangerzone'>"
      "<h3>Something went wrong?</h3>"
      "<p class=sub>Not part of the normal flow — only for undoing.</p>"
      "<div class=dzrow><div>"
      "<b>Reset unsaved edits</b>"
      "<div class=sub>Puts edited transcripts back to their last saved state. Only touches "
      "edits you have not saved; anything already saved is untouched, and newly synced "
      "conversations are left alone. Undoable — the edits are set aside rather than deleted, "
      "and the output tells you how to put them back.</div>"
      "</div><div class=dzact>"
      "<button class=sec onclick='resetUnsaved(this)'>Reset unsaved edits</button>"
      "</div></div></div>")
    return page("Save & Share", "<div class=lg>" + body + "</div>", active="git")


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
        if self.path == "/analytics" or self.path.startswith("/analytics?"):
            # No admin gate: it is read-only usage data about the team's own agent, with no
            # verdicts and no permissions attached.
            return self._send(200, analytics_page(force="refresh=1" in self.path))
        if self.path == "/backups" or self.path.startswith("/backups?"):
            # `unquote` is what this file already imports; parse_qs would need a second import
            # for one parameter. The gate on `browse` is in backups_page(), not here, so there
            # is exactly one place that decides what a path is allowed to be.
            qs = self.path.split("?", 1)[1] if "?" in self.path else ""
            q = {}
            for kv in qs.split("&"):
                k, _, v = kv.partition("=")
                if k:
                    q[k] = unquote(v)
            return self._send(200, backups_page(
                force="refresh=1" in self.path,
                browse=q.get("browse", "").strip(),
                compare=q.get("compare", "").strip(),
                agent=q.get("agent", "").strip(),
                date=q.get("date", "").strip()))
        if self.path == "/prs" or self.path.startswith("/prs?"):
            # Same gate as All Transcripts, and for the same reason: a contributor cannot
            # merge, so every button here would refuse. Not a security boundary - the page
            # only shows what `gh` would tell them anyway.
            if not is_admin():
                return self._send(200, page("Change Requests",
                    "<div class=card><h3>Admins only</h3><p class=sub>Merging is an admin "
                    "action. Send your reviews in from <b>Save &amp; Share</b> and an admin "
                    "will merge them.</p></div>", active="git"))
            return self._send(200, pr_page(force="refresh=1" in self.path))
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
                # FIRST bring the local copy in line with the shared one, THEN ask Foundry for
                # new conversations. Order matters: a transcript merged by someone else - or by
                # you in the browser, which this server never sees - is stale on disk until
                # this runs, and a reviewed transcript that reads as `pending` looks like a
                # lost verdict rather than a stale file.
                #
                # This is why it lives in the SYNC and not only after the merge button. A merge
                # can happen anywhere: GitHub's own UI, another contributor's machine, a
                # different clone. Hooking only our own button would cover the one case we
                # already control and miss every other. Fast-forward only, so it can never
                # move or discard work in progress.
                # Return value ignored: every outcome it can report - fetch failure, declined
                # because of unsaved edits - already says so in the message, which is shown.
                _, pulled_msg = pull_main()

                if not os.environ.get("FOUNDRY_API_KEY"):
                    raise ValueError("FOUNDRY_API_KEY is not set in the environment this "
                                     "server was started from — start it from a shell where "
                                     "the key is available, then try again")
                r = subprocess.run([sys.executable, str(REPO / "scripts" / "fetch_transcripts.py")],
                                   cwd=REPO, capture_output=True, text=True, timeout=600)
                out = (r.stdout or "") + (r.stderr or "")
                # The line is "added: 2 new | untouched (already present): 56 | ...", so take
                # the first integer after the label - not the whole field, which is "2 new".
                added = updated = 0
                m = re.search(r"^added:\s*(\d+)", out, re.M)
                if m:
                    added = int(m.group(1))
                # A sync can change nothing, add files, OR correct the Foundry-owned fields on
                # files we already had - a thumbs-down arriving on something already reviewed
                # is the case that matters, and it adds no files at all.
                mu = re.search(r"\|\s*updated:\s*(\d+)", out)
                if mu:
                    updated = int(mu.group(1))
                refresh_index()
                if r.returncode == 0:
                    note_sync()
                # `ok` reports the Foundry sync only. The pull is best-effort by design -
                # it declines while there are unsaved edits, which is the normal mid-review
                # state, and that must not read as a failed sync.
                return self._send(200, json.dumps({"ok": r.returncode == 0,
                                                   "added": added,
                                                   "updated": updated,
                                                   "pulled": pulled_msg,
                                                   "output": ((pulled_msg + "\n\n")
                                                              if pulled_msg else "")
                                                             + out[-4000:],
                                                   "age": last_sync_age()}),
                                  "application/json")
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
                # The disabled checkbox in the UI is advice; this is the rule. A transcript
                # already inside an unmerged change request must not be re-stamped here - the
                # verdict in that request is the real one, and stamping a duplicate guarantees
                # a conflict when it merges.
                tpr = transcript_pr_map()
                for rel in rels:
                    f = (TDIR / rel).resolve()
                    if not str(f).startswith(str(TDIR.resolve())) or not f.is_file():
                        skipped.append((rel, "not found")); continue
                    if rel in tpr:
                        skipped.append((rel, f"already inside change request "
                                             f"#{tpr[rel]['number']} — open that instead"))
                        continue
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
        if self.path == "/bk":
            # THE ONLY WRITE-TO-PRODUCTION ENDPOINT IN THIS APP. Admin-gated here as well as in
            # the page, because a page-level check protects the button and not the endpoint.
            if not is_admin():
                return self._send(200, json.dumps(
                    {"ok": False, "output": "Restoring is an admin action."}),
                    "application/json")
            act = (data.get("action") or "").strip()
            slug = (data.get("slug") or "").strip()
            when = (data.get("date") or "").strip()
            try:
                if act == "kb":
                    ok, out = bk_restore_kb(slug, when)
                elif act == "fields":
                    fields = [str(f) for f in (data.get("fields") or []) if f]
                    ok, out = bk_restore_fields(slug, when, fields)
                else:
                    ok, out = False, "unknown action"
            except Exception as e:                                    # noqa: BLE001
                ok, out = False, f"{type(e).__name__}: {e}"
            return self._send(200, json.dumps({"ok": ok, "output": out}),
                              "application/json")
        if self.path == "/pr":
            if not is_admin():
                return self._send(200, json.dumps(
                    {"ok": False, "output": "Merging is an admin action."}),
                    "application/json")
            act = (data.get("action") or "").strip()
            num = str(data.get("number") or "").strip()
            if not num.isdigit():
                return self._send(200, json.dumps(
                    {"ok": False, "output": "no change request number"}),
                    "application/json")
            try:
                if act == "approve":
                    rc, out = gh("pr", "review", num, "--approve")
                elif act == "ready":
                    rc, out = gh("pr", "ready", num)
                elif act == "update":
                    # This repo sets required_status_checks.strict, so a branch behind main
                    # cannot merge until it is updated. `gh pr update-branch --rebase` keeps
                    # the linear history the rest of the flow assumes; a merge commit here
                    # would put a "Merge branch main into..." commit in a review batch.
                    rc, out = gh("pr", "update-branch", num, "--rebase")
                    if rc == 0:
                        out += ("\n\nUpdated. Checks will re-run — merge once they are green.")
                elif act in ("merge", "merge-override"):
                    # Rebase, matching how this repo has been merged throughout - a merge
                    # commit per review batch would bury the actual content in the history.
                    # merge_pr() brings the branch up to date first if GitHub refuses for that
                    # reason, so being behind main is not something to click through by hand.
                    override = act == "merge-override"
                    rc, out, updated = merge_pr(num, override)
                    if rc == 0:
                        head = ("Merged WITH the review gate bypassed (admin override).\n\n"
                                if override else "Merged.\n\n")
                        # Merging only moved the REMOTE. Without this the app is stale because
                        # of its own action, and merged transcripts come back as pending.
                        okp, msgp = pull_main()
                        refresh_index()
                        out = head + out + (("\n\n" + msgp) if msgp else "") + (
                            "\n\nOne thing follows:\n"
                            "  python3 scripts/check_foundry_drift.py   "
                            "(main is now ahead of the live agents)\n"
                            "  python3 scripts/publish_to_foundry.py    "
                            "(only if knowledge files changed)")
                    elif not override and _needs_override(out):
                        out += ("\n\nGitHub refused because the required approval is missing. "
                                "You can merge it anyway as an admin — that BYPASSES the review "
                                "gate, so only do it on your own work:\n"
                                "  press Merge anyway on your own change request")
                    elif updated:
                        out += ("\n\nThe branch WAS brought up to date, so that part is done "
                                "— the refusal above is a different reason. Required checks "
                                "re-run after a rebase, so if they are still queued, give them "
                                "a moment and try again.")
                else:
                    rc, out = 1, "unknown action"
            except Exception as e:                                    # noqa: BLE001
                rc, out = 1, str(e)
            return self._send(200, json.dumps(
                {"ok": rc == 0, "output": out or "(no output)"}), "application/json")
        if self.path == "/git":
            act = data.get("action")
            # Blank is the normal case, so it resolves to the generated label rather than
            # to a generic one - "Review transcripts" as a change-request title told a
            # reviewer nothing about whose it was or when.
            msg = (data.get("message") or "").strip() or auto_commit_message()
            try:
                if act == "commit":
                    rc, out = save_reviews(msg)
                elif act == "reset":
                    rc, out = reset_unsaved()
                elif act == "discard":
                    rc, out = discard_saves((data.get("hash") or "").strip())
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
                     "html": diff_html(out),
                     # The page's live parts, rebuilt AFTER the action - the file list, the
                     # status line and the progress history all go stale the instant you save,
                     # and reloading to fix that would discard the output above.
                     "refresh": git_fragments()}),
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
