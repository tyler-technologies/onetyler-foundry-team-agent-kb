#!/usr/bin/env python3
"""
Close out reviewed transcripts: step (g) of the review process.

Moves `review_status: reviewed` -> `pushed`, meaning "processed, and any resulting change is
live in Foundry". This is the step that keeps the queue honest — without it, `reviewed` grows
forever and there is no way to see what is still owed.

Only run this AFTER the corresponding change is actually deployed. `pushed` is a claim about
Foundry, not about the repo.

A transcript reviewed with `kb_action: none` still becomes `pushed`: nothing needed
deploying, so it is closed out. `action_status` records which of those two happened —
`applied` for a real change, `none-needed` when there was nothing to do.

    python3 scripts/mark_pushed.py --all                       # every reviewed transcript
    python3 scripts/mark_pushed.py transcripts/team/x.md ...    # specific ones
    python3 scripts/mark_pushed.py --all --dry-run
    python3 scripts/mark_pushed.py --all --note "uploaded to OT-OpsCenter, verified"

Re-reviewing something already `pushed` is fine — use the Re-review button, which raises
`review_round` and sets it back to `reviewed`.
"""
import argparse, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TDIR = REPO / "transcripts"


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

def setfield(text, key, value):
    pat = re.compile(rf"^{re.escape(key)}:.*$", re.M)
    return pat.sub(f"{key}: {value}", text, count=1) if pat.search(text) else text


def fm_get(text, key):
    m = re.search(rf"^{re.escape(key)}: *(.*)$", text, re.M)
    return (m.group(1).strip() if m else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", help="transcript files; omit with --all")
    ap.add_argument("--all", action="store_true", help="every reviewed transcript")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--note", default="", help="appended to notes, e.g. what was deployed")
    a = ap.parse_args()

    if a.all:
        targets = [f for f in sorted(TDIR.rglob("*.md")) if is_transcript(f)]
    elif a.paths:
        targets = [Path(p) if Path(p).is_absolute() else REPO / p for p in a.paths]
    else:
        return ap.error("give paths or --all")

    moved, skipped = [], []
    for f in targets:
        if not f.is_file():
            skipped.append((f, "not found")); continue
        t = f.read_text(encoding="utf-8")
        st = fm_get(t, "review_status")
        if st != "reviewed":
            skipped.append((f, f"review_status={st or 'unset'} (only 'reviewed' is closed out)"))
            continue
        if not fm_get(t, "reviewer"):
            skipped.append((f, "no reviewer set")); continue

        new = setfield(t, "review_status", "pushed")
        # an open action that was never resolved is a bug, not a close-out
        act = fm_get(new, "action_status")
        kb = fm_get(new, "kb_action")
        if act == "open":
            if kb in ("", "none"):
                new = setfield(new, "action_status", "none-needed")
            else:
                skipped.append((f, f"kb_action={kb} but action_status is still 'open' — "
                                   f"apply the change and set 'applied' first"))
                continue
        if a.note:
            cur = fm_get(new, "notes")
            new = setfield(new, "notes", (cur + " | " if cur else "") + a.note)

        if not a.dry_run:
            f.write_text(new, encoding="utf-8")
        moved.append(f)

    for f in moved:
        print(f"  {'would close' if a.dry_run else 'pushed'}   {f.relative_to(REPO)}")
    for f, why in skipped:
        print(f"  skipped  {f.relative_to(REPO) if f.exists() else f}: {why}", file=sys.stderr)
    print(f"\n{len(moved)} closed out, {len(skipped)} skipped")
    if moved and not a.dry_run:
        print("Next: python3 scripts/review_status.py   (refreshes INDEX.md)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
