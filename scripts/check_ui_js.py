#!/usr/bin/env python3
"""Assert the review UI's JavaScript actually parses.

Why this exists. `review_server.py` holds its client-side JS in a Python string, and a plain
triple-quoted string eats backslash escapes before the browser ever sees them. On 2026-08-27
`alert('Skipped:\n')` was found to have become a REAL newline inside a single-quoted JS
literal. That is a SyntaxError, and a SyntaxError anywhere in a <script> block kills the whole
block - so every filter, every popover, the checkbox selection, the row-click handler and the
empty states were all inert on a page that looked completely normal.

It survived for days because the things people check are rendered SERVER-side. Row counts,
tile numbers and nav badges all come from Python, so the page reads as working. Nothing that
looked broken was broken; everything that was broken looked fine.

Two guards, because either alone would have missed it:
  1. The JS block must be a raw string, so JS owns its escapes.
  2. The emitted JS must parse. Uses `node --check` when node is available, and falls back to
     a brace/quote balance check when it is not, so this is never silently skipped.

    python3 scripts/check_ui_js.py
"""
import importlib.util
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent
SRC = REPO / "scripts" / "review_server.py"


def fail(msg):
    print(f"FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main():
    text = SRC.read_text(encoding="utf-8")

    # Guard 1 - the declaration itself.
    if not re.search(r"^JS = r\"\"\"", text, re.M):
        fail("scripts/review_server.py declares JS as a non-raw string.\n"
             "      Use `JS = r\"\"\"` — otherwise Python consumes JS escape sequences such as\n"
             "      \\n and \\t, which breaks JS string literals and silently kills the entire\n"
             "      <script> block. See the docstring in this file.")

    # Guard 2 - the emitted JS must parse. Import the module rather than re-deriving the
    # string, so this tests what the browser is actually served.
    sys.path.insert(0, str(REPO / "scripts"))
    spec = importlib.util.spec_from_file_location("review_server", SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    js = mod.JS

    node = shutil.which("node")
    if node:
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                         encoding="utf-8") as fh:
            fh.write(js)
            tmp = fh.name
        r = subprocess.run([node, "--check", tmp], capture_output=True, text=True)
        pathlib.Path(tmp).unlink(missing_ok=True)
        if r.returncode != 0:
            fail("the review UI's JavaScript does not parse — the whole <script> block "
                 "would be dead in the browser:\n" + (r.stderr or r.stdout).rstrip())
        print(f"UI JavaScript parses ({len(js)} bytes, checked with node).")
        return

    # No node. A newline inside a quoted literal is the specific failure this file exists
    # for, so check for it directly rather than reporting "skipped".
    bad = [i + 1 for i, line in enumerate(js.splitlines())
           if line.count("'") % 2 or line.count('"') % 2]
    if bad:
        fail("node is unavailable, and these emitted JS lines have an odd number of quotes, "
             "which usually means a string literal spans a newline: "
             f"{bad[:10]}")
    print(f"UI JavaScript looks balanced ({len(js)} bytes; install node for a real parse).")


if __name__ == "__main__":
    main()
