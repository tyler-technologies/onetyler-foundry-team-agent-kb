#!/usr/bin/env python3
"""
Assert try_autorebase_dirty() against a real, isolated git remote - never the actual
GitHub repo. Two things must both hold:

1. An INDEX.md-only conflict is resolved automatically: the fake remote's branch ends up
   rebased onto its main, with INDEX.md regenerated, and nothing else changed.
2. A conflict that ALSO touches a real content file is refused cleanly: the fake remote's
   branch is left exactly as it was - no partial rebase, no force-push - and the function
   says why.

The fixture is a bare clone of THIS repo's own current state (real transcripts, real
scripts, so scripts/review_status.py has what it needs to run) with two branches built
inside it. The conflicts are hand-crafted (both sides edit the same line of INDEX.md
directly) rather than relying on review_status.py's aggregate counts happening to collide -
deterministic, and it is the mechanism under test (worktree rebase, conflict-file
detection, regenerate, continue, force-push) that matters here, not realistic content.
`review_server.REPO` is monkeypatched to a temp working clone of the fixture for the
duration of each case, so every git() call the function under test makes lands on the
fixture, never on origin.

Run with no arguments. Exits non-zero and prints every offending line on failure.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def run(cwd, *args, check=True):
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {cwd}:\n{r.stdout}\n{r.stderr}")
    return r.returncode, (r.stdout + r.stderr).strip()


def build_fixture(tmp):
    """A bare 'origin' seeded from this repo's real current state, plus a working clone to
    build branches in. Returns (origin_bare, seed_clone)."""
    tmp.mkdir(parents=True, exist_ok=True)
    origin = tmp / "origin.git"
    run(tmp, "clone", "--bare", str(REPO), str(origin))
    seed = tmp / "seed"
    run(tmp, "clone", str(origin), str(seed))
    run(seed, "config", "user.email", "test@example.com")
    run(seed, "config", "user.name", "check_pr_autorebase")
    return origin, seed


def any_real_transcript(clone):
    for f in sorted((clone / "transcripts").rglob("*.md")):
        if f.name not in ("INDEX.md", "README.md", "ONBOARDING.md"):
            return f
    raise RuntimeError("no transcript file found in fixture")


def overwrite_first_line(path, text):
    lines = path.read_text().splitlines(keepends=True)
    lines[0] = text + "\n"
    path.write_text("".join(lines))


def case_index_only_conflict(tmp, failures):
    print("--- case 1: INDEX.md-only conflict, should resolve automatically ---")
    origin, seed = build_fixture(tmp / "case1")
    index = seed / "transcripts" / "INDEX.md"

    run(seed, "switch", "-c", "test/pr-branch")
    overwrite_first_line(index, "# BRANCH VERSION - deliberately conflicting")
    run(seed, "add", "-A")
    run(seed, "commit", "-m", "test: branch edits INDEX.md's first line")
    run(seed, "push", "origin", "test/pr-branch")

    run(seed, "switch", "main")
    overwrite_first_line(index, "# MAIN VERSION - deliberately conflicting")
    run(seed, "add", "-A")
    run(seed, "commit", "-m", "test: main edits the SAME line differently")
    run(seed, "push", "origin", "main")

    work = tmp / "case1-work"
    run(tmp / "case1", "clone", str(origin), str(work))
    run(work, "config", "user.email", "test@example.com")
    run(work, "config", "user.name", "check_pr_autorebase")

    import review_server as rs
    old_repo = rs.REPO
    rs.REPO = work
    try:
        ok, msg = rs.try_autorebase_dirty("test/pr-branch")
    finally:
        rs.REPO = old_repo

    if not ok:
        failures.append(f"case 1: expected success, got failure: {msg}")
        return
    print(f"    function reported: {msg}")

    _, remote_tip = run(work, "ls-remote", str(origin), "test/pr-branch")
    remote_tip = remote_tip.split()[0] if remote_tip else ""
    _, remote_main = run(work, "rev-parse", "origin/main")
    rc, _ = run(work, "merge-base", "--is-ancestor", remote_main.strip(), remote_tip,
               check=False)
    if rc != 0:
        failures.append("case 1: rebased branch on the remote is not a descendant of main - "
                        "not actually rebased")

    check = subprocess.run(["git", "show", f"{remote_tip}:transcripts/INDEX.md"],
                           cwd=str(work), capture_output=True, text=True)
    first_line = check.stdout.splitlines()[0] if check.stdout else ""
    if "BRANCH VERSION" in first_line or "MAIN VERSION" in first_line:
        failures.append(f"case 1: INDEX.md was not regenerated - hand-edited line survived: "
                        f"{first_line!r}")
    print(f"    ok: regenerated INDEX.md first line is now: {first_line!r}")


def case_real_content_conflict(tmp, failures):
    print("--- case 2: real conflict outside INDEX.md, should refuse cleanly ---")
    origin, seed = build_fixture(tmp / "case2")
    index = seed / "transcripts" / "INDEX.md"
    t = any_real_transcript(seed)
    orig_t = t.read_text()

    run(seed, "switch", "-c", "test/pr-branch")
    overwrite_first_line(index, "# BRANCH VERSION - deliberately conflicting")
    t.write_text(orig_t + "\nBRANCH-ONLY LINE\n")
    run(seed, "add", "-A")
    run(seed, "commit", "-m", "test: branch touches INDEX.md AND a real transcript")
    run(seed, "push", "origin", "test/pr-branch")
    before_tip = run(seed, "rev-parse", "test/pr-branch")[1]

    run(seed, "switch", "main")
    overwrite_first_line(index, "# MAIN VERSION - deliberately conflicting")
    t.write_text(orig_t + "\nMAIN-ONLY LINE\n")
    run(seed, "add", "-A")
    run(seed, "commit", "-m", "test: main touches INDEX.md AND the SAME transcript")
    run(seed, "push", "origin", "main")

    work = tmp / "case2-work"
    run(tmp / "case2", "clone", str(origin), str(work))
    run(work, "config", "user.email", "test@example.com")
    run(work, "config", "user.name", "check_pr_autorebase")

    import review_server as rs
    old_repo = rs.REPO
    rs.REPO = work
    try:
        ok, msg = rs.try_autorebase_dirty("test/pr-branch")
    finally:
        rs.REPO = old_repo

    if ok:
        failures.append(f"case 2: expected refusal, got success: {msg}")
        return
    print(f"    function reported: {msg.splitlines()[0]}")
    if not any(k in msg.lower() for k in ("human", "conflict")):
        failures.append(f"case 2: refusal message doesn't explain why: {msg}")
    if t.name not in msg:
        failures.append(f"case 2: refusal message doesn't name the real offending file "
                        f"({t.name}): {msg}")

    _, remote_tip = run(work, "ls-remote", str(origin), "test/pr-branch")
    remote_tip = remote_tip.split()[0] if remote_tip else ""
    if remote_tip != before_tip:
        failures.append("case 2: the remote branch CHANGED despite refusing - "
                        f"was {before_tip}, now {remote_tip}. A refusal must leave it alone.")
    print("    ok: remote branch untouched")


def main():
    sys.path.insert(0, str(REPO / "scripts"))
    failures = []
    with tempfile.TemporaryDirectory(prefix="fkb-autorebase-check-") as tmpdir:
        tmp = Path(tmpdir)
        case_index_only_conflict(tmp, failures)
        case_real_content_conflict(tmp, failures)

    if failures:
        print("\nFAILED:")
        for f in failures:
            print(" ", f)
        return 1
    print("\nAll PR auto-rebase checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
