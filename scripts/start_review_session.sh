#!/usr/bin/env bash
#
# Steps (a) and (b) of the review process, in the right order.
#
#   (a) pull the latest main, so you are not reviewing against a stale base
#   (b) fetch any new transcripts from Foundry, then show what needs reviewing
#
# Pulling FIRST is not a nicety. Two reviewers who each start from a stale main can both
# first-review the same transcript; the diffs apply cleanly, git reports no conflict, and
# whoever merges second silently overwrites the other. scripts/validate_reviews.py will
# catch it in CI, but starting fresh avoids the wasted work.
#
# Usage:  ./scripts/start_review_session.sh [branch-name]
#
set -euo pipefail
cd "$(dirname "$0")/.."

BRANCH="${1:-review/$(git config user.email | cut -d@ -f1)-$(date +%Y%m%d)}"

echo "==> (a) syncing with origin/main"
git fetch --quiet origin
if [ -n "$(git status --porcelain)" ]; then
  echo "    ! working tree is dirty — commit or stash before starting a session:"
  git --no-pager status --short | sed 's/^/      /'
  exit 1
fi
git switch --quiet main
git pull --quiet --ff-only origin main
echo "    main is at $(git rev-parse --short HEAD)"

if git show-ref --quiet "refs/heads/${BRANCH}"; then
  git switch --quiet "${BRANCH}"
  git merge --quiet --ff-only main || {
    echo "    ! ${BRANCH} has diverged from main; rebase it before continuing"; exit 1; }
  echo "    reusing branch ${BRANCH}"
else
  git switch --quiet -c "${BRANCH}"
  echo "    created branch ${BRANCH}"
fi

echo
echo "==> (b) fetching new transcripts from Foundry"
if [ -z "${FOUNDRY_API_KEY:-}" ]; then
  echo "    FOUNDRY_API_KEY not set — skipping the fetch, working with what is already in the repo."
  echo "    (source your env file to pull anything new)"
else
  python3 scripts/fetch_transcripts.py
fi

echo
echo "==> what needs reviewing"
python3 scripts/review_status.py | sed -n '1,4p'
echo
PENDING=$(python3 scripts/review_status.py --pending | wc -l | tr -d ' ')
if [ "$PENDING" = "0" ]; then
  echo "    nothing pending — you are clear."
else
  echo "    ${PENDING} pending. Open the UI:"
  echo "      python3 scripts/review_server.py"
  echo
  echo "    A clean transcript is one click: the form opens pre-filled as 'no changes"
  echo "    needed', so just confirm your name and hit 'Mark reviewed & next'."
  echo "    Save without marking if you want to come back to one."
fi
echo
echo "    When you are done reviewing, commit and tell Claude to process the reviewed ones."
