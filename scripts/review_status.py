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
"""
import argparse, json, re, sys
from collections import Counter
from pathlib import Path

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
          "review_status", "reviewer", "routing_verdict", "reassign_to",
          "answer_verdict", "diagnosis", "fix_target", "kb_action", "kb_files",
          "action_status", "notes", "review_round"]

VALID = {
    "review_status":   {"", "pending", "reviewed", "pushed", "excluded"},
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
        rv = d.get("reviewer", "")
        if rv and rv not in people:
            bad.append((f, f"reviewer={rv!r} is not in contributors.json"))
        if d.get("review_status") in ("reviewed", "pushed", "excluded") and not rv:
            bad.append((f, f"review_status={d.get('review_status')} but no reviewer set"))
        rows.append((f, d))

    if a.check:
        for f, why in bad:
            print(f"INVALID {f.relative_to(REPO)}: {why}")
        sys.exit(1 if bad else 0)

    if a.pending:
        for f, d in rows:
            if d.get("review_status", "pending") not in ("reviewed", "pushed", "excluded"):
                print(f.relative_to(REPO))
        return
    if a.actions:
        # Only REVIEWED items are actionable. A pending transcript with fields filled in is
        # work in progress - acting on it would pre-empt a human who has not finished, and
        # CLAUDE.md forbids it. Those are listed separately so they are not invisible.
        ready, inflight = [], []
        for f, d in rows:
            if d.get("kb_action", "") not in {"add", "update", "split"}:
                continue
            if d.get("action_status") != "open":
                continue
            (ready if d.get("review_status") == "reviewed" else inflight).append((f, d))
        for f, d in ready:
            print(f"{f.relative_to(REPO)}  {d.get('kb_action')}  {norm_paths(d.get('kb_files',''))}")
        if inflight:
            print(f"\n-- not actionable yet: {len(inflight)} transcript(s) have an open action "
                  f"but review_status is not 'reviewed' --", file=sys.stderr)
            for f, d in inflight:
                print(f"   {f.relative_to(REPO)}  ({d.get('review_status')}, "
                      f"reviewer={d.get('reviewer') or 'unset'})", file=sys.stderr)
        return

    # dashboard
    tot = len(rows)
    st = lambda v: sum(1 for _, d in rows if d.get("review_status") == v)
    excl, pend, rev, push = st("excluded"), st("pending"), st("reviewed"), st("pushed")
    inscope = tot - excl
    closed = push
    print(f"Transcripts: {tot}   (excluded {excl}, in scope {inscope})")
    print(f"  lifecycle:  pending {pend}  ->  reviewed {rev}  ->  pushed {push}"
          f"   ({100*closed//inscope if inscope else 0}% closed out)")
    if rev:
        print(f"  ** {rev} reviewed and awaiting processing - run --actions **")
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
    openacts = [(f, d) for f, d in rows
                if d.get("kb_action") in {"add", "update", "split"} and d.get("action_status") == "open"]
    print(f"\nopen KB actions: {len(openacts)}")
    for f, d in openacts:
        print(f"  [{d.get('kb_action')}] {d.get('kb_files','(unspecified)')}  <- {f.name}")
    if bad:
        print(f"\n⚠ {len(bad)} file(s) with invalid frontmatter — run --check")

    # INDEX.md
    L = ["# Transcript review index", "",
         f"_Generated by `scripts/review_status.py`. {tot} transcripts: "
         f"{pend} pending, {rev} reviewed, {push} pushed, {excl} excluded._", "",
         "| Transcript | Agent | Date | Ex | Foundry FB | Status | Routing | Answer | Diagnosis | KB action |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for f, d in rows:
        rel = f.relative_to(TDIR).as_posix()
        L.append("| [{}]({}) | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            f.stem, rel, d.get("answered_by", ""), (d.get("date", "") or "")[:10],
            d.get("exchanges", ""), d.get("foundry_feedback", ""),
            d.get("review_status", ""),
            d.get("routing_verdict", "") + ("→" + d["reassign_to"] if d.get("reassign_to") else ""),
            d.get("answer_verdict", ""), d.get("diagnosis", ""),
            (d.get("kb_action", "") or "") + (f" ({d.get('action_status')})" if d.get("kb_action") in {"add","update","split"} else "")))
    (TDIR / "INDEX.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"\nwrote {(TDIR/'INDEX.md').relative_to(REPO)}")


if __name__ == "__main__":
    main()
