#!/usr/bin/env python3
"""Compare every Foundry collection and the team router against this repo.

RUN THIS AFTER EVERY PR MERGE. The repo is the source of truth for all five collections
(CLAUDE.md hard rule 1), and a merge is exactly the moment that stops being true: `main` now
carries content the live agents do not have. Nothing else notices — a knowledge file only
reaches an agent when somebody uploads it, and an unnoticed gap means the agent keeps
answering from the old text while the repo looks correct.

The two guards face opposite directions and you want both:

    preflight_upload.py     blocks Foundry getting AHEAD of main (unapproved content)
    this script             catches main being ahead of FOUNDRY  (unshipped content)

WHAT IT COMPARES
----------------
1. Every file in each collection against its local folder — missing, extra, or size-mismatched.
2. Shared files against EVERY collection in sources.json upload_targets. A shared file
   uploaded to four of five targets leaves the fifth answering from stale text, and nothing
   about the four successful uploads hints at it.
3. The live team routing prompt against team-config/team-routing-prompt.md.

`fileSize` is the drift signal because the file record carries no content hash. Equal sizes
are strong but not conclusive evidence of equal content; --deep downloads and byte-compares.

    python3 scripts/check_foundry_drift.py
    python3 scripts/check_foundry_drift.py --deep        # download and byte-compare
    python3 scripts/check_foundry_drift.py --collection OT-OpsCenter

Exit 0 = in sync. Exit 1 = drift found; the output says which direction and what to do.
Needs FOUNDRY_API_KEY. Read-only — it never uploads anything.
"""
import argparse, json, os, subprocess, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE = os.environ.get("FOUNDRY_API_URL", "https://foundry.tylertechai.com")
KEY = os.environ.get("FOUNDRY_API_KEY", "")
UA = "claude-code-foundry-kb/1.0"          # a missing User-Agent gets a 403 from the WAF
TEAM_ID = "e92bd437-cb84-4e18-88e6-757370b39c90"

# collection -> local folder. Keep in step with the table in CLAUDE.md.
COLLECTIONS = {
    "OT-OpsCenter":       "Knowledge-OpsCenter",
    "OT-BPD":             "Knowledge-BP-General",
    "OT-SAC":             "Knowledge-SupportAccessCenter",
    "OT-AlignedReleases": "Knowledge-AlignedReleases",
    "TCP-KB-Identity":    "Knowledge-TylerIdentity",
}


def api(path):
    r = subprocess.run(["curl", "-s", "-A", UA, "-H", f"X-API-Key: {KEY}", BASE + path],
                       capture_output=True, text=True)
    if not r.stdout.strip():
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        print(f"  ! non-JSON from {path[:70]} — auth failure? (403 usually means a missing "
              f"User-Agent, 401 a rotated key)", file=sys.stderr)
        return None


def download(col, fid):
    r = subprocess.run(["curl", "-s", "-A", UA, "-H", f"X-API-Key: {KEY}",
                        f"{BASE}/api/tenant-knowledge-base/collections/{col}/files/{fid}/download"],
                       capture_output=True)
    return r.stdout


def shared_targets():
    try:
        d = json.loads((REPO / "scripts" / "sources.json").read_text(encoding="utf-8"))
        return {k: v for k, v in (d.get("upload_targets") or {}).items()
                if not k.startswith("_")}
    except Exception:
        return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deep", action="store_true", help="download and byte-compare")
    ap.add_argument("--collection", help="check only this collection")
    a = ap.parse_args()

    if not KEY:
        print("FOUNDRY_API_KEY is not set — cannot check Foundry.\n"
              "  source ../foundry-secrets.env    (path depends on your checkout)")
        return 1

    shared = shared_targets()
    cols = {a.collection: COLLECTIONS[a.collection]} if a.collection else COLLECTIONS
    if a.collection and a.collection not in COLLECTIONS:
        print(f"unknown collection {a.collection!r}; known: {', '.join(COLLECTIONS)}")
        return 1

    drift, pending = [], []
    for col, folder in cols.items():
        files = api(f"/api/tenant-knowledge-base/collections/{col}/files")
        if files is None:
            drift.append((col, "-", "could not read the collection"))
            continue
        remote = {f["fileName"]: f for f in files}

        # Which local files are SUPPOSED to be in this collection: the folder's own .md
        # files, plus any shared file whose upload_targets name it.
        expected = {p.name: p for p in (REPO / folder).glob("*.md")} if (REPO / folder).is_dir() else {}
        for rel, targets in shared.items():
            if col in targets:
                p = REPO / rel
                if p.is_file():
                    expected[p.name] = p

        for name, p in sorted(expected.items()):
            r = remote.get(name)
            if r is None:
                drift.append((col, name, "MISSING from Foundry — in the repo, never uploaded"))
                continue
            loc = p.stat().st_size
            if loc != r.get("fileSize"):
                drift.append((col, name,
                              f"SIZE differs — Foundry {r.get('fileSize')}, repo {loc}"))
            elif a.deep:
                if download(col, r["id"]) != p.read_bytes():
                    drift.append((col, name, "CONTENT differs despite equal size"))
            if r.get("ingestionStatus") not in ("ingested", None):
                # NOT drift. The repo and Foundry hold the same bytes; Bedrock is still
                # indexing. Reporting it as drift right after a correct upload is how a check
                # earns a reputation for crying wolf. Retrieval also commonly goes live
                # minutes before this field flips, so it is not even a reliable
                # "not available yet" signal — probe retrieval for that.
                pending.append((col, name, f"ingestionStatus={r.get('ingestionStatus')} — "
                                           f"same content as the repo, still indexing"))

        for name in sorted(set(remote) - set(expected)):
            drift.append((col, name, "EXTRA in Foundry — not in the repo. Left over from a "
                                     "rename, or edited in the UI"))

    # The team router. Not a collection file — the only copy of this lives in Foundry, so a
    # repo mirror that has silently diverged is worth knowing about.
    mirror = REPO / "team-config" / "team-routing-prompt.md"
    if not a.collection and mirror.is_file():
        t = api(f"/api/teams/{TEAM_ID}") or {}
        t = t.get("team", t)
        # Verified against the live object 2026-08-26: the router's prompt is `system_prompt`
        # on the team. NOT `instructions`, and not under orchestrator_config — that dict holds
        # strategy/llm_model/toolIds only. Guessing the field name produced a "could not read
        # the live prompt" false positive, which is worse than no check: it trains you to
        # ignore the one line that would report real router drift.
        live = t.get("system_prompt") or ""
        if not live:
            drift.append(("team", "routing prompt", "could not read the live prompt"))
        else:
            def norm(s):
                return " ".join(s.split())
            if norm(live) not in norm(mirror.read_text(encoding="utf-8")):
                drift.append(("team", "routing prompt",
                              "live prompt is not contained in team-config/"
                              "team-routing-prompt.md — mirror may be stale. Note Foundry "
                              "HTML-escapes '>' and strips <tag>-shaped text, so compare "
                              "content, not length"))

    if pending:
        print(f"{len(pending)} file(s) still indexing (NOT drift — same content as the repo):")
        for col, name, why in pending:
            print(f"  {col:<20} {name}\n  {'':<20}   {why}")
        print("  Normal for a few minutes after an upload. Retrieval is often live already —"
              "\n  probe content rather than waiting on this field.\n")

    if not drift:
        n = sum(1 for _ in cols)
        print(f"In sync — {n} collection(s) and the team router match the repo"
              f"{' (byte-compared)' if a.deep else ' (by file size)'}.")
        return 0

    print(f"{len(drift)} drift item(s):\n")
    for col, name, why in drift:
        print(f"  {col:<20} {name}")
        print(f"  {'':<20}   {why}")
    print("\nBefore fixing: run scripts/preflight_upload.py on anything you intend to upload.\n"
          "Only content that is already on main may go to Foundry.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
