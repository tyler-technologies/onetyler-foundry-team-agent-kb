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
# Instruction files are admin-only. Catch a stray edit HERE, before it is committed and
# before CI has to reject the PR — an AI agent that has quietly "improved" CLAUDE.md is
# then following its own rewrite, and this is the cheapest place to notice.
# Patterns from .github/admin-only-paths.txt — the single source shared with CI and
# CODEOWNERS, so all three describe one boundary.
INSTR_RE=$(grep -vE '^[[:space:]]*(#|$)' .github/admin-only-paths.txt | paste -sd'|' -)
touched_instr=$(git diff --name-only "origin/main...HEAD" 2>/dev/null \
                | grep -E "($INSTR_RE)" || true)
if [ -n "$touched_instr" ]; then
  echo "==> ⚠ this branch modifies ADMIN-ONLY files"
  echo "$touched_instr" | sed 's/^/      /'
  echo "    These decide which agent answers, or how the repo operates. Contributors own"
  echo "    knowledge CONTENT (Conf-/Docusaurus-/FAQ-/Misc-/Training-/GitHub- files in each"
  echo "    Knowledge-<Domain>/ folder) and their verdicts under transcripts/ — but NOT"
  echo "    _START_HERE.md, which carries cross-agent hand-off rules."
  echo "    If you are not a repo admin, revert these and raise it in the PR description:"
  echo "      git checkout origin/main -- <file>"
  echo "    CI will fail the PR otherwise."
  echo
fi

echo "==> checking the reviewer list is current"
# Uses YOUR gh credentials — there is deliberately no shared PAT for this. Needs read:org;
# if it is missing, run:  gh auth refresh -s read:org
if python3 scripts/sync_contributors.py --check >/dev/null 2>&1; then
  echo "    contributors.json matches team membership"
else
  echo "    contributors.json may have drifted from GitHub team membership."
  echo "    Run:  python3 scripts/sync_contributors.py   then commit the result."
  echo "    (If that errors, your gh token may lack read:org: gh auth refresh -s read:org)"
fi

echo
echo "==> what needs reviewing"
python3 scripts/review_status.py | sed -n '1,5p'
echo

# Suggestions handed to YOU. Surfaced here because this is the moment it is actionable — a
# suggestion sitting in the queue is waiting on a specific person, and folding it into the
# pending count would hide exactly that. Uses your own gh identity; degrades to nothing if
# gh is unavailable.
ME=$(gh api user --jq .login 2>/dev/null || true)
if [ -n "$ME" ]; then
  MINE=$(python3 scripts/review_status.py --suggestions --for "$ME" 2>/dev/null \
         | grep -v '^no suggestions waiting' || true)
  if [ -n "$MINE" ]; then
    echo "==> suggestions waiting on you ($ME)"
    echo "$MINE" | sed 's/^/    /'
    echo
    echo "    These are colleagues' worked-up opinions, not verdicts. Open one, change what"
    echo "    you disagree with, put YOUR name in reviewer, and mark it reviewed to accept."
    echo
  fi
fi

PENDING=$(python3 scripts/review_status.py --pending | wc -l | tr -d ' ')
if [ "$PENDING" = "0" ]; then
  echo "    nothing open — you are clear."
else
  # Counts everything not closed out, so suggestions are included here as well as listed
  # above. That is deliberate: a suggestion still needs a human decision.
  echo "    ${PENDING} open (pending + suggested). Open the UI:"
  echo "      python3 scripts/review_server.py"
  echo
  echo "    A clean transcript is one click: the form opens pre-filled as 'no changes"
  echo "    needed', so just confirm your name and hit 'Mark reviewed & next'."
  echo "    Save without marking if you want to come back to one."
fi
echo
echo "    When you are done reviewing, commit and tell Claude to process the reviewed ones."
