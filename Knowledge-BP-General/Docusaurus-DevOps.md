# OneTyler DevOps: Developer Tooling, Infrastructure, Disaster Recovery, and Runbooks

Source: Tyler Blueprint Docusaurus — `https://docs.tylerdev.io/platform-architecture/dev-ops/` (multiple sub-pages)

Domain: Blueprint General — Tyler Cloud Platform / Blueprint docs not served by a specialized Foundry agent.

Audience: Tyler OneTyler / platform DevOps engineers — internal.

**Companion documents:** _START_HERE.md, Docusaurus-PlatformOverview.md, Docusaurus-ClientApps.md, Docusaurus-OpsApps.md, Docusaurus-CloudPlatformAPI.md, Docusaurus-ServiceArchitecture.md, Docusaurus-Security.md, Docusaurus-ProductSystemReg.md, Docusaurus-AlignedReleases.md, Docusaurus-StatusPageAndSLA.md

> **Dedicated-agent hand-off (do NOT answer these here — point to the correct agent):**
> - Ops Center questions → https://docs.tylerdev.io/app-guides/ops/ops-center/overview/
> - Support Access Center (SAC) → https://docs.tylerdev.io/ops/support-access-center/
> - Identity (Tyler Identity / TID) → https://docs.tylerdev.io/identity

---

## How to Use This Guide

| I need to… | Go to section |
|---|---|
| Set up Datadog access, agents, tagging, or dashboards | [Dev Tools — Datadog](#dev-tools--datadog) |
| Onboard to Harness CI/CD or understand Harness governance | [Dev Tools — Harness](#dev-tools--harness) |
| Set up or manage JSM on-call schedules | [Dev Tools — JSM and On-Call](#dev-tools--jsm-and-on-call) |
| Migrate a GitHub repo to Artifactory, or set up CI workflows | [Dev Tools — Continuous Integration](#dev-tools--continuous-integration) |
| Migrate a DynamoDB or Aurora RDS database between accounts | [Dev Tools — Database Migration](#dev-tools--database-migration) |
| Migrate an app out of TCP EKS clusters | [Application Migration Out of TCP Clusters](#application-migration-out-of-tcp-clusters) |
| Understand Terraform Cloud, workspace manager, or IaC approach | [Infrastructure as Code — Terraform](#infrastructure-as-code--terraform) |
| Understand AWS account architecture, shared VPCs, EKS, CI/CD pipelines | [TCP AWS Infrastructure](#tcp-aws-infrastructure) |
| Provision AWS resources (DynamoDB, RDS, S3, SNS/SQS, secrets, Harness) with Terraform | [OneTyler Terraform Docs — AWS Resources](#onetyler-terraform-docs--aws-resources) |
| Design or execute disaster recovery (DR) for an application | [Disaster Recovery — Design Guides](#disaster-recovery--design-guides) |
| Execute a regional failover or failback for TCP platform | [Disaster Recovery — Regional Failover Runbooks](#disaster-recovery--regional-failover-runbooks) |
| Respond to a P1 incident (on-call triage, escalation) | [Runbooks — P1 Incident Management](#runbooks--p1-incident-management) |
| Set up AWS CLI or kubectl EKS access | [Runbooks — AWS SSO and EKS Access](#runbooks--aws-sso-and-eks-access) |
| Upgrade an EKS cluster | [Runbooks — Kubernetes Upgrade](#runbooks--kubernetes-upgrade) |
| Set up PagerDuty with Datadog | [Runbooks — PagerDuty Setup](#runbooks--pagerduty-setup) |
| Provision Aqua, Artifactory, Docker Hub, GitHub, or PrivX access | [Runbooks — Dev Tool Provisioning](#runbooks--dev-tool-provisioning) |

---

## Glossary

| Term | Meaning |
|---|---|
| TCP | Tyler Cloud Platform — the OneTyler-operated multi-tenant SaaS platform |
| TID | Tyler Identity — the identity/authentication platform; has its own Foundry agent |
| EKS | Amazon Elastic Kubernetes Service |
| IaC | Infrastructure as Code |
| DR | Disaster Recovery |
| RTO | Recovery Time Objective — max acceptable time for service restoration |
| RPO | Recovery Point Objective — max acceptable data loss (measured in time) |
| JSM | Jira Service Management — used for on-call, alerts, and incidents |
| FME | Feature Management & Experimentation (Harness module) — replaces Split and Feature Flags Classic |
| PrivX | SSH access management tool used for database and infrastructure access |
| CRR | Cross-Region Replication (S3) |
| Karpenter | AWS EKS node autoscaler used by TCP clusters |
| git2consul | Service that posts config from GitHub repos to Consul for service configuration |
| tcpci / tcpqa / tcpprod | CI, QA, and Production environments for the Tyler Cloud Platform |
| Workspace Manager | Tyler-internal automation for managing Terraform Cloud workspaces |
| Cloud Living | Tyler's operating model requiring automated, SaaS-style software delivery |

---

## Dev Tools — Datadog

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/datadog/getting-started

### What is Datadog?

Datadog is Tyler's cloud-scale monitoring and observability platform. It provides infrastructure metrics, APM/distributed tracing, log aggregation, Real User Monitoring (RUM), and synthetics. Datadog correlates data across these streams to help pinpoint issues quickly and provides integrations with JSM and PagerDuty for alerting.

### Getting Access

Tyler auto-provisions read-only Datadog accounts when an employee logs in with their Tyler domain email.

- **SSO login:** https://app.datadoghq.com/account/login/id/75818fc62
- For elevated access, contact your division/business unit's designated Datadog admin.
- For general questions: Slack `#tyl-datadog`

### Datadog Agent Setup

**Use when:** You need to instrument a service, VM, or container to ship metrics/logs/traces to Datadog.

**Critical rule:** When setting up any new agent, follow the [tagging standards](#datadog-tagging-standards) before deployment.

- **Windows agent:** https://docs.datadoghq.com/agent/basic_agent_usage/windows/?tab=commandline
- **Linux agent:** https://docs.datadoghq.com/agent/
- **Container/Kubernetes agents:** Follow the official Datadog daemonset documentation.

**Agent config YAML — core tags block:**

```yaml
tags:
  - product:tcp
  - division:onetyler
  - <TAG_KEY>:<TAG_VALUE>

env: <environment name>
```

**Log configuration note:** Be very careful changing JSON log preprocessing settings — it can break JSON logs for everyone. Use the known-good configuration kept in the Blueprint docs.

### Datadog Tagging Standards

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/datadog/tagging

Consistent tagging is mandatory for dashboards, cost attribution, and alerting to work correctly. Always use automation (Terraform) to apply tags.

**Format rule:** All tag names must be lower-case kebab-case (e.g., `env-group`, not `EnvGroup` or `env_group`).

**Core (mandatory) tags:**

| Tag | Purpose | Example value |
|---|---|---|
| `env` | Top-level environment filter for APM; configured account-wide | `tcpprod-1` |
| `division` | Division-level cost/usage attribution | `onetyler`, `erp`, `pr`, `cj`, `ps`, `lgd`, `ccs`, `nic`, `federal`, `di` |
| `product` | Which Tyler product owns the resource; use `shared` if multi-product | `tcp` |
| `customer-id` | Customer scope; use `multi-tenant` for multi-tenant cloud apps | `multi-tenant` |

**Environment examples:**
- TCP CI: `tcpci-1`
- TCP QA: `tcpqa-1`
- TCP Prod: `tcpprod-1`

**Extended tags for specific filtering:**

| Tag | Values |
|---|---|
| `env-group` | `tcp`, `prod`, `non-prod` |
| `tyler-account` | `onetyler-dev`, `onetyler-qa`, etc. |
| `erp-env-group` | `prod`, `non-prod` (ERP-specific) |

### Datadog Dashboards

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/datadog/dashboards

**Best practices:**
- Use template variables (especially `$env`) so one dashboard covers all environments — do not create separate dashboards per environment.
- Copy (steal) widgets from existing canned AWS dashboards or from other Tyler engineers instead of building from scratch. Use `cmd+shift+k` (Mac) or `ctrl+shift+k` (Windows) to open the Widget Clipboard.
- Use the Log Stream widget as a "jump-off point" to Log Explorer with pre-applied context filters.
- Structure dashboards with levels of context; a dashboard is an overview, not an exhaustive view.
- Use color dividers and whitespace (see the Ecosystem Webhooks dashboard as a reference example).

**Reference dashboards:**
- Tyler Cloud Platform Kubernetes Activity: https://app.datadoghq.com/dashboard/fp7-su4-p6q/tyler-cloud-platform-kubernetes-activity
- Tyler Cloud Platform Stats: https://app.datadoghq.com/dashboard/dzq-9km-dgy/tyler-cloud-platform-stats
- Ecosystem Webhooks: https://app.datadoghq.com/dashboard/szp-ers-bcc/ecosystem-webhooks
- Example dashboard for tutorial: https://app.datadoghq.com/dashboard/uci-b6j-xbc/chris-datadog-example

**Creating a template variable (env):**
1. Open the dashboard editor → click "Add Template Variables."
2. Select tag `env`, give it a name, set a default (e.g., `tcpprod-1`).
3. Use `$env` in widget filter configurations to parameterize by environment.

**Note:** Template variables do not support multi-select. Using `$env:*` shows all environments across all Tyler AWS accounts.

---

## Dev Tools — Harness

Live docs:
- Overview: https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/harness/overview
- Onboarding Guide: https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/harness/onboarding-guide
- Governance Standard: https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/harness/governance-standard

### What is Harness?

Harness is Tyler's **recommended CI/CD platform** for automated builds and deployments. It enables teams to:
- Build and deploy through repeatable pipelines
- Manage orgs, projects, environments, and deployment workflows
- Integrate approvals, secrets, testing, and rollbacks into release processes

**Harness FME** (Feature Management & Experimentation) is Tyler's standard for feature flags and experimentation. It replaces Split (consolidated into Harness on Feb 5, 2026) and Feature Flag Classic (in maintenance mode; migrate to FME before end of 2027).

**Use when:** Deploying services to TCP EKS clusters; managing feature flags; running CD pipelines.

Official docs: https://developer.harness.io/docs/

### Core Concepts

| Term | Meaning |
|---|---|
| Organization (Org) | Top-level boundary in Harness; maps 1:1 to a **product** |
| Project | Scoped unit for a service or deployable component |
| Environment | Lifecycle stage (dev, staging, production) with independent config |
| Pipeline | Automated workflow that builds, tests, deploys |
| Feature Flag (FME) | Runtime on/off control without redeployment |

### Requesting Access

Submit a Tyler Help Desk form: https://help.center.tylertech.com/servicedesk/customer/portal/3168/group/3328/create/4140

### Setting Up a Harness Org and Project

**Use when:** A new team or product needs a Harness org for CI/CD pipelines.

**Prerequisites:** Review the Governance Standard (below) first.

1. Review the [Harness Governance Standard](#harness-governance-standard).
2. Submit a PR to the Org Manage repo with a YAML file: https://github.com/tyler-technologies/harness-org-manage/blob/main/docs/user_guide.md
3. Request review from OneTyler Infrastructure through the [Cloud Platform Community Teams Channel](https://teams.microsoft.com/l/channel/19%3A1e6bcc02bd3242a193bf9171a51a0395%40thread.tacv2/Cloud%20Platform%20Community?groupId=d9db441d-35fa-433c-8fe0-ff7fe5825d3c&tenantId=7cc5f0f9-ee5b-4106-a62d-1b9f7be46118).
4. Upon merge, automation creates the Harness org, all configured projects, Kubernetes connectors, and Org/Project Admin user groups.

> **Warning:** The Org Admins and Project Admins user groups are managed by Terraform. Changes made in the Harness UI will not be persisted.

### Harness Governance Standard

*Status: CTO Office Approved, effective March 16, 2026.*

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/harness/governance-standard

**Core principles (non-negotiable):**

1. **Orgs represent Products.** A Harness Org maps 1:1 to a production-deployed product registered in TCP. Orgs do NOT represent teams, temporary initiatives, shared platforms, or divisions. Multiple divisions in one org = governance violation.

2. **YAML is the source of truth.** All org configuration must be in [harness-org-manage](https://github.com/tyler-technologies/harness-org-manage). UI changes are ephemeral and will be overwritten.

3. **Tags drive chargeback.** `tags.division` is the sole source of truth for financial attribution. Missing/incorrect tags = governance violation; must be remediated within two weeks of notification.

**Required org tags (all must be present in YAML):**

```yaml
tags:
  division: onetyler          # lowercase kebab-case; must match AWS Tagging Standards
  owner: first.last          # accountable owner
  lifecycle: poc             # poc | prod | deprecated
```

**Division tag values:** See the [AWS Tagging Standards (Corporate Required Tags → division)](https://tylertech.atlassian.net/wiki/spaces/CCSD/pages/357303454/AWS+Tagging+Standards#division-tag) — this is the authoritative list; do not rely on cached values.

**Lifecycle rules:**
- `poc` — must NOT be used for production workloads
- `deprecated` — must NOT be used for active production workloads; subject to removal

**Org creation requirements:**

| Requirement | Rule |
|---|---|
| Product-aligned | Exactly one TCP-registered product (or approved tightly-coupled bundle) |
| Division-attributed | Single `tags.division` value |
| YAML-defined | Exists only via `harness-org-manage` |
| Tagged | All three required tags present |
| Admin-defined | Named org admins listed in YAML |

**PR will fail automatically if** `tags.division` is missing/invalid, `tags.owner` is missing, `tags.lifecycle` is missing/invalid, or org represents multiple products/divisions.

**Legacy org deadline:** All non-compliant orgs must be decommissioned by **September 30, 2026** unless the CTO Office approves an exception.

### Harness Best Practices

**CI/CD:**
- Standardize org and project naming
- Reuse pipeline templates
- Do NOT store secrets directly in Harness Secrets Manager — store in AWS Secrets Manager and connect Harness to it
- Set up pipelines using Terraform or GitOps
- Use remote manifests for Harness Services

**FME:**
- Use FME for all new feature-flag implementations
- Keep flag names simple, consistent, descriptive
- Remove stale flags regularly
- Use gradual rollouts for higher-risk releases

**Learning resources:**
- Harness University: https://developer.harness.io/university/
- FME Training: https://university-registration.harness.io/page/fme

---

## Dev Tools — JSM and On-Call

Live docs:
- Overview: https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/jsm/overview
- Manage On-call: https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/jsm/manage-oncall-schedule

### What is JSM for OneTyler?

Jira Service Management (JSM) is the on-call and incident management platform for OneTyler. It:
- Manages on-call schedules and escalation policies
- Ingests P1 alerts from Datadog monitors and synthetic tests
- Routes notifications to the appropriate on-call engineer
- Creates Jira Work Items in the OneTyler workspace
- Automates communication via Microsoft Teams and email

**OneTyler JSM URLs:**
- Team: https://home.atlassian.com/o/8419343d-b09d-1jj2-7472-18d1k0410baa/people/team/37a5b6fe-45c3-49fd-a101-55951a7b77b3
- Operations/On-call: https://my.work.tylertech.com/jira/ops/teams/37a5b6fe-45c3-49fd-a101-55951a7b77b3/on-call
- Alerts: https://my.work.tylertech.com/jira/ops/alerts?view=list&query=responders%3A37a5b6fe-45c3-49fd-a101-55951a7b77b3
- OneTyler Jira Space: https://my.work.tylertech.com/jira/servicedesk/projects/CORPDEV/summary

**Datadog integrations:**
- Production Synthetic Tests: https://app.datadoghq.com/synthetics/tests?query=team%3Atyler-cloud-platform%20tag%3A%22env%3Atcpprod-1%22%20tag%3A%22createdby%3Aterraform%22
- Production Monitors: https://app.datadoghq.com/monitors/manage?q=team%3Atyler-cloud-platform%20pagerduty%20tag%3A%22environment%3Atcpprod-1%22%20priority%3Ap1

### Requesting JSM Access

Use the [Tyler Helpdesk Form](https://help.center.tylertech.com/servicedesk/customer/portal/1/group/35/create/320):
- Request Type: JSM Access
- URL: https://my.work.tylertech.com/jira/ops/teams/37a5b6fe-45c3-49fd-a101-55951a7b77b3/on-call
- Additional Details: "Add Request Team Admin access to the CorpDev JSM Team."

### Configuring On-Call Notifications

1. Go to your [Atlassian notification settings](https://my.work.tylertech.com/jira/settings/personal/alert-notifications).
2. Add SMS/voice/email to Contact methods.
3. Add notification rules (New Alert, Closed Alert, etc.).

### Managing On-Call Schedules

- Access on-call schedules: https://my.work.tylertech.com/jira/ops/teams/37a5b6fe-45c3-49fd-a101-55951a7b77b3/on-call
- [Create an on-call schedule](https://support.atlassian.com/jira-service-management-cloud/docs/create-an-on-call-schedule/)
- [Override an on-call schedule](https://support.atlassian.com/jira-service-management-cloud/docs/override-an-on-call-schedule/)

**To add a team member to the rotation:**
1. Edit your On-call Schedule.
2. Select the Rotation and edit.
3. Add Participant — the user must already be in the [CorpDev JSM Team](https://home.atlassian.com/o/8419343d-b09d-1jj2-7472-18d1k0410baa/people/team/37a5b6fe-45c3-49fd-a101-55951a7b77b3).

- [Create/edit/delete Escalation Policy](https://support.atlassian.com/jira-service-management-cloud/docs/create-edit-delete-an-escalation-policy/)

---

## Dev Tools — Continuous Integration

### GitHub Actions and Artifactory Migration

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/continuous-integration/github-artifactory-migration

**Use when:** Migrating a project from Bitbucket to GitHub, or from ProGet/TeamCity to Artifactory/GitHub Actions.

**Migration steps overview:**
1. Install script prerequisites (bash/WSL, git, nvm, dos2unix, jq, Java 8+)
2. Set up local Artifactory credentials
3. Create Artifactory team repositories (open an Ops Center support ticket to request)
4. Update projects (NuGet.config, .npmrc, Dockerfiles, build scripts) to use Artifactory
5. Move projects from Bitbucket to GitHub (scrub secrets from history)
6. Switch CI from TeamCity to GitHub Actions

**Local Artifactory setup — required environment variables:**

```bash
export ARTIFACTORY_USERNAME="your.user@tylertech.com"  # must be lowercase
export ARTIFACTORY_PASSWORD="your-api-key"             # from JFrog UI under Edit Profile
export ARTIFACTORY_TOKEN="$(echo -n "$ARTIFACTORY_USERNAME:$ARTIFACTORY_PASSWORD" | base64)"
export ARTIFACTORY_PULL_REGISTRY="tylertech-docker.jfrog.io"
export ARTIFACTORY_PUSH_REGISTRY="tylertech-scratch-docker-local.jfrog.io"
export ARTIFACTORY_NPM_REGISTRY="https://tylertech.jfrog.io/artifactory/api/npm/scratch-npm-local"
export ARTIFACTORY_NUGET_REGISTRY="https://tylertech.jfrog.io/artifactory/api/nuget/scratch-nuget-local"
```

Log in to Artifactory:
```bash
docker login tylertech-docker.jfrog.io -u "$ARTIFACTORY_USERNAME" -p "$ARTIFACTORY_PASSWORD"
```

**NuGet.config for Artifactory:**
```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <add key="Artifactory" value="https://tylertech.jfrog.io/artifactory/api/nuget/v3/nuget" protocolVersion="3"/>
  </packageSources>
  <packageSourceCredentials>
    <Artifactory>
      <add key="username" value="%ARTIFACTORY_USERNAME%"/>
      <add key="cleartextpassword" value="%ARTIFACTORY_PASSWORD%"/>
    </Artifactory>
  </packageSourceCredentials>
</configuration>
```

**Critical Dockerfile rule:** Pass Artifactory credentials as build ARGs in intermediate stages ONLY — never in the final stage, or they will be embedded in the image.

**GitHub migration script:**
```bash
./repo-to-github.sh --git-user "your.user" --git-token "git-token" \
  --bitbucket-user "your.user" --bitbucket-token "bitbucket-token" \
  -r "repository-name" --bitbucket-project "PROJ" -s secrets.txt
```

**Harness connector note:** When creating a GitHub connector in Harness, use RSA keys (not ED25519 — Harness does not support ED25519 in its secret store):
```bash
ssh-keygen -t rsa -m PEM
```

**Scratch repositories (for temporary developer testing; cleaned up periodically):**
```
Docker:  tylertech-scratch-docker-local.jfrog.io
NuGet:   https://tylertech.jfrog.io/artifactory/api/nuget/scratch-nuget-local
NPM:     https://tylertech.jfrog.io/artifactory/api/npm/scratch-npm-local/
```

### GitHub Actions Workflow Samples

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/continuous-integration/github-action-samples

**Use when:** Writing a new GitHub Actions CI workflow for Armadillo web apps, Dapper web apps, or NuGet SDKs.

**Versioning model for master branch:**
- Every push to master gets a `MAJOR.MINOR.PATCH` semantic version tag.
- Commits with `(MAJOR)` or `(MINOR)` in the message increment those version parts.
- Pull request builds get a `branch-vMAJOR.MINOR.PATCH` tag.
- Create an initial `v1.1.0` tag in GitHub before migrating to set the starting version.

**Calling a Harness webhook from GitHub Actions:**
```yaml
- name: Trigger Harness
  if: ${{ github.event_name == 'push' }}
  env:
    HARNESS_WEBHOOK: ${{ secrets.HARNESS_WEBHOOK }}
    HARNESS_WEBHOOK_APPLICATION: ${{ secrets.HARNESS_WEBHOOK_APPLICATION }}
    HARNESS_SERVICE: "your-harness-service"
  run: |
    curl -X POST -H 'content-type: application/json' --url "$HARNESS_WEBHOOK" \
      -d '{"application":"'"$HARNESS_WEBHOOK_APPLICATION"'","artifacts":[{"service":"'"$HARNESS_SERVICE"'","buildNumber":"${{ steps.semver.outputs.version }}"}]}'
```

**Artifactory security scanning (Xray) — include in every workflow:**
```yaml
- run: |
    cat <<\EOF > xray-scan.yml
    images:
      - '${{ env.IMAGE_TAG }}'
    EOF
- uses: actions/upload-artifact@v2
  with:
    name: xray-scan.yml
    path: xray-scan.yml
    retention-days: 7
```

**Docker build script tip:** Output docker image tag to `$GITHUB_ENV` so the Xray scan step can reference it:
```bash
echo "IMAGE_TAG=$dockerTag" >> "$GITHUB_ENV"
```

Full workflow templates (Armadillo, Dapper, NuGet) and `pr-cleanup.yml` are available in the Blueprint docs at https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/continuous-integration/github-action-samples.

---

## Dev Tools — Database Migration

### Aurora RDS Migration Between AWS Accounts

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/db-migration/aurora

**Use when:** Moving an existing Aurora DB cluster from a TCP AWS account to an application team's AWS account (part of the FedRamp migration or federated account model).

**Prerequisites:** Source and target regions must match, or you must specify a new KMS key and parameter group for the new region.

**Steps:**
1. Create a customer-managed KMS key in the source account's AWS console; add the target account so it can see the key.
2. Select the source snapshot → Actions → Copy Snapshot → associate the new KMS key.
3. Snapshot list → Actions → Share Snapshot → add the target AWS account ID.
4. In the target account (same region): RDS → Snapshots → Shared with me → verify the snapshot appears → Actions → Copy Snapshot → select shared KMS key.
5. Once copy completes, launch a new instance from the copied snapshot.
6. Confirm with the new owner that the instance is running and services are repointed.
7. Stop sharing the snapshot (Snapshot → Actions → Share Snapshot → Delete the account → Save).
8. Decommission timeline: leave TCP DB running for 1 week → notify teams → wait 1 more week → delete.

### DynamoDB Migration Between Accounts

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/dev-tools/db-migration/dynamodb-migration

**Use when:** Moving a DynamoDB table from a TCP account to an application team's AWS account.

**Note:** DynamoDB access across accounts does NOT require Shared VPC. Access is IAM-based.

**Customer preparation (before maintenance window):**
- Request AWS account access at hosting@tylertech.com
- Create a temporary IAM user (e.g., `dynamodb-migrator-temp`) with `AmazonDynamoDBFullAccess` on the target table
- Create the target table with matching schema
- Prepare a security group (see: https://docs.dev.tylerops.io/infra/tcp-infrastructure/shared-vpc/overview)
- Identify which K8s services must be stopped during migration
- Prepare updated service deployment (pointing to new account's role) — ready to apply but not yet merged

**During maintenance (TCP actions):**

```bash
./go-dynamodb-migrate \
  -sourceregion SOURCE_REGION \
  -sourceDB SOURCE_DB_NAME \
  -src_profile [aws-profile-for-tcp-account] \
  -destDB [destination-dynamo-table-name] \
  -dest_profile [aws-profile-for-dest-account] \
  -filterOperator BeginsWith \
  -filterValue [FILTER_REGEX]
```

Migration tool: https://github.com/tyler-technologies/go-dynamodb-migrate

**Regex limitation:** The tool only matches values that _begin with_ the regex value.

**After maintenance:**
- Customer confirms data, redeploys service pointing to new table, removes temporary IAM user
- If all data was migrated: delete the old table after 90 days
- If partial migration: leave old data intact for 90 days, then delete only migrated data

---

## Application Migration Out of TCP Clusters

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/application-migration/migrating

**Use when:** Moving a non-OneTyler application out of TCP EKS clusters (required as OneTyler migrates to FedRamp).

Reference test application: https://github.com/tyler-technologies/tcp-redirect-test-app

**Steps:**

1. **Create an ingress redirect middleware** on the appropriate account:

```yaml
apiVersion: traefik.io/v1alpha1
kind: Middleware
metadata:
  name: <middleware name>
  namespace: <k8s namespace>
spec:
  redirectRegex:
    permanent: true
    regex: (^.*)\.tylerportico\.com/(.*$)
    replacement: ${1}.<target domain>/${2}
```

Update ingress with the annotation:
```
traefik.ingress.kubernetes.io/router.middlewares: <namespace>-<middleware-name>@kubernetescrd
```

2. **Update product YAML** in `tcp-product-catalog` to include the new application URL in addition to the existing cloudplatform URL.

3. **Ensure authority** is set to `tcp_platform_api:authority` and `TokenClientScope` to `tyler-cloud-platform-api-access`.

4. **Adjust subdomain logic** so the app can determine its subdomain from the Host name. Reference PRs:
   - https://github.com/tyler-technologies/tcp-redirect-test-app/pull/7/changes
   - https://github.com/tyler-technologies/tcp-redirect-test-app/pull/6/changes

---

## Infrastructure as Code — Terraform

### IaC Overview

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/infrastructure-as-code/overview

OneTyler uses **Terraform** managed through **Terraform Cloud** (HashiCorp-managed service) for all infrastructure automation. Terraform was chosen over AWS CDK and CloudFormation for state management control, drift detection, multi-cloud support, and strong community ecosystem.

**Tyler Terraform organizations:**
- `tyler-corp` — Owner: OneTyler
- `tyler-hosting` — Owner: Corporate Cloud Services
- `dsd` — Owner: DSD

Other tools used via Terraform providers (beyond AWS): Harness, GitHub, Datadog.

### Terraform Cloud Overview

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/infrastructure-as-code/terraform/terraform-cloud

**Key terminology:**

| Term | Meaning |
|---|---|
| Workspace | Logical unit containing Terraform state, variables, and optionally a triggered run |
| Project | Logical collection of workspaces |
| Organization | Top-level Terraform Cloud entity scoped to a company/division |
| Local Execution Mode | Terraform runs locally; state uploaded to TFC |
| Remote Execution Mode | Execution happens in TFC, triggered manually |
| VCS Execution Mode | Remote execution triggered by source control changes to specified directories |
| Agent Mode | Remote execution in user-provided compute; enables access to private infrastructure |
| Terraform Workspace Manager | Tyler-built automation to create and manage TFC workspaces via GitHub YAML |

**Getting access to Terraform Cloud:**
1. Submit a help desk ticket to allow your account to access the appropriate TFC organization.
2. Contact the org owners (for `tyler-corp`, submit a JIRA ticket) for an invitation.

### Terraform Workspace Manager

Live docs:
- Part I: https://docs.tylerdev.io/platform-architecture/dev-ops/infrastructure-as-code/terraform/workspace-manager-p1
- Part II: https://docs.tylerdev.io/platform-architecture/dev-ops/infrastructure-as-code/terraform/workspace-manager-p2
- AWS Dynamic Auth: https://docs.tylerdev.io/platform-architecture/dev-ops/infrastructure-as-code/terraform/configure-dynamic-aws-auth

**Use when:** A team needs new Terraform Cloud workspaces for a project.

**Part I — Creating a new project:**

1. Navigate to https://github.com/tyler-technologies/onetyler-tf-workspace-management/
2. Create a branch; add a YAML file in `/team-definitions/`. The filename becomes the project name and management repo prefix.
3. Submit a PR — OneTyler devops team reviews and merges.
4. Upon merge, automation creates:
   - A dedicated TFC project
   - A workspace to manage workspaces within that project (`<team>-tf-workspace-management`)
   - A GitHub repo for that project's workspace management
   - AWS role configuration for dynamic auth (if configured)
   - Terraform teams with access to the project

**Part II — Managing workspaces within a project:**

In the generated `<team>-tf-workspace-management` repo, add YAML files in `/configuration/`. One file = one collection of related workspaces.

**Workspace naming pattern:** `<workspace-prefix>-<project_name>-<file_name>-<environment_name>` (default prefix: `tcp-app`)

**Variable precedence (lowest to highest):**
1. `global-config.yaml` `global_config` section
2. `global-config.yaml` environment section
3. Individual YAML file `stackset_config` section
4. Individual YAML file environment section

**Sensitive variable storage:**
1. Add a GitHub Actions Secret in the `tf-workspace-management` repo.
2. Expose it in `.github/workflows/terraform.yaml` `env` section.
3. Reference it in workspace YAML as `{{ .Env.YOUR_SECRET_NAME }}` with `sensitive: true`.

**HCL variables** (list, map, object, boolean) require `hcl: true` in the YAML.

### AWS Dynamic Authentication for Terraform

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/infrastructure-as-code/terraform/configure-dynamic-aws-auth

The Terraform Workspace Manager can create and manage AWS IAM roles for use in TFC authentication with AWS.

**Process:**
1. Ensure Terraform Cloud is configured as an identity provider in the AWS account.
2. In `onetyler-tf-workspace-management`, set `auto_update: true` and define `dynamic_aws_auth` with existing IAM role ARNs (restricted to the `<project>-tf-management` workspace). Each entry needs a unique `id`.
3. Upon apply, TFC configures those IAM roles as environment variables in the management workspace.
4. In the `<project>-tf-management` GitHub repo YAML, set `aws_dynamic_auth_info.id` to match the logical ID from step 2.
5. Upon apply, the management workspace creates workspace-specific admin IAM roles with trust policies scoped to only allow the specific workspace.

**Limitation:** Workspace Manager will not create the role used to create other IAM roles — that stays with the owners of the management workspace.

---

## TCP AWS Infrastructure

### High-Level Architecture

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/01-aws-infrastructure

TCP operates a federated group of AWS accounts linked by shared VPCs. This replaced the original monolithic single-account approach to improve security and account isolation. Each application team owns their own AWS account; TCP provides the shared networking and EKS compute layer.

**Five environments:**
| Environment | Harness ID | Purpose |
|---|---|---|
| tcpci primary | tcpci-1 | CI/dev |
| tcpqa primary | tcpqa-1 | QA |
| tcpqa secondary (DR) | tcpqa-1-us-east-1 | QA failover |
| tcpprod primary | tcpprod-1 | Production |
| tcpprod secondary (DR) | tcpprod-1-us-west-2 | Production failover |

No secondary cluster exists for tcpci.

### Shared VPC

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/02-shared-vpc

The TCP Shared VPC connects application team AWS accounts to the central EKS clusters through a distributed networking model.

**Subnet types:**

| Type | Routes | Example services |
|---|---|---|
| Public | Outbound: Internet via IGW; Inbound: Internet, Public/Private subnets | Public Load Balancer, Public API Gateway |
| Private | Outbound: Internet via NAT; Inbound: Public/Private subnets | EC2, Lambda, Fargate, Private LB/API Gateway |
| Isolated | No outbound; Inbound: Private subnet only | RDS |

**To add a resource to the shared VPC (from an app team's account):**
1. Create a security group allowing inbound access from the appropriate EKS security group.
2. Create the AWS resource using that security group and one of the shared VPC subnets.

**Adding your account to the shared VPC:**
- Submit a PR to [tcp-infrastructure](https://github.com/tyler-technologies/tcp-infrastructure) adding your account number to the `shared_accounts` list in the appropriate environment's `main.tf`.

**CIDR ranges and EKS security groups per environment:**

*TCPCI (us-west-2):*
- Public: `172.11.120.0/23`, `172.11.122.0/23`, `172.11.124.0/23`
- Private: `172.11.0.0/19`, `172.11.32.0/19`, `172.11.64.0/19`
- Isolated: `172.11.96.0/21`, `172.11.104.0/21`, `172.11.112.0/21`
- EKS SG: `sg-0699078209f88265b`

*TCPQA (us-west-2):*
- Private: `172.18.0.0/19`, `172.18.32.0/19`, `172.18.64.0/19`
- EKS SG: `sg-0a44cf5b969f85ebe`

*TCPPROD (us-east-1):*
- Private: `10.148.128.0/19`, `10.148.160.0/19`, `10.148.192.0/19`
- EKS SG: `sg-0b51e71a54247c186`

**Internal ingress pattern (for private services):**
```yaml
annotations:
  kubernetes.io/ingress.class: nginx-alb-internal
  nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  rules:
    - host: internal.tcpci.com
      http:
        paths:
          - path: /[yournamespace]/[yourservice](/|$)(.*)
            backend:
              serviceName: [yourservice]
              servicePort: 80
```

### CI/CD Pipelines

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/03-ci-cd-pipelines

The TCP/TID CI/CD pipeline uses:
- **GitHub Actions** for building and packaging code into Docker images
- **Harness** for deploying Docker images to Kubernetes

A Harness delegate runs as a deployment inside the EKS cluster, maintains a web socket connection to the Harness SaaS, receives YAML manifests from Harness, and applies them via the Kubernetes API. Docker images are pulled directly from Artifactory.

### Karpenter Node Consolidation Schedule

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/04-karpenter-node-conslidate-scheulde

Automatically adjusts Karpenter node consolidation policy based on time-of-day to save ~20+ EC2 instances per night.

| Period | Policy | Cron (UTC) | Local (Eastern) |
|---|---|---|---|
| Business Hours | `WhenEmpty` | `0 9 * * 1-5` (Mon–Fri) | 4 AM |
| Off Hours | `WhenEmptyOrUnderutilized` | `0 2 * * *` (Daily) | 9 PM |

**Current status:**
- TCPCI (us-west-2): Enabled (~20+ instances/night saved)
- TCPQA (us-west-2): Enabled (~15+ instances/night saved)
- TCPQA (us-east-1), TCPPROD: Disabled

**Verify consolidation policy:**
```bash
kubectl get nodepool karpenter -o jsonpath='{.spec.disruption.consolidationPolicy}'
```

**Debug:**
```bash
kubectl get cronjobs -n karpenter
kubectl logs -n karpenter -l job-name=karpenter-set-whenempty
```

Source: https://github.com/tyler-technologies/tcp-eks-manage/tree/main/modules/karpenter

---

## OneTyler Terraform Docs — AWS Resources

These documents describe how the TCP team provisions specific AWS resources with Terraform in a multi-region (primary + secondary DR) configuration. Other teams may need to adapt these patterns (fewer regions).

### General Infrastructure Guidelines

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/corpdev-tf-docs/general-guidelines

**Shared infrastructure (managed centrally, not per-service):**
- VPC, EKS cluster, ALBs
- Redis, ElastiCache
- S3 logging bucket
- KMS keys for TCP services
- Route53 zones and wildcard DNS
- Harness Application Definition, Environment Definitions, Pipelines

**Per-service infrastructure rules:**
- Each TCP service "owns" its supporting infrastructure (RDS, DynamoDB, S3, etc.)
- **Naming pattern:** `<namespace>-<environment>-<service-name>-<optional-attribute>`
  - Namespace: `tcp`; Environment: `tcpci`, `tcpqa`, `tcpprod`
  - Avoid "primary", "replica" in names — use region name if unique identification is needed

**Required tags on all AWS entities:**

| Tag | Value |
|---|---|
| `Product` | `tcp` |
| `division` | `onetyler` |
| `managedby` | `terraform` |
| `workspace` | `<terraform cloud workspace name>` |
| `gitrepo` | `<github repo name + path to terraform root>` |
| `backup-plan-selection` | `<name of appropriate backup plan>` |

**Encryption rules:**
- All disk-storing entities: use custom KMS key (per-environment ARNs listed in per-resource docs)
- Exception: S3 buckets fronted by CloudFront → use built-in AWS S3 encryption key
- SNS/SQS: generate your own custom KMS key (not the shared one)

**Secrets:** Store all secrets in AWS Secrets Manager with naming prefix `tcp/<environment>/shared/`. Expose to Harness through dedicated Harness secret managers (read-only access).

### Creating a Terraform Cloud Workspace

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/corpdev-tf-docs/creating-a-workspace

TCP Cloud Platform workspaces are in `corpdev-tcp-services-tf-workspace-management`: https://github.com/tyler-technologies/corpdev-tcp-services-tf-workspace-management

**Standard workspace YAML template:**
```yaml
stackset_config:
  create_workspace: true
  execution_mode: "remote"
  allow_destroy_plan: true
  auto_apply: false
  terraform_version: "1.1.4"
  working_directory: /infrastructure
  vcs_repo:
    enabled: true
    branch: <default_branch>
    repo_name: <github_repo_name>
  variables:
    - key: global_var
      value: "not-a-secret"
    - key: secret_var
      value: {{ .Env.DB_SECRET }}
      sensitive: true
environments:
  tcpci:
    variables:
      - key: tcpci_var
        value: "this-is-ci"
  tcpqa:
    variables: []
  tcpprod:
    variables: []
  onetime_config:
    working_directory: /infrastructure/onetime_config
    variables: []
```

**Note:** A single AWS account backs tcpqa + tcpqa-failover, and another backs tcpprod + tcpprod-failover — so only 3 environment workspaces (tcpci, tcpqa, tcpprod) are needed even though 5 EKS clusters exist.

Use the `onetime_config` environment for Harness resources. If you only need Harness resources (no AWS resources), use only the `onetime_config` workspace.

### DynamoDB Global Tables

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/corpdev-tf-docs/dynamo

TCP uses DynamoDB global tables (bi-directional replication across all regions). No DR action is needed for DynamoDB during regional failover — all regional tables remain available.

**KMS key ARNs by environment/region:**

| Environment | Region | KMS ARN |
|---|---|---|
| tcpci | us-west-2 | `arn:aws:kms:us-west-2:740289861468:key/79b86f4b-c980-4dad-bd81-e937f34fa490` |
| tcpqa | us-west-2 | `arn:aws:kms:us-west-2:740289861468:key/171f41e2-d8ed-4cee-b8ff-8a2983c60e39` |
| tcpqa | us-east-1 | `arn:aws:kms:us-east-1:740289861468:key/9b2bb50e-1f86-444a-9f83-077a362a9e15` |
| tcpprod | us-east-1 | `arn:aws:kms:us-east-1:180511163127:key/abf329e2-d62a-49b2-9453-6603e301a8eb` |
| tcpprod | us-west-2 | `arn:aws:kms:us-west-2:180511163127:key/fc6f508e-05dd-45b4-8bec-dc82a6207f54` |

Reference example repo: https://github.com/tyler-technologies/tcp-user-admin

### Global RDS Instances

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/corpdev-tf-docs/rds

TCP uses Aurora global instances: primary region has read+write; secondary region has read-only (write inactive). Replication is one-way (primary → secondary). During failover, replication is broken and secondary is promoted to read-write. **Failovers are permanent** — a new secondary must be created afterward.

KMS key ARNs are the same as for DynamoDB (see table above). Additional variables needed include subnets, security groups, Datadog lambda ARNs, and Harness secret manager names per environment — see the Blueprint docs for the full table.

Reference example repo: https://github.com/tyler-technologies/tcp-app-availability

**Harness secret naming pattern for RDS:**
```
tcp-<environment_name>-<service_name>-rds-<aws_region>
```

### Replicated S3 Buckets

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/corpdev-tf-docs/s3

TCP uses S3 Cross-Region Replication (CRR) — bi-directional (unlike RDS). No changes needed in S3 during regional failover; workloads in both regions point to their own bucket which stays in sync.

**Exception:** S3 buckets fronted by CloudFront must use the built-in AWS S3 KMS key (not the custom key).

KMS key ARNs are the same as the table in the DynamoDB section. Logging bucket names follow the pattern `<region>-<account-id>-s3-logging-bucket`.

Reference example repo: https://github.com/tyler-technologies/tcp-provisioningservice

### Secrets Management

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/corpdev-tf-docs/secrets-management

Use AWS Secrets Manager for all secrets. Secret naming prefix: `tcp/<environment>/shared/<service>/<type>`.

**Two patterns:**
1. **Region-independent secrets** (e.g., API lookup keys): Use AWS Secrets Manager replication to copy secret to another region.
2. **Region-dependent secrets** (e.g., RDS connection strings): Create separate secrets per region.

**Harness secret managers (read-only access, scoped by prefix and KMS key):**

| Environment | Region | Manager Name | Secret Prefix |
|---|---|---|---|
| tcpci | us-west-2 | `tcp-tcpci-temp` | `tcp/tcpci/shared` |
| tcpqa | us-west-2 | `tcp-tcpqa-us-west-2-temp` | `tcp/tcpqa/shared` |
| tcpqa | us-east-1 | `tcp-tcpqa-us-east-1-temp` | `tcp/tcpqa/shared` |
| tcpprod | us-east-1 | `tcp-tcpprod-us-east-1-temp` | `tcp/tcpprod/shared` |
| tcpprod | us-west-2 | `tcp-tcpprod-us-west-2-temp` | `tcp/tcpprod/shared` |

**Harness secret naming convention:**
```
tcp-<environment>-<service-name>-<secret-type>-<aws-region>
```
Example: `tcp-tcpqa-platform-rds-us-east-1`

Even with replicated AWS secrets, you must create **separate Harness secrets for each AWS region**.

### SNS and SQS (Replicated)

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/corpdev-tf-docs/sns-sqs

SNS and SQS have no native AWS replication. TCP's strategy: create a copy in both primary and secondary regions. Design note: plan for the case where in-flight SQS/SNS messages are lost during a disaster — ensure data can be replayed.

Use a Terraform module pattern (see tcp-webhook-api for a reference) that creates primary and replica resources. SNS/SQS must use their own custom KMS key (not the shared one).

Reference: https://github.com/tyler-technologies/tcp-webhook-api/blob/main/infrastructure/main.tf

### Harness Services and Overrides via Terraform

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/corpdev-tf-docs/harness

Harness resources (service, artifact source, environment overrides, git connector, deploy key) live in the `onetime_config` workspace.

**Recommended approach — use the item template:**
```bash
dotnet new -i "TCP.Item.Templates::*"
dotnet new tcp-tf-onetime -H <GITHUB_REPO_NAME>
# With separate names:
dotnet new tcp-tf-onetime -H <HARNESS_SERVICE_NAME> -G <GITHUB_REPO_NAME> -D <DOCKER_IMAGE_NAME> -Te <TERRAFORM_WORKSPACE_PREFIX>
# Also scaffold git2consul resources:
dotnet new tcp-tf-onetime -H <GITHUB_REPO_NAME> -I
```

**Manual approach:** Copy Terraform files from tcp-app-availability: https://github.com/tyler-technologies/tcp-app-availability/tree/master/infrastructure/onetime_config

Workspace name prefix in `terraform.tf`:
```
tcp-app-onetyler-tcp-services-<your_workspace_name>-
```

### Git2Consul Configuration

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/corpdev-tf-docs/git2consul

git2consul posts JSON configuration from GitHub repos to Consul. Each repo that uses git2consul has five environment configuration folders: `tcpci`, `tcpqa`, `tcpqa-us-east-1`, `tcpprod`, `tcpprod-us-west-2`.

GitHub webhooks call git2consul on merge to the default branch. The `tcp-platform-configuration` repo's git2consul deployment YAML must be updated to include your service's SSH key. Create all resources via Terraform in the `onetime_config` workspace.

Reference: https://github.com/tyler-technologies/tcp-service-url-api

### FAQ — Backups, DR, Patches, Vulnerabilities

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/tcp-aws-infrastructure/faq

**Backup retention:** CI: 5 days | QA: 10 days | Prod: 30 days

**Backup services:** AWS Backup covers Aurora, DynamoDB, EBS, EC2, EFS, EKS, RDS, Storage Gateway. Backups are copied to the DR region. Databases are backed up daily.

**Patch cadence:** EKS minor version updates ~1–2 times per year. RDS/Aurora uses auto minor version upgrade. AWS-managed services (S3, ElastiCache, DynamoDB) are patched by AWS.

**Application teams do NOT have access to TCP AWS console.** Request resource status via support ticket. Use Datadog for monitoring your own services.

**Vulnerability toolchain:** Gitleaks (secret detection in code/build), JFrog Xray (artifact scanning), Aqua (deployed image scanning), Datadog (runtime monitoring).

**Privx access:** External teams can access their databases in TCP accounts via Privx — file a support ticket with the resource name and access duration needed.

---

## Disaster Recovery — Design Guides

### General Guidelines and Definitions

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/disaster-recovery/guide/general-guidelines

| Term | Definition |
|---|---|
| Application Up State | Objective, testable criteria that determine when an application is fully functional |
| Disaster Recovery | Restoring application and data after a catastrophic event (not routine outages or data corruption) |
| RTO | Max acceptable time from disaster occurrence to service restoration |
| RPO | Max acceptable data loss (measured as time since last backup/sync) |
| Partial Failover | Failing over only the specific impacted service, not the entire region |

**DR modes available:**

| Component | Low RPO/Low RTO | Recovery from Backup |
|---|---|---|
| Aurora RDS | Cross-region read replica cluster | Restore from snapshot |
| DynamoDB | Global Tables | Restore from snapshot |
| S3 | Cross-region replication (CRR) | Restore from backup |
| OpenSearch | Replication from active region | None |
| EFS | Replication | Restore from backup |

**Assets that do NOT need recovery:** CloudFront distributions, Route53 zones, IAM assets.

**Assets that CANNOT be recovered:** SQS/SNS messages, ActiveMQ messages — plan for data replay.

### Designing a Recovery Process

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/disaster-recovery/guide/designing-recovery-process

**Step 1 — Define RTO/RPO targets.** Consider: contractual obligations, dependent services' RTO/RPO, cost, impact of data loss, interactions with external systems (e.g., payment processors). **Your RTO/RPO cannot be lower than your dependencies' RTO/RPO.**

**Step 2 — Identify non-recoverable data stores.** Review SQS, ActiveMQ, etc. — if losing in-flight messages is unacceptable, implement message replay capability.

**Step 3 — Choose recovery model:**

| | Low RPO/Low RTO | Recovery from Backup |
|---|---|---|
| Data preservation | Nearly all | Depends on backup frequency |
| Time to recover | Low (infra pre-staged in DR region) | Higher |
| Cost | Higher (all infra replicated) | Lower |
| Complexity | Lower (configs set in advance) | Higher (configs must be set after recovery) |
| Partial failover | Straightforward | Complicated |

For backup-based recovery, configure two backup vaults (source region + recovery region), secured with KMS keys.

**Step 4 — Recover specific components** (see component-specific sections below).

### DynamoDB DR

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/disaster-recovery/guide/dynamo-recovery

**Low RPO/Low RTO:** Use DynamoDB global tables — bi-directional real-time replication. No additional action during recovery. Reference: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/V2globaltables_HowItWorks.html

**Recovery from snapshot:** Configure backup rule with frequency matching RPO; destination vault must be in the recovery region. Restore using AWS Backup: https://docs.aws.amazon.com/aws-backup/latest/devguide/restoring-dynamodb.html — ensure compute workloads have permissions to the restored table.

### EFS DR

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/disaster-recovery/guide/efs-recovery

**Low RPO/Low RTO:** Replicate EFS to DR region. At disaster time, break replication and point DR workloads to the replicated filesystem. **Note:** EFS replication may lag up to 15 minutes. Reference: https://docs.aws.amazon.com/efs/latest/ug/efs-replication.html

**Recovery from backup:** Configure backup with RPO-matching frequency and destination in recovery region. Restore: https://docs.aws.amazon.com/aws-backup/latest/devguide/restoring-efs.html

### RDS DR

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/disaster-recovery/guide/rds-recovery

**Low RPO/Low RTO (read replicas):** Create a global RDS cluster with read replicas in the recovery region. During recovery, break replication and promote the replica:

```bash
aws rds promote-read-replica-db-cluster \
  --db-cluster-identifier <rds-instance-name> \
  --region <replica-region-name>
```

The promoted instance retains the original username/password. There is no way to "re-attach" a replica — after a test, destroy and recreate from the original database.

**Recovery from snapshot:** Set backup frequency = RPO; destination vault in recovery region. After restore, update network access and connection strings. Reference: https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-restore-snapshot.html

### S3 DR

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/disaster-recovery/guide/s3-recovery

**Low RPO/Low RTO:** Use bi-directional CRR (cross-region replication). Workloads in each region point to their own bucket, which stays in sync automatically.

**Recovery from backup:** Set backup frequency = RPO; destination vault in recovery region. Restore to a new bucket; update workload permissions and connectivity settings.

### EKS Workload DR

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/disaster-recovery/guide/eks-workload-recovery

**Low RPO/Low RTO:** Pre-create all Harness secrets and configurations for both primary and recovery regions. Deploy services to recovery environments with **0 replica count** (deployments exist but no pods run). During recovery, scale up replica count.

**Recovery from backup:** After AWS assets are restored, create all Harness configuration items with the new asset names/connection strings, then deploy correct service versions to the recovery EKS cluster.

---

## Disaster Recovery — Regional Failover Runbooks

Live docs:
- Decision Tree: https://docs.tylerdev.io/platform-architecture/dev-ops/disaster-recovery/regional-failover/dr-decision-tree
- Failover Runbook: https://docs.tylerdev.io/platform-architecture/dev-ops/disaster-recovery/regional-failover/runbook
- Recovery Runbook: https://docs.tylerdev.io/platform-architecture/dev-ops/disaster-recovery/regional-failover/recovery-runbook

**Overview:** TCP runs primary EKS clusters in one region and pre-staged secondary/failover clusters (scaled to zero) in another. Regional failover is a last resort for full regional AWS failures. **Regional failovers are permanent** — the secondary becomes the new primary and a new secondary is created afterward.

### DR Decision Checklist (Incident → Failover Decision)

**1. Incident Detection & Triage:**
- [ ] Acknowledge PagerDuty alert
- [ ] Confirm actual incident (if Datadog monitor self-recovered → close and abort)

**2. Debug the Incident:**
- [ ] Review Datadog errors, traces, dashboards
- [ ] Review Kubernetes Explorer
- [ ] Check AWS Service Health Dashboard
- [ ] Check social media/DownDetector
- [ ] Classify: not an AWS issue → escalate to OneTyler Dev or Infra team (do NOT failover)

**3. Assess AWS Components:**
- [ ] Networking: ALB, Route Tables, Internet Gateway, NAT Gateway
- [ ] VPC-bound services: OpenSearch, ElastiCache, RDS
- [ ] If impacted service is in the above list → proceed with failover
- [ ] Otherwise → update AWS config for specific service only (partial failover)

**4. Execute Failover:**
- [ ] Announce to stakeholders via [TCP DR Status Teams channel](https://teams.microsoft.com/l/channel/19%3A3d14dd3e64f945158bb25193a6b34a2c%40thread.tacv2/TCP%20Disaster%20Recovery%20Status?groupId=d9db441d-35fa-433c-8fe0-ff7fe5825d3c&tenantId=7cc5f0f9-ee5b-4106-a62d-1b9f7be46118)
- [ ] Contact DR-dependent teams via [OneTyler DR Collaboration Teams channel](https://teams.microsoft.com/l/channel/19%3ACx0b8ZXk3FrG0V6Zs0XXTBr6am5mkzZttjyjvg-4s_E1%40thread.tacv2/CorpDev%20DR%20Collaboration?groupId=d9db441d-35fa-433c-8fe0-ff7fe5825d3c&tenantId=7cc5f0f9-ee5b-4106-a62d-1b9f7be46118)
- [ ] Switch environment to secondary AWS region
- [ ] Update AWS service configurations to point to secondary region
- [ ] Run validation tests; confirm stability
- [ ] Mark incident resolved; notify stakeholders

**Post-incident:** Write a [Post Mortem in Coda](https://coda.io/d/OneTyler-Engineering-Center_dEyhmwumaY8/Post-Mortems_su1iAXax); identify improvements.

### Failover Runbook — Preparing

**Validate primary cluster (DR test only):**
```bash
# Run tcp-cluster-validation in Harness (select tcpqa-us-west-2 environment)
# Navigate to: https://app.harness.io/ng/account/NVsV7gjbTZyA3CgSgXNOcg/module/cd/orgs/CorpDev/projects/Cloud_Platform/pipelines/Single_Environment_K8s_Job_Deployment/executions
```

Local ingress validation:
```bash
aws eks update-kubeconfig --region us-west-2 --name tcpqa-1-eks
./tcp-cluster-validation
```

**Identify AWS Backup recovery point:**
```bash
aws backup list-recovery-points-by-backup-vault \
  --backup-vault-name <vault-name> \
  --by-resource-type EKS \
  --region us-west-2 \
  --query "RecoveryPoints[*].[RecoveryPointArn,CreationDate,Status]" \
  --output table
```

For DR test (optional — create a dedicated backup):
```bash
aws backup start-backup-job \
  --backup-vault-name <vault-name> \
  --resource-arn arn:aws:eks:us-west-2:<account-id>:cluster/<cluster-name> \
  --iam-role-arn <iam-role-arn> \
  --region us-west-2
```

**Switchover DNS and promote DR replicas** (using tcp-dr-automation):
```bash
git clone https://github.com/tyler-technologies/tcp-dr-automation
# For TEST:
configfile="tcpqa.yaml"
# For PRODUCTION:
configfile="tcpprod.yaml"

./dr.sh break --configfile="$configfile" --profile=<aws-profile>
# Verify RDS list, type "yes", wait 3–5 minutes
```

### Failover Runbook — Scaling the Cluster

Automated script available in Harness: https://app.harness.io/ng/account/NVsV7gjbTZyA3CgSgXNOcg/module/cd/orgs/CorpDev/projects/Cloud_Platform_Tools/pipelines/Single_Environment_K8s_Job_Deployment — select `tcp-pod-scale-up` service.

**Manual steps:**

Set replica count:
```bash
numpods=2   # for QA
numpods=3   # for PROD
```

Restart git2consul (must run first):
```bash
for ns in $(k get deploy -A | grep 'git2consul-deployment'| awk '{print $1}'); do
  k -n "$ns" rollout restart deploy $(k get deploy -n "$ns" | grep 'git2consul-deployment'| awk '{print $1}')
done
```

Scale OneTyler namespaces (by startup tier):
```bash
# infra tier (repeat with core-service, service, ui, finalize tiers)
for ns in 'cloudplatform-injector' 'tidgateway' 'tidops' 'cloudplatform'; do
  kubectl -n "$ns" scale deploy --replicas="$numpods" -l startup.tylertech.tcp/tier=infra,deploy.tylertech.tcp/single-replica!=true
  kubectl -n "$ns" scale deploy --replicas=1 -l startup.tylertech.tcp/tier=infra,deploy.tylertech.tcp/single-replica=true
done
```

Restore other teams' resources from AWS Backup:
```bash
# List recovery points in DR vault
aws backup list-recovery-points-by-backup-vault \
  --backup-vault-name <dr-vault-name> --by-resource-type EKS \
  --region us-east-1 \
  --query "RecoveryPoints[*].[RecoveryPointArn,CreationDate,Status]" \
  --output table

# Restore EKS resources from recovery point
aws backup start-restore-job \
  --recovery-point-arn <LATEST_RECOVERY_POINT_ARN> \
  --metadata '{"eks_cluster_name":"<target-cluster-name>"}' \
  --iam-role-arn <iam-role-arn> \
  --region us-east-1
```

### Recovery Runbook — Failing Back to Primary (after DR)

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/disaster-recovery/regional-failover/recovery-runbook

**Preconditions:** AWS confirms all primary region issues fully resolved; primary region validated in Datadog.

**Path A — Config-only failover (~15 minutes):**
- [ ] Update AWS service configurations to point back to primary region
- [ ] Validate with in-cluster and ingress DR validation tests
- [ ] Check Datadog monitors and synthetics

**Path B — Full regional failover (~5 hours):**
- [ ] Notify stakeholders via Teams
- [ ] Rebuild primary: delete primary RDS instances → recreate as replicas of current active region
- [ ] Break RDS replication → switch DNS back to primary region → scale up workloads in primary
- [ ] Validate (in-cluster tests, ingress tests, Datadog)
- [ ] Decommission secondary: scale down → delete RDS replicas → re-run Terraform to re-establish replication
- [ ] Notify stakeholders that failback is complete

**DR test rollback (test only — do NOT run in real DR):**
```bash
# Scale down all pods (except git2consul) in failover cluster
deplist=$(k -n cloudplatform get deployment --no-headers | grep -v git2consul | awk '{print $1}')
for dep in $(echo "$deplist"); do k -n cloudplatform scale deployment "$dep" --replicas=0; done

# Switch DNS back and delete replicated DBs
./dr.sh restore --configfile="$configfile" --profile=<aws-profile>
```

---

## Runbooks — P1 Incident Management

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/runbooks/01-incident-management/onetyler-p1-response

Environment: Production (`tcpprod-1`, `us-east-1`, cluster `tcpprod-1-eks`)
Teams channel: `@teams-OneTyler-P1-Prod`
All times: Pacific Time (PT)

### P1 On-Call Schedule

| Time Window (PT) | On-Call | Layer |
|---|---|---|
| 5:00 AM – 6:00 AM | Albert Sheynkman | Early Morning |
| 6:00 AM – 12:00 PM | Albert Sheynkman / Yuliia Slobodzian (rotation) | Morning Shift |
| 12:00 PM – 3:00 PM | Yuliia Slobodzian | Afternoon Transition |
| 3:00 PM – 6:00 PM | Mukta Puri | Late Afternoon |
| 6:00 PM – 2:00 AM | Raymond Gao | Evening Shift |
| 2:00 AM – 5:00 AM + Weekends | Off-Hours Rotation | Mukta / Albert / Raymond / Yuliia |

### Service Escalation Tiers

| Service | Primary | Secondary | Tertiary |
|---|---|---|---|
| TCP Services | P1 Primary | Mark Graves / Matt Bartel / Sami Khan | Chris Cummings / Zovin Khanmohammed |
| TID Gateway Workforce | P1 Primary | Zovin Khanmohammed / Harrison Ulrich | Jason Howard |
| TID C Service | P1 Primary | Rich Steck | Harrison Ulrich / Zovin Khanmohammed / Jason Howard |
| Infrastructure Service | P1 Primary | Mukta Puri / Albert Sheynkman | Chris Cummings |
| PETREG | Raymond Gao (dedicated) | — | — |

### PagerDuty Services

| Datadog Annotation | Pods monitored | Priority |
|---|---|---|
| `@pagerduty-tcp-p1-services-monitoring` | Pods with `p1-tcp` label | P1 — 24/7 |
| `@pagerduty-tid-gateway-workforce-monitoring` | TID Gateway Workforce | P1 — 24/7 |
| `@pagerduty-tid-c-service-monitoring` | TID C Service | P1 — 24/7 |
| `@pagerduty-tcp-infrastructure-monitoring` | Infrastructure | P1 — 24/7 |
| `@pagerduty-petreg-registration-monitoring` | PETREG | P1 — 24/7 |
| `@pagerduty-tcp-p2-services-monitoring` | OneTyler namespaces (no priority label) | P2 — business hours |

P2 namespaces: `cloudplatform`, `tidops`, `tidgateway`, `cloudplatform-injector`, `community-service-directory`

### Alert Triage — Kubernetes Commands

```bash
# Unhealthy pods across all namespaces
kubectl get pods -A | grep -v -E 'Running|Completed|Succeeded'
kubectl get pods -A | grep -E 'CrashLoopBackOff|Error|OOMKilled|Evicted|Pending|ImagePullBackOff'

# Inspect a specific pod
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace> --tail=100
kubectl logs <pod-name> -n <namespace> --previous --tail=100

# Check deployment status
kubectl get deployments -A | awk 'NR==1 || $4 != $3'
kubectl rollout status deployment/<deployment-name> -n <namespace>
kubectl rollout history deployment/<deployment-name> -n <namespace>

# Events
kubectl get events -A --field-selector=type=Warning --sort-by='.lastTimestamp'

# Node health
kubectl get nodes -o wide
kubectl describe node <node-name>
kubectl top nodes
kubectl top pods -A

# HPA and PVC
kubectl get hpa -n <namespace>
kubectl get pvc -n <namespace> | grep -v Bound
```

### External Vendor Escalation Contacts

| Vendor | Support URL | P1 Process |
|---|---|---|
| AWS | https://console.aws.amazon.com/support | Open case → "Business-critical system down" → Phone/Chat; 15-min response SLA (Enterprise) |
| Harness | https://support.harness.io/hc/en-us/requests | Submit at highest priority; email cx-escalation@harness.io |
| JFrog Artifactory | https://support.jfrog.com | Open case at highest severity; escalate via assigned TAM |
| Aqua Security | https://support.aquasec.com | https://support.aquasec.com/support/tickets/new — escalate via CSM |
| GitHub Enterprise | https://support.github.com | Select "Urgent" priority; 30-min response SLA (Premium/Premium Plus) |

---

## Runbooks — AWS SSO and EKS Access

### AWS CLI Login Setup (AWS SSO)

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/runbooks/02-aws-sso/aws-cli-login-setup

**Use when:** Setting up AWS CLI access to a OneTyler AWS account for the first time.

**Prerequisites:** Login access to tylerhost with the appropriate roles assigned. Contact the OneTyler Infrastructure team via [OneTyler Engineering Teams channel](https://teams.microsoft.com/l/channel/19%3Ae05d366187ac4aa689cf82f173b21b57%40thread.tacv2/Engineering?groupId=dc2864ad-8662-497b-98d5-7ba047f7ece7&tenantId=7cc5f0f9-ee5b-4106-a62d-1b9f7be46118) if roles are missing.

**Steps:**
```bash
aws configure sso --profile <name-of-aws-profile>
# SSO start URL: https://tylerhost.awsapps.com/start/#
# SSO region: us-east-1   <-- MUST be us-east-1; do NOT use us-west-2
# SSO registration scopes: <leave blank, press Enter>
# Then select AWS account and IAM role in the browser
```

Refresh expired credentials:
```bash
aws sso login --profile <name-of-aws-profile>
```

### EKS Kubeconfig Setup (AWS SSO)

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/runbooks/02-aws-sso/eks-kubeconfig-setup

**Use when:** Needing `kubectl` access to a TCP EKS cluster.

**Prerequisites:** Need either `EKS_Administrator` or `EKS_ReadOnly` role in tylerhost for the target AWS account.

**Steps:**
1. Configure AWS SSO profile (same as AWS CLI setup above; choose `EKS_Administrator` or `EKS_ReadOnly` role).
2. Create kubeconfig:
```bash
aws eks update-kubeconfig \
  --region <aws-region> \
  --name <eks-cluster-name> \
  --alias <kube-context-alias> \
  --profile <name-of-aws-profile>
```
3. Switch context:
```bash
kubectl config use-context <kube-context-alias>
```
4. Refresh expired credentials: `aws sso login --profile <name-of-aws-profile>`

---

## Runbooks — Kubernetes Upgrade

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/runbooks/03-kubernetes/upgrade

**Use when:** Upgrading an EKS cluster to a new minor Kubernetes version.

**Prerequisites:** kubectl, eksctl, awscli, jq — all up to date. Verified access to cluster and AWS account.

**General upgrade flow (1.20+ pattern — most current):**

1. Set environment variables:
```bash
export CLUSTER_NAME=<cluster-name>
export AWS_REGION=<region>
export AWS_PROFILE=<profile>
export TARGET_CLUSTER_VERSION=<target-version>
```

2. Verify context and version:
```bash
kubectl config current-context
kubectl version --short
kubectl get nodes
```

3. **Run EKS cluster backup before upgrading:**
```bash
aws backup start-backup-job \
  --backup-vault-name <vault-name> \
  --resource-arn arn:aws:eks:<region>:<account-id>:cluster/<cluster_name> \
  --iam-role-arn <iam-role-arn> \
  --region <region>

aws backup describe-backup-job --backup-job-id <backup-job-id>
```

4. Upgrade cluster control plane (~30+ minutes):
```bash
eksctl upgrade cluster --name $CLUSTER_NAME --approve
```

5. Check current add-on versions, then update each add-on:
```bash
# Check version
aws eks describe-addon --cluster-name $CLUSTER_NAME --addon-name <addon_name> \
  --query "addon.addonVersion" --output text --region $AWS_REGION --profile $AWS_PROFILE

# List available versions for target Kubernetes version
aws eks describe-addon-versions --addon-name <addon_name> \
  --kubernetes-version $TARGET_CLUSTER_VERSION \
  --query "addons[].addonVersions[].[addonVersion, compatibilities[].defaultVersion]" \
  --output text --region $AWS_REGION --profile $AWS_PROFILE

# Update add-on (vpc-cni, coredns, kube-proxy)
aws eks update-addon --cluster-name $CLUSTER_NAME \
  --addon-name vpc-cni --addon-version [version] \
  --region $AWS_REGION --profile $AWS_PROFILE
```

6. Update Terraform state (Terraform Cloud workspace): update `eks_kubernetes_version` and `eks_cluster_autoscaler_version` variables, run plan + apply.

7. Update managed node groups (~3–5 min per node):
```bash
# List node groups
eksctl get nodegroup --cluster=$CLUSTER_NAME --profile $AWS_PROFILE --region $AWS_REGION

# Upgrade to specific version
eksctl upgrade nodegroup --name=[node_group_name] --cluster=$CLUSTER_NAME \
  --kubernetes-version=$TARGET_CLUSTER_VERSION --region $AWS_REGION --profile $AWS_PROFILE \
  --timeout 120m

# Estimate upgrade time
eksctl get nodegroup --cluster $CLUSTER_NAME --region $AWS_REGION --profile $AWS_PROFILE -o json | \
  jq '.[] | {size: .DesiredCapacity, Name: .Name, ExpectedUpgradeTime: ([(((.DesiredCapacity * 3)|tostring), ((.DesiredCapacity * 5)|tostring)+" (min)")]| join("-"))}'
```

AWS upgrade guide reference: https://docs.aws.amazon.com/eks/latest/userguide/update-cluster.html

---

## Runbooks — PagerDuty Setup

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/runbooks/04-pagerduty/setup

**Use when:** Setting up PagerDuty for a new team/service or connecting Datadog monitors to PagerDuty.

**Access:** PagerDuty uses Okta SSO — https://tylertech.pagerduty.com/

**Setup flow:**

1. **Create a PagerDuty service** — top-level container owned by one team; each service links to one Slack channel.
2. **Configure the service:**
   - **Team:** members who receive alerts (names + email addresses)
   - **Escalation policy:** who to notify if first responder doesn't acknowledge within the timeout (default: 30 min)
   - **Schedule:** rotation schedule (who is on-call and when)
   - **Integrations:** Datadog + Slack

3. **Create the Datadog integration in PagerDuty** — you need the PagerDuty service name and integration key (found on the PagerDuty service integration page).

4. **Add PagerDuty annotations to Datadog monitors:**
```
{{#is_alert}}
@pagerduty-<YourServiceName>
## Alert message here
{{/is_alert}}
{{#is_alert_recovery}}
@pagerduty-<YourServiceName>
## Recovering from alert
{{/is_alert_recovery}}
{{#is_recovery}}
@pagerduty-<YourServiceName>
## System self-recovery
{{/is_recovery}}
```

5. **Store monitor configurations in Terraform** (two repos required):
   - https://github.com/tyler-technologies/terraform-tcp-env-infrastructure
   - https://github.com/tyler-technologies/tcp-infrastructure

6. **Schedules and escalation policies** are managed via Terraform: https://github.com/tyler-technologies/terraform-tcp-pagerduty

---

## Runbooks — Dev Tool Provisioning

### Aqua Security Provisioning

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/runbooks/dev-tool-provisioning-runbooks/aqua/provisioning

**Use when:** Onboarding a new team to Aqua container security scanning.

1. Log in to [Aqua](https://1pdaieaaj.cloud.aquasec.com/#/dashboard) via SSO.
2. **Create Application Scopes** (Administration → Application Scopes):
   - Name format: `<team>-app-<appname>-<clusterenvironment>` (e.g., `tcp-app-tylerhub-ci`)
   - Create four scopes per app: CI, QA, Prod, Global
   - Each scope needs: Artifacts (registry + image repo regex), Workloads (cluster + namespace)
3. **Create Role** (Access Management → Roles):
   - One role per app scope family (e.g., `tcp-app-twf-*`) using `application-operator` permission set
   - Add all related scopes (CI, QA, Prod, Global) to the role
4. **Add Users** (Access Management → Users):
   - Username: user's tylertech.com email
   - Roles: assign applicable roles
   - Use a random generated password (users authenticate via SSO; password is not used)
5. Notify the requester that onboarding is complete.

### Artifactory Provisioning

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/runbooks/dev-tool-provisioning-runbooks/artifactory/provisioning

**Access:** All engineering AD group members are auto-provisioned with Artifactory read-only accounts via Okta SSO. Log in at https://tylertech.jfrog.io/ui/login/ (click the cloud/SSO button).

**Team repositories:** Teams get `-local` repositories (e.g., `onetyler-npm-local`, `onetyler-nuget-local`, `onetyler-docker-local`) and `.devops`/`.publish`/`.service` automation users. Credentials are stored in LastPass under `Shared-artifactory-[teamname]`.

**Repository types:**
- **local**: Team-specific internal artifact storage (push target)
- **remote**: Proxy/cache for external repositories
- **virtual**: Aggregates local + remote for single pull endpoint (e.g., `npm`, `nuget`, `go`)

**Rules for sharing automation credentials:** Deliver over Slack and delete the message after the recipient copies the information. These credentials are for automation only, not for individual developer machines.

**Scratch repositories (for temporary developer testing):**
```
Docker:  tylertech-scratch-docker-local.jfrog.io
NuGet:   https://tylertech.jfrog.io/artifactory/api/nuget/scratch-nuget-local
NPM:     https://tylertech.jfrog.io/artifactory/api/npm/scratch-npm-local/
```

### Docker Hub User Provisioning

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/runbooks/dev-tool-provisioning-runbooks/docker-hub/create-user

Docker Hub login is controlled by Okta SSO. Users need a Docker Hub account to legally use Docker Desktop and `docker` commands locally.

**Three-step process:**

1. **Email HelpDesk** to add user to the Docker Users SSO group:
   - To: help.desk@tylertech.com
   - Subject: `Please ADD the following user(s) to the Docker Users SSO group`
   - Body: user's email address

2. **Invite user in Docker Hub** (requires admin privileges; only after HelpDesk resolves step 1):
   - Log in to https://hub.docker.com with admin account
   - Go to `tylerorg` organization → Invite Members → Emails or Docker IDs
   - Enter team name and user's email → send invite

3. **Email the user** with the Docker onboarding instructions (template attachment: `WelcomeDockerLicensee.docx`).

### GitHub Provisioning

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/runbooks/dev-tool-provisioning-runbooks/github/provisioning

**Use when:** Adding a new employee to the Tyler GitHub Enterprise organization.

**Required information per request:**
- Full name and @tylertech.com email
- Team assignment(s)
- Existing GitHub account name (optional)
- License type: Visual Studio with GitHub bundle, or GitHub-only standalone

**Provisioning steps:**
1. Check for existing Visual Studio license at https://manage.visualstudio.com/Subscribers
2. Assign/request appropriate license (contact Arleigh Hays for management console access)
3. Email HelpDesk to add user to the `Github Users AD group`:
   - Subject: `Please ADD the following user(s) to the Github Users AD group`
4. Send invitation from the [tyler-technologies People page](https://github.com/orgs/tyler-technologies/people) (search name/alias, not email — known limitation)
5. Email the new member using the appropriate informational mail template

**Note:** HelpDesk AD group addition takes ~1 hour. Users will get a 403 until complete. Invitation expires after 7 days.

**Permissions model:**
- All org members (not in a team) have broad read access to all repos
- Repos protected by branch lockdown + CODEOWNERS files
- Team + CODEOWNERS combination governs elevated (merge) privileges

**Removing a user:** Email HelpDesk with `REMOVE` instead of `ADD` in the subject line.

**GitHub Open Source org (tyler-enterprises):** Public-facing — apply strict rules: no internal references, no secrets, no PII, no dependencies on internal systems.

### PrivX User Management

Live doc: https://docs.tylerdev.io/platform-architecture/dev-ops/runbooks/dev-tool-provisioning-runbooks/privx/user-management

PrivX is the SSH access management tool for database and infrastructure access. All users authenticate via Tyler SSO.

**Available roles:** `tcp`, `lgd`, `erp`, `appraisaltax`, `civic-services`, `cybersecurity`, `tyler-privx-admins`

> **Critical:** Only OneTyler DevOps team members should be added to `tyler-privx-admins`.

**Adding a user:**

1. Ensure user exists in tyler-devtools Okta instance (https://tyler-devtools-admin.oktapreview.com/admin/users). If not, create them — add tylertech.com email as username and primary email. Notify user first (to avoid phishing concerns), then activate.
2. Determine the user's role by looking up their organization in Outlook Contacts ("Company" field).
3. Clone https://github.com/tyler-technologies/tcp-privx-management
4. Edit `privx-users.yml` in `nonprod_config/` (for non-prod) or `prod_config/` (for prod):
   - `username`: user's Tyler email
   - `user_source`: `oidc`
   - `mapping_attribute_value_list`: user's role(s)
5. Create a branch, commit (include JIRA ticket number), open a PR, merge to main.
6. In Terraform Cloud, review the generated plan:
   - Nonprod: https://app.terraform.io/app/tyler-corp/workspaces/tcp-app-onetyler-infra-privx-management-nonprod
   - Prod: https://app.terraform.io/app/tyler-corp/workspaces/tcp-app-onetyler-infra-privx-management-prod
7. Note: All null resources will appear as "replaced" — this is expected permanent diff. If plan looks correct, apply.

**Removing a user:** Follow the same repo/PR/apply process but remove the entry from `privx-users.yml`.

---

## Notes for the Chatbot

1. **This is internal OneTyler platform-engineering content only.** Nothing in this file is customer-facing. Do not share raw runbook commands or internal escalation contacts with external parties.

2. **Three areas have dedicated Foundry agents** and must not be answered from this file — hand off immediately: Ops Center, SAC (Support Access Center), and Identity (TID). See the "Dedicated-agent hand-off" box at the top.

3. **Harness governance is actively enforced.** The Governance Standard has a CTO Office approval date of March 16, 2026, and a legacy org deadline of September 30, 2026. Treat all governance rules as current and binding.

4. **DR failovers are permanent** in TCP's model. When asked about "switching back" after a failover, emphasize that failback involves a full reconstruction process (~5 hours for full regional failover), not a simple DNS flip.

5. **Environment context matters.** tcpci = CI/dev; tcpqa = QA; tcpprod = production. Secondary/failover environments (tcpqa-us-east-1, tcpprod-us-west-2) exist but run at zero replicas until a failover is executed.

6. **AWS SSO region is always us-east-1** for the SSO login step — never us-west-2, even for resources in us-west-2.

7. **Harness Feature Flag Classic is deprecated** — always direct new feature flag questions to Harness FME. Split was consolidated into Harness FME on February 5, 2026.

8. **KMS key ARNs** are environment and region-specific — when helping teams provision AWS resources, point them to the correct ARN from the tables in the corpdev-tf-docs sections rather than guessing.

9. **Cite file path** for follow-up: `/Knowledge-BP-General/Docusaurus-DevOps.md`
