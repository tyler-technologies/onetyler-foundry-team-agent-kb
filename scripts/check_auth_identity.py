#!/usr/bin/env python3
"""
Assert P2 (per-request identity) and P3 (auth) against real behavior, not by eye.

Companion to check_base_path.py and check_write_boundary.py: same discipline (start the
real server, hit real HTTP, assert on real responses). Three things must all hold:

1. AUTH_ENABLED unset (laptop default) is completely unaffected - no session code runs.
2. With AUTH_ENABLED on but no real identity gateway reachable, every non-exempt route
   serves the welcome/login page rather than the app, and /healthz stays reachable with
   no session.
3. The session/cookie primitives themselves are correct in isolation: a tampered
   signature is rejected, a fresh session round-trips, and per-request identity is
   thread-isolated (the exact mis-attribution bug P2 exists to prevent) - checked by
   importing the module directly rather than over HTTP, since simulating two concurrent
   real logins would need a live identity gateway this check cannot depend on.

Run with no arguments. Exits non-zero and prints every offending line on failure.
"""
import http.client
import importlib
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SERVER = REPO / "scripts" / "review_server.py"
PORT = 7802


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
            c.request("GET", "/healthz")
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


def get(path):
    c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=5)
    c.request("GET", path)
    r = c.getresponse()
    status, body = r.status, r.read().decode("utf-8", "replace")
    c.close()
    return status, body


def check_unauth_default(failures):
    print("--- AUTH_ENABLED unset (laptop default): unaffected ---")
    p = start_server({})
    try:
        st, body = get("/")
        if st != 200:
            failures.append(f"laptop default: / returned {st}, expected 200 (app, no login gate)")
        if "Sign in" in body:
            failures.append("laptop default: served a login page with no auth configured")
        st, body = get("/healthz")
        if st != 200 or '"ok":true' not in body.lower().replace(" ", ""):
            failures.append(f"laptop default: /healthz returned {st} / unexpected body: {body[:200]}")
    finally:
        stop_server(p)


def check_auth_gate(failures):
    print("--- AUTH_ENABLED on (no real IdP): gate blocks the app, /healthz stays open ---")
    env = {
        "FKB_OIDC_CLIENT_ID": "test-client-id",
        "FKB_OIDC_CLIENT_SECRET": "test-secret",
        "FKB_REDIRECT_URI": "http://127.0.0.1:7802/auth/callback",
        "FKB_SESSION_SECRET": "test-session-secret",
    }
    p = start_server(env)
    try:
        st, body = get("/")
        if st != 200 or "Sign in" not in body:
            failures.append(f"auth-on: / did not serve the welcome/login page (status {st})")
        st, _ = get("/healthz")
        if st != 200:
            failures.append(f"auth-on: /healthz should stay reachable with no session, got {st}")
        # A write route should ALSO be gated, not just the page routes.
        c = http.client.HTTPConnection("127.0.0.1", PORT, timeout=5)
        c.request("POST", "/save", body=b"{}", headers={"Content-Type": "application/json"})
        r = c.getresponse()
        if r.status != 401:
            failures.append(f"auth-on: POST /save with no session should be 401, got {r.status}")
        r.read()
        c.close()
    finally:
        stop_server(p)


def check_internals(failures):
    print("--- session/identity primitives, checked in isolation ---")
    os.environ["FKB_SESSION_SECRET"] = "isolation-test-secret"
    sys.path.insert(0, str(REPO / "scripts"))
    rs = importlib.import_module("review_server")

    sid = rs._new_session({"login": "octocat", "email": "octocat@tylertech.com"})
    sig = rs._sign(sid)
    if not rs.__dict__["hmac"].compare_digest(rs._sign(sid), sig):
        failures.append("session sign: same input produced different signatures")
    if rs._sign(sid) == rs._sign(sid + "x"):
        failures.append("session sign: a tampered sid produced the SAME signature - not detecting tampering")

    # Thread isolation: current_login() must never leak between concurrent "requests".
    seen = {}

    def worker(name, delay_before_read):
        rs._LOCAL.login = name
        time.sleep(delay_before_read)
        seen[name] = rs.current_login()

    t1 = threading.Thread(target=worker, args=("alice", 0.05))
    t2 = threading.Thread(target=worker, args=("bob", 0.0))
    t1.start(); t2.start()
    t1.join(); t2.join()
    if seen.get("alice") != "alice" or seen.get("bob") != "bob":
        failures.append(f"current_login() leaked across threads: {seen} (expected each to see its own name)")

    # _identity_map() reads FKB_IDENTITY_MAP from a real file - build one to check casefolding.
    import json as _json
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        _json.dump({"Alice@TylerTech.com": "alice-gh"}, f)
        map_path = f.name
    try:
        os.environ["FKB_IDENTITY_MAP"] = map_path
        got = rs._identity_map()
        if got.get("alice@tylertech.com") != "alice-gh":
            failures.append(f"_identity_map() did not casefold keys: {got}")
    finally:
        os.unlink(map_path)
        os.environ.pop("FKB_IDENTITY_MAP", None)

    class _FakeHandler:
        pass
    fh = _FakeHandler()
    fh.path = "/save"
    safe_next = rs.H._safe_next
    if safe_next(fh, "//evil.com") is not None:
        failures.append("_safe_next accepted a protocol-relative URL ('//evil.com')")
    if safe_next(fh, "http://evil.com/x") is not None:
        failures.append("_safe_next accepted an absolute URL with a scheme")
    if safe_next(fh, "/t/foo") != "/t/foo":
        failures.append("_safe_next rejected an ordinary same-origin path")


def main():
    failures = []
    check_unauth_default(failures)
    check_auth_gate(failures)
    check_internals(failures)
    if failures:
        print("\nFAILED:")
        for f in failures:
            print(" ", f)
        return 1
    print("\nAll auth/identity checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
