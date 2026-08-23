#!/usr/bin/env bash
#
# Apply repo governance for onetyler-foundry-team-agent-kb.
#
# The goal of this configuration is one thing: **contributors must not silently overwrite
# each other's work.** Two reviewers can each pick up the same pending transcript, and both
# diffs apply cleanly, so git reports no conflict and whoever merges second wins invisibly.
#
#   * A pull request is REQUIRED to change main. Every change gets a diff and a record.
#   * ONE required approving review, from a CODE OWNER. .github/CODEOWNERS makes
#     @vijay-tylertech the owner of every path, so every contributor's PR needs his
#     approval while this workflow is bedding in.
#   * Administrators are NOT forced through the gate (enforce_admins=false). This is
#     deliberate: a PR author can never approve their own PR, so with a single code
#     owner, enforcing it on admins would permanently block him on his own changes.
#     Admins can merge their own work; everyone else waits for review.
#   * Status checks from .github/workflows/validate.yml are required, so a PR that
#     collides with someone else's review cannot merge.
#   * Force pushes and branch deletion on main are blocked.
#
# The pairing that actually prevents overwrites is `strict: true` on the status check plus
# scripts/validate_reviews.py. `strict` forces a PR to be up to date with main before it can
# merge, which re-runs the collision check against the *current* main — so a review that
# landed while this PR was open is seen, not clobbered.
#
# Idempotent — safe to re-run to re-assert settings after manual changes.
#
# Requires: gh CLI authenticated as someone with admin on the repo.
# Usage:  ./scripts/setup-repo-governance.sh [owner/repo]
#
set -euo pipefail

SLUG="${1:-tyler-technologies/onetyler-foundry-team-agent-kb}"
ADMIN_TEAM="onetyler-tcp-pm-admins"
PUSH_TEAM="global-fte"
BRANCH="main"
OWNER="${SLUG%%/*}"

echo "==> Target: ${SLUG} (branch: ${BRANCH})"
OWNER_TYPE="$(gh api "repos/${SLUG}" -q '.owner.type' 2>/dev/null)" || {
  echo "ERROR: ${SLUG} does not exist or you lack access."
  exit 1
}
echo "    owner: ${OWNER} (${OWNER_TYPE})"

# ---------------------------------------------------------------------------
# 1. Team grants (organization repos only — GitHub teams don't exist for users)
# ---------------------------------------------------------------------------
if [[ "${OWNER_TYPE}" == "Organization" ]]; then
  echo "==> Granting '${ADMIN_TEAM}' = admin"
  gh api -X PUT "orgs/${OWNER}/teams/${ADMIN_TEAM}/repos/${SLUG}" -f permission=admin
  echo "==> Granting '${PUSH_TEAM}' = push"
  gh api -X PUT "orgs/${OWNER}/teams/${PUSH_TEAM}/repos/${SLUG}" -f permission=push
  echo "    done"
else
  echo "==> SKIPPING team grants: '${OWNER}' is a user account, not an org."
fi

# ---------------------------------------------------------------------------
# 2. Merge settings
#    Auto-merge stays OFF: a PR now needs a human code-owner approval, so there is no
#    point queueing a merge on checks alone.
# ---------------------------------------------------------------------------
echo "==> Merge settings (all three methods; auto-merge off; keep branches)"
gh api -X PATCH "repos/${SLUG}" \
  -F allow_auto_merge=false \
  -F allow_squash_merge=true \
  -F allow_merge_commit=true \
  -F allow_rebase_merge=true \
  -F delete_branch_on_merge=false \
  -q '"    squash=" + (.allow_squash_merge|tostring) + " merge=" + (.allow_merge_commit|tostring) + " rebase=" + (.allow_rebase_merge|tostring) + " auto_merge=" + (.allow_auto_merge|tostring)'

# ---------------------------------------------------------------------------
# 3. Branch protection on main — classic protection, no rulesets
#    (the reference repo has zero rulesets; all of this is classic protection)
# ---------------------------------------------------------------------------
echo "==> Protecting '${BRANCH}': PR + 1 code-owner approval + validate check; admins exempt"
gh api -X PUT "repos/${SLUG}/branches/${BRANCH}/protection" --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["validate"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "required_approving_review_count": 1,
    "require_last_push_approval": false
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": false,
  "required_linear_history": false,
  "block_creations": false
}
JSON
echo "    done"

# ---------------------------------------------------------------------------
# 4. Report
# ---------------------------------------------------------------------------
echo
echo "==> Final state"
gh api "repos/${SLUG}/branches/${BRANCH}/protection" -q '
  "    PR required:        yes (approvals required: " + (.required_pull_request_reviews.required_approving_review_count|tostring) + ")",
  "    applies to admins:  " + (.enforce_admins.enabled|tostring),
  "    force pushes:       " + (.allow_force_pushes.enabled|tostring),
  "    branch deletion:    " + (.allow_deletions.enabled|tostring)'
if [[ "${OWNER_TYPE}" == "Organization" ]]; then
  gh api "repos/${SLUG}/teams" -q '.[] | "    team: " + .slug + " = " + .permission'
fi
echo
echo "Governance applied. Direct pushes to ${BRANCH} are blocked. Contributor PRs need"
echo "an approving review from a CODEOWNER (@vijay-tylertech) and a passing validate"
echo "check. Repo admins are exempt from the gate so they are not blocked on their own"
echo "PRs - a PR author cannot approve themselves. Loosen CODEOWNERS to the admin team"
echo "once the process is settled."
