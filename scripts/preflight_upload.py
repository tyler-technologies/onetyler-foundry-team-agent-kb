#!/usr/bin/env python3
"""Refuse to upload a knowledge file to Foundry unless that exact content is on `main`.

WHY THIS EXISTS
---------------
The repo is the source of truth for every Foundry collection (CLAUDE.md hard rule 1). That
holds only if Foundry never receives content `main` has not accepted. Break it and the
failure is quiet and nasty:

  1. You upload from an unmerged branch. Live agents now answer from it.
  2. The PR is rejected, or just changed during review. `main` never gets that content.
  3. Someone runs the drift check against `main`, sees drift, and "fixes" it by
     re-uploading main's version — silently reverting the live agents.

Nobody in that sequence does anything wrong, and the agent's behaviour changes twice.

It has already happened once, on 2026-08-25: an upload went out at 22:32 UTC and the PR
carrying it merged at 05:02 UTC the next day — a 6.5-hour window where Foundry was ahead of
`main`. The process said "open a PR, then upload", which was followed to the letter and still
produced the gap, because opening a PR is not the same as landing it.

WHAT IT CHECKS
--------------
For each file: the bytes on disk are IDENTICAL to the bytes at `origin/main`. That is the
real invariant, and it is stricter than "am I on a merged branch" — you can sit on a merged
branch with uncommitted edits, and those edits are not approved either.

    python3 scripts/preflight_upload.py Knowledge-OpsCenter/FAQ-OpsCenter.md ...
    python3 scripts/preflight_upload.py --all-changed-vs <collection-dir>

Exit 0 = safe to upload. Exit 1 = do not upload; the message says what to do instead.

This is a REPO check, not a Foundry one. It says nothing about whether the upload will
succeed or whether the content is any good — verify retrieval separately afterwards.
"""
import argparse, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE = "origin/main"


def git(*args):
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True)
    return r.returncode, r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*", help="repo-relative paths intended for upload")
    ap.add_argument("--no-fetch", action="store_true",
                    help="skip the git fetch (offline; comparison may be against a stale base)")
    a = ap.parse_args()

    if not a.files:
        return ap.error("name the files you intend to upload")

    if not a.no_fetch:
        # Without this, a stale origin/main can make an unmerged file look approved.
        rc, _ = git("fetch", "--quiet", "origin", "main")
        if rc != 0:
            print("warning: could not fetch origin/main — comparing against a possibly stale "
                  "base. Re-run with network access before trusting a PASS.", file=sys.stderr)

    rc, _ = git("rev-parse", "--verify", BASE)
    if rc != 0:
        print(f"REFUSE: {BASE} not found — cannot prove anything is approved.")
        return 1

    ok, bad = [], []
    for rel in a.files:
        rel = rel.lstrip("./")
        # Tolerate a path pasted with the repo name in front, as kb_files often is.
        if rel.startswith(REPO.name + "/"):
            rel = rel[len(REPO.name) + 1:]
        local = REPO / rel
        if not local.is_file():
            bad.append((rel, "does not exist locally"))
            continue
        rc, on_main = git("show", f"{BASE}:{rel}")
        if rc != 0:
            bad.append((rel, f"does not exist on {BASE} — it is a NEW file that has not been "
                             f"merged yet"))
            continue
        if local.read_bytes() != on_main:
            bad.append((rel, f"differs from {BASE} — the version you are about to upload is "
                             f"not the approved one"))
            continue
        ok.append(rel)

    for rel in ok:
        print(f"  ok       matches {BASE}   {rel}")
    for rel, why in bad:
        print(f"  REFUSE   {rel}\n           {why}")

    if bad:
        print(f"\n{len(bad)} file(s) not safe to upload. Land the change first:\n"
              f"  1. Commit and push it, open a PR, get it reviewed.\n"
              f"  2. MERGE the PR to main — opening it is not enough.\n"
              f"  3. git pull, re-run this check, then upload.\n"
              f"\nUploading now would put content in front of live agents that main has not\n"
              f"accepted, and the next drift check would try to undo it.")
        return 1

    print(f"\nAll {len(ok)} file(s) are byte-identical to {BASE} — safe to upload.\n"
          f"After uploading: verify by RETRIEVAL (not ingestionStatus), then mark_pushed.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
