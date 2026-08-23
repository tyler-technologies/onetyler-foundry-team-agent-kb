#!/usr/bin/env python3
"""
Guard against two people first-reviewing the same transcript in parallel.

Two reviewers can each pick up a `pending` transcript, review it, and open a PR. Both
diffs apply cleanly — git sees no conflict, because each branch changed the file relative
to a base where it was still `pending`. Whoever merges second silently overwrites the
first reviewer's verdict, and neither of them ever finds out.

This check makes that collision loud. For every transcript the PR touches it compares the
review state on the base branch with the state in the PR:

  base pending  -> PR reviewed, round 1     first review           OK
  base reviewed -> PR reviewed, round n+1   deliberate re-review    OK
  base reviewed -> PR reviewed, same round  COLLISION               FAIL
  base excluded -> PR reviewed, same round  COLLISION               FAIL

A collision means someone else's review of that transcript reached the base branch while
this one was in flight. The fix is not to force it through: update from the base branch,
read what they concluded, and if you still disagree, raise the round with the Re-review
button so both verdicts are on the record.

Re-reviewing is encouraged — it just has to be explicit.

Usage:
    python3 scripts/validate_reviews.py                 # compare against origin/main
    python3 scripts/validate_reviews.py --base main
    python3 scripts/validate_reviews.py --base "$GITHUB_BASE_REF"

Exit 0 clean, 1 on any collision or malformed review.
"""
import argparse, re, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TDIR = "transcripts/"
DONE = {"reviewed", "excluded"}


def git(*args):
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)
    return r.returncode, r.stdout


def fm_of(text):
    m = re.match(r"^---\n(.*?)\n---\n", text or "", re.S)
    if not m:
        return {}
    d = {}
    for line in m.group(1).splitlines():
        line = line.strip()
        if line and not line.startswith("#") and ":" in line:
            k, _, v = line.partition(":")
            d[k.strip()] = v.strip()
    return d


def at_rev(rev, path):
    rc, out = git("show", f"{rev}:{path}")
    return out if rc == 0 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="origin/main")
    a = ap.parse_args()

    rc, _ = git("rev-parse", "--verify", a.base)
    if rc != 0:
        print(f"note: base ref {a.base!r} not found — skipping collision check "
              f"(expected before the remote exists)")
        return 0

    rc, out = git("diff", "--name-only", f"{a.base}...HEAD", "--", TDIR)
    changed = [l for l in out.splitlines()
               if l.endswith(".md") and not l.endswith(("INDEX.md", "README.md"))]
    if not changed:
        print("no transcript changes in this PR")
        return 0

    problems, firsts, rerevs = [], [], []
    for path in changed:
        head_txt = (REPO / path).read_text(encoding="utf-8") if (REPO / path).exists() else at_rev("HEAD", path)
        if head_txt is None:
            continue                                     # deleted in this PR
        head = fm_of(head_txt)
        h_status = head.get("review_status", "pending") or "pending"
        h_round = int(head.get("review_round") or 1)

        base_txt = at_rev(a.base, path)
        if base_txt is None:                             # brand-new transcript file
            if h_status in DONE and not head.get("reviewer"):
                problems.append((path, f"{h_status} but no reviewer set"))
            continue

        base = fm_of(base_txt)
        b_status = base.get("review_status", "pending") or "pending"
        b_round = int(base.get("review_round") or 1)

        if h_status not in DONE:
            continue                                     # not claiming a review

        if not head.get("reviewer"):
            problems.append((path, f"{h_status} but no reviewer set"))
            continue

        if b_status not in DONE:
            firsts.append((path, head.get("reviewer"), h_status))
            continue

        # base already reviewed — only a declared re-review is allowed
        if h_round > b_round:
            rerevs.append((path, head.get("reviewer"), b_round, h_round))
        else:
            problems.append((path, (
                f"COLLISION — already {b_status} by {base.get('reviewer','?')} "
                f"on {a.base} (round {b_round}); this PR sets {h_status} by "
                f"{head.get('reviewer','?')} at round {h_round}. Two first reviews of the "
                f"same transcript. Pull {a.base}, read their verdict, and if you still "
                f"disagree use Re-review to raise the round.")))

    for p, r, s in firsts:
        print(f"  ok       first review   {p}  ({s} by {r})")
    for p, r, b, h in rerevs:
        print(f"  ok       re-review      {p}  (round {b} -> {h} by {r})")
    for p, why in problems:
        print(f"  FAIL     {p}\n           {why}")

    print(f"\n{len(firsts)} first review(s), {len(rerevs)} re-review(s), "
          f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
