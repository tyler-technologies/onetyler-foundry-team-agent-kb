#!/usr/bin/env python3
"""Attribute the current Blueprint edits to one transcript.

Each transcript marked `bp_updates: yes` gets its OWN Blueprint change request, so the flow has
to know which Blueprint edits belong to which transcript. A working tree cannot say that - it is
one flat pile of edits - so the attribution is made explicitly, here, at the moment the edits are
made.

USE IT ONE TRANSCRIPT AT A TIME:

    # ... make the Blueprint edits for transcript A ...
    python3 scripts/bp_stage.py --transcript transcripts/bp-general/2026-08-28--5f52f2b7.md
    # ... the Blueprint tree is now clean; make the edits for transcript B ...
    python3 scripts/bp_stage.py --transcript transcripts/team/2026-08-27--6498f4a8.md

Staging captures everything Blueprint has against `master` right now and then resets that
checkout, which is what stops the next capture re-including the previous one. So staging BEFORE
starting the next transcript is not a tidiness rule - it is the only thing keeping the patches
apart.

    --list      what is staged for whom
    --drop REL  drop one transcript's staged Blueprint changes (also closes its request)

Nothing here touches Foundry, and nothing is pushed: `--transcript` only writes a patch file
under `.bp-stage/`. The requests are opened later, per transcript, after the eval is approved.
"""
import argparse
import importlib.util
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent


def load_server():
    """Reuse review_server's Blueprint helpers rather than reimplementing them.

    Two implementations of "which Blueprint files belong to this transcript" would eventually
    disagree, and the one the UI showed would be the one nobody had tested.
    """
    spec = importlib.util.spec_from_file_location(
        "review_server", REPO / "scripts" / "review_server.py")
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(REPO / "scripts"))
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--transcript", metavar="REL",
                   help="repo-relative transcript path to attribute the current edits to")
    g.add_argument("--list", action="store_true", help="show what is staged")
    g.add_argument("--drop", metavar="REL", help="drop one transcript's staged changes")
    a = ap.parse_args()
    rs = load_server()

    if a.list:
        staged = rs.bp_staged()
        if staged:
            for rel, files in staged.items():
                print(f"{rel}")
                for f in files:
                    print(f"    {f}")
        else:
            print("Nothing staged for Blueprint.")
        # THE MISMATCH THAT MATTERS, and it must be reported even when nothing is staged - which
        # is precisely the case it is most likely to arise in. An early return on the empty case
        # would silence the warning exactly when every marked transcript is missing its edits.
        missing = [r for r in rs.bp_batch() if r not in staged]
        if missing:
            print("\nMarked BP updates but NOTHING staged — these will be refused on send:")
            for r in missing:
                print(f"    {r}")
            print("  Make the Blueprint edits, then:")
            for r in missing:
                print(f"    python3 scripts/bp_stage.py --transcript {r}")
        return 0

    if a.drop:
        ok, msg = rs.bp_unstage(a.drop)
        print(msg)
        return 0 if ok else 1

    rel = a.transcript.strip()
    if not (REPO / rel).is_file():
        print(f"No such transcript: {rel}", file=sys.stderr)
        return 1
    fm, _ = rs.parse(REPO / rel)
    if (fm or {}).get("bp_updates", "").strip().lower() not in ("yes", "true", "1"):
        # A warning, not a refusal: the reviewer may be about to tick the box, and refusing here
        # would send someone to the form and back for no reason.
        print(f"note: {rel} does not have BP updates ticked. Staging anyway, but the request "
              "will not be opened until it is.")
    ok, msg = rs.bp_stage_add(rel)
    print(msg)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
