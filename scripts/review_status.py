#!/usr/bin/env python3
"""
Summarise transcript review progress and regenerate transcripts/INDEX.md.

Reads the frontmatter of every transcript file, prints a dashboard, and writes an
index table so reviewers can see at a glance what is left and what actions are open.

Usage:
    python3 scripts/review_status.py              # dashboard + rewrite INDEX.md
    python3 scripts/review_status.py --pending    # list unreviewed files only
    python3 scripts/review_status.py --actions    # list open KB actions only
    python3 scripts/review_status.py --check      # exit 1 on malformed frontmatter (CI)
    python3 scripts/review_status.py --suggestions             # handoffs awaiting a decision
    python3 scripts/review_status.py --suggestions --for me    # ...just the ones aimed at me
"""
import argparse, json, re, sys
from collections import Counter
from pathlib import Path
from golive import GO_LIVE, EXCLUDE_NOTE, is_pre_go_live
from reviewtext import has_feedback, feedback_summary, needs_triage, body_feedback

REPO = Path(__file__).resolve().parent.parent
TDIR = REPO / "transcripts"
CONTRIB = REPO / "contributors.json"


def contributors():
    try:
        d = json.loads(CONTRIB.read_text(encoding="utf-8"))
        return {c["github"] for c in d.get("contributors", []) if c.get("github")}
    except Exception:
        return set()

FIELDS = ["conversation_id", "answered_by", "date", "exchanges", "foundry_feedback",
          "review_status", "reviewer", "reviewer", "suggested_to", "routing_verdict",
          "reassign_to", "answer_verdict", "diagnosis", "fix_target", "kb_action", "kb_files",
          "action_status", "notes", "review_round"]

# Fields that must name a real contributor. See review_server.PEOPLE_KEYS.
PEOPLE_KEYS = ("reviewer", "reviewer", "suggested_to")

# Not closed out. `suggested` is open work with a name on it, not a verdict.
OPEN = ("pending", "suggested")
DONE = ("reviewed", "pushed", "excluded")


VALID = {
    "review_status":   {"", "pending", "suggested", "reviewed", "pushed", "excluded"},
    "routing_verdict": {"", "correct", "wrong-agent", "ambiguous"},
    "reassign_to":     {"", "ops-center", "bp-general", "sac", "identity", "team"},
    "answer_verdict":  {"", "good", "incomplete", "wrong", "stale", "refused"},
    "diagnosis":       {"", "n-a", "no-search", "search-empty", "search-irrelevant",
                        "retrieved-ok-answered-badly", "routing-only"},
    "fix_target":      {"", "none", "knowledge-file", "agent-instructions",
                        "team-routing", "sample-prompts"},
    "kb_action":       {"", "none", "add", "update", "split"},
    "action_status":   {"", "none-needed", "open", "applied", "wontfix"},
}


def norm_paths(v):
    """Strip a leading repo-name segment if a reviewer pasted a path from higher up.
    'onetyler-foundry-team-agent-kb/Knowledge-X/f.md' -> 'Knowledge-X/f.md'"""
    out = []
    for part in (v or "").split(","):
        t = part.strip()
        if t.startswith(REPO.name + "/"):
            t = t[len(REPO.name) + 1:]
        if t:
            out.append(t)
    return ", ".join(out)


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

def parse(p):
    txt = p.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    if not m:
        return None
    d = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, _, v = line.partition(":")
            d[k.strip()] = v.strip()
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pending", action="store_true")
    ap.add_argument("--actions", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--suggestions", action="store_true",
                    help="list suggestions awaiting a human decision")
    ap.add_argument("--for", dest="for_", metavar="USER",
                    help="with --suggestions: only those handed to USER (or to nobody)")
    a = ap.parse_args()

    files = sorted(TDIR.rglob("*.md"))
    files = [f for f in files if is_transcript(f)]
    if not files:
        sys.exit("No transcripts found. Run: python3 scripts/fetch_transcripts.py")

    people = contributors()
    if not people:
        print("warning: contributors.json missing or empty — reviewer cannot be validated",
              file=sys.stderr)
    rows, bad = [], []
    for f in files:
        d = parse(f)
        if d is None:
            bad.append((f, "no frontmatter"))
            continue
        for k, allowed in VALID.items():
            if d.get(k, "") not in allowed:
                bad.append((f, f"{k}={d.get(k)!r} not in {sorted(allowed - {''})}"))
        for k in PEOPLE_KEYS:
            v = d.get(k, "")
            if v and people and v not in people:
                bad.append((f, f"{k}={v!r} is not in contributors.json"))
        rv = d.get("reviewer", "")
        pre_go_live = is_pre_go_live(d.get("date", ""))
        st = d.get("review_status")
        # A pre-go-live exclusion is arithmetic, not a judgement, so it needs no reviewer —
        # fetch_transcripts.py stamps it automatically. Every OTHER done-state still does.
        if st in DONE and not rv and not (st == "excluded" and pre_go_live):
            bad.append((f, f"review_status={st} but no reviewer set"))
        # The reverse, and the reason this check exists: a pre-go-live transcript must not be
        # reviewed or suggested. It is not user signal, so a verdict on it is wasted work that
        # also inflates the reviewed percentage with review nobody needed to do.
        if pre_go_live and st in ("reviewed", "suggested", "pushed"):
            bad.append((f, f"date {d.get('date')} is before go-live ({GO_LIVE}) but "
                           f"review_status={st} — pre-go-live conversations are internal "
                           f"testing and belong in 'excluded', not the review queue"))
        # An unattributed suggestion is the failure this state exists to prevent: the owner
        # inherits verdict-shaped fields with nobody to ask what they meant.
        if d.get("review_status") == "suggested" and not d.get("reviewer"):
            bad.append((f, "review_status=suggested but no reviewer set"))
        rows.append((f, d))

    if a.check:
        for f, why in bad:
            print(f"INVALID {f.relative_to(REPO)}: {why}")
        sys.exit(1 if bad else 0)

    if a.pending:
        for f, d in rows:
            if d.get("review_status", "pending") not in DONE:
                print(f.relative_to(REPO))
        return
    if a.suggestions:
        # What an area owner runs to find work handed to them. `awaiting` unset means the
        # suggester named no owner, so it is everyone's to pick up — always show those.
        hits = [(f, d) for f, d in rows if d.get("review_status") == "suggested"
                and (not a.for_ or d.get("suggested_to", "") in ("", a.for_))]
        for f, d in hits:
            print(f"{f.relative_to(REPO)}  from {d.get('reviewer','?')}"
                  f"  -> {d.get('suggested_to') or 'anyone'}"
                  f"  [{d.get('answered_by','?')}]  {d.get('notes','')[:70]}")
        if not hits:
            print("no suggestions waiting" + (f" for {a.for_}" if a.for_ else ""))
        return
    if a.actions:
        # Only REVIEWED items are actionable. A pending transcript with fields filled in is
        # work in progress - acting on it would pre-empt a human who has not finished, and
        # CLAUDE.md forbids it. Those are listed separately so they are not invisible.
        #
        # TWO ways an item is actionable, and the second one is the common one:
        #   (a) the fields say so - kb_action add/update/split with action_status open
        #   (b) the reviewer WROTE something, whatever the fields say
        #
        # (b) exists because reviewers write the correction and click "Mark reviewed" without
        # touching the dropdowns, which is fine and expected. The form is pre-filled as
        # "no changes needed", so those transcripts claim kb_action: none while the body says
        # the answer was wrong. Keying only on (a) made them invisible: --actions printed
        # nothing while the dashboard said work was waiting.
        ready, triage, inflight = [], [], []
        for f, d in rows:
            txt = f.read_text(encoding="utf-8")
            classified = (d.get("kb_action", "") in {"add", "update", "split"}
                          and d.get("action_status") == "open")
            written = has_feedback(txt) and d.get("action_status") not in ("applied", "wontfix")
            if not (classified or written):
                continue
            if d.get("review_status") != "reviewed":
                inflight.append((f, d))
            elif classified:
                ready.append((f, d))
            else:
                triage.append((f, d, txt))
        for f, d in ready:
            print(f"{f.relative_to(REPO)}  {d.get('kb_action')}  {norm_paths(d.get('kb_files',''))}")
        if triage:
            print(f"\n-- {len(triage)} reviewed transcript(s) with WRITTEN feedback and no "
                  f"classification. Read the body; the fields are still the pre-filled "
                  f"\"nothing wrong\" defaults and mean nothing here --")
            for f, d, txt in triage:
                fb = body_feedback(txt)
                where = ", ".join(f"exchange {n}" for n in sorted(fb["corrections"])) or "-"
                print(f"   {f.relative_to(REPO)}")
                print(f"      by {d.get('reviewer') or d.get('reviewer') or '?'}"
                      f" | corrections in: {where}"
                      f" | proposed fix: {'yes' if fb['proposed'] else 'no'}")
                print(f"      \"{feedback_summary(txt)}\"")
        if inflight:
            print(f"\n-- not actionable yet: {len(inflight)} transcript(s) have an open action "
                  f"but review_status is not 'reviewed' --", file=sys.stderr)
            for f, d in inflight:
                who = (f"reviewer={d.get('reviewer') or 'unset'}, "
                       f"suggested_to={d.get('suggested_to') or d.get('reassign_to') or 'unassigned'}"
                       if d.get("review_status") == "suggested"
                       else f"reviewer={d.get('reviewer') or 'unset'}")
                print(f"   {f.relative_to(REPO)}  ({d.get('review_status')}, {who})",
                      file=sys.stderr)
        return

    # dashboard
    tot = len(rows)
    st = lambda v: sum(1 for _, d in rows if d.get("review_status") == v)
    excl, pend, rev, push = st("excluded"), st("pending"), st("reviewed"), st("pushed")
    sugg = st("suggested")
    inscope = tot - excl
    closed = push
    print(f"Transcripts: {tot}   (excluded {excl}, in scope {inscope})")
    print(f"  lifecycle:  pending {pend}  ->  suggested {sugg}  ->  reviewed {rev}"
          f"  ->  pushed {push}   ({100*closed//inscope if inscope else 0}% closed out)")
    if rev:
        print(f"  ** {rev} reviewed and awaiting processing - run --actions **")
    # Counted from the BODY, because that is where the feedback is. Reported separately from
    # "open KB actions" below, which counts fields — a reviewer who wrote a correction and
    # left the dropdowns alone appears here and nowhere else.
    untriaged = [(f, d) for f, d in rows
                 if d.get("review_status") in ("reviewed", "suggested")
                 and d.get("action_status") not in ("applied", "wontfix")
                 and needs_triage(d, f.read_text(encoding="utf-8"))]
    if untriaged:
        print(f"  ** {len(untriaged)} transcript(s) carry WRITTEN feedback that nobody has "
              f"classified - run --actions and read the prose **")
    if sugg:
        # Name the owners, because the whole point of the state is that it is waiting on a
        # specific person. A bare count reads as progress rather than as a queue.
        wait = Counter(d.get("suggested_to") or "anyone" for _, d in rows
                       if d.get("review_status") == "suggested")
        print(f"  ** {sugg} suggestion(s) awaiting a decision: "
              + ", ".join(f"{k} ({v})" for k, v in sorted(wait.items()))
              + " - run --suggestions **")
    print()
    print("by agent (reviewed or pushed / total):")
    per = Counter(d.get("answered_by", "?") for _, d in rows)
    perdone = Counter(d.get("answered_by", "?") for _, d in rows
                      if d.get("review_status") in ("reviewed", "pushed"))
    for k in sorted(per):
        print(f"  {k:12} {perdone[k]:>3}/{per[k]:<3}")
    for label, key in [("routing verdict", "routing_verdict"), ("answer verdict", "answer_verdict"),
                       ("diagnosis", "diagnosis"), ("fix target", "fix_target"),
                       ("kb action", "kb_action")]:
        c = Counter(d.get(key, "") or "(blank)" for _, d in rows)
        print(f"\n{label}: " + "  ".join(f"{k}={v}" for k, v in sorted(c.items())))
    reassign = [(f, d) for f, d in rows if d.get("reassign_to")]
    if reassign:
        print(f"\nreassignments proposed: {len(reassign)}")
        for f, d in reassign:
            print(f"  {d.get('answered_by')} -> {d['reassign_to']}   {f.name}")
    withtext = sum(1 for f, d in rows if has_feedback(f.read_text(encoding="utf-8")))
    print(f"\ntranscripts carrying written feedback: {withtext}"
          f"   (the fields may say otherwise - the prose is the signal)")
    openacts = [(f, d) for f, d in rows
                if d.get("kb_action") in {"add", "update", "split"} and d.get("action_status") == "open"]
    print(f"\nopen KB actions (by field): {len(openacts)}")
    for f, d in openacts:
        print(f"  [{d.get('kb_action')}] {d.get('kb_files','(unspecified)')}  <- {f.name}")
    if bad:
        print(f"\n⚠ {len(bad)} file(s) with invalid frontmatter — run --check")

    # INDEX.md
    L = ["# Transcript review index", "",
         f"_Generated by `scripts/review_status.py`. {tot} transcripts: "
         f"{pend} pending, {sugg} suggested, {rev} reviewed, {push} pushed, "
         f"{excl} excluded._", "",
         "| Transcript | Agent | Date | Ex | Foundry FB | Status | Routing | Answer | Diagnosis | KB action |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for f, d in rows:
        rel = f.relative_to(TDIR).as_posix()
        L.append("| [{}]({}) | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            f.stem, rel, d.get("answered_by", ""), (d.get("date", "") or "")[:10],
            d.get("exchanges", ""), d.get("foundry_feedback", ""),
            (d.get("review_status", "")
             + (f" ({d.get('reviewer','?')}→{d.get('suggested_to') or 'anyone'})"
                if d.get("review_status") == "suggested" else "")),
            d.get("routing_verdict", "") + ("→" + d["reassign_to"] if d.get("reassign_to") else ""),
            d.get("answer_verdict", ""), d.get("diagnosis", ""),
            (d.get("kb_action", "") or "") + (f" ({d.get('action_status')})" if d.get("kb_action") in {"add","update","split"} else "")))
    (TDIR / "INDEX.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nwrote {(TDIR/'INDEX.md').relative_to(REPO)}")


if __name__ == "__main__":
    main()
