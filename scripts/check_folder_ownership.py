#!/usr/bin/env python3
"""Report when a change request touches a corpus its author does not own.

    python3 scripts/check_folder_ownership.py --base origin/main --author <login>

NOT A GATE, AND SAYING SO MATTERS. CODEOWNERS already gates the merge: the corpus owner or an
admin has to approve. This exists because that gate is invisible until someone tries to
approve, and by then the reviewer is deciding about a diff without being told the author was
outside their patch. Surfacing it in CI puts the fact next to the diff.

It exits 0 for a non-owner edit ON PURPOSE. Editing another agent's corpus and opening a
request for it is how a contributor gives feedback on that agent - it is supposed to be
possible. What must not happen is it merging without the owner, and CODEOWNERS handles that.

Exits 1 only for something genuinely wrong: a contributor touching an ADMIN-ONLY path, which
no approval flow should be asked to rescue.
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from owners import load_owners  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from gen_codeowners import AGENT_FOLDER, SHARED_FOLDER          # noqa: E402


def admins():
    try:
        d = json.loads((REPO / "contributors.json").read_text(encoding="utf-8"))
        return {c["github"] for c in d.get("contributors", [])
                if c.get("github") and (c.get("role") == "maintainer"
                                        or "admins" in (c.get("team") or ""))}
    except Exception:                                           # noqa: BLE001
        return set()


def owners_of_folder(folder):
    """Every owner of this corpus. A list, because a corpus may have several.

    Was `owner_of_folder`, returning the raw JSON value - so with a list of owners the caller's
    `author != own` compared a string against a list, which is always true, and BOTH legitimate
    owners were reported as making foreign edits.
    """
    by_agent, default = load_owners()
    for slug, f in AGENT_FOLDER.items():
        if f == folder:
            return by_agent.get(slug) or list(default)
    return []


def admin_only_regexes():
    out = []
    for raw in (REPO / ".github" / "admin-only-paths.txt").read_text().splitlines():
        s = raw.strip()
        if s and not s.startswith("#"):
            out.append(re.compile(s))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--author", default="")
    a = ap.parse_args()

    r = subprocess.run(["git", "diff", "--name-only", f"{a.base}...HEAD"],
                       cwd=REPO, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f"could not diff against {a.base}; skipping", file=sys.stderr)
        return 0
    paths = [l.strip() for l in r.stdout.splitlines() if l.strip()]
    if not paths:
        print("No files changed.")
        return 0

    author = a.author.strip()
    if author in admins():
        print(f"{author} is an admin — every path is theirs.")
        return 0

    admin_rx = admin_only_regexes()
    violations, foreign = [], {}
    for p in paths:
        if any(rx.search(p) for rx in admin_rx):
            violations.append(p)
            continue
        folder = p.split("/")[0]
        if folder == SHARED_FOLDER:
            violations.append(p)                # shared feeds every agent; admin-owned
            continue
        if folder in AGENT_FOLDER.values():
            own = owners_of_folder(folder)
            if author and own and author not in own:
                foreign.setdefault(folder, (own, []))[1].append(p)

    if foreign:
        print("Heads up — this request touches corpora the author does not own:")
        for folder, (own, fs) in sorted(foreign.items()):
            print(f"  {folder}  (owned by {', '.join('@' + o for o in own)})")
            for f in fs:
                print(f"      {f}")
        print("\nThat is allowed: editing another agent's corpus and opening a request is how")
        print("feedback reaches its owner. It cannot MERGE without them — CODEOWNERS requires")
        print(f"{', '.join(sorted({o for o, _ in foreign.values()}))} or an admin to approve.")

    if violations:
        print("\nFAIL: admin-only paths changed by a non-admin:", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        return 1

    if not foreign:
        print(f"Every changed path is {author or 'the author'}'s to own.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
