#!/usr/bin/env python3
"""The Coda half of the FAQ harvesting loop.

The loop, per domain: read the source Teams channel(s) -> extract FAQ candidates not already
in that domain's FAQ-*.md -> post them to a review table on the domain's Coda page -> when a
reviewer ticks **Ready for Processing**, pull the row, index it into FAQ-*.md, and delete it,
so Coda only ever holds outstanding items.

**The checkbox is the whole gate.** There is no Status column: a row does not survive being
processed, so an Approved/Rejected value written on it would never be read again. Decisions
are remembered in `team-config/faq-harvest/ledger-<domain>.json` instead, which outlives the
row. A rejection is expressed by simply deleting the row in Coda — `push` notices that a key
it previously sent has gone and records it as rejected, so the harvester stops proposing it.

This script owns the Coda side: push, pull, delete, status. It does NOT read Teams and it does
NOT edit the FAQ file. Reading a Teams *channel* needs the Microsoft 365 MCP tool
`teams_list_channel_messages`, which is available to Claude in a session but not to a plain
Python process — there are no Graph app credentials on this machine. So the harvest step is
agent-driven and this script is the deterministic part around it. The whole loop, and the rules
the harvest step follows, are in scripts/faq-harvest/HARVEST.md.

    export CODA_API_TOKEN=...            # the REST token, NOT the MCP one
    python3 scripts/coda_faq_review.py status --domain AlignedReleases
    python3 scripts/coda_faq_review.py push   --domain AlignedReleases \\
        team-config/faq-harvest/candidates-alignedreleases-2026-09-08.json
    python3 scripts/coda_faq_review.py pull   --domain AlignedReleases
    python3 scripts/coda_faq_review.py delete --domain AlignedReleases --keys ar-123,ar-456

Two Coda facts this script exists to absorb:

1. **The API cannot create a table.** There is no create-table endpoint, and a markdown table
   in page canvas content becomes static text, not a grid (verified 2026-09-08 by creating a
   probe page and finding no new table). The table is made once by CSV import; see
   scripts/faq-harvest/TABLE-SPEC.md. `status` tells you whether it is there yet.
2. **Writes are async.** POST/DELETE return a requestId and the change is not visible for a few
   seconds — a probe page took ~20s to disappear. Every mutation here polls to completion, so
   "delete the processed row" cannot silently half-happen.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://coda.io/apis/v1"
TOKEN = os.environ.get("CODA_API_TOKEN", "")

# The OneTyler Initiatives Trackers doc. Same doc holds both domains' FAQ pages.
DOC_ID = "KV_6fSnfBc"

# Per-domain: the Coda page the review table lives on, and the FAQ file it feeds.
# `table_id` is the reliable handle and takes precedence when set. Fill it in once the table
# exists: a CSV import lands the table on a page of its own rather than on the FAQ page, so
# matching by page or by name can both miss it. `status` prints the id it resolved.
DOMAINS = {
    "AlignedReleases": {
        "table_id": "grid-4mdZMRDPAE",
        "page_id": "canvas-xQGl2GpyJF",
        "page_name": "FAQs - Aligned Releases",
        "table_name": "FAQ Review Queue (Aligned Releases)",
        "faq_file": "Knowledge-AlignedReleases/FAQ-AlignedReleases.md",
    },
    "StatusPageAndSLA": {
        "table_id": None,
        "page_id": "canvas-fDCK9ni2hA",
        "page_name": "FAQs - Status Pages",
        "table_name": "FAQ Review Queue (Status Pages)",
        "faq_file": "Knowledge-StatusPageAndSLA/FAQ-StatusPageAndSLA.md",
    },
}

# Column names. Must match TABLE-SPEC.md.
KEY_COLUMN = "Key"
# The checkbox is the ONLY gate: checked means "index this into the FAQ and drop the row".
# There is deliberately no Status column. Rows do not survive processing, so an
# Approved/Rejected value on a row would never be read again — the ledger is what remembers a
# decision, because it outlives the row.
READY_COLUMN = "Ready for Processing"
NOTES_COLUMN = "Notes"
DATE_COLUMN = "Date"

# Eight columns, in the order a reviewer reads them. The table is a REVIEW SURFACE, not the
# record: it carries only what a human reads or edits. Everything the FAQ entry format needs
# but a reviewer does not act on — type, confidence, promote_when, conflicts_with — rides in
# the candidates JSON and is written into the entry at indexing time. Earlier versions had a
# column per FAQ field; it just made the thing a human has to read harder to read.
COLUMNS = [
    DATE_COLUMN, "Key", "Question", "Answer",
    "Source", "Source link", NOTES_COLUMN, READY_COLUMN,
]
# Fields the harvester maps straight across. NOTES_COLUMN and DATE_COLUMN are built in push().
CANDIDATE_FIELDS = {
    "Key": "key",
    "Question": "question",
    "Answer": "answer",
    "Source": "source",
    "Source link": "source_link",
}

# Two things that lost their own column but must still reach the reviewer, so they are
# prefixed onto Notes:
#   - an unconfirmed claim must not be published as fact (FAQ policy), and
#   - a candidate that contradicts a live entry must never be applied silently.
PROVISIONAL_PREFIX = "PROVISIONAL — confirm before publishing. "
CONFLICT_PREFIX = "CONFLICTS WITH the live entry \u201c%s\u201d. "


def build_notes(cand):
    """Assemble the Notes cell: conflict pointer, provisional warning, then the note itself."""
    parts = []
    if cand.get("conflicts_with"):
        parts.append(CONFLICT_PREFIX % cand["conflicts_with"])
    if str(cand.get("confidence", "")).lower().startswith("provisional"):
        parts.append(PROVISIONAL_PREFIX)
    note = str(cand.get("review_note", "") or "")
    if note:
        parts.append(note)
    return "".join(parts)


def die(msg):
    sys.exit("coda_faq_review: " + msg)


def request(method, path, body=None, allow_404=False):
    if not TOKEN:
        die("CODA_API_TOKEN is not set.\n"
            "  The REST token is in ~/Library/CloudStorage/OneDrive-TylerTechnologies,Inc/"
            "Repo/claude/coda-details.md\n"
            "  under 'REST API' — NOT the MCP token in the row below it.\n"
            "  Never paste it into a file in this repo; .gitignore blocks *secrets* but the "
            "token has no business here.")
    url = path if path.startswith("http") else BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + TOKEN)
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        if e.code == 404 and allow_404:
            return None
        if e.code == 401:
            die("Coda rejected the token (401). Check CODA_API_TOKEN is the REST token.")
        die("Coda %s %s -> HTTP %s\n  %s" % (method, url, e.code, detail))
    except urllib.error.URLError as e:
        die("Could not reach Coda: %s" % e.reason)


def paged(path):
    """Yield every item across Coda's pagination (it caps page size at 100)."""
    while path:
        page = request("GET", path)
        for item in page.get("items", []):
            yield item
        path = page.get("nextPageLink")


def await_mutation(request_id, what):
    """Coda writes are async. Block until the change is actually applied."""
    if not request_id:
        return
    for _ in range(40):  # ~2 min ceiling; a probe page delete took ~20s
        time.sleep(3)
        status = request("GET", "/mutationStatus/%s" % urllib.parse.quote(request_id))
        if status.get("completed"):
            return
    die("Coda did not confirm %s within 2 minutes (requestId %s).\n"
        "  The write may still land. Re-run `status` before retrying so you do not "
        "double-apply it." % (what, request_id))


def find_table(domain, table_id=None):
    """Return the review table for a domain, or None if it has not been created yet.

    Resolution order: an explicit --table, then the configured table_id, then the FAQ page,
    then the table name. The id forms are exact; the last two are conveniences for a table
    made by hand on the right page.
    """
    cfg = DOMAINS[domain]
    wanted = table_id or cfg.get("table_id")
    if wanted:
        # A mistyped id should fall through to require_table's guidance, not a bare 404.
        table = request("GET", "/docs/%s/tables/%s"
                        % (DOC_ID, urllib.parse.quote(wanted, safe="")),
                        allow_404=True)
        if table is None and table_id:
            die("no Coda table with id '%s' in doc %s.\n"
                "  Check the id you were given — it looks like 'grid-XXXXXXXXXX'."
                % (table_id, DOC_ID))
        return table or None
    for table in paged("/docs/%s/tables?limit=100&tableTypes=table" % DOC_ID):
        if table.get("parent", {}).get("id") == cfg["page_id"]:
            return table
        if table.get("name") == cfg["table_name"]:
            return table
    return None


def require_table(domain, table_id=None):
    table = find_table(domain, table_id)
    if table:
        return table
    cfg = DOMAINS[domain]
    die("no review table found on Coda page '%s'.\n"
        "  The Coda API cannot create one — see scripts/faq-harvest/TABLE-SPEC.md; make it by hand once:\n"
        "    https://docs.superhuman.com/d/_d%s\n"
        "  Name it '%s' (or just put it on that page; this script matches on either)."
        % (cfg["page_name"], DOC_ID, cfg["table_name"]))


def read_rows(domain, table_id=None):
    table = require_table(domain, table_id)
    path = ("/docs/%s/tables/%s/rows?limit=100&useColumnNames=true&valueFormat=simple"
            % (DOC_ID, table["id"]))
    rows = []
    for row in paged(path):
        values = row.get("values", {})
        rows.append({
            "row_id": row["id"],
            "key": str(values.get(KEY_COLUMN, "")).strip(),
            "ready": values.get(READY_COLUMN) is True,
            "values": {k: values.get(k, "") for k in COLUMNS},
        })
    return table, rows


def cmd_status(args):
    table = find_table(args.domain, args.table)
    cfg = DOMAINS[args.domain]
    if not table:
        print("Review table: NOT CREATED YET on page '%s'." % cfg["page_name"])
        print("  Create it once by hand — see scripts/faq-harvest/TABLE-SPEC.md.")
        return 1
    _, rows = read_rows(args.domain, args.table)
    ready = [r for r in rows if r["ready"]]
    print("Review table: %s (%s)" % (table["name"], table["id"]))
    print("Rows: %d  —  %d ready for processing, %d still under review"
          % (len(rows), len(ready), len(rows) - len(ready)))
    if ready:
        print("\nReady to index into %s:" % cfg["faq_file"])
        for row in ready:
            print("  %-22s %s" % (row["key"], str(row["values"].get("Question", ""))[:66]))
        print("\n  pull them:   python3 scripts/coda_faq_review.py pull --domain %s"
              % args.domain)
    ledger = load_ledger(args.domain)
    if ledger:
        counts = {}
        for outcome in ledger.values():
            counts[outcome] = counts.get(outcome, 0) + 1
        print("\nLedger: %d decided (%s)"
              % (len(ledger), ", ".join("%s %s" % (n, k) for k, n in sorted(counts.items()))))
    return 0


def cmd_push(args):
    table = require_table(args.domain, args.table)
    with open(args.candidates) as fh:
        batch = json.load(fh)
    if batch.get("domain") != args.domain:
        die("%s is a batch for domain '%s', but --domain is '%s'."
            % (args.candidates, batch.get("domain"), args.domain))

    _, existing = read_rows(args.domain, args.table)
    seen = {r["key"] for r in existing if r["key"]}
    # Catch rejections expressed by deleting the row, before deciding what is new.
    removed = reconcile_removed(args.domain, existing, table["id"])
    if removed:
        print("Recorded %d row(s) you removed in Coda as rejected: %s"
              % (len(removed), ", ".join(removed)))
    ledger = load_ledger(args.domain)

    rows, skipped_present, skipped_decided = [], [], []
    for cand in batch["candidates"]:
        key = cand["key"]
        if key in seen:
            skipped_present.append(key)
            continue
        if key in ledger:
            skipped_decided.append("%s (%s)" % (key, ledger[key]))
            continue
        cells = [{"column": col, "value": str(cand.get(src, "") or "")}
                 for col, src in CANDIDATE_FIELDS.items()]
        cells.append({"column": NOTES_COLUMN, "value": build_notes(cand)})
        cells.append({"column": READY_COLUMN, "value": False})
        cells.append({"column": DATE_COLUMN, "value": batch.get("harvested", "")})
        rows.append({"cells": cells})

    for label, items in (("already in the table", skipped_present),
                         ("already decided (in the ledger)", skipped_decided)):
        if items:
            print("Skipped %d %s: %s" % (len(items), label, ", ".join(items)))

    if not rows:
        print("Nothing new to push.")
        return 0
    if args.dry_run:
        print("Would push %d candidates:" % len(rows))
        for row in rows:
            cells = {c["column"]: c["value"] for c in row["cells"]}
            print("  %-22s [%-11s] %s"
                  % (cells["Key"], cells["Type"], cells["Question"][:64]))
        return 0

    resp = request("POST", "/docs/%s/tables/%s/rows" % (DOC_ID, table["id"]),
                   {"rows": rows, "keyColumns": [KEY_COLUMN]})
    await_mutation(resp.get("requestId"), "the push of %d rows" % len(rows))

    # Remember what we sent, so a row later deleted by hand can be read as a rejection.
    pushed, decided, _ = _read_ledger(args.domain)
    for row in rows:
        cells = {c["column"]: c["value"] for c in row["cells"]}
        pushed[cells[KEY_COLUMN]] = batch.get("harvested", "")
    save_ledger(args.domain, pushed, decided, table["id"])
    print("Pushed %d candidates to %s." % (len(rows), table["name"]))
    print("Review them at https://docs.superhuman.com/d/_d%s" % DOC_ID)
    return 0


def cmd_pull(args):
    """Emit the rows whose Ready-for-Processing box is checked, for indexing into the FAQ."""
    _, rows = read_rows(args.domain, args.table)
    picked = [r for r in rows if r["ready"]]
    if args.key:
        wanted = {k.strip() for k in args.key.split(",") if k.strip()}
        picked = [r for r in picked if r["key"] in wanted]
    if not picked:
        print("Nothing is checked as ready for processing.", file=sys.stderr)
    out = {
        "domain": args.domain,
        "faq_file": DOMAINS[args.domain]["faq_file"],
        "pulled": time.strftime("%Y-%m-%d"),
        "rows": [{"key": r["key"], **r["values"]} for r in picked],
        "delete_after_indexing": (
            "python3 scripts/coda_faq_review.py delete --domain %s --keys %s"
            % (args.domain, ",".join(r["key"] for r in picked)) if picked else None),
    }
    print(json.dumps(out, indent=2))
    return 0


def ledger_path(domain):
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, os.pardir, "team-config", "faq-harvest",
                        "ledger-%s.json" % domain.lower())


def _read_ledger(domain):
    try:
        with open(ledger_path(domain)) as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return {}, {}, None
    return data.get("pushed", {}), data.get("decided", {}), data.get("table_id")


def load_ledger(domain):
    """Keys already decided — indexed or rejected. The harvester must not re-propose these."""
    return _read_ledger(domain)[1]


def save_ledger(domain, pushed, decided, table_id):
    path = ledger_path(domain)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump({
            "domain": domain,
            "note": ("Shared state, committed on purpose. `pushed` is every key ever sent to "
                     "the Coda review table; `decided` is what happened to it. The review "
                     "table holds only outstanding items, so it cannot itself remember that "
                     "something was already handled — without this file the next harvest "
                     "re-proposes everything already dealt with. `table_id` records which "
                     "table `pushed` refers to, so rebuilding the table is not mistaken for "
                     "the reviewer having deleted every row."),
            "table_id": table_id,
            "pushed": pushed,
            "decided": decided,
        }, fh, indent=2, sort_keys=True)
        fh.write("\n")


def reconcile_removed(domain, rows, table_id):
    """A key we pushed, now absent from the table and not in `decided`, was deleted by a human.

    That is how a rejection is expressed once there is no Status column: the reviewer just
    removes the row. Record it as rejected so the harvester stops proposing it.

    Guarded on table identity. If `pushed` was recorded against a DIFFERENT table — the table
    was rebuilt, which is the normal way a column change happens, since the Coda API cannot
    rename or delete a column — then every key looks absent and would be marked rejected
    wholesale. In that case re-point the ledger and reconcile nothing.
    """
    pushed, decided, ledger_table = _read_ledger(domain)
    if ledger_table and table_id and ledger_table != table_id:
        save_ledger(domain, pushed, decided, table_id)
        print("Ledger was recorded against table %s, now pointing at %s — treating this as a "
              "rebuild, not %d rejections." % (ledger_table, table_id, len(pushed)))
        return []
    present = {r["key"] for r in rows if r["key"]}
    removed = [k for k in pushed if k not in present and k not in decided]
    for key in removed:
        decided[key] = "rejected (row removed in Coda)"
    if removed or ledger_table != table_id:
        save_ledger(domain, pushed, decided, table_id)
    return removed


def cmd_delete(args):
    table = require_table(args.domain, args.table)
    _, rows = read_rows(args.domain, args.table)
    keys = [k.strip() for k in args.keys.split(",") if k.strip()]
    by_key = {r["key"]: r for r in rows}

    missing = [k for k in keys if k not in by_key]
    if missing:
        die("not in the table: %s\n  Nothing was deleted. Run `status` to see what is there."
            % ", ".join(missing))

    targets = [by_key[k] for k in keys]
    not_ready = [r["key"] for r in targets if not r["ready"]]
    if not_ready and not args.force:
        die("these are not checked as ready for processing: %s\n"
            "  Nothing was deleted. Deleting an unreviewed row loses the candidate — the "
            "harvester will not re-propose it once it is in the ledger.\n"
            "  Pass --force if you really mean to discard them."
            % ", ".join(not_ready))

    print("About to delete %d row(s) from %s:" % (len(targets), table["name"]))
    for row in targets:
        print("  %-22s %s" % (row["key"], str(row["values"].get("Question", ""))[:64]))
    if args.dry_run:
        print("\n--dry-run: nothing deleted.")
        return 0

    resp = request("DELETE", "/docs/%s/tables/%s/rows" % (DOC_ID, table["id"]),
                   {"rowIds": [r["row_id"] for r in targets]})
    await_mutation(resp.get("requestId"), "the delete of %d rows" % len(targets))

    pushed, decided, _ = _read_ledger(args.domain)
    for row in targets:
        decided[row["key"]] = args.outcome or ("indexed" if row["ready"] else "discarded")
    save_ledger(args.domain, pushed, decided, table["id"])
    print("Deleted %d row(s); ledger now holds %d decided keys." % (len(targets), len(decided)))
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Coda side of the FAQ harvesting loop.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__)
    # --domain is accepted on both sides of the subcommand. Putting it only at the top level
    # makes `status --domain X` an error, which reads as a broken script rather than a
    # misplaced flag — and every usage example naturally writes the subcommand first.
    # The subcommand copy writes to its own dest: a subparser's default DOES overwrite a value
    # the parent already set, so sharing one dest silently discarded `--domain X status`.
    def domain_arg(p, dest="domain_sub", table_dest="table_sub"):
        p.add_argument("--domain", dest=dest, default=None, choices=sorted(DOMAINS),
                       help="which corpus's review table to act on "
                            "(default: AlignedReleases)")
        p.add_argument("--table", dest=table_dest, default=None,
                       help="Coda table id (grid-...), overriding the configured one. Use "
                            "this the first time, before DOMAINS[...]['table_id'] is filled in")
        return p

    domain_arg(parser, dest="domain", table_dest="table")
    sub = parser.add_subparsers(dest="command", required=True)

    domain_arg(sub.add_parser("status", help="is the table there, and what is waiting in it"))

    p_push = domain_arg(sub.add_parser("push", help="upsert candidates into the review table"))
    p_push.add_argument("candidates", help="path to a candidates-*.json batch")
    p_push.add_argument("--dry-run", action="store_true")

    p_pull = domain_arg(
        sub.add_parser("pull", help="print the ready-for-processing rows as JSON"))
    p_pull.add_argument("--key", help="comma-separated keys, to pull a subset of the ready rows")

    p_del = domain_arg(
        sub.add_parser("delete", help="delete rows by Key and record them in the ledger"))
    p_del.add_argument("--keys", required=True, help="comma-separated candidate keys")
    p_del.add_argument("--outcome", help="what to record in the ledger (default: 'indexed')")
    p_del.add_argument("--force", action="store_true",
                       help="allow deleting rows that are not checked ready")
    p_del.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()
    # Whichever side of the subcommand supplied --domain wins; the fallback applies only when
    # neither did. Giving both the same dest loses the parent's value (see domain_arg).
    args.domain = args.domain_sub or args.domain or "AlignedReleases"
    args.table = args.table_sub or args.table
    return {"status": cmd_status, "push": cmd_push,
            "pull": cmd_pull, "delete": cmd_delete}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
