#!/usr/bin/env python3
"""Start a review sitting. No AI, no terminal knowledge, no bash.

    python3 scripts/start.py        (macOS / Linux)
    python  scripts\\start.py        (Windows)

Or double-click `Start-reviewing.command` (macOS) / `Start-reviewing.bat` (Windows).

This exists because the reviewing half of this repo does not need an assistant. It brings the
repo up to date, pulls new conversations from Foundry, starts the review UI and opens it. Then
a reviewer reads transcripts, writes what the answer should have said, saves, and sends it in —
all in the browser.

Replaces `start_review_session.sh` for everyday use. Two reasons it is Python:
  - the team runs Windows as well as macOS, and the bash script needs Git Bash or WSL;
  - the bash script CREATES A BRANCH up front, which no longer matches how the UI works. The
    branch is now made on the first save of a sitting and never shown to the reviewer, so
    making one here would put them on a branch before they had anything to put on it.

WHAT THIS DELIBERATELY WILL NOT DO
----------------------------------
It never discards, stashes or resets anything. If the working tree is dirty it leaves the
branch alone and says so. That is not caution for its own sake: on 2026-08-27 a `git reset
--hard` in this repo destroyed a reviewer's unsaved verdicts, unrecoverably, because they were
never committed. A launcher that "tidies up" before starting is a launcher that eventually
eats somebody's afternoon.

Every step is allowed to fail without stopping the others. A missing `gh`, no network, or an
unset FOUNDRY_API_KEY should cost you the transcripts you would have fetched — not the review
UI you were trying to open.
"""
import argparse
import os
import shutil
import socket
import subprocess
import sys
import webbrowser
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PY = sys.executable or "python3"

# review_server.py needs 3.12+. It uses backslashes inside f-string expressions, which older
# interpreters reject at PARSE time - so the failure is a SyntaxError with a line number, not a
# message anyone can act on, and it happens before a single line of the server runs.
#
# macOS ships /usr/bin/python3 as 3.9.6. A contributor who has not installed a newer Python
# gets, in full:
#
#     File ".../scripts/review_server.py", line 2368
#       + (f"<div class=prbadge><a href=\"{html.escape(r['openpr']['url'])}\" "
#     SyntaxError: f-string expression part cannot include a backslash
#
# which reads as "the repo is broken", not "install a newer Python". Checked here because a
# guard cannot live in the file it protects: the SyntaxError fires on import, before any code
# in that module executes.
MIN_PY = (3, 12)


def check_python():
    if sys.version_info[:2] >= MIN_PY:
        return True
    have = ".".join(str(x) for x in sys.version_info[:3])
    want = ".".join(str(x) for x in MIN_PY)
    print(f"\n  This needs Python {want} or newer. You are running {have}"
          f"\n    ({sys.executable})\n"
          "\n  macOS ships 3.9, which cannot parse the review UI at all - it fails with a"
          "\n  SyntaxError before it starts, which looks like a broken repo rather than an old"
          "\n  interpreter.\n"
          "\n  Install a newer one and re-run this the same way:"
          "\n    macOS    brew install python@3.12"
          "\n    Windows  https://www.python.org/downloads/  (tick 'Add python.exe to PATH')"
          "\n"
          "\n  If you already have one, run this script with it explicitly:"
          "\n    /opt/homebrew/bin/python3 scripts/start.py\n", file=sys.stderr)
    return False


def say(msg=""):
    print(msg, flush=True)


def step(n, total, title):
    say()
    say(f"[{n}/{total}] {title}")


def run(args, **kw):
    """Run a command, returning (rc, combined output). Never raises."""
    try:
        r = subprocess.run(args, cwd=REPO, capture_output=True, text=True,
                           timeout=kw.pop("timeout", 300), **kw)
        return r.returncode, (r.stdout + r.stderr).strip()
    except FileNotFoundError:
        return 127, f"{args[0]} is not installed"
    except subprocess.TimeoutExpired:
        return 124, f"{args[0]} timed out"
    except Exception as e:                                    # noqa: BLE001
        return 1, str(e)


def git(*args, **kw):
    return run(["git", *args], **kw)


def indent(text, prefix="      "):
    for line in (text or "").splitlines():
        say(prefix + line)


# ---------------------------------------------------------------- steps

def update_repo():
    """Fast-forward main, but only when it is safe to do so."""
    rc, dirty = git("status", "--porcelain")
    if rc != 0:
        say("      could not read the repo state — skipping the update")
        indent(dirty)
        return
    rc, cur = git("rev-parse", "--abbrev-ref", "HEAD")
    cur = cur.strip()

    if dirty.strip():
        # The whole point of the docstring's warning. Leave everything exactly as it is.
        say("      you have unsaved work, so nothing was touched:")
        # lstrip each line, because run() strips the whole output and so eats the leading
        # space off the FIRST porcelain line only - which prints as a ragged list where one
        # entry is indented differently from the rest, for no visible reason.
        indent("\n".join(l.lstrip() for l in dirty.splitlines()[:8]), "        ")
        if len(dirty.splitlines()) > 8:
            say(f"        … and {len(dirty.splitlines()) - 8} more")
        say("      that is fine — carry on reviewing, or send in what you have first.")
        return

    if cur.startswith("review/"):
        say(f"      you are part-way through a sitting, so it was left alone")
        return

    rc, out = git("fetch", "--quiet", "origin", timeout=120)
    if rc != 0:
        say("      could not reach GitHub — working with the copy you already have")
        indent(out)
        return
    if cur != "main":
        rc, out = git("switch", "--quiet", "main")
        if rc != 0:
            say(f"      staying on {cur} — could not switch to the shared copy")
            indent(out)
            return
    rc, out = git("pull", "--quiet", "--ff-only", "origin", "main", timeout=120)
    if rc != 0:
        say("      could not fast-forward; someone may have rewritten history")
        indent(out)
        return
    _, at = git("log", "-1", "--format=%h %s")
    say(f"      up to date — {at.strip()[:78]}")


def sync_contributors():
    """Keep the reviewer list in step with the GitHub teams.

    A new contributor who is not in contributors.json cannot pick their own name in the UI and
    is stuck before they start, so this is worth attempting even though it needs `gh`.
    """
    if not shutil.which("gh"):
        say("      the GitHub CLI (gh) is not installed — skipping")
        say("      only matters if someone new joined the team")
        return
    rc, out = run([PY, str(REPO / "scripts" / "sync_contributors.py"), "--check"])
    if rc == 0:
        say("      the reviewer list matches the team")
        return
    rc, out = run([PY, str(REPO / "scripts" / "sync_contributors.py")])
    if rc != 0:
        say("      could not refresh the reviewer list:")
        indent(out)
        say("      if it mentions permissions, run:  gh auth refresh -s read:org")
        return
    say("      refreshed the reviewer list — remember to send this in with your reviews")


def fetch_transcripts():
    if not os.environ.get("FOUNDRY_API_KEY"):
        say("      FOUNDRY_API_KEY is not set, so nothing new was pulled")
        say("      you can still review everything already in the repo")
        return
    rc, out = run([PY, str(REPO / "scripts" / "fetch_transcripts.py")], timeout=600)
    interesting = [l for l in out.splitlines()
                   if l.startswith(("added:", "WARNING", "note:")) or "conversations" in l]
    indent("\n".join(interesting) or out.splitlines()[-1] if out else "")
    if rc != 0:
        say("      the fetch did not finish cleanly — the UI still works with what is here")


def status_line():
    rc, out = run([PY, str(REPO / "scripts" / "review_status.py")])
    for line in (out or "").splitlines():
        if any(k in line.lower() for k in ("pending", "reviewed", "suggested", "excluded")):
            return line.strip()
    return ""


def port_free(port):
    with socket.socket() as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) != 0


def main():
    ap = argparse.ArgumentParser(description="Start a transcript review sitting.")
    ap.add_argument("--port", type=int, default=7777)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--me", help="your GitHub username (normally detected for you)")
    a = ap.parse_args()

    # FIRST, before anything else runs. Every later step either shells out to a script that
    # would hit the same parse error, or prints progress that makes the eventual SyntaxError
    # look like it came from whatever step was on screen.
    if not check_python():
        return 1

    say("=" * 62)
    say("  OneTyler Foundry Team Agent — transcript review")
    say("=" * 62)

    total = 3
    step(1, total, "Bringing the repo up to date")
    update_repo()
    step(2, total, "Checking the reviewer list")
    sync_contributors()
    step(3, total, "Pulling new conversations from Foundry")
    fetch_transcripts()

    port = a.port
    if not port_free(port):
        # Almost always this script already running in another window. Say which, rather than
        # silently moving to another port and printing a URL that is not the one in the
        # instructions.
        say()
        say(f"  Port {port} is already in use.")
        say(f"  If the review UI is already open, use it: http://127.0.0.1:{port}")
        say(f"  Otherwise start on another port:  {Path(PY).name} scripts/start.py "
            f"--port {port + 1}")
        return 1

    counts = status_line()
    say()
    say("-" * 62)
    say(f"  Review UI:  http://127.0.0.1:{port}")
    if counts:
        say(f"  {counts}")
    say("  Loopback only — nothing leaves this machine, and the address")
    say("  will not work for anyone else.")
    say()
    say("  Leave this window open while you review. Ctrl-C to stop.")
    say("-" * 62)
    say()

    cmd = [PY, str(REPO / "scripts" / "review_server.py"), "--port", str(port),
           "--no-browser"]
    if a.me:
        cmd += ["--me", a.me]
    proc = subprocess.Popen(cmd, cwd=REPO)
    if not a.no_browser:
        # Wait for the port to answer BEFORE opening the tab. Opening it first shows a
        # connection error, and someone who sees that on their first run concludes the tool is
        # broken - the server takes a couple of seconds to bind because it reads git state on
        # startup.
        say("  Opening your browser…")
        up = False
        for _ in range(60):
            if not port_free(port):
                up = True
                break
            try:
                proc.wait(timeout=0.25)
                break                    # it exited; do not open a tab at a dead port
            except subprocess.TimeoutExpired:
                pass
        if up:
            opened = False
            try:
                opened = webbrowser.open(f"http://127.0.0.1:{port}")
            except Exception:            # noqa: BLE001
                opened = False
            if not opened:
                # webbrowser returns False on a headless box or when no handler is
                # registered. Say so plainly instead of leaving them waiting for a tab that
                # is never coming - the URL above is all they need.
                say("  Could not open a browser automatically — paste the address above "
                    "into one.")
        else:
            say("  The server did not start. Nothing was opened; see the messages above.")
    try:
        return proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        say()
        say("  Stopped. Your reviews are saved in files — nothing was lost.")
        say("  Run this again any time; anything you had not sent in is still there.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
