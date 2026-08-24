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
#   * Access is deliberately narrow: ${ADMIN_TEAM} (admin) and ${CONTRIB_TEAM} (write).
#     No org-wide team grant - see the comment at the grant step.
#
# Why contributors get WRITE and not ADMIN: protection exempts administrators, because a
# PR author cannot approve their own PR and the sole code owner would otherwise be blocked
# on his own changes. So admin = bypasses review, write = subject to review. Anyone whose
# PRs should be approved must be on the contributors team, not the admins team.
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
CONTRIB_TEAM="onetyler-tcp-pm-contributors"   # write access; NOT admins, so the PR gate applies
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
  echo "    done"

  # Contributors get write, not admin. That distinction is the whole point: branch
  # protection exempts admins (see below), so anyone who should have their PRs reviewed
  # must NOT be an admin. Tolerates the team not existing yet.
  echo "==> Granting '${CONTRIB_TEAM}' = push (write)"
  if gh api "orgs/${OWNER}/teams/${CONTRIB_TEAM}" >/dev/null 2>&1; then
    gh api -X PUT "orgs/${OWNER}/teams/${CONTRIB_TEAM}/repos/${SLUG}" -f permission=push
    echo "    done"
  else
    echo "    SKIPPED - team '${CONTRIB_TEAM}' does not exist yet. Re-run this script once"
    echo "    it has been created; the grant is idempotent."
  fi
  # Deliberately NO org-wide team grant, and do not add one without asking the repo owner.
  # The reference repo (tcp-oc-reports-tools) grants `global-fte` push access, and that was
  # copied here in error. Two reasons it is wrong:
  #   1. Scope. This repo's contributors are the named entries in contributors.json. Its
  #      owner does not work across the rest of Tyler engineering.
  #   2. It would not work as written anyway. Since SecureGuard, access is divisionally
  #      protected, so an org-wide team grant does not confer what its member count suggests.
  # The repo is public, so anyone else can fork and open a PR - they simply cannot push a
  # branch into the repo. Add reviewers as direct collaborators or to ${ADMIN_TEAM}.
  echo "==> No org-wide grant by design (see comment above)"
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
