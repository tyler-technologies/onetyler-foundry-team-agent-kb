#!/usr/bin/env python3
"""Upload merged knowledge files to Foundry, then prove they landed. Admins only.

    python3 scripts/publish_to_foundry.py --dry-run     # what would go, and where
    python3 scripts/publish_to_foundry.py               # asks before writing anything
    python  scripts\\publish_to_foundry.py               # Windows

This is the one step in the daily loop that still needed an assistant, purely because it was a
sequence of curl calls nobody should have to remember. Everything it does was already written
down in CLAUDE.md; this file is that procedure, executed in the right order with the checks
that the order exists for.

WHAT IT ENFORCES, AND WHY EACH ONE IS HERE
------------------------------------------
1. MERGED FIRST. Refuses any file whose bytes differ from origin/main. Uploading from an
   unmerged branch puts content in front of users that the repo has not accepted, and the next
   drift check then tries to undo it. That happened once - a 6.5-hour window on 2026-08-25 -
   which is why `preflight_upload.py` exists and why this calls it rather than reimplementing
   it.
2. ASKS BEFORE WRITING. A Foundry write is a production change: these collections back live
   agents answering real customer questions. `--yes` exists for scripted use but is not the
   default, and no amount of "it is probably fine" should make it the default.
3. UPLOAD EVERYTHING, THEN SYNC ONCE. Bedrock runs one ingestion job per data source and a job
   only indexes what was present when its scan snapshot was taken. Every upload auto-triggers
   its own scoped sync, so a naive file-by-file loop becomes N queued jobs where the first
   indexes its own files and the rest sit `pending` for hours.
4. VERIFIES BY RETRIEVAL, NOT BY STATUS. `ingestionStatus: "ingested"` proves nothing - a file
   can report ingested and hold zero retrievable text. Conversely retrieval often goes live
   BEFORE the status flips (measured ~100s vs ~6min), so the status field is the weaker signal
   in both directions.

WHAT IT DOES NOT DO
-------------------
It does not decide WHAT to change. Turning a reviewer's "it should have said X" into the right
words in the right file is writing and judgement, and it is the one part of this repo that
genuinely needs a person or an assistant. This script only ships what has already been
written, reviewed and merged.

It also does not mark transcripts `pushed` - that is `mark_pushed.py`, kept separate because a
transcript is only closed out when its change is verified live, and this script tells you when
that is true rather than assuming it.
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE = os.environ.get("FOUNDRY_API_URL", "https://foundry.tylertechai.com").rstrip("/")
KEY = os.environ.get("FOUNDRY_API_KEY", "")
UA = "claude-code-foundry-kb/1.0"

# Folder -> collection. Same table as check_foundry_drift.py and the review UI; if these ever
# disagree, the drift check is the one to trust because it is what CI runs.
COLLECTIONS = {
    "Knowledge-OpsCenter": ["OT-OpsCenter"],
    "Knowledge-BP-General": ["OT-BPD"],
    "Knowledge-SupportAccessCenter": ["OT-SAC"],
    "Knowledge-AlignedReleases": ["OT-AlignedReleases"],
    "Knowledge-TylerIdentity": ["TCP-KB-Identity"],
    # Shared files go to EVERY writable collection, so any agent can answer directly instead
    # of handing off - in a direct conversation there is nobody to hand off to, and the
    # failure mode is an invented ticket URL. A shared file uploaded to only some of them
    # leaves the copies drifting.
    "Knowledge-Shared": ["OT-OpsCenter", "OT-BPD", "OT-SAC", "OT-AlignedReleases",
                         "TCP-KB-Identity"],
}


def die(msg):
    print(f"\nERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def api(path, method="GET", body=None, ctype="application/json", raw=None, timeout=120):
    url = f"{BASE}{path}"
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-API-Key", KEY)
    req.add_header("User-Agent", UA)       # missing UA -> 403 from the WAF, valid key or not
    if data is not None and ctype:
        req.add_header("Content-Type", ctype)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            text = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}"
    except Exception as e:                                        # noqa: BLE001
        return None, str(e)
    if not text.strip():
        return {}, None
    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        # HTML back means auth failed and we were redirected to a login page.
        return None, f"non-JSON response (auth failure?): {text[:160]}"


def git(*args):
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=120)
    return r.returncode, (r.stdout + r.stderr).strip()


def changed_knowledge_files(since):
    """Knowledge files whose content on main differs from what Foundry last received.

    Uses git, not the Foundry file sizes, to decide the candidate set: git knows what CHANGED,
    while sizes only reveal drift after the fact. The size comparison still runs afterwards as
    the skip check, so an unchanged file is not re-uploaded for nothing.
    """
    rc, out = git("diff", "--name-only", f"{since}...origin/main")
    if rc != 0:
        die(f"could not diff against {since}: {out}")
    files = []
    for path in out.splitlines():
        path = path.strip()
        folder = path.split("/")[0] if "/" in path else ""
        if folder in COLLECTIONS and path.endswith(".md") and (REPO / path).is_file():
            files.append(path)
    return sorted(set(files))


def remote_sizes(collection):
    data, err = api(f"/api/tenant-knowledge-base/collections/{collection}/files")
    if err:
        return {}, err
    return {f["fileName"]: f.get("fileSize") for f in (data or [])}, None


def multipart(paths):
    """Build a multipart body by hand - stdlib only, no requests.

    The mime type is explicit on purpose: without it curl and urllib send
    application/octet-stream, which lands in the file record and makes the collection
    inconsistent with anything uploaded through the Foundry UI.
    """
    boundary = "----foundrykb" + os.urandom(8).hex()
    parts = []
    for p in paths:
        parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="files"; filename="{Path(p).name}"\r\n'
            f"Content-Type: text/markdown\r\n\r\n".encode()
            + (REPO / p).read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def preflight(paths):
    r = subprocess.run([sys.executable, str(REPO / "scripts" / "preflight_upload.py"), *paths],
                       cwd=REPO, capture_output=True, text=True, timeout=180)
    return r.returncode, (r.stdout + r.stderr).strip()


def verify(collection, path):
    """Ask the retriever for text that is in the file, and report whether it comes back."""
    body = (REPO / path).read_text(encoding="utf-8", errors="replace")
    probe = next((ln.strip("# ").strip() for ln in body.splitlines()
                  if ln.startswith("#") and len(ln.strip()) > 12), Path(path).stem)
    data, err = api("/api/tenant-knowledge-base/retrieve", "POST", {
        "query": probe, "numberOfResults": 5, "searchType": "HYBRID",
        "filterCollectionNames": [collection]})
    if err:
        return None, err
    hits = [r for r in (data or [])
            if Path(path).name in str(r.get("metadata", {})
                                      .get("x-amz-bedrock-kb-source-uri", ""))]
    empty = [r for r in hits if not (r.get("content") or "")]
    return {"probe": probe, "hits": len(hits), "empty": len(empty),
            "any_results": len(data or [])}, None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--since", default="origin/main@{1}",
                    help="what to diff against to find changed files "
                         "(default: main as of your previous fetch)")
    ap.add_argument("--files", nargs="*", help="explicit files instead of the git diff")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    ap.add_argument("--timeout-min", type=int, default=15)
    a = ap.parse_args()

    if not KEY:
        die("FOUNDRY_API_KEY is not set. Open a terminal where it is available and re-run.\n"
            "       macOS:   see CLAUDE.md - it lives in the login keychain\n"
            "       Windows: see CLAUDE.md - a DPAPI-encrypted file under %LOCALAPPDATA%")

    print("Checking access…")
    _, err = api("/api/transcripts/agents")
    if err:
        die(f"cannot reach Foundry: {err}")
    print("  ok")

    git("fetch", "--quiet", "origin", "main")
    files = a.files or changed_knowledge_files(a.since)
    if not files:
        print("\nNothing to publish — no knowledge files changed on main.")
        print("Reviews alone never need uploading; they are not agent knowledge.")
        return 0

    # file -> collections
    plan = {}
    for f in files:
        plan[f] = COLLECTIONS[f.split("/")[0]]
    print(f"\n{len(files)} file(s) would go to Foundry:")
    for f, cols in plan.items():
        print(f"  {f}\n      -> {', '.join(cols)}")

    rc, out = preflight(files)
    if rc != 0:
        die("these files are NOT identical to origin/main, so they are not merged yet.\n"
            "       Nothing reaches Foundry until it is merged - see hard rule 5.\n\n" + out)
    print("\nAll files match origin/main (merged). ok")

    # Skip anything already the right size remotely; re-uploading is harmless but pointless.
    work = {}
    for f, cols in plan.items():
        local = (REPO / f).stat().st_size
        for c in cols:
            sizes, err = remote_sizes(c)
            if err:
                die(f"could not list {c}: {err}")
            if sizes.get(Path(f).name) == local:
                print(f"  unchanged in {c}: {Path(f).name}")
                continue
            work.setdefault(c, []).append(f)
    if not work:
        print("\nEverything is already in sync. Nothing to do.")
        return 0

    print("\nTo upload:")
    for c, fs in work.items():
        print(f"  {c}: {', '.join(Path(f).name for f in fs)}")

    if a.dry_run:
        print("\n--dry-run: stopping here, nothing was written.")
        return 0

    if not a.yes:
        print("\nThis changes what live agents tell users.")
        try:
            if input("Type 'yes' to upload: ").strip().lower() != "yes":
                print("Cancelled. Nothing was written.")
                return 1
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled. Nothing was written.")
            return 1

    # ---- upload everything first, in batches of 10 (the API's per-request limit) ----
    for c, fs in work.items():
        for i in range(0, len(fs), 10):
            batch = fs[i:i + 10]
            raw, ctype = multipart(batch)
            data, err = api(f"/api/tenant-knowledge-base/collections/{c}/files",
                            "POST", raw=raw, ctype=ctype, timeout=300)
            if err:
                die(f"upload to {c} failed: {err}")
            print(f"  uploaded {len(batch)} file(s) to {c}")

    # ---- then ONE sync, retried past the transient Bedrock job conflict ----
    print("\nStarting one ingestion job for everything…")
    job = None
    for attempt in range(6):
        data, err = api("/api/tenant-knowledge-base/sync", "POST", body={})
        if not err and (data or {}).get("jobId"):
            job = data["jobId"]
            break
        # A genuine intermittent 500 on a Bedrock job conflict; retrying is correct here,
        # unlike the Content-Type error which no amount of retrying fixes.
        print(f"  sync not started ({err or 'no jobId'}), retrying in 45s")
        time.sleep(45)
    if not job:
        print("  could not start a job. The uploads themselves auto-trigger a scoped sync,")
        print("  so this is usually recoverable — check status in a few minutes.")
    else:
        print(f"  job {job}")

    # ---- verify by RETRIEVAL, which is the signal that matters ----
    print(f"\nVerifying by retrieval (up to {a.timeout_min} min)…")
    deadline = time.time() + a.timeout_min * 60
    pending = [(c, f) for c, fs in work.items() for f in fs]
    good = []
    while pending and time.time() < deadline:
        still = []
        for c, f in pending:
            res, err = verify(c, f)
            if err or not res:
                still.append((c, f))
                continue
            if res["hits"] and not res["empty"]:
                print(f"  OK   {c}: {Path(f).name} — {res['hits']} chunk(s) retrievable")
                good.append((c, f))
            else:
                still.append((c, f))
        pending = still
        if pending:
            time.sleep(20)

    print()
    if pending:
        for c, f in pending:
            print(f"  NOT YET  {c}: {Path(f).name}")
        print("\nRetrieval usually catches up within ~6 minutes; past ~30 it is a real problem.")
        print("Re-run this to check again, or:  python3 scripts/check_foundry_drift.py")
        print("Do NOT mark transcripts pushed until these verify.")
        return 1

    print(f"All {len(good)} upload(s) verified live in Foundry.")
    print("\nNext:")
    print("  python3 scripts/check_foundry_drift.py     confirm the repo and Foundry agree")
    print("  python3 scripts/mark_pushed.py             close out the transcripts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
