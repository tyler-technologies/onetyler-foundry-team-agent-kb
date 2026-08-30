#!/usr/bin/env python3
"""Read a reviewer's WRITTEN feedback out of a transcript body.

THE FEEDBACK IS THE PROSE, NOT THE DROPDOWNS.

Reviewers write an ideal response under the bad answer and click "Mark reviewed & next". They
often do not touch the header fields at all — and they should not have to. Writing "this is
wrong, it should have said X" is the valuable part; classifying it into `diagnosis` and
`fix_target` is clerical work an agent can do from the prose.

That collides with how the form is pre-filled. A `pending` transcript opens set to
routing `correct` / answer `good` / diagnosis `n-a` / fix_target `none` / kb_action `none` /
action_status `none-needed`, so that a genuinely clean transcript is one click. Click
"Mark reviewed" after writing an ideal response and the file now says "nothing wrong" in the
frontmatter while the body says the answer was wrong.

Measured on 2026-08-26: in exactly that state, `review_status.py --check` passed without
complaint and `--actions` — the command CLAUDE.md tells agents to use to find work —
returned NOTHING, while the dashboard said "1 reviewed and awaiting processing". An agent
follows that pointer, finds an empty list, and reasonably concludes there is nothing to do.
The reviewer's ideal response is never acted on and nobody finds out.

So: any tool deciding "is there work here" must read the BODY. Fields are a hint, and a
misleading one.

    from reviewtext import body_feedback, has_feedback
"""
import re

# The empty-state placeholder the fetch script writes into each exchange. Present in every
# unreviewed transcript, so it must not count as feedback.
PLACEHOLDERS = (
    "**Review —** _verdict:_ · _should have said:_",
    "**Review —** _verdict:_ * _should have said:_",
)


def _clean(s):
    """Strip boilerplate and whitespace; return '' when nothing real remains."""
    if not s:
        return ""
    out = []
    for line in s.splitlines():
        t = line.strip()
        if not t or t in PLACEHOLDERS:
            continue
        # A line that is only italic/bold markers and colons is still the placeholder,
        # reworded. Cheap guard against the template drifting.
        if re.fullmatch(r"[*_\s:·.—-]*", t):
            continue
        out.append(t)
    return "\n".join(out).strip()


def body_feedback(text):
    """Everything a human wrote into a transcript body.

    Returns {"corrections": {n: text}, "proposed": text}. Both are stripped of the empty-state
    placeholders, so truthiness means a human actually wrote something.
    """
    ideals = {}
    for m in re.finditer(r"<!-- review:(\d+) -->\n?(.*?)<!-- /review:\1 -->", text or "", re.S):
        c = _clean(m.group(2))
        if c:
            ideals[int(m.group(1))] = c
    pm = re.search(r"<!-- proposed-fix -->\n?(.*?)<!-- /proposed-fix -->", text or "", re.S)
    return {"corrections": ideals, "proposed": _clean(pm.group(1)) if pm else ""}


def has_feedback(text):
    fb = body_feedback(text)
    return bool(fb["corrections"] or fb["proposed"])


def feedback_summary(text, width=90):
    """One-line gist for a listing. Prefers the proposed fix, which is usually the
    actionable sentence; falls back to the first ideal response."""
    fb = body_feedback(text)
    s = fb["proposed"] or (next(iter(fb["corrections"].values()), "") if fb["corrections"] else "")
    s = " ".join(s.split())
    return s[:width] + ("…" if len(s) > width else "")


# The header values a `pending` form is pre-filled with. Fields still sitting at ALL of these
# means nobody classified anything — whatever the reviewer wrote in the body is untriaged,
# regardless of what the fields claim.
NO_CHANGE_DEFAULTS = {
    "routing_verdict": "correct",
    "answer_verdict": "good",
    "diagnosis": "n-a",
    "fix_target": "none",
    "kb_action": "none",
    "action_status": "none-needed",
}


def is_unclassified(fm):
    """True when every classification field is still the pre-filled no-change answer."""
    return all((fm.get(k, "") or "") == v for k, v in NO_CHANGE_DEFAULTS.items())


def needs_triage(fm, text):
    """A human wrote feedback but nothing was classified — an agent must read the prose and
    fill the fields in. This is the case that used to vanish."""
    return has_feedback(text) and is_unclassified(fm)
