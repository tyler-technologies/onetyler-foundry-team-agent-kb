# START HERE — the Shared corpus

**This folder breaks the one-folder-per-agent rule deliberately.** Every other
`Knowledge-<Domain>/` folder maps to exactly one Foundry agent and one KB collection. This
one holds content that **every** agent needs, and its files are uploaded to **all** writable
collections.

## Files

| File | What it is |
|---|---|
| `Conf-OneTylerTickets.md` | The single authoritative catalog of **every OneTyler ticket**, across all domains — Ops Center, Identity, Support Access Center, Development/infrastructure, Forge/TCW, 3rd-party — plus the separate feature-request portal, deprecated and superseded forms, and known broken links. |

## Why this is shared, not owned by Ops Center

Ticket questions arrive at every agent. Someone talking directly to the Identity agent asks
"which ticket do I file for a federation issue?" and the answer is in this catalog. If the
file lived only in `Knowledge-OpsCenter/`, the Identity agent would have to hand off — and
in a direct (non-team) conversation there is nobody to hand off to. The likely failure mode
is a plausible invented ticket URL, which is worse than no answer.

The team router *also* sends ticket questions to Ops Center, so both paths are covered:
routing for team conversations, this shared file for direct ones.

## Upload targets

One source file, several collections. **A change here must be uploaded to all of them**, or
the copies drift:

| Collection | Agent | Status |
|---|---|---|
| `OT-OpsCenter` | Ops Center | ✅ upload |
| `OT-BPD` | General Blueprint Docs | ✅ upload |
| `OT-SAC` | Support Access Center | ✅ upload |
| `OT-AlignedReleases` | Aligned Releases | ✅ upload |
| `TCP-KB-Identity` | Tyler Identity Assistant | ✅ upload (since 2026-08-24) |

## Maintenance

`Conf-OneTylerTickets.md` is reconciled against **three** upstream sources — see
`scripts/sources.json` and the *Keeping the ticket catalog current* section of `CLAUDE.md`.
Never edit it from memory; always re-derive from the sources.
