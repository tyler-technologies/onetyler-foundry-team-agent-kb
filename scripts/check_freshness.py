#!/usr/bin/env python3
"""
Report which upstream sources are overdue for a re-check.

Date arithmetic against scripts/sources.json, plus one check of the config backup's heartbeat.
No Foundry API key needed. The backup check makes one `gh` call and is skippable with
--no-backup; everything else is offline and fast enough to run on every session start.

    python3 scripts/check_freshness.py            # human summary; exit 0 always
    python3 scripts/check_freshness.py --quiet    # print only when something is overdue
    python3 scripts/check_freshness.py --strict   # exit 1 if anything is overdue (CI)
    python3 scripts/check_freshness.py --mark ops-center-tickets   # record a re-check
    python3 scripts/check_freshness.py --no-backup   # skip the backup check (needs gh) today

Bump `last_verified` only after actually diffing the live source against the file.
"""
import argparse, json, re, sys
from datetime import date, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REG = REPO / "scripts" / "sources.json"


BACKUP_REPO = "tyler-technologies/onetyler-foundry-config-backups"
BACKUP_STALE_DAYS = 2


def backup_age():
    """Days since the config backup last ran, from the backup repo's heartbeat file.

    Returns (days, detail, err). Needs `gh`; degrades to a clear message without it.

    WHY THIS IS HERE AND NOT IN sources.json
    ----------------------------------------
    Everything in sources.json is a MANUAL re-check: a human diffs an upstream page against a
    knowledge file and bumps `last_verified`. The config backup is the opposite - it verifies
    itself nightly and nobody bumps anything - so registering it as a source would create a
    date that only goes stale because no human touched it, which is not the question.

    The question is whether the nightly job is still running. That is what `snapshots/LAST_RUN`
    answers, and it is written on EVERY run including days when nothing changed.

    WHY IT MATTERS THAT THIS IS CHECKED SOMEWHERE A HUMAN LOOKS
    -----------------------------------------------------------
    A failed scheduled workflow emails only whoever last touched the workflow file. Nobody else
    finds out. And GitHub disables scheduled workflows entirely after 60 days of repository
    inactivity - which a backup repo is, by nature. The daily commit currently keeps that timer
    from starting, but only as a side effect. A backup that has silently stopped is worse than
    no backup, because it manufactures confidence.
    """
    import shutil
    import subprocess
    if not shutil.which("gh"):
        return None, None, "gh is not installed, so the backup repo cannot be checked"
    try:
        r = subprocess.run(
            ["gh", "api", f"repos/{BACKUP_REPO}/contents/snapshots/LAST_RUN", "-q", ".content"],
            capture_output=True, text=True, timeout=45)
    except (subprocess.TimeoutExpired, OSError) as e:
        return None, None, f"could not reach GitHub: {e}"
    if r.returncode != 0:
        msg = (r.stderr or r.stdout).strip()[:160]
        # Admin-only repo, so "not found" is far more likely to be access than absence.
        if "404" in msg or "Not Found" in msg:
            return None, None, ("cannot read the backup repo — it is admin-only, so the usual "
                                "cause is that your gh account is not on "
                                "onetyler-tcp-pm-admins")
        return None, None, msg
    import base64
    try:
        text = base64.b64decode(r.stdout).decode("utf-8", "replace").strip()
    except Exception:                                                 # noqa: BLE001
        return None, None, "LAST_RUN was unreadable"
    # Format: "2026-08-28T04:05:15Z  2026-08-28  72811B  tiers=daily"
    stamp = text.split()[0] if text else ""
    try:
        when = datetime.strptime(stamp[:10], "%Y-%m-%d").date()
    except ValueError:
        return None, text, f"could not parse a date from {stamp!r}"
    # UTC, NOT date.today(). LAST_RUN is stamped by a GitHub runner in UTC, and comparing it
    # against a LOCAL date is wrong by a day for most of the working day in the Americas - and
    # wrong in the dangerous direction, since it makes a stale backup look fresher. First
    # written as date.today() here and it immediately printed "-1 days ago", which is the same
    # mistake made in the Backups tab an hour earlier. Two occurrences in one evening: treat any
    # comparison against a Foundry or Actions date as UTC unless proven otherwise.
    from datetime import timezone
    today_utc = datetime.now(timezone.utc).date()
    return max(0, (today_utc - when).days), text, None


def report_backup():
    """Print the backup's freshness. Returns True if it is overdue."""
    days, detail, err = backup_age()
    if err:
        print(f"  ??  config-backup  —  {err}")
        return False            # unknown is not the same as overdue; do not fail CI on access
    if days is None:
        print(f"  ??  config-backup  —  {detail}")
        return False
    label = "today" if days == 0 else "yesterday" if days == 1 else f"{days} days ago"
    if days >= BACKUP_STALE_DAYS:
        print(f"\n⚠  Config backup last ran {label} — expected daily.\n")
        print(f"     {detail}")
        print(f"     https://github.com/{BACKUP_REPO}/actions")
        print("     A scheduled workflow that stops emails only whoever last edited it, and")
        print("     GitHub disables schedules after 60 days of repo inactivity.\n")
        return True
    print(f"  ok  config-backup  ({label}, expected daily)")
    return False


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
    ap.add_argument("--no-backup", action="store_true",
                    help="skip the config-backup check (it needs gh and network)")
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

    # The config backup, checked separately from sources.json for the reason in backup_age().
    # Not part of `overdue`, so --strict does not fail CI on it: this needs `gh` and network,
    # and a check that cannot reach GitHub must not be reported as a stale backup.
    backup_overdue = False
    if not a.no_backup:
        backup_overdue = report_backup()

    if a.strict and (overdue or backup_overdue):
        sys.exit(1)


if __name__ == "__main__":
    main()
