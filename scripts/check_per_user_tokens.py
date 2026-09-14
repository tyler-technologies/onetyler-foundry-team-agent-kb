#!/usr/bin/env python3
"""
Assert _github_token_for()/_subprocess_env_for_login() pick the right credential per login,
in isolation (no subprocess, no network) - imports review_server directly.

Four things must hold:
1. A login with its own GH_TOKEN_FOR_<LOGIN> env var gets that token, not the shared one.
2. A login with no token of its own falls back to the shared GH_TOKEN/GITHUB_TOKEN -
   nothing breaks for a contributor who has not added their own yet.
3. No login at all (laptop/CLI, current_login() returns _STARTUP_ME which is usually None
   in a bare test) and no shared token either -> _subprocess_env_for_login() returns None,
   meaning "inherit the environment unchanged" - never touches os.environ itself.
4. Dashes in a GitHub login (e.g. jon-olson-tylertech) map to underscores in the env var
   name, since env var names cannot contain dashes.

Run with no arguments. Exits non-zero and prints every offending line on failure.
"""
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main():
    sys.path.insert(0, str(REPO / "scripts"))
    failures = []
    import review_server as rs

    saved_env = dict(os.environ)

    def reset_env():
        os.environ.clear()
        os.environ.update(saved_env)
        for k in list(os.environ):
            if k.startswith("GH_TOKEN") or k == "GITHUB_TOKEN":
                os.environ.pop(k, None)

    print("--- own token takes priority over the shared one ---")
    reset_env()
    os.environ["GH_TOKEN"] = "shared-token"
    os.environ["GH_TOKEN_FOR_JAYEXPRS"] = "jayexprs-own-token"
    got = rs._github_token_for("jayexprs")
    if got != "jayexprs-own-token":
        failures.append(f"expected jayexprs' own token, got {got!r}")
    else:
        print("    ok")

    print("--- falls back to the shared token when there is no per-user one ---")
    reset_env()
    os.environ["GH_TOKEN"] = "shared-token"
    got = rs._github_token_for("jon-olson-tylertech")
    if got != "shared-token":
        failures.append(f"expected the shared fallback token, got {got!r}")
    else:
        print("    ok")

    print("--- dashes in the login map to underscores in the env var name ---")
    reset_env()
    os.environ["GH_TOKEN_FOR_JON_OLSON_TYLERTECH"] = "jon-own-token"
    got = rs._github_token_for("jon-olson-tylertech")
    if got != "jon-own-token":
        failures.append(f"dash-to-underscore mapping did not find jon's token, got {got!r}")
    else:
        print("    ok")

    print("--- no token anywhere -> _subprocess_env_for_login() returns None (inherit as-is) ---")
    reset_env()
    rs.AUTH_ENABLED = False
    got = rs._subprocess_env_for_login()
    if got is not None:
        failures.append(f"expected None (inherit unchanged), got a dict: {got}")
    else:
        print("    ok")

    print("--- with a token present, returns a COPY, never mutates the real os.environ ---")
    reset_env()
    os.environ["GH_TOKEN"] = "shared-token"
    before = dict(os.environ)
    got = rs._subprocess_env_for_login()
    if got is None or got.get("GH_TOKEN") != "shared-token" or got.get("GITHUB_TOKEN") != "shared-token":
        failures.append(f"expected a dict with both GH_TOKEN and GITHUB_TOKEN set, got {got}")
    if dict(os.environ) != before:
        failures.append("_subprocess_env_for_login() mutated the real os.environ - it must not")
    else:
        print("    ok")

    reset_env()

    if failures:
        print("\nFAILED:")
        for f in failures:
            print(" ", f)
        return 1
    print("\nAll per-user token checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
