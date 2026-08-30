#!/usr/bin/env python3
"""
Local transcript review UI for the OneTyler Cloud Living knowledge repo.

Serves a browser interface on http://127.0.0.1:7777 for reading collected
transcripts, recording verdicts and ideal responses, and writing them straight back
into the repo's markdown files so the result is an ordinary reviewable diff.

Stdlib only — no pip install, no build step. Binds to loopback only.

    python3 scripts/review_server.py
    python3 scripts/review_server.py --port 7778 --no-browser

Everything it writes lands in transcripts/*.md. Commit and open a PR as normal,
or use the Git panel in the UI.
"""
import argparse, csv, html, io, json, os, re, shutil, subprocess, sys, time, webbrowser
from collections import Counter
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from golive import GO_LIVE, EXCLUDE_NOTE, is_pre_go_live
from reviewtext import has_feedback, needs_triage, PLACEHOLDERS
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


def _foundry_raw(path, timeout=90):
    """GET raw bytes from Foundry. For file downloads, where the body is markdown, not JSON, and
    where the exact bytes are the point - a hash over a re-encoded string would not match."""
    import urllib.request
    base = os.environ.get("FOUNDRY_API_URL", "https://foundry.tylertechai.com").rstrip("/")
    req = urllib.request.Request(base + path)
    req.add_header("X-API-Key", os.environ.get("FOUNDRY_API_KEY", ""))
    req.add_header("User-Agent", "claude-code-foundry-kb/1.0")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


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


def owners_of_agent(slug):
    """Everyone who owns this agent's corpus, or an empty set if the slug is not an agent.

    Lets a routing field name an AGENT rather than a person. That is usually the answer a
    reviewer has - you know it is a SAC problem long before you know who owns SAC - and it
    survives ownership changing hands, which a hard-coded username does not.

    "team" is not a corpus, so it resolves to the admins: a routing-level problem belongs to
    whoever owns routing.
    """
    by, default = agent_owners()
    if slug == "team":
        return set(admins())
    if slug in by:
        return set(by[slug])
    # Not named in by_agent, but still a real agent - so it falls to the default owner. The
    # slug set comes from BK_AGENT_ID, which is the same list gen_codeowners.py uses, so one
    # name means one thing across the repo.
    if slug in BK_AGENT_ID:
        return {default} if default else set()
    return set()


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


# ---------------------------------------------------------------------------------------------
# Tyler Forge icons.
#
# Generated by scripts/gen_icons.py from the forge-icons repo - DO NOT HAND-EDIT the path
# data. Regenerate if an icon needs changing, so the source of truth stays the icon set.
#
# WHY THE PATHS ARE INLINE rather than served as files. This is a single-file app that runs
# from memory on loopback; adding a static-file route plus fifteen files to fetch would be
# more machinery than the 2.2 KB of path data it replaces. Inline SVG also inherits
# currentColor, which is what lets one icon work in both display modes and take a per-item
# tint - see nav.side .ic below.
#
# THESE REPLACED EMOJI, and the swap is not purely cosmetic. Emoji render from a font, so
# they differed per platform - the same nav looked different on macOS and Windows - they
# could not be tinted, and they carried their own baked-in colour that fought the theme.
FORGE_ICONS = {
    # My Transcripts - the queue flagged as yours (was U+1F6A9)
    'flag': ("M14.4 6 14 4H5v17h2v-7h5.6l.4 2h7V6z"),
    # All Transcripts - the whole queue (was U+1F4CB)
    'clipboard_list': ("M19 3h-4.18C14.4 1.84 13.3 1 12 1s-2.4.84-2.82 2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2M7 8h2v4H8V9H7zm3 9v1H7v-.92L9 15H7v-1h2.25c.41 0 .75.34.75.75 0 .2-.08.39-.21.52L8.12 17zm1-13c0-.55.45-1 1-1s1 .45 1 1-.45 1-1 1-1-.45-1-1m6 13h-5v-2h5zm0-6h-5V9h5z"),
    # OT Analytics (was U+1F4CA)
    'chart_bar': ("M22 21H2V3h2v16h2v-9h4v9h2V6h4v13h2v-5h4z"),
    # Save & Share - commit and send in (was U+1F4E4)
    'publish': ("M5 4v2h14V4zm0 10h4v6h6v-6h4l-7-7z"),
    # PRs - the icon for a pull request (was U+1F500)
    'source_pull': ("M6 3a3 3 0 0 1 3 3c0 1.31-.83 2.42-2 2.83v6.34c1.17.41 2 1.52 2 2.83a3 3 0 0 1-3 3 3 3 0 0 1-3-3c0-1.31.83-2.42 2-2.83V8.83A2.99 2.99 0 0 1 3 6a3 3 0 0 1 3-3m0 2a1 1 0 0 0-1 1 1 1 0 0 0 1 1 1 1 0 0 0 1-1 1 1 0 0 0-1-1m0 12a1 1 0 0 0-1 1 1 1 0 0 0 1 1 1 1 0 0 0 1-1 1 1 0 0 0-1-1m15 1a3 3 0 0 1-3 3 3 3 0 0 1-3-3c0-1.31.83-2.42 2-2.83V7h-2v3.25L10.75 6 15 1.75V5h2a2 2 0 0 1 2 2v8.17c1.17.41 2 1.52 2 2.83m-3-1a1 1 0 0 0-1 1 1 1 0 0 0 1 1 1 1 0 0 0 1-1 1 1 0 0 0-1-1"),
    # Config Backups, including the restore actions (was U+1F4BE)
    'backup_restore': ("M12 3a9 9 0 0 0-9 9H0l4 4 4-4H5a7 7 0 0 1 7-7 7 7 0 0 1 7 7 7 7 0 0 1-7 7c-1.5 0-2.91-.5-4.06-1.3L6.5 19.14A9.1 9.1 0 0 0 12 21a9 9 0 0 0 9-9 9 9 0 0 0-9-9m2 9a2 2 0 0 0-2-2 2 2 0 0 0-2 2 2 2 0 0 0 2 2 2 2 0 0 0 2-2"),
    # a directory in the snapshot browser (was U+1F4C1)
    'folder': ("M10 4H4c-1.11 0-2 .89-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-8z"),
    # a file in the snapshot browser (was U+1F4C4)
    'file_document_outline': ("M6 2a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zm0 2h7v5h5v11H6zm2 8v2h8v-2zm0 4v2h5v-2z"),
    # every refresh and sync button (was U+21BB)
    'refresh': ("M17.65 6.35A7.96 7.96 0 0 0 12 4a8 8 0 0 0-8 8 8 8 0 0 0 8 8c3.73 0 6.84-2.55 7.73-6h-2.08A5.99 5.99 0 0 1 12 18a6 6 0 0 1-6-6 6 6 0 0 1 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4z"),
    # the search field (was U+1F50D)
    'magnify': ("M9.5 3A6.5 6.5 0 0 1 16 9.5c0 1.61-.59 3.09-1.56 4.23l.27.27h.79l5 5-1.5 1.5-5-5v-.79l-.27-.27A6.52 6.52 0 0 1 9.5 16 6.5 6.5 0 0 1 3 9.5 6.5 6.5 0 0 1 9.5 3m0 2C7 5 5 7 5 9.5S7 14 9.5 14 14 12 14 9.5 12 5 9.5 5"),
    # positive Foundry feedback on a transcript (was U+1F44D)
    'thumb_up': ("M23 10a2 2 0 0 0-2-2h-6.32l.96-4.57c.02-.1.03-.21.03-.32 0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.58C7.22 7.95 7 8.45 7 9v10a2 2 0 0 0 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73zM1 21h4V9H1z"),
    # negative Foundry feedback on a transcript (was U+1F44E)
    'thumb_down': ("M19 15h4V3h-4m-4 0H6c-.83 0-1.54.5-1.84 1.22l-3.02 7.05c-.09.23-.14.47-.14.73v2a2 2 0 0 0 2 2h6.31l-.95 4.57c-.02.1-.03.2-.03.31 0 .42.17.79.44 1.06L9.83 23l6.58-6.59c.37-.36.59-.86.59-1.41V5a2 2 0 0 0-2-2"),
    # the empty-state glyph (was U+2630)
    'menu': ("M3 6h18v2H3zm0 5h18v2H3zm0 5h18v2H3z"),
    # column filter caret, and an open disclosure (was U+25BE)
    'chevron_down': ("M7.41 8.58 12 13.17l4.59-4.59L18 10l-6 6-6-6z"),
    # a closed disclosure (was U+25B8)
    'chevron_right': ("M8.59 16.58 13.17 12 8.59 7.41 10 6l6 6-6 6z"),
    # Eval Review - a checklist being ticked off, one transcript at a time
    'clipboard_check': ("M19 3h-4.18C14.4 1.84 13.3 1 12 1s-2.4.84-2.82 2H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2m-7 0a1 1 0 0 1 1 1 1 1 0 0 1-1 1 1 1 0 0 1-1-1 1 1 0 0 1 1-1M7 7h10V5h2v14H5V5h2zm.5 6.5L9 12l2 2 4.5-4.5L17 11l-6 6z"),
}


def icon(name, size=20, cls=""):
    """One Forge icon as inline SVG. Unknown names render nothing rather than raising.

    `fill="currentColor"` is the whole point: the icon takes the colour of its context, so one
    definition serves light mode, dark mode, the hover state and a per-item tint. An emoji could
    do none of those - it carried its own colour and ignored the theme.

    aria-hidden because every icon here sits beside its own text label. Announcing "flag, My
    Transcripts" is worse than announcing "My Transcripts".
    """
    d = FORGE_ICONS.get(name)
    if not d:
        return ""
    c = f' class="{cls}"' if cls else ""
    return (f'<svg{c} viewBox="0 0 24 24" width="{size}" height="{size}" '
            f'fill="currentColor" aria-hidden="true" focusable="false">'
            f'<path d="{d}"/></svg>')




def icon_mask(name):
    """One Forge icon as a CSS mask-image url(), for the few places that need a pseudo-element.

    Generated from the same FORGE_ICONS path as the inline SVG, so a chevron never drifts from
    the chevron next to it. A MASK rather than a background-image because a mask takes
    `currentColor` - a background-image data URI would bake in a colour and break in dark mode,
    which is exactly what went wrong with the review banners when they were inline styles.
    """
    d = FORGE_ICONS.get(name, "")
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>"
           f"<path d='{d}'/></svg>")
    # Only the characters that actually break a url() need escaping; leaving the rest readable
    # makes the emitted CSS inspectable in devtools.
    enc = (svg.replace("%", "%25").replace("#", "%23").replace('"', "%22")
              .replace("<", "%3C").replace(">", "%3E"))
    return f"url(\"data:image/svg+xml,{enc}\")"


def icon_vars():
    """The :root custom properties the CSS masks refer to."""
    return (":root{--chev-right:" + icon_mask("chevron_right")
            + ";--chev-down:" + icon_mask("chevron_down") + "}")


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
REVIEW_KEYS = ["review_status", "reviewer", "suggested_to", "review_round",
               "routing_verdict", "reassign_to", "answer_verdict", "diagnosis", "fix_target",
               "kb_action", "kb_files", "action_status", "bp_updates"]

# The four fields that DESCRIBE a change, and are therefore meaningless without one. They sit
# directly under the Summary box and stay disabled until an Ideal response or a Summary exists.
#
# They are not triggers - prose is still the only trigger (see wants_change). What they do is
# DIRECT the work prose asks for: which files, what kind of edit, where the fix belongs, and
# whether Blueprint needs the same change. Set on their own they described a change nobody had
# described, and `bp_updates` was the sharp end of that: ticked without prose it opens a Blueprint
# change request carrying no statement of what should be different.
#
# Order matters - bp_updates first, because it is the one that acts.
DEPENDENT_FIELDS = ["bp_updates", "fix_target", "kb_action", "kb_files"]

# `notes` IS DELIBERATELY ABSENT from the form. It was a one-line free-text box, which is the
# wrong shape for the only thing anyone wanted to put in it: prose. A reviewer with something to
# say now writes it against the exchange it is about (Ideal response) or against the transcript as a
# whole (the summary), both of which are proper textareas and both of which Claude already
# reads.
#
# The KEY still exists in the files and is still written by the tooling - mark_pushed.py records
# what it closed, fetch_transcripts.py records the go-live exclusion reason. write_fields()
# preserves any frontmatter key it does not recognise, so those values survive a save from a
# form that never shows them. Removing it from REVIEW_KEYS hides the input; it does not delete
# anybody's data.

# `reviewer` IS ALWAYS THE PERSON DOING THE REVIEWING. It is defaulted to whoever opened the
# transcript and is never blanked - not even by Suggest.
#
# That replaced a three-field arrangement that nobody could keep straight: `reviewer` (who made
# the call), `suggested_by` (who drafted a suggestion without claiming it as a verdict) and
# `awaiting` (the owner it was handed to). Two problems with it. The direction was ambiguous -
# "suggested by" reads as provenance when what a reviewer wants to record is a DESTINATION - and
# once `reviewer` always names the current person, `suggested_by` has no job left, because the
# reviewer IS the suggester.
#
# So both collapse into ONE field, `suggested_to`: who this is being handed to. Safe to do
# because neither old field had ever been given a value on any of the 61 transcripts - the
# arrangement was confusing enough that nobody used it.
#
# `suggested_to` and `reassign_to` are the two fields that put a transcript in someone ELSE's
# queue, and both accept a person OR an agent. An agent means "whoever owns that corpus", which
# is the common case: you rarely know who owns SAC, but you always know it is a SAC problem.
PEOPLE_KEYS = ("reviewer",)

# Only the labels whose wording differs from the key. Everything else is the key with
# underscores swapped for spaces and the first letter capitalised.
FIELD_LABEL = {
    "review_status": "Review status",
    "reviewer":      "Reviewer",
    "suggested_to":  "Suggested to",
    "reassign_to":   "Reassign to",
    "review_round":  "Review round",
    "bp_updates":    "BP updates",
    "kb_files":      "KB files",
    "kb_action":     "KB action",
}

# Fields that route a transcript to another queue. Values may be a contributors.json `github`
# login or an agent slug.
ROUTING_KEYS = ("suggested_to", "reassign_to")

# Maintained by the tooling, shown but not editable. See the DERIVED_KEYS branch in field().
DERIVED_KEYS = ("review_round",)

# Column-filter id (minus the `f_` prefix) -> the record key it filters on. Only the ones
# that differ need an entry.
FILTER_SRC = {"sugg": "suggested_to"}

# Set by the WORKFLOW, not by a contributor. A contributor sees the value and cannot change it.
#
#   review_status  the buttons set it - Mark reviewed, Suggest, Re-review. Typing it by hand is
#                  how a transcript ends up `pushed` without ever reaching Foundry, or `excluded`
#                  without anybody deciding to exclude it.
#   reviewer       always the current person. There is no case where a contributor should record
#                  somebody else as having made a call.
#   action_status  follows kb_action, or is Claude's claim that the work is done. Neither is a
#                  contributor's to assert.
#
# Admins keep them editable: closing out a batch, correcting a bad state and re-opening something
# excluded by mistake all need a hand on these, and an admin is who does that.
#
# The buttons still drive them for everyone - the field renders as text plus a HIDDEN input
# carrying the same `data-fm`, so every existing querySelector('[data-fm=review_status]').value
# assignment keeps working. Locking the input does not lock the workflow.
ADMIN_ONLY_FIELDS = ("review_status", "reviewer", "action_status")

# Picked from the repo, not typed. See the MULTI_KEYS branch in field().
MULTI_KEYS = ("kb_files",)

# Yes/no fields, rendered as a checkbox. Stored as "yes" or empty, so the frontmatter stays
# greppable and a human editing the file by hand cannot produce a third state.
BOOL_KEYS = ("bp_updates",)


def knowledge_files(scoped=True):
    """Knowledge files grouped by corpus, as `Corpus/File.md`.

    SCOPED TO WHAT YOU OWN unless you are an admin. A contributor can only APPROVE changes to
    their own corpus - CODEOWNERS enforces that - so offering them the whole repo in a picker
    invites naming a file whose change they cannot get merged. Worse, `kb_files` is read as
    instructions by whoever applies the change, so a contributor pointing at Knowledge-Shared
    is asking for an edit that alters what all five agents say.

    Admins see everything, because they own the admin-only corpora and routing.

    NOT a security control - this is a picker, and the same person can edit the frontmatter by
    hand. It is there so the common path does not lead somewhere that cannot be merged.
    Enforcement stays where it belongs: CODEOWNERS, branch protection, and
    check_folder_ownership.py in CI.

    Read from disk each time rather than cached: a reviewer who has just added a file should
    find it in the list, and the alternative is a picker quietly missing the thing they are
    about to name.
    """
    mine = None
    if scoped and ME and not is_admin():
        by, default = agent_owners()
        owned = {AGENT_FOLDER_NAME[s] for s, who in by.items()
                 if ME in (who if isinstance(who, (list, set, tuple)) else [who])
                 and s in AGENT_FOLDER_NAME}
        if default == ME:
            owned |= {AGENT_FOLDER_NAME[s] for s in AGENT_FOLDER_NAME if s not in by}
        mine = owned
    out = {}
    for d in sorted(REPO.iterdir()):
        if not (d.is_dir() and d.name.startswith("Knowledge-")):
            continue
        if mine is not None and d.name not in mine:
            continue
        files = sorted(f.name for f in d.glob("*.md"))
        if files:
            out[d.name] = files
    return out


# Agent slug -> corpus folder. Same table as gen_codeowners.py's AGENT_FOLDER, kept here so the
# picker and the permissions it mirrors cannot disagree about which folder an agent owns.
AGENT_FOLDER_NAME = {
    "ops-center":       "Knowledge-OpsCenter",
    "bp-general":       "Knowledge-BP-General",
    "sac":              "Knowledge-SupportAccessCenter",
    "identity":         "Knowledge-TylerIdentity",
    "aligned-releases": "Knowledge-AlignedReleases",
    "status-page":      "Knowledge-StatusPageAndSLA",
}

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
        "about": "Where this transcript sits in the review lifecycle. Normally changed "
                 "with the buttons at the bottom rather than the dropdown. `suggested` is "
                 "optional — skip it for an owned area.",
        "values": {
            "pending": "Nobody has reached a conclusion yet. Saving with fields filled in and "
                       "leaving it here is a deliberate note-to-self — nobody else will act on it.",
            "suggested": "Worked up, but the call belongs to someone else. Goes to whoever is "
                         "named in `suggested_to`. Claude will NOT act on it.",
            "reviewed": "The reviewer's verdict, on the record. This is the queue Claude works from, so "
                        "only set it when changes may be made on this basis.",
            "pushed": "Processed AND live in Foundry. Claude sets this after verifying the "
                      "upload — it is a claim about Foundry, not about the repo. Don't set it by hand.",
            "excluded": "Not real feedback, so it leaves the queue without counting as review "
                        "work. Used for pre-go-live internal testing (before 2026-08-19 19:42 UTC).",
        },
    },
    "reviewer": {
        "about": "Whoever is reviewing this. Defaulted to the person who opened it and "
                 "never cleared, including on a suggestion: suggesting is still something a person "
                 "did. Restricted to contributors.json, which is generated from GitHub team "
                 "membership — a missing name means the person is not on the team yet, and typing "
                 "it in will not help.",
        "values": {},
    },
    "suggested_to": {
        "about": "The PERSON this is handed to. Setting it moves the transcript into "
                 "their queue and out of the current one — the decision is given up, not just "
                 "asking for a second opinion.\n\n"
                 "`Reassign to` is the same act one level up: name an AGENT when the problem "
                 "belongs to another corpus and its current owner is unknown or irrelevant this "
                 "month. Set either one and **Mark reviewed** no longer applies, because the "
                 "call has been handed over — use **Suggest** instead.",
        "values": {},
    },
    "review_round": {
        "about": "Which pass over this transcript this is — **maintained automatically, not typed**. "
                 "The Re-review button raises it by one; nothing else should. Raising it re-opens "
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
    # reassign_to is the OTHER routing field. Same consequence as suggested_to - it puts the
    # transcript in someone else's queue - for a different reason: the wrong agent answered,
    # rather than the wrong person is deciding.
    "reassign_to": {
        "about": "Which AGENT should own this instead — the same act as `Suggested to`, one "
                 "level up. Use it when the problem belongs to another corpus and there is no need to "
                 "know, or should not need to know, who owns that corpus this month; it "
                 "resolves through ownership, so it survives the owner changing.\n\n"
                 "Setting it moves the transcript into that agent's owners' queue and out of "
                 "the current one, and **Mark reviewed** no longer applies — the call has been handed over. "
                 "Repeated reassignments to the same target are the strongest evidence the team "
                 "routing rules need changing.",
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
        "about": "Quality of the answer the user actually received. Judge it against what a "
                 "would have told them — not against whether the agent tried hard.",
        "values": {
            "": "Not assessed.",
            "good": "Fit to send as-is.",
            "incomplete": "Correct as far as it goes, but missing something that matters. The "
                          "most common real verdict.",
            "wrong": "Materially incorrect — it would mislead someone who acted on it.",
            "stale": "Was true once; the world moved and the corpus did not.",
            "refused": "Declined or deflected a question it should have answered.",
        },
    },
    "diagnosis": {
        "about": "WHY it went wrong — the single most important field, because it decides who "
                 "fixes it. Read the 'Tools called' line on the exchange: it reports what the "
                 "agent actually did, which four different failures all look identical in the "
                 "visible chat. Do not guess; if it cannot be told from the record, say so.",
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
                                  "Foundry — write the exact wording under Overall suggestions and comments; Claude "
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
                 "`none` and a good summary is still a complete contribution.",
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
                 "`open` and kb_action asks for something.\n\n"
                 "**Mostly automatic.** `none-needed` and `open` follow from `kb_action`, so "
                 "picking them is not a reviewer task. `applied` is Claude's, after the work is done. "
                 "`wontfix` is the only one that is genuinely a decision — and it wants a "
                 "reason written in Ideal response or in the summary.",
        "values": {
            "": "Not assessed.",
            "none-needed": "Nothing had to change. **Set automatically** when `kb_action` is `none`.",
            "open": "A change is required and has not been made yet — Claude's to-do list. "
                    "**Set automatically** when `kb_action` asks for something.",
            "applied": "The change has been made. Set by Claude after doing it, not by a reviewer, and "
                       "never overwritten automatically — it is a claim about work, not a "
                       "restatement of `kb_action`.",
            "wontfix": "Decided against acting on it. A reviewer decision, never automatic — say why "
                       "in Ideal response or in the summary, so the reason sits with the reasoning.",
        },
    },
    # Not frontmatter fields — the two free-text boxes. Same treatment so the page reads
    # uniformly: a label, an icon, and nothing else.
    "ideal response": {
        # WHY THE LABEL CHANGED. This field was called "Correction", and the old help text here
        # said "what the agent SHOULD have said" - which is right - but the label said the
        # opposite thing, and the label is what gets read. Reviewers reasonably took it as a
        # place for notes ABOUT the answer. What the field actually wants is the answer itself,
        # written out as the user should have received it: the recovered 2026-08-28 workspace
        # review holds a 2,300-character formatted reply, not a critique, and that is the shape
        # the whole pipeline is built around - Claude turns this text into knowledge-file content
        # directly, and the eval scores the live answer against it word for word.
        "about": "The answer the agent should have given, written out in full as the user "
                 "should have seen it — not notes about what went wrong. Markdown is fine, and "
                 "\"Copy Foundry response\" seeds the box with the answer that was actually "
                 "given, so most reviews are an edit rather than a blank page.\n\n"
                 "A FULL RESPONSE IS WHAT MAKES THE EVALUATION WORK. After the knowledge files "
                 "are updated, Eval Review re-asks this question and compares the new Foundry "
                 "response against this text word for word, reporting a match percentage and "
                 "the deviations still outstanding. Notes cannot be compared to an answer, so a "
                 "box holding \"this is wrong\" scores meaninglessly and the check cannot say "
                 "whether the fix landed. A complete answer both becomes knowledge-file content "
                 "directly and gives the eval something real to measure against.\n\n"
                 "Leave it empty if the answer was already right.",
        "values": {},
    },
    "bp_updates": {
        "about": "Tick this when the feedback also implies a change to the **Blueprint** "
                 "documentation — either because an ideal response contradicts what Blueprint says, "
                 "or because Blueprint should be checked for the same problem.\n\n"
                 "Blueprint is not edited here. Ticking it tells the assistant to work "
                 "both repos: apply what the ideal responses imply, and scan the Blueprint docs for "
                 "conflicts with the same subject. Part 2 then opens a SECOND change request "
                 "against Blueprint alongside this one, and both are merged together.\n\n"
                 "**Required, not optional, when the fix lands in a `Docusaurus-` file.** Those "
                 "are DERIVED from Blueprint and re-generated from it, so a fix made only in the "
                 "knowledge file is silently deleted by the next reconciliation. The agent "
                 "answers correctly for a while and then quietly regresses, with the transcript "
                 "closed out and nobody looking. Fixing Blueprint is the only durable fix.\n\n"
                 "This box ticks itself when a `Docusaurus-` file is named in KB files, for that "
                 "reason. Untick it only if the Blueprint page already says the right "
                 "thing.",
        "values": {},
    },
    # Named "Overall suggestions and comments" in the UI. The key stays `proposed_fix` because
    # it is the marker in every transcript body and in CLAUDE.md's process; renaming it would
    # rewrite 61 files to change a label.
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
                 "ask, what is uncertain, what was decided against. Long-form belongs in "
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


def derived_round(rel):
    """Which round this transcript's NEXT verdict belongs to. Derived, never typed.

    Read off what `origin/main` already holds, because that is the question the round exists to
    answer: has a verdict on this transcript already been merged, and is this a new pass over it?

    The rules match validate_reviews.py exactly, which is the point - a round the reviewer
    cannot set is a round CI cannot reject:

        not on main yet          -> 1        first review
        on main, no verdict      -> its round no decision has been merged, so still that pass
        on main, suggested       -> its round the owner ACCEPTING a handoff is the same pass
        on main, reviewed        -> +1       a genuine second opinion
        on main, excluded        -> +1       same: re-opening something already decided
        on main, pushed          -> +1       decided AND shipped; a new look is a new pass

    Note `suggested` does NOT advance it. A suggestion is a handoff, not a decision, so the
    owner's verdict completes the round rather than starting a new one - and CI treats
    suggested -> reviewed at the same round as the normal path.
    """
    rc, out = git("show", f"origin/main:{rel}")
    if rc != 0 or not out.strip():
        return 1
    fm = {}
    m = re.match(r"^---\n(.*?)\n---", out, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line and not line.strip().startswith("#"):
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip()
    status = fm.get("review_status") or "pending"
    try:
        base = int(fm.get("review_round") or 1)
    except ValueError:
        base = 1
    # validate_reviews.py accepts ANY higher round as a deliberate re-review
    # (`elif h_round > b_round`), whatever the base status, so advancing here cannot trip CI.
    return base + 1 if status in ("reviewed", "excluded", "pushed") else base


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
    (fragile) or passing empty strings, which WIPES the reviewer's ideal response and proposed
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


# ---------------------------------------------------------------------------------------------
# CSV round-trip for ideal responses
#
# The point is COLLABORATION OUTSIDE THIS TOOL. Ideal responses are the one part of a review that
# somebody else may be better placed to write - a product owner who knows what the answer should
# have been but is never going to open a local review server. Export the questions and answers,
# let them fill the fourth column in whatever they already use, import it back.
#
# ONLY THE IDEAL RESPONSE IS IMPORTED. The first three columns are identity, not payload: they say
# WHICH exchange an ideal response belongs to. An edited question therefore does not rewrite the
# transcript - it stops the row matching anything, and the row is dropped. That is the intended
# behaviour and the reason those headers carry (DO NOT MODIFY): the failure mode of a mutable
# identity column is silently attaching an ideal response to the wrong exchange, which is worse than
# losing the row.
CSV_ID_HEAD = "Transcript id (DO NOT MODIFY)"
CSV_HEADERS = [CSV_ID_HEAD,
               "Exchange question (DO NOT MODIFY)",
               "Foundry response (DO NOT MODIFY)",
               "Ideal response"]

# Excel guesses the encoding of a .csv unless a BOM tells it, and guesses wrong on anything
# non-ASCII - so an exported transcript comes back with mojibake in the questions, which then
# fails to match on import. Written on export, stripped on import.
CSV_BOM = "﻿"


def _qkey(s):
    """Match key for a question. Whitespace-collapsed and case-folded, nothing else.

    Deliberately NOT fuzzy. The column is identity, so a near-match must fail rather than pick
    a probable exchange - but a spreadsheet that re-wraps a long cell or changes its case is
    reformatting, not editing, and should still match.
    """
    return re.sub(r"\s+", " ", (s or "")).strip().casefold()


def _is_placeholder(s):
    """The fetch template's empty-state line, which is not an ideal response anybody wrote."""
    t = (s or "").strip()
    return not t or t in PLACEHOLDERS


def _neutralise_markers(s):
    """Make imported text incapable of closing the block it is being written into.

    An ideal response containing `<!-- /review:1 -->` would otherwise terminate its own block: the
    stored ideal response is truncated at that point and the remainder leaks into the document body
    as loose prose. Measured, not theorised - a five-line ideal response came back as one word with
    the other four sitting outside the block.

    `&lt;!--` renders as literal text in markdown and can never terminate anything, so the
    ideal response stays readable and the file stays parseable. Every HTML-comment opener is
    converted, not just the review ones: `proposed-fix` has the same shape, and a rule with an
    exception list is a rule waiting to be outgrown.
    """
    return (s or "").replace("<!--", "&lt;!--")


def csv_export(rels):
    """One row per EXCHANGE across the given transcripts. (csv_text, n_rows, skipped).

    Row order is the order of the transcripts as given, then document order within each - so the
    file reads like the queue it came from.
    """
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(CSV_HEADERS)
    n, skipped = 0, []
    for rel in rels:
        f = (TDIR / rel).resolve()
        if not str(f).startswith(str(TDIR.resolve())) or not f.is_file():
            skipped.append((rel, "not found"))
            continue
        fm, body = parse(f)
        if fm is None:
            skipped.append((rel, "no frontmatter"))
            continue
        # PENDING ONLY, matching the import side exactly. Exporting a transcript that cannot be
        # imported back would hand a collaborator work with nowhere to land.
        st = (fm.get("review_status") or "pending").strip() or "pending"
        if st != "pending":
            skipped.append((rel, f"{st} — export covers pending transcripts only"))
            continue
        exs = exchanges_of(body or "")
        if not exs:
            skipped.append((rel, "no exchanges"))
            continue
        for num, _tools, q, a, rv in exs:
            # The placeholder goes out EMPTY. Shipping template text to a collaborator invites
            # them to edit around it, and it would then import as an ideal response saying nothing.
            w.writerow([rel, q, a, "" if _is_placeholder(rv) else rv])
            n += 1
    return CSV_BOM + buf.getvalue(), n, skipped


def _sniff_reader(text):
    """A csv reader for text that may not use commas.

    Excel writes the LIST SEPARATOR of the machine's locale, which is a semicolon across much of
    Europe. Someone editing an export in that Excel and sending it back produces a file that
    parses as one column per row and matches nothing - a confusing failure, since the file looks
    right when opened in the same Excel.
    """
    head = (text.split("\n", 1)[0] or "")[:2000]
    delim = ","
    try:
        delim = csv.Sniffer().sniff(head, delimiters=",;\t|").delimiter
    except csv.Error:
        pass
    return csv.reader(io.StringIO(text), delimiter=delim), delim


def csv_import(text):
    """Apply the Ideal response column back onto matching exchanges. Returns a report dict.

    MATCHING is by transcript id plus question text, never by row position. Position would break
    the moment a collaborator sorted the sheet or deleted a row they had nothing to say about,
    and both are things people do to a spreadsheet without thinking of it as destructive.

    A question repeated inside one transcript is resolved in document order: the first CSV row
    carrying it takes the first such exchange, the second takes the second. Claiming exchanges as
    they are matched is what makes that work - without it both rows would write to exchange 1 and
    the second exchange would silently keep its old text.
    """
    text = (text or "").lstrip(CSV_BOM)
    if not text.strip():
        return {"ok": False, "error": "that file is empty"}
    reader, delim = _sniff_reader(text)
    rows = list(reader)
    if not rows:
        return {"ok": False, "error": "no rows in that file"}

    # A header is optional. Recognised by its first cell rather than by position, so a file with
    # the header stripped still imports and a file that kept it does not treat it as data.
    if _qkey(rows[0][0] if rows[0] else "").startswith(_qkey("transcript id")):
        rows = rows[1:]

    # Group by transcript first: each file is opened, matched and written ONCE, so a transcript
    # with six ideal responses is one read and one write rather than six of each.
    by_rel = {}
    ignored = []
    for i, row in enumerate(rows, start=2):          # 2 = first data line in a headered file
        if not row or not any((c or "").strip() for c in row):
            continue                                  # blank spacer line, not an error
        if len(row) < 4:
            ignored.append((i, f"only {len(row)} column(s) — needs 4"))
            continue
        rel = (row[0] or "").strip()
        if not rel:
            ignored.append((i, "no transcript id"))
            continue
        by_rel.setdefault(rel, []).append((i, row[1], row[3]))

    applied, unchanged, skipped = [], 0, []
    for rel, items in by_rel.items():
        f = (TDIR / rel).resolve()
        if not str(f).startswith(str(TDIR.resolve())) or not f.is_file():
            for i, _q, _c in items:
                ignored.append((i, f"no such transcript: {rel}"))
            continue
        fm, body = parse(f)
        if fm is None:
            skipped.append((rel, "no frontmatter"))
            continue
        st = (fm.get("review_status") or "pending").strip() or "pending"
        # PENDING ONLY. Anything else carries a decision, and an imported ideal response would edit a
        # body whose frontmatter still asserts the old verdict - `reviewed` and `suggested` claim
        # a human has judged this text, `pushed` claims it is already live in Foundry, `excluded`
        # claims it is out of scope. Landing new prose under any of those makes the claim false
        # while leaving it on the page.
        if st != "pending":
            skipped.append((rel, f"{st} — import covers pending transcripts only"))
            continue
        exs = exchanges_of(body or "")
        pool = [[num, _qkey(q), False] for num, _tools, q, _a, _rv in exs]
        current = {num: rv for num, _t, _q, _a, rv in exs}

        writes = {}
        for i, q_csv, corr in items:
            key = _qkey(q_csv)
            hit = next((slot for slot in pool if slot[1] == key and not slot[2]), None)
            if hit is None:
                # Either the question was edited, or it belongs to a different transcript, or
                # every matching exchange is already claimed by an earlier row.
                ignored.append((i, f"question does not match an unclaimed exchange in {rel}"))
                continue
            hit[2] = True
            num = hit[0]
            new = _neutralise_markers(corr).strip()
            # BLANK MEANS "NOTHING SUPPLIED", NOT "DELETE". A round-trip through a spreadsheet
            # drops cells for all sorts of dull reasons, and an import that wiped ideal responses on
            # a blank would destroy work that is not recoverable from anywhere else. Clearing a
            # ideal response stays a deliberate act in the transcript form.
            if not new:
                unchanged += 1
                continue
            if new == (current.get(num) or "").strip():
                unchanged += 1
                continue
            writes[num] = new

        if not writes:
            continue
        txt = f.read_text(encoding="utf-8")
        for num, new in writes.items():
            txt = re.sub(rf"(<!-- review:{num} -->\n).*?(<!-- /review:{num} -->)",
                         lambda m: m.group(1) + new.strip() + "\n" + m.group(2),
                         txt, flags=re.S)
        f.write_text(txt, encoding="utf-8")
        applied.append((rel, sorted(writes, key=lambda x: int(x))))
        # NO frontmatter repair here, unlike the transcript form. That repair exists to reconcile
        # a `reviewed` file whose fields say "nothing wrong" while its body says otherwise - and
        # only pending transcripts reach this point, where the fields have not been asserted yet.
        # The reviewer opens it, reads the imported ideal response and records the verdict themselves.

    if applied:
        refresh_index()
    return {"ok": True, "applied": applied, "unchanged": unchanged,
            "ignored": ignored, "skipped": skipped, "delimiter": delim}


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
  /* Diff view. Tinted rows rather than a dark terminal block: this is for reading a
     change, not for watching command output, and the surrounding page is light. */
  --d-add-bg:#e6ffed;  --d-add-ln:#d0f5da;  --d-add-fg:#12401f;
  --d-del-bg:#ffebe9;  --d-del-ln:#ffd7d5;  --d-del-fg:#4a1416;
  --d-hunk-bg:#eef2f7; --d-hunk-fg:#41525f;
  /* Routing warning. Light red rather than the amber used for ordinary attention: a
     routing mistake has a different blast radius from a content one. */
  --bnr-router-bg:#fdeced; --bnr-router-bd:#f0bcc0; --bnr-router-fg:#5c1a1f;
  --d-ln-fg:#8a97a3;   --d-plus:#116329;   --d-minus:#a40e26;
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
  --d-add-bg:#12261a;  --d-add-ln:#1b3a26;  --d-add-fg:#c4e8cf;
  --d-del-bg:#2b1517;  --d-del-fg:#f3c9c9;  --d-del-ln:#43201f;
  --d-hunk-bg:#1b2430; --d-hunk-fg:#b6c6d4;
  --bnr-router-bg:#33191c; --bnr-router-bd:#5e2d33; --bnr-router-fg:#f4cdd1;
  --d-ln-fg:#7c8a97;   --d-plus:#7ee2a8;   --d-minus:#ff9c9c;
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
/* Nav icons are Tyler Forge SVG, not emoji. Emoji rendered from a system font, so the same
   nav looked different on macOS and Windows, could not be tinted, and carried a baked-in
   colour that fought the theme in dark mode.
   Each item keeps a DISTINCT HUE, from semantic theme tokens rather than arbitrary colours -
   the nav being scannable by colour was the point of using emoji in the first place, and a
   monochrome swap would have lost it. currentColor on the svg is what makes the tint work. */
nav.side a .ic{width:20px;height:20px;flex:0 0 auto;display:inline-flex;
align-items:center;justify-content:center;line-height:0}
nav.side a .ic svg{display:block}
.ic-mine{color:var(--forge-theme-warning)}      /* yours, wants attention */
.ic-all{color:var(--forge-theme-text-medium)}   /* the whole queue: deliberately neutral */
.ic-an{color:var(--forge-theme-info)}           /* monitoring */
.ic-git{color:var(--forge-theme-primary)}       /* the main outbound action */
.ic-prs{color:var(--accent-purple)}             /* matches the delegated/suggested purple */
.ic-bk{color:var(--forge-theme-success)}        /* safety net */
.ic-ev{color:var(--forge-theme-warning)}        /* a decision is waiting on you */
/* On the selected row the label goes primary, and a coloured icon beside it reads as a
   mismatch rather than as emphasis - so the tint yields to the active state. */
nav.side a.on .ic svg{color:var(--forge-theme-primary)}
/* Inline icons elsewhere sit on the text baseline next to words. */
button svg,.mag svg,th .caretbtn svg{vertical-align:-3px}
.emptyglyph{color:var(--forge-theme-text-low);opacity:.55;margin-bottom:10px}
.fb svg{vertical-align:-3px}
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
/* The list of saves. A recessed panel, like the change list - it is a record of what has
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
   Save and Publish only: everything one step larger. SCOPED, not global - the transcript list is
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
/* --- EVAL REVIEW. Before/Now side by side, because the judgement being asked for is a
   comparison and stacking them makes the reader hold one in their head. */
.evcard{border-left:3px solid var(--forge-theme-outline-low)}
.evcard.evok{border-left-color:var(--forge-theme-success)}
.evhead{display:flex;align-items:center;gap:9px;cursor:pointer;font-size:14px}
.evhead input{width:17px;height:17px;accent-color:var(--forge-theme-primary);cursor:pointer;
flex:0 0 auto}
.evq{background:var(--forge-theme-surface-container);border-radius:5px;padding:9px 11px;
margin:0 0 10px;font-size:13.5px}
.evq b{color:var(--forge-theme-text-medium);margin-right:6px}
.evcols{display:grid;grid-template-columns:1fr 1fr;gap:12px;align-items:start;--evbox-h:360px}
@media(max-width:900px){.evcols{--evbox-h:280px}}
@media(max-width:900px){.evcols{grid-template-columns:1fr}}
.evlab{font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;
margin:0 0 5px;color:var(--forge-theme-text-medium)}
.evbefore pre,.evafter pre{margin:0;padding:10px;border-radius:5px;font-size:12px;
line-height:1.5;white-space:pre-wrap;word-break:break-word;max-height:320px;overflow:auto;
border:1px solid var(--forge-theme-outline-low)}
.evbefore pre{background:var(--d-del-bg,var(--forge-theme-surface-container))}
/* SAME BOX, BOTH SIDES. The target is a <pre> and the answer is a <textarea>, and left to
   their own devices they size to their content - so the two things a reviewer is comparing
   side by side started and ended at different heights. A fixed, shared height is the only way
   two different elements line up; --evbox-h keeps them defined in one place. */
.evtarget pre{margin:0;padding:10px;border-radius:5px;font-size:12px;line-height:1.5;
white-space:pre-wrap;word-break:break-word;height:var(--evbox-h);overflow:auto;
box-sizing:border-box;
border:1px solid var(--forge-theme-outline-low);
background:var(--bnr-sug-bg);color:var(--bnr-sug-fg)}
.evafter pre{background:var(--d-add-bg,var(--forge-theme-surface-container))}
.evmatch{margin-left:8px;padding:1px 7px;border-radius:9px;font-size:10.5px;font-weight:600;
letter-spacing:0;text-transform:none;cursor:help}
/* The SAME token pairs the status pills use, not invented ones. My first attempt reached for
   `--forge-theme-*-container-low` with the raw accent as the text colour; the light-mode
   fallback resolved to #e0e0e0 and check_contrast.py caught .ok at 3.88:1 and .warn at 3.81:1
   against a 4.5:1 floor. --pill-ok-fg / --pill-warn-fg exist precisely because the raw accents
   are too light on a tinted chip, and they are already verified in both modes. */
.evmatch.ok{background:var(--tint-success);color:var(--pill-ok-fg)}
.evmatch.warn{background:var(--forge-theme-warning-container-low);color:var(--pill-warn-fg)}
.evmatch.bad{background:var(--tint-error);color:var(--forge-theme-error)}
/* A refreshed answer has to be visibly refreshed - the whole complaint was not being able to
   tell whether Ask again had done anything. */
@keyframes evflash{from{background:var(--forge-theme-primary-container-minimum)}to{background:transparent}}
.evafter.isnew pre,.evvar.isnew pre{animation:evflash 1.8s ease-out}
.evnowbox{width:100%;box-sizing:border-box;font:inherit;font-size:12px;line-height:1.5;
padding:10px;border-radius:5px;resize:vertical;height:var(--evbox-h);
border:1px solid var(--forge-theme-outline-low);
background:var(--d-add-bg,var(--forge-theme-surface-container));
color:var(--forge-theme-text-high)}
.evnowbox:focus{outline:2px solid var(--forge-theme-primary);outline-offset:-1px}
.evmarks{font-size:11.5px;color:var(--forge-theme-text-medium);align-self:center}
.evedited{font-size:10.5px;font-weight:600;color:var(--forge-theme-warning);margin-left:8px}
/* Group headers inside the review form. Deliberately quiet - they orient, they are not a
   warning, and the form has enough going on. */
/* On the two prose inputs, which are the strongest change signals and cannot be grouped with
   the dropdowns because each appears once, in a different place. Quiet on purpose - it is a
   reminder, not a warning. */
.trigtag{margin-left:8px;padding:1px 6px;border-radius:8px;font-size:10px;font-weight:600;
letter-spacing:.03em;text-transform:uppercase;
/* text-high, not text-medium: medium-on-surface-container measures 4.47:1 in dark mode, just
   under the 4.5 floor. Same pair caught by check_contrast on the eval card's disclosure. */
background:var(--forge-theme-surface-container);color:var(--forge-theme-text-high)}
.fldgrp{grid-column:1/-1;margin:14px 0 2px;padding-top:10px;
border-top:1px solid var(--forge-theme-outline-low)}
.fldgrp:first-child{margin-top:0;padding-top:0;border-top:0}
.fldgrp-h{font-weight:600;font-size:11.5px;letter-spacing:.05em;text-transform:uppercase;
color:var(--forge-theme-text-medium)}
.evask{margin:0 0 10px}
.evqbox{width:100%;box-sizing:border-box;font:inherit;font-size:13.5px;padding:8px 10px;
border:1px solid var(--forge-theme-outline-medium);border-radius:5px;resize:vertical;
background:var(--forge-theme-surface);color:var(--forge-theme-text-high)}
.evqbox:focus{outline:2px solid var(--forge-theme-primary);outline-offset:-1px}
.evvar{margin-top:10px;padding-left:10px;border-left:2px solid var(--forge-theme-outline-low)}
.evvq{font-size:13px;font-weight:500;margin:0 0 5px}
.evvar pre{margin:0;padding:9px 10px;border-radius:5px;font-size:12px;line-height:1.5;
white-space:pre-wrap;word-break:break-word;max-height:260px;overflow:auto;
background:var(--forge-theme-surface-container);border:1px solid var(--forge-theme-outline-low)}
.evcorr{margin-top:10px}
.evcorr summary{cursor:pointer;font-size:13px;color:var(--forge-theme-primary)}
/* NEUTRAL GREY, not the purple this rule used to carry. `.evcorr` was the ideal response's own
   styling; the disclosure was then repurposed to hold the ORIGINAL (bad) answer and kept the
   tint, so the known-bad answer and the target answer looked identical. Purple means "this is
   the suggestion" everywhere else in the app, which made it actively misleading here.
   Scoped with `>` so it cannot reach the .evvar pre blocks inside the Earlier disclosure -
   those two selectors have equal specificity and were resolving on source order. */
.evcorr > pre{margin:8px 0 0;padding:10px;border-radius:5px;font-size:12.5px;
white-space:pre-wrap;word-break:break-word;max-height:320px;overflow:auto;
background:var(--forge-theme-surface-container);color:var(--forge-theme-text-high);
border:1px solid var(--forge-theme-outline-low)}
/* "It ran; a person decides." Deliberately not `done`: a green tick on the eval would say the
   step is complete when the only thing that completes it is a human reading the answers. It
   was the absence of any such state that made the eval invisible in this list. */
ol.prog li.you{color:var(--forge-theme-text-high)}
ol.prog li.you::before{content:"\2691";background:none;border:0;
color:var(--forge-theme-warning);font-size:14px;top:6px}
ol.prog li.you b{color:var(--forge-theme-warning)}
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
/* Now a disclosure inside the state bar rather than a standalone panel, so it drops the tinted
   background it used to need to separate itself - the bar already provides that - and keeps only
   the spacing and the summary's own styling. */
.whatsent{margin-top:10px;font-size:13.5px}
.whatsent summary{cursor:pointer;list-style:none}
.whatsent summary::-webkit-details-marker{display:none}
.whatsent summary>b{font-weight:500;font-size:13px;color:var(--forge-theme-text-medium)}
/* A caret, so a collapsed panel reads as openable rather than as a dead label. */
.whatsent summary>b::before{content:"\25B8";display:inline-block;margin-right:6px;
font-size:11px;transition:transform .12s}
.whatsent[open] summary>b::before{transform:rotate(90deg)}
.whatsent ul{margin:4px 0 10px 18px;padding:0}
.whatsent ul:last-child{margin-bottom:0}
/* Same treatment as the panel's own heading, one level in - so the groups read as part
   of it rather than as separate panels. */
.fgrp{font-weight:500;font-size:12px;color:var(--forge-theme-text-medium);
margin-top:10px;letter-spacing:.02em}
.fgrp:first-child{margin-top:6px}

/* Merged-request history. Collapsed, and styled like the other disclosures rather than as a
   card, so it reads as an archive under the open requests instead of competing with them. */
.histbox{margin-top:26px}
.histbox>summary{cursor:pointer;list-style:none;padding:6px 0}
.histbox>summary::-webkit-details-marker{display:none}
.histbox>summary>b{font-weight:500;font-size:13px;color:var(--forge-theme-text-high)}
.histbox>summary>b::before{content:"\25B8";display:inline-block;margin-right:6px;
font-size:11px;transition:transform .12s}
.histbox[open]>summary>b::before{transform:rotate(90deg)}
.histbox .tblcard{margin-top:8px}
.histbox td{vertical-align:top}

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
/* The disclosure marker is a Forge chevron drawn through a mask rather than a text glyph.
   A mask (not background-image) so it still takes `currentColor` - a background-image data URI
   would hard-code a colour and break in dark mode, which is the trap that caught the review
   banners. The paths are the same chevron_right / chevron_down from FORGE_ICONS. */
.chev::before{content:"";display:block;width:16px;height:16px;background:currentColor;
-webkit-mask:var(--chev-right) center/16px no-repeat;mask:var(--chev-right) center/16px no-repeat}
details.card[open]>summary .chev::before{-webkit-mask-image:var(--chev-down);
mask-image:var(--chev-down)}
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
/* The action row, directly under the telemetry cards. `position:relative` is load-bearing:
   confirmThen appends its confirm box to the button's PARENT, so an unpositioned row would let
   that box escape the layout. */
.actbar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;position:relative;
margin-bottom:var(--forge-spacing-medium)}
.actbar .hint{margin-left:4px}
td.fbcell,th.fbcell{width:1%;text-align:center;padding-left:6px;padding-right:6px}
.fb{font-size:15px;line-height:1;cursor:help}
.fb-none{color:var(--fb-none-fg);cursor:help}
/* The thumbs-down signal lives in its own CELL, not on the row. A row tint or a left bar
   would compete with the amber/blue "this row is assigned" highlighting below, and on a row that
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
.bar.bnr-router{background:var(--bnr-router-bg);border-color:var(--bnr-router-bd);
color:var(--bnr-router-fg)}
.evalbox{background:var(--forge-theme-surface-container-minimum);
border:1px solid var(--forge-theme-outline);border-radius:4px;
padding:12px 14px;margin:var(--forge-spacing-medium) 0}
.evalrow{display:flex;align-items:center;gap:9px;margin:0;text-transform:none;
letter-spacing:0;font:400 13.5px/1.4 Roboto,sans-serif;
color:var(--forge-theme-text-high);cursor:pointer}
.evalrow input{width:auto;margin:0;flex:0 0 auto}
.boolrow{display:flex;align-items:center;gap:9px;margin:0;padding:7px 0;
text-transform:none;letter-spacing:0;font:400 13px/1.4 Roboto,sans-serif;
color:var(--forge-theme-text-high);cursor:pointer}
.boolrow input{width:auto;margin:0;flex:0 0 auto}
/* ---- diff view -------------------------------------------------------------------
   Two number gutters and a code column, which is what makes a line number in a review
   comment mean something. The gutters are `user-select:none` so copying a hunk gives
   you the code and not a column of digits - the single most annoying thing about a
   home-made diff view. */
.difftable{border:1px solid var(--forge-theme-outline);border-radius:4px;overflow:auto;
max-height:640px;margin-bottom:var(--forge-spacing-medium);
background:var(--forge-theme-surface)}
.difftable table{width:100%;border-collapse:collapse;
font:12.5px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace}
.difftable td{padding:0;border:0;white-space:pre}
.difftable td.dln{width:1%;min-width:44px;text-align:right;padding:0 10px;
color:var(--d-ln-fg);user-select:none;-webkit-user-select:none;
border-right:1px solid var(--forge-theme-outline)}
.difftable td.dcode{padding:0 12px;width:100%;overflow-wrap:normal}
.difftable tr.dadded td{background:var(--d-add-bg);color:var(--d-add-fg)}
.difftable tr.dadded td.dln{background:var(--d-add-ln)}
.difftable tr.dremoved td{background:var(--d-del-bg);color:var(--d-del-fg)}
.difftable tr.dremoved td.dln{background:var(--d-del-ln)}
.difftable tr.dhunkrow td{background:var(--d-hunk-bg);color:var(--d-hunk-fg);
font-size:11.5px;padding-top:3px;padding-bottom:3px}
.dplus{color:var(--d-plus);font-weight:600}
.dminus{color:var(--d-minus);font-weight:600}
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
/* `a.btn` rides along with `button` so a real download link can look like the buttons beside it.
   A download is one of the few things better done as an anchor than a click handler - the
   browser handles the filename and the save dialog - but it must not read as body text next to
   two actual buttons. inline-flex + the line-height reset keep an anchor the same height as a
   button, which padding alone does not. */
button,a.btn{background:var(--forge-theme-primary);color:var(--on-accent);border:0;padding:9px 16px;border-radius:4px;
font-size:13px;font-weight:500;cursor:pointer;letter-spacing:.02em}
a.btn{display:inline-flex;align-items:center;line-height:1;text-decoration:none;
font-family:inherit}
button:hover,a.btn:hover{filter:brightness(.92)}
/* NO DISABLED STYLE EXISTED ANYWHERE IN THIS APP until now, so every disabled button rendered in
   full primary colour with a pointer cursor and looked completely live. A reviewer asked why
   "Copy prompt" was enabled before they had typed anything - it was not; it just looked it.
   That affected every gated control: Ask again and Foundry re-upload when nothing is live, and
   the send button on Eval Review before approval.
   Opacity rather than new colours on purpose: the contrast checker skips translucent values, so
   this cannot introduce a contrast failure, and the disabled state stays legible. */
button:disabled,button:disabled:hover{opacity:.45;cursor:not-allowed;filter:none}
button.sec,a.btn.sec{background:var(--forge-theme-surface);color:var(--forge-theme-primary);
border:1px solid var(--forge-theme-outline-medium)}
button.sec:hover,a.btn.sec:hover{background:var(--forge-theme-primary-container-minimum);filter:none}
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
/* The dependent group, dimmed while it is closed. Dimmed rather than hidden: a control that
   vanishes takes its own explanation with it, and the reason it is unavailable is the whole
   point. `pointer-events` off stops a click landing on a disabled label. */
.depwrap{margin-top:var(--forge-spacing-medium)}
.fld.depoff{opacity:.45;pointer-events:none}
.fld.depoff *{cursor:not-allowed}
/* Label on the left, Copy Foundry response on the right. The button sits OUTSIDE the label
   deliberately - inside one, a click would also focus the textarea and the two actions would
   fight. Baseline alignment so the label and the button text sit on the same line. */
.fldhead{display:flex;align-items:baseline;gap:10px;margin-top:10px}
.fldhead label{flex:1 1 auto}
.fldhead button{flex:0 0 auto;font-size:12px;padding:4px 10px}
/* A derived field's value, shown as text. Sized to sit level with a real input so the
   form does not develop a step where the read-only field is. */
/* Knowledge-file picker. A dialog because ctrl/cmd-click on a multi-select is the least
   discoverable interaction on the web, and 42 files across 7 corpora will not fit inline. */
.kbmodal{position:fixed;inset:0;z-index:60;background:rgba(0,0,0,.45);
display:flex;align-items:center;justify-content:center;padding:24px}
.kbmodal[hidden]{display:none}
.kbbox{background:var(--forge-theme-surface);border-radius:6px;box-shadow:var(--shadow-pop);
padding:20px;width:min(560px,100%);max-height:min(74vh,640px);display:flex;flex-direction:column}
.kblist{overflow:auto;border:1px solid var(--forge-theme-outline);border-radius:4px;
padding:6px 4px;flex:1 1 auto;min-height:120px}
.kbgroup{font:500 11px/1.6 Roboto,sans-serif;text-transform:uppercase;letter-spacing:.06em;
color:var(--forge-theme-text-medium);padding:10px 10px 3px}
.kbrow{display:flex;align-items:center;gap:9px;padding:5px 10px;border-radius:3px;
font:400 13px/1.4 Roboto,sans-serif;color:var(--forge-theme-text-high);cursor:pointer;
text-transform:none;letter-spacing:0;margin:0}
.kbrow:hover{background:var(--forge-theme-primary-container-minimum)}
.kbrow input{width:auto;margin:0;flex:0 0 auto}
.kbrow.kball{border-bottom:1px solid var(--forge-theme-outline);border-radius:0;
margin-bottom:6px;padding-bottom:9px}
.kbacts{display:flex;gap:8px;justify-content:flex-end;margin-top:14px}
.roval{padding:7px 0;font-size:13px;color:var(--forge-theme-text-high);
font-weight:500;display:flex;align-items:center}
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
// WHAT ACTIVATES THE ASSISTANT: PROSE, AND ONLY PROSE.
//
// This used to also read the verdict dropdowns against a NEUTRAL table, which made a field value
// into a request for work. It is not one. Answer verdict = stale records what already happened;
// it cannot ask for a knowledge file to be rewritten, and treating it as if it could put
// transcripts into Eval Review with nothing to test.
//
// So the rule is now the same one a reader would guess from the form: an Ideal response under an
// exchange, or a Summary. Those two carry the "triggers changes" tag; the fields are attributes
// and may route the transcript, but they never queue an assistant. The server half of this is
// eval_batch.wants_change(), which was changed in step with it - two copies of this rule that
// disagree is how a transcript ends up in a batch nobody can act on.
function formAsksForChange(){
 for (const e of document.querySelectorAll('[data-ex]')) if (askedForChangeIn(e)) return true;
 const pf = document.getElementById('proposed');
 if (pf && proseTyped(pf.value)) return true;
 return false;
}
// Strip the review block's own header before deciding whether anything was written.
function proseTyped(v){
 return (v || '').replace(/^\s*\*\*Review\s*[\u2014-]\*\*.*$/m, '').trim().length > 0;
}
// An ideal response IDENTICAL to the answer that was given is not a change - it says the answer
// was already right. Without this, pressing Copy Foundry response and then deciding nothing was
// wrong left the button reading "Changes suggested", which would put the transcript into Eval
// Review to test a fix that does not exist.
function askedForChangeIn(ta){
 if(!proseTyped(ta.value)) return false;
 const card = ta.closest('.card');
 const src  = card && card.querySelector('.a');
 if(src && src.textContent.trim() === ta.value.trim()) return false;
 return true;
}
// Empty the two things that activate the assistant - the Ideal responses and the Summary - so
// the form records as a deliberate no-change review again.
//
// IT NO LONGER TOUCHES THE FIELDS. It used to reset every "Triggers changes" dropdown to a
// neutral value, on the old theory that a verdict could ask for work. Since the fields are
// attributes, resetting them here destroyed a reviewer's observations - Answer verdict = stale,
// the diagnosis, the kb_files they picked - to clear something those fields never caused.
//
// CONFIRMS FIRST. This is the only control on the page that can discard a paragraph somebody
// typed - an ideal response is often the most considered thing in the whole review - and an
// unconfirmed button next to the one you press to finish is a bad place to be one click out.
function clearChanges(btn){
 confirmThen(btn, 'Clear the ideal responses and summary?',
   'Empties every <b>Ideal response</b> and the <b>Summary</b>, so this records as '
   + '<b>no changes needed</b>. The verdict fields are left as they are. Typed text is '
   + 'discarded &mdash; there is no undo.',
   ()=>{
     document.querySelectorAll('[data-ex]').forEach(e => { e.value = ''; });
     const pf = document.getElementById('proposed');
     if (pf) pf.value = '';
     refreshMarkLabel();
     toast('Cleared \u2014 this now records as no changes needed');
   });
}
// ---- the four fields that DIRECT a change, gated on there being one ----------------------
// BP updates, Fix target, KB action and KB files describe work that prose has asked for. Set on
// their own they described a change nobody had described - and a ticked BP updates with no prose
// opens a Blueprint change request that says nothing about what should be different.
//
// THE GATE IS NOT PURELY "IS THERE PROSE". It also opens when these fields ALREADY hold values,
// because otherwise simply opening a transcript that recorded them without prose would clear a
// reviewer's work on page load - silent data loss triggered by reading. So the gate closes only
// while everything is empty, which is the fresh-transcript case the rule is for, and the
// "No changes & next" path clears them explicitly.
function depFieldEls(){
 const w = document.getElementById('depfields');
 return w ? [...w.querySelectorAll('.fld')] : [];
}
function depHasValues(){
 const bp = document.querySelector('[data-fm=bp_updates]');
 if (bp && bp.checked) return true;
 const kv = document.getElementById('kbvalue');
 if (kv && kv.value.trim()) return true;
 for (const k of ['fix_target','kb_action']) {
   const e = document.querySelector('[data-fm='+k+']');
   if (e && !['','none'].includes((e.value||'').trim().toLowerCase())) return true;
 }
 return false;
}
function clearDepFields(){
 const bp = document.querySelector('[data-fm=bp_updates]');
 if (bp) bp.checked = false;
 for (const k of ['fix_target','kb_action']) {
   const e = document.querySelector('[data-fm='+k+']');
   if (!e) continue;
   // Pick a neutral value the select actually offers - "" is not always an option.
   const opt = [...e.options].map(o=>o.value)
                  .find(v => ['','none'].includes((v||'').trim().toLowerCase()));
   if (opt !== undefined) e.value = opt;
 }
 // kb_files is three controls: the hidden value the form saves, the dialog checkboxes, and the
 // button that shows the count. Missing any leaves the picker claiming a selection that is gone.
 const kv = document.getElementById('kbvalue');
 if (kv) kv.value = '';
 if (typeof kbBoxes === 'function') kbBoxes().forEach(b => b.checked = false);
 const kbb = document.getElementById('kbbtn');
 if (kbb) kbb.innerHTML = 'Select\\u2026';
}
function syncDepFields(){
 const on = formAsksForChange() || depHasValues();
 depFieldEls().forEach(f => {
   f.classList.toggle('depoff', !on);
   f.querySelectorAll('input,select,button,textarea').forEach(c => {
     if (c.type === 'hidden') return;          // the saved value must stay readable
     c.disabled = !on;
   });
 });
 const h = document.getElementById('dephint');
 if (h) h.hidden = on;
}
function refreshMarkLabel(){
 const b = document.getElementById('markbtn');
 if (!b) return;
 const asks = formAsksForChange();
 b.textContent = (asks ? 'Changes suggested' : 'No changes') + ' & next \u2192';
 syncDepFields();
 const c = document.getElementById('clearbtn');
 if (c) {
   c.disabled = !asks;
   c.title = asks ? 'Put every verdict field back to its default and empty the prose'
                  : 'Nothing suggested yet';
 }
 b.title = asks
   ? 'Records the verdict and the changes requested. This transcript WILL appear under '
     + 'Eval Review, where the fix can be checked.'
   : 'Records that the answer was fine as-is. This transcript will NOT appear under Eval Review '
     + '\u2014 there is nothing to test.';
}
document.addEventListener('input', e=>{
 if (e.target.matches('[data-fm],[data-ex],#proposed')) refreshMarkLabel();
});
document.addEventListener('change', e=>{
 if (e.target.matches('[data-fm]')) refreshMarkLabel();
 if (e.target.id === 'kbvalue') refreshMarkLabel();
});
document.addEventListener('DOMContentLoaded', refreshMarkLabel);
document.addEventListener('DOMContentLoaded', syncDepFields);
async function saveDoc(path,then){const fields={},ex={};
const rv=document.querySelector('[data-fm=reviewer]');
if(rv&&rv.value){try{localStorage.setItem('lastReviewer',rv.value)}catch(e){}}
// A multi-select's `.value` is only its FIRST selected option, so reading every control the
// same way would silently drop all but one chosen kb_file. Comma-joined to match the format
// the field has always been stored in.
document.querySelectorAll('[data-fm]').forEach(e=>{
  fields[e.dataset.fm] = e.dataset.multi
    ? [...e.selectedOptions].map(o=>o.value).join(', ')
    : e.dataset.bool ? (e.checked ? 'yes' : '')
    : e.value;
});
document.querySelectorAll('[data-ex]').forEach(e=>ex[e.dataset.ex]=e.value);
const proposed=(document.getElementById('proposed')||{}).value||'';
const r=await post('/save',{path,fields,exchanges:ex,proposed});
if(r.ok){toast('Saved to '+r.path);if(then)location.href=then}else toast(r.error||'Save failed',false)}
// Handing off and deciding are mutually exclusive. If either routing field names somebody, the
// transcript is THEIRS now - marking it reviewed would record your verdict on work you have
// just given away, and it would also pull it back out of their queue, which is the opposite of
// what setting the field was for. So the button refuses and says which field to clear.
// Checked at click time rather than by disabling the button, because the selects can change
// after the page renders and a button that is enabled-then-silently-inert is worse.
// A fix in a `Docusaurus-` file needs Blueprint updating too, so the box ticks itself.
//
// Those knowledge files are DERIVED from Blueprint and re-generated from it. A fix made only in
// the knowledge file survives until the next reconciliation and is then silently deleted - the
// agent answers correctly for a while, then regresses, with the transcript long since closed and
// nobody watching. That is a worse outcome than never having fixed it, because it looks handled.
//
// Ticks, never unticks: a reviewer who knows the Blueprint page is already right can turn it off,
// and this must not fight them.
(function(){
 const kb=document.getElementById('kbvalue');
 const bp=document.querySelector('[data-fm=bp_updates]');
 if(!kb||!bp) return;
 const check=()=>{
   const derived=(kb.value||'').split(',').map(s=>s.trim())
     .filter(s=>s.split('/').pop().startsWith('Docusaurus-'));
   if(!derived.length||bp.checked) return;
   bp.checked=true;
   toast('BP updates ticked \u2014 '+derived.length+' Docusaurus file(s) are derived from '
     +'Blueprint, so a fix there alone gets reverted');
 };
 // The hidden input is set by the dialog's OK, which does not fire `change` on its own.
 const ok=window.kbOk;
 if(ok) window.kbOk=function(){ok.apply(this,arguments); check();};
 check();
})();

// `action_status` follows from `kb_action` for the two mechanical values, so a reviewer is not
// asked a question whose answer is already on the form:
//
//     kb_action none/blank  -> none-needed   nothing has to change
//     kb_action add/update/split -> open     a change is required and has not been made
//
// The other two are NOT derivable and are left alone:
//     applied  is a claim that the work was done - Claude sets it after doing it
//     wontfix  is a decision to not act, and needs a reason in `notes`
//
// So it never overwrites applied or wontfix. Deriving those would either lie about work having
// been done or silently discard somebody's decision.
(function(){
 const ka=document.querySelector('[data-fm=kb_action]');
 const as=document.querySelector('[data-fm=action_status]');
 if(!ka||!as) return;
 ka.addEventListener('change',()=>{
   if(as.value==='applied'||as.value==='wontfix') return;
   const want=(!ka.value||ka.value==='none')?'none-needed':'open';
   if(as.value===want) return;
   as.value=want;
   toast('Action status set to '+want+' — follows from KB action');
 });
})();

// Reassigning to a DIFFERENT agent is a routing finding by definition: the content was fine,
// the wrong agent got the question. So the diagnosis follows from the reassignment rather than
// being a second thing to remember - and getting it wrong sends the fix to the wrong place,
// since `routing-only` means "do not edit a knowledge file for this".
//
// Only fires when the target differs from the agent that actually answered. Reassigning to the
// same agent is not a routing problem, and would be a strange thing to record at all.
// A reviewer who then picks a different diagnosis keeps it - this defaults, it does not enforce.
(function(){
 const ra=document.querySelector('[data-fm=reassign_to]');
 const dg=document.querySelector('[data-fm=diagnosis]');
 if(!ra||!dg) return;
 const current=(document.body.dataset.agent||'').trim();
 ra.addEventListener('change',()=>{
   const to=(ra.value||'').trim();
   if(!to||to===current) return;
   if(dg.value==='routing-only') return;
   dg.value='routing-only';
   toast('Diagnosis set to routing-only — reassigned away from '+(current||'this agent'));
 });
})();

// ---- knowledge-file picker dialog ---------------------------------------------------------
// OK commits, Cancel reverts. The checkbox state is snapshotted on open so Cancel can put it
// back - without that, ticking six boxes and pressing Cancel would leave them ticked, and the
// hidden value would disagree with what the dialog shows the next time it opens.
let KB_SNAP = null;
// The master checkbox is itself a checkbox inside the modal, so it has to be excluded or it
// would toggle itself and be counted as a file.
function kbBoxes(){return [...document.querySelectorAll('#kbmodal input[type=checkbox]')]
  .filter(b=>b.id!=='kball')}
function kbAll(master){kbBoxes().forEach(b=>b.checked=master.checked); kbSyncAll()}
// Keeps the master honest as individual boxes are ticked: checked when all are, indeterminate
// when some are. Without the indeterminate state a half-selected list shows an empty master,
// which reads as "nothing is selected".
function kbSyncAll(){
 const all=kbBoxes(), n=all.filter(b=>b.checked).length, m=document.getElementById('kball');
 if(!m) return;
 m.checked = n===all.length && n>0;
 m.indeterminate = n>0 && n<all.length;
}
function kbOpen(){
 KB_SNAP = kbBoxes().map(b=>b.checked);
 kbSyncAll();
 document.getElementById('kbmodal').hidden = false;
 const first = kbBoxes()[0]; if(first) first.focus();
}
function kbClose(){document.getElementById('kbmodal').hidden = true}
function kbCancel(){
 if(KB_SNAP) kbBoxes().forEach((b,i)=>b.checked = KB_SNAP[i]);
 kbSyncAll();
 kbClose();
}
function kbOk(){
 const picked = kbBoxes().filter(b=>b.checked).map(b=>b.value);
 document.getElementById('kbvalue').value = picked.join(', ');
 const btn = document.getElementById('kbbtn');
 if(btn) btn.innerHTML = picked.length ? 'Selected (' + picked.length + ')' : 'Select\u2026';
 kbClose();
}
// Escape cancels, and a click on the backdrop cancels - both are what a dialog is expected to
// do, and neither should COMMIT, since the click that dismissed it was not an OK.
document.addEventListener('keydown', e=>{
 const m = document.getElementById('kbmodal');
 if(e.key === 'Escape' && m && !m.hidden){ e.preventDefault(); kbCancel(); }
});
document.addEventListener('click', e=>{
 const m = document.getElementById('kbmodal');
 if(m && !m.hidden && e.target === m) kbCancel();
});
// Delegated, because the rows are rendered server-side and there are 42 of them.
document.addEventListener('change', e=>{
 if(e.target.matches('#kbmodal .kblist input[type=checkbox]')) kbSyncAll();
});

function handedOff(){
 const s=(document.querySelector('[data-fm=suggested_to]')||{}).value||'';
 const r=(document.querySelector('[data-fm=reassign_to]')||{}).value||'';
 return [s.trim()&&['Suggested to',s.trim()], r.trim()&&['Reassign to',r.trim()]].filter(Boolean);
}
async function markAndNext(path,next){
 const off=handedOff();
 if(off.length){
   toast(off.map(o=>o[0]+' = '+o[1]).join(' and ')
     +' — use Suggest & next, or clear it to keep this one', false);
   return;
 }
 // Directions for a change that is not being requested are not records - they are wrong. A
 // transcript marked "no changes" must not carry a Fix target, a KB action, KB files or a
 // ticked BP updates, or the batch would try to act on it.
 if (!formAsksForChange()) clearDepFields();
 document.querySelector('[data-fm=review_status]').value='reviewed';
 await saveDoc(path,next)}
// Suggest = "this is not my call." `reviewer` stays as YOU - suggesting is still something you
// did, and blanking it lost the only record of who looked at the transcript. What moves the work
// is `suggested_to` (a person) or `reassign_to` (an agent), which is also what puts it in their
// queue. One of them has to be set, or the suggestion has no destination and sits where it is.
async function suggestAndNext(path,next){
 const off=handedOff();
 if(!off.length){
   toast('Set Suggested to (a person) or Reassign to (an agent) first — a suggestion needs '
     +'somewhere to go', false);
   return;
 }
 const rv=document.querySelector('[data-fm=reviewer]');
 if(rv&&!rv.value){toast('Pick a name in Reviewer first',false);return}
 document.querySelector('[data-fm=review_status]').value='suggested';
 await saveDoc(path,next)}
// Re-review RE-OPENS a transcript; it does not record a verdict. So the status goes back to
// `pending` and the verdict fields are left for the reviewer to fill in again - the point is to
// look afresh, and a button that jumped straight to `reviewed` recorded a decision nobody had
// made yet.
//
// It does NOT touch `review_round`, which used to be incremented here. The round is derived from
// what is on origin/main, so once a verdict is merged the next one is already on the following
// round - computing it in two places was how they could disagree.
async function reReview(path){
 const st=document.querySelector('[data-fm=review_status]');
 st.value='pending';
 await saveDoc(path);
 toast('Re-opened for a fresh look — record a verdict when done');
}
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
   +'<br><br>A recovery point is created first, and the output explains how to use it.',
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
   +'branch is behind main it is brought up to date first.<br><br><b>Any knowledge files in '
   +'this request are then uploaded to Foundry and verified.</b> This is the whole make-it-live '
   +'action, so the agents change as soon as it finishes.',
   ()=>prDo(btn,'merge',number));
}
// Blueprint merges via GitHub's auto-merge, not by waiting here: its CI takes minutes and a
// plain merge would be refused for being behind the checks.
function bpMerge(btn,number,title){
 confirmThen(btn,'Queue Blueprint #'+number+' to merge when checks pass?',
   '<code>'+title+'</code><br><br>GitHub merges it the moment Blueprint\u2019s CI passes, so there is '
   +'do not have to wait here. Squash merge, branch deleted.<br><br><b>Merge the knowledge '
   +'request as well</b> \u2014 most indexed knowledge is derived from Blueprint, so shipping '
   +'one without the other leaves a fix the next reconciliation undoes.',
   ()=>prDo(btn,'bp-merge',number));
}
function prOverride(btn,number,title,checks){
 const warn = checks==='failing' ? '<b>Checks are failing on this one.</b><br>'
            : checks==='running' ? 'Checks are still running.<br>' : '';
 confirmThen(btn,'Merge #'+number+' bypassing review?',
   warn+'<code>'+title+'</code><br><br>This skips the required approval \u2014 the one action '
   +'here that removes a safety gate rather than passing through it, and reasonable only on '
   +'own work.<br><br>Rebases onto main and deletes the branch, brings it up to date '
   +'first if needed, then <b>uploads any knowledge files to Foundry and verifies them</b>. '
   +'The agents change as soon as it finishes.',
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
     +'Part 2.<br><br>If the assistant prompt has not been run yet, the change request will '
     +'carry verdicts with no fix behind them \u2014 it will look complete, merge, and the '
     +'agents will keep giving the answers just reviewed.<br><br>Have the assistant '
     +'instructions been completed?'
   : 'No transcript in this batch is waiting on a knowledge update, so there is nothing for '
     +'the assistant to have done.<br><br>Send it in?';
 // A DISABLED checkbox still reports checked:true, so reading .checked alone would re-run the
 // eval every time Process Part 2 was pressed after the first. Disabled means "already run for
 // this content" - so the press should go on to the change request instead.
 const _cb = document.getElementById('doeval');
 const wantEval = !!(_cb && _cb.checked && !_cb.disabled);
 // Two different presses, so two different notes. The old text said "then puts Foundry back",
 // which stopped being true when the content started staying live for adjacent phrasings.
 const evalNote = wantEval
   ? '<br><br><b>The check runs first.</b> It saves the work in progress, uploads the changed knowledge '
     +'files and asks the agents this batch\u2019s questions. The content STAYS live afterwards '
     +'so other phrasings can be tried. Nothing is sent in until the answers have been read.'
   : (_cb && _cb.disabled
      ? '<br><br>The check has already run for this version, so this goes straight on to the '
        +'change request \u2014 and takes the eval content back out of Foundry.'
      : '');
 confirmThen(btn, n ? 'Has the assistant finished the knowledge updates?' : 'Send these in?',
   detail + evalNote, ()=>{ wantEval ? runEval(btn) : gitDo('pr'); });
}

// The eval is a GATE, not a step that flows into the send. It runs, shows the answers, and
// stops - because the entire point is a human deciding whether the change is good, and a flow
// that continued automatically would be an eval nobody read.
//
// Minutes long, so the panel says what is happening rather than looking hung. Foundry is put
// back by the script's own final phase, so a failure part-way still restores.
function runEval(btn){
 const out=document.getElementById('gitout');
 const was=btn.textContent;
 btn.disabled=true; btn.textContent='Checking\u2026';
 stage('eval','run');
 if(out){out.style.display='block';
   out.textContent='Saving work in progress, uploading the candidate files, asking the agents.\n'
     +'This takes a few minutes - two Bedrock syncs plus one question at a time.\n'
     +'Foundry is restored automatically when it finishes.\n\nWorking\u2026';}
 fetch('/git',{method:'POST',headers:{'Content-Type':'application/json'},
               body:JSON.stringify({action:'eval'})})
  .then(r=>r.json()).then(d=>{
    if(out){out.textContent=d.output||'(no output)';}
    // `you`, not `done` - the eval has run but the step is not finished until the answers have
    // been read. gitDo('pr') is what finally ticks it, from the Eval Review screen.
    stage('eval', d.ok===false ? 'fail' : 'you');
    btn.disabled=false; btn.textContent=was;
    // STRAIGHT TO THE DEDICATED SCREEN. The answers used to be left in this panel with two
    // buttons under them, which is where a reviewer failed to find anything to approve: the
    // panel's job is git output, and per-transcript approval was not expressible there at all.
    if(d.ok!==false){
      const host=btn.parentNode;
      if(!host.querySelector('.evalgate')){
        const g=document.createElement('div');
        g.className='evalgate';
        g.innerHTML='<div class="bar bnr-note" style="margin:12px 0 8px">'
          +'<b>The check has run. Now approve it, one transcript at a time.</b> '
          +'Nothing has been sent.</div>'
          +'<button onclick="location.href=\'/evalreview\'">Go to Eval Review</button>';
        host.appendChild(g);
      }
      location.href='/evalreview';
    }
  })
  .catch(e=>{ if(out){out.textContent='The check failed to run: '+e
    +'\n\nIf it had already uploaded, restore with:\n'
    +'  python3 scripts/eval_batch.py --restore-only .eval/<newest>';}
    stage('eval','fail');
    btn.disabled=false; btn.textContent=was; });
}

// When the answers are wrong, the batch goes back to pending so the work can continue. Only the
// STATUS moves - every ideal response, summary and field value is kept, because the verdict was
// premature rather than wrong to have been written.
//
// IT MUST VISIBLY RESET PART 2. The first version wrote its output into the panel and changed
// nothing else, so the stages still read as they had, the eval gate was still sitting there, and
// the banner still described a batch that no longer existed. A reviewer clicked it and reported
// that it "didn't seem to do anything" - the transcripts HAD gone back to pending, silently.
// A state change nobody can see is indistinguishable from a no-op.
function resetPending(btn){
 confirmThen(btn,'Put this batch back to pending?',
   'Clears the reviewed status on the transcripts in this batch so work can continue on '
   +'them. Ideal responses, summaries and field values are all kept \u2014 only the status '
   +'changes.<br><br>Part 2 resets: the check will need to run again once the answers are '
   +'right.',
   ()=>gitDo('reset-pending').then(()=>resetPart2()));
}

// ---- EVAL REVIEW screen ----
// One checkbox per replayed exchange. Each click persists immediately rather than on a Save:
// the reviewer is reading long answers and will scroll, open the transcript, come back - and an
// approval that only existed in the DOM would be lost the first time they did.
function evSet(cb,key){
 const card=document.getElementById('c-'+key);
 if(card) card.classList.toggle('evok',cb.checked);
 post('/evalapprove',{action:'one',key:key,on:cb.checked}).then(evTally);
}
function evAll(on){
 document.querySelectorAll('.evcard input[type=checkbox]').forEach(cb=>{
   cb.checked=!!on; const c=cb.closest('.evcard'); if(c)c.classList.toggle('evok',!!on);});
 post('/evalapprove',{action:'all',on:!!on}).then(evTally);
}
// The send button and the banner both depend on ALL of them, so they are recomputed from the
// server's count rather than from the checkboxes - the two can disagree if a knowledge file
// changed underneath, in which case the server drops every approval and the page must say so.
function evTally(r){
 if(!r||r.ok===false)return;
 const st=document.getElementById('evstate');
 if(st) st.innerHTML = r.allOk
   ? '<b>All '+r.nTot+' approved.</b> The batch can be sent in.'
   : '<b>'+r.nOk+' of '+r.nTot+' approved.</b> Tick every transcript whose answer is right. '
     +'Anything left unticked is not ready, and the send stays shut.';
 const send=document.getElementById('evsend');
 if(send){send.disabled=!r.allOk;
   send.title = r.allOk ? '' : 'Approve every transcript first';}
}
// Ask an adjacent phrasing against the live candidate content. The answer is appended, never
// substituted for the scripted one - consistency across phrasings is the thing being judged.
// TWO HAZARDS, BOTH WARNED RATHER THAN BLOCKED.
//  1. The answer replaces what is in Now - so unsaved {{...}} markup is lost. That is the one
//     that costs work, so it leads.
//  2. With nothing live, the answer comes from the PUBLISHED content and says nothing about the
//     change under review. Worth knowing, not worth forbidding: a reviewer may want to see what
//     the agent says today, and the answer is labelled accordingly in Earlier either way.
function evAsk(btn,key,agent){
 const card=btn.closest('.evcard'), box=card.querySelector('.evqbox');
 const q=(box.value||'').trim();
 if(!q){toast('Type a question first');return}
 const nowBox=card.querySelector('.evnowbox');
 const edited=nowBox && (nowBox.value||'')!==(nowBox.dataset.orig||'');
 const notLive=btn.dataset.live==='0';
 const nStale=parseInt(btn.dataset.stale||'0',10)||0;
 if(edited||notLive||nStale){
   const parts=[];
   if(edited) parts.push('<b>Edits to Now will be replaced</b> by the new answer, '
     +'including any <code>{{...}}</code> typed there. Copy the prompt first to '
     +'to keep them.');
   if(notLive) parts.push('<b>Nothing is live in Foundry</b>, so the answer will come from the '
     +'PUBLISHED content — it will not reflect the pending knowledge edits. Use '
     +'<b>Foundry re-upload</b> first to test those.');
   else if(nStale) parts.push('<b>'+nStale+' knowledge file(s) have changed since the last '
     +'upload</b>, so the answer will come from the PREVIOUS round, not the latest edits — '
     +'which looks exactly like the fix not working. Press <b>Foundry re-upload</b> first.');
   confirmThen(btn,'Ask again?',parts.join('<br><br>'),()=>evAskGo(btn,key,agent,q));
   return;
 }
 evAskGo(btn,key,agent,q);
}
function evAskGo(btn,key,agent,q){
 const card=btn.closest('.evcard');
 // An agent round-trip is seconds, and the reviewer is staring at a screen that looks the same
 // as before. So: the button counts, the answer is stamped with the server's own time, and the
 // new block flashes. Without the stamp two Asks produced identical-looking blocks and there was
 // no way to tell the second one had run at all.
 const was=btn.textContent; btn.disabled=true;
 let secs=0; btn.textContent='Asking… 0s';
 const tick=setInterval(()=>{btn.textContent='Asking… '+(++secs)+'s'},1000);
 const done=()=>{clearInterval(tick); btn.disabled=false; btn.textContent=was};
 post('/evalask',{key:key,agent:agent,question:q}).then(r=>{
   done();
   if(r.ok===false){toast(r.output||'Could not ask');return}
   // Same shuffle the server does on a reload: whatever is under "Now" becomes history, and the
   // fresh answer takes its place with its own stamp. Doing it here as well means the page does
   // not have to reload to stay consistent with what a refresh would render.
   const now=card.querySelector('.evafter'), host=card.querySelector('.evvars');
   const oldLab=now.querySelector('.evlab').textContent||'';
   const oldStamp=(oldLab.match(/\(([^)]+)\)/)||[])[1]||'';
   const prev=document.createElement('div'); prev.className='evvar';
   prev.innerHTML='<div class=evlab></div><div class=evvq></div><pre></pre>';
   prev.querySelector('.evlab').textContent=oldStamp+' · superseded';
   prev.querySelector('.evvq').textContent=card.querySelector('.evqbox').dataset.lastAsked||'';
   prev.querySelector('pre').textContent=now.querySelector('pre').textContent;
   let hdr=host.querySelector('.evlab,summary');
   host.appendChild(prev);
   if(!hdr){const h=document.createElement('div'); h.className='evlab';
     h.style.marginTop='12px'; h.textContent='Earlier'; host.insertBefore(h,prev);}
   const lab=now.querySelector('.evlab');
   lab.textContent='Now ('+(r.at||'')+')';
   if(r.pct!=null){
     const t=r.pct>=70?'ok':(r.pct>=40?'warn':'bad');
     const chip=document.createElement('span');
     chip.className='evmatch '+t;
     chip.title='Share of the substantive words in the ideal response that appear in this answer. '
       +'A word-overlap hint only \u2014 it cannot tell a paraphrase from a contradiction, so '
       +'read the answer.';
     chip.textContent='Match '+r.pct+'% against the ideal response';
     lab.appendChild(chip);
   }
   now.querySelector('pre').textContent=r.answer||'(no answer returned)';
   card.querySelector('.evqbox').dataset.lastAsked=r.question||q;
   now.classList.add('isnew'); setTimeout(()=>now.classList.remove('isnew'),2000);
   now.scrollIntoView({block:'nearest',behavior:'smooth'});
   toast('Answered at '+(r.at||'now')+(secs?' — took '+secs+'s':''));
 }).catch(e=>{done(); toast('Could not ask: '+e)});
}
// Back to what the transcript actually asked. Cheap to provide and the alternative is asking
// someone to remember an exact wording they have since typed over three times.
// Same rule as Reset under Now: nothing typed, nothing to reset. Gated for consistency - a
// live Reset beside a dead one invites the reader to wonder which of them is broken.
function evQEdited(box){
 const rst=box.closest('.evcard').querySelector('.evresetq');
 if(!rst)return;
 const changed=(box.value||'')!==(box.dataset.orig||'');
 rst.disabled=!changed;
 if(changed) rst.removeAttribute('title');
}
function evResetQ(btn){
 const box=btn.closest('.evcard').querySelector('.evqbox');
 box.value=box.dataset.orig||''; evQEdited(box); box.focus();
}
// Take the candidate content out of production. Minutes long - it is a second upload plus a
// Bedrock sync - so the button says what it is doing rather than looking hung.
function evRemove(btn){
 confirmThen(btn,'Remove the eval content from Foundry?',
   'Puts the published content back, so the agents stop answering from the candidate files. '
   +'Knowledge edits and approvals are untouched — this only affects what is live in '
   +'Foundry, and it goes back up permanently when the change is merged.',
   ()=>{
     const was=btn.textContent; btn.disabled=true; btn.textContent='Removing…';
     const out=document.getElementById('gitout');
     if(out){out.style.display='block';
       out.textContent='Uploading the previous content back and waiting for the sync.\nA few minutes.\n\nWorking…';}
     return post('/evalremove',{}).then(r=>{
       if(out){out.textContent=r.output||'(no output)';}
       btn.disabled=false; btn.textContent=was;
       if(r.ok && !r.live){ location.reload(); }
     });
   });
}
// Editing NOW is how defects get marked, so the Copy button stays shut until something has
// actually been typed - a prompt built from an untouched answer is just the transcript again.
function evNowEdited(box){
 const card=box.closest('.evcard');
 const changed=(box.value||'')!==(box.dataset.orig||'');
 // Both buttons are gated on the same fact: has anything been typed. Copy prompt because a
 // prompt built from an untouched answer is only the transcript again, and Reset because there
 // is nothing to reset to.
 const btn=card.querySelector('.evcopy'), rst=card.querySelector('.evresetnow');
 btn.disabled=!changed;
 if(rst) rst.disabled=!changed;
 if(changed){btn.removeAttribute('title'); if(rst) rst.removeAttribute('title');}
 const marks=(box.value.match(/\{\{[\s\S]*?\}\}/g)||[]).length;
 card.querySelector('.evmarks').textContent = marks ? marks+' marked' : (changed?'edited':'');
 const tag=card.querySelector('.evedited');
 if(tag) tag.hidden=!changed;
}
// Back to the agent's own words. The stored answer was never touched, so this is just putting
// the scratch copy back - nothing is recovered or lost.
function evResetNow(btn){
 const card=btn.closest('.evcard'), box=card.querySelector('.evnowbox');
 box.value=box.dataset.orig||'';
 evNowEdited(box);
 box.focus();
}
// Minutes long - an upload plus a Bedrock sync - so it counts, and it says plainly when the new
// content is live, because "Ask again" before then silently answers from the PREVIOUS round and
// looks like the fix not working.
function evReupload(btn){
 confirmThen(btn,'Re-upload the knowledge files to Foundry?',
   'Pushes every changed knowledge file over the live eval content, so Ask again tests the '
   +'latest edits. A few minutes. The restore point is kept, so Remove evals still puts the '
   +'published content back.',
   ()=>{
     const was=btn.textContent; btn.disabled=true;
     let n=0; btn.textContent='Uploading… 0s';
     const tick=setInterval(()=>{btn.textContent='Uploading… '+(++n)+'s'},1000);
     const out=document.getElementById('gitout');
     if(out){out.style.display='block';
       out.textContent='Uploading the current knowledge files and waiting for the sync.\nA few minutes.\n\nWorking…';}
     return post('/evalreupload',{}).then(r=>{
       clearInterval(tick); btn.disabled=false; btn.textContent=was;
       if(out){out.textContent=r.output||'(no output)';}
       toast(r.ok ? 'Live — Ask again to test the new edits'
                  : 'Re-upload did not fully land — read the output');
     }).catch(e=>{clearInterval(tick); btn.disabled=false; btn.textContent=was;
       toast('Re-upload failed: '+e)});
   });
}
function evCopyPrompt(btn,key){
 const box=btn.closest('.evcard').querySelector('.evnowbox');
 const was=btn.textContent; btn.disabled=true; btn.textContent='Building…';
 post('/evalprompt',{key:key,edited:box.value||''}).then(r=>{
   btn.disabled=false;
   if(r.ok===false){btn.textContent=was; toast(r.output||'Could not build the prompt'); return}
   copyText(r.prompt, btn, was);
 }).catch(e=>{btn.disabled=false; btn.textContent=was; toast('Could not build it: '+e)});
}
// Shared clipboard path with the Part 2 prompt button: navigator.clipboard needs a secure
// context, and 127.0.0.1 counts - but a browser with the permission denied still has to work,
// so the textarea fallback stays.
function copyText(text, btn, was){
 const done=ok=>{btn.textContent = ok ? '\u2713 Copied — ready to paste to an assistant'
                                      : 'Could not copy — select the text below instead';
   if(!ok){const ta=document.createElement('textarea'); ta.value=text;
     ta.style.cssText='width:100%;margin-top:8px;font:inherit'; ta.rows=8;
     btn.parentNode.appendChild(ta); ta.select();}
   else setTimeout(()=>{btn.textContent=was},4000);};
 if(navigator.clipboard&&window.isSecureContext){
   navigator.clipboard.writeText(text).then(()=>done(true),()=>done(false));
 } else {
   const ta=document.createElement('textarea'); ta.value=text;
   ta.style.position='fixed'; ta.style.opacity='0'; document.body.appendChild(ta); ta.select();
   let ok=false; try{ok=document.execCommand('copy')}catch(e){ok=false}
   document.body.removeChild(ta); done(ok);
 }
}
function evSend(btn){
 confirmThen(btn,'Send the batch in?',
   'Opens the change request(s) for the knowledge updates and verdicts. On merge, the '
   +'knowledge files are published to Foundry and the agents change.',
   ()=>post('/git',{action:'pr'}).then(r=>{
     const o=document.getElementById('gitout');
     if(o){o.style.display='block'; o.textContent=r.output||'(no output)';}
   }));
}
function evReset(btn){
 confirmThen(btn,'Put the batch back to pending?',
   'Clears the reviewed status on every transcript in this batch so work can continue. '
   +'Ideal responses, summaries and field values are all kept — only the status changes, and '
   +'Part 2 resets.',
   ()=>post('/git',{action:'reset-pending'}).then(r=>{
     const o=document.getElementById('gitout');
     if(o){o.style.display='block'; o.textContent=r.output||'(no output)';}
     setTimeout(()=>{location.href='/save'},900);
   }));
}

// Put Part 2 back to its starting state. Called after a reset, and deliberately not merged into
// gitDo's generic refresh: every other action moves the batch FORWARD, and only this one
// unwinds it.
function resetPart2(){
 ['ai','eval','push','pr'].forEach(s=>{
   const el=document.querySelector('#prog li[data-stage='+s+']');
   if(el&&!el.classList.contains('none')){
     el.classList.remove('run','done','fail','you'); el.classList.add('wait');}});
 document.querySelectorAll('.evalgate').forEach(g=>g.remove());
 const cb=document.getElementById('doeval'); if(cb) cb.checked=true;
 const b=document.querySelector('[data-ai-pending]');
 // Restore the label the server derived, not a literal - the button's text depends on where
 // the batch is, so a hardcoded string here would rename it wrongly after a reset.
 if(b){b.disabled=false; b.textContent=b.dataset.label||'Process';}
}
function copyPrompt(btn){
 const text=window.AI_PROMPT||'';
 const done=ok=>{btn.textContent = ok ? '\u2713 Copied — ready to paste to an assistant'
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
 const s=document.getElementById('outsub');
 if(!s)return;
 // The heading no longer changes - see where it is rendered. Only the sub-line moves, because
 // which of the two things the panel is showing is still worth saying.
 if(action==='diff'){
   s.textContent='Pending edits are reflected in color: Green indicates addition, '
     +'Red indicates removal.';
 } else {
   // Impersonal for the same reason: "what the step you just ran reported" and "paste this to
   // your AI assistant" both address the reader rather than describing the panel.
   s.textContent='Output from the step just run. If it failed, this text can be passed to an '
     +'AI assistant.';}
}
function stage(name,state){const el=document.querySelector('#prog li[data-stage='+name+']');
 if(!el||el.classList.contains('none'))return;
 el.classList.remove('wait','run','done','fail','you'); el.classList.add(state);}
// No `branch` field any more — the branch is chosen server-side per sitting and never shown.
async function gitDo(action,extra){const msg=(document.getElementById('cmsg')||{}).value||'';
// Reaching the send is the reviewer having read the answers, which is the only thing that
// completes the eval step. Ticked here rather than in runEval for that reason.
if(action==='pr'){stage('eval','done'); stage('push','run')}
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
 const badge=document.querySelector('nav.side a[href="/save"] .ct');
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
// The action row is always on the page; only availability moves. Both selection actions need at
// least one row, Import needs none - it names its own rows from the file.
function ckSync(){const n=ckSel().length;
 const set=(id,off,why)=>{const b=document.getElementById(id); if(!b) return;
                          b.disabled=off; b.title=off?why:''};
 set('ckmark',  !n, 'Select at least one pending transcript');
 set('ckexport',!n, 'Select at least one pending transcript');
 const el=document.getElementById('ckelig');
 if(el) el.textContent = n ? (n+' selected · as '+(ckWho()||'nobody — pick a name on a transcript'))
                           : 'Pending rows only';
}
// Every box, not just the visible ones - see the ckall handler for why.
function clearCk(){document.querySelectorAll('input.ck').forEach(c=>c.checked=false);
 const a=document.getElementById('ckall'); if(a)a.checked=false; ckSync()}
async function bulkReview(){
 const paths=ckSel().map(c=>c.value);
 if(!paths.length){toast('Nothing selected',false);return}
 const who=ckWho();
 if(!who){toast('Open any transcript and pick a name first',false);return}
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
// ---- CSV round-trip for ideal responses ----------------------------------------------------
// Four columns: transcript id, question, answer, ideal response. The first three are identity and
// carry (DO NOT MODIFY) in their headers; only the ideal response is read back.
async function csvExport(){
 const paths=ckSel().map(c=>c.value);
 if(!paths.length){toast('Select at least one transcript',false);return}
 const r=await post('/csvexport',{paths});
 if(!r.ok){toast(r.error||'export failed',false);return}
 // Built client-side as a Blob rather than served as a download response: the selection lives
 // in the browser, and a GET carrying dozens of paths in its query string would hit URL limits.
 const b=new Blob([r.csv],{type:'text/csv;charset=utf-8'});
 const u=URL.createObjectURL(b), a=document.createElement('a');
 a.href=u; a.download=r.name; document.body.appendChild(a); a.click();
 a.remove(); URL.revokeObjectURL(u);
 let m=r.rows+' exchange(s) from '+paths.length+' transcript(s)';
 if(r.skipped&&r.skipped.length) m+=' — '+r.skipped.length+' skipped';
 toast(m);
}
// Import OVERWRITES an ideal response that is already there, and the file was authored somewhere
// else - so the warning comes BEFORE the file picker, not after the read. Cancelling here costs
// nothing; cancelling after a write is not on offer.
function csvImportPick(btn){
 confirmThen(btn,'Import ideal responses from a CSV?',
   'Replaces the existing Ideal response on every exchange the file matches. '
   +'Pending transcripts only; blank cells and unmatched rows are left alone.',
   ()=>document.getElementById('csvfile').click());
}
async function csvImport(input){
 const f=input.files&&input.files[0];
 input.value='';                                  // so re-picking the same file fires again
 if(!f) return;
 const text=await f.text();
 const r=await post('/csvimport',{csv:text});
 if(!r.ok){toast(r.error||'import failed',false);return}
 const n=(r.applied||[]).reduce((s,a)=>s+a[1].length,0);
 // The IGNORED rows are the interesting part of an import, not the applied ones - an edited
 // question column silently matches nothing, and a count with no detail would hide that.
 const det=[];
 if(r.applied&&r.applied.length) det.push('Applied:\n'+r.applied.map(
   a=>'  • '+a[0]+' — exchange '+a[1].join(', ')).join('\n'));
 if(r.unchanged) det.push(r.unchanged+' row(s) left alone (blank or identical ideal response)');
 if(r.ignored&&r.ignored.length) det.push('Ignored rows:\n'+r.ignored.map(
   x=>'  • line '+x[0]+': '+x[1]).join('\n'));
 if(r.skipped&&r.skipped.length) det.push('Skipped transcripts:\n'+r.skipped.map(
   x=>'  • '+x[0]+': '+x[1]).join('\n'));
 if(det.length) alert(det.join('\n\n'));
 toast(n?(n+' ideal response(s) imported'):'Nothing changed', n>0);
 if(n) location.reload();
}

// ---- seed the Ideal response from the answer that was actually given -------------------
// The point of the field is the ANSWER AS IT SHOULD HAVE READ, and most of a bad answer is
// usually fine - so editing the real one is the realistic way to produce it. Retyping the
// correct paragraphs to fix one wrong sentence is the friction that made this box get used for
// notes instead, which then made the Eval Review match score meaningless.
function copyFoundry(btn){
 const card = btn.closest('.card');
 const src  = card && card.querySelector('.a');
 const ta   = card && card.querySelector('textarea[data-ex]');
 if(!src || !ta){ toast('Could not find the response to copy',false); return }
 const put = () => {
   ta.value = src.textContent;
   // MUST bubble: the mark-button label is driven by a delegated listener on document, so a
   // non-bubbling event leaves the button saying "No changes" over a full ideal response.
   ta.dispatchEvent(new Event('input',{bubbles:true}));
   ta.focus(); ta.setSelectionRange(0,0); ta.scrollTop=0;
 };
 if(ta.value.trim())
   confirmThen(btn,'Replace what is in the box?',
     'The Foundry response overwrites the current text.', put);
 else put();
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
 // The header checkbox IS the clear-all, now that the button is gone - so unchecking it clears
 // every box, not only the visible ones. Otherwise a row selected before a filter was applied
 // stays selected invisibly, and the next export silently includes it.
 if(e.target.id==='ckall'){
   if(e.target.checked){ckList().forEach(c=>c.checked=true); ckSync()}
   else clearCk();
 }
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

// Single-word keys ON PURPOSE. Each has to match BOTH an element id (`f_<key>`) and a row
// data attribute read as `tr.dataset[key]`. A hyphenated attribute like `data-suggested-to`
// arrives as `dataset.suggestedTo`, so a snake_case key here would silently never match and
// the filter would appear to do nothing.
const FKEYS=['agent','ex','fb','status','sugg','routing','answer','diag','fix'];
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
// Filtering changes what counts as selected, so the buttons have to be re-derived here too.
// Without it, narrowing the list away from a selection leaves them enabled against nothing.
ckSync();
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
     em.textContent='Nothing is assigned \u2014 no transcript is waiting by name '
       +'and none of the owned agents has an open conversation.';
     ea.innerHTML=SHOW_ALL_LINK
       ? '<a href="/?all=1">Click on All Transcripts to see all transcripts.</a>'
       : '<button class=sec onclick="syncNow()">Sync transcripts</button>';
   } else if(mineOnly&&onlyDefaultStatus){
     em.innerHTML='Nothing assigned is <b>'+dflt.replace(/__/g,'')+'</b>. '
       +'There are '+total+' transcript(s) in total \u2014 remove the <b>Status</b> filter to '
       +'see them all.';
     ea.innerHTML='<button onclick="dropStatus()">Show all '+total+' transcripts</button>';
   } else if(mineOnly&&anyFilter){
     em.textContent='Nothing assigned matches these filters.';
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
               ("auto", "Automatic", "auto", "Follow the browser setting")]


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
    "<p>Choose the theme for this application.</p>"
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
            if ME and (fm.get("suggested_to") == ME or fm.get("awaiting") == ME
                       or ME in {o for a in effective_agents(fm) for o in owners_of(a)}):
                mine_n += 1
    _, st = git("status", "--porcelain", "--", "transcripts")
    uncommitted = len([l for l in st.splitlines() if l.strip()])
    # BOTH REPOS, matching the status line and the Change list on the Save page. The badge counted
    # this working tree only, so a batch with 3 transcript edits and 2 staged Blueprint files put
    # 3 on the nav beside a sentence reading "5 edited file(s) not yet saved" - two numbers for one
    # thing, and the smaller one is the one seen from every other page.
    try:
        uncommitted += sum(len(v) for v in bp_staged().values())
    except Exception:                                                     # noqa: BLE001
        pass                                    # no Blueprint checkout - count this repo alone
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


def page(title, inner, active="", all_view=False, rel="", agent=""):
    """Shell with a Forge-style SIDE NAV.

    The previous version put "All transcripts" and "Git & PR" as bare links in the app bar,
    where they read as body text - people did not realise they were navigation. A left rail
    with an icon, a label and a live count per item makes each one visibly a destination.
    """
    open_n, mine_n, uncommitted = nav_counts()
    # Saved locally but not yet sent in - the Publish badge. Distinct from `uncommitted`,
    # which is unsaved edits and belongs to Save.
    try:
        unsent = len(unsent_saves())
    except Exception:                                                  # noqa: BLE001
        unsent = 0
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
        + (item("/", icon("flag", 19, "ic-mine"), "My Transcripts", mine_n or None, "mine") if ME else "")
        # Admins only. For a contributor the item would be a link to other people's work they
        # cannot push to - an invitation to a dead end. An unidentified user gets it too,
        # because with no `me` there is no "mine" to fall back to and an empty app is worse.
        + (item("/?all=1", icon("clipboard_list", 19, "ic-all"), "All Transcripts", open_n or None, "all")
           if (is_admin() or not ME) else "")
        + "<div class=grp>Save &amp; Publish</div>"
        # TWO ITEMS, NOT ONE. "Save & Share" named two jobs with nothing in common: a local
        # checkpoint that shares nothing, and the publish sequence. The badges differ too -
        # unsaved edits are a Save concern, saved-but-unsent work is a Publish one.
        + item("/save", icon("folder", 19, "ic-git"), "Save", uncommitted or None, "save")
        + item("/publish", icon("publish", 19, "ic-git"), "Publish", unsent or None, "publish")
        # Visible to everyone who can run Part 2, which is everyone. The badge is the number
        # still needing a decision, so an unread eval is visible from any page rather than only
        # from the panel it happened to print into.
        + item("/evalreview", icon("clipboard_check", 19, "ic-ev"), "Eval Review",
               eval_pending_count() or None, "evalrev")
        # Admins only, same rule as All Transcripts: a contributor cannot merge, so the item
        # would be a link to a page of buttons that all refuse.
        + (item("/prs", icon("source_pull", 19, "ic-prs"), "PRs", open_pr_count or None, "prs")
           if is_admin() else "")
        # MONITOR AFTER SAVE & PUBLISH. It used to sit above, matching where Foundry's own
        # sidebar puts Analytics - but this app is not Foundry: the daily path here is review,
        # then publish, and a section nobody needs mid-task was interrupting it.
        + "<div class=grp>Monitor</div>"
        + item("/analytics", icon("chart_bar", 19, "ic-an"), "OT Analytics", None, "analytics")
        # Its own section rather than under Monitor: Monitor is visible to everyone, and this
        # is not. Admin-only for the same reason the backup repo is - snapshots carry agent
        # instructions, tenant storage paths, and per-file IDs that are direct DELETE handles.
        + ("<div class=grp>Backups</div>"
           + item("/backups", icon("backup_restore", 19, "ic-bk"), "Backups", None, "backups")
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
<style>{CSS}{icon_vars()}</style><header><img class=brand src="/logo.svg" alt="Tyler Technologies" width=28 height=28><b>OneTyler Foundry Team Agent Transcript Review</b><div class=hdrright>{MODE_SWITCH}{who}</div></header>
<body data-default-mine="{'1' if (ME and not all_view) else '0'}" data-default-status="{'pending' if (ME and not all_view) else '__open__'}" data-show-all="{'1' if (is_admin() or not ME) else '0'}" data-rel="{html.escape(rel)}" data-agent="{html.escape(agent)}">
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
            # `awaiting` is the old name for this field, still read so a transcript written
            # before the rename does not lose its handoff.
            "suggested_to": fm.get("suggested_to", "") or fm.get("awaiting", ""),
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
        #   handed to you    -> somebody named you, or named an agent you own. Strongest signal.
        #   you own the agent-> yours by area; nobody asked you specifically.
        # Collapsing them would hide the difference between "waiting on me" and "my patch".
        #
        # BOTH routing fields count, and each accepts a person or an agent. An agent resolves
        # through ownership, which is the whole point: a reviewer can hand a SAC problem to
        # "sac" without knowing who owns SAC this month.
        handed = []
        for key in ROUTING_KEYS:
            v = (r.get(key) or "").strip()
            if not v:
                continue
            if ME and v == ME:
                handed.append(key)
            elif ME and ME in owners_of_agent(v):
                handed.append(key)
        r["handed_to_me"] = handed
        r["mine_awaiting"] = bool(handed)
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
            f" data-sugg=\"{html.escape(r['suggested_to'])}\""
            f" data-owner=\"{html.escape(','.join(r['owners']))}\""
            f" data-eff=\"{html.escape(','.join(r['eff_agents']))}\""
            f" title=\"{html.escape(r.get('own_basis',''))}\""
            f" data-mine=\"{'awaiting' if r['mine_awaiting'] else ('area' if r['mine_area'] else '')}\""
            f" data-openpr=\"{r['openpr']['number'] if r['openpr'] else ''}\""
            f" data-href=\"/t/{html.escape(r['rel'])}\">"
            # PENDING ROWS ONLY, for every bulk action - marking, export and import alike.
            # A transcript that is already reviewed, pushed or excluded carries a decision, and
            # none of these three actions is a safe thing to do to a decision: marking re-stamps
            # it, and an imported ideal response would edit a body whose frontmatter still asserts
            # the old verdict.
            #
            # Also disabled inside an unmerged change request: the verdict in that request is
            # the real one, and a second stamp guarantees a conflict when it merges.
            f"<td class=nowrap><input type=checkbox class=ck value=\"{html.escape(r['rel'])}\""
            f"{' disabled' if (r['status'] != 'pending' or r['openpr']) else ''}"
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
            f"{'<div class=deleg>&rarr; '+html.escape(r['suggested_to'] or r['reassign'] or 'unassigned')+'</div>' if r['status']=='suggested' else ''}"
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
                        f"<b>{mine_a}</b> handed over</a>")
        if mine_r:
            bits.append(f"<b>{mine_r}</b> open in the owned area")
        youline = ("<p class=youline>"
                   + (" &middot; ".join(bits) if bits else "Nothing open is assigned right now.")
                   + " &nbsp;&mdash;&nbsp; amber rows were handed over, blue rows are the owned "
                     "area.</p>")

    # (label, filter-kind, select-id). kind: "" = not filterable, "sel" = value dropdown,
    # "date" = From/To range. Order matches the columns rendered per row.
    # Feedback sits FIRST, left of the question: a thumbs-down is the strongest signal on the
    # page about which row to open, and it was buried five columns in where you had to already
    # be reading the row to find it. Rare, too - 2 of 59 - so it has to be findable by scanning
    # one narrow column rather than by reading.
    HEADS = [(icon("thumb_up", 15) + icon("thumb_down", 15), "sel", "f_fb"),
             ("First question", "", ""), ("Handled by", "sel", "f_agent"),
             ("Date", "date", ""), ("Ex", "sel", "f_ex"),
             ("Status", "sel", "f_status"),
             ("Suggested to", "sel", "f_sugg"), ("Routing", "sel", "f_routing"),
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
            # The filter id is a short single word (see FKEYS); the record key it reads may
            # not be. Mapped rather than derived, because `f_sugg`[2:] is not a record key and
            # the crash it caused was a KeyError on page load, not a wrong filter.
            src = FILTER_SRC.get(fid[2:], fid[2:])
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
                f"onclick='fpop(this)' aria-label='Filter by {label}'>"
                f"{icon('chevron_down', 14)}</button>"
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
            why="These have a verdict, but only in a file on this laptop. "
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
            f"{icon('refresh', 15)} Sync transcripts</button>"
            # The reassurance itself. Without this the page could be an hour stale or five
            # minutes stale and look identical, which is the actual problem - nobody should
            # have to keep the tool open to trust what it is showing them.
            f"<span class=fresh id=freshness data-age='{age if age is not None else -1}'></span>"
            "<span class=hint id=syncmsg style='font-size:12px'></span></div>")
    # ALWAYS VISIBLE, availability the only thing that moves. The row used to appear only once
    # something was selected, which meant the two selection actions did not exist until after
    # the gesture that needs them - nothing on the page said a selection would lead anywhere.
    # A permanently-present disabled button states the affordance; a hidden one cannot.
    #
    # No Clear selection button: the header checkbox is already select-all / clear-all.
    actbar = ("<div class=actbar>"
              "<button id=ckmark onclick='bulkReview()' disabled>Mark reviewed</button>"
              "<button class=sec id=ckexport onclick='csvExport()' disabled>Export CSV</button>"
              "<input type=file id=csvfile accept='.csv,text/csv' hidden "
              "onchange='csvImport(this)'>"
              "<button class=sec id=ckimport onclick='csvImportPick(this)'>Import CSV</button>"
              "<span class=hint id=ckelig></span></div>")

    bar = (head + youline + "<div class=kpis>" + "".join(tiles) + "</div>"
           # Directly under the telemetry cards: the actions belong with the numbers they
           # act on, and above the filter row so narrowing the list does not move them.
           + actbar)

    # Search and the narrowing controls on ONE row. Previously the search field, its helper
    # paragraph, the date/mine/clear bar and the count line were four stacked blocks before
    # the table even started.
    search = ("<div class=bar id=fbar style='display:flex;gap:10px;align-items:center;"
              "flex-wrap:wrap'>"
              "<div class=searchwrap style='flex:1 1 260px;margin:0'>"
              "<span class=mag>" + icon("magnify", 18) + "</span>"
              "<input class=bigsearch id=f_q placeholder='Search question or filename&hellip;'>"
              "</div>"
              "<button class=sec onclick='clearFilters()'>Clear</button></div>"
              f"<p class=shown><b id=shown>0</b> of {tot} shown"
              + (f" &middot; <span class=hint>{total_all - tot} other row(s) hidden &mdash; "
                 "this view is per-person</span>" if mine_only and total_all > tot else "")
              + "</p>")


    return page("Transcripts", bar + search
                + "<div class=tblcard><table id=tbl><tr>"
                  "<th class=nowrap style='width:1%'>"
                  "<input type=checkbox id=ckall title='select all shown'></th>"
                  + "".join(hdr(*h) for h in HEADS)
                  + "</tr>"
                  + "".join(rows) + "</table>"
                  "<div id=emptystate style='display:none;padding:38px 8px 44px;text-align:center'>"
                  "<div class=emptyglyph>" + icon("menu", 34) + "</div>"
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
             # Blank lines become paragraphs. `about` is escaped, so markup in it would render
             # literally and a newline inside one <p> would collapse to a space - which turned a
             # three-part explanation into one unreadable block.
             + "".join(f"<p>{html.escape(para.strip())}</p>"
                       for para in re.split(r"\n\s*\n", d["about"]) if para.strip())
             + f"{table}"
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
                "" + icon("thumb_up", 16) + "</span>")
    if fb == "THUMBS_DOWN":
        return ("<span class='fb down' title='The user gave this answer a thumbs DOWN in "
                "Foundry - read this one first'>" + icon("thumb_down", 16) + "</span>")
    # No rating is the norm, and an icon for it would drown the two that matter.
    return "<span class=fb-none title='The user did not rate this answer'>&middot;</span>"


def awaiting_cell(r):
    """Who a transcript is waiting on, plus why the row is highlighted.

    Shows `suggested_to` when set. When it is not, falls back to the agent's owner in muted text —
    so a row is never blank in this column, and "nobody has been asked, but this is Jon's area"
    is visible at a glance rather than requiring you to know the mapping.
    """
    if r["suggested_to"]:
        badge = " <span class='pill mineflag'>assigned</span>" if r["mine_awaiting"] else ""
        return (f"<span class=whocell>{avatar(r['suggested_to'], 20)}"
                f"<b>{html.escape(r['suggested_to'])}</b></span>{badge}")
    if r["owners"]:
        faces = "".join(avatar(o, 20) for o in r["owners"])
        tag = " <span class='pill mineflag'>owned area</span>" if r["mine_area"] else ""
        return (f"<span class=whocell>{faces}"
                f"<span class=owner>{html.escape(', '.join(r['owners']))}</span></span>{tag}")
    return "<span class=owner>—</span>"


# Set by detail_page() immediately before it renders the form, so field() can show the derived
# round without `rel` being threaded through every call site.
_round_for_this_doc = None


def _render_fields(rel, prefill, keys=None, heading=""):
    """Render review fields, with the round derived for THIS transcript.

    `keys` selects which ones, so the dependent group can be rendered directly beneath the
    Summary box while the rest stay in their own grid below.
    """
    global _round_for_this_doc
    _round_for_this_doc = derived_round(rel)
    try:
        # ONE LIST. NO FIELD TRIGGERS THE AI.
        #
        # These were split into "Triggers changes" and "No action" on the theory that a verdict
        # value could ask for work. It cannot, and the split asserted otherwise: Answer verdict
        # sat under "Triggers changes", so recording `stale` - an observation about what already
        # happened - claimed to queue an assistant. Every field here is an ATTRIBUTE. Some route
        # the transcript (whose queue it appears in, who is asked to decide); none of them is a
        # request for content to change.
        #
        # What activates the assistant step under Publish is prose: an Ideal response under an
        # exchange, or a Summary. Those two carry the "triggers changes" tag, and they are the
        # only things in the form that do.
        out = [heading] if heading else []
        out += [field(k, prefill.get(k, ""))
                for k in (keys if keys is not None else REVIEW_KEYS)]
        return "".join(out)
    finally:
        _round_for_this_doc = None


def field(k, val):
    # Label = field name + ⓘ, nothing else. All guidance is in the panel; see FIELD_DOC.
    #
    # Sentence case, from FIELD_LABEL with a capitalise-the-first-word fallback. The labels used
    # to be the raw key with underscores swapped for spaces, so the form read "review status /
    # reviewer / suggested by" in all lowercase - which looks like unfinished markup rather than
    # a form. Only the ones whose wording differs from the key need an entry.
    icon, panel = doc_popover(k)
    words = k.replace("_", " ")
    lab = f"<label>{FIELD_LABEL.get(k, words[:1].upper() + words[1:])}{icon}</label>"
    if k in ADMIN_ONLY_FIELDS and not is_admin():
        # `reviewer` is forced to the current user rather than shown blank: for a contributor it
        # is not a choice, and an empty locked field looks broken.
        if k == "reviewer":
            val = ME or val
        shown = html.escape(val) if val else "&mdash;"
        why = {"review_status": "set by the buttons below",
               "reviewer": "you", "action_status": "follows KB action"}[k]
        return (f"<div class=fld>{lab}"
                f"<div class=roval>{shown}<span class=hint style='margin-left:8px'>"
                f"{why}</span></div>"
                f"<input type=hidden data-fm={k} value=\"{html.escape(val)}\">{panel}</div>")
    if k in PEOPLE_KEYS or k == "suggested_to":
        # Default `reviewer` to the person using the tool. They opened the transcript; they are
        # the reviewer. Leaving it blank made the commonest action - open, agree, mark reviewed -
        # fail on its first click for every new contributor, and the error it produced was about
        # a field they had no reason to think was theirs to fill.
        #
        # ONLY when blank, so it never overwrites a name already recorded, and only for
        # `reviewer` - a routing field is a deliberate choice about someone else and must stay
        # empty until a reviewer makes it.
        if k == "reviewer" and not val and ME and ME in contributors():
            val = ME
        people = contributors()
        if not people:
            return (f"<div class=fld>{lab}<input data-fm={k} value=\"{html.escape(val)}\" "
                    f"placeholder='contributors.json is empty or unreadable'>{panel}</div>")
        # ONE TYPE PER FIELD. `suggested_to` is a PERSON, `reassign_to` is an AGENT - they are
        # the same act at two different granularities, and a select that accepted either would
        # blur exactly the distinction the two fields exist to draw.
        allowed = [""] + people
        opts = "".join(f"<option{' selected' if o == val else ''}>{html.escape(o)}</option>"
                       for o in allowed)
        stale = ("<div class=hint style='color:var(--danger-fg)'>current value "
                 f"'{html.escape(val)}' is not in contributors.json</div>"
                 if val and val not in allowed else "")
        return f"<div class=fld>{lab}<select data-fm={k}>{opts}</select>{stale}{panel}</div>"
    if k in CHOICES:
        opts = "".join(f"<option{' selected' if o == val else ''}>{html.escape(o)}</option>"
                       for o in CHOICES[k])
        return f"<div class=fld>{lab}<select data-fm={k}>{opts}</select>{panel}</div>"
    if k in BOOL_KEYS:
        ck = " checked" if (val or "").strip().lower() in ("yes", "true", "1") else ""
        return (f"<div class=fld>{lab}"
                f"<label class=boolrow><input type=checkbox data-fm={k} data-bool=1{ck}>"
                "<span>Blueprint needs updating too</span></label>"
                f"{panel}</div>")
    if k in MULTI_KEYS:
        # A BUTTON AND A DIALOG, not an inline list. A multi-select needs ctrl/cmd-click to pick
        # more than one, which is the least discoverable interaction on the web - and with 42
        # files across 7 corpora the box was either too short to scan or tall enough to push the
        # rest of the form off screen. Checkboxes in a dialog cost one extra click and remove
        # both problems.
        #
        # The value still lives in a hidden input as a comma-separated list, so the save path,
        # the file format and everything downstream are unchanged.
        chosen = [x.strip() for x in (val or "").split(",") if x.strip()]
        groups = knowledge_files()
        known = {f"{d}/{f}" for d, fs in groups.items() for f in fs}
        rows = []
        for corpus, files in groups.items():
            rows.append(f"<div class=kbgroup>{html.escape(corpus)}</div>")
            for f in files:
                full = f"{corpus}/{f}"
                ck = " checked" if full in chosen else ""
                rows.append(f"<label class=kbrow><input type=checkbox value=\"{html.escape(full)}\""
                            f"{ck}><span>{html.escape(f)}</span></label>")
        # A path already recorded but no longer in the repo stays listed and ticked, or clicking
        # OK would silently drop it - and a renamed or deleted file is exactly when this field
        # matters most.
        gone = [c for c in chosen if c not in known]
        if gone:
            rows.append("<div class=kbgroup>No longer in the repo</div>")
            rows += [f"<label class=kbrow><input type=checkbox value=\"{html.escape(g)}\" checked>"
                     f"<span>{html.escape(g)}</span></label>" for g in gone]
        scope = ("" if is_admin() or not ME else
                 "<div class=hint style='margin-bottom:8px'>Showing the owned corpora. "
                 "An admin can name any file.</div>")
        # The BUTTON carries the state - "Select…" or "Selected (5)". A separate summary line
        # above it listed the chosen paths, which pushed this field taller than every other
        # control in the grid and knocked the row out of alignment. The count is what a reviewer
        # needs at a glance; the names are one click away and were never legible in a narrow
        # column anyway.
        n_sel = len(chosen)
        btn_label = f"Selected ({n_sel})" if n_sel else "Select&hellip;"
        return (f"<div class=fld>{lab}"
                f"<button type=button class=sec id=kbbtn onclick='kbOpen()'>"
                f"{btn_label}</button>"
                f"<input type=hidden data-fm={k} id=kbvalue value=\"{html.escape(val)}\">"
                "<div class=kbmodal id=kbmodal hidden>"
                "<div class=kbbox role=dialog aria-modal=true aria-label='Select knowledge files'>"
                "<h3 style='margin:0 0 4px'>Knowledge files</h3>"
                "<p class=sub style='margin:0 0 10px'>Which file(s) the change belongs in.</p>"
                f"{scope}"
                "<label class='kbrow kball'><input type=checkbox id=kball "
                "onchange='kbAll(this)'><span><b>Select all</b> &middot; untick to clear "
                "all</span></label>"
                f"<div class=kblist>{''.join(rows)}</div>"
                "<div class=kbacts>"
                "<button type=button class=sec onclick='kbCancel()'>Cancel</button>"
                "<button type=button onclick='kbOk()'>OK</button>"
                "</div></div></div>"
                f"{panel}</div>")
    if k in DERIVED_KEYS:
        val = str(_round_for_this_doc or val or "1")
        # READ-ONLY. `review_round` is a counter the tooling maintains, not an opinion: the
        # Re-review button raises it, and validate_reviews.py uses it to tell a deliberate
        # second verdict from an accidental overwrite of somebody else's.
        #
        # It was a free-text input, which made the one thing CI checks the one thing a reviewer
        # could quietly break - and the instructions had to say "do not edit this by hand",
        # which is the tell that it should never have been editable. Typing 1 over a 2 makes CI
        # reject the push; typing 3 over a 2 defeats the check silently. Neither is a judgement
        # anyone should be asked to make.
        #
        # Still submitted, via a hidden input, so the value round-trips unchanged on every save.
        shown = html.escape(val or "1")
        return (f"<div class=fld>{lab}"
                f"<div class=roval>{shown}<span class=hint style='margin-left:8px'>"
                "set by Re-review</span></div>"
                f"<input type=hidden data-fm={k} value=\"{html.escape(val)}\">{panel}</div>")
    return f"<div class=fld>{lab}<input data-fm={k} value=\"{html.escape(val)}\">{panel}</div>"


def button_legend():
    """The four verdict buttons, explained where they are used.

    Written from what the handlers actually do, not from their labels. The distinctions that
    matter are invisible from the button faces:

      * Save changes NO status - the other three all do.
      * Suggest KEEPS `reviewer` as you. What moves the work is `suggested_to` (a person) or
        `reassign_to` (an agent), and one of them must be set or the suggestion has nowhere to
        go. `reviewer` is always whoever did the reviewing, suggestion included.
      * Mark reviewed REFUSES while either routing field is set. Handing off and deciding are
        mutually exclusive: recording your verdict on work you just gave away would also pull it
        back out of the recipient's queue.
      * `review_round` is derived from what is on origin/main, not set by any of these.
      * The "& next" buttons navigate; Save and Re-review stay put.

    And the one people get wrong: none of these four touch git. They write the transcript FILE.
    Sharing happens on Save & Publish.
    """
    # ONE LINE EACH. The long-form version of this table was accurate and nobody read it - four
    # paragraphs of explanation above the buttons they describe reads as documentation printed
    # onto the screen. The reasoning that used to be here lives in this docstring, where a
    # maintainer will find it and a reviewer is not made to scroll past it.
    # FIVE ROWS, and "Mark reviewed & next" is not one of them. That button no longer exists: it
    # renders as "No changes & next" or "Changes suggested & next" depending on whether an Ideal
    # response or Summary was written, and those two do materially different things downstream -
    # one skips the publishing steps, the other joins them. A legend naming a button nobody can
    # see is worse than no legend.
    #
    # "Moves on?" is gone as a column. Every row said "yes" or "stays" about navigation, which is
    # the least consequential thing any of these buttons does and read as though it were a
    # property of the verdict.
    rows = [
        ("Save",
         "reviewed", False,
         "Saves entered text locally. No verdict recorded.",
         "Not a durable save &mdash; use the <b>Save</b> tab to back up work in progress."),
        ("Suggest &amp; next &rarr;",
         "suggested", True,
         "Transfers the decision to another owner.",
         "For a transcript belonging to another person or agent, including suggestions and the "
         "field settings under Summary. Does <b>not</b> mark it reviewed &mdash; the other person "
         "sees it as pending. Needs <b>Suggested to</b> (a person) or <b>Reassign to</b> "
         "(an agent)."),
        ("Re-review",
         "pending", False,
         "Re-opens an already reviewed transcript.",
         "Puts it back to pending and clears the verdict fields. Round 2 means someone decided "
         "before &mdash; read theirs first."),
        ("No changes &amp; next &rarr;",
         "reviewed", True,
         "Marks reviewed and SKIPS the transcript in the publishing steps.",
         "Shown when no Ideal response or Summary has been written. Nothing for an assistant to "
         "act on, so it stays out of Eval Review."),
        ("Changes suggested &amp; next &rarr;",
         "reviewed", True,
         "Marks reviewed and INCLUDES the transcript in the publishing steps.",
         "Shown once an Ideal response or a Summary is written. Unavailable while a hand-off "
         "is set."),
    ]
    out = ["<details class=card><summary>"
           "<span class=info aria-hidden=true>i</span>"
           "<h3>What do these buttons do?</h3>"
           "<span class=chev aria-hidden=true></span></summary>"
           "<div class=tblcard style='margin-top:10px'><table>"
           "<tr><th>Button</th><th>Sets status to</th><th>What it is for</th></tr>"]
    for label, status, _moves, gist, detail in rows:
        out.append(
            f"<tr><td class=nowrap><b>{label}</b></td>"
            + ("<td class=nowrap><span class='pill excluded'>unchanged</span></td>"
               if label == "Save" else
               f"<td class=nowrap><span class='pill {status}'>{status}</span></td>")
            + f"<td>{gist}<div class=sub style='margin-top:4px'>{detail}</div></td></tr>")
    out.append("</table></div>"
               "<div class='bar bnr-note' style='margin:12px 0 0'>"
               "None of these share anything. Sharing happens on "
               "<b>Publish</b>.</div></details>")
    return "".join(out)


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
        # Four sentences, in the order the work happens. The previous version explained the
        # pre-filled defaults, what to do if they were wrong, and who reads the prose - all true,
        # and all of it above the transcript the reviewer had come to read. The defaults do not
        # need explaining if they are correct, and the rest is on the buttons' own legend.
        banner = ("<div class='bar bnr-ok'>"
                  "Add an <b>Ideal response</b> under each <b>Exchange</b> to indicate the response "
                  "Foundry was expected to provide. This can then be used to compare the "
                  "performance of Foundry once knowledge files have been updated and "
                  "iteratively improved upon. The <b>Summary</b> section can be used to give "
                  "overall suggestions to improve Foundry responses. If no changes are needed, "
                  "fill out <b>Answer verdict = good</b> and select "
                  "<b>No changes &amp; next &rarr;</b>."
                  "</div>")
    elif (fm.get("review_status") or "") == "suggested":
        # Nothing here is a verdict yet. Say so loudly, or the owner reads a filled-in form
        # as settled and rubber-stamps someone else's guess.
        banner = ("<div class='bar bnr-sug'>"
                  f"<b>Suggestion from {html.escape(fm.get('reviewer','?'))}</b>"
                  + (f", handed to <b>{html.escape(fm.get('suggested_to') or fm.get('reassign_to') or '')}</b>"
                     if (fm.get("suggested_to") or fm.get("reassign_to"))
                     else " — no destination named")
                  + ". <b>Not a verdict.</b> Nothing has been accepted and Claude will not act "
                    "on it. Read the ideal response and the proposed fix, change anything to disagree "
                    "with, then <b>Mark reviewed</b> to accept it under a new name — or "
                    "<b>Suggest</b> again to hand it on.</div>")
    else:
        banner = (f"<div class='bar bnr-done'>"
                  f"Already <b>{html.escape(fm.get('review_status',''))}</b> by "
                  f"<b>{html.escape(fm.get('reviewer','?'))}</b> (round "
                  f"{html.escape(fm.get('review_round','1'))}). Saving edits keeps the same round; "
                  f"use <b>Re-review</b> to start a new one.</div>")

    # THE FORM COMES AFTER THE TRANSCRIPT, not before it.
    #
    # It used to sit at the top, which put thirteen dropdowns between the reviewer and the thing
    # they came to read - and asked for a diagnosis before they had seen the conversation. The
    # fields are conclusions; conclusions belong after the evidence. Reading order is now the
    # order of the work: what was asked, what came back, what you would have said, then the
    # summary that classifies it.
    parts = [head, banner]

    ci, cp = doc_popover("ideal response")
    for n, tools, q, a, rv in exchanges_of(body):
        none_tools = "none" in tools.lower()
        parts.append(
            f"<div class=card><b>Exchange {n}</b>"
            f"<div class=tools>Tools called: "
            f"{'<span class=pill.bad>none — answered without searching</span>' if none_tools else html.escape(tools)}</div>"
            f"<div class=q>{html.escape(q)}</div>"
            f"<div style='margin:8px 0 4px;font-size:12px;color:var(--forge-theme-text-medium)'><b>Foundry response</b></div>"
            f"<div class=a>{html.escape(a)}</div>"
            "<div class=fld><div class=fldhead>"
            f"<label style='margin:0'>Ideal response{ci}"
            f"<span class=trigtag title='Content here activates the assistant step under Publish. The verdict fields do not.'>triggers changes</span></label>"
            # Editing the real answer is how an ideal response actually gets written - most of it
            # is usually right, and retyping the correct parts to fix one paragraph is what made
            # this box feel like a place for notes rather than for the answer.
            "<button type=button class=sec onclick='copyFoundry(this)'>Copy Foundry response"
            f"</button></div>{cp}"
            # EMPTY, not the scaffolding. The fetch template used to seed every box with
            # "**Review -** _verdict:_ - _should have said:_", which read as an instruction to
            # annotate rather than to answer. New transcripts no longer carry it; the 67 already
            # on disk are rendered blank here and drop it the first time they are saved, so no
            # bulk rewrite of review data is needed.
            f"<textarea data-ex={n}>"
            f"{'' if _is_placeholder(rv) else html.escape(rv)}</textarea>"
            # One line, and it states the CONSEQUENCE rather than the instruction: Eval Review
            # scores the agent's new answer against this text, so notes score meaninglessly
            # while a full reply gives a number worth reading.
            "<div class=hint>The full answer, not notes &mdash; Eval Review scores the next "
            "answer against it.</div></div></div>")

    # ---- Summary: the free-text conclusion, then the fields that classify it ---------------
    pi, pp = doc_popover("proposed_fix")
    parts.append(
        "<h2 class=sec style='margin-top:var(--forge-spacing-large)'>Summary</h2>"
        "<p class=sub style='margin:0 0 12px'>Complete after reviewing the exchanges. "
        "Prose carries the substance; the fields route it.</p>"
        f"<div class=card><div class=fld>"
        f"<label>Overall suggestions and comments{pi}"
          f"<span class=trigtag title='Content here activates the assistant step under Publish. The verdict fields do not.'>triggers changes</span></label>{pp}"
        f"<textarea id=proposed style='min-height:150px'>"
        f"{html.escape(proposed_of(body))}</textarea></div>"
        # DIRECTLY UNDER THE PROSE, in its own row rather than mixed into the grid below. These
        # four only mean something once something has been written, and putting them beside the
        # box that has to be written first is the shortest way to say so.
        "<div class=depwrap id=depfields>"
        "<div class=fldgrp><span class=fldgrp-h>Directs the change</span>"
        "<span class=hint id=dephint> &mdash; available once an <b>Ideal response</b> or "
        "<b>Overall suggestions and comments</b> has been written.</span></div>"
        "<div class=grid>"
        + _render_fields(rel, prefill, DEPENDENT_FIELDS) + "</div></div>"
        "<div class=grid style='margin-top:var(--forge-spacing-medium)'>"
        + _render_fields(rel, prefill,
                         [k for k in REVIEW_KEYS if k not in DEPENDENT_FIELDS],
                         heading="<div class=fldgrp><span class=fldgrp-h>No action</span>"
                                 "<span class=hint> &mdash; recorded, but does not trigger AI "
                                 "updates to knowledge files.</span></div>")
        + "</div></div>")

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
        f"title='Record this as a suggestion for the area owner, not as a verdict'>"
        f"Suggest &amp; next &rarr;</button>"
        f"<button class=sec onclick=\"reReview('{html.escape(rel)}')\">Re-review</button>"
        # LABEL FOLLOWS THE FORM. "Mark reviewed" said the same thing whether the reviewer had
        # asked for a change or explicitly signed the answer off - two very different acts, and
        # only one of them puts the transcript in an eval. The label is recomputed as the form is
        # edited, from the SAME neutral-value pools eval_batch uses to decide what to replay, so
        # a transcript labelled "No changes" is guaranteed not to appear under Eval Review.
        # Before the verdict button, so it reads as "undo what I typed, then finish". Disabled
        # until there is something to clear - see refreshMarkLabel().
        f"<button class=sec id=clearbtn disabled onclick='clearChanges(this)' "
        f"title='Nothing suggested yet'>Clear changes</button>"
        f"<button onclick=\"markAndNext('{html.escape(rel)}','{next_}')\" id=markbtn>"
        "No changes &amp; next &rarr;</button>"
        f"</div></div>"
        # Directly under the buttons, collapsed. The four labels do not distinguish themselves -
        # "Save" and "Mark reviewed" both sound like saving, and nothing on the faces hints that
        # Suggest blanks `reviewer` or that Re-review bumps the round.
        + button_legend())
    # The agent that ANSWERED, as a slug, so the reassign-to rule can tell "a different agent"
    # from "the same one". A delegated conversation is owned by the sub-agent that handled it,
    # not by the team router that passed it along.
    cur_agent = (DELEGATE_SLUG.get((fm.get("delegated_to") or "").strip(), "")
                 or (fm.get("answered_by") or "").strip())
    return page(f"{fm.get('answered_by','')} {rel}", "".join(parts), rel=rel, agent=cur_agent)


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
            raise RuntimeError(f"could not set the work aside: {out}\n{out2}")
        SITTING_LANE = name
        return name, True
    SITTING_LANE = name
    return name, True


# `git commit` returns 1 both for "nothing to commit" and for a real failure. They need
# telling apart: sending in reviews that were already saved is normal, a broken commit is not.
NOTHING_TO_SAVE = 99


def save_reviews(msg):
    """Put this sitting on its own branch if needed, then commit the reviewer's work.

    This is "Save my reviews", and it is also the first thing "Process Part 2" does. The
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
        lines.append("The work has been set aside from everyone else's, so it cannot "
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

    SCANS EVERY REVIEW LANE, not just HEAD - and the previous version claimed to while doing the
    opposite. `git log HEAD --not --remotes` is bounded by HEAD's ancestry, so with the checkout
    on any other branch a reviewer's saves become invisible: measured 2026-08-30 with the repo
    left on `main`, this reported 0 unsent saves while 6 sat on
    `review/vijay-tylertech/08282026-121644`, and the Save page said "Nothing waiting." That is
    the worst possible failure for this particular indicator - it is the one thing a reviewer
    would check to confirm their work still exists, and it told them it did not.
    `review/*` and not `--branches`, because machinery branches (feature/, fix/) are not saves
    and listing them here would report the tool's own development as the reviewer's pending work.

    No fetch: this runs on every page render, and a network call would hang the page on a bad
    connection. It uses the last-known remote state, like the rest of the page.
    """
    rc, out = git("log", "--format=%h%x09%ad%x09%s", "--date=format:%m/%d %H:%M",
                  "HEAD", "--branches=review/*", "--not", "--remotes")
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
        return 1, (f"There are {n} edited file(s) not saved yet. Discarding rewinds the "
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
    `git log` - but it is NOT redundant where it actually gets read: "Process Part 2" runs
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
                     "nothing hand-written:\n"
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


# Where the Blueprint checkout lives. Overridable, because it is a sibling clone and not everyone
# puts it in the same place; the default is where it sits on the machine this was built on.
BP_REPO = Path(os.environ.get(
    "BLUEPRINT_REPO",
    str(REPO.parent.parent / "blueprint" / "corpdev-new-blueprint")))
BP_REMOTE = "tyler-technologies/corpdev-new-blueprint"


def bp_batch():
    """Transcripts in this batch whose feedback also implies Blueprint work. [] if none."""
    out = []
    _, listed = git("diff", "--name-only", "origin/main", "--", "transcripts")
    for rel in (l.strip() for l in listed.splitlines()):
        if not rel.endswith(".md") or Path(rel).name in (
                "README.md", "INDEX.md", "ONBOARDING.md"):
            continue
        f = REPO / rel
        if not f.is_file():
            continue
        fm, _ = parse(f)
        if (fm or {}).get("bp_updates", "").strip().lower() in ("yes", "true", "1"):
            out.append(rel)
    # A STAGED PATCH IS ITSELF A PENDING REQUEST, whether or not the transcript is still in the
    # diff against main. Once a transcript's verdict merges it drops out of the diff - and the
    # Blueprint patch attributed to it was then orphaned: staged, listed by --list, and never
    # opened, because nothing asked for it any more. Silently dropping Blueprint work is the
    # failure the whole per-transcript attribution exists to prevent.
    for rel in bp_staged():
        if rel not in out:
            out.append(rel)
    return sorted(out)


def bp_available():
    """(ok, why). Whether the Blueprint checkout can be worked with at all."""
    if not BP_REPO.is_dir():
        return False, (f"No Blueprint checkout at {BP_REPO}. Clone "
                       f"{BP_REMOTE} there, or set BLUEPRINT_REPO to where it is.")
    if not (BP_REPO / ".git").exists():
        return False, f"{BP_REPO} exists but is not a git checkout."
    return True, ""


def bp_git(*args, timeout=120):
    """git, but in the Blueprint checkout. Output is stripped — DO NOT use it for a patch."""
    r = subprocess.run(["git", *args], cwd=BP_REPO, capture_output=True, text=True,
                       timeout=timeout)
    return r.returncode, (r.stdout + r.stderr).strip()


def bp_git_bytes(*args, timeout=120):
    """git in Blueprint, returning stdout as RAW BYTES. (rc, stdout_bytes, stderr_text).

    THE ONLY SAFE WAY TO CAPTURE A PATCH. Two separate things corrupt one, and both have
    actually happened here:

    1. `.strip()` (see bp_git) deletes trailing blank context lines - a blank context line is a
       single space - while the hunk header goes on claiming they are there. Result:
       `error: corrupt patch at line N`, which reads like a damaged file rather than a caller
       that trimmed it.

    2. `text=True` performs universal-newline translation, silently rewriting every `\\r\\n` as
       `\\n`. Blueprint has CRLF files (`workspaces.md` is 95 CRLF lines, 0 LF), so a patch
       captured in text mode does not match the file it came from and `git apply` refuses it.
       This one is nastier than the first: the patch looks perfectly well-formed, and the same
       diff applies fine from the command line, so the bug appears to be in the repo rather
       than in the capture.

    Bytes mode fixes both, and stderr stays separate because mixing it into stdout would
    corrupt a patch just as effectively.
    """
    r = subprocess.run(["git", *args], cwd=BP_REPO, capture_output=True, timeout=timeout)
    return r.returncode, r.stdout, (r.stderr or b"").decode(errors="replace")


def bp_sync():
    """Fast-forward the Blueprint checkout to origin/master. (ok, message).

    THIS IS A CORRECTNESS REQUIREMENT, NOT HYGIENE - see bp_stage_add's guard.
    `bp_stage_add` captures `git diff origin/master`, so if the local tree is BEHIND
    origin/master that diff also contains the REVERSE of everything that landed upstream, and
    those reversions get attributed to the transcript and opened as part of its request.

    Measured on a tree one commit behind: the captured patch picked up
    `src/clientModules/chatbot.js` - a file the transcript never touched - carrying 38 removal
    lines. Merging that request would have quietly reverted somebody's work.

    Fast-forward only, and never over local edits: a Blueprint tree with work in it belongs to
    whoever left it there. A refusal is reported, never forced.
    """
    ok, why = bp_available()
    if not ok:
        return False, why
    rc, out = bp_git("fetch", "--prune", "origin", "master", timeout=120)
    if rc != 0:
        return False, "Could not fetch Blueprint from origin:\n" + out
    cur = bp_git("rev-parse", "--abbrev-ref", "HEAD")[1].strip()
    dirty = bool(bp_git("status", "--porcelain")[1].strip())
    if cur not in ("master", "main"):
        return False, (f"The Blueprint checkout is on `{cur}`, not master, so it was not "
                       "synced. Switch it to master (or finish what is on that branch) before "
                       "staging Blueprint edits.")
    if dirty:
        # Deliberately NOT an error. Uncommitted Blueprint edits are the normal mid-work state -
        # they are exactly what is about to be staged - and refusing here would block the flow
        # it exists to protect. Whether the tree is at origin/master is what actually matters,
        # and bp_stage_add checks that separately.
        head = bp_git("rev-parse", "HEAD")[1].strip()
        want = bp_git("rev-parse", "origin/master")[1].strip()
        if head == want:
            return True, "Blueprint is up to date (uncommitted edits left alone)."
        return False, ("Blueprint has uncommitted edits AND is behind origin/master, so it "
                       "cannot be fast-forwarded without touching them. Commit, stash or "
                       "discard them, then sync — staging from a stale tree would attribute "
                       "other people's reverted work to this transcript.")
    rc, out = bp_git("merge", "--ff-only", "origin/master")
    if rc != 0:
        return False, "Blueprint could not be fast-forwarded:\n" + out
    return True, ("Blueprint already up to date." if "up to date" in out.lower()
                  else "Blueprint synced to origin/master.")


def bp_at_origin():
    """(ok, head, want). Is the Blueprint checkout's HEAD exactly origin/master?"""
    head = bp_git("rev-parse", "HEAD")[1].strip()
    want = bp_git("rev-parse", "origin/master")[1].strip()
    return head == want, head[:8], want[:8]


def bp_changes():
    """Blueprint files changed against its default branch, committed or not."""
    ok, _ = bp_available()
    if not ok:
        return []
    bp_git("fetch", "-q", "origin", "master")
    rc, out = bp_git("diff", "--name-only", "origin/master")
    if rc != 0:
        return []
    return sorted({l.strip() for l in out.splitlines() if l.strip()})


# Per-transcript Blueprint attribution.
#
# WHY A STAGING AREA RATHER THAN JUST READING THE BLUEPRINT WORKING TREE.
# ----------------------------------------------------------------------
# `bp_changes()` can say WHAT changed in Blueprint but never WHICH TRANSCRIPT asked for it - a
# working tree is one flat pile of edits. That was fine while all Blueprint work rode in a single
# request, and is not fine now that each transcript gets its own: without attribution, "revert
# this transcript" can only mean "revert everything", and one rejected answer would silently drop
# another transcript's approved Blueprint fix.
#
# So each transcript's Blueprint edits are captured as a patch the moment they are made, and the
# Blueprint working tree is returned to clean. The patch IS the attribution: one file per
# transcript, named after it. A per-transcript branch is then built by applying just that patch
# to a fresh branch off master, which is also what makes the requests independently mergeable.
BP_STAGE = REPO / ".bp-stage"


def bp_slug(rel):
    """A filesystem-safe key for a transcript path. Stable, and reversible enough to read."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", rel)


def bp_stage_path(rel):
    return BP_STAGE / (bp_slug(rel) + ".patch")


def bp_stage_add(rel):
    """Capture the CURRENT Blueprint diff as this transcript's patch. (ok, message).

    Takes everything Blueprint has against master right now, so it must be called once per
    transcript, while the tree holds only that transcript's edits - edit, stage, edit, stage.
    Staging resets the Blueprint tree afterwards, which is what keeps the next transcript's
    capture from re-including this one.
    """
    ok, why = bp_available()
    if not ok:
        return False, why
    bp_git("fetch", "-q", "origin", "master")
    # THE STALE-TREE GUARD. Refuse rather than capture a patch that reverts upstream work.
    #
    # The capture below is `git diff origin/master`. If HEAD is not origin/master, that diff
    # ALSO contains the reverse of every upstream commit the tree lacks - attributed to this
    # transcript, and opened as part of its Blueprint request. Measured on a tree one commit
    # behind: the patch picked up a file the transcript never touched, carrying 38 removal
    # lines, and merging it would have reverted somebody's work.
    #
    # Nothing downstream can catch this. The patch applies cleanly, the reverse-check passes,
    # and every file in it is a real diff - it is only wrong about WHOSE change it is. So it has
    # to be refused here.
    at, head, want = bp_at_origin()
    if not at:
        return False, ("The Blueprint checkout is not at origin/master "
                       f"(HEAD {head}, origin/master {want}), so nothing was staged.\n\n"
                       "Staging from a stale tree would capture the REVERSE of everything that "
                       "landed in Blueprint meanwhile and attribute it to this transcript — "
                       "merging that would revert other people's work.\n\n"
                       "Sync Blueprint first:\n"
                       f"  git -C {BP_REPO} switch master\n"
                       f"  git -C {BP_REPO} pull --ff-only\n"
                       "then redo this transcript's Blueprint edits and stage again.")
    # -N so a brand-new page appears in `git diff` at all; without it an added file is untracked
    # and the patch would silently omit the whole thing.
    bp_git("add", "-AN")
    # BYTES, not bp_git and not text mode: see bp_git_bytes. Stripping the output, or letting
    # Python translate newlines, each produce a patch git refuses.
    rc, patch, err = bp_git_bytes("diff", "--binary", "origin/master")
    if rc != 0:
        return False, f"could not read the Blueprint diff: {err[:300]}"
    if not patch.strip():
        return False, ("Blueprint has no changes against master, so there is nothing to attribute "
                       "to this transcript. Make the Blueprint edits first, then stage them.")
    files = bp_changes()
    BP_STAGE.mkdir(exist_ok=True)
    bp_stage_path(rel).write_bytes(patch if patch.endswith(b"\n") else patch + b"\n")
    # Prove the patch is sound BEFORE throwing the working tree away. Writing a patch that
    # cannot be replayed and then resetting would destroy the edits with nothing recoverable,
    # and the failure would surface days later at send time with the work gone. That is not
    # hypothetical - the first version of this function wrote a truncated patch and reset over
    # the top of it.
    #
    # Checked with --reverse, against the tree as it is NOW. A plain --check would be wrong here
    # and fails on every real call: the patch describes master -> working tree, and the working
    # tree already holds those changes, so applying it forward has nothing to bite on. Reversing
    # it proves the patch's post-image matches the tree exactly; its pre-image matches master by
    # construction, since git generated it against master a moment ago.
    chk = subprocess.run(["git", "apply", "--check", "--reverse", str(bp_stage_path(rel))],
                         cwd=BP_REPO, capture_output=True, text=True, timeout=120)
    if chk.returncode != 0:
        bp_stage_path(rel).unlink(missing_ok=True)
        return False, ("The captured Blueprint patch does not describe the Blueprint tree "
                       "faithfully, so nothing was staged and the Blueprint edits are "
                       "untouched:\n" + (chk.stdout + chk.stderr)[:400])
    # Back to clean, so the next transcript's capture is only its own. Reset AND clean: reset
    # restores tracked files, and a newly added page would otherwise survive as untracked and be
    # captured again by the next stage.
    bp_git("reset", "-q", "--hard", "origin/master")
    bp_git("clean", "-qfd")
    return True, (f"Attributed {len(files)} Blueprint file(s) to {rel}:\n"
                  + "\n".join("  " + f for f in files)
                  + "\n\nThe Blueprint tree is clean again — make the next transcript's edits.")


def bp_staged():
    """{transcript_rel: [blueprint files]} for everything currently staged."""
    if not BP_STAGE.is_dir():
        return {}
    # The slug is lossy (any non-safe char becomes "_"), so recover the real path by matching
    # slugs against the transcripts that exist rather than trying to un-slug the filename.
    known = {bp_slug(r): r for r in (
        str(p.relative_to(REPO)) for p in (REPO / "transcripts").rglob("*.md"))}
    out = {}
    for p in sorted(BP_STAGE.glob("*.patch")):
        rel = known.get(p.stem, p.stem)
        # rstrip("\r") because a CRLF file's patch mixes line endings: git writes the header
        # lines with LF but the content lines carry the file's own CRLF, and a stray \r on a
        # captured path would make every filename comparison miss.
        files = sorted({m.group(1).rstrip("\r") for m in
                        re.finditer(r"^\+\+\+ b/(.+)$", p.read_text(errors="replace"), re.M)})
        out[rel] = files
    return out


def bp_unstage(rel):
    """Drop this transcript's Blueprint changes. (ok, message).

    Called when a transcript goes back to pending: its Blueprint edits are part of the same
    rejected change and leaving them staged would ship them on the next send, attached to a
    verdict that no longer exists.

    Also tears down a request if one was already opened - closing it and deleting the branch
    rather than leaving an orphan open against a shared docs repo. Blueprint requests are only
    created after eval approval, so in the normal case there is nothing there yet.
    """
    p = bp_stage_path(rel)
    had = p.is_file()
    if had:
        p.unlink()
    msgs = [f"Blueprint changes for {rel} dropped." if had else
            f"No Blueprint changes were staged for {rel}."]
    br = f"kb-review/bp-{bp_slug(rel)}"
    ok, _ = bp_available()
    if ok:
        r = subprocess.run(["gh", "pr", "list", "--repo", BP_REMOTE, "--head", br,
                            "--state", "open", "--json", "number", "-q", ".[].number"],
                           cwd=BP_REPO, capture_output=True, text=True, timeout=90)
        for num in (r.stdout or "").split():
            subprocess.run(["gh", "pr", "close", num, "--repo", BP_REMOTE, "--delete-branch",
                            "--comment", "The transcript behind this went back to pending, so "
                            "these Blueprint edits are withdrawn."],
                           cwd=BP_REPO, capture_output=True, text=True, timeout=120)
            msgs.append(f"Closed Blueprint request #{num} and deleted its branch.")
    return True, " ".join(msgs)


def bp_open_pr_for(rel, hint):
    """One Blueprint request for ONE transcript, from its staged patch. (ok, message).

    Built on a branch off origin/master carrying only this transcript's patch, so each request
    stands alone and can be merged without waiting on the others. Two transcripts touching the
    same Blueprint page will conflict on the second merge - which is correct and visible, rather
    than one silently overwriting the other inside a combined request.
    """
    ok, why = bp_available()
    if not ok:
        return False, why
    p = bp_stage_path(rel)
    if not p.is_file():
        return False, (f"{rel} is marked BP updates but no Blueprint edits are attributed to it. "
                       "The assistant needs to make them and run:\n"
                       f"  python3 scripts/bp_stage.py --transcript {rel}")
    bp_git("fetch", "-q", "origin", "master")
    bp_git("reset", "-q", "--hard")
    bp_git("clean", "-qfd")
    br = f"kb-review/bp-{bp_slug(rel)}"
    bp_git("branch", "-qD", br)
    rc, out = bp_git("switch", "-q", "-c", br, "origin/master")
    if rc != 0:
        return False, f"could not branch in Blueprint for {rel}: {out[:300]}"
    r = subprocess.run(["git", "apply", "--index", str(p)], cwd=BP_REPO,
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        bp_git("switch", "-q", "master")
        return False, (f"could not apply the staged Blueprint patch for {rel} — Blueprint's "
                       f"master has probably moved under it:\n{(r.stdout + r.stderr)[:400]}")
    title = f"Blueprint updates from transcript review — {Path(rel).name}"
    body = ("Opened from transcript review feedback in "
            "`onetyler-foundry-team-agent-kb`.\n\n"
            f"Transcript: `{rel}`\n\n"
            "Most of the indexed knowledge is derived from Blueprint, so the knowledge-file "
            "fix for this transcript does not hold unless this lands too — the next "
            "reconciliation would restore the old wording.")
    rc, out = bp_git("commit", "-qm", title + "\n\n" + body)
    if rc != 0 and "nothing to commit" not in out.lower():
        return False, f"could not commit in Blueprint for {rel}: {out[:300]}"
    rc, out = bp_git("push", "-qu", "--force-with-lease", "origin", br, timeout=240)
    if rc != 0:
        return False, f"could not push the Blueprint branch for {rel}: {out[:300]}"
    r = subprocess.run(["gh", "pr", "create", "--repo", BP_REMOTE, "--base", "master",
                        "--head", br, "--title", title, "--body", body],
                       cwd=BP_REPO, capture_output=True, text=True, timeout=180)
    made = ((r.stdout or "") + (r.stderr or "")).strip()
    bp_git("switch", "-q", "master")
    if r.returncode != 0 and "already exists" not in made.lower():
        return False, f"could not open the Blueprint request for {rel}: {made[:300]}"
    tail = made.splitlines()[-1] if made.splitlines() else ""
    # Tag it so the set is identifiable on GitHub itself, not only from this tool. Not fatal:
    # labelling Blueprint may exceed a contributor's rights, and the `kb-review/` branch prefix
    # keeps the request in the history either way.
    ok_tag, tagmsg = tag_pr(br, BP_REMOTE)
    ok_auto, auto = bp_set_automerge(br)
    return True, (f"{Path(rel).name}: {tail}\n    {auto}"
                  + ("" if ok_tag else f"\n    not tagged: {tagmsg}"))


def bp_set_automerge(branch):
    """Put a Blueprint request into auto-merge. (ok, message).

    AUTO-MERGE AT CREATION, ALWAYS - not as a separate click afterwards.
    A contributor can push to Blueprint and open the request but cannot approve it; an admin
    approves. Auto-merge is what joins those two facts up: the request merges itself the moment
    the approval and Blueprint's own CI are both in, so nobody has to come back and press a
    button at the right time. Without it the request sits green and unmerged, and the knowledge
    file ships while the Blueprint page it was derived from does not - which the next
    reconciliation then reverts.

    Enabling it may itself need more rights than a contributor has. That is reported rather than
    treated as a failure of the whole send: the request exists and is correct either way, and an
    admin turning auto-merge on afterwards is a small, obvious job.
    """
    r = subprocess.run(["gh", "pr", "merge", "--repo", BP_REMOTE, branch,
                        "--squash", "--auto", "--delete-branch"],
                       cwd=BP_REPO, capture_output=True, text=True, timeout=150)
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    if r.returncode == 0:
        return True, "auto-merge ON — merges itself once an admin approves and CI passes."
    why = out.splitlines()[-1][:160] if out.strip() else "no output from gh"
    return False, f"auto-merge could NOT be set (an admin needs to turn it on): {why}"


def bp_open_pr(branch_hint, title, body):
    """Commit, push and open a change request in the Blueprint checkout. (ok, message).

    A SEPARATE REPO MEANS A SEPARATE REQUEST. Blueprint is not a subdirectory of this repo and has
    its own reviewers, its own CI and its own default branch, so the two changes cannot ride in one
    request - they can only be opened and merged together, which is what the PRs tab does.

    Never touches Blueprint's master directly, and refuses if the checkout has nothing to send:
    an empty request against a shared docs repo is noise its reviewers have to read.
    """
    ok, why = bp_available()
    if not ok:
        return False, why
    changes = bp_changes()
    if not changes:
        return False, ("Nothing to send to Blueprint — that checkout has no changes against "
                       "master. The transcripts are marked BP updates, so either the assistant "
                       "has not made those edits yet, or it made them somewhere else.")
    cur = bp_git("rev-parse", "--abbrev-ref", "HEAD")[1].strip()
    if cur in ("master", "main", "HEAD"):
        br = f"kb-review/{branch_hint}"
        rc, out = bp_git("switch", "-c", br)
        if rc != 0:
            return False, f"could not branch in Blueprint: {out}"
    else:
        br = cur
    bp_git("add", "-A")
    rc, out = bp_git("commit", "-m", title + "\n\n" + body)
    if rc != 0 and "nothing to commit" not in out.lower():
        return False, f"could not commit in Blueprint: {out}"
    rc, out = bp_git("push", "-u", "origin", br, timeout=240)
    if rc != 0:
        return False, f"could not push the Blueprint branch: {out}"
    r = subprocess.run(["gh", "pr", "create", "--repo", BP_REMOTE, "--base", "master",
                        "--head", br, "--title", title, "--body", body],
                       cwd=BP_REPO, capture_output=True, text=True, timeout=180)
    made = ((r.stdout or "") + (r.stderr or "")).strip()
    if r.returncode != 0 and "already exists" not in made.lower():
        return False, f"could not open the Blueprint request: {made[:300]}"
    ok_tag, tagmsg = tag_pr(br, BP_REMOTE)
    return True, (f"Blueprint change request, {len(changes)} file(s):\n"
                  + "\n".join("  " + c for c in changes) + "\n" + made.splitlines()[-1]
                  + ("" if ok_tag else f"\n  not tagged: {tagmsg}"))


def analysis_prompt(n):
    """The exact words to hand an assistant. Generated, not written by the reviewer.

    Deliberately short and deliberately NOT a description of the mechanics. The instructions an
    assistant needs are already in CLAUDE.md, which it reads on its own; repeating them here
    would create a second copy to drift. What it cannot know is that a batch is ready and what
    the human wants out of it.
    """
    base = (f"I have finished reviewing {n} transcript(s) in this repo. "
            "Sync this repo to the latest main first (`git fetch origin` and bring main up to "
            "date; do not disturb my in-progress branch), so you are editing current content "
            "and not reintroducing something already fixed. "
            "Read all of my feedback as one body before changing anything, then update the "
            "knowledge files so the agents stop giving those answers. Summarise what you "
            "changed, per transcript, so I can follow my own feedback through. "
            "Do not change my verdicts, and ask me rather than guessing if any of my feedback "
            "is ambiguous.")
    bp = bp_batch()
    if not bp:
        return base
    # The Blueprint half is stated here rather than left to CLAUDE.md, because it is the one
    # thing an assistant cannot infer: which transcripts I marked as needing it. The REASON is
    # spelled out because it changes what "done" means - a Docusaurus- file fixed on its own is
    # not fixed, it is fixed until the next reconciliation.
    return (base + "\n\n"
            + (f"{len(bp)} of these is marked" if len(bp) == 1
               else f"{len(bp)} of these are marked")
            + " **BP updates**, so the Blueprint documentation needs the same treatment:\n"
            + "\n".join(f"  - {r}" for r in bp) + "\n\n"
            f"The Blueprint checkout is at {BP_REPO}. For each of those transcripts: apply what "
            "my ideal responses imply to the Blueprint pages, and also SCAN the Blueprint docs for "
            "anything on the same subject that now conflicts. Most of the indexed knowledge is "
            "derived from Blueprint, so a `Docusaurus-` knowledge file fixed on its own is "
            "reverted by the next reconciliation - fixing Blueprint is what makes it stick.\n\n"
            "SYNC THE BLUEPRINT CHECKOUT BEFORE YOU EDIT IT, every time:\n\n"
            f"  git -C {BP_REPO} switch master && git -C {BP_REPO} pull --ff-only\n\n"
            "This is a correctness requirement, not hygiene. The edits are captured as a diff "
            "against Blueprint's origin/master, so editing a stale tree captures the REVERSE of "
            "everything that landed upstream meanwhile, attributes it to your transcript, and "
            "opens it as part of that request - merging it would revert other people's work. "
            "Measured on a tree one commit behind: the captured patch picked up an unrelated "
            "file with 38 removal lines. Staging refuses outright if the tree is not at "
            "origin/master, so syncing first is also the only way it will let you proceed.\n\n"
            "EACH of those transcripts gets its OWN Blueprint change request, so work through "
            "them ONE AT A TIME and tell the flow which edits belong to which transcript:\n\n"
            "  1. make the Blueprint edits for ONE transcript\n"
            "  2. run: python3 scripts/bp_stage.py --transcript <that transcript's path>\n"
            "  3. that captures those edits and resets the Blueprint tree, so repeat from 1 "
            "for the next one\n\n"
            "Staging in step 2 is not tidiness - it is the only thing that keeps one "
            "transcript's Blueprint edits separable from another's. Without it, rejecting one "
            "transcript's answer would drag back another transcript's approved Blueprint fix. "
            "Check with `python3 scripts/bp_stage.py --list` before you finish; anything marked "
            "BP updates with nothing staged is refused at send time.\n\n"
            "Do not commit or push in the Blueprint checkout yourself. The requests are opened "
            "per transcript, after the eval is approved.")


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
    """The parts of Save and Publish that go stale the moment you click something.

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

    # COUNTED ACROSS BOTH REPOS, because that is what the Change list below now shows. `n` is
    # this repo's working tree only, so while the list gained a "Blueprint docs" group the
    # sentence above it kept quoting a smaller number - two figures for one thing, on one line.
    n_bp = sum(len(v) for v in bp_staged().values())
    n_all = n + n_bp

    if n_all:
        where = ""
        if n and n_bp:
            where = f" ({n} here, {n_bp} in Blueprint)"
        elif n_bp and not n:
            where = " (in Blueprint)"
        state = (f"<span class='pill pending'>{n_all} unsent</span> "
                 f"<b>{n_all}</b> edited file(s) not yet saved{where}.")
    elif unpushed != "0":
        state = (f"<span class='pill reviewed'>saved</span> Saved, but "
                 f"<b>{unpushed}</b> change(s) have not been sent in yet — do Part 2.")
    else:
        state = ("<span class='pill pushed'>all sent</span> Nothing waiting. "
                 "Everything reviewed has been sent in.")

    # GROUPED, and the Blueprint group folded in from what used to be its own panel below. A
    # reviewer asked for this: two panels listing what is about to go out, one per repo, with the
    # second one carrying a paragraph explaining itself. Labels only now - the grouping IS the
    # explanation, and the two repos are visibly separate without a sentence saying so.
    paths = [porcelain_path(l) for l in changed]
    groups = [
        ("Reviews", [x for x in paths if x.startswith("transcripts/")]),
        ("Agent files", [x for x in paths if x.startswith("Knowledge-")]),
    ]
    other = [x for x in paths
             if not x.startswith("transcripts/") and not x.startswith("Knowledge-")]
    if other:
        groups.append(("Other", other))

    # Blueprint lives in a different checkout, so it can never appear in `changed`. It comes from
    # the per-transcript staged patches instead.
    bp_rows = []
    staged = bp_staged()
    for rel in bp_batch():
        got = staged.get(rel) or []
        if got:
            bp_rows += [html.escape(f) for f in got]
        else:
            # Kept as a row rather than a paragraph: a transcript marked BP updates with nothing
            # attributed is refused at send time, and that has to be visible before then.
            bp_rows.append(f"<span class=warn>{html.escape(Path(rel).name)} — nothing staged"
                           "</span>")
    if bp_rows:
        groups.append(("Blueprint docs", bp_rows))

    def grp(label, rows):
        shown = rows[:12]
        extra = f"<li>… and {len(rows) - 12} more</li>" if len(rows) > 12 else ""
        return (f"<div class=fgrp>{label}</div><ul>"
                + "".join(f"<li>{r}</li>" for r in shown) + extra + "</ul>")

    files = ("".join(grp(l, r) for l, r in groups if r)
             or "<div class=hint style='margin-top:6px'>Nothing edited yet — review something on "
                "<b>My Transcripts</b> first.</div>")

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
            "<div class=hint>Sending in covers all of these. Discarding rewinds to just before the "
            "save selected, and always leaves a recovery point.</div></details>")
    else:
        saves_html = ("<div class=saves><span class=hint>Nothing saved and unsent."
                      "</span></div>")
    # The change list now lives INSIDE the state bar, collapsed. It was a permanently-open
    # panel between the "Publish your reviews" heading and Part 1, so the first actual step
    # started well down the page - and the list is reference material, not something you act on.
    #
    # Built into `state` deliberately: the JS refresh replaces #gitstate's entire innerHTML after
    # every action, so a panel composed separately in git_page would disappear on first use.
    state = (state
             + "<details class=whatsent><summary><b>Change list</b></summary>"
             + "<div id=gitfiles>" + files + "</div></details>")
    return {"state": state, "files": files, "saves": saves_html, "unsent": n_all}


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


def drifted_files():
    """Knowledge files on main that Foundry does not have yet. [] if in sync or unknowable.

    Byte-compares, not size-compares: an equal-length edit is invisible to a size check, which is
    how Docusaurus-OpsCenterAdoption.md sat drifted for five days while the drift check reported
    everything in sync.
    """
    import hashlib
    # WHAT SHIPS FROM Knowledge-Shared COMES FROM sources.json, NOT from the folder listing.
    #
    # Foundry keys a file by its BASENAME, so two local files called _START_HERE.md are the same
    # file to it. Knowledge-Shared/_START_HERE.md is the shared folder's own routing guide and is
    # NOT uploaded anywhere - but a folder-based scan compares it against OT-OpsCenter's
    # _START_HERE.md, finds them different, and calls it drift. Auto-publishing that would
    # overwrite five agents' routing guides with the wrong file.
    #
    # Caught before it ran, on the first call: drifted_files() returned
    # Knowledge-Shared/_START_HERE.md alongside two real ones. upload_targets is the authority on
    # which shared files ship and where, and it lists only Conf-OneTylerTickets.md.
    try:
        shared = {k: v for k, v in
                  (json.loads((REPO / "scripts" / "sources.json").read_text(encoding="utf-8"))
                   .get("upload_targets") or {}).items() if not k.startswith("_")}
    except Exception:                                                 # noqa: BLE001
        shared = {}

    out = []
    for folder, cols in FOLDER_COLLECTION.items():
        d = REPO / folder
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            rel = f"{folder}/{f.name}"
            if folder == "Knowledge-Shared":
                if rel not in shared:
                    continue                      # not a file that ships; see the note above
                cols = shared[rel]
            local = f.read_bytes()
            for col in cols:
                try:
                    recs = _foundry_get(
                        f"/api/tenant-knowledge-base/collections/{col}/files")
                except Exception:                                     # noqa: BLE001
                    return []
                rec = next((r for r in (recs or []) if r.get("fileName") == f.name), None)
                if rec is None:
                    out.append(rel)
                    break
                if rec.get("fileSize") != len(local):
                    out.append(rel)
                    break
                try:
                    got = _foundry_raw(
                        f"/api/tenant-knowledge-base/collections/{col}/files/{rec['id']}/download")
                except Exception:                                     # noqa: BLE001
                    return []
                if hashlib.sha256(got).hexdigest() != hashlib.sha256(local).hexdigest():
                    out.append(rel)
                    break
    return sorted(set(out))


def autopublish_drift():
    """Publish anything main has that Foundry does not. Returns a message, or "" if nothing to do.

    WHY THE SYNC DOES THIS AND NOT ONLY THE MERGE BUTTON.
    ----------------------------------------------------
    Merge publishes - but only a merge done HERE. A merge on github.com moves main and this app
    never hears about it, so the agents stay stale with nothing to indicate it. That is not a
    hypothetical: the merge that produced today's TCP-KB-Identity drift was done on the website.
    Asking people to merge in one particular place to keep the agents current is a rule that will
    be broken, and the failure is silent.

    So the periodic sync closes it. It already fast-forwards main, which is exactly the moment new
    content arrives, and it runs every 30 minutes and on tab focus.

    ADMIN ONLY. Uploading changes what live agents tell customers, and publishing is an admin
    responsibility - a contributor's sync must not push anything. It also only ever uploads what
    is already on origin/main, because preflight_upload.py refuses anything else.
    """
    if not is_admin() or not os.environ.get("FOUNDRY_API_KEY"):
        return ""
    files = drifted_files()
    if not files:
        return ""
    ok, msg = publish_after_merge(files)
    head = (f"Foundry was behind on {len(files)} file(s) — published now "
            "(a merge made outside this app does not reach the agents on its own):\n"
            + "\n".join("  " + f for f in files) + "\n\n")
    return head + msg


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
            return True, ("In-progress work is left exactly as it is, so "
                          + (f"{behind} changes" if behind > 1 else "1 change")
                          + " other people sent in is not on this copy yet. It arrives on its "
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
        return True, ("There are unsaved edits, so the newest copies of a few files are not in "
                      f"yet ({behind} waiting). Nothing was changed or discarded. They come in "
                      "on their own once saved.")
    return True, (f"Brought in {behind} updates from the shared copy." if behind > 1
                  else "Brought in 1 update from the shared copy.")


def merged_knowledge_files(number):
    """Knowledge files this change request touched. Returns a sorted list of repo-relative paths.

    ASKS GITHUB rather than diffing git, because with a REBASE merge there is no merge commit to
    diff against. The tip's first parent is the previous REBASED COMMIT, not main's old tip - so
    `git diff HEAD^1 HEAD` sees only the last commit of the request. Measured on #47, a
    three-commit request touching two knowledge files: the git diff found one of them, and would
    have published half the change while reporting success.

    `publish_to_foundry.py --since` has the same class of problem from the other direction - it
    guesses the comparison point from the reflog, which is wrong as soon as two merges land close
    together.

    The PR's own file list has neither problem: it is what the request changed, by definition.
    """
    files, err = pr_files(number, force=True)   # knowledge repo only; see merged_knowledge_files
    if err or not files:
        return []
    out = []
    for f in files:
        path = f.get("filename") or ""
        top = path.split("/")[0] if "/" in path else ""
        if (top.startswith("Knowledge-") and path.endswith(".md")
                and f.get("status") != "removed" and (REPO / path).is_file()):
            out.append(path)
    return sorted(set(out))


def publish_after_merge(files):
    """Upload the merged knowledge files to Foundry. Returns (ok, message).

    WHY THIS IS PART OF MERGE, not a step afterwards.
    -----------------------------------------------
    Merging is the moment `main` gets ahead of the live agents, and nothing else notices: a
    knowledge file only reaches an agent when somebody uploads it, so a merge without an upload
    leaves the agent answering from old text while the repo looks correct. That gap has been
    real - a 6.5-hour window on 2026-08-25 - and it was only ever closed by somebody remembering.
    Merge is an ADMIN action and publishing is an admin responsibility, so the button that makes
    a change permanent is the right place for it.

    Everything still runs through publish_to_foundry.py rather than being reimplemented here,
    which means the guarantees come along: it refuses any file whose bytes differ from
    origin/main, uploads every batch before triggering ONE consolidated sync, and verifies by
    retrieval rather than trusting ingestionStatus.
    """
    if not files:
        return True, "No knowledge files in this request, so nothing to publish."
    if not os.environ.get("FOUNDRY_API_KEY"):
        return False, ("Merged, but FOUNDRY_API_KEY is not set in the environment this server "
                       "was started from, so the upload did not run. The agents are still "
                       "answering from the old content.\n\nStart the server from a shell that "
                       "has the key, then:\n  python3 scripts/publish_to_foundry.py --files "
                       + " ".join(files))
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "publish_to_foundry.py"),
         "--files", *files, "--yes", "--timeout-min", "12"],
        cwd=REPO, capture_output=True, text=True, timeout=900)
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    tail = "\n".join(out.splitlines()[-24:])
    if r.returncode != 0:
        return False, ("Merged, but the Foundry upload FAILED. The repo is ahead of the live "
                       "agents until this is fixed:\n\n" + tail)
    return True, tail


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


# ---------------------------------------------------------------------------------------------
# Provenance: which change requests came from THIS flow
#
# Needed because the two repos have opposite problems. The knowledge repo carries its own
# machinery work alongside review batches, and Blueprint is a shared docs repo with a lot of
# unrelated traffic - so "every request in the repo" is the wrong answer in both directions.
#
# TWO INDEPENDENT MARKERS, and both are load-bearing:
#
#   * The LABEL is authoritative and visible on GitHub itself, so the set is identifiable
#     without this tool. It only exists from 2026-08-29, so it is absent from everything
#     merged before then.
#   * The BRANCH PREFIX covers that history. `headRefName` survives the branch being deleted
#     at merge - verified on #84, whose branch 404s on the branches API while the PR record
#     still reports its name - so it stays readable indefinitely.
#
# Either marker qualifies a request. Requiring both would hide the back-catalogue; requiring
# only the label would make the history start empty on the day it shipped.
REVIEW_LABEL = "onetyler-review"
REVIEW_LABEL_DESC = "Opened by the OneTyler transcript-review flow"
REVIEW_LABEL_COLOR = "5B4B8A"
KB_BRANCH_PREFIX = "review/"
BP_BRANCH_PREFIX = "kb-review/"


def _repo_args(remote):
    return ["--repo", remote] if remote else []


def ensure_label(remote=""):
    """Create the tracking label if it is not there yet. (ok, message).

    Lazy on purpose: called when a request is opened, never on page load. Creating a label in
    Blueprint is a write to somebody else's repo, and it should happen as part of an action the
    user took there rather than as a side effect of viewing a dashboard.
    """
    rc, out = gh("label", "create", REVIEW_LABEL, "--description", REVIEW_LABEL_DESC,
                 "--color", REVIEW_LABEL_COLOR, *_repo_args(remote), timeout=60)
    if rc == 0:
        return True, "label created"
    if "already exists" in (out or "").lower():
        return True, "label present"
    return False, (out or "").strip()[:200]


def tag_pr(ref, remote=""):
    """Mark a change request as belonging to this flow. (ok, message). NEVER fatal.

    A request that could not be tagged is still a correct request, and the branch prefix means
    it will appear in the history regardless - so a failure here is reported and nothing more.
    Labelling Blueprint may need more rights than a contributor has, which is the expected
    failure and not worth blocking a send over.
    """
    ok, why = ensure_label(remote)
    if not ok:
        return False, f"could not create the {REVIEW_LABEL} label: {why}"
    rc, out = gh("pr", "edit", str(ref), "--add-label", REVIEW_LABEL,
                 *_repo_args(remote), timeout=90)
    return (True, f"tagged {REVIEW_LABEL}") if rc == 0 else (False, (out or "").strip()[:200])


def _from_this_flow(pr, prefix):
    labels = {str(x.get("name", "")).lower() for x in (pr.get("labels") or [])}
    return (REVIEW_LABEL in labels
            or str(pr.get("headRefName", "")).startswith(prefix))


MERGED_FIELDS = ("number,title,author,mergedAt,mergedBy,headRefName,additions,deletions,"
                 "changedFiles,url,labels")

_MPR_CACHE = {"at": 0.0, "rows": None, "err": ""}
_MPR_TTL = 5 * 60.0


def merged_prs(force=False, limit=100):
    """Merged change requests this flow opened, both repos, newest first. (rows, err).

    Each row is the `gh` record plus `repo` ("" for knowledge, "bp" for Blueprint), so the
    caller can link into the diff viewer for the right repo.

    Cached for five minutes. A merged request never changes, so the only thing a refetch can
    discover is a NEW merge - and this is the page where merging happens, so the merge actions
    drop the cache themselves rather than making the page poll for their own effects.
    """
    now = time.monotonic()
    if not force and _MPR_CACHE["rows"] is not None and (now - _MPR_CACHE["at"]) < _MPR_TTL:
        return _MPR_CACHE["rows"], _MPR_CACHE["err"]
    if not shutil.which("gh"):
        return [], "The GitHub CLI (gh) is not installed, so history cannot be listed."
    rows, errs = [], []
    targets = [("", "", KB_BRANCH_PREFIX)]
    if bp_available()[0]:
        targets.append(("bp", BP_REMOTE, BP_BRANCH_PREFIX))
    for tag, remote, prefix in targets:
        rc, out = gh("pr", "list", "--state", "merged", "--limit", str(limit),
                     "--json", MERGED_FIELDS, *_repo_args(remote), timeout=120)
        if rc != 0:
            errs.append((out or "").strip()[:200])
            continue
        try:
            got = json.loads(out or "[]")
        except json.JSONDecodeError:
            errs.append(f"{remote or 'the knowledge repo'} returned something that is not JSON")
            continue
        for pr in got:
            if _from_this_flow(pr, prefix):
                pr["repo"] = tag
                rows.append(pr)
    # mergedAt is ISO-8601 UTC, so a plain string sort is a correct chronological sort and
    # needs no parsing. Blank sorts last, which is where an unmergeable oddity belongs.
    rows.sort(key=lambda x: x.get("mergedAt") or "", reverse=True)
    err = " / ".join(errs)
    _MPR_CACHE.update(at=now, rows=rows, err=err)
    return rows, err


def drop_merged_cache():
    _MPR_CACHE.update(at=0.0, rows=None, err="")


def bp_open_prs():
    """Open change requests in the Blueprint repo. (list, err).

    Only the ones this workflow opened - branches prefixed `kb-review/`. Blueprint is a shared docs
    repo with its own traffic, and listing everybody's requests here would make this page a second,
    worse view of a repo it is not responsible for.
    """
    if not shutil.which("gh"):
        return [], ""
    ok, _ = bp_available()
    if not ok:
        return [], ""
    r = subprocess.run(["gh", "pr", "list", "--repo", BP_REMOTE, "--state", "open",
                        "--limit", "30", "--json", PR_FIELDS],
                       cwd=REPO, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        return [], (r.stderr or r.stdout).strip()[:200]
    try:
        prs = json.loads(r.stdout)
    except json.JSONDecodeError:
        return [], "could not parse the Blueprint request list"
    return [x for x in prs
            if str(x.get("headRefName", "")).startswith("kb-review/")], ""


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


_PRF_CACHE = {}
_PRF_TTL = 120.0

# A single file's diff is truncated past this many lines, and a request past this many files.
# GitHub does the same thing and for the same reason: a 4000-line patch rendered inline is not a
# review aid, it is a wall. The count of what was hidden is always shown - a silent truncation
# would be the worst outcome, since a reviewer would believe they had seen everything.
#
# `?full=1` lifts BOTH caps for one page load. The default stays capped because most visits want
# the first screen of a change, but the uncapped view has to exist here rather than only on
# GitHub, or the cap turns into a dead end on the requests most worth reading.
PR_DIFF_MAX_LINES = 600
PR_DIFF_MAX_FILES = 40


def pr_files(number, force=False, repo=""):
    """Per-file diffs for one change request. Returns (files, err).

    Each entry carries `patch` - a unified diff - plus additions, deletions and status. Cached
    for two minutes: a PR's diff only changes when someone pushes to it, and the page is read
    far more often than that.
    """
    key = f"{repo}:{number}"
    now = time.time()
    hit = _PRF_CACHE.get(key)
    if hit and not force and (now - hit[0]) < _PRF_TTL:
        return hit[1], None
    if not shutil.which("gh"):
        return None, "The GitHub CLI (gh) is not installed, so diffs cannot be fetched."
    target = BP_REMOTE if repo == "bp" else ":owner/:repo"
    rc, out = gh("api", f"repos/{target}/pulls/{number}/files", "--paginate", timeout=90)
    if rc != 0:
        return None, out.strip()[:300]
    try:
        files = json.loads(out)
    except json.JSONDecodeError as e:
        return None, f"could not parse the file list: {e}"
    if not isinstance(files, list):
        return None, "unexpected response shape from the files API"
    _PRF_CACHE[key] = (now, files)
    return files, None


def render_patch(patch, anchor, full=False, more_url=""):
    """A unified diff as a two-gutter table, the way GitHub shows it.

    Real line numbers on both sides, because "line 91" in a review comment has to mean something.
    A unified patch only states them in the hunk header (@@ -42,7 +42,7 @@), so both counters are
    tracked from there: a context line advances both, a deletion advances only the old side, an
    addition only the new.
    """
    if not patch:
        return ("<p class=sub>No textual diff &mdash; usually a binary file, a pure rename, or a "
                "file too large for the API to return.</p>")
    rows = []
    old = new = 0
    shown = 0
    total = patch.count("\n") + 1
    cap = float("inf") if full else PR_DIFF_MAX_LINES
    for line in patch.split("\n"):
        if shown >= cap:
            break
        if line.startswith("@@"):
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)", line)
            if m:
                old, new = int(m.group(1)), int(m.group(2))
            rows.append("<tr class=dhunkrow><td class=dln></td><td class=dln></td>"
                        f"<td class=dcode>{html.escape(line)}</td></tr>")
            shown += 1
            continue
        if line.startswith("+"):
            rows.append("<tr class=dadded><td class=dln></td>"
                        f"<td class=dln>{new}</td>"
                        f"<td class=dcode>{html.escape(line)}</td></tr>")
            new += 1
        elif line.startswith("-"):
            rows.append(f"<tr class=dremoved><td class=dln>{old}</td>"
                        "<td class=dln></td>"
                        f"<td class=dcode>{html.escape(line)}</td></tr>")
            old += 1
        elif line.startswith("\\"):
            # "\ No newline at end of file" - real diff output, belongs to neither side.
            rows.append("<tr class=dctx><td class=dln></td><td class=dln></td>"
                        f"<td class=dcode>{html.escape(line)}</td></tr>")
        else:
            rows.append(f"<tr class=dctx><td class=dln>{old}</td>"
                        f"<td class=dln>{new}</td>"
                        f"<td class=dcode>{html.escape(line)}</td></tr>")
            old += 1
            new += 1
        shown += 1

    out = ["<div class=difftable><table>", "".join(rows), "</table></div>"]
    if shown < total:
        # The whole diff is one click away IN HERE, not only on GitHub. Leaving GitHub as the
        # sole way to read a long patch made the cap a dead end on exactly the requests worth
        # reading - a large one.
        out.append(f"<p class=sub>Showing the first {shown:,} of {total:,} diff lines. "
                   + (f"<a href='{html.escape(more_url)}'>Show all {total:,} lines</a> &middot; "
                      if more_url else "")
                   + f"<a href='{html.escape(anchor)}' target=_blank rel=noopener>"
                     "open the file on GitHub &rarr;</a></p>")
    return "".join(out)


def pr_diff_page(number, force=False, repo="", full=False):
    """GitHub-style 'Files changed' for one change request. Read-only.

    Serves MERGED requests as readily as open ones - the files endpoint does not care - which is
    what makes the history list on /prs a real archive rather than a set of links off to GitHub.
    """
    if not is_admin():
        return page("Change Requests",
                    "<div class=lg><h2 class=sec>Change Requests</h2>"
                    "<div class='bar bnr-note'>Admins only.</div></div>", active="prs")
    tgt = BP_REMOTE if repo == "bp" else ":owner/:repo"
    rc, meta_raw = gh("api", f"repos/{tgt}/pulls/{number}",
                      "-q", '[.title, .user.login, .base.ref, .head.ref, .state, '
                            '.additions, .deletions, .changed_files, .html_url, '
                            '(.merged_at // ""), (.merged_by.login // "")] | @tsv',
                      timeout=60)
    if rc != 0:
        return page("Change Requests",
                    "<div class=lg><h2 class=sec>Change Requests</h2>"
                    f"<div class='bar bnr-done'>{html.escape(meta_raw.strip()[:300])}</div>"
                    "<p><a href='/prs'>Back to change requests</a></p></div>", active="prs")
    parts = (meta_raw.strip().split("\t") + [""] * 11)[:11]
    (title, who, base, head, state, adds, dels, nfiles, url,
     merged_at, merged_by) = parts

    # `state` is only ever "open" or "closed", so a merged request reports "closed" - which reads
    # as abandoned. Say merged, and by whom, since that is the whole point of the history view.
    qs = f"diff={html.escape(str(number))}" + ("&repo=bp" if repo == "bp" else "")
    if merged_at:
        stateline = (f"<span class='pill reviewed'>merged</span> {html.escape(merged_at[:10])}"
                     + (f" by {html.escape(merged_by)}" if merged_by else ""))
    else:
        stateline = f"<span class='pill pending'>{html.escape(state or 'open')}</span>"

    files, err = pr_files(number, force=force, repo=repo)
    body = [
        "<div style='display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:6px'>"
        f"<h2 class=sec style='margin:0'>#{html.escape(str(number))} "
        f"{html.escape(title[:110])}</h2>"
        # Both flags carried through, or Refresh silently switches repo (fetching the KB request
        # with the same number) and drops back to the capped view.
        f"<a href='/prs?{qs}{'&full=1' if full else ''}&refresh=1' "
        "style='margin-left:auto;text-decoration:none'>"
        f"<button class=sec>{icon('refresh', 15)} Refresh</button></a></div>",
        f"<p class=sub><a href='/prs'>Change requests</a> / <b>#{html.escape(str(number))}</b> "
        + ("<span class='pill suggested'>Blueprint</span> " if repo == "bp" else "")
        + f"&middot; {html.escape(who)} &middot; <code>{html.escape(head)}</code> &rarr; "
        f"<code>{html.escape(base)}</code> &middot; {stateline} &middot; "
        f"<span class=dplus>+{html.escape(adds)}</span> "
        f"<span class=dminus>&minus;{html.escape(dels)}</span> across "
        f"{html.escape(nfiles)} file(s) &middot; "
        f"<a href='{html.escape(url)}' target=_blank rel=noopener>open on GitHub &rarr;</a></p>",
    ]
    if err:
        body.append(f"<div class='bar bnr-done'>{html.escape(err)}</div>")
        return page("Change Requests", "<div class=lg>" + "".join(body) + "</div>", active="prs")

    full_url = f"/prs?{qs}&full=1"
    fcap = len(files) if full else PR_DIFF_MAX_FILES
    shown_files = files[:fcap]

    # A contents list first. On a 20-file request, scrolling to find the one file you care about
    # is the actual friction, and it is the thing GitHub's sidebar solves.
    body.append("<div class=tblcard><table><tr><th>File</th><th>Change</th>"
                "<th style='text-align:right'>Diff</th></tr>")
    for f in shown_files:
        name = f.get("filename", "?")
        st = f.get("status", "")
        body.append(
            f"<tr><td><a href='#f-{html.escape(_slug(name))}'>{html.escape(name)}</a></td>"
            f"<td><span class='pill {_status_pill(st)}'>{html.escape(st)}</span></td>"
            f"<td style='text-align:right'><span class=dplus>+{f.get('additions', 0)}</span> "
            f"<span class=dminus>&minus;{f.get('deletions', 0)}</span></td></tr>")
    body.append("</table></div>")
    if len(files) > len(shown_files):
        body.append(f"<p class=sub>{len(files) - len(shown_files)} further file(s) not shown "
                    f"&mdash; <a href='{html.escape(full_url)}'>show all {len(files)} "
                    f"file(s)</a> &middot; <a href='{html.escape(url)}/files' target=_blank "
                    "rel=noopener>on GitHub &rarr;</a></p>")
    elif full:
        body.append(f"<p class=sub>Complete diff &mdash; {len(files)} file(s), nothing "
                    f"truncated. <a href='/prs?{qs}'>Back to the short view</a></p>")

    for f in shown_files:
        name = f.get("filename", "?")
        body.append(
            f"<h3 class=angroup id='f-{html.escape(_slug(name))}'>{html.escape(name)}</h3>"
            f"<p class=sub style='margin:0 0 8px'>"
            f"<span class=dplus>+{f.get('additions', 0)}</span> "
            f"<span class=dminus>&minus;{f.get('deletions', 0)}</span> &middot; "
            f"{html.escape(f.get('status', ''))} &middot; "
            f"<a href='{html.escape(f.get('blob_url') or url)}' target=_blank rel=noopener>"
            "view whole file &rarr;</a></p>")
        body.append(render_patch(f.get("patch"), (f.get("blob_url") or url),
                                 full=full, more_url=full_url))

    return page("Change Requests", "<div class=lg>" + "".join(body) + "</div>", active="prs")


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:80]


def _status_pill(st):
    return {"added": "reviewed", "removed": "bad", "renamed": "suggested",
            "modified": "pending"}.get(st, "excluded")


def _ago(iso):
    """'3d' / '2h' / 'today' from an ISO-8601 UTC stamp. Empty string if unparseable."""
    if not iso:
        return ""
    from datetime import timezone as _tz
    try:
        then = datetime.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=_tz.utc)
    except ValueError:
        return ""
    # Aware both sides. `utcnow()` is deprecated in 3.12 and, worse, returns a NAIVE value that
    # subtracts cleanly against a naive parse while being wrong the moment either side gains a
    # timezone - a bug that only shows up as a few hours' drift.
    secs = (datetime.now(_tz.utc) - then).total_seconds()
    if secs < 3600:
        return f"{int(secs // 60)}m"
    if secs < 86400:
        return f"{int(secs // 3600)}h"
    return f"{int(secs // 86400)}d"


def history_html(force=False):
    """Merged change requests from this flow, both repos. Collapsed by default.

    Collapsed because it answers a question nobody asks while merging - "what went in, and can I
    read the diff again?" - and the open requests above it are the working surface. Expanded, it
    pushes them off the screen within a week.

    Every row links into the diff viewer rather than out to GitHub: the diffs are readable here,
    and a merged request's files endpoint serves them exactly as it does for an open one.
    """
    rows, err = merged_prs(force=force)
    n = len(rows)
    out = ["<details class=histbox><summary><b>History</b> "
           f"<span class=sub>{n} merged</span></summary>"]
    if err:
        out.append(f"<div class=hint>Partly unavailable: {html.escape(err)}</div>")
    if not rows:
        out.append("<p class=sub>No merged requests from this flow yet.</p></details>")
        return "".join(out)
    out.append("<div class=tblcard><table><tr><th>Request</th><th>Repo</th>"
               "<th>Merged</th><th>By</th><th style='text-align:right'>Change</th>"
               "<th></th></tr>")
    for pr in rows:
        rep = pr.get("repo") or ""
        pill = ("<span class='pill suggested'>Blueprint</span>" if rep == "bp"
                else "<span class='pill reviewed'>Knowledge</span>")
        by = ((pr.get("mergedBy") or {}).get("login")
              or (pr.get("author") or {}).get("login") or "")
        when = (pr.get("mergedAt") or "")[:10]
        ago = _ago(pr.get("mergedAt"))
        qrep = "&repo=bp" if rep == "bp" else ""
        out.append(
            f"<tr><td><a href='{html.escape(pr.get('url', ''))}' target=_blank rel=noopener>"
            f"#{pr.get('number', '?')}</a> {html.escape(str(pr.get('title', ''))[:78])}</td>"
            f"<td>{pill}</td>"
            f"<td>{html.escape(when)}"
            + (f" <span class=sub>{html.escape(ago)}</span>" if ago else "")
            + "</td>"
            f"<td>{html.escape(by)}</td>"
            f"<td style='text-align:right'><span class=dplus>+{pr.get('additions', 0)}</span> "
            f"<span class=dminus>&minus;{pr.get('deletions', 0)}</span></td>"
            f"<td style='text-align:right'><a href='/prs?diff={pr.get('number')}{qrep}'>"
            f"Diff ({pr.get('changedFiles', 0)})</a></td></tr>")
    out.append("</table></div></details>")
    return "".join(out)


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
            "<button class=sec>" + icon("refresh", 15) + " Refresh PRs</button></a>"
            f"<span class=fresh id=freshness data-age='{prs_age}' data-kind=prs></span></div>"
            "<p class=sub style='margin:-14px 0 20px'>Refreshes by itself when it is more "
            "than 30 minutes stale, and on every return to this tab.</p>"]
    if err:
        body.append(f"<div class='bar bnr-done'>{html.escape(err)}</div>")
    # Blueprint requests this workflow opened, listed alongside. They ship WITH the knowledge
    # change - most indexed knowledge is derived from Blueprint, so merging one without the other
    # leaves a fix that the next reconciliation undoes. Shown here so that pairing is visible
    # rather than being something somebody has to remember.
    bprs, bperr = bp_open_prs()
    if not prs and not bprs and not err:
        body.append("<div class=card><h3>Nothing open</h3>"
                    "<p class=sub>Every change request has been merged or closed.</p></div>")
    if bprs:
        body.append("<div class='bar bnr-note'><b>"
                    + str(len(bprs)) + " Blueprint request(s) belong with these.</b> Most "
                    "indexed knowledge is derived from Blueprint, so a knowledge fix that ships "
                    "without its Blueprint counterpart is reverted at the next reconciliation. "
                    "Merge them together.</div>")
    for pr in bprs:
        n_files = pr.get("changedFiles", 0)
        state = (pr.get("mergeStateStatus") or "UNKNOWN").upper()
        st_label, st_cls = MERGE_STATE.get(state, ("state unknown", "excluded"))
        cls, _why = pr_checks(pr)
        chk = {"passing": "<span class='pill reviewed'>checks passed</span>",
               "failing": "<span class='pill bad'>checks failed</span>",
               "running": "<span class='pill pending'>checks running</span>",
               "none": "<span class='pill excluded'>no checks</span>"}[cls]
        body.append(
            "<div class=card>"
            f"<h3><a href=\"{html.escape(pr['url'])}\" target=_blank rel=noopener>"
            f"#{pr['number']}</a> {html.escape(pr['title'][:110])}</h3>"
            "<p class=sub><span class='pill suggested'>Blueprint</span> "
            f"{html.escape(pr['author']['login'])} &middot; "
            f"<code>{html.escape(pr['headRefName'])}</code> &middot; "
            f"+{pr['additions']} &minus;{pr['deletions']} across {n_files} file(s)</p>"
            f"<div class=prpills>{chk}<span class='pill {st_cls}'>{st_label}</span></div>"
            "<div class=hint>Blueprint requires its own CI to pass and no approvals, so "
            "<b>Merge when checks pass</b> queues GitHub's auto-merge rather than waiting "
            "here.</div>"
            f"<div class=stepacts>"
            f"<a href=\"/prs?diff={pr['number']}&repo=bp\">"
            f"<button class=sec>Files changed ({n_files})</button></a>"
            f"<button onclick=\"bpMerge(this,{pr['number']},"
            f"'{html.escape(pr['title'][:60])}')\">Merge when checks pass</button>"
            f"<a href=\"{html.escape(pr['url'])}\" target=_blank rel=noopener>"
            "<button class=sec>Open on GitHub</button></a></div></div>")
    if bperr:
        body.append(f"<div class=hint>Blueprint requests could not be listed: "
                    f"{html.escape(bperr)}</div>")
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
        # APPROVE IS NOT A STEP ON THE WAY TO MERGE. It does the one thing Merge cannot: sanction
        # somebody else's work while leaving the merge with them.
        #
        # An admin can always just merge - enforce_admins is false - so if the goal is "get this
        # in", Merge alone is enough and Approve is redundant. The case Approve exists for is a
        # CONTRIBUTOR's request: approving unblocks it so they merge their own work. Merging it
        # for them takes the last step of their own change away, and they never see the flow
        # close.
        #
        # Only ever shown on someone else's request - GitHub refuses self-approval, so on your own
        # it would be a button that can only error.
        if not mine and not approved:
            acts.append(f"<button class=sec onclick=\"prDo(this,'approve',{pr['number']})\" "
                        "title='Sanction it and leave the merge to the author — use this on a "
                        "contributor&#39;s request'>Approve, they merge</button>")

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
                        "title='Merge using the admin override, which skips the required "
                        "approval an author cannot give themselves'>Merge anyway</button>")
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
            selfnote = ("<div class=hint style='margin-top:8px'>This is the current user's change "
                        "request, so a plain merge is refused: an approval is required and "
                        "GitHub does not let anyone approve their own. <b>Merge anyway</b> "
                        "uses the admin override, which skips that gate &mdash; reasonable on "
                        "own work, and the only way through on a repo with one code "
                        f"owner.{behind}</div>")
        elif state == "BLOCKED":
            selfnote = ("<div class=hint style='margin-top:8px'>Somebody else's request. Two "
                        "different options: <b>Approve, they merge</b> unblocks it and "
                        "leaves the last step with them &mdash; right for a contributor's work. "
                        "<b>Merge</b> puts it in directly, which is quicker but closes their "
                        "change for them.</div>")
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
            + (f"<div class='hint fdrynote'>Merging <b>publishes</b> this to "
               f"<b>{html.escape(', '.join(kind['cols']))}</b> and verifies it by retrieval. "
               "One button, one outcome &mdash; there is nothing to remember afterwards.</div>"
               if kind["kb"] else
               "<div class=hint>Nothing to publish — this one does not touch knowledge "
               "files.</div>")
            + f"{selfnote}"
            f"<div class=stepacts>{''.join(acts)}"
            # Files changed sits BEFORE "Open on GitHub" on purpose: reading the diff is what
            # you do before merging, and it should not require leaving the app to do it.
            f"<a href=\"/prs?diff={pr['number']}\">"
            f"<button class=sec>Files changed ({pr['changedFiles']})</button></a>"
            f"<a href=\"{html.escape(pr['url'])}\" target=_blank rel=noopener>"
            "<button class=sec>Open on GitHub</button></a></div>"
            "</div>")
    body.append(history_html(force=force))
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
                      f"that this `gh` account is not on the onetyler-tcp-pm-admins team.\n\n{err}")
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
                  "  The restore point above is the undo for this."]
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
            "<button class=sec>" + icon("refresh", 15) + " Refresh</button></a></div>")


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
            "only the fields to revert &mdash; the payload is built from the <b>live</b> "
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
            glyph = icon("folder", 17) if ty == "dir" else icon("file_document_outline", 17)
            sz = "" if ty == "dir" else f"{int(size):,} B"
            body.append(f"<tr><td>{glyph} <a href=\"{link}\">{html.escape(name)}</a></td>"
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
            f"<p class=sub style='margin:0 0 22px'>Nightly snapshots of the router, the five agent "
            f"configs and the collection file records &mdash; "
            f"<code>{html.escape(d['repo'])}</code>.</p>"]

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
                       "Weekly full git bundles of the knowledge repo, kept as release assets.")
                # THE HEADLINE FACT, not a detail. A snapshot used to pin config precisely and
                # say nothing about which knowledge commit accompanied it, so a day could not be
                # restored as a unit - config and knowledge were two backups of one system. This
                # tile is the answer to "can I actually roll back to this day".
                + tile("Restorable as a day",
                       "yes" if m.get("restorable") else "no",
                       "green" if m.get("restorable") else "red",
                       "Green means the knowledge commit is pinned AND every live Foundry file "
                       "matches it, so config and knowledge can be put back together. Red means "
                       "the commit is unknown, or a file was edited in Foundry and those exact "
                       "bytes exist nowhere.",
                       (f"knowledge @ {html.escape((m.get('kb_repo') or {}).get('commit','')[:8])}"
                        if (m.get("kb_repo") or {}).get("commit") else "not pinned"))
                + "</div>")

    drifted = m.get("kb_files_drifted") or []
    if drifted:
        body.append("<div class='bar bnr-router'><b>"
                    + str(len(drifted))
                    + " live file(s) do not match the pinned commit</b>, so this day cannot be "
                      "restored exactly. Those bytes were written in Foundry and exist nowhere "
                      "else."
                    + "".join(f"<br>&nbsp;&nbsp;<code>{html.escape(x.get('collection',''))}/"
                              f"{html.escape(x.get('file',''))}</code> — "
                              f"{html.escape(x.get('why',''))}" for x in drifted[:10])
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
                    "<p class=sub style='margin:0 0 8px'>Written every run, changes or not.</p>"
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
                    "<p class=sub style='margin:0 0 8px'>Compared by content hash against the "
                    + html.escape(d["dates"][0]) + " snapshot. Click a row for a live diff.</p>")
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
                    "<p class=sub style='margin:0 0 8px'>Live config vs the "
                    + html.escape(newest) + " snapshot. Roll back single fields or the KB "
                    "binding.</p>"
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
        body.append(f"<tr><td>{icon('folder', 17)} <a href='/backups?browse=snapshots/{html.escape(date)}'>"
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
        "snapshot is descriptive: it records what should exist.</td></tr>"
        "</table></div>"
        "<div class='bar bnr-note'>Every write takes a Foundry version first &mdash; that version is the undo.</div>")

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
            "<button class=sec>" + icon("refresh", 15) + " Refresh</button></a>"
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


# Paths that change how a conversation is ROUTED rather than what an answer says. A bad content
# edit gives one wrong answer; a bad routing edit misroutes every conversation, and the transcript
# that reveals it looks like a content problem, so it gets misdiagnosed. Hence its own warning.
ROUTER_PATHS = ("team-config/", "README.md")

# Set by a completed eval, read by the "pr" action. Keyed on the exact candidate content that was
# evaluated, so editing a knowledge file AFTER the eval invalidates the approval - otherwise a
# reviewer could evaluate one version and send in another, which is the one way this gate could
# be defeated without meaning to.
#
# Process-lifetime only, deliberately. It is a "did you look at the answers" gate, not an audit
# trail, and persisting it would mean an approval surviving a restart the reviewer did not connect
# to it.
def eval_ran_fingerprint():
    """The candidate fingerprint the newest eval run actually evaluated, or None.

    ON DISK, NOT IN MEMORY. This used to be a module-level dict, which meant the send gate
    forgot every eval the moment the server restarted - and then refused the send with "the
    check has not been run on this version yet", which is a lie the reviewer cannot argue with.
    Reported as "it reset the Part 2 memory so it doesn't know where things are currently at",
    and that is exactly what it was: the approvals survived a restart because they were written
    to APPROVALS.json, while the fact that an eval had run did not.

    The run directory is the natural home - it is already the record of that run, it is already
    what APPROVALS.json is keyed against, and it outlives the process.
    """
    d = latest_eval_dir()
    if d is None:
        return None
    f = d / "FINGERPRINT"
    if not f.is_file():
        # Runs made before this was recorded. Fall back to the approvals file, which has carried
        # the fingerprint since it existed - better than declaring an eval never happened.
        ap = d / "APPROVALS.json"
        if ap.is_file():
            try:
                return (json.loads(ap.read_text()) or {}).get("fingerprint")
            except Exception:                                             # noqa: BLE001
                return None
        return None
    return (f.read_text().strip() or None)


def set_eval_ran(fingerprint):
    d = latest_eval_dir()
    if d is not None and fingerprint:
        (d / "FINGERPRINT").write_text(fingerprint + "\n")


def candidate_fingerprint():
    """A hash of the candidate knowledge content, so an approval can be tied to what it approved."""
    try:
        sys.path.insert(0, str(REPO / "scripts"))
        import eval_batch
        files = eval_batch.candidate_files()
    except Exception:                                                 # noqa: BLE001
        return None
    if not files:
        return None
    import hashlib
    h = hashlib.sha256()
    for f in sorted(files):
        h.update(f.encode())
        h.update((REPO / f).read_bytes())
    return h.hexdigest()


def latest_eval_dir():
    """Newest .eval/<stamp>/ that actually produced answers, or None.

    Sorted by NAME, not mtime: the stamp is the run time, while mtime moves when the restore
    phase rewrites files in an older directory. Name ordering is what "newest run" means.
    """
    root = REPO / ".eval"
    if not root.is_dir():
        return None
    runs = sorted((d for d in root.iterdir()
                   if d.is_dir() and (d / "RESULTS.json").is_file()),
                  key=lambda d: d.name, reverse=True)
    return runs[0] if runs else None


def eval_records():
    """[(rel, agent, n, question, before, after, approved)] for the newest eval run.

    `before` is the answer PRESERVED IN THE TRANSCRIPT - what the agent said when the
    conversation happened - and `after` is what it said during the eval. Showing them together
    is the entire point of the screen: an answer can look reasonable on its own and still be
    the same wrong answer that was reviewed, and nobody can tell without the pair side by side.
    """
    d = latest_eval_dir()
    if d is None:
        return []
    try:
        results = json.loads((d / "RESULTS.json").read_text())
    except Exception:                                                     # noqa: BLE001
        return []
    appr = eval_approvals()
    # FILTER THE DISPLAY BY THE CURRENT RULE, not by what the run happened to ask. A run made
    # before `pending` transcripts were excluded still has their answers in RESULTS.json, and
    # showing those cards keeps demanding approval for a review nobody made - which blocks the
    # send on work that was never requested. The stale card outlives the fix otherwise.
    try:
        sys.path.insert(0, str(REPO / "scripts"))
        import eval_batch as _eb
    except Exception:                                                     # noqa: BLE001
        _eb = None

    def _still_qualifies(rel):
        if _eb is None:
            return True
        f = REPO / rel
        if not f.is_file():
            return False
        fm, body = parse(f)
        fm = fm or {}
        if (fm.get("review_status") or "") not in ("reviewed", "suggested"):
            return False
        return _eb.wants_change(fm, body or "")

    out = []
    for r in results:
        rel = r.get("transcript") or ""
        if not _still_qualifies(rel):
            continue
        n = str(r.get("n") or "")
        # eval_batch writes `question`/`answer`; accept the short names too so an older run
        # directory still renders instead of showing two empty panes.
        q = r.get("question") or r.get("q") or ""
        after = r.get("answer") or r.get("ans") or ""
        # MATCH ON THE QUESTION TEXT, NOT THE INDEX. eval_batch numbers the questions it
        # replays from 1, while the transcript keeps the original exchange numbers - and canned
        # starting prompts are dropped on the way in, so the two disagree whenever one was
        # present. This batch is exactly that case: eval `n=1` is the file's `## Exchange 2`.
        # Indexing by n silently showed no "before" at all.
        before, xnum = "", n
        f = REPO / rel
        if f.is_file():
            _, body = parse(f)
            exs = exchanges_of(body or "")
            norm = lambda s: re.sub(r"\s+", " ", (s or "")).strip().lower()
            hit = next((e for e in exs if norm(e[2]) == norm(q)), None)
            if hit is None:                       # fall back to positional, then to the index
                hit = next((e for e in exs if e[0] == n), None)
            if hit is not None:
                xnum, before = hit[0], hit[3]
        out.append((rel, r.get("agent") or "team", n, q, before, after,
                    f"{rel}#{n}" in appr, xnum))
    return out


def eval_propagation():
    """[(collection, file, live, seconds)] for the newest run, or [] if not recorded.

    Absent for runs made before this was captured - treated as "unknown", not as "fine".
    """
    d = latest_eval_dir()
    if d is None or not (d / "PROPAGATION.json").is_file():
        return []
    try:
        return [(p.get("collection", ""), p.get("file", ""), bool(p.get("live")),
                 p.get("seconds")) for p in json.loads((d / "PROPAGATION.json").read_text())]
    except Exception:                                                     # noqa: BLE001
        return []


def eval_live():
    """The LIVE marker for the newest run, or None. {since, collections, files, minutes}.

    A run started with --keep leaves the candidate content SERVING REAL USERS until somebody
    takes it down. That is the point - one phrasing of one question does not establish that a
    change is sound, and adjacent phrasings cannot be tried against content that has already
    been torn down - but it is also a standing production exposure, so it has to be impossible
    to forget. Hence a marker on disk rather than in memory: it survives a server restart, and
    the UI can show how long it has been up.
    """
    d = latest_eval_dir()
    if d is None or not (d / "LIVE").is_file():
        return None
    try:
        m = json.loads((d / "LIVE").read_text())
    except Exception:                                                     # noqa: BLE001
        return None
    mins = None
    try:
        since = datetime.fromisoformat(m["since"])
        mins = int((datetime.now(since.tzinfo) - since).total_seconds() // 60)
    except Exception:                                                     # noqa: BLE001
        pass
    m["minutes"] = mins
    m["dir"] = str(d.relative_to(REPO))
    # WHICH FILES HAVE MOVED ON SINCE THE UPLOAD. This is the gap that made the iteration loop
    # quietly lie: the assistant edits a knowledge file, the reviewer presses Ask again, and the
    # agent answers from the content uploaded BEFORE those edits - which reads as the fix not
    # working. Nothing warned, because the marker recorded only file NAMES.
    import hashlib as _h
    stale = []
    for f, want in (m.get("hashes") or {}).items():
        fp = REPO / f
        if not fp.is_file():
            continue
        if _h.sha256(fp.read_bytes()).hexdigest() != want:
            stale.append(f)
    # A file added to the candidate set since the upload has never been uploaded at all.
    known = set((m.get("hashes") or {}).keys())
    try:
        sys.path.insert(0, str(REPO / "scripts"))
        import eval_batch as _eb
        for f in _eb.candidate_files():
            if f not in known:
                stale.append(f)
    except Exception:                                                     # noqa: BLE001
        pass
    m["stale"] = sorted(set(stale))
    return m


def eval_reupload():
    """Push the current candidate files over the live eval content. (ok, message).

    Only meaningful while something IS live: with nothing live this would upload unmerged
    content to production outside the eval's restore-point protection, which is precisely the
    thing the whole flow exists to avoid. So it refuses.
    """
    live = eval_live()
    if not live:
        return False, ("Nothing is live, so there is no eval content to replace. Run the check "
                       "from Publish first — re-uploading now would put unmerged content "
                       "into production with no restore point behind it.")
    d = latest_eval_dir()
    if not os.environ.get("FOUNDRY_API_KEY"):
        return False, ("FOUNDRY_API_KEY is not set in the environment this server was started "
                       "from, so nothing was uploaded.")
    res = subprocess.run([sys.executable, str(REPO / "scripts" / "eval_batch.py"),
                          "--reupload", str(d)],
                         cwd=REPO, capture_output=True, text=True, timeout=1800)
    out = ((res.stdout or "") + (res.stderr or "")).strip()
    tail = "\n".join(out.splitlines()[-24:])
    if res.returncode != 0:
        return False, ("The re-upload did not fully land — asking again now may answer from the "
                       "previous content:\n\n" + tail)
    return True, tail


def eval_remove():
    """Put Foundry back and clear the LIVE marker. (ok, message)."""
    d = latest_eval_dir()
    if d is None:
        return False, "There is no eval run to remove."
    if not (d / "LIVE").is_file():
        return True, "Nothing is live — Foundry is already back to what it was."
    if not os.environ.get("FOUNDRY_API_KEY"):
        return False, ("FOUNDRY_API_KEY is not set in the environment this server was started "
                       "from, so the removal did not run. The candidate content is STILL LIVE. "
                       f"Remove it from a shell that has the key:\n"
                       f"  python3 scripts/eval_batch.py --restore-only {d.relative_to(REPO)}")
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "eval_batch.py"),
                        "--restore-only", str(d)],
                       cwd=REPO, capture_output=True, text=True, timeout=1800)
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    tail = "\n".join(out.splitlines()[-20:])
    if r.returncode != 0:
        return False, ("The removal FAILED and the candidate content may still be live:\n\n"
                       + tail)
    # AND UNDO THE STEP, not just the upload. Clearing only the LIVE marker left the send gate
    # still satisfied - eval_ran_fingerprint() matched, so Part 2 kept showing Eval Review as
    # done-and-waiting and the opt-in checkbox stayed read-only. A reviewer who removed the
    # content saw nothing backtrack, which is the same complaint as the silent reset-to-pending:
    # the state changed and the page did not say so.
    #
    # The run directory is kept - its answers and approvals are the record of what happened. Only
    # the claim "an eval covers the current content" is withdrawn, because it no longer does.
    d = latest_eval_dir()
    if d is not None:
        (d / "FINGERPRINT").unlink(missing_ok=True)
        (d / "APPROVALS.json").unlink(missing_ok=True)
    return True, ("Foundry is back to what it was, and the Eval Review step is reset — run it "
                  "again when ready.\n\n" + tail)


def _var_path():
    d = latest_eval_dir()
    return None if d is None else d / "VARIANTS.json"


def eval_variants():
    """{key: [{question, answer, at}]} — the adjacent phrasings tried against the live content.

    Kept because they are the actual evidence that a change holds up. The scripted question is
    the one the transcript happened to record; the variants are what shows the fix is not tuned
    to a single wording, and they are the most useful thing to hand back to an assistant.
    """
    p = _var_path()
    if p is None or not p.is_file():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:                                                     # noqa: BLE001
        return {}


def eval_add_variant(key, question, answer, was_live=True):
    """Store one variant and RETURN THE RECORD, so the response can echo the exact stamp.

    Returning the whole dict was the mistake: the caller then had nothing specific to send back,
    the JS invented "just now", and two clicks produced two visually identical blocks - a
    reviewer could not tell whether the second Ask had done anything. The stamp has to come from
    the same write that stored it.
    """
    p = _var_path()
    rec = {"question": question, "answer": answer, "live": bool(was_live),
           "at": datetime.now().strftime("%H:%M:%S")}
    if p is None:
        return rec
    v = eval_variants()
    v.setdefault(key, []).append(rec)
    p.write_text(json.dumps(v, indent=2))
    return rec


def eval_improve_prompt(key, edited):
    """The prompt to hand an assistant after marking up an answer. (ok, text).

    Composed HERE rather than in the page for the same reason analysis_prompt is: the standing
    instructions - read the feedback as one body, do not change my verdicts, ask rather than
    guess, sync first - already exist in one place and must not acquire a second copy that
    drifts. This adds the exchange-specific context around them.

    The edited answer is the payload. Every `{{...}}` in it is a defect marked against the
    sentence it follows, which is what makes this more useful than the transcript alone: the
    transcript says what the answer should have been, while this says which parts of the answer
    the agent is STILL getting wrong after a round of knowledge edits.
    """
    rec = next((r for r in eval_records() if f"{r[0]}#{r[2]}" == key), None)
    if rec is None:
        return False, "That exchange is not in the current eval run."
    rel, agent, _n, q, _before, _after, _ok, xnum = rec
    corr = ""
    f = REPO / rel
    if f.is_file():
        _, b = parse(f)
        for xn, _t, _qq, _a, rv in exchanges_of(b or ""):
            if xn == xnum and rv:
                corr = correction_text(rv)
                break
    marks = re.findall(r"\{\{(.*?)\}\}", edited or "", re.S)
    files, _nq, _m = eval_estimate()
    # TARGET FIRST, THEN THE GAP. The assistant's job is to close the distance between what the
    # agent says and what the reviewer said it should say, so the target has to be stated before
    # the current answer - otherwise the current answer reads as the subject and the ideal response
    # as an aside. This is also an ITERATIVE loop: re-upload, ask again, mark up again. Saying so
    # stops the assistant treating one pass as final and rewriting more than the evidence
    # supports.
    L = [
        f"The `{agent}` agent is still not answering this the way I asked. This is one round of "
        "an iterative loop: you edit the knowledge files, I re-upload them to Foundry, ask the "
        "question again, and mark up whatever is still wrong. Your job this round is to close "
        "the gap between the two texts below.",
        "",
        "Sync this repo to the latest main first (`git fetch origin` and bring main up to date; "
        "do not disturb my in-progress branch). Read everything below as one body before "
        "changing anything. Do not change my verdicts, and ask me rather than guessing if "
        "anything here is ambiguous.",
        "",
        f"Transcript: {rel} (exchange {xnum})",
        "",
        "QUESTION ASKED",
        "--------------",
        (q or "").strip(),
        "",
    ]
    if corr:
        L += ["1. WHAT THE ANSWER SHOULD LOOK LIKE  (my ideal response — the target)",
              "----------------------------------------------------------------",
              corr, ""]
    L += ["2. WHAT IT ACTUALLY SAYS NOW" + (", with my ideal responses inline in {{...}}" if marks
                                            else ""),
          "----------------------------" + ("-" * (38 if marks else 0)),
          (edited or "").strip(), ""]
    L += ["WHAT TO DO",
          "----------"]
    if marks:
        L += [f"Each of the {len(marks)} `{{{{...}}}}` in (2) is a defect in the sentence it "
              "follows — start there."]
    else:
        L += ["I have not marked individual defects, so treat the whole of (2) as the problem."]
    L += ["Change the knowledge files so a fresh answer to that question reads like (1). Do not "
          "simply append an ideal response elsewhere in the file: retrieval returns the chunk that "
          "matches the question, and the wrong statement is IN that chunk — fix it where it is, "
          "and fix any nearby example that contradicts the rule you are adding.",
          "",
          "Match (1) on substance, not wording. I do not need the answer to quote me; I need it "
          "to stop saying the things (1) contradicts.",
          ""]
    if files:
        L += ["KNOWLEDGE FILES ALREADY CHANGED IN THIS BATCH",
              "---------------------------------------------"]
        L += [f"  {x}" for x in files]
        L += ["",
              "Those are the files whose current state produced (2), so start there — but "
              "identify more or fewer as the evidence requires.", ""]
    L += ["When you are done, tell me what you changed and why, per file. I will re-upload to "
          "Foundry and ask again, plus adjacent phrasings, to confirm it holds."]
    return True, "\n".join(L)


def eval_ask_live(slug, question):
    """Ask a live agent one question, right now. (ok, answer).

    Goes through eval_batch.ask so the two stream payload shapes stay handled in one place -
    the team endpoint returns {"delta":...} and the agent endpoint {"payload":{"text":...}},
    and a second implementation would eventually read only one and return an empty answer that
    looks like the agent refusing.
    """
    if not os.environ.get("FOUNDRY_API_KEY"):
        return False, "FOUNDRY_API_KEY is not set in the environment this server was started from."
    try:
        sys.path.insert(0, str(REPO / "scripts"))
        import eval_batch
        return True, (eval_batch.ask(slug, question) or "")
    except Exception as e:                                                # noqa: BLE001
        return False, f"the agent could not be reached: {e}"


def _appr_path():
    d = latest_eval_dir()
    return None if d is None else d / "APPROVALS.json"


def eval_approvals():
    """The set of approved "<rel>#<n>" keys for the newest run.

    Tied to the candidate fingerprint on disk. Edit a knowledge file after approving and the
    stored fingerprint stops matching, so every approval is dropped rather than carried over -
    an approval means "these answers, from this content", and the content just changed.
    """
    p = _appr_path()
    if p is None or not p.is_file():
        return set()
    try:
        d = json.loads(p.read_text())
    except Exception:                                                     # noqa: BLE001
        return set()
    if d.get("fingerprint") != candidate_fingerprint():
        return set()
    return set(d.get("approved") or [])


def set_eval_approval(keys, on):
    """Add/remove approval keys, stamped with the fingerprint they were given against."""
    p = _appr_path()
    if p is None:
        return set()
    cur = eval_approvals()
    cur = (cur | set(keys)) if on else (cur - set(keys))
    p.write_text(json.dumps({"fingerprint": candidate_fingerprint(),
                             "approved": sorted(cur)}, indent=2))
    return cur


def eval_all_approved():
    """(all_approved, n_approved, n_total) for the newest run."""
    recs = eval_records()
    if not recs:
        return False, 0, 0
    ok = sum(1 for r in recs if r[6])
    return ok == len(recs), ok, len(recs)


def eval_pending_count():
    """How many replayed exchanges still need a decision - the nav badge.

    Cheap enough to run on every page render: it reads one JSON file and one transcript per
    result, and a batch is single digits. Guarded anyway, because a nav item that can raise
    takes out every page in the app rather than just its own.
    """
    try:
        recs = eval_records()
    except Exception:                                                     # noqa: BLE001
        return 0
    return sum(1 for r in recs if not r[6])


def router_changes():
    """Router-affecting files in this batch, committed or not. [] if none."""
    rc, out = git("diff", "--name-only", "origin/main", "--", *ROUTER_PATHS)
    if rc != 0:
        return []
    return sorted({l.strip() for l in out.splitlines() if l.strip()})


def eval_estimate():
    """(files, n_questions, minutes) for the batch, so the checkbox can state a real cost.

    Reuses eval_batch.py's own detection rather than reimplementing it - two functions deciding
    "what is in this batch" would eventually disagree, and the one the UI showed would be the one
    nobody had tested.
    """
    try:
        sys.path.insert(0, str(REPO / "scripts"))
        import eval_batch
        files = eval_batch.candidate_files()
        n_q = 0
        for rel in eval_batch.batch_transcripts():
            # SAME PREDICATE AS THE RUN. This used to carry its own copy of the status list,
            # which then diverged: the script stopped replaying `pending` and transcripts with
            # nothing to change, while this kept counting them - so the screen quoted a question
            # count and a cost the run would not incur.
            _, qs, fm, body = eval_batch.parse_transcript(rel)
            if (qs and (fm.get("review_status") or "") in ("reviewed", "suggested")
                    and eval_batch.wants_change(fm, body)):
                n_q += len(qs)
        mins = max(1, (2 * eval_batch.SECS_PER_SYNC + n_q * eval_batch.SECS_PER_QUESTION) // 60)
        return files, n_q, mins
    except Exception:                                                 # noqa: BLE001
        return [], 0, 0


def _eval_optin(spent=False):
    """The eval checkbox, with the real cost stated rather than implied.

    ON by default: the whole point of an eval is that it runs when nobody remembered to ask for
    one. Off by default would mean it ran on the days somebody was already being careful.

    READ-ONLY ONCE THE EVAL HAS RUN FOR THIS CONTENT (`spent`). The checkbox only governs what
    the FIRST press of Process Part 2 does; after the eval has run, pressing it again goes on to
    the push and the change request, and the tickbox governs nothing. Leaving it live implied a
    choice that no longer existed - untick it at that point and nothing changes, which is worse
    than a disabled control because it looks like it did something.
    """
    files, n_q, mins = eval_estimate()
    if not files or not n_q:
        return ""
    if spent:
        return (
            "<div class=evalbox>"
            "<label class=evalrow><input type=checkbox id=doeval checked disabled>"
            "<span><b>Include Eval Review</b></span></label>"
            "<div class=hint style='margin:6px 0 0 26px'>Already run for this version &mdash; "
            "the next <b>Process</b> press goes on to the change request. Change a knowledge "
            "file and this becomes live again.</div></div>")
    # The cost and the live-agent side effect stay; the mechanics do not. A reviewer needs to
    # know how long it takes and that it touches production - not how Bedrock schedules jobs.
    return (
        "<div class=evalbox>"
        "<label class=evalrow><input type=checkbox id=doeval checked>"
        "<span><b>Include Eval Review</b></span></label>"
        f"<div class=hint style='margin:6px 0 0 26px'>"
        f"{n_q} question(s) against {len(files)} changed file(s). <b>~{mins} min.</b><br>"
        "Content stays live in Foundry until removed or sent. Best outside business hours. "
        "Required before a change request.</div></div>")


def _router_warning():
    """Light-red warning when the batch touches routing. The paths are admin-only, so in practice
    only an admin sees it - but it renders on what the batch contains, not on who is looking."""
    rc = router_changes()
    if not rc:
        return ""
    return ("<div class='bar bnr-router'>"
            "<b>This batch changes ROUTING.</b> "
            + ", ".join(f"<code>{html.escape(f)}</code>" for f in rc)
            + "<br>A content mistake gives one wrong answer. A routing mistake misroutes "
            "<i>every</i> conversation &mdash; and the transcript that reveals it looks like a "
            "content problem, so it gets misdiagnosed for days. Doubly worth doing outside "
            "working hours, and worth having somebody else read the diff first.</div>")


def eval_txt():
    """The whole eval run as plain text, for pasting back to an assistant. (filename, body).

    WHY PLAIN TEXT AND WHY THE WHOLE RUN.
    -------------------------------------
    When the answers are wrong, the next step is another round of knowledge edits - and the most
    useful thing to hand the assistant is exactly what the agents SAID, next to what they said
    before and next to the ideal response they were supposed to satisfy. Copying that out of the
    screen means selecting across several scrolling panes per card and losing the structure.

    So: every replayed exchange, in run order, each one demarcated, with the question, the
    before, the now, and the reviewer's own ideal response. The approval state is included because
    it is the reviewer's judgement on that specific answer and is the thing that tells the
    assistant which ones still need work.

    Deliberately NOT markdown. It gets pasted into a prompt, where stray `#` and backticks
    become formatting the model has to see past - and the answers themselves are already
    markdown, so wrapping markdown in markdown makes the boundary between them unreadable.
    """
    recs = eval_records()
    d = latest_eval_dir()
    files, n_q, _ = eval_estimate()
    prop = eval_propagation()
    allvars = eval_variants()
    bar = "=" * 78
    sep = "-" * 78
    L = [bar,
         "OneTyler Foundry - transcript eval results",
         f"Run                : {d.name if d else '(none)'}",
         f"Exported           : {datetime.now().strftime('%Y-%m-%d %H:%M')}",
         f"Exchanges replayed : {len(recs)}",
         f"Candidate files    : {len(files)}"]
    for f in files:
        L.append(f"                     {f}")
    if prop:
        stale = [p for p in prop if not p[2]]
        L.append("Content live during the run: "
                 + ("NO - " + ", ".join(f"{c}/{f}" for c, f, _l, _s in stale)
                    + "  <-- the answers below came from the OLD content and cannot be trusted"
                    if stale else "yes, all files verified live before the questions were asked"))
    else:
        L.append("Content live during the run: NOT RECORDED (this run predates that check)")
    L += [bar, ""]

    for i, (rel, agent, n, q, before, after, ok, xnum) in enumerate(recs, 1):
        corr = ""
        f = REPO / rel
        if f.is_file():
            _, b = parse(f)
            for xn, _t, _qq, _a, rv in exchanges_of(b or ""):
                if xn == xnum and rv:
                    corr = correction_text(rv)
                    break
        L += [sep,
              f"[{i}/{len(recs)}]  {rel}",
              f"          agent: {agent}    exchange: {xnum}",
              f"          approved by reviewer: {'YES' if ok else 'NO'}",
              sep, "",
              "QUESTION", "--------", q.strip() or "(none)", "",
              "ANSWER BEFORE  (as recorded in the transcript)",
              "---------------------------------------------",
              (before.strip() or "(not recorded)"), "",
              "ANSWER NOW  (with the candidate knowledge files live)",
              "----------------------------------------------------",
              (after.strip() or "(no answer returned)"), ""]
        if corr:
            L += ["REVIEWER'S IDEAL RESPONSE  (what the answer was supposed to become)",
                  "---------------------------------------------------------------",
                  corr.strip(), ""]
        # The adjacent phrasings, because they are what shows the fix is not tuned to one
        # wording - which is the single most useful thing to hand back to an assistant.
        for v in (allvars.get(f"{rel}#{n}") or []):
            L += [f"ALSO ASKED  ({v.get('at','')})",
                  "-----------",
                  (v.get("question") or "").strip(), "",
                  "  ->", (v.get("answer") or "(no answer)").strip(), ""]
        L.append("")

    L += [bar,
          "To act on this: read every exchange above as one body before changing anything.",
          "An exchange marked 'approved: NO' still gives a wrong answer - compare ANSWER NOW",
          "against the REVIEWER'S IDEAL RESPONSE to see what is still missing. Do not change any",
          "verdict in the transcripts, and ask rather than guessing where feedback is unclear.",
          bar, ""]
    stamp = d.name if d else "no-run"
    return f"eval-{stamp}.txt", "\n".join(L)


# NEGATIONS ARE DELIBERATELY NOT STOPWORDS. They are the highest-value words in this whole
# comparison: "a workspace is NOT 1:1 with a tenant" and "a workspace is 1:1 with a tenant" are
# opposite claims, and with "not" filtered out they scored 100% identical - the single worst way
# this hint could mislead. Keeping them counted turns that case into a visible miss.
def correction_text(rv):
    """The reviewer's actual words, without the block's own scaffolding.

    `exchanges_of` hands back the whole review block, which opens with
    `**Review -** _verdict:_ - _should have said:_`. That is template text the form wrote, not
    something the reviewer said, and leaving it in does two kinds of damage: it is the first
    thing shown in the pane that is supposed to be the target answer, and its words land in the
    match denominator, so the score moves depending on how much scaffolding happened to be
    present.
    """
    if not rv:
        return ""
    out = re.sub(r"^\s*\*\*Review\s*[—-]\*\*.*?(?:\n|$)", "", rv, count=1)
    return out.strip()


_MATCH_STOP = set("""a an and are as at be been but by can do does for from had has have
how i if in into is it its may must of on or should so than that the their them then there
these they this to under use used using was were what when where which who will with within
you your""".split())


def match_pct(correction, answer):
    """How much of the reviewer's ideal response the answer actually covers, 0-100, or None.

    RECALL, not similarity, and the choice matters. `difflib`-style similarity punishes an answer
    for being shorter or longer than the ideal response, which says nothing about whether it picked
    up the content - and a reviewer's ideal response is often a full replacement answer while the
    agent's reply is a summary of it. Recall asks the question actually being asked: of the
    substantive words I told it to say, how many did it say?

    It is a WORD-OVERLAP MEASURE AND NOTHING MORE. It cannot tell paraphrase from contradiction:
    "a workspace is not 1:1 with a tenant" and "a workspace is 1:1 with a tenant" score nearly
    identically. So it is labelled as a hint and the checkbox is still the reviewer's, which is
    why this returns a number rather than gating anything on it.
    """
    def toks(t):
        t = re.sub(r"`[^`]*`", " ", t or "")            # code spans are formatting, not content
        t = re.sub(r"[^A-Za-z0-9]+", " ", t).lower()
        return {w for w in t.split() if len(w) > 2 and w not in _MATCH_STOP}
    c, a = toks(correction), toks(answer)
    if not c:
        return None
    return int(round(100 * len(c & a) / len(c)))


def match_html(pct):
    """The match hint, with a tone. "" when there is no ideal response to compare against."""
    if pct is None:
        return ""
    tone = "ok" if pct >= 70 else ("warn" if pct >= 40 else "bad")
    return (f"<span class='evmatch {tone}' title='Share of the substantive words in the "
            "ideal response that appear in this answer. A word-overlap hint only — it cannot tell a "
            f"paraphrase from a contradiction, so read the answer.'>Match {pct}% against the "
            "ideal response</span>")


def run_clock(d):
    """HH:MM:SS from a run directory name like 2026-08-28T20-18-21."""
    try:
        return d.name.split("T", 1)[1].replace("-", ":")
    except Exception:                                                     # noqa: BLE001
        return ""


def variants_html(earlier):
    """The answers SUPERSEDED by the one now shown under "Now", oldest first.

    "Now" always holds the most recent answer, stamped, because a reviewer clicking Ask again
    needs to see at a glance that something changed - two unstamped blocks looked identical and
    there was no way to tell the second Ask had run. Everything before it falls back here rather
    than being discarded: what is being judged is CONSISTENCY across phrasings, so three answers
    that all come back right is the evidence and one is a coincidence.
    """
    if not earlier:
        return ""
    rows = "".join(
        f"<div class=evvar><div class=evlab>{html.escape(v.get('at') or '')}"
        + (" &middot; from the run" if v.get("scripted")
           else (" &middot; asked" if v.get("live", True)
                 else " &middot; asked against PUBLISHED content"))
        + f"</div><div class=evvq>{html.escape(v.get('question') or '')}</div>"
        f"<pre>{html.escape(v.get('answer') or '(no answer)')}</pre></div>"
        for v in earlier)
    n = len(earlier)
    if n <= 2:
        return f"<div class=evlab style='margin-top:12px'>Earlier ({n})</div>" + rows
    return f"<details class=evcorr><summary>Earlier ({n})</summary>{rows}</details>"


def eval_review_page():
    """A screen of its own for judging what the agents said after the change.

    WHY THIS IS NOT PART OF THE OUTPUT PANE.
    ----------------------------------------
    It used to be: the eval printed its answers into the same panel that shows git output, with
    a pair of buttons underneath. A reviewer said plainly they could not find anything to
    approve, and they were right - the one screen in this app where somebody has to read
    carefully and make a per-transcript judgement was rendered as terminal output, in a panel
    whose stated job is "for passing to an assistant if a step failed". Approval per transcript
    was not expressible at all: the two buttons acted on the whole batch.

    So each replayed exchange gets a card with the question, the answer BEFORE, the answer NOW,
    the reviewer's own ideal response to check it against, and one checkbox. The send stays shut
    until every card is ticked.
    """
    recs = eval_records()
    d = latest_eval_dir()
    files, n_q, _mins = eval_estimate()

    if not recs:
        # Two genuinely different empty states. "No eval has run" is a normal starting point;
        # "an eval ran but the content has moved on" is a stale result that must not be
        # mistaken for one, because its answers describe content that no longer exists.
        if d is None:
            body = ("<div class='bar bnr-note'><b>No check has run yet.</b> Run it from "
                    "<a href='/publish'><b>Publish</b></a>. Answers land "
                    "here to approve.</div>")
        else:
            body = ("<div class='bar bnr-router'><b>The last check is out of date</b> &mdash; a knowledge "
                    "file changed since it ran. Run it again from "
                    "<a href='/publish'><b>Publish</b></a>.</div>")
        return page("Eval Review", "<h2 class=sec>Eval Review</h2>" + body, active="evalrev")

    all_ok, n_ok, n_tot = eval_all_approved()
    when = d.name.replace("T", " ").replace("-", ":", 0) if d else ""

    # DID THE CANDIDATE CONTENT ACTUALLY GO LIVE BEFORE THE QUESTIONS WERE ASKED?
    # If it did not, every answer below came from the OLD content and approving them would ship
    # an untested change while the screen said it was checked. This warning exists because that
    # happened: a run's answers repeated the exact claim the change removed, and the only
    # evidence was one line in a scrollback nobody had reason to re-read.
    prop = eval_propagation()
    stale = [p for p in prop if not p[2]]
    warn = ""
    if stale:
        warn = ("<div class='bar bnr-router'><b>These answers cannot be trusted.</b> "
                + f"{len(stale)} of {len(prop)} file(s) never went live in Foundry before the "
                "questions were asked, so the agents answered from the <b>old</b> content:"
                + "".join(f"<br>&nbsp;&nbsp;<code>{html.escape(c)}/{html.escape(f)}</code>"
                          for c, f, _l, _s in stale)
                + "<br><br>Do not approve &mdash; run the check again.</div>")
    # NO banner for "propagation not recorded". It only ever applied to runs predating that
    # check, said nothing actionable, and cost a full-width bar on every load. The RED banner
    # above stays: a run whose content demonstrably never went live must not be approved.

    live = eval_live()
    if live:
        mins = live.get("minutes")
        age = f" for {mins} min" if isinstance(mins, int) else ""
        livebar = (
            "<div class='bar bnr-router' id=evlive>"
            f"<b>Candidate content is LIVE in Foundry{age}.</b> "
            f"{len(live.get('files') or [])} file(s) in "
            + ", ".join(f"<code>{html.escape(c)}</code>"
                        for c in (live.get("collections") or []))
            + " &mdash; every user of these agents is answering from it.<br>"
            "Left up on purpose so adjacent phrasings can be tried below. It comes down on "
            "<b>Remove evals</b>, or by itself when the batch is sent in &mdash; and goes "
            "back up permanently on merge."
            + (f"<br><br><b>{len(live['stale'])} knowledge file(s) have changed since that "
               "upload</b>, so what is live is behind the repo. Press <b>Foundry re-upload</b> "
               "before asking again, or the answers will come from the previous round:"
               + "".join(f"<br>&nbsp;&nbsp;<code>{html.escape(f)}</code>"
                         for f in live["stale"])
               if live.get("stale") else "")
            + "<div class=stepacts style='margin-top:10px'>"
            + "<button class=sec onclick='evRemove(this)'>Remove evals</button></div></div>")
    else:
        # NO BANNER WHEN NOTHING IS LIVE. It was a full-width bar restating what the card below
        # already implies, shown on every load for the normal resting state. The Remove evals
        # button it used to hold now lives in the card's action row, where it is findable in
        # both states instead of appearing and vanishing - which is what made it unfindable.
        livebar = ""

    head = (
        f"<h2 class=sec>Eval Review</h2>"
        + warn
        + livebar
        # ONE CARD, not a bar plus a card. The approval count sat in its own full-width bar
        # directly above a card that explained the same screen, so the two were read together
        # anyway while taking twice the vertical space and pushing the actual exchanges below
        # the fold. Heading dropped too: "What you are deciding" named the page, which the h2
        # already does.
        + "<div class=card>"
        + "<p class=sub style='margin:0' id=evstate>"
        + (f"<b>All {n_tot} approved.</b> Ready to send in."
           if all_ok else
           f"<b>{n_ok} of {n_tot} approved.</b> All must be approved before sending.")
        + "</p>"
        + f"<p class=sub style='margin:4px 0 0'><code>{html.escape(when)}</code> &middot; "
        f"{len(files)} file(s) &middot; {n_q} question(s) &middot; <b>Match %</b> is word "
        "overlap, indicative only.</p>"
        + "<div class=stepacts style='margin-top:10px'>"
        + "<button class=sec onclick=\"evAll(1)\">Approve all</button>"
        + "<button class=sec onclick=\"evAll(0)\">Clear all</button>"
        # A plain link, not a fetch-and-blob: the browser's own download handling gets the
        # filename and the save dialog right. The title carries what a whole caption line used
        # to say underneath.
        + "<a class='btn sec' href='/evalreview.txt' download "
          "title='Every exchange, demarcated — for passing back to an assistant'>"
          "Download as .txt</a>"
        # Lives here rather than in a banner that only existed while something was live, which
        # is why it could not be found.
        + ("<button class=sec onclick='evRemove(this)' title='Put the published content back'>"
           "Remove evals</button>"
           if live else
           "<button class=sec disabled title='Nothing is live to remove'>Remove evals</button>")
        + "</div></div>")

    allvars = eval_variants()
    cards = []
    for rel, agent, n, q, before, after, ok, xnum in recs:
        key = f"{rel}#{n}"
        # The scripted answer is just the first entry in a sequence; every Ask again appends.
        # "Now" is whatever is last, so it is always the answer the reviewer most recently
        # provoked - which is the thing they are looking at the screen to confirm.
        seq = [{"at": run_clock(d), "question": q, "answer": after, "scripted": True}]
        seq += (allvars.get(key) or [])
        latest, earlier = seq[-1], seq[:-1]
        loc = f"/t/{rel.split('/', 1)[1].rsplit('/', 1)[0]}/{Path(rel).name}" \
            if rel.startswith("transcripts/") and rel.count("/") >= 2 else "/"
        # The reviewer's own ideal response, quoted back. They wrote it hours or days ago and it is
        # the only statement of what "right" means for this exchange.
        corr = ""
        f = REPO / rel
        if f.is_file():
            _, b = parse(f)
            for xn, _t, _qq, _a, rv in exchanges_of(b or ""):
                if xn == xnum and rv:
                    corr = correction_text(rv)
                    break
        cards.append(
            "<div class='card evcard" + (" evok" if ok else "") + f"' id=\"c-{html.escape(key)}\">"
            "<label class=evhead>"
            f"<input type=checkbox {'checked' if ok else ''} "
            f"onchange=\"evSet(this,'{html.escape(key)}')\">"
            "<span><b>This answer is right</b></span></label>"
            f"<div class=sub style='margin:2px 0 10px'>"
            f"<a href=\"{html.escape(loc)}\">{html.escape(Path(rel).name)}</a> &middot; "
            f"agent <code>{html.escape(agent)}</code> &middot; "
            f"exchange {html.escape(str(xnum))}</div>"
            # EDITABLE, because tailoring content to one phrasing is the failure mode this
            # whole step exists to catch. The original is kept in data-orig so Reset can put it
            # back - a reviewer who has typed three variants should not have to remember what
            # the transcript actually asked.
            "<div class=evask>"
            "<div class=evlab>Question &mdash; edit it and ask again</div>"
            f"<textarea class=evqbox data-orig=\"{html.escape(q)}\" rows=2 "
            f"oninput='evQEdited(this)'>{html.escape(q)}</textarea>"
            "<div class=stepacts style='margin:6px 0 0'>"
            # ALWAYS ENABLED. It used to be disabled whenever nothing was live, on the grounds
            # that the answer would come from PUBLISHED content and so say nothing about the
            # change being reviewed. That reasoning is right but the remedy was wrong: a
            # reviewer may legitimately want to see what the agent says today, and a dead button
            # cannot explain itself. Both hazards - answering from published content, and
            # replacing unsaved {{...}} markup - are now warnings on the click.
            + f"<button data-live='{'1' if live else '0'}' "
            f"data-stale='{len((live or {}).get('stale') or [])}' "
            f"onclick=\"evAsk(this,'{html.escape(key)}','{html.escape(agent)}')\">"
            "Ask again</button>"
            + "<button class='sec evresetq' disabled title='The question is unchanged' "
            "onclick='evResetQ(this)'>Reset question</button>"
            # Sits with the other two because this is where the loop happens - mark up, copy the
            # prompt, the assistant edits, re-upload, ask again - but it is BATCH-scoped, not
            # per-card: it pushes every changed knowledge file. The label says "Foundry" so it
            # does not read as a per-question action.
            + ("<button class=sec onclick='evReupload(this)' title='Push the current knowledge "
               "files over the live eval content, so Ask again tests the latest edits. Affects "
               "the whole batch.'>Foundry re-upload</button>"
               if live else
               "<button class=sec disabled title='Nothing is live to replace'>"
               "Foundry re-upload</button>")
            + "</div></div>"
            # IDEAL RESPONSE vs NOW, side by side - not Before vs Now. Before is known-bad; that is
            # why the transcript was reviewed. The judgement being made is whether the answer has
            # become what the reviewer asked for, and putting the target beside the response is
            # the only layout that lets that be read in one glance. Before drops to a disclosure
            # for the occasions when someone wants to see what changed.
            "<div class=evcols>"
            + (f"<div class=evtarget><div class=evlab>Ideal response</div>"
               f"<pre>{html.escape(corr)}</pre></div>"
               if corr else
               "<div class=evtarget><div class=evlab>Ideal response</div>"
               "<pre>(none written for this exchange)</pre></div>")
            # NOW IS EDITABLE, and editing it is how a reviewer marks what is still wrong:
            # `{{...}}` inline against the sentence it is about. The marker carries its own
            # location, which a separate notes box cannot - and a fix aimed at the wrong
            # sentence is the failure that box would produce.
            #
            # The stored answer is NOT touched. This is a scratch copy; the agent's actual words
            # stay in the run and in Earlier, so the record of what it said survives the markup.
            + "<div class=evafter>"
            f"<div class=evlab>Now{(' (' + html.escape(latest['at']) + ')') if latest.get('at') else ''}"
            f"{match_html(match_pct(corr, latest.get('answer') or ''))}"
            "<span class=evedited hidden> · edited</span></div>"
            f"<textarea class=evnowbox oninput='evNowEdited(this)' "
            f"data-orig=\"{html.escape(latest.get('answer') or '')}\">"
            f"{html.escape(latest.get('answer') or '(no answer returned)')}</textarea>"
            "<div class=hint style='margin:5px 0 0'>Mark defects inline as "
            "<code>{{ }}</code>, then <b>Copy prompt</b> for an AI-enabled terminal.</div>"
            # DIRECTLY UNDER THE INSTRUCTION THAT NAMES THEM, inside the Now column. They began
            # ABOVE the box, which pushed this column down and left the two compared panes
            # starting at different heights; moving them to the card's bottom fixed that but
            # divorced them from the sentence telling you to press them. Here the boxes still
            # align - they have a fixed shared height - and the buttons sit with their own
            # instruction.
            "<div class=stepacts style='margin:8px 0 0'>"
            f"<button class=evcopy disabled title='Edit the answer above first — add "
            f"{{{{...}}}} where it is wrong' "
            f"onclick=\"evCopyPrompt(this,'{html.escape(key)}')\">Copy prompt</button>"
            "<button class='sec evresetnow' disabled title='Nothing to reset yet' "
            "onclick='evResetNow(this)'>Reset</button>"
            "<span class=evmarks></span></div></div>"
            "</div>"
            + (f"<details class=evcorr><summary>The original (bad) answer &mdash; reference only</summary>"
               f"<pre>{html.escape(before)}</pre></details>" if before else "")
            # Variants accumulate rather than replacing the scripted answer: the consistency
            # across phrasings IS the evidence, so losing the earlier ones would lose the point.
            + f"<div class=evvars>{variants_html(earlier)}</div>"
            + "</div>")

    foot = (
        "<div class=card><h3>When finished</h3>"
        + ("<p class=sub>Sending in opens the change request(s); merging publishes to Foundry.</p>"
           if all_ok else
           "<p class=sub>If an answer is wrong, return the batch to pending. Ideal responses are kept.</p>")
        + "<div class=stepacts>"
        + (f"<button id=evsend onclick=\"evSend(this)\">Send the batch in</button>"
           if all_ok else
           "<button id=evsend disabled title='Approve every transcript first' "
           "onclick=\"evSend(this)\">Send the batch in</button>")
        + "<button class=sec onclick=\"evReset(this)\">Put the batch back to pending</button>"
        "</div></div>"
        "<div class=card><h3 id=outhead>Processing output</h3>"
        "<pre class=out id=gitout style='display:none'></pre></div>")

    return page("Eval Review", head + "".join(cards) + foot, active="evalrev")


def part2_state():
    """Which Part 2 stages are already done, derived from reality. {stage: cls}.

    THE PROGRESS LIST USED TO BE CLIENT-SIDE ONLY. Every stage rendered as `wait` on load and
    only turned green if you happened to be on the page when the step ran - so a reviewer who
    reloaded, or came back the next morning, saw four untouched steps and no way to tell what had
    already happened. Worse, the assistant step stayed grey after the knowledge files had been
    written, which reads as "this still needs doing".

    Derived per stage, cheaply:
      ai    knowledge work outstanding? awaiting_analysis() is the same count the stage prints.
      eval  has an eval run against THIS content, and is every transcript approved?
      push  is the current lane on the remote, with nothing unsent?
      pr    is there an open change request for it?
    """
    out = {}
    # THREE OUTCOMES, NOT TWO. "Nothing waiting" is ambiguous: it means either the assistant has
    # finished, or no review in this batch ever asked for a change. Rendering both as `none`
    # struck through "nothing to update" told a reviewer who HAD run the assistant that their
    # work did not count. So: `done` when something in this batch is marked applied, `none` only
    # when there was genuinely nothing to do.
    applied = 0
    _, listed = git("diff", "--name-only", "origin/main", "--", "transcripts")
    for rel in (l.strip() for l in listed.splitlines()):
        if not rel.endswith(".md") or Path(rel).name in ("README.md", "INDEX.md",
                                                         "ONBOARDING.md"):
            continue
        f = REPO / rel
        if not f.is_file():
            continue
        fm, _b = parse(f)
        if (fm or {}).get("action_status", "").strip() == "applied":
            applied += 1
    if awaiting_analysis():
        out["ai"] = "wait ai"
    elif applied:
        out["ai"] = "done"
    else:
        out["ai"] = "none"

    fp = candidate_fingerprint()
    ran = eval_ran_fingerprint()
    all_ok, _n_ok, n_tot = eval_all_approved()
    if not fp:
        out["eval"] = "none"                      # nothing to evaluate
    elif ran != fp:
        out["eval"] = "wait"                      # never run, or the content moved on
    elif n_tot and all_ok:
        out["eval"] = "done"
    else:
        out["eval"] = "you"                       # ran; waiting on the reviewer to read it

    branch, _ = current_lane()
    pushed = False
    if branch:
        rc, _o = git("rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{branch}")
        pushed = rc == 0 and not unsent_saves()
    out["push"] = "done" if pushed else "wait"

    out["pr"] = "wait"
    if branch:
        r = subprocess.run(["gh", "pr", "list", "--head", branch, "--state", "open",
                            "--json", "number", "-q", ".[].number"],
                           cwd=REPO, capture_output=True, text=True, timeout=60)
        if (r.stdout or "").strip():
            out["pr"] = "done"
    return out

def git_page(which="save"):
    """Save (local checkpoint) and Publish (share it), as two tabs.

    One function because both pages are built from the same derived state - the pending file
    list, the saves history, part2_state() - and computing that twice would let the two tabs
    disagree about what is pending. `which` only picks which body is returned.


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
    # DERIVED ON LOAD, so a reload or a fresh morning shows what has actually
    # happened rather than four untouched steps. The classes used to be set only by
    # the JS that ran the step, so progress existed solely for whoever was watching.
    # Must come BEFORE ai_stage is built - it is read there.
    st = part2_state()
    # THE BUTTON NAMES WHAT IT WILL DO. "Process Part 2" was accurate and uninformative: Part 2 is
    # four stages and this button performs a different subset depending on where you are. Derived
    # from the same state the progress list renders, so the two can never disagree.
    # SAME PREDICATE AS THE CHECKBOX, deliberately. `spent` means an eval already covers this
    # content, which is exactly when the checkbox goes read-only and the press stops running an
    # eval and goes on to the push. Deriving the label from anything else let the two disagree:
    # with eval="you" - run, not yet approved - the button said "Eval Review" while the press
    # actually attempted the change request.
    spent = st["eval"] in ("you", "done")
    if not spent and eval_estimate()[1]:
        next_step = "Eval Review"
    elif st["push"] != "done":
        next_step = "Upload to GitHub"
    elif st["pr"] != "done":
        next_step = "Create the change request"
    else:
        next_step = "Re-send"        # everything already out; the press just re-pushes
    btn_label = f"Process: {next_step}"
    if n_ai:
        # A stage with its own state, `ai`, because it is neither waiting on this button nor
        # something the page can do. The prompt is a copy button rather than text to retype:
        # the words matter (read all the feedback as one body, ask rather than guess) and
        # nobody should have to remember them.
        ai_stage = (
            f"<li data-stage=ai class='{st['ai']}'><b>Update the knowledge files</b>"
            f"<span><b>{n_ai}</b> transcript(s) waiting. Needs an assistant.<br>"
            "<button type=button class=sec id=aiprompt onclick='copyPrompt(this)' "
            "style='margin-top:8px'>Copy the prompt for my assistant</button>"
            "</span></li>")
    else:
        ai_stage = (
            f"<li data-stage=ai class='{st['ai']}'><b>Update the knowledge files</b>"
            + ("<span>done</span></li>" if st["ai"] == "done"
               else "<span>nothing to update</span></li>"))

    # The eval used to be invisible until it ran: the checkbox described it, but the numbered
    # progress list jumped straight from "Update the knowledge files" to "Upload to GitHub", so
    # the one step that needs the reviewer to STOP AND READ was the only step not shown as a
    # step. A reviewer asked for it by name for exactly that reason - they could not tell it was
    # what came next. It is a gate, so it earns a place in the list more than the two stages
    # after it, which are automatic.
    ev_files, ev_q, _ev_mins = eval_estimate()   # the cost is stated on the checkbox above
    if ev_files and ev_q:
        eval_stage = (
            f"<li data-stage=eval class='{st['eval']}'><b>Eval Review</b>"
            # The cost line lived here AND on the "Include Eval Review" checkbox directly above.
            # One statement of it is enough; this stage only needs to say what to do next.
            "<span>Read/test the updated responses on the <b>Eval Review</b> tab, select "
            "agreeable outputs and return to this part to publish changes.</span></li>")
    else:
        eval_stage = (
            "<li data-stage=eval class=none><b>Eval Review</b>"
            "<span>nothing to check</span></li>")

    prompt_json = json.dumps(analysis_prompt(n_ai))

    def step(desc, inner):
        """One block of controls, with an optional one-line description.

        NO NUMBER, NO TITLE. Backing up and publishing are INDEPENDENT - either one, in any
        order, as often as you like - so "1" and "2" asserted a sequence that does not exist.
        Each also has a card of its own now, whose heading already names it, so a title inside
        the step said the same thing twice and the badge numbered nothing.
        """
        sub = f"<p class=sub>{desc}</p>" if desc else ""
        return f"<div class=step><div class=stepbody>{sub}{inner}</div></div>"

    # SPLIT INTO TWO PAGES. One tab held two unrelated jobs: a local checkpoint that shares
    # nothing, and a publish sequence that shares everything. Different audiences, different
    # risk, and no ordering between them - so a reviewer looking for one had to read past the
    # other to find it.
    #
    # The state bar and the Processing output panel appear on BOTH, because they are status
    # rather than functionality: the bar answers "what is pending" and the panel is where every
    # button on either page prints. Omitting either would leave a page unable to report on
    # itself. The JS that patches them after an action tests for each element, so a page that
    # does not have one is fine.
    state_bar = f"<div class=bar id=gitstate>{state}</div>"
    out_panel = (
      # ONE HEADING FOR BOTH STATES, and not "Your changes". This panel shows the pending diff
      # on load and a step's console output after one runs, and it used to rename itself between
      # the two. "Your changes" was actively misleading: on a page about reviewing transcripts
      # that reads as the reviewer's own suggestions, which live in the transcript, not here.
      "<div class=card>"
      "<h3 id=outhead>Processing output</h3>"
      "<p class=sub id=outsub>Pending edits are reflected in color: Green indicates addition, "
      "Red indicates removal.</p>"
      "<pre class=out id=gitout>" + diff_html(review_diff()) + "</pre></div>")

    save_body = (
      "<h2 class=sec>Save</h2>"
      # NO BRANCH NAME HERE, deliberately. This line used to read "You are working on
      # feature/owner-highlighting", which is git vocabulary a reviewer has no use for and
      # cannot act on. The branch is handled entirely server-side now - see ensure_lane().
      + state_bar
      + "<div class=card>"
        "<h3>Back up review progress</h3>"
        "<p class=sub>Local checkpoint. Not shared.</p>"
      + step("",
             # Empty by DEFAULT, not prefilled. A prefilled box asks to be read, edited and
             # worried about; an empty one labelled "optional" asks for nothing. Blank is
             # handled server-side by auto_commit_message().
             "<label>Optional label for these changes<span class=hint> &mdash; leave blank and "
             "the reviewer name and the time are used</span></label>"
             "<input id=cmsg value='' placeholder='e.g. identity transcripts, first pass'>"
             "<div class=stepacts>"
             "<button class=sec onclick=\"gitDo('commit')\">Save progress</button>"
             "<button class=sec onclick=\"gitDo('diff')\">View pending changes</button>"
             "</div>" + "<div id=githist>" + saves_html + "</div>")
      + "</div>"
      + out_panel
      # Recovery belongs with Save: it undoes unsaved edits, which is the same subject as
      # checkpointing them. Last on the page - it is an EXCEPTION to the workflow, not a stage
      # of it, and leading with a way to throw work away is the wrong first thing to see.
      + "<div class='card dangerzone'>"
        "<h3>Recovery</h3>"
        "<p class=sub>Not part of the normal flow &mdash; only for undoing.</p>"
        "<div class=dzrow><div>"
        "<b>Reset unsaved edits</b>"
        "<div class=sub>Reverts unsaved transcript edits. Saved work and newly synced "
        "conversations are untouched. Recoverable &mdash; edits are set aside, not deleted.</div>"
        "</div><div class=dzact>"
        "<button class=sec onclick='resetUnsaved(this)'>Reset unsaved edits</button>"
        "</div></div></div>")

    publish_body = (
      "<h2 class=sec>Publish</h2>"
      + state_bar
      # The honest division of labour, stated where it is acted on: a verdict is not the
      # deliverable. The knowledge file that stops the agent repeating that answer is, and
      # writing it is the ONE job here that needs an assistant.
      + "<div class=card>"
      + "<h3>Publish reviewed transcripts</h3>"
      + "<p class=sub>Requires an AI-enabled terminal with access to the affected files.</p>"
      + step("",
             "<ol class=prog id=prog>"
             + ai_stage
             + eval_stage +
             f"<li data-stage=push class='{st['push']}'><b>Upload to GitHub</b>"
             "<span>pushes the review branch</span></li>"
             f"<li data-stage=pr class='{st['pr']}'><b>Create the change request</b>"
             "<span>a pull request, for review</span></li>"
             + "</ol>"
             # `spent` when an eval already covers this exact content - the tickbox then
             # governs nothing, so it must not look like it does.
             + _eval_optin(spent=st["eval"] in ("you", "done"))
             + _router_warning()
             + "<div class=stepacts>"
             f"<button onclick='sendReviews(this)' data-ai-pending='{n_ai}' "
             f"data-label=\"{html.escape(btn_label)}\">{html.escape(btn_label)}</button></div>"
             # Publishing ENDS here. Merging and the Foundry upload are decisions ABOUT a
             # request that already exists, not steps in submitting one, and they live on the
             # PRs tab where the request can be seen next to its checks.
             + ("<div class=handoff>Merging and the Foundry upload are on "
                "<a href='/prs'><b>PRs</b></a>."
                if is_admin() else
                "<div class=handoff>An admin merges it from there. Nothing further is needed.")
             + "</div>")
      + "</div>"
      f"<script>window.AI_PROMPT={prompt_json};</script>"
      + out_panel
      + "<details class=card><summary>"
        "<span class=info aria-hidden=true>i</span>"
        "<h3>Reference</h3>"
        "<span class=chev aria-hidden=true></span></summary>"
        "<ul class=sub style='margin:10px 0 0 20px;padding:0'>"
        "<li>Reviews with no changes should still be submitted.</li>"
        "<li>Writing what <i>should</i> have been said is the valuable part &mdash; a "
        "knowledge-file change is not required.</li>"
        "<li>Suggestions handed to someone else need sending in too; that is how they reach "
        "them.</li>"
        "<li>Saving shares nothing. Only this page does.</li>"
        "</ul></details>")

    if which == "publish":
        return page("Publish", "<div class=lg>" + publish_body + "</div>", active="publish")
    return page("Save", "<div class=lg>" + save_body + "</div>", active="save")


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
        if self.path.startswith("/prs?diff="):
            qs = self.path.split("?", 1)[1]
            num = ""
            for kv in qs.split("&"):
                if kv.startswith("diff="):
                    num = unquote(kv[len("diff="):]).strip()
            if not num.isdigit():
                return self._send(200, page("Change Requests",
                    "<div class=lg><h2 class=sec>Change Requests</h2>"
                    "<div class='bar bnr-done'>Not a change-request number.</div>"
                    "<p><a href='/prs'>Back</a></p></div>", active="prs"))
            rep = "bp" if "repo=bp" in self.path else ""
            return self._send(200, pr_diff_page(num, force="refresh=1" in self.path, repo=rep,
                                                full="full=1" in self.path))
        if self.path == "/prs" or self.path.startswith("/prs?"):
            # Same gate as All Transcripts, and for the same reason: a contributor cannot
            # merge, so every button here would refuse. Not a security boundary - the page
            # only shows what `gh` would tell them anyway.
            if not is_admin():
                return self._send(200, page("Change Requests",
                    "<div class=card><h3>Admins only</h3><p class=sub>Merging is an admin "
                    "action. Send the reviews in from <b>Publish</b> and an admin "
                    "will merge them.</p></div>", active="git"))
            return self._send(200, pr_page(force="refresh=1" in self.path))
        if self.path in ("/git", "/save"):
            # /git kept as an alias: it is linked from other pages and may be bookmarked.
            return self._send(200, git_page("save"))
        if self.path == "/publish":
            return self._send(200, git_page("publish"))
        if self.path == "/evalreview.txt":
            name, body = eval_txt()
            b = body.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            # Named after the run, so several rounds of this do not overwrite each other in the
            # downloads folder - which is exactly the case it gets used in.
            self.send_header("Content-Disposition", f'attachment; filename="{name}"')
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            return self.wfile.write(b)
        if self.path == "/evalreview" or self.path.startswith("/evalreview?"):
            return self._send(200, eval_review_page())
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
                if st == "suggested" and not ((fields.get("suggested_to") or "").strip()
                                             or (fields.get("reassign_to") or "").strip()):
                    raise ValueError("a suggestion needs a destination — set 'Suggested to' "
                                     "(a person) or 'Reassign to' (an agent), otherwise it "
                                     "sits in the current queue and nobody is asked to decide")
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
                # The reviewer may have written an ideal response and left the pre-filled
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
                # Closes the gap merge-publishes cannot: a merge made on github.com never runs
                # our publish, so the agents stay stale. See autopublish_drift().
                pub_msg = autopublish_drift()

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
                                                             + ((pub_msg + "\n\n")
                                                                if pub_msg else "")
                                                             + out[-4000:],
                                                   "age": last_sync_age()}),
                                  "application/json")
            except Exception as e:
                return self._send(200, json.dumps({"ok": False, "error": str(e)}),
                                  "application/json")
        if self.path == "/csvexport":
            try:
                rels = data.get("paths") or []
                if not rels:
                    raise ValueError("nothing selected")
                body, n, skipped = csv_export(rels)
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                return self._send(200, json.dumps(
                    {"ok": True, "csv": body, "rows": n, "skipped": skipped,
                     "name": f"ideal-responses-{stamp}.csv"}), "application/json")
            except Exception as e:                                    # noqa: BLE001
                return self._send(200, json.dumps({"ok": False, "error": str(e)}),
                                  "application/json")
        if self.path == "/csvimport":
            try:
                return self._send(200, json.dumps(csv_import(data.get("csv") or "")),
                                  "application/json")
            except Exception as e:                                    # noqa: BLE001
                return self._send(200, json.dumps({"ok": False, "error": str(e)}),
                                  "application/json")
        if self.path == "/bulk":
            # Mark several transcripts reviewed at once. For a batch of thumbs-up
            # conversations that need no ideal response, one-at-a-time is pure friction.
            #
            # Refuses anything that is NOT a clean no-change review, rather than forcing it:
            #   - already reviewed/pushed/excluded  -> skip, do not silently re-stamp
            #   - pre-go-live                        -> skip, it must stay excluded
            #   - carries WRITTEN feedback           -> skip. An ideal response someone typed needs
            #     a real verdict, and bulk-stamping it "nothing wrong" would bury it.
            # Every skip is reported with its reason; nothing fails silently.
            try:
                rels = data.get("paths") or []
                who = (data.get("reviewer") or "").strip()
                if not who:
                    raise ValueError("pick a name first — the reviewer box on any "
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
        if self.path == "/evalask":
            # Ask a live agent an ADJACENT phrasing. This is the point of leaving the candidate
            # content up: a fix that only works for the exact wording the transcript recorded is
            # not a fix, it is a coincidence, and the only way to know is to ask differently.
            key = (data.get("key") or "").strip()
            slug = (data.get("agent") or "").strip()
            q = (data.get("question") or "").strip()
            if not q:
                return self._send(200, json.dumps(
                    {"ok": False, "output": "Type a question first."}), "application/json")
            # No longer refused when nothing is live - the reviewer is warned on the click and
            # may still want to see today's answer. But the provenance is RECORDED, because an
            # answer from published content sitting unlabelled in Earlier would later be read as
            # evidence about the candidate change, which is the opposite of what it is.
            was_live = bool(eval_live())
            ok, ans = eval_ask_live(slug, q)
            at, pct = "", None
            if ok:
                at = (eval_add_variant(key, q, ans, was_live) or {}).get("at", "")
                # Recomputed server-side rather than in the page: the tokeniser and the stop
                # list live here, and a second implementation in JS would drift from this one
                # and disagree with what a reload shows.
                rel_ = key.rsplit("#", 1)[0]
                f_ = REPO / rel_
                if f_.is_file():
                    _, b_ = parse(f_)
                    want = key.rsplit("#", 1)[-1]
                    for r_ in eval_records():
                        if f"{r_[0]}#{r_[2]}" == key:
                            for xn, _t, _qq, _a, rv in exchanges_of(b_ or ""):
                                if xn == r_[7] and rv:
                                    pct = match_pct(correction_text(rv), ans)
                            break
            return self._send(200, json.dumps(
                {"ok": ok, "answer": ans, "question": q, "at": at, "pct": pct,
                 "live": was_live, "output": "" if ok else ans}), "application/json")
        if self.path == "/evalprompt":
            ok, text = eval_improve_prompt((data.get("key") or "").strip(),
                                           data.get("edited") or "")
            return self._send(200, json.dumps(
                {"ok": ok, "prompt": text if ok else "", "output": "" if ok else text}),
                "application/json")
        if self.path == "/evalreupload":
            ok, msg = eval_reupload()
            return self._send(200, json.dumps({"ok": ok, "output": msg}), "application/json")
        if self.path == "/evalremove":
            ok, msg = eval_remove()
            return self._send(200, json.dumps(
                {"ok": ok, "output": msg, "live": bool(eval_live())}), "application/json")
        if self.path == "/evalapprove":
            # Per-exchange approval. Kept on disk beside the run it approves, not in memory:
            # the reviewer reads several long answers and will navigate away, and an approval
            # lost to a page reload is worse than no approval at all.
            act = (data.get("action") or "").strip()
            try:
                if act == "all":
                    keys = [f"{r[0]}#{r[2]}" for r in eval_records()]
                    set_eval_approval(keys, bool(data.get("on")))
                elif act == "one":
                    set_eval_approval([str(data.get("key") or "")], bool(data.get("on")))
                all_ok, n_ok, n_tot = eval_all_approved()
                return self._send(200, json.dumps(
                    {"ok": True, "allOk": all_ok, "nOk": n_ok, "nTot": n_tot}),
                    "application/json")
            except Exception as e:                                        # noqa: BLE001
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
                elif act == "bp-merge":
                    # AUTO-MERGE, not merge. Blueprint requires its own CI ("Build / Build and
                    # Test") and takes minutes, so a plain merge would just be refused for being
                    # behind the checks. `--auto` hands the waiting to GitHub, which merges the
                    # moment they pass - the repo has auto-merge enabled, which is what makes this
                    # possible rather than a polling loop here.
                    rc, out = gh("pr", "merge", num, "--repo", BP_REMOTE, "--squash", "--auto",
                                 "--delete-branch")
                    if rc == 0:
                        out = ("Queued. GitHub merges it as soon as Blueprint's checks pass — "
                               "there is no need to wait here.\n\n" + out
                               + "\n\nMerge the knowledge request too, or the fix ships without "
                                 "the documentation it was derived from.")
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

                        # MERGE PUBLISHES. This button is the whole "make it live" action, not
                        # the first half of one - see publish_after_merge().
                        kbf = merged_knowledge_files(num)
                        okpub, msgpub = publish_after_merge(kbf)
                        if not okpub:
                            rc = 1        # a merge that did not reach the agents is not done

                        parts = [head + out]
                        if msgp:
                            parts.append(msgp)
                        if kbf:
                            parts.append(f"Publishing {len(kbf)} knowledge file(s) to Foundry:\n"
                                         + "\n".join("  " + f for f in kbf))
                        parts.append(msgpub)
                        if okpub and kbf:
                            parts.append("Live and verified by retrieval. Close out the "
                                         "transcripts with:\n"
                                         "  python3 scripts/mark_pushed.py --all")
                        out = "\n\n".join(parts)
                    elif not override and _needs_override(out):
                        out += ("\n\nGitHub refused because the required approval is missing. "
                                "It can be merged anyway as an admin — that BYPASSES the review "
                                "gate, so only do it on own work:\n"
                                "  press Merge anyway on an own change request")
                    elif updated:
                        out += ("\n\nThe branch WAS brought up to date, so that part is done "
                                "— the refusal above is a different reason. Required checks "
                                "re-run after a rebase, so if they are still queued, give them "
                                "a moment and try again.")
                else:
                    rc, out = 1, "unknown action"
                # A merge from here is the only thing that ADDS to the history, so it drops that
                # cache itself. Otherwise the request just merged is missing from the list for up
                # to five minutes on the very page where it was merged.
                if rc == 0 and act in ("merge", "merge-override", "bp-merge"):
                    drop_merged_cache()
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
                elif act == "eval":
                    # SYNC BOTH REPOS FIRST. An eval measures the candidate content against what
                    # is live, and a stale `main` makes both halves of that wrong: the candidate
                    # set is computed as "differs from origin/main", so anything a colleague
                    # merged meanwhile is counted as this batch's change and gets uploaded under
                    # this batch's name. Five minutes of Foundry calls is a long way to go on the
                    # wrong input.
                    #
                    # Fast-forward only, and a refusal is reported rather than forced - see
                    # pull_main. Failing to sync does NOT stop the eval: on a review lane the
                    # tree is deliberately left alone, so "could not sync" is often just "you
                    # have work in progress", which is not a reason to refuse to check it.
                    sync_notes = []
                    _oks, msgs = pull_main()
                    if msgs.strip():
                        sync_notes.append(msgs.strip())
                    if bp_batch():
                        _okb, msgb = bp_sync()
                        sync_notes.append(msgb.strip())
                    # SAVE THE REVIEWER'S WORK FIRST, for the same reason "Process Part 2"
                    # does. The eval reads the WORKING TREE, so it evaluates uncommitted edits -
                    # and then spends five minutes talking to Foundry, which is a long window in
                    # which to lose them to a crash or a closed laptop.
                    #
                    # THIS is the auto-save. The .eval/ directory is NOT: that holds the bytes
                    # FOUNDRY was serving before the upload, so the old live content can be put
                    # back. It protects the collections, not the reviewer.
                    pre = ""
                    if git("status", "--porcelain", "--", *review_scope())[1].strip():
                        rc0, out0 = save_reviews(auto_commit_message())
                        if rc0 != 0:
                            return self._send(200, json.dumps({"ok": False, "output": (
                                "Could not save the work in progress, so the check did NOT run — five "
                                "minutes of Foundry calls is too long to hold uncommitted "
                                "edits:\n\n" + out0.strip()[:400])}), "application/json")
                        pre = "Saved the work in progress first:\n" + out0.strip()[:400]
                    else:
                        pre = "Nothing to save — the work is already committed."
                    if sync_notes:
                        pre = "Synced first:\n  " + "\n  ".join(sync_notes) + "\n\n" + pre

                    # Minutes long by nature - two Bedrock syncs. Runs the script rather than
                    # reimplementing it, so the restore-point-to-disk guarantee and the
                    # --restore-only recovery path are the same ones a terminal would get.
                    if not os.environ.get("FOUNDRY_API_KEY"):
                        rc, out = 1, (pre + "\n\nFOUNDRY_API_KEY is not set in the environment "
                                      "this server was started from, so the check cannot talk "
                                      "to Foundry.")
                    else:
                        r = subprocess.run(
                            # --keep: the content stays live so adjacent phrasings can be
                            # tried on the Eval Review tab. It comes down when the reviewer
                            # clicks Remove, or automatically when they send the batch in.
                            [sys.executable, str(REPO / "scripts" / "eval_batch.py"),
                             "--yes", "--keep"],
                            cwd=REPO, capture_output=True, text=True, timeout=1800)
                        out = pre + "\n\n" + ((r.stdout or "") + (r.stderr or "")).strip()
                        rc = r.returncode
                        if rc == 0:
                            # Tied to the content that was actually evaluated. Change a knowledge
                            # file after this and the fingerprint stops matching, so the gate
                            # closes again rather than trusting a stale run.
                            set_eval_ran(candidate_fingerprint())
                elif act == "reset-pending":
                    # Status only. Ideal responses, summaries and field values stay - the verdict was
                    # premature, not wrong to have been written, and throwing the prose away
                    # would make the reviewer redo the part that took the thinking.
                    changed, bpmsgs = [], []
                    _, listed = git("diff", "--name-only", "origin/main", "--", "transcripts")
                    for rel in (l.strip() for l in listed.splitlines()):
                        if not rel.endswith(".md") or Path(rel).name in (
                                "README.md", "INDEX.md", "ONBOARDING.md"):
                            continue
                        f = REPO / rel
                        if not f.is_file():
                            continue
                        fm, _ = parse(f)
                        if (fm or {}).get("review_status") in ("reviewed", "suggested"):
                            set_fields(f, {"review_status": "pending"})
                            changed.append(rel)
                            # THE BLUEPRINT EDITS GO BACK TOO. They are part of the same rejected
                            # change: left staged, they would ride out on the next send attached
                            # to a verdict that no longer exists, and Blueprint would carry a
                            # wording nobody approved. Only this transcript's are dropped -
                            # that is what the per-transcript patch is for.
                            if (fm or {}).get("bp_updates", "").strip().lower() in (
                                    "yes", "true", "1"):
                                _ok, bmsg = bp_unstage(rel)
                                bpmsgs.append("  " + bmsg)
                    refresh_index()
                    rc = 0
                    out = (("Put back to pending:\n" + "\n".join("  " + c for c in changed)
                            + ("\n\nBlueprint:\n" + "\n".join(bpmsgs) if bpmsgs else "")
                            + "\n\nIdeal responses, summaries and field values were left alone. "
                              "Keep working, then send the batch in when the answers come out "
                              "right.") if changed else
                           "Nothing in this batch was reviewed or suggested, so there was "
                           "nothing to put back.")
                elif act == "pr":
                    # SYNC BOTH REPOS FIRST, before anything is pushed. `main` moving under a
                    # lane is the ordinary case on an active day, and it decides two things that
                    # are hard to unpick afterwards: which files count as this batch's change,
                    # and whether the request can merge at all (this repo sets
                    # required_status_checks.strict, so a branch behind main is blocked).
                    # Blueprint matters more sharply - bp_stage_add refuses outright on a stale
                    # tree, because a patch captured there reverts other people's work.
                    sync_pre = []
                    _oks, msgs = pull_main()
                    if msgs.strip():
                        sync_pre.append(msgs.strip())
                    if bp_batch():
                        _okb, msgb = bp_sync()
                        sync_pre.append(msgb.strip())
                    # NO CHANGE REQUEST UNTIL THE EVAL HAS BEEN RUN AND ITS ANSWERS SEEN.
                    #
                    # Enforced HERE and not only on the button, because the checkbox can be
                    # unticked and the endpoint can be called directly - a gate that lives only
                    # in the page is a suggestion. The point of the eval is that a knowledge
                    # change is judged by what the agent SAYS next, and a request opened without
                    # that has skipped the only step that checks the thing that matters.
                    #
                    # Only applies when there is something to evaluate: knowledge files changed
                    # AND transcripts with questions to replay. A batch of verdicts with no
                    # content change has nothing an eval could tell you, and blocking it would be
                    # a gate with no question behind it.
                    fp = candidate_fingerprint()
                    _, n_q, _ = eval_estimate()
                    ran = eval_ran_fingerprint()
                    if fp and n_q and ran != fp:
                        why = ("the check has not been run on this version yet"
                               if ran is None else
                               "a knowledge file changed after the last check, so its answers "
                               "were about different content")
                        return self._send(200, json.dumps({"ok": False, "output": (
                            "No change request was created — " + why + ".\n\n"
                            "Tick \"Include Eval Review\" and press "
                            "the <b>Process</b> button. It uploads the candidate files, asks the agents "
                            "this batch's questions, puts Foundry back, and reports the "
                            "answers. Read them, then send it in.\n\n"
                            "Nothing has been pushed and nothing was lost — the work is saved "
                            "locally either way.")}), "application/json")

                    # AND every replayed transcript must be individually approved. Running the
                    # eval is not approving it: the old flow treated "the script exited 0" as
                    # consent, so a batch could be sent in by somebody who never read a single
                    # answer. The per-transcript decision lives on /evalreview and this is the
                    # check that makes it mean something.
                    if fp and n_q:
                        all_ok, n_ok, n_tot = eval_all_approved()
                        if n_tot and not all_ok:
                            return self._send(200, json.dumps({"ok": False, "output": (
                                f"No change request was created — {n_ok} of {n_tot} "
                                "transcript(s) are approved.\n\n"
                                "Open Eval Review and tick each transcript whose answer is "
                                "right. If an answer is still wrong, the change is not ready: "
                                "put the batch back to pending and keep working.\n\n"
                                "Nothing has been pushed and nothing was lost.")}),
                                "application/json")

                    # TAKE THE CANDIDATE CONTENT DOWN NOW. It was left live so adjacent
                    # phrasings could be tried; from here the batch is going through review, and
                    # unapproved content has no business serving users while it waits. It goes
                    # back up permanently on Merge, via publish_after_merge - so this is a
                    # hand-off, not a loss.
                    #
                    # Placed AFTER the gates above on purpose: a send refused for want of an
                    # eval or an approval must leave the reviewer's live content exactly where
                    # it was, or the refusal would cost them the thing they were still using.
                    if eval_live():
                        okr, msgr = eval_remove()
                        sync_pre.append(("Removed the live eval content." if okr
                                         else "COULD NOT remove the live eval content — "
                                              "it may still be serving users. " + msgr[:200]))

                    # Save FIRST, always. "Process Part 2" used to push and open a PR
                    # without committing, so a reviewer who never clicked Save sent an empty
                    # change request and was told it worked. Save is a checkpoint a reviewer
                    # may want; it must not be a prerequisite they can forget.
                    rc, out = save_reviews(msg)
                    if rc not in (0, NOTHING_TO_SAVE):
                        raise RuntimeError(out)
                    if sync_pre:
                        out = "Synced first:\n  " + "\n  ".join(sync_pre) + "\n\n" + out
                    _, cur = git("rev-parse", "--abbrev-ref", "HEAD")
                    prc, pout = git("push", "-u", "origin", cur.strip(), timeout=180)
                    out = (out + "\n\n" + pout).strip()
                    rc = prc
                    # BLUEPRINT GOES OUT AT THE SAME TIME. Marked transcripts mean the feedback
                    # implies Blueprint work too, and most indexed knowledge is DERIVED from
                    # Blueprint - so a Docusaurus- knowledge file fixed on its own is reverted by
                    # the next reconciliation. Shipping one without the other is shipping a fix
                    # with a countdown on it.
                    # ONE REQUEST PER TRANSCRIPT, not one per batch. A combined request cannot be
                    # unwound per transcript: rejecting one answer would drag back another
                    # transcript's approved Blueprint fix, and Blueprint's reviewers would be
                    # reading one diff answering to several unrelated verdicts. Each is built
                    # from its own staged patch on its own branch off master, so they merge
                    # independently and a conflict between two of them is visible rather than
                    # resolved silently inside one diff.
                    bp_marked = bp_batch()
                    if prc == 0 and bp_marked:
                        hint = cur.strip().replace("review/", "").replace("/", "-")
                        lines, bad = [], []
                        for rel in bp_marked:
                            bok, bmsg = bp_open_pr_for(rel, hint)
                            lines.append(("  " if bok else "  FAILED ") + bmsg)
                            if not bok:
                                bad.append(rel)
                        out += ("\n\nBlueprint change requests (one per transcript):\n"
                                + "\n".join(lines))
                        if bad:
                            out += ("\n\nThe knowledge request WAS created. "
                                    f"{len(bad)} Blueprint request(s) were not — fix the above "
                                    "and re-run, or open them by hand.")
                    if prc == 0:
                        r = subprocess.run(["gh", "pr", "create", "--fill"], cwd=REPO,
                                           capture_output=True, text=True, timeout=180)
                        rc = r.returncode
                        out = (out + "\n" + r.stdout + r.stderr).strip()
                        # AUTO-MERGE ON THE KNOWLEDGE REQUEST TOO. Same reasoning as Blueprint:
                        # a contributor opens it and an admin approves, and auto-merge is what
                        # joins those without somebody having to return at the right moment.
                        # Reported, not fatal - the request is correct either way, and an admin
                        # can switch it on.
                        if rc == 0:
                            # Tag BEFORE arming auto-merge. Auto-merge can land the request
                            # immediately when it is already approved and green, and `gh pr edit`
                            # resolves the branch name - which is deleted on merge. Ordering it
                            # first removes that race entirely.
                            ok_tag, tagmsg = tag_pr(cur.strip())
                            if not ok_tag:
                                out += f"\n\nNot tagged {REVIEW_LABEL}: {tagmsg}"
                            drop_merged_cache()
                            a = subprocess.run(
                                ["gh", "pr", "merge", cur.strip(), "--rebase", "--auto",
                                 "--delete-branch"],
                                cwd=REPO, capture_output=True, text=True, timeout=150)
                            aout = ((a.stdout or "") + (a.stderr or "")).strip()
                            out += ("\n\nAuto-merge ON — it merges itself once an admin approves "
                                    "and CI passes." if a.returncode == 0 else
                                    "\n\nAuto-merge could NOT be set; an admin needs to turn it "
                                    "on: " + (aout.splitlines()[-1][:160] if aout.strip()
                                              else "no output from gh"))
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
    ap.add_argument("--me", help="the GitHub username to highlight rows for; "
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
              f"as the reviewer. Pass --me with a registered name if that is wrong.", flush=True)
        ME = None
    if not ME:
        print("note: no reviewer identified, so no rows are highlighted. "
              "Pass --me <github-username>, or check `gh auth status`.", flush=True)
    else:
        by, dflt = agent_owners()
        if not by and not dflt:
            print("note: agent-owners.json is missing or unreadable — no ownership "
                  "highlighting. Row colouring is a convenience; everything else works.",
                  flush=True)
        print(f"identified as: {ME}", flush=True)
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
