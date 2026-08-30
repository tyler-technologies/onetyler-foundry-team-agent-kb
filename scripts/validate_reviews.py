#!/usr/bin/env python3
"""
Guard against two people first-reviewing the same transcript in parallel.

Two reviewers can each pick up a `pending` transcript, review it, and open a PR. Both
diffs apply cleanly — git sees no conflict, because each branch changed the file relative
to a base where it was still `pending`. Whoever merges second silently overwrites the
first reviewer's verdict, and neither of them ever finds out.

This check makes that collision loud. For every transcript the PR touches it compares the
review state on the base branch with the state in the PR:

  base pending   -> PR reviewed,  round 1     first review           OK
  base pending   -> PR suggested, round 1     first suggestion       OK
  base suggested -> PR reviewed,  same round  owner accepted it      OK
  base reviewed  -> PR pushed,    same round  processing completed   OK
  base reviewed  -> PR reviewed,  round n+1   deliberate re-review    OK
  base reviewed  -> PR reviewed,  same round  COLLISION               FAIL
  base excluded  -> PR reviewed,  same round  COLLISION               FAIL
  base suggested -> PR suggested, same round  COLLISION               FAIL

`suggested` is protected for the same reason the finished states are. A suggestion is real
work — a colleague's ideal response and proposed fix, handed to the area owner — and it is NOT
covered by the reviewer/verdict states. When it was left out of this check, a suggestion that
had merged to the base branch read as never-looked-at, so the next person to review that
transcript from a stale base overwrote it and CI called it a clean first review.

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
DONE = {"reviewed", "pushed", "excluded"}
# States that represent work somebody has actually done, and which a later PR must therefore
# not silently replace. `suggested` is not a verdict, but it is not nothing either.
PROTECTED = DONE | {"suggested"}


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


_MB = {}


def merge_base(base):
    """The commit this branch was cut from — i.e. the newest state of `base` the author
    demonstrably had. Anything that landed on `base` after this, they never saw."""
    if base not in _MB:
        rc, out = git("merge-base", base, "HEAD")
        _MB[base] = out.strip() if rc == 0 and out.strip() else None
    return _MB[base]


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
    # Identify transcripts by content, not filename — a doc added to this folder must not
    # be mistaken for one. Files deleted in the PR no longer exist, so fall back to the
    # path shape for those.
    def looks_like_transcript(rel):
        f = REPO / rel
        if f.is_file():
            head = f.read_text(encoding="utf-8", errors="replace")[:1500]
            return head.startswith("---") and "conversation_id:" in head
        return "/" in rel[len(TDIR):] or rel.count("/") >= 2
    changed = [l for l in out.splitlines() if l.endswith(".md") and looks_like_transcript(l)]
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

        # Who this PR credits for the state it is claiming. `suggested` is attributed to
        # reviewer, always - it is whoever did the reviewing, including for a suggestion.
        def actor(fm, status):
            # `suggested_by` was the old field for this. It was removed once `reviewer` became
            # "always the current person", which made it redundant. Still read as a fallback so
            # a transcript written before the change still validates.
            return fm.get("reviewer") or fm.get("suggested_by")

        h_actor = actor(head, h_status)
        need = "reviewer"

        base_txt = at_rev(a.base, path)
        if base_txt is None:                             # brand-new transcript file
            if h_status in PROTECTED and not h_actor:
                problems.append((path, f"{h_status} but no {need} set"))
            continue

        base = fm_of(base_txt)
        b_status = base.get("review_status", "pending") or "pending"
        b_round = int(base.get("review_round") or 1)
        b_actor = actor(base, b_status)

        if h_status not in PROTECTED:
            continue                                     # not claiming any state

        if not h_actor:
            problems.append((path, f"{h_status} but no {need} set"))
            continue

        if b_status not in PROTECTED:
            firsts.append((path, h_actor, h_status))
            continue

        # UNCHANGED VERDICT = NOT A COLLISION. If the status, the actor and the round are all
        # identical to the base, this PR is not claiming anything: the file was touched for some
        # other reason - a frontmatter key renamed, a `notes` line appended, a reformat.
        #
        # Without this, any mechanical edit across the transcripts reads as "everyone re-reviewed
        # everything". Measured 2026-08-28: renaming one frontmatter field failed 20 files at
        # once with "COLLISION - already pushed by X (round 1); this PR sets pushed by X at round
        # 1", which is self-evidently not two people disagreeing - it is the same verdict, by the
        # same person, at the same round.
        #
        # A real collision still fails: base `reviewed by A`, head `reviewed by B` at the same
        # round differs in actor and is caught below, which is the case this check exists for.
        if (h_status, h_actor, h_round) == (b_status, b_actor, b_round):
            continue

        # base already carries work — only a declared advance or re-review is allowed.
        # reviewed -> pushed at the same round is the normal close-out, not a collision.
        if b_status == "reviewed" and h_status == "pushed" and h_round == b_round:
            firsts.append((path, h_actor, "pushed (close-out)"))
        # suggested -> a real verdict at the same round is EITHER the handoff completing (the
        # owner accepted or overrode the suggestion) OR the exact clobber this script exists
        # to catch. The frontmatter is identical in both cases; what separates them is whether
        # the reviewer had actually seen the suggestion. So ask git: was it already present in
        # the commit the PR branched from? If yes they superseded it deliberately. If it
        # reached the base branch only after they branched, they never saw it.
        elif b_status == "suggested" and h_status in DONE and h_round == b_round:
            mb_txt = at_rev(merge_base(a.base), path) if merge_base(a.base) else None
            if mb_txt is not None and (fm_of(mb_txt).get("review_status") or "") == "suggested":
                firsts.append((path, h_actor,
                               f"{h_status} (accepted "
                               f"{base.get('reviewer') or base.get('suggested_by') or '?'}'s "
                               f"suggestion)"))
            else:
                problems.append((path, (
                    f"COLLISION — {base.get('reviewer') or base.get('suggested_by') or '?'} "
                    f"suggested changes to this on "
                    f"{a.base} AFTER this branch was cut, so this PR was written without seeing "
                    f"them and merging it would discard them. Pull {a.base}, read the "
                    f"suggestion and the proposed fix, then re-record your verdict on top.")))
        elif h_round > b_round:
            rerevs.append((path, h_actor, b_round, h_round))
        else:
            if b_status == h_status == "suggested":
                kind = "Two independent suggestions on the same transcript"
            elif h_status == "suggested":
                kind = (f"This PR suggests changes to something already {b_status}. "
                        f"Re-opening a decided transcript is a re-review")
            else:
                kind = "Two first reviews of the same transcript"
            problems.append((path, (
                f"COLLISION — already {b_status} by {actor(base, b_status) or '?'} "
                f"on {a.base} (round {b_round}); this PR sets {h_status} by "
                f"{h_actor} at round {h_round}. {kind}. Pull {a.base}, read what they "
                f"concluded, and if you still disagree use Re-review to raise the round.")))

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
