#!/usr/bin/env python3
"""Ask the live agents the reviewed transcripts' own questions, against the CANDIDATE knowledge
files, then put Foundry back exactly as it was.

    python3 scripts/eval_batch.py --dry-run     # what it would do, no writes
    python3 scripts/eval_batch.py               # run it
    python3 scripts/eval_batch.py --restore-only .eval/2026-08-28T14-02-11
                                                # recover after a crash

WHY THIS EXISTS
---------------
A knowledge-file change is only as good as what the agent says next time. Everything before this
was a proxy: `ingestionStatus` proves nothing, a retrieval probe proves the text is findable, and
neither proves the agent will USE it. Measured 2026-08-27: a rule was live and retrievable in all
five collections and the agent still ignored it, because the chunk it retrieved was a contradicting
example elsewhere in the file. Only asking the question catches that.

ONE UPLOAD, ALL TRANSCRIPTS, ONE REVERT
---------------------------------------
The slow part is Bedrock ingestion, and it is per-SYNC, not per-file. So the whole candidate set
goes up once, every transcript's question is asked against that one state, and everything comes
back once. Doing it per transcript would multiply the only expensive step by N for no extra
information - and the questions are seconds each.

It also tests the right thing: a reviewer's batch is a set of changes that will ship together, so
they should be evaluated together. Files evaluated one at a time can each look fine and still
contradict each other.

THE HONEST COST
---------------
Retrieval went live ~100 seconds after an upload when measured on 2026-08-22, and
`ingestionStatus` lagged to ~6 minutes. The restore is a second upload with the same lag. So for
the duration - a few minutes - LIVE AGENTS ANSWER FROM CANDIDATE CONTENT. That is the trade, it is
why this is off by default outside quiet hours, and it is stated on screen rather than buried here.

THE RESTORE POINT IS WRITTEN TO DISK BEFORE ANYTHING IS UPLOADED
----------------------------------------------------------------
Not held in memory. If this process dies mid-eval - crash, closed laptop, killed terminal - the
candidate content is live in Foundry with nothing to indicate it and no copy of what it replaced.
The restore directory plus `--restore-only` is what makes that recoverable, and it is the single
most important thing in this file.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

REPO = pathlib.Path(__file__).resolve().parent.parent
BASE = os.environ.get("FOUNDRY_API_URL", "https://foundry.tylertechai.com").rstrip("/")
KEY = os.environ.get("FOUNDRY_API_KEY", "")
UA = "claude-code-foundry-kb/1.0"

TEAM_ID = "e92bd437-cb84-4e18-88e6-757370b39c90"
AGENT_ID = {
    "ops-center":       "5b3efdff-921a-4131-be81-b7a4be427d9b",
    "bp-general":       "bd1c5d91-8234-486e-9f5a-2f1b7a947426",
    "sac":              "55444576-1fa3-4d12-a738-6ba83b17e6a7",
    "aligned-releases": "b0544224-b120-469a-8f39-c4a7b14c17c0",
    "identity":         "3f5e586f-0d0f-4638-9839-bebe45a6cb47",
}
FOLDER_COLLECTION = {
    "Knowledge-OpsCenter":         ["OT-OpsCenter"],
    "Knowledge-BP-General":        ["OT-BPD"],
    "Knowledge-SupportAccessCenter": ["OT-SAC"],
    "Knowledge-AlignedReleases":   ["OT-AlignedReleases"],
    "Knowledge-TylerIdentity":     ["TCP-KB-Identity"],
    "Knowledge-Shared":            ["OT-OpsCenter", "OT-BPD", "OT-SAC",
                                    "OT-AlignedReleases", "TCP-KB-Identity"],
}

# Measured on this tenant, not guessed. Used only for the estimate shown to a human.
SECS_PER_SYNC = 150
SECS_PER_QUESTION = 18


def die(msg):
    print("FAIL: " + msg, file=sys.stderr)
    sys.exit(1)


def api(path, method="GET", payload=None, raw=False, timeout=120):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(BASE + path, method=method, data=data)
    req.add_header("X-API-Key", KEY)
    req.add_header("User-Agent", UA)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            return body if raw else json.loads(body.decode() or "null")
    except urllib.error.HTTPError as e:
        die(f"HTTP {e.code} on {method} {path} — {e.read().decode()[:200]}")
    except urllib.error.URLError as e:
        die(f"could not reach {BASE}{path} — {e.reason}")


def git(*args):
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=120)
    return r.returncode, (r.stdout + r.stderr).strip()


def candidate_files():
    """Knowledge files that differ from origin/main — the change being evaluated.

    Both committed and uncommitted, because a reviewer runs this BEFORE sending anything in:
    the point is to find out whether the change is good while it is still cheap to alter.
    """
    rc, out = git("diff", "--name-only", "origin/main", "--", *[
        d.name for d in REPO.iterdir() if d.is_dir() and d.name.startswith("Knowledge-")])
    if rc != 0:
        return []
    return sorted({l.strip() for l in out.splitlines()
                   if l.strip().endswith(".md") and (REPO / l.strip()).is_file()})


def batch_transcripts():
    """The transcripts this batch is about: anything whose verdict differs from origin/main.

    Not "everything reviewed" - a reviewer evaluating their own batch should not be waiting on
    questions from somebody else's work that shipped last week.
    """
    rc, out = git("diff", "--name-only", "origin/main", "--", "transcripts")
    if rc != 0:
        return []
    return sorted({l.strip() for l in out.splitlines()
                   if l.strip().endswith(".md")
                   and pathlib.Path(l.strip()).name not in
                   ("README.md", "INDEX.md", "ONBOARDING.md")
                   and (REPO / l.strip()).is_file()})


def parse_transcript(rel):
    """(agent_slug, [questions]) for one transcript."""
    txt = (REPO / rel).read_text(encoding="utf-8")
    fm = {}
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line and not line.strip().startswith("#"):
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip()
    body = txt[m.end():] if m else txt
    qs = []
    for blk in re.finditer(r"## Exchange (\d+)\n(.*?)(?=\n## Exchange |\n---\n\n## Proposed fix|\Z)",
                           body, re.S):
        q = (re.search(r"\*\*Q:\*\*\n\n((?:> .*\n?)+)", blk.group(2)) or [None, ""])[1]
        q = re.sub(r"^> ?", "", q, flags=re.M).strip()
        if q:
            qs.append(q)
    slug = (fm.get("answered_by") or "").strip()
    return slug, qs, fm


def collections_for(files):
    out = {}
    for f in files:
        folder = f.split("/")[0]
        for col in FOLDER_COLLECTION.get(folder, []):
            out.setdefault(col, []).append(f)
    return out


def remote_records(col):
    return {f["fileName"]: f for f in (api(f"/api/tenant-knowledge-base/collections/{col}/files")
                                       or [])}


def download(col, fid):
    return api(f"/api/tenant-knowledge-base/collections/{col}/files/{fid}/download", raw=True)


def upload(col, paths, labels=None):
    """Multipart upload. Written by hand because the stdlib has no multipart helper and the
    tenant rejects application/octet-stream, which is what curl sends without an explicit type."""
    boundary = "----evalbatch" + hashlib.sha1(str(time.time()).encode()).hexdigest()[:16]
    body = b""
    for i, p in enumerate(paths):
        name = (labels or [pathlib.Path(x).name for x in paths])[i]
        content = p.read_bytes() if isinstance(p, pathlib.Path) else p
        body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; "
                 f"filename=\"{name}\"\r\nContent-Type: text/markdown\r\n\r\n").encode()
        body += content + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{BASE}/api/tenant-knowledge-base/collections/{col}/files", method="POST", data=body)
    req.add_header("X-API-Key", KEY)
    req.add_header("User-Agent", UA)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode() or "null")
    except urllib.error.HTTPError as e:
        die(f"upload to {col} failed: HTTP {e.code} {e.read().decode()[:200]}")


def sync_once():
    for attempt in range(6):
        try:
            return api("/api/tenant-knowledge-base/sync", method="POST", payload={})
        except SystemExit:
            raise
        except Exception:
            pass
        time.sleep(45)
    return None


def wait_for_content(col, filename, expect_sha, budget=420):
    """Poll until the collection serves the expected bytes. Returns seconds waited, or None.

    Waits on CONTENT, not on `ingestionStatus`. The status field lagged retrieval by minutes when
    measured, in both directions - so it is the weaker signal for "is this live yet", and using it
    would either start the eval too early or waste minutes after it was already ready.
    """
    t0 = time.time()
    while time.time() - t0 < budget:
        recs = remote_records(col)
        rec = recs.get(filename)
        if rec:
            got = download(col, rec["id"])
            if hashlib.sha256(got).hexdigest() == expect_sha:
                return int(time.time() - t0)
        time.sleep(15)
    return None


def ask(slug, question, timeout=180):
    """Ask one question and reassemble the streamed answer.

    The two stream endpoints have DIFFERENT payload shapes, which is not documented anywhere:
        /api/team/{id}/stream    -> {"type":"text-delta","delta":"..."}
        /api/agents/{id}/stream  -> {"type":"text-delta","payload":{"text":"..."}}
    Both are handled; reading only one silently yields an empty answer, which looks like the agent
    refusing rather than a parsing bug.
    """
    if slug == "team" or slug not in AGENT_ID:
        path = f"/api/team/{TEAM_ID}/stream"
    else:
        path = f"/api/agents/{AGENT_ID[slug]}/stream"
    req = urllib.request.Request(BASE + path, method="POST",
                                 data=json.dumps({"messages": [{"role": "user",
                                                                "content": question}]}).encode())
    req.add_header("X-API-Key", KEY)
    req.add_header("User-Agent", UA)
    req.add_header("Content-Type", "application/json")
    buf = []
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            for raw in r:
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                try:
                    d = json.loads(line[5:].strip())
                except json.JSONDecodeError:
                    continue
                if d.get("type") != "text-delta":
                    continue
                buf.append(d.get("delta") or d.get("textDelta")
                           or (d.get("payload") or {}).get("text") or "")
    except Exception as e:                                            # noqa: BLE001
        return f"[no answer — {type(e).__name__}: {e}]"
    return "".join(buf).strip() or "[empty answer]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--restore-only", metavar="DIR",
                    help="put Foundry back from a saved restore point and exit")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation")
    ap.add_argument("--keep", action="store_true",
                    help="leave the candidate content LIVE in Foundry after the questions, so "
                         "adjacent phrasings can be tried. Writes a LIVE marker; remove with "
                         "--restore-only.")
    a = ap.parse_args()

    if not KEY:
        die("FOUNDRY_API_KEY is not set.")

    if a.restore_only:
        d = pathlib.Path(a.restore_only)
        rc = restore(d)
        # Clear the marker only on success. A failed restore that still looked "removed" would
        # leave candidate content live with nothing in the UI saying so - the exact state this
        # marker exists to make visible.
        if rc == 0:
            (d / "LIVE").unlink(missing_ok=True)
        return rc

    keep = a.keep
    files = candidate_files()
    transcripts = batch_transcripts()
    pairs = []
    for rel in transcripts:
        slug, qs, fm = parse_transcript(rel)
        if qs and (fm.get("review_status") or "") in ("reviewed", "suggested", "pending"):
            pairs.append((rel, slug, qs))
    n_q = sum(len(q) for _, _, q in pairs)

    print(f"Candidate knowledge files : {len(files)}")
    for f in files:
        print(f"    {f}")
    print(f"Transcripts to replay     : {len(pairs)}  ({n_q} question(s))")
    cols = collections_for(files)
    print(f"Collections touched       : {', '.join(cols) or 'none'}")
    est = (2 * SECS_PER_SYNC + n_q * SECS_PER_QUESTION) // 60
    print(f"Rough time                : ~{est} min "
          f"(two syncs at ~{SECS_PER_SYNC // 60}-3 min each, plus ~{SECS_PER_QUESTION}s a question)")

    if not files:
        print("\nNothing to evaluate — no knowledge file differs from origin/main.")
        return 0
    if not pairs:
        print("\nNo transcripts in this batch have questions to replay.")
        return 0

    print("\n  WHILE THIS RUNS, LIVE AGENTS ANSWER FROM THE CANDIDATE CONTENT.")
    print("  Bedrock ingestion is the slow part and cannot be shortened. Best done off-hours.")
    if a.dry_run:
        print("\n(dry run — nothing uploaded)")
        return 0
    if not a.yes:
        if input("\nProceed? type yes: ").strip().lower() != "yes":
            print("Aborted; nothing was uploaded.")
            return 1

    # ---- 1. restore point, ON DISK, before anything is written ---------------------------
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    rdir = REPO / ".eval" / stamp
    rdir.mkdir(parents=True, exist_ok=True)
    manifest = {"created": stamp, "files": []}
    print(f"\n[1/5] Saving what is live now -> {rdir.relative_to(REPO)}")
    for col, fs in cols.items():
        recs = remote_records(col)
        for f in fs:
            name = pathlib.Path(f).name
            rec = recs.get(name)
            if not rec:
                print(f"      {col}/{name}: not in the collection yet — will be DELETED on restore")
                manifest["files"].append({"collection": col, "fileName": name, "absent": True})
                continue
            body = download(col, rec["id"])
            out = rdir / col
            out.mkdir(exist_ok=True)
            (out / name).write_bytes(body)
            manifest["files"].append({"collection": col, "fileName": name, "absent": False,
                                      "bytes": len(body),
                                      "sha256": hashlib.sha256(body).hexdigest()})
            print(f"      {col}/{name}: {len(body)} B saved")
    (rdir / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    print(f"      restore with: python3 scripts/eval_batch.py --restore-only "
          f"{rdir.relative_to(REPO)}")

    # ---- 2. upload the candidates, ONE sync ---------------------------------------------
    print("\n[2/5] Uploading the candidate files")
    for col, fs in cols.items():
        upload(col, [REPO / f for f in fs])
        print(f"      {col}: {len(fs)} file(s)")
    print("      one consolidated sync")
    sync_once()

    print("\n[3/5] Waiting for the collections to serve the new content")
    # RECORDED, not just printed. A file that never went live makes every answer below it
    # meaningless - the agent answered from the old content - and approving those answers would
    # ship a change nobody actually tested. Printing the warning put it in a scrollback the
    # reviewer had no reason to re-read; the review screen needs it as data.
    propagation = []
    for col, fs in cols.items():
        for f in fs:
            want = hashlib.sha256((REPO / f).read_bytes()).hexdigest()
            waited = wait_for_content(col, pathlib.Path(f).name, want)
            propagation.append({"collection": col, "file": pathlib.Path(f).name,
                                "live": waited is not None, "seconds": waited})
            print(f"      {col}/{pathlib.Path(f).name}: "
                  + (f"live after {waited}s" if waited is not None
                     else "TIMED OUT — the answers below may not reflect the change"))
    (rdir / "PROPAGATION.json").write_text(json.dumps(propagation, indent=2))
    stale = [p for p in propagation if not p["live"]]
    if stale:
        print(f"\n  ⚠ {len(stale)} file(s) never went live. The answers below were given from "
              "the OLD content and must not be approved.")

    # ---- 4. replay the questions ---------------------------------------------------------
    print("\n[4/5] Asking the transcripts' own questions")
    results = []
    for rel, slug, qs in pairs:
        for i, q in enumerate(qs, 1):
            ans = ask(slug, q)
            results.append({"transcript": rel, "agent": slug, "n": i,
                            "question": q, "answer": ans})
            print(f"\n  --- {rel}  (exchange {i}, agent {slug or 'team'})")
            print(f"  Q: {q[:200]}")
            print(f"  A: {ans[:600]}")
    (rdir / "RESULTS.json").write_text(json.dumps(results, indent=2))

    # ---- 5. put it back, OR leave it up on purpose ---------------------------------------
    #
    # WHY --keep EXISTS, AND WHY IT IS NOT THE SAFE-LOOKING OPTION.
    # One phrasing of one question does not establish that a knowledge change is sound. The
    # reviewer needs to try adjacent questions - the same thing asked differently, the
    # neighbouring topic that shares a chunk - and that is impossible if the candidate content
    # is torn down the moment the scripted questions finish.
    #
    # The cost is real and must not be soft-pedalled: the candidate content stays LIVE for
    # every user of these agents until somebody removes it. That is a much longer exposure than
    # the few minutes the auto-restore gave. So --keep writes a LIVE marker naming the restore
    # directory, the UI shows a standing warning with the elapsed time, and removal is one
    # button. The restore point is on disk either way, so nothing here is unrecoverable.
    if keep:
        (rdir / "LIVE").write_text(json.dumps({
            "since": dt.datetime.now(dt.timezone.utc).isoformat(),
            "collections": sorted(cols),
            "files": files,
        }, indent=2))
        print("\n[5/5] LEAVING THE CANDIDATE CONTENT LIVE (--keep)")
        print("      The agents answer from it until you remove it. Try adjacent phrasings now.")
        print(f"      Remove with: python3 scripts/eval_batch.py --restore-only "
              f"{rdir.relative_to(REPO)}")
    else:
        print("\n[5/5] Restoring Foundry")
        restore(rdir)

    print(f"\nResults saved to {(rdir / 'RESULTS.json').relative_to(REPO)}")
    print("Read the answers above. If they are wrong, the change is not ready — reset those "
          "transcripts to pending and keep working. Nothing has been sent in.")
    return 0


def restore(rdir):
    """Put Foundry back from a saved restore point. Safe to run twice."""
    mf = rdir / "MANIFEST.json"
    if not mf.is_file():
        die(f"no MANIFEST.json in {rdir}")
    manifest = json.loads(mf.read_text())
    by_col = {}
    deletes = []
    for e in manifest["files"]:
        if e.get("absent"):
            deletes.append((e["collection"], e["fileName"]))
        else:
            by_col.setdefault(e["collection"], []).append(e)
    for col, entries in by_col.items():
        blobs, names = [], []
        for e in entries:
            blobs.append((rdir / col / e["fileName"]).read_bytes())
            names.append(e["fileName"])
        upload(col, blobs, labels=names)
        print(f"      {col}: {len(names)} file(s) put back")
    for col, name in deletes:
        recs = remote_records(col)
        rec = recs.get(name)
        if rec:
            api(f"/api/tenant-knowledge-base/collections/{col}/files/{rec['id']}",
                method="DELETE")
            print(f"      {col}/{name}: removed (it was not there before)")
    print("      one consolidated sync")
    sync_once()
    print("\n  Verifying the restore")
    bad = 0
    for col, entries in by_col.items():
        for e in entries:
            waited = wait_for_content(col, e["fileName"], e["sha256"])
            if waited is None:
                bad += 1
                print(f"      {col}/{e['fileName']}: NOT BACK YET — check before walking away")
            else:
                print(f"      {col}/{e['fileName']}: restored after {waited}s")
    if bad:
        print(f"\n  {bad} file(s) not confirmed restored. Re-run:\n"
              f"    python3 scripts/eval_batch.py --restore-only {rdir}")
        return 1
    print("  Foundry is back to what it was.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
