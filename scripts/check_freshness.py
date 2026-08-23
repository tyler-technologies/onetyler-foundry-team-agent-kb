#!/usr/bin/env python3
"""
Report which upstream sources are overdue for a re-check.

Pure date arithmetic against scripts/sources.json — no network, no API key, fast enough
to run on every session start.

    python3 scripts/check_freshness.py            # human summary; exit 0 always
    python3 scripts/check_freshness.py --quiet    # print only when something is overdue
    python3 scripts/check_freshness.py --strict   # exit 1 if anything is overdue (CI)
    python3 scripts/check_freshness.py --mark ops-center-tickets   # record a re-check today

Bump `last_verified` only after actually diffing the live source against the file.
"""
import argparse, json, sys
from datetime import date, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REG = REPO / "scripts" / "sources.json"


def load():
    d = json.loads(REG.read_text(encoding="utf-8"))
    return d, d.get("sources", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="silent unless something is overdue")
    ap.add_argument("--strict", action="store_true", help="exit 1 if anything is overdue")
    ap.add_argument("--mark", metavar="ID", help="set last_verified=today for this source id")
    a = ap.parse_args()

    doc, sources = load()

    if a.mark:
        hit = [s for s in sources if s["id"] == a.mark]
        if not hit:
            sys.exit(f"unknown source id {a.mark!r}. known: {[s['id'] for s in sources]}")
        hit[0]["last_verified"] = date.today().isoformat()
        REG.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        print(f"{a.mark}: last_verified = {hit[0]['last_verified']}")
        return

    today = date.today()
    overdue, ok = [], []
    for s in sources:
        try:
            age = (today - datetime.strptime(s["last_verified"], "%Y-%m-%d").date()).days
        except Exception:
            overdue.append((s, None))
            continue
        (overdue if age >= s.get("interval_days", 7) else ok).append((s, age))

    if not overdue and a.quiet:
        return
    if overdue:
        print("\n⚠  Source re-check due:\n")
        for s, age in overdue:
            print(f"  {s['id']}  —  last verified "
                  f"{'never / unparseable' if age is None else f'{age} days ago'}"
                  f" (interval {s.get('interval_days','?')}d)")
            print(f"     source: {s['url']}")
            print(f"     files:  {', '.join(s.get('files', []))}")
            if s.get("notes"):
                print(f"     note:   {s['notes']}")
            print()
        print("  To reconcile: fetch the page, diff it against the file(s), apply changes,")
        print("  then `python3 scripts/check_freshness.py --mark <id>` and commit.")
        print("  Re-upload any changed knowledge file to its Foundry collection.\n")
    for s, age in ok:
        print(f"  ok  {s['id']}  ({age}d ago, interval {s.get('interval_days')}d)")
    if a.strict and overdue:
        sys.exit(1)


if __name__ == "__main__":
    main()
