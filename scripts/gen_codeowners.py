#!/usr/bin/env python3
"""Generate .github/CODEOWNERS from agent-owners.json. Admins only.

    python3 scripts/gen_codeowners.py --check    # exits 1 if CODEOWNERS has drifted
    python3 scripts/gen_codeowners.py            # rewrite it

WHY GENERATED, NOT HAND-MAINTAINED
----------------------------------
Ownership is recorded in `agent-owners.json`. Before this file existed, CODEOWNERS said
something different: every `Knowledge-*/` folder was owned by the WHOLE contributors team, so
any contributor was an approving owner for every corpus. The intent ("each contributor owns
their agent's folder") lived in one file and the enforcement in another, and nothing kept them
honest.

Two sources of truth for one fact is the bug. So CODEOWNERS is now derived, and `--check` runs
in CI: change the owner of an agent in one place and the permission follows, or the build
fails.

WHAT THE RULES MEAN
-------------------
CODEOWNERS is LAST-MATCH-WINS, which is why the order below is not cosmetic:

  1. `*` -> admins. The floor: anything not named later needs an admin.
  2. Per-corpus lines -> that corpus's owner, plus every admin.
  3. Admin-only paths, listed AFTER the corpus lines so they win where they overlap -
     `Knowledge-*/_START_HERE.md` sits inside a folder a contributor owns, and must still be
     admin-owned.

Combined with branch protection (a PR is required, and a code owner must approve), the effect
is what was asked for: a contributor can EDIT any file and open a request for it, but only the
owner of that corpus - or an admin - can approve it through. Feedback stays open to everyone;
merging someone else's corpus does not.

WHAT THIS CANNOT DO
-------------------
CODEOWNERS gates APPROVAL, not the edit. Nothing stops a contributor committing to a folder
they do not own and opening a request; it just cannot merge without the owner. That is the
right shape - it is how they give feedback on another agent - but it means CODEOWNERS is not a
lock, and describing it as one would be wrong. `scripts/check_folder_ownership.py` reports the
case explicitly in CI so a reviewer sees it rather than discovering it in the approval flow.
"""
import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
OWNERS = REPO / "agent-owners.json"
CODEOWNERS = REPO / ".github" / "CODEOWNERS"
ADMIN_PATHS = REPO / ".github" / "admin-only-paths.txt"

ORG = "tyler-technologies"
ADMIN_TEAM = f"@{ORG}/onetyler-tcp-pm-admins"

# agent slug -> corpus folder. The slugs match agent-owners.json and the review UI's
# DELEGATE_SLUG, so one name means one thing across the repo.
AGENT_FOLDER = {
    "ops-center": "Knowledge-OpsCenter",
    "bp-general": "Knowledge-BP-General",
    "sac": "Knowledge-SupportAccessCenter",
    "identity": "Knowledge-TylerIdentity",
    "aligned-releases": "Knowledge-AlignedReleases",
    "status-page": "Knowledge-StatusPageAndSLA",
}

# Knowledge-Shared is NOT in the table above, deliberately. Its files upload to ALL five
# collections, so a change there alters what every agent says - the blast radius of a routing
# change with none of the visibility. It stays admin-owned.
SHARED_FOLDER = "Knowledge-Shared"


def admin_only_paths():
    """The admin-only globs, from the single source that already defines them.

    Read as regexes and translated to CODEOWNERS globs. Only the shapes this repo actually
    uses are handled, and anything unrecognised is reported rather than silently dropped -
    a path that quietly fails to translate would become contributor-writable.
    """
    out, unknown = [], []
    for raw in ADMIN_PATHS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        rx = line
        if not rx.startswith("^"):
            unknown.append(raw)
            continue
        rx = rx[1:]
        if rx.endswith("$"):
            rx = rx[:-1]
        rx = rx.replace(r"\.", ".")
        if rx == "Knowledge-[^/]+/_START_HERE.md":
            out.append("/Knowledge-*/_START_HERE.md")
        elif rx == "Start-reviewing.(command|bat)":
            out.append("/Start-reviewing.command")
            out.append("/Start-reviewing.bat")
        elif "[" not in rx and "(" not in rx and "|" not in rx:
            out.append("/" + rx)
        else:
            unknown.append(raw)
    return out, unknown


def build():
    data = json.loads(OWNERS.read_text(encoding="utf-8"))
    default = data.get("default_owner") or ""
    by_agent = data.get("by_agent") or {}
    admin_globs, unknown = admin_only_paths()

    L = []
    A = L.append
    A("# GENERATED FILE - do not hand-edit.")
    A("#   python3 scripts/gen_codeowners.py          rewrite")
    A("#   python3 scripts/gen_codeowners.py --check  CI: fails if this has drifted")
    A("#")
    A("# Ownership comes from agent-owners.json. Editing this file by hand does not change who")
    A("# owns an agent - it just makes the two disagree until CI says so.")
    A("#")
    A("# LAST MATCH WINS in CODEOWNERS, so the order here is load-bearing:")
    A("#   1. `*` is the floor: anything unnamed needs an admin.")
    A("#   2. each corpus goes to its owner AND the admins.")
    A("#   3. admin-only paths come LAST so they win inside a folder a contributor owns.")
    A("")
    A(f"*                               {ADMIN_TEAM}")
    A("")
    A("# ---- one corpus per owner -------------------------------------------------------------")
    A("# A contributor may edit any file and open a change request for it; only the owner of")
    A("# that corpus, or an admin, can approve it through. Feedback stays open to everyone.")
    for slug in sorted(AGENT_FOLDER):
        folder = AGENT_FOLDER[slug]
        if not (REPO / folder).is_dir():
            continue
        owner = by_agent.get(slug) or default
        owners = [f"@{owner}"] if owner else []
        if ADMIN_TEAM not in owners:
            owners.append(ADMIN_TEAM)
        A(f"/{folder}/".ljust(32) + " ".join(owners))
    A("")
    A("# Shared corpus: uploads to ALL five collections, so a change here alters what every")
    A("# agent says. Admin-owned for the same reason routing is.")
    A(f"/{SHARED_FOLDER}/".ljust(32) + ADMIN_TEAM)
    A("")
    A("# ---- transcripts ---------------------------------------------------------------------")
    A("# Reviews are the contributors' own work, and any of them may review any transcript -")
    A("# the per-agent split is about corpus CONTENT, not about who may record a verdict.")
    A("/transcripts/".ljust(32) + f"@{ORG}/onetyler-tcp-pm-contributors {ADMIN_TEAM}")
    A("")
    A("# ---- admin-only, LAST so these win --------------------------------------------------")
    for g in admin_globs:
        A(g.ljust(32) + ADMIN_TEAM)
    return "\n".join(L) + "\n", unknown


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    text, unknown = build()
    if unknown:
        print("FAIL: admin-only-paths.txt has entries this generator cannot translate to a\n"
              "      CODEOWNERS glob. Left out, they would become contributor-writable:",
              file=sys.stderr)
        for u in unknown:
            print(f"        {u}", file=sys.stderr)
        return 1

    current = CODEOWNERS.read_text(encoding="utf-8") if CODEOWNERS.exists() else ""
    if a.check:
        if current != text:
            print("FAIL: .github/CODEOWNERS has drifted from agent-owners.json.\n"
                  "      Run: python3 scripts/gen_codeowners.py", file=sys.stderr)
            return 1
        print("CODEOWNERS matches agent-owners.json.")
        return 0

    if current == text:
        print("CODEOWNERS already up to date.")
        return 0
    CODEOWNERS.write_text(text, encoding="utf-8")
    print(f"Wrote .github/CODEOWNERS ({len(text.splitlines())} lines).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
