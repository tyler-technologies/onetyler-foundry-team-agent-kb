#!/usr/bin/env python3
"""
Pull Foundry conversation transcripts into transcripts/ as reviewable markdown.

One file per conversation, with YAML-ish frontmatter for review metadata and the
exchanges in the body. Safe to re-run: an existing file is NEVER overwritten, so
human review edits are preserved. New conversations are added as `pending` stubs.

Secrets are redacted on the way in (see REDACTIONS) because this repo is public
and agents have been observed reproducing credentials from their knowledge base.

Usage:
    export FOUNDRY_API_KEY=...
    python3 scripts/fetch_transcripts.py                 # all agents + team
    python3 scripts/fetch_transcripts.py --agent sac     # one agent
    python3 scripts/fetch_transcripts.py --start 06/01/2026
    python3 scripts/fetch_transcripts.py --dry-run
"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

BASE = os.environ.get("FOUNDRY_API_URL", "https://foundry.tylertechai.com")
KEY = os.environ.get("FOUNDRY_API_KEY", "")
UA = "claude-code-foundry-kb/1.0"          # a missing User-Agent gets a 403 from the WAF
REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "transcripts"

AGENTS = {
    "ops-center": "5b3efdff-921a-4131-be81-b7a4be427d9b",
    "bp-general": "bd1c5d91-8234-486e-9f5a-2f1b7a947426",
    "sac":        "55444576-1fa3-4d12-a738-6ba83b17e6a7",
    "identity":   "3f5e586f-0d0f-4638-9839-bebe45a6cb47",
}
TEAM_ID = "e92bd437-cb84-4e18-88e6-757370b39c90"

# Applied to every question and response before writing to disk. Order matters.
REDACTIONS = [
    # Known live credential the agents have been seen handing out verbatim.
    (re.compile(r"W#lcome123\$"), "[REDACTED-CREDENTIAL]"),
    # Any password/secret/token assignment with a real-looking value.
    #
    # The leading (?:\w*[_-])? matters: `\bsecret\b` can NEVER match inside `client_secret`,
    # because the underscore is a word character so there is no boundary before "secret".
    # A real `client_secret=...` therefore slipped straight through. Caught 2026-08-24 by the
    # pre-publish scan, before the first push to a public repo.
    #
    # The trailing `&` in the exclusion set stops a match running past the end of one
    # query-string parameter into the next.
    # The whole key name is captured, prefix included, so `client_secret=` stays
    # `client_secret=[REDACTED-CREDENTIAL]` rather than collapsing to `secret=`.
    (re.compile(r"(?i)\b((?:\w*[_-])?(?:password|passwd|secret|api[_ -]?key))\b"
                r"(\s*[:=]\s*)`?[^\s`\"'<>{}&]{6,}`?"),
     r"\1\2[REDACTED-CREDENTIAL]"),
    # Real JWTs (a long body after the header). Short doc placeholders are left alone.
    (re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}[.A-Za-z0-9_-]*"), "[REDACTED-TOKEN]"),
    # Real Tyler staff addresses. Doc-example addresses on other domains are kept,
    # since they carry meaning for the reviewer.
    (re.compile(r"\b[\w.+-]+@tylertech\.com\b"), "[REDACTED-EMAIL]"),
]

# Canned starting prompts ("sample questions") shown as clickable chips by the team and
# each sub-agent, read live from chatExperience.sampleQuestions on 2026-08-21. A user
# clicking a chip tells us nothing about real information needs, and these dominate the
# raw data by volume, so exchanges matching one are dropped. Re-check these if the agents'
# chat experience is reconfigured.
SAMPLE_PROMPTS = {
    # team
    "I need help with Identity", "I need help with Ops Center",
    "I need help with Support Access Center", "I need help with other topics",
    # ops-center
    "How do I get access to Ops Center?", "How can I get access to a client's Admin Center?",
    "Where can I see the Identity Configuration details for a customer?",
    "Where can I see Ops Center training and other useful guides?",
    # bp-general
    "What can you help me with?", "Which tools do you have access to?",
    "How do I get started?", "Can you summarize what you can do for me?",
    # sac
    "How do I get access to Support Access Center?",
    "How do I integrate my product with Support Access Center?",
    "How do I request access to my product for a customer installation?",
    "How do I extend access?", "How do I see past access?",
    # identity
    "How does Tyler Identity handle SSO with SAML?",
    "What are the steps to onboard a new client tenant?",
    "How do I configure Entra ID as an external identity provider?",
    "What token types does Tyler Identity support?",
    "How does MFA work in Tyler Identity?",
}


def live_sample_prompts():
    """Fetch the sample-question chips from Foundry rather than trusting the list below.

    The hardcoded set went stale the moment a new agent was added: the Aligned Releases
    agent and its team prompt were created on 2026-08-23 and the list was not updated, so
    five chip-click conversations came through as if they were real questions. Reading the
    live config makes that impossible. Falls back to SAMPLE_PROMPTS if Foundry is
    unreachable, so an offline fetch still filters the known ones.
    """
    out = set()
    team = api(f"/api/teams/{TEAM_ID}") or {}
    team = team.get("team", team)
    for src in (team.get("chatExperience") or {}, (team.get("orchestrator_config") or {}).get("chatExperience") or {}):
        out.update(src.get("sampleQuestions") or [])
    for aid in AGENTS.values():
        a = api(f"/api/configurable-agents/{aid}") or {}
        out.update((a.get("chatExperience") or {}).get("sampleQuestions") or [])
    return {q for q in out if isinstance(q, str) and q.strip()}


def norm(s):
    """Loose match so punctuation/casing/whitespace drift doesn't defeat the filter."""
    return re.sub(r"[\s]+", " ", (s or "").strip().lower()).rstrip("?.!, ")


SAMPLE_NORM = {norm(p) for p in SAMPLE_PROMPTS}   # replaced with the live set in main()


def keep_exchange(e):
    """Keep only real user turns: a genuine prompt AND a response, not a canned chip."""
    q = (e.get("question") or "").strip()
    r = (e.get("response") or "").strip()
    if not q or not r:
        return False
    return norm(q) not in SAMPLE_NORM


# Review fields a human fills in. Kept in the file so the schema is self-documenting.
REVIEW_TEMPLATE = """review_status: pending
reviewer:
routing_verdict:
reassign_to:
answer_verdict:
diagnosis:
fix_target:
kb_action:
kb_files:
action_status: open
notes:"""


def api(path):
    r = subprocess.run(["curl", "-s", "-A", UA, "-H", f"X-API-Key: {KEY}", BASE + path],
                       capture_output=True, text=True)
    if not r.stdout.strip():
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        print(f"  ! non-JSON from {path[:70]} (auth failure?)", file=sys.stderr)
        return None


def team_delegation():
    """conversationId -> which sub-agents the orchestrator actually invoked.

    Team transcripts carry NO metadataMessages, so the only record of who handled a
    team conversation is the run spans in /api/team-logs. Span names look like
    "agent: 'Ops Center'" and "tool: 'searchTenantKnowledge'".
    """
    out = {}
    d = api(f"/api/team-logs?teamId={TEAM_ID}&limit=500") or {}
    for run in (d.get("logs") or []):
        cid = run.get("conversationId")
        if not cid:
            continue
        rec = out.setdefault(cid, {"agents": [], "tools": [], "pattern": None, "strategy": None})
        for sp in (run.get("spans") or []):
            name = sp.get("name") or ""
            m = re.search(r"'(.*)'", name)
            label = m.group(1) if m else name
            if sp.get("span_type") == "agent" or name.startswith("agent:"):
                rec["agents"].append(label)
            elif sp.get("span_type") == "tool" or name.startswith("tool:"):
                rec["tools"].append(label)
        rec["pattern"] = rec["pattern"] or run.get("orchestrationPattern")
        rec["strategy"] = rec["strategy"] or run.get("strategy")
    for rec in out.values():                       # de-dupe, preserve first-seen order
        rec["agents"] = list(dict.fromkeys(rec["agents"]))
        rec["tools"] = list(dict.fromkeys(rec["tools"]))
    return out


def scrub(text):
    t = text or ""
    for pat, repl in REDACTIONS:
        t = pat.sub(repl, t)
    return t


def render(slug, meta, data, deleg=None):
    """Returns the file body, or None if nothing worth reviewing survives filtering."""
    cid = data["conversationId"]
    date = (meta.get("conversationDate") or "")[:19].replace("T", " ") or "unknown"
    raw = data.get("conversation", []) or []

    # Keep the original 1-based index so a reviewer can correlate with Foundry's UI.
    kept = [(i, e) for i, e in enumerate(raw, 1) if keep_exchange(e)]
    if not kept:
        return None
    dropped = len(raw) - len(kept)

    fb = [e.get("feedback") for _, e in kept if e.get("feedback") and e["feedback"] != "NO_ACTION"]
    comments = [e.get("thumbsDownTextFeedback") for _, e in kept if e.get("thumbsDownTextFeedback")]

    L = ["---",
         f"conversation_id: {cid}",
         f"answered_by: {slug}",
         f"date: {date}",
         f"exchanges: {len(kept)}",
         f"dropped_sample_prompts: {dropped}",
         f"foundry_feedback: {', '.join(fb) if fb else 'none'}",
         f"user_comments: {json.dumps(comments) if comments else '[]'}",
         f"delegated_to: {', '.join(deleg['agents']) if deleg and deleg.get('agents') else ''}",
         f"orchestration: {(deleg or {}).get('pattern') or ''}"
         f"{'/' + deleg['strategy'] if deleg and deleg.get('strategy') else ''}",
         "",
         "# ---- review fields: edit these ----",
         REVIEW_TEMPLATE,
         "---",
         "",
         f"# Transcript — {slug} — {date}",
         ""]
    if dropped:
        L += [f"_{dropped} canned starting-prompt exchange(s) omitted._", ""]
    if slug == "team":
        ags = (deleg or {}).get("agents") or []
        tls = (deleg or {}).get("tools") or []
        L += ["## Delegation", "",
              "| | |", "|---|---|",
              f"| **Sub-agent(s) invoked** | {', '.join(ags) if ags else '_no team-log found for this conversation_'} |",
              f"| **Tools used across the run** | {', '.join(tls) if tls else '_none recorded_'} |",
              f"| **Orchestration** | {(deleg or {}).get('pattern') or '?'} / {(deleg or {}).get('strategy') or '?'} |",
              "",
              "_Source: run spans in `/api/team-logs`. Team transcripts carry no per-exchange"
              " tool detail, so the above is for the whole conversation, not one exchange._", ""]

    for i, e in kept:
        mm = e.get("metadataMessages") or []
        tools = [tc.get("name") for m in mm for tc in (m.get("toolCalls") or []) if tc.get("name")]
        L += [f"## Exchange {i}", ""]
        if e.get("feedback") and e["feedback"] != "NO_ACTION":
            L += [f"> **Foundry feedback:** {e['feedback']}"]
            if e.get("thumbsDownTextFeedback"):
                L += [f"> **User comment:** {scrub(e['thumbsDownTextFeedback'])}"]
            L += [""]
        if mm:
            L += [f"**Tools called:** {', '.join(tools) if tools else '_none — answered without searching_'}", ""]
        else:
            L += ["**Tools called:** _not recorded for team conversations — see Delegation above_", ""]
        L += ["**Q:**", "", "> " + scrub(e.get("question") or "").replace("\n", "\n> "), ""]
        L += ["**A:**", "", "```markdown", scrub(e.get("response") or ""), "```", ""]
        L += [f"<!-- review:{i} -->",
              "**Review —** _verdict:_ · _should have said:_", "",
              f"<!-- /review:{i} -->", ""]
    L += ["---", "", "## Proposed fix", "",
          "_What should change so this answer is right next time? For an instructions or"
          " routing fix, say exactly what to add or reword._", "",
          "<!-- proposed-fix -->", "", "<!-- /proposed-fix -->", ""]
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", choices=list(AGENTS) + ["team"], help="limit to one agent")
    ap.add_argument("--start", default="01/01/2025", help="startDate (MM/DD/YYYY)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if not KEY:
        sys.exit("FOUNDRY_API_KEY is not set. Source your env file first.")

    # Prefer the live chips over the hardcoded list — see live_sample_prompts().
    global SAMPLE_NORM
    live = live_sample_prompts()
    if live:
        extra = {norm(q) for q in live} - SAMPLE_NORM
        SAMPLE_NORM = SAMPLE_NORM | {norm(q) for q in live}
        print(f"sample-prompt filter: {len(SAMPLE_NORM)} chips "
              f"({len(live)} read live, {len(extra)} not in the hardcoded list)")
    else:
        print("sample-prompt filter: could not read live chips, using the hardcoded list only",
              file=sys.stderr)

    targets = {a.agent: AGENTS[a.agent]} if a.agent in AGENTS else ({} if a.agent == "team" else dict(AGENTS))
    include_team = a.agent in (None, "team")
    new = existing = skipped = 0

    for slug, aid in targets.items():
        lst = api(f"/api/transcripts/conversation_ids?agent_id={aid}&startDate={a.start}") or []
        print(f"{slug}: {len(lst)} conversations" + ("  (200 = CAP HIT, narrow the range)" if len(lst) == 200 else ""))
        for meta in lst:
            cid = meta["conversationId"]
            d = api(f"/api/transcripts/{cid}")
            if not d:
                continue
            p = OUT / slug / f"{(meta.get('conversationDate') or 'unknown')[:10]}--{cid[:8]}.md"
            if p.exists():
                existing += 1
                continue
            body = render(slug, meta, d[0])
            if body is None:
                skipped += 1
                continue
            new += 1
            if not a.dry_run:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(body, encoding="utf-8")

    if include_team:
        lst = api(f"/api/transcripts/team_conversation_ids?team_id={TEAM_ID}&startDate={a.start}") or []
        deleg = team_delegation()
        print(f"team: {len(lst)} conversations ({len(deleg)} with delegation logs)")
        for meta in lst:
            cid = meta["conversationId"]
            d = api(f"/api/transcripts/team/{cid}")
            if not d:
                continue
            p = OUT / "team" / f"{(meta.get('conversationDate') or 'unknown')[:10]}--{cid[:8]}.md"
            if p.exists():
                existing += 1
                continue
            body = render("team", meta, d[0], deleg.get(cid))
            if body is None:
                skipped += 1
                continue
            new += 1
            if not a.dry_run:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(body, encoding="utf-8")

    print(f"\n{'would add' if a.dry_run else 'added'}: {new} new"
          f" | untouched (already present): {existing}"
          f" | skipped (only canned prompts, nothing to review): {skipped}")
    if new and not a.dry_run:
        print("Next: python3 scripts/review_status.py")


if __name__ == "__main__":
    main()
