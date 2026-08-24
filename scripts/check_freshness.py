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
import argparse, json, re, sys
from datetime import date, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REG = REPO / "scripts" / "sources.json"


def load():
    d = json.loads(REG.read_text(encoding="utf-8"))
    return d, d.get("sources", [])


def scan_readiness(src):
    """Is an upstream source substantive enough to build a corpus from yet?

    Blueprint sections get created as stub pages long before anyone writes them, so a
    directory existing tells you nothing. This counts real content: markdown lines that
    are not frontmatter, headings, or a stub marker.
    """
    r = src.get("readiness") or {}
    path = Path(src.get("source_path", ""))
    if not src.get("source_path"):
        return None
    if not path.is_dir():
        return {"available": False,
                "msg": f"source not available on this machine ({path})"}
    markers = [m.lower() for m in r.get("stub_markers", [])]
    files = sorted(path.rglob("*.md"))
    stub_files, substantive = [], 0
    for f in files:
        txt = f.read_text(encoding="utf-8", errors="replace")
        body = re.sub(r"^---\n.*?\n---\n", "", txt, flags=re.S)   # drop frontmatter
        low = body.lower()
        if any(m in low for m in markers):
            stub_files.append(f.name)
        for line in body.splitlines():
            t = line.strip()
            if t and not t.startswith("#") and not any(m in t.lower() for m in markers):
                substantive += 1
    need = r.get("min_substantive_lines", 150)
    ready = not stub_files and substantive >= need
    return {"available": True, "ready": ready, "files": len(files),
            "stub_files": stub_files, "substantive": substantive, "need": need}


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
    # readiness of sources that are waiting for upstream content
    waiting = [s for s in sources if s.get("source_path")]
    if waiting:
        print("\nUpstream content readiness:")
        for src in waiting:
            res = scan_readiness(src)
            if res is None:
                continue
            if not res["available"]:
                print(f"  ?   {src['id']}: {res['msg']}")
                continue
            if res["ready"]:
                print(f"  ✅ READY  {src['id']}: {res['substantive']} substantive lines "
                      f"across {res['files']} file(s), no stubs left "
                      f"(threshold {res['need']}).")
                print(f"      -> build {src.get('target_corpus','the corpus')} and spin up its agent. "
                      f"See that corpus's 'Becoming a real corpus' section for the order.")
            else:
                why = []
                if res["stub_files"]:
                    why.append(f"{len(res['stub_files'])}/{res['files']} file(s) still stubs")
                if res["substantive"] < res["need"]:
                    why.append(f"{res['substantive']} substantive lines < {res['need']}")
                print(f"  ⏳ not ready  {src['id']}: " + "; ".join(why))

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
