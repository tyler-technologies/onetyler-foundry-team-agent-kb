# team-config

Mirrors of Foundry-side configuration that is **not** knowledge-base content but still
needs version control, review, and an audit trail.

These files are the source of truth for *what we intend*; Foundry holds what is *live*.
A change here is not in effect until it is pushed to Foundry — and a change made directly
in the Foundry UI will silently drift from this folder.

| File | Mirrors | Where it lives in Foundry |
|---|---|---|
| `team-routing-prompt.md` | The OneTyler Cloud Living team's `system_prompt` — the entire router, since `routing_rules` is `null` | Team config, `system_prompt` |
| `backups/*.json` | Full pre-change snapshots of Foundry config objects. Permanent — never pruned | n/a (this repo is the only copy) |

## backups/ — mandatory, and permanent

**Never change a Foundry config object without committing a backup first.** These objects
exist only in Foundry: there is no undo and no other copy. Backups are kept in
`backups/` **forever** — they are the only record of what a config looked like before a
change, and they are what you restore from.

Naming: `<object>-backup-<YYYYMMDD-HHMMSS>.json`, holding the full GET response verbatim.

```bash
UA="claude-code-foundry-kb/1.0"; B="https://foundry.tylertechai.com"
T="e92bd437-cb84-4e18-88e6-757370b39c90"
curl -s -A "$UA" -H "X-API-Key: $FOUNDRY_API_KEY" "$B/api/teams/$T" \
  -o "team-config/backups/team-backup-$(date +%Y%m%d-%H%M%S).json"
```

Scan a backup for credentials before committing it — config objects can carry auth
material (an MCP server's API key, an OIDC client secret). Redact rather than skip the
backup, and note the redaction in the file.

To restore: PUT the backup body back (full-object replace), then re-fetch and diff.

## ⚠ Foundry sanitises angle brackets on write — keep them out of prompts

The team-config write path HTML-escapes `>` to `&gt;` **and deletes anything that looks
like an HTML tag**. Observed 2026-08-23: `- **"the <product> client"**` came back as
`- **"the  client"**`, with the placeholder silently gone, and every `->` became `-&gt;`.

The escaping and the deletion happened to cancel out in length, so the payload was the
**same byte count** before and after. A size check would have passed. Only a content diff
caught it.

So: **write prompts with no `<` or `>` at all** — use "then route to" instead of `->`, and
an uppercase word like `PRODUCT` instead of `<product>`. And always diff the live value
against the mirror after a write, not just the field list.

## Pushing a change to Foundry

`PUT /api/teams/{teamId}` is a **full-object replace**: GET the team, change only the field
you mean to change, PUT the whole object back, then re-fetch and diff to confirm.

Team id: `e92bd437-cb84-4e18-88e6-757370b39c90`

## Checking for drift

```bash
curl -s -A "claude-code-foundry-kb/1.0" -H "X-API-Key: $FOUNDRY_API_KEY" \
  "https://foundry.tylertechai.com/api/teams/e92bd437-cb84-4e18-88e6-757370b39c90" \
  | python3 -c "import json,sys; print(json.load(sys.stdin).get('team',{}).get('system_prompt'))"
```

Compare against the fenced block in `team-routing-prompt.md`.
