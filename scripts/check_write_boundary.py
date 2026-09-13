#!/usr/bin/env python3
"""
Assert FKB_READ_ONLY refuses every declared write route, mechanically rather than by eye.

Companion to check_base_path.py: same reasoning (assert against real HTTP responses, not
source), same "run with no arguments" contract. Checks two things that must both hold:
every route in WRITE_ROUTES gets 409 when FKB_READ_ONLY is on, and an unset FKB_READ_ONLY
(the laptop default) is completely unaffected.
"""
import http.client
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SERVER = REPO / "scripts" / "review_server.py"
PORT = 7801

WRITE_ROUTES = ("/save", "/publish", "/sync", "/csvimport", "/bulk",
                "/evalapprove", "/bk", "/pr", "/git")


def start_server(env_extra):
    env = os.environ.copy()
    env.update(env_extra)
    p = subprocess.Popen(
        [sys.executable, str(SERVER), "--port", str(PORT), "--no-browser"],
        env=env, cwd=str(REPO),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
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
    p.terminate()
    try:
        p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        p.kill()


def post(path, body=b"{}"):
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=5)
    c.request("POST", path, body=body, headers={"Content-Type": "application/json"})
    r = c.getresponse()
    status = r.status
    r.read()
    c.close()
    return status


def main():
    failures = []

    print("--- FKB_READ_ONLY=1 ---")
    p = start_server({"FKB_READ_ONLY": "1"})
    try:
        for path in WRITE_ROUTES:
            st = post(path)
            if st != 409:
                failures.append(f"{path}: expected 409 in read-only mode, got {st}")
    finally:
        stop_server(p)

    print("--- FKB_READ_ONLY unset (laptop default) ---")
    p = start_server({})
    try:
        st = post("/nonexistent-route-xyz")
        if st == 409:
            failures.append("unset FKB_READ_ONLY still returned 409 - default changed behavior")
    finally:
        stop_server(p)

    if failures:
        print("\nFAILED:")
        for f in failures:
            print(" ", f)
        return 1
    print("\nAll write-boundary checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
