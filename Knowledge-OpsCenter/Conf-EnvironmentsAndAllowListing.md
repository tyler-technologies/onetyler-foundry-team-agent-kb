# TCP Environments and Allow-Listing Reference

Source: Confluence — *Environments* (SPY space) — https://tylertech.atlassian.net/wiki/spaces/SPY/pages/407175596/Environments
Domain: Ops Center
Audience: Tyler operational staff (deployment, implementation, support), customer IT admins, and product engineering teams who need (a) the canonical Ops Center URL for each environment, (b) **inbound allow-list entries** (root domain or DNS endpoint) so traffic from customer on-prem can reach the TCP cloud platform, and (c) **outbound allow-list entries** (cluster outbound IPs) so traffic from the TCP cloud platform can reach customer on-prem systems.

This document covers the **three AWS-based TCP environments** (CI, QA, Production), the **four Tyler Identity Enterprise (Okta) instances**, and a pointer to the supported-browsers list.

**Companion documents in this same Knowledge folder:**
- `Docusaurus-OpsCenter.md` → *Access — environment URLs* (same three Ops Center URLs distilled there; this file adds the allow-list IPs and inbound/outbound directionality).
- `Training-OpsCenterOperations.md` → *Basic Concepts — the three environments* and *Resources — General knowledge topics on Confluence* (referenced allow-listing detail for Workforce Direct/Managed orgs).
- `Docusaurus-Terminology.md` → *Environment* and *Tyler Cloud Platform (TCP)*.
- `Knowledge-Shared/Conf-OneTylerTickets.md` → *General Information / Inquiry* for filing a Cloud Platform support ticket (referenced repeatedly in this page).

---

## How to use this guide (quick decision guide)

| If the user wants to… | Go to section |
|---|---|
| Find the **Ops Center URL** for a given environment | **AWS-based environments — table** |
| Allow-list TCP environments on a **customer firewall** (inbound side) | **Allow-listing — inbound (on-prem → TCP)** |
| Allow-list customer IPs to **receive traffic from TCP** (outbound side) | **Allow-listing — outbound (TCP → on-prem)** |
| Get the **Tyler Identity (TID) host URLs** for Okta-based allow-listing | **Tyler Identity Enterprise (Okta)** |
| Sign on to TCP portals as a Tyler team member | **Signing on / getting added to a portal** |
| Find the **DataDog infrastructure dashboard** for TCP AWS environments | **Monitoring — DataDog dashboard** |
| Find the **supported browsers** list | **Supported browsers** |
| Get a **test account for TID Enterprise** | **TID Enterprise test accounts** |

---

## AWS-based environments

TCP runs three AWS-based environments. Each has a distinct root domain, Ops Center URL, set of cluster outbound IPs, and Tyler Identity authority pairing.

### Environment table

| Platform | Use | Authentication (TID instance / realm) | Root domain — inbound allow-list (on-prem → TCP) | Cluster outbound — outbound allow-list (TCP → on-prem) | Ops Center URL |
|---|---|---|---|---|---|
| **Continuous Integration (Development)** | CI | TID-Citizen CI & TID-Enterprise Preview | `tcpci.com` | DNS: `allow-list.tcpci.com` — see *CI cluster outbound IPs* below | https://admin.tcpci.com/portal/ops-center/manage-organizations |
| **Citizen & Enterprise (QA)** | Pre-Production | TID-Citizen QA & TID-Enterprise Preview | `tcpqa.com` | DNS: `http://allow-list.tcpqa.com` — see *QA cluster outbound IPs* below | https://admin.tcpqa.com/portal/ops-center/manage-organizations |
| **Citizen & Enterprise (Production)** | **Production** | **TID-Citizen PROD & TID-Enterprise Production** | **`tylerportico.com`** | DNS: `http://allow-list.tylerportico.com` — see *Production cluster outbound IPs* below | https://admin.tylerportico.com/portal/ops-center/manage-organizations |

For the **Tyler Identity Authority Usage** chart referenced under the authentication column, see the Confluence chart (linked from the source page).

---

## Allow-listing — inbound (on-prem → TCP)

For traffic going **from customer on-prem networks into the TCP cloud platform**, allow-list by **root domain**:

| Environment | Root domain to allow-list |
|---|---|
| CI (Development) | `tcpci.com` |
| QA (Pre-Production) | `tcpqa.com` |
| Production | **`tylerportico.com`** |

---

## Allow-listing — outbound (TCP → on-prem)

For traffic going **from the TCP cloud platform out to customer on-prem systems**, the customer needs to allow-list the cluster's outbound IP addresses. Tyler maintains a DNS allow-list endpoint per environment that resolves to the current set of egress IPs, plus the explicit IP list (subject to change).

### Preferred: use the DNS entry

| Environment | DNS allow-list endpoint |
|---|---|
| CI | `allow-list.tcpci.com` |
| QA | `http://allow-list.tcpqa.com` |
| Production | `http://allow-list.tylerportico.com` |

Customers whose firewall supports FQDN-based allow-lists should use these endpoints — the IP set may evolve over time, and resolving the FQDN at firewall-rule time keeps the customer's list in sync.

### Explicit IP lists (for firewalls that only support IPs)

#### CI cluster outbound IPs (`tcpci.com`)
- **44.225.249.146** (original)
- 18.213.216.179
- 52.73.150.69
- 23.21.151.254
- 18.188.186.251
- 52.15.131.57
- 18.224.164.158
- 54.215.254.203
- 54.241.53.184
- 54.176.241.103
- 54.244.117.102
- 44.235.198.25

#### QA cluster outbound IPs (`tcpqa.com`)
- 52.41.29.225
- 3.228.58.192
- 34.202.139.9
- 54.158.147.104
- 3.132.251.32
- 3.22.255.169
- 3.132.68.92
- 54.215.52.123
- 54.241.55.231
- 54.176.17.164
- 44.228.146.86
- 54.188.42.51

#### Production cluster outbound IPs (`tylerportico.com`)
- **3.214.129.200** (original)
- 52.3.78.222
- 54.86.150.104
- 3.211.38.10
- 52.45.130.133
- 3.224.33.232
- 3.209.222.104
- 54.165.37.167
- 3.128.0.106
- 18.117.14.226
- 18.116.94.195
- 18.219.163.37
- 3.12.23.7
- 3.143.118.40
- 3.131.47.186
- 3.128.194.127
- 184.72.13.128
- 184.169.232.151
- 13.52.14.157
- 13.52.47.104
- 13.52.115.69
- 52.8.239.86
- 50.18.154.230
- 13.52.60.31
- 35.161.139.26
- 35.164.206.98
- 35.86.29.43
- 50.112.73.115
- 35.167.7.237
- 35.160.55.223
- 54.187.79.236
- 44.233.132.79

> **Important:** these IP lists are point-in-time snapshots from the source page. **Always cross-check against the live Confluence page** before sharing with a customer — Tyler adds new egress IPs as clusters scale. The DNS allow-list endpoint is the most resilient way to stay in sync.

---

## Tyler Identity Enterprise (Okta)

Tyler Identity Enterprise (TID-E) is hosted on Okta. Customers using TID-E need to allow-list the relevant Okta-backed URIs **for both inbound and outbound traffic**. For Okta's own IP allow-listing guidance, see: https://help.okta.com/en/prod/Content/Topics/Security/ip-address-allow-listing.htm

### TID instances and URIs

| Instance (realm) | URI (both inbound/outbound traffic) |
|---|---|
| Tyler Identity Citizen — **QA/Dev** | `dev.tyleridentity.com` |
| **Tyler Identity Citizen — Prod** | **`tyleridentity.com`** |
| Tyler Identity Enterprise — QA | `devbroker.tyleridentity.com` |
| **Tyler Identity Enterprise — Prod** | **`broker.tyleridentity.com`** |

> Note: "Tyler Identity Enterprise" (TID-E) is the older Okta-based identity for Tyler workforce / customers. "TID Citizen" is the older naming for Community Access. In current customer-facing terminology, prefer **Identity Workforce** and **Community Access** — see `Docusaurus-Terminology.md`.

---

## Signing on / getting added to a portal

If you (a Tyler team member) don't yet have access to a TCP portal:

1. **Find a system administrator on your team** who already has access to the portal you need.
2. Have them go to **any portal in the list** → the **overflow kebab icon** on the portal card → **User management**.
3. Click the **+** button and add you using your `@tylertech.com` email.
4. Once added, go to your **Enterprise profile**: https://profile.tylerportico.com/portal/enterpriseprofile/settings/global (sign in with your Tyler AD credentials).
5. Navigate to your portal — for example, `https://coffeecup.tcpci.com/portal/administration/portal-settings` — once an admin has either made you a PortalAdmin or added you as a member in the portal's **Group Management** app (if the team has implemented group management).

If you're unsure about something, **file a Cloud Platform support ticket** (`Knowledge-Shared/Conf-OneTylerTickets.md` → *General Information / Inquiry*) and Tyler will help guide you.

### TID Enterprise test accounts

If you need a test account for TID-E, see the Tyler-internal Confluence page **"Utilizing TylerDev.IO for TID Workforce Testing"** at `https://tylertech.atlassian.net/wiki/spaces/TID/pages/388341759`.

---

## Monitoring — DataDog dashboard

Tyler maintains a unified DataDog dashboard covering all three TCP AWS environments:

- **Dashboard:** https://app.datadoghq.com/dashboard/z29-qry-srm/tcp-aws---infrastructure-health
- **How-to guide:** *How to use the DataDog Dashboard?* at `https://tylertech.atlassian.net/wiki/spaces/SPY/pages/407175646`

---

## Supported browsers

For the canonical supported-browsers list, see the Confluence page:

- `https://tylertech.atlassian.net/wiki/spaces/SPY/pages/407176640` (*Browser support*)

---

## Notes for the chatbot

- **Three environments only:** CI (`tcpci.com`), QA (`tcpqa.com`), Production (`tylerportico.com`). Customer-facing work is **production only**. CI and QA are internal Tyler use.
- **Inbound allow-listing = root domains.** Customer firewalls should allow outbound traffic to `tcpci.com`, `tcpqa.com`, and/or `tylerportico.com` depending on which TCP environments their users need to reach.
- **Outbound allow-listing = cluster IP set.** When TCP services call into customer on-prem APIs (webhooks, integrations), the customer's firewall must allow inbound from the TCP cluster egress IPs. Use the **DNS endpoint** (`allow-list.<env>.com`) if their firewall supports FQDN-based rules — it stays in sync as Tyler adds new IPs. Otherwise hand them the explicit IP list.
- **The IP lists in this document are a snapshot.** Always recommend the customer verify against the live Confluence page before configuring production firewalls. New egress IPs are added as TCP clusters scale.
- **"Original" IPs are noted.** `44.225.249.146` (CI) and `3.214.129.200` (Prod) are labeled "original" in the source — they're the longest-standing egress IPs, sometimes hard-coded into older customer rules. Don't remove them when refreshing the list; just add new ones.
- **TID Enterprise (TID-E) is the Okta-based identity solution.** Allow-listing the TID URIs (`tyleridentity.com`, `devbroker.tyleridentity.com`, `broker.tyleridentity.com`, `dev.tyleridentity.com`) is required for customers using TID-E. For broader Okta egress IPs, defer to Okta's own allow-listing doc.
- **Customer-facing terminology reminder:** TID-Citizen is now branded **Community Access**; TID-Enterprise is now branded **Identity Workforce**. The internal TID-E URIs (`*.tyleridentity.com`) remain in use. When discussing with customers, use the new brand names; when reading firewall logs / configuring DNS, use the actual `*.tyleridentity.com` hosts.
- **The portal sign-on flow described here is for Tyler staff** getting added to TCP portals — NOT customer end users. Customer users land in Admin Center / Workforce App Directory / Community Launcher, not the portal-administration screens.
- **The DataDog dashboard is for Tyler internal monitoring**, not customer self-service. Customers should NOT be pointed at this URL.
- **For Cloud Platform support tickets**, see `Knowledge-Shared/Conf-OneTylerTickets.md` — the canonical catalog of OneTyler support ticket types.
