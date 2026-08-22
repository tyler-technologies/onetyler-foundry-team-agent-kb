#!/usr/bin/env bash
#
# Apply repo governance for onetyler-foundry-team-agent-kb.
#
# These settings mirror tyler-technologies/tcp-oc-reports-tools exactly (verified
# against its live config on 2026-08-21), which is the reference behaviour we want:
#
#   * A pull request is REQUIRED to change main — for everyone, admins included
#     (enforce_admins=true). That gives every change a diff, a record, and a place
#     to hang CI later.
#   * ZERO required approving reviews. This is what makes admin changes effectively
#     "auto-approved": the PR is immediately mergeable by anyone with write access,
#     with no bot, no workflow, and no second reviewer needed. Outside contributors
#     can open a PR but still cannot merge it — merging needs push access.
#   * Force pushes and branch deletion on main are blocked.
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
# 2. Merge settings — matching the reference repo
#    Auto-merge stays OFF: with zero required approvals and no required status
#    checks, a PR is mergeable the moment it opens, so "merge when checks pass"
#    would have nothing to wait for.
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
echo "==> Protecting '${BRANCH}': PR required, 0 approvals, admins included"
gh api -X PUT "repos/${SLUG}/branches/${BRANCH}/protection" --input - <<'JSON'
{
  "required_status_checks": null,
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 0,
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
echo "Governance applied, mirroring tcp-oc-reports-tools. Direct pushes to ${BRANCH}"
echo "are blocked for everyone including admins; admin PRs need no approval and can"
echo "be merged immediately."
