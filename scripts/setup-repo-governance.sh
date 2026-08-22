#!/usr/bin/env bash
#
# Apply repo governance for onetyler-foundry-team-agent-kb.
#
# Idempotent — safe to re-run to re-assert settings, and designed to be run TWICE
# in this repo's life:
#
#   1. Now, while the repo lives under the personal account vijay-tylertech.
#      The admin-team grant is skipped (GitHub teams exist only inside orgs).
#   2. Again after the repo is transferred into the tyler-technologies org,
#      at which point the onetyler-tcp-pm-admins grant is applied.
#
# Requires: gh CLI authenticated as someone with admin on the repo.
# Usage:  ./scripts/setup-repo-governance.sh [owner/repo]
#
set -euo pipefail

SLUG="${1:-vijay-tylertech/onetyler-foundry-team-agent-kb}"
TEAM="onetyler-tcp-pm-admins"
BRANCH="main"
OWNER="${SLUG%%/*}"

echo "==> Target: ${SLUG} (branch: ${BRANCH})"
OWNER_TYPE="$(gh api "repos/${SLUG}" -q '.owner.type' 2>/dev/null)" || {
  echo "ERROR: ${SLUG} does not exist or you lack access."
  exit 1
}
echo "    owner: ${OWNER} (${OWNER_TYPE})"

# ---------------------------------------------------------------------------
# 1. Grant the admin team — organization repos only
# ---------------------------------------------------------------------------
if [[ "${OWNER_TYPE}" == "Organization" ]]; then
  echo "==> Granting '${TEAM}' admin permission"
  gh api -X PUT "orgs/${OWNER}/teams/${TEAM}/repos/${SLUG}" -f permission=admin
  echo "    done"
else
  echo "==> SKIPPING team grant: '${OWNER}' is a user account, not an org."
  echo "    GitHub teams exist only inside orgs. To add ${TEAM}, first transfer"
  echo "    this repo to tyler-technologies, then re-run this script with:"
  echo "      ./scripts/setup-repo-governance.sh tyler-technologies/${SLUG#*/}"
fi

# ---------------------------------------------------------------------------
# 2. Repo-level merge settings
#    Auto-merge must be enabled at the repo level before `gh pr merge --auto`
#    (and the auto-approve workflow) can use it.
# ---------------------------------------------------------------------------
echo "==> Enabling auto-merge; squash-only; delete merged branches"
gh api -X PATCH "repos/${SLUG}" \
  -F allow_auto_merge=true \
  -F allow_squash_merge=true \
  -F allow_merge_commit=false \
  -F allow_rebase_merge=false \
  -F delete_branch_on_merge=true \
  -q '"    auto_merge=" + (.allow_auto_merge|tostring) + " squash_only=" + (.allow_squash_merge|tostring)'

# ---------------------------------------------------------------------------
# 3. Let GitHub Actions approve PRs
#    Default is OFF; without this the auto-approve workflow cannot submit a review.
#    An org-level policy can override it after transfer — if approvals start
#    failing, set the same flag at orgs/<org>/actions/permissions/workflow.
# ---------------------------------------------------------------------------
echo "==> Allowing Actions to approve pull requests"
gh api -X PUT "repos/${SLUG}/actions/permissions/workflow" \
  -F default_workflow_permissions=write \
  -F can_approve_pull_request_reviews=true
echo "    done"

# ---------------------------------------------------------------------------
# 4. Branch protection on main
#    enforce_admins=true means the PR gate applies to admins too — nobody pushes
#    straight to main. That is what makes the gate real; the auto-approve workflow
#    is what keeps it from blocking the people who own the repo.
# ---------------------------------------------------------------------------
echo "==> Protecting '${BRANCH}': PR required, 1 approval, admins included"
gh api -X PUT "repos/${SLUG}/branches/${BRANCH}/protection" --input - <<'JSON'
{
  "required_status_checks": null,
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 1,
    "require_last_push_approval": false
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true,
  "required_linear_history": false,
  "block_creations": false
}
JSON
echo "    done"

# ---------------------------------------------------------------------------
# 5. Report
# ---------------------------------------------------------------------------
echo
echo "==> Final state"
gh api "repos/${SLUG}/branches/${BRANCH}/protection" -q '
  "    PR required:        yes (approvals: " + (.required_pull_request_reviews.required_approving_review_count|tostring) + ")",
  "    applies to admins:  " + (.enforce_admins.enabled|tostring),
  "    force pushes:       " + (.allow_force_pushes.enabled|tostring),
  "    branch deletion:    " + (.allow_deletions.enabled|tostring)'
if [[ "${OWNER_TYPE}" == "Organization" ]]; then
  gh api "repos/${SLUG}/teams" -q '.[] | "    team: " + .slug + " = " + .permission'
fi
echo
echo "Governance applied. Direct pushes to ${BRANCH} are blocked for everyone,"
echo "including admins. Admin PRs auto-approve and auto-merge via"
echo ".github/workflows/auto-approve-admin-prs.yml."
