#!/bin/bash
# Double-click this on macOS. Nothing to type, no assistant needed.
#
# A .command file is what macOS opens in Terminal on a double-click. `cd` to the script's own
# directory first: Finder launches it from the user's home, not from the repo.
cd "$(dirname "$0")" || exit 1
exec python3 scripts/start.py
