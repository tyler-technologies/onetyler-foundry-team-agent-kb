# Platform Security — RDS IAM Auth, Akeyless Secrets Management, Vulnerability Scanning, WAF Rules

Source: Tyler Blueprint Docusaurus — `https://docs.tylerdev.io/platform-architecture/security/`
Domain: Blueprint General — Tyler Cloud Platform / Blueprint docs not served by a specialized Foundry agent
Audience: OneTyler engineers and product-team engineers deploying services on TCP EKS clusters; anyone integrating with OneTyler security tooling (RDS, secrets, container scanning, WAF).

**Companion documents:**
- `_START_HERE.md` — routing guide for this corpus
- `Docusaurus-PlatformOverview.md` — TCP architecture, AWS accounts, EKS cluster topology
- `Docusaurus-ServiceArchitecture.md` — service patterns, Kubernetes workloads
- `Docusaurus-DevOps.md` — Harness pipelines, GitHub Actions, CI/CD
- `Docusaurus-CloudPlatformAPI.md` — API patterns, identity tokens
- `Docusaurus-ProductSystemReg.md` — product registration, customer onboarding

---

## How to use this guide

| User intent | Go to section |
|---|---|
| Connect a .NET service to MySQL using IAM instead of a password | [RDS IAM Authentication](#rds-iam-authentication) |
| Emergency human access to an RDS database | [RDS — Human Database Access](#human-database-access) |
| Understand Akeyless secrets management design & structure | [Akeyless Secrets Management](#akeyless-secrets-management-design) |
| How Kubernetes workloads authenticate to Akeyless | [Akeyless — Kubernetes Access](#kubernetes-access) |
| How GitHub Actions authenticate to Akeyless | [Akeyless — GitHub Access](#access-from-github) |
| Scan container images for vulnerabilities | [Vulnerability Scanning](#vulnerability-scanning) |
| Register images with AquaSec in Harness pipeline | [Harness Shared Template](#harness-shared-template) |
| Block images with CVEs from deploying to EKS | [Admission Control](#admission-control) |
| Understand which countries are geo-blocked by WAF | [WAF Rules — GeoIP Blocking](#waf-rules-for-infrastructure-security) |

---

## Glossary

| Term | Meaning |
|---|---|
| RDS IAM Auth | AWS-native mechanism to authenticate database connections using IAM roles rather than passwords |
| Akeyless | SaaS secrets-management platform used by OneTyler; supports zero-knowledge encryption |
| Zero Knowledge Encryption | Akeyless feature where a customer-controlled key fragment is combined with Akeyless key fragments; Akeyless itself cannot decrypt secrets |
| AquaSec / Aqua Security | Container security platform used for vulnerability scanning and Kubernetes admission control |
| Trivy | Open-source AquaSec tool used in CI/CD pipelines to scan code, binaries, and images for CVEs |
| CVE | Common Vulnerabilities and Exposures — tracked vulnerabilities in software packages |
| WAF | Web Application Firewall — AWS WAF rules enforced in front of all OneTyler-hosted apps |
| ITAR | International Traffic in Arms Regulations — the country list OneTyler uses as the basis for GeoIP blocking |
| PrivX | Jump host used for emergency human access to RDS instances (`jump.tylerops.io` / `jump.nonprod.tylerops.io`) |
| corpdev_db_admin | Shared MySQL IAM user name used for RDS IAM authentication |
| onetylertools_dev / aws_devtools | AWS accounts where Akeyless gateways are deployed |

---

## RDS IAM Authentication

**Use when:** Connecting a service to a TCP MySQL database. RDS IAM Auth eliminates static passwords from connection strings and Kubernetes secrets.

**Benefits:**
1. Dynamic (ephemeral) credentials — no password stored in code or secrets managers
2. Connection strings no longer contain secrets
3. Root database password is not used for application connections

### Infrastructure Setup

1. Remove `password` from the MySQL server connection string.
2. Enable IAM authentication on the RDS cluster (`IAM authentication: enabled`).
3. Create the IAM-authenticated MySQL user and grant privileges:
   ```sql
   CREATE USER corpdev_db_admin IDENTIFIED WITH AWSAuthenticationPlugin AS 'RDS';
   GRANT ALL PRIVILEGES ON <database_name>.* TO 'corpdev_db_admin'@'%';
   ```
4. Attach this IAM permissions policy to the service account running the container:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": ["rds-db:connect"],
         "Resource": [
           "arn:aws:rds-db:<aws_region>:<aws_account>:dbuser:<cluster_unique_id>/corpdev_db_admin"
         ]
       }
     ]
   }
   ```

### Code Setup (.NET)

1. Add the `TCP.RdsIAMAuth` NuGet package to the project.
2. When configuring `DbContext`, register the interceptor:
   ```csharp
   options.AddTcpRDSMysqlIAMInterceptor(provider.GetRequiredService<ILoggerFactory>());
   ```

### Human Database Access

**Use when:** Emergency human access is required (not routine).

**Option A — AWS Secrets Manager root password:**
Retrieve the root master password from AWS Secrets Manager via PrivX.

**Option B — IAM token via AWS CLI (requires IAM policy or account admin):**

1. From your dev machine (not inside PrivX), generate a token:
   ```bash
   aws rds generate-db-auth-token \
     --hostname <cluster_write_endpoint> \
     --port 3306 \
     --region <aws_region> \
     --username corpdev_db_admin \
     --profile <your_aws_profile>
   ```
2. From the PrivX console, connect using the token as the password:
   ```bash
   stty -echo; set +o history
   mypass="--password <your_token>"; stty echo; set -o history
   mysql -h <rds_host> -u corpdev_db_admin --enable-cleartext-plugin $mypass
   ```
3. Enter the token from step 1 as the password.

**PrivX URLs:**
- Production: https://jump.tylerops.io/privx/home
- Non-production: https://jump.nonprod.tylerops.io/privx/home

**References:**
- AWS RDS IAM Authentication overview: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.IAMDBAuth.html
- NuGet package source: https://github.com/tyler-technologies/TCP.RdsIAMAut

---

## Akeyless Secrets Management Design

**Use when:** Understanding how OneTyler designs and deploys its Akeyless secrets management infrastructure, or configuring a service to use Akeyless for secrets.

> **Note:** This is the **design proposal** document. Refer to any published operations documentation on the OneTyler docs site for finalized implementation details.

### Design Principles

- **Zero Knowledge Encryption**: OneTyler controls a custom key fragment; Akeyless cannot decrypt OneTyler secrets without it.
- **Ephemeral credentials preferred**: SAML (humans), OIDC (GitHub, Terraform Cloud), k8s service account tokens, and IAM roles are the preferred auth methods. API keys are avoided.
- **Disaster recovery**: Secrets must be recoverable; CI instances in `us-west-2` and `us-east-1` share the same customer key fragment per environment.
- **Two Akeyless accounts**:
  - **OneTyler Internal** — secrets only OneTyler accesses
  - **OneTyler Shared** — secrets shared with external teams (e.g., product registration keys, Terraform Cloud tokens)

### Gateway Architecture

Akeyless gateways are Kubernetes workloads. One gateway can only target one Akeyless account.

| Environment | AWS Account | Regions | Gateway instances |
|---|---|---|---|
| CI & QA | `onetylertools_dev` | `us-west-2`, `us-east-1` | 4 per cluster (CI-Internal, CI-Shared, QA-Internal, QA-Shared) |
| Production | `aws_devtools` | `us-west-2`, `us-east-1` | Similar layout |

Customer key fragments are stored in AWS Secrets Manager and mounted in gateway deployments. Internal TLS uses dummy certificates within the cluster. Gateways communicate via Internet and ingress.

### Authentication Methods

| Method | Used by |
|---|---|
| k8s service account tokens | Kubernetes workloads (mapped per cluster/namespace/service account) |
| IAM roles / Role ARN | Non-k8s AWS entities such as Lambdas |
| OIDC / JWT | GitHub Actions, Terraform Cloud |
| SAML / Okta SSO | Humans |

**Important:** Any Kubernetes workload that needs Akeyless access must have a dedicated service account, even if not bound to an IAM role.

### Kubernetes Access

Akeyless provides a **k8s secret injector** (mutating webhook) that injects secrets as init containers or sidecars. Limitations:
- Only one injector per cluster; it can only target one Akeyless account.
- Workarounds being evaluated: Akeyless feature request, segregated area in OneTyler Internal, Akeyless SDK, or a custom injector.

Infrastructure configuration uses Terraform modules that allow individual services to configure access for their k8s service accounts.

### Access from GitHub

Repositories must be explicitly listed to use JWT access. PR-based automation is planned to simplify this.

### Access from Terraform Cloud

Terraform workspace manager grants access to specified areas. Service-specific plans get permissions scoped to their secret paths.

### Secret Path Structure (OneTyler Internal)

```
/OneTyler/secrets/{env}/application/{team}/{secret-group}/{k8s-service}
```
Environments: `ci`, `qa`, `prod`
Teams: `cloudplatform`, `tid-ops`, `tid-gateway`, `csd`

Infrastructure secrets:
```
/OneTyler/secrets/infrastructure/GitHub
/OneTyler/secrets/infrastructure/Harness
/OneTyler/secrets/infrastructure/Terraform
/OneTyler/secrets/infrastructure/Styra
/OneTyler/secrets/infrastructure/Aqua
/OneTyler/secrets/infrastructure/DataDog
```

Encryption keys:
```
/OneTyler/keys/ci
/OneTyler/keys/qa
/OneTyler/keys/prod
```

### Secret Migration — Current vs. Target State

| Secret type | Current flow | Proposed final state |
|---|---|---|
| **Kubernetes secrets** | GitHub action secret → Terraform → AWS Secrets Manager + Harness → K8s | Generated by app → entered into Akeyless → mounted via injector or SDK; rotated automatically |
| **CCF tokens** | Manual AWS Secrets Manager entry | Same as K8s secrets path above |
| **Product registration keys** | Entered into Harness by external team → GitHub Action → Harness pipeline → CRD | Entered into OneTyler Shared Akeyless → secret name in YAML → Harness pipeline → CRD; registration operator retrieves from Akeyless |
| **GitHub Artifactory credentials** | Static GitHub Org/Repo secrets | Akeyless generates short-lived Artifactory token; token expires after use |
| **Other GitHub secrets** | Static GitHub secrets | Stored in Akeyless; GitHub authenticates via JWT; access controlled by org/repo claims; rotation configured |
| **Terraform Cloud tokens** | Terraform-generated token stored as GitHub Actions Secret | Token in OneTyler Shared Akeyless; secret name in GitHub repo variables; custom rotator configured |

### Phase 1 Deliverables

1. K8s clusters and Akeyless gateways deployed in respective accounts and regions
2. Terraform modules to interact with Akeyless
3. Design and operations documentation published on OneTyler docs site

---

## Vulnerability Scanning

**Use when:** A product team needs to understand how to comply with OneTyler EKS container security requirements, or how to set up image scanning and registration.

### Why It Matters

Container image scanning detects known CVEs in OS packages and dependencies before they reach production. OneTyler uses **AquaSec** as its primary platform for scanning and admission control across all OneTyler EKS clusters (`tcpci.com`, `tcpqa.com`, `tylerportico.com`).

### Admission Control

AquaSec's Kubernetes admission controller is active in all OneTyler EKS environments. Images are **blocked** if they:
- Are not registered with AquaSec
- Contain high or critical vulnerabilities with known exploits
- Contain malware
- Contain sensitive data

### Product Team Security Requirements

All product teams deploying to OneTyler EKS clusters **must**:

1. **Implement vulnerability scanning** in their CI/CD pipeline (use Shared Trivy GitHub Actions)
2. **Register container images with AquaSec** in their CI/CD pipeline (use the Shared Image Registration GitHub Action or the Shared Harness Template)
3. **Ensure only registered images** with no high/critical vulnerabilities are deployed

Non-compliant images are rejected at the admission controller.

### AquaSec Portal

**URL:** https://cloud.aquasec.com/signin — sign in with SSO using your `@tylertech.com` email.

**Navigation path for image details:**
`Nine-box (top left) > Workload Protection > Images & Functions > Images > [search image name] > image:tag link`
- **Risk tab**: Policy compliance status
- **Vulnerabilities tab**: CVE details

**Access requests:** File a support ticket at https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386600308/Tyler+Cloud+Platform+TCP+Ops+Center+Related+Tickets+and+Permissions

### Shared GitHub Actions

Repository: https://github.com/tyler-technologies/corpdev-automation-shared

| Action | Purpose | README |
|---|---|---|
| Trivy Dotnet Security Scanner | CVE scan for .NET projects | https://github.com/tyler-technologies/corpdev-automation-shared/blob/main/.github/workflows/trivy-dotnet-scanner-shared.md |
| Trivy Go Security Scanner | CVE scan for Go projects | https://github.com/tyler-technologies/corpdev-automation-shared/blob/main/.github/workflows/trivy-golang-scanner-shared.md |
| Trivy Image Security Scanner | CVE scan for container images | https://github.com/tyler-technologies/corpdev-automation-shared/blob/main/.github/workflows/trivy-image-scanner-shared.md |
| Trivy npm Security Scanner | CVE scan for npm source directories | https://github.com/tyler-technologies/corpdev-automation-shared/blob/main/.github/workflows/trivy-npm-scanner-shared.md |
| Shared Image Registration Action | Register docker images with AquaSec | https://github.com/tyler-technologies/corpdev-automation-shared/blob/main/.github/workflows/image-registration-shared.md |

**Reviewing Trivy results:** Navigate to the Actions summary tab and scroll to the bottom. High and Critical vulnerabilities fail the workflow — they must be remediated before proceeding.

### Harness Shared Template

**Use when:** Registering images with AquaSec as part of a Harness deployment pipeline.

Steps to add the "Image Scan by Aqua Security" shared template:

1. Create a new **stage template** in your Harness project.
2. Add a stage of type `Deploy → Kubernetes`.
3. On the **Environment** tab, select `tcpci` for environment and infrastructure.
4. On the **Execution** tab, choose **Blank Canvas**.
5. Click **Add step > Use Template**, select the account-level **"Image Scan by Aqua Security"** template, and give it a name.
6. Save the template.
7. In your deployment pipeline, add a new stage **before any deployment stages**; select **Use Template** and pick your template.
8. In your pipeline trigger, copy `serviceRef` and `serviceInputs` values from the existing deploy stage to the new Aqua scan stage.

**Multiple images:** Override the `moreImages` variable in the template to include additional image names.

### Contact

OneTyler DevOps team: https://teams.microsoft.com/l/channel/19%3A1e6bcc02bd3242a193bf9171a51a0395%40thread.tacv2/Cloud%20Platform%20Community?groupId=d9db441d-35fa-433c-8fe0-ff7fe5825d3c&tenantId=7cc5f0f9-ee5b-4106-a62d-1b9f7be46118

---

## WAF Rules for Infrastructure Security

**Use when:** Understanding what traffic is blocked at the WAF level across all OneTyler-hosted applications.

### GeoIP Blocking (ITAR Country List)

OneTyler blocks traffic from countries on the ITAR (International Traffic in Arms Regulations) list to reduce risk surface, mitigate bot activity, and protect infrastructure availability. This applies to **all** apps hosted in OneTyler infrastructure.

**Blocked countries (IP-level block, HTTP 403):**

Afghanistan, Angola, Belarus, Myanmar, Cambodia, Central African Republic, China (PRC), Cuba, Cyprus, Democratic Republic of the Congo, Eritrea, Ethiopia, Haiti, Iran, Iraq, Kyrgyzstan, Lebanon, Liberia, Libya, Nicaragua, Nigeria, North Korea, Russia, Rwanda, Somalia, South Sudan, Sudan, Syria, Venezuela, Vietnam, Yemen, Zimbabwe

**Country codes (for WAF rule reference):** AF, AO, BY, CD, CF, CN, CU, CY, ER, ET, HT, IQ, IR, KG, KH, KP, LB, LR, LY, MM, NG, NI, RU, RW, SD, SO, SY, VE, VN, YE, ZW

**Example AWS WAF rule:**
```json
{
  "Name": "geo_block_countries",
  "Priority": 1,
  "Action": {
    "Block": {
      "CustomResponse": {
        "ResponseCode": 403,
        "CustomResponseBodyKey": "default_custom_body_response"
      }
    }
  },
  "Statement": {
    "GeoMatchStatement": {
      "CountryCodes": ["AF","AO","BY","CD","CF","CN","CU","CY","ER","ET","HT","IQ","IR","KG","KH","KP","LB","LR","LY","MM","NG","NI","RU","RW","SD","SO","SY","VE","VN","YE","ZW"]
    }
  }
}
```

**References:**
- D&I blocked countries (Socrata): https://socrata.atlassian.net/wiki/spaces/support/pages/3644883127/Countries+Blocked+from+Accessing+Our+Platform
- ITAR country list (official): https://www.ecfr.gov/current/title-22/chapter-I/subchapter-M/part-126/section-126.1

---

## Notes for the Chatbot

1. **RDS IAM Auth is the standard** for MySQL on TCP. When a team asks about database credentials or connection strings, direct them here. The IAM username is always `corpdev_db_admin` in OneTyler infrastructure.
2. **Akeyless is a design proposal as of the document date.** For the current (live) secrets tooling status, direct users to OneTyler DevOps or the published operations docs. This file captures the *intended architecture* and migration path.
3. **AquaSec requirements are mandatory gating requirements** — images that fail are blocked by the admission controller. This is not optional for product teams deploying to OneTyler EKS clusters.
4. **WAF GeoIP blocking is infrastructure-level** — it applies to all apps regardless of the product team. Product teams cannot override it. If a customer in a blocked country cannot access the platform, this WAF rule is the likely cause.
5. **Ops Center links** for access requests referenced in this file point to: https://tylertech.atlassian.net/wiki/spaces/TTI/pages/386600308/Tyler+Cloud+Platform+TCP+Ops+Center+Related+Tickets+and+Permissions — surface this URL verbatim when users ask how to request Harness or AquaSec access.
6. **Dedicated agents exist for:** Ops Center → https://docs.tylerdev.io/app-guides/ops/ops-center/overview/ | Support Access Center (SAC) → https://docs.tylerdev.io/ops/support-access-center/ | Identity → https://docs.tylerdev.io/identity — do not answer Ops Center, SAC, or identity-specific questions from this file; route to those agents instead.
