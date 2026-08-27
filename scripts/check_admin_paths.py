#!/usr/bin/env python3
"""Assert .github/CODEOWNERS and .github/admin-only-paths.txt describe the same boundary.

Two mechanisms enforce "admins own team-level routing", and they cannot share a file:

  CODEOWNERS              GitHub's format, evaluated server-side at merge. The REAL gate.
  admin-only-paths.txt    regexes, read by CI and the session script. The early warning.

Different syntax, same intent — so they will drift, and the drift is silent in the dangerous
direction: a path dropped from CODEOWNERS stops being gated at merge while CI still says it
is protected, so everything *looks* fine.

This check fails when a path in one is missing from the other. It is a consistency check, not
a policy check: it cannot tell you the boundary is *correct*, only that both files agree.

    python3 scripts/check_admin_paths.py

Exit 0 when they agree, 1 otherwise.
"""
import re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OWNERS = REPO / ".github" / "CODEOWNERS"
PATHS = REPO / ".github" / "admin-only-paths.txt"


def regexes():
    out = []
    for line in PATHS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def codeowner_patterns():
    """CODEOWNERS entries, as the leading path pattern of each rule line."""
    out = []
    for line in OWNERS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1].startswith("@"):
            out.append(parts[0])
    return out


# A regex from admin-only-paths.txt, and the CODEOWNERS pattern that should cover it.
# Written out rather than derived: converting between the two syntaxes automatically would be
# its own source of bugs, and the list is short enough to read.
EXPECTED = {
    r"^README\.md$":                     "/README.md",
    r"^team-config/":                    "/team-config/",
    r"^Knowledge-[^/]+/_START_HERE\.md$": "/Knowledge-*/_START_HERE.md",
    r"^CLAUDE\.md$":                     "/CLAUDE.md",
    r"^contributor-initial-prompt\.md$": "/contributor-initial-prompt.md",
    r"^contributor-update-prompt\.md$":  "/contributor-update-prompt.md",
    r"^contributor-prompting-guide\.md$": "/contributor-prompting-guide.md",
    r"^RUNNING-WITHOUT-AI\.md$":          "/RUNNING-WITHOUT-AI.md",
    r"^transcripts/README\.md$":         "/transcripts/README.md",
    r"^transcripts/ONBOARDING\.md$":     "/transcripts/ONBOARDING.md",
    r"^scripts/":                        "/scripts/",
    # One regex, two CODEOWNERS lines - CODEOWNERS has no alternation, so the pair is
    # listed and only the first is asserted here. Both are present in the file.
    r"^Start-reviewing\.(command|bat)$": "/Start-reviewing.command",
    r"^templates/":                      "/templates/",
    r"^\.github/":                       "/.github/",
    r"^\.gitignore$":                     "/.gitignore",
    r"^contributors\.json$":             "/contributors.json",
    r"^agent-owners\.json$":             "/agent-owners.json",
}


def main():
    got = set(regexes())
    owners = set(codeowner_patterns())
    problems = []

    for rx in sorted(got):
        want = EXPECTED.get(rx)
        if want is None:
            problems.append(f"admin-only-paths.txt has {rx!r} with no mapping in "
                            f"check_admin_paths.py EXPECTED — add it, and add the matching "
                            f"CODEOWNERS entry")
        elif want not in owners:
            problems.append(f"{rx!r} is admin-only but CODEOWNERS has no {want!r} entry — "
                            f"the merge gate does not actually protect it")

    for rx, want in EXPECTED.items():
        if rx not in got:
            problems.append(f"EXPECTED maps {rx!r} but admin-only-paths.txt no longer lists "
                            f"it — CI and the session script have stopped warning about it")

    for p in problems:
        print(f"  FAIL  {p}")
    if problems:
        print(f"\n{len(problems)} inconsistency(ies) between CODEOWNERS and "
              f"admin-only-paths.txt.")
        return 1
    print(f"CODEOWNERS and admin-only-paths.txt agree on all {len(got)} admin-only path(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
