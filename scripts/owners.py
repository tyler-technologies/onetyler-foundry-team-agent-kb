#!/usr/bin/env python3
"""Who owns which corpus. The single reader of agent-owners.json.

WHY THIS MODULE EXISTS
----------------------
`agent-owners.json` documented, in its own comments, that "a value may be one username or a
list of them". Three scripts read that file and each did something different with a list:

    review_server.py           handled it correctly - `{v} if isinstance(v, str) else set(v)`
    gen_codeowners.py          f-string'd it, producing the owner `@['jon-x', 'someone-y']`
    check_folder_ownership.py  compared `author != ['jon-x', 'someone-y']`, always true

So a two-person corpus would have looked right in the review UI while CODEOWNERS granted
approval to a username that does not exist - meaning nobody but an admin could approve that
folder - and CI would have reported both legitimate owners as making foreign edits. Every part
of that failure is silent.

One documented behaviour implemented three ways is the bug. It is the same shape as the
prose-vs-examples drift this repo has been bitten by before, so the fix is one reader, not
three careful ones.

    from owners import load_owners, owners_for
"""
import json
import pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
OWNERS_FILE = REPO / "agent-owners.json"
CONTRIBUTORS_FILE = REPO / "contributors.json"


def _as_list(v):
    """A value from `by_agent` -> a list of usernames, in a stable order.

    Accepts a bare string or a list, because both are documented. Blanks are dropped: an empty
    string in the file means "not set", and `@` on its own in CODEOWNERS is a parse error that
    GitHub reports by ignoring the whole line.
    """
    if v is None:
        return []
    if isinstance(v, str):
        v = [v]
    seen, out = set(), []
    for name in v:
        name = str(name or "").strip().lstrip("@")
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def load_owners():
    """({slug: [usernames]}, [default_usernames]). Raises if the file is unreadable.

    `default_owner` is normalised the same way, so a team can be the default too.
    """
    d = json.loads(OWNERS_FILE.read_text(encoding="utf-8"))
    by = {k: _as_list(v) for k, v in (d.get("by_agent") or {}).items()
          if not k.startswith("_")}
    return by, _as_list(d.get("default_owner"))


def owners_for(slug, by=None, default=None):
    """Everyone who owns this agent's corpus. Falls back to the default owner(s)."""
    if by is None or default is None:
        by, default = load_owners()
    return by.get(slug) or list(default)


def known_usernames():
    """The `github` values in contributors.json, or an empty set if it cannot be read.

    Used to catch a typo'd owner. That matters more than it sounds: CODEOWNERS silently ignores
    an unknown user, so a misspelled name does not error - it just means the folder has no
    owner and only admins can approve it, which looks exactly like working correctly until
    someone needs an approval.
    """
    try:
        d = json.loads(CONTRIBUTORS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    rows = d if isinstance(d, list) else (d.get("contributors") or [])
    return {str(c.get("github") or "").strip() for c in rows if c.get("github")}
