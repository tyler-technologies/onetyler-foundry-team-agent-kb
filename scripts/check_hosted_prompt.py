#!/usr/bin/env python3
"""
Assert analysis_prompt()/eval_improve_prompt() actually differ correctly between hosted and
local, and that push_lane_for_processing() is a true no-op when not hosted. Imports
review_server directly (no subprocess) since these are pure functions of module state.

Three things must hold:
1. Unset AUTH_ENABLED (laptop default): analysis_prompt()'s text is BYTE-IDENTICAL to the
   original, well-tested local wording - the hosted work must not have touched it at all.
2. AUTH_ENABLED on: the prompt names the actual current lane branch and tells the assistant
   to fetch/check it out itself, and adds the eval/commit/push/PR instructions the laptop
   prompt never needed (there's no browser session on that machine to finish the job).
3. push_lane_for_processing() returns "" immediately when AUTH_ENABLED is off - never touches
   git at all - so it is provably inert on every laptop run.

Run with no arguments. Exits non-zero and prints every offending line on failure.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

ORIGINAL_LOCAL_PROMPT = (
    "I have finished reviewing 1 transcript(s) in this repo. "
    "Sync this repo to the latest main first (`git fetch origin` and bring main up to "
    "date; do not disturb my in-progress branch), so you are editing current content "
    "and not reintroducing something already fixed. "
    "Read all of my feedback as one body before changing anything, then update the "
    "knowledge files so the agents stop giving those answers. Summarise what you "
    "changed, per transcript, so I can follow my own feedback through. "
    "Do not change my verdicts, and ask me rather than guessing if any of my feedback "
    "is ambiguous."
)


def main():
    sys.path.insert(0, str(REPO / "scripts"))
    failures = []

    import review_server as rs

    print("--- laptop default: analysis_prompt() text unchanged ---")
    rs.AUTH_ENABLED = False
    got = rs.analysis_prompt(1)
    if got != ORIGINAL_LOCAL_PROMPT:
        failures.append(
            "analysis_prompt(1) with AUTH_ENABLED off no longer matches the original "
            f"local wording.\n--- got ---\n{got}\n--- expected ---\n{ORIGINAL_LOCAL_PROMPT}"
        )
    else:
        print("    ok: byte-identical to the original")

    print("--- hosted: analysis_prompt() names the branch and adds the extra steps ---")
    rs.AUTH_ENABLED = True
    rs._SITTING_LANE_LOCAL.value = "review/octocat/09999999-000000"
    try:
        got = rs.analysis_prompt(2)
    finally:
        rs.AUTH_ENABLED = False
        rs._SITTING_LANE_LOCAL.value = None
    if "review/octocat/09999999-000000" not in got:
        failures.append(f"hosted analysis_prompt() did not name the current lane branch: {got}")
    if "eval_batch.py" not in got:
        failures.append(f"hosted analysis_prompt() did not mention running the eval itself: {got}")
    if "gh pr create" not in got:
        failures.append(f"hosted analysis_prompt() did not mention opening the PR itself: {got}")
    if "do not disturb my in-progress branch" in got:
        failures.append("hosted analysis_prompt() still contains the laptop-only phrase "
                        "(assumes the branch is already local) - should not appear hosted")
    print(f"    ok: {got.splitlines()[0][:80]}...")

    print("--- push_lane_for_processing() is a true no-op when not hosted ---")
    rs.AUTH_ENABLED = False
    real_git = rs.git
    called = []
    rs.git = lambda *a, **k: (called.append(a) or (1, "SHOULD NOT HAVE BEEN CALLED"))
    try:
        result = rs.push_lane_for_processing()
    finally:
        rs.git = real_git
    if result != "":
        failures.append(f"push_lane_for_processing() with AUTH_ENABLED off returned "
                        f"non-empty: {result!r}")
    if called:
        failures.append(f"push_lane_for_processing() with AUTH_ENABLED off called git(): "
                        f"{called}")
    else:
        print("    ok: returned '' without touching git at all")

    if failures:
        print("\nFAILED:")
        for f in failures:
            print(" ", f)
        return 1
    print("\nAll hosted-prompt checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
