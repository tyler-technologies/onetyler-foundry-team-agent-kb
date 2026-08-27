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
*{box-sizing:border-box}body{margin:0;font:14px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
color:#1a1d21;background:#f5f6f8}
a{color:#1c5fbf}header{background:#16203a;color:#fff;padding:12px 20px;display:flex;gap:18px;align-items:center;
position:sticky;top:0;z-index:10}header b{font-size:15px}header a{color:#9fc4ff;text-decoration:none}
.wrap{max-width:1180px;margin:0 auto;padding:20px}
.bar{background:#fff;border:1px solid #dfe3e8;border-radius:8px;padding:12px 16px;margin-bottom:16px}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #dfe3e8;border-radius:8px;overflow:hidden}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid #eef1f4;font-size:13px;white-space:nowrap}
th{background:#f0f2f5;font-weight:600}tr:hover td{background:#fafbfc}
.pill{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;font-weight:600}
.pending{background:#fff3d6;color:#8a5a00}.reviewed{background:#dcf5e4;color:#0f6b34}
.excluded{background:#e8e9ec;color:#5b6470}
.pushed{background:#dde8f7;color:#1c4f8f}
.suggested{background:#ede4fb;color:#5b3ba8}
.bad{background:#fde4e4;color:#a11}.warn{background:#ffeccc;color:#8a4b00}
.card{background:#fff;border:1px solid #dfe3e8;border-radius:8px;padding:16px;margin-bottom:14px}
.q{background:#eef4ff;border-left:3px solid #2b6cb0;padding:10px 12px;border-radius:4px;white-space:pre-wrap}
.a{background:#fafbfc;border:1px solid #e8ebef;border-radius:4px;padding:10px 12px;max-height:340px;
overflow:auto;white-space:pre-wrap;font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}
.tools{font-size:12px;color:#5b6470;margin:6px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:12px}
label{display:block;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.03em;color:#4a5260;margin-bottom:3px}
.hint{font-size:11px;color:#6b7280;font-weight:400;text-transform:none;letter-spacing:0}
select,input,textarea{width:100%;padding:6px 8px;border:1px solid #cbd2da;border-radius:5px;font-size:13px;
font-family:inherit;background:#fff}
textarea{min-height:88px;resize:vertical}
button{background:#1c5fbf;color:#fff;border:0;padding:8px 16px;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer}
button:hover{background:#174b98}button.sec{background:#e6e9ee;color:#26303d}button.sec:hover{background:#d7dce3}
.toast{position:fixed;bottom:18px;right:18px;background:#0f6b34;color:#fff;padding:10px 16px;border-radius:6px;
opacity:0;transition:.25s;z-index:50}.toast.on{opacity:1}
.nav{display:flex;justify-content:space-between;margin:16px 0}
td.qcell{white-space:normal;max-width:430px;min-width:300px}
tr.filters th{background:#e9edf2;padding:5px 6px;font-weight:400}
tr.filters input,tr.filters select{width:100%;padding:4px 6px;font-size:12px;border:1px solid #c3cbd5;border-radius:4px;background:#fff}
tr.filters small{color:#6b7280;font-weight:400}
#fbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
#fbar input[type=date]{width:auto;padding:4px 6px;font-size:12px;border:1px solid #c3cbd5;border-radius:4px}
td.nowrap,th.nowrap{white-space:nowrap}
tr.row[data-status=excluded] td{opacity:.5}
/* Two strengths of "this row is yours", deliberately different. Awaiting-you is a personal
   hand-off and gets the strong treatment; your-area is ambient and must not shout, or a
   contributor who owns four agents sees a wall of colour and stops noticing any of it. */
tr.row.mine-area td{background:#fbfdff}
tr.row.mine-area td:first-child{box-shadow:inset 3px 0 0 #9dc0e8}
tr.row.mine-awaiting td{background:#fff8e6}
tr.row.mine-awaiting td:first-child{box-shadow:inset 3px 0 0 #e0a92b}
tr.row.mine-awaiting:hover td{background:#fff3d6}
.pill.mineflag{background:#e0a92b;color:#fff;margin-left:5px}
tr.row.mine-area .pill.mineflag{background:#9dc0e8;color:#14385e}
span.owner{color:#8b95a3;font-size:12px}
.deleg{font-size:11px;color:#7a5cbf;font-weight:600}
pre.out{background:#10151f;color:#d6dde8;padding:10px;border-radius:6px;font-size:12px;overflow:auto;max-height:240px}
/* Field help. .fld is the positioning context so the panel OVERLAYS rather than reflowing
   the grid — otherwise opening one help panel shoves every other field down the page. */
.fld{position:relative}
button.info{background:#dbe4f0;color:#1c4f8f;border:0;border-radius:50%;width:15px;height:15px;
padding:0;margin-left:5px;font:700 10px/15px Georgia,serif;cursor:pointer;vertical-align:middle;
text-transform:none;letter-spacing:0}
button.info:hover{background:#1c5fbf;color:#fff}
.tip{position:absolute;z-index:40;top:100%;left:0;width:340px;max-width:78vw;background:#fff;
border:1px solid #b9c3d0;border-radius:8px;box-shadow:0 6px 22px rgba(16,21,31,.18);
padding:11px 13px;font-size:12px;font-weight:400;text-transform:none;letter-spacing:0;color:#1a1d21}
.tip[hidden]{display:none}
.tip b{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:#4a5260}
.tip p{margin:6px 0 8px}
.flow{margin:7px 0 0;padding:5px 7px;background:#f4f6f9;border-radius:4px;
font:11px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;color:#3d4655;white-space:nowrap;
overflow:auto}
table.dvt{border:0;border-radius:0;margin:0 0 8px}
table.dvt td{border-bottom:1px solid #f0f2f5;padding:3px 6px 3px 0;font-size:12px;
white-space:normal;vertical-align:top}
td.dv{white-space:nowrap;width:1%}
td.dv code{background:#eef1f5;padding:1px 5px;border-radius:3px;font-size:11px}
button.tipclose{padding:3px 10px;font-size:11px}
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
try{sessionStorage.setItem('tfilters',JSON.stringify(f))}catch(e){}}
function clearFilters(){['f_q','dfrom','dto'].forEach(i=>{const e=document.getElementById(i);if(e)e.value=''});
FKEYS.forEach(k=>{const e=document.getElementById('f_'+k);if(e)e.value=''});
applyFilters()}
function initFilters(){let saved=null;
try{saved=JSON.parse(sessionStorage.getItem('tfilters'))}catch(e){}
const set=(id,v)=>{const e=document.getElementById(id); if(e&&v) e.value=v};
if(saved){set('f_q',saved.q);set('dfrom',saved.dfrom);set('dto',saved.dto);
 FKEYS.forEach(k=>set('f_'+k,saved[k]));}
else{set('f_status','__open__');}  // default view: everything still open (pending + suggested)
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


def page(title, inner):
    return f"""<!doctype html><meta charset=utf-8><title>{html.escape(title)}</title>
<style>{CSS}</style><header><b>Transcript Review</b>
<a href="/">All transcripts</a><a href="/git">Git &amp; PR</a>
<span style="margin-left:auto;font-size:12px;opacity:.7">{html.escape(str(REPO.name))}</span></header>
<div class=wrap>{inner}</div><div class=toast id=toast></div><script>{JS}</script>"""


def list_page():
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
        })
    by_agent, default_owner = agent_owners()
    for r in recs:
        owners = by_agent.get(r["agent"], {default_owner} if default_owner else set())
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
            "<tr class='row"
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
            f" data-mine=\"{'awaiting' if r['mine_awaiting'] else ('area' if r['mine_area'] else '')}\">"
            f"<td class=qcell title=\"{html.escape(r['qfull'])}\">"
            f"<a href='/t/{html.escape(r['rel'])}'>{html.escape(r['q'])}</a></td>"
            f"<td>{html.escape(r['agent'])}"
            f"{'<div class=deleg>&rarr; '+html.escape(r['deleg'])+'</div>' if r['deleg'] else ''}</td>"
            f"<td class=nowrap>{html.escape(r['date'])}</td>"
            f"<td>{html.escape(r['ex'])}</td>"
            f"<td>{'<span class=\'pill warn\'>'+html.escape(r['fb'])+'</span>' if r['fb'] not in ('none','') else ''}</td>"
            f"<td><span class='pill {r['status']}'>{html.escape(r['status'])}</span>"
            f"{'<div class=deleg>'+html.escape(r['suggested_by'])+' &rarr; '+html.escape(r['awaiting'] or 'anyone')+'</div>' if r['status']=='suggested' else ''}</td>"
            f"<td class=nowrap>{awaiting_cell(r)}</td>"
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
    wholine = ""
    if ME:
        wholine = (f"<div class=bar style='background:#fff8e6;border-color:#e8d3a8'>"
                   f"You are <b>{html.escape(ME)}</b>."
                   + (f" <b>{mine_a}</b> transcript(s) awaiting you." if mine_a else "")
                   + (f" <b>{mine_r}</b> open in your area." if mine_r else "")
                   + ("" if (mine_a or mine_r) else " Nothing open is yours right now.")
                   + " Highlighted rows are yours — amber means handed to you, blue means your "
                     "area. Ownership is in <code>agent-owners.json</code>.</div>")
    bar = (wholine + f"<div class=bar><b>{done} / {scope} in-scope reviewed</b> ({pct}%)"
           f" &nbsp;·&nbsp; {counts['pending']} pending"
           + (f" &nbsp;·&nbsp; <span class='pill suggested'>{counts['suggested']} suggested"
              f"</span>" if counts["suggested"] else "")
           + f" &nbsp;·&nbsp; {excl} excluded (pre-go-live)"
           f" &nbsp;·&nbsp; {tot} total"
           f" &nbsp;·&nbsp; <a href='/git'>commit &amp; open a PR &rarr;</a></div>"
           "<div class=bar id=fbar>Showing <b id=shown>0</b> of "
           f"<b>{tot}</b> &nbsp;·&nbsp; date "
           "<input type=date id=dfrom> to <input type=date id=dto>"
           " &nbsp;<label style='display:inline;font-size:12px;text-transform:none;letter-spacing:0;font-weight:400'><input type=checkbox id=f_mine style='width:auto;margin-right:4px'>mine only</label>"" &nbsp;<button class=sec onclick='clearFilters()'>Clear all</button></div>")

    filt = ("<tr class=filters>"
            "<th><input id=f_q placeholder='search question / filename'></th>"
            f"<th><select id=f_agent>{opts('agent')}</select></th>"
            "<th class=nowrap><small>use date range above</small></th>"
            f"<th><select id=f_ex>{opts('ex')}</select></th>"
            f"<th><select id=f_fb>{opts('fb')}</select></th>"
            f"<th><select id=f_status><option value='__open__'>open (pending+suggested)"
            f"</option>{opts('status')}</select></th>"
            f"<th><select id=f_awaiting>{opts('awaiting')}</select></th>"
            f"<th><select id=f_routing>{opts('routing')}</select></th>"
            f"<th><select id=f_answer>{opts('answer')}</select></th>"
            f"<th><select id=f_diag>{opts('diag')}</select></th>"
            f"<th><select id=f_fix>{opts('fix')}</select></th></tr>")

    return page("Transcripts", bar
                + "<table id=tbl><tr><th>First question<th>Handled by<th>Date<th>Ex"
                  "<th>Foundry FB<th>Status<th>Awaiting<th>Routing<th>Answer<th>Diagnosis<th>Fix target</tr>"
                + filt + "".join(rows) + "</table>")


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
    _, branch = git("rev-parse", "--abbrev-ref", "HEAD")
    _, st = git("status", "--porcelain", "--", "transcripts")
    changed = [l for l in st.splitlines() if l.strip()]
    body = (f"<div class=bar>Branch: <b>{html.escape(branch)}</b> · "
            f"{len(changed)} changed file(s) under transcripts/</div>"
            "<div class=card><label>New branch name</label>"
            f"<input id=branch value='review/{branch if branch.startswith('review/') else 'batch'}'>"
            "<label style='margin-top:10px'>Commit message</label>"
            "<input id=cmsg value='Review transcripts: verdicts and proposed fixes'>"
            "<div style='margin-top:12px;display:flex;gap:8px;flex-wrap:wrap'>"
            "<button class=sec onclick=\"gitDo('branch')\">Create branch</button>"
            "<button class=sec onclick=\"gitDo('commit')\">Stage &amp; commit transcripts/</button>"
            "<button onclick=\"gitDo('pr')\">Push &amp; open PR</button>"
            "<button class=sec onclick=\"gitDo('diff')\">Show diff</button></div></div>"
            "<div class=card><b>Output</b><pre class=out id=gitout>"
            + html.escape("\n".join(changed) or "(no changes under transcripts/)")
            + "</pre></div>"
            "<div class=card><small>Reviews are committed even when no knowledge file changes — "
            "a verdict of <code>fix_target: agent-instructions</code> with no <code>kb_files</code> "
            "is a complete, mergeable contribution. The same applies to a "
            "<code>review_status: suggested</code> handoff: commit and PR it so the area owner "
            "picks it up on their next pull.</small></div>")
    return page("Git & PR", body)


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
        if self.path == "/":
            return self._send(200, list_page())
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
