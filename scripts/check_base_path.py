#!/usr/bin/env python3
"""
Assert FKB_BASE_PATH support in review_server.py, mechanically rather than by eye.

Two things must both hold, or hosting this app under a path prefix (e.g. /FART) breaks
silently: every link/form/fetch the server emits must carry the prefix, and a request
missing the prefix must get nothing back. A single missed link is a dead control - see
the hosting doc's own warning - so this is checked by parsing the actual HTTP responses,
not by grepping source.

Run with no arguments. Exits non-zero and prints every offending line on failure.
"""
import http.client
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SERVER = REPO / "scripts" / "review_server.py"
PORT = 7799
BASE = "/FART"

# Captures the actual quoted value after href=/action=/src=/fetch(/location.href= so
# the caller can compare it against the configured prefix, rather than just noticing
# that *some* absolute path was emitted (which is normal - it just has to carry BASE).
VALUE_RE = re.compile(
    r"""(?:href|action|src)=(?P<q1>["'])(?P<v1>/[^"']*)(?P=q1)"""
    r"""|fetch\((?P<q2>["'])(?P<v2>/[^"']*)(?P=q2)"""
    r"""|location\.href\s*=\s*(?P<q3>["'])(?P<v3>/[^"']*)(?P=q3)"""
)


def start_server(env_extra):
    env = os.environ.copy()
    env.update(env_extra)
    env["FKB_NO_BROWSER"] = "1"
    p = subprocess.Popen(
        [sys.executable, str(SERVER), "--port", str(PORT), "--no-browser"],
        env=env, cwd=str(REPO),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    # Poll for the port rather than a fixed sleep - startup does a `gh api user` call.
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=1)
            c.request("GET", "/")
            c.getresponse().read()
            c.close()
            return p
        except (ConnectionRefusedError, OSError):
            if p.poll() is not None:
                out = p.stdout.read()
                raise RuntimeError(f"server exited early:\n{out}")
            time.sleep(0.3)
    p.kill()
    raise RuntimeError("server never came up")


def stop_server(p):
    p.send_signal(signal.SIGTERM)
    try:
        p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        p.kill()


def get(path):
    # /prs shells out to `gh pr list` live - budget for real network latency, not just
    # loopback overhead.
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=30)
    c.request("GET", path)
    r = c.getresponse()
    body = r.read().decode("utf-8", "replace")
    c.close()
    return r.status, body


def check_prefixed_pages(prefix):
    pages = [prefix + p for p in
             ("/", "/?all=1", "/save", "/publish", "/prs", "/analytics",
              "/backups", "/evalreview", "/logo.svg")]
    # A live PR diff and a live transcript detail page - both dynamically-built pages
    # that turned out to hide their own un-prefixed links on the first pass.
    _, listing = get(prefix + "/?all=1")
    m = re.search(r"data-href=\"" + re.escape(prefix) + r"(/t/[^\"]+)\"", listing)
    if m:
        pages.append(prefix + m.group(1))
    m = re.search(r"href=[\"']" + re.escape(prefix) + r"(/prs\?diff=\d+[^\"']*)[\"']", listing)
    if not m:
        _, prs_body = get(prefix + "/prs")
        m = re.search(r"href=[\"']" + re.escape(prefix) + r"(/prs\?diff=\d+[^\"']*)[\"']", prs_body)
    if m:
        pages.append(prefix + m.group(1))
    offenders = []
    for path in pages:
        status, body = get(path)
        if status not in (200, 404):
            offenders.append(f"{path}: unexpected status {status}")
            continue
        if status != 200:
            continue
        for m in VALUE_RE.finditer(body):
            value = m.group("v1") or m.group("v2") or m.group("v3")
            if value.startswith("//"):
                continue  # protocol-relative external URL, not ours to prefix
            if value.startswith(prefix + "/") or value == prefix:
                continue
            frag = body[max(0, m.start() - 10):m.start() + 60]
            offenders.append(f"{path}: {frag!r}")
    return offenders


def check_unprefixed_refused(prefix):
    """A request that misses the prefix must get nothing usable back."""
    offenders = []
    for path in ("/", "/save", "/publish", f"{prefix}evil", prefix.lower()
                 if prefix != prefix.lower() else prefix + "x"):
        status, _ = get(path)
        if status != 404:
            offenders.append(f"{path}: expected 404 outside the base path, got {status}")
    return offenders


def snapshot(prefix, paths):
    out = {}
    for p in paths:
        status, body = get(prefix + p)
        out[p] = (status, body)
    return out


def main():
    failures = []

    print(f"--- starting with FKB_BASE_PATH={BASE} ---")
    p = start_server({"FKB_BASE_PATH": BASE})
    try:
        offenders = check_prefixed_pages(BASE)
        if offenders:
            failures.append(("un-prefixed link/action/fetch emitted", offenders))
        offenders = check_unprefixed_refused(BASE)
        if offenders:
            failures.append(("request outside the base path was answered", offenders))
    finally:
        stop_server(p)

    print("--- starting with FKB_BASE_PATH unset (laptop default) ---")
    p = start_server({"FKB_BASE_PATH": ""})
    try:
        before = snapshot("", ["/", "/save", "/publish", "/analytics"])
    finally:
        stop_server(p)

    # Re-run the same probe against a build from before this change, if a snapshot
    # was captured; otherwise just assert internal consistency (200s, no crash).
    for path, (status, body) in before.items():
        if status != 200:
            failures.append((f"unset-BASE {path} did not return 200", [str(status)]))

    if failures:
        print("\nFAILED:")
        for title, offenders in failures:
            print(f"  {title}:")
            for o in offenders:
                print(f"    {o}")
        return 1

    print("\nAll base-path checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
