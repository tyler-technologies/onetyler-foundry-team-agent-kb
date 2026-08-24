#!/usr/bin/env python3
"""
Regenerate contributors.json from the GitHub teams that actually grant repo access.

The reviewer registry and the GitHub teams are the same list of people expressed twice, so
maintaining it by hand guarantees they drift: someone joins the team, the review UI never
offers their name, and they cannot record a review. This makes the teams the source of truth
and the file a generated artifact.

    python3 scripts/sync_contributors.py              # rewrite contributors.json
    python3 scripts/sync_contributors.py --check      # exit 1 if out of sync (CI/pre-PR)
    python3 scripts/sync_contributors.py --dry-run    # show the diff, write nothing

Requires the `gh` CLI authenticated with an account that can read org team membership.
A team that does not exist yet is skipped with a warning rather than treated as empty —
otherwise a transient 404 would silently wipe every reviewer from the file.
"""
import argparse, json, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "contributors.json"
ORG = "tyler-technologies"

# Which teams confer what. Order matters: a person on both teams keeps the FIRST role listed.
TEAMS = [
    ("onetyler-tcp-pm-admins", "maintainer"),
    ("onetyler-tcp-pm-contributors", "reviewer"),
]

COMMENT = [
    "GENERATED FILE - do not hand-edit. Regenerate with:",
    "    python3 scripts/sync_contributors.py",
    "",
    "Authorized transcript reviewers, derived from GitHub team membership. The `reviewer`",
    "field on every transcript must be one of the `github` values below - the review UI",
    "offers only these, and scripts/review_status.py --check fails on anything else.",
    "",
    "Source of truth is the teams, not this file:",
    "    onetyler-tcp-pm-admins        -> admin on the repo; role 'maintainer'.",
    "                                     NOTE: admins bypass the PR review gate.",
    "    onetyler-tcp-pm-contributors  -> write on the repo; role 'reviewer'.",
    "                                     Their PRs require a code-owner approval.",
    "",
    "To add a reviewer: add them to onetyler-tcp-pm-contributors, then re-run the sync and",
    "commit the result. Do not add an entry by hand - it would be overwritten, and it would",
    "not give them repo access anyway.",
]


def gh(path):
    """Returns parsed JSON, or None if the resource does not exist."""
    r = subprocess.run(["gh", "api", "--paginate", path],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    try:
        # --paginate can emit several concatenated arrays; normalise to one list
        txt = r.stdout.strip()
        if txt.startswith("[") and "][" in txt:
            txt = "[" + txt.replace("][", ",") + "]"
            txt = txt.replace("[[", "[").replace("]]", "]")
        return json.loads(txt)
    except json.JSONDecodeError:
        return None


def collect():
    people, missing = {}, []
    for team, role in TEAMS:
        members = gh(f"orgs/{ORG}/teams/{team}/members")
        if members is None:
            missing.append(team)
            continue
        for m in members:
            login = m.get("login")
            if not login or login in people:      # first team listed wins the role
                continue
            u = gh(f"users/{login}") or {}
            people[login] = {
                "github": login,
                "name": u.get("name") or login,
                "role": role,
                "team": team,
            }
    return [people[k] for k in sorted(people)], missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if the file is out of sync")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    contributors, missing = collect()

    for t in missing:
        print(f"warning: team '{t}' not found (not created yet, or no permission to read it) "
              f"- skipping rather than dropping its members", file=sys.stderr)

    if not contributors:
        print("ERROR: no members resolved from any team. Refusing to write an empty registry "
              "- that would lock every reviewer out.", file=sys.stderr)
        return 1

    new = {"_comment": COMMENT, "contributors": contributors}
    new_txt = json.dumps(new, indent=2) + "\n"
    old_txt = OUT.read_text(encoding="utf-8") if OUT.exists() else ""

    if a.check:
        if new_txt == old_txt:
            print(f"in sync — {len(contributors)} contributor(s)")
            return 0
        print("OUT OF SYNC with GitHub team membership. Run:\n"
              "    python3 scripts/sync_contributors.py", file=sys.stderr)
        return 1

    for c in contributors:
        print(f"  {c['github']:24} {c['role']:11} {c['name']}  ({c['team']})")
    if new_txt == old_txt:
        print("\nalready in sync — nothing written")
        return 0
    if a.dry_run:
        print("\n--dry-run: would rewrite contributors.json")
        return 0
    OUT.write_text(new_txt, encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(REPO)} — {len(contributors)} contributor(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
