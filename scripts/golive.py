#!/usr/bin/env python3
"""The go-live cutoff, in ONE place.

Every script that decides whether a conversation is real user feedback needs this instant,
and three of them had their own copy of the string. A date constant that exists in three
files is a date constant that will eventually disagree with itself — and the failure is
quiet: transcripts drift between "internal testing" and "user signal" depending on which
script last touched them.

`from golive import GO_LIVE` works from any script in this directory, because Python puts
the running script's own directory on sys.path.

The instant is the merge of tyler-technologies/tcp-ops-center PR #1206
("Feat/cd 285/foundry chatbot"), which shipped the chatbot into Ops Center.

Use the full TIMESTAMP, never just the date: 2026-08-19 21:28 UTC is post-go-live even
though the merge happened the same calendar day. Comparing dates alone would wrongly
exclude the first real conversations we ever got.

Do not re-litigate the cutoff — it was settled against PR #1206's merge time. The commit
linked from that PR (a3be96ca) is only a merge-from-main dated Aug 11 and is not the
go-live moment.
"""

GO_LIVE = "2026-08-19 19:42:29"

# Boilerplate for a transcript that is out of scope because it predates GO_LIVE. Deciding
# this is arithmetic, not a judgement, so no reviewer is named.
EXCLUDE_NOTE = ("Pre-go-live internal testing - the Foundry chatbot shipped "
                "2026-08-19 19:42 UTC (tcp-ops-center PR 1206 merge). Not real user feedback; "
                "auto-excluded on fetch.")


def is_pre_go_live(date_str):
    """True if this `date:` frontmatter value is before go-live.

    String comparison is correct here and deliberate: the format is a zero-padded
    'YYYY-MM-DD HH:MM:SS', which sorts lexicographically the same way it sorts
    chronologically. A missing or malformed date returns False — treat an unknown date as
    in-scope so it surfaces for a human rather than being silently excluded.
    """
    return bool(date_str) and str(date_str) < GO_LIVE
