# Status Page and SLA Tracking — Key Concepts, Guides, and Checklists

Source: Tyler Blueprint Docusaurus — https://docs.tylerdev.io/status-page-and-sla
Domain: Blueprint General — Tyler Cloud Platform / Blueprint docs not served by a specialized Foundry agent
Audience: Tyler product-team engineers integrating with the Status Page service and implementing SLA tracking for their products

**Companion documents:**
- `_START_HERE.md` — corpus routing guide
- `Docusaurus-PlatformOverview.md` — TCP platform overview and service landscape
- `Docusaurus-CloudPlatformAPI.md` — authentication and Platform Service API general reference
- `Docusaurus-ServiceArchitecture.md` — event-driven architecture and observability patterns
- `Docusaurus-AlignedReleases.md` — quarterly release management (related platform service)
- `Docusaurus-OpsApps.md` — Ops-facing applications including status and incident surfaces

---

## How to use this guide

| User intent | Go to section |
|---|---|
| "What is the Status Page?" | Key Concepts → Status Page |
| "What is SLA tracking?" | Key Concepts → SLA Tracking |
| "How do I integrate with / use the Status Page?" | Guides → Status Page Integration and Usage |
| "How do I implement SLA tracking?" | Guides → SLA Tracking |
| "Is there a checklist for Status Page integration?" | Checklists → Status Page Checklist |
| "Is there a checklist for SLA tracking?" | Checklists → SLA Tracking Checklist |

---

## Glossary

| Term | Definition |
|---|---|
| Status Page | A platform-provided service that publishes real-time and historical status of Tyler product/platform components to internal staff and/or clients. |
| SLA | Service Level Agreement — a contractual commitment defining expected availability, performance, or response time for a product or service. |
| SLA Tracking | The platform mechanism for measuring actual product behavior against defined SLA commitments, generating compliance data and alerts. |
| Incident | A degradation or outage event that affects product availability or performance, surfaced on the Status Page. |
| Component | A discrete unit of a product or platform service tracked on the Status Page (e.g., API, database, web front-end). |

---

## Important Notice: Documentation Under Construction

> All source pages for Status Page and SLA Tracking in Tyler Blueprint Docusaurus are currently stubs marked **"content coming soon."** This file represents the structural intent of this platform area based on available metadata. Substantive implementation detail is not yet published.
>
> For the current state of documentation, visit: https://docs.tylerdev.io/status-page-and-sla
>
> To get help from the platform team, see the Cloud Platform Community Teams channel linked in `Docusaurus-PlatformOverview.md` or `Docusaurus-CloudPlatformAPI.md`.

---

## Key Concepts

### Status Page

**Live doc (stub):** https://docs.tylerdev.io/status-page-and-sla/key-concepts/status-page

The Status Page is a TCP platform service that provides a real-time and historical view of system health for Tyler products and platform components. It surfaces incident information and component status to relevant audiences (internal teams and/or clients), reducing support burden and improving transparency during outages or degraded performance.

Use when:
- Your product team needs to publish health or incident status to clients
- You want to integrate your product's availability signals with Tyler's central status surface
- You need to query or display status information from another application

### SLA Tracking

**Live doc (stub):** https://docs.tylerdev.io/status-page-and-sla/key-concepts/sla-tracking

SLA Tracking is the platform mechanism for defining and measuring Service Level Agreement commitments for Tyler products. It records actual uptime and performance against defined SLA targets, generating compliance data and enabling reporting to clients and internal stakeholders.

Use when:
- Your product has contractual availability or performance commitments to clients
- You need to report SLA compliance data to clients or leadership
- You want the platform to track SLA breach events and generate alerts

### Overview

**Live doc (stub):** https://docs.tylerdev.io/status-page-and-sla

The Status Page and SLA Tracking area covers two related but distinct platform capabilities:
1. **Status Page** — real-time status publication and incident communication
2. **SLA Tracking** — measurement and reporting of availability/performance against contractual commitments

These two capabilities are often used together: the Status Page surfaces incidents that may count against SLA commitments, while SLA Tracking provides the quantitative record of those impacts.

---

## Guides

### Status Page Integration and Usage

**Live doc (stub):** https://docs.tylerdev.io/status-page-and-sla/guides/status-page-integration-and-usage

Prerequisites (anticipated based on pattern of peer services):
- Product registered in Product Registration with a valid `productRegistrationId`
- OAuth 2.0 credentials from Tyler Identity Gateway with appropriate scope for Platform Service APIs
- Defined components to track (e.g., API availability, web application, data processing)

Integration overview (content pending; check live doc for current guidance):
- Register your product's components with the Status Page service
- Emit health/availability signals or configure monitoring probes to update component status
- Optionally subscribe to status-change events for downstream notification or alerting

### SLA Tracking

**Live doc (stub):** https://docs.tylerdev.io/status-page-and-sla/guides/sla-tracking

Prerequisites (anticipated):
- SLA definitions agreed upon with client contracts / product management
- Incident and availability event streams from your product
- OAuth 2.0 credentials for Platform Service API access

Integration overview (content pending; check live doc for current guidance):
- Define SLA commitments (availability percentage, response-time thresholds, etc.) for your product
- Integrate your incident/outage signals with the SLA Tracking service
- Query compliance reports and configure alerting on SLA breach thresholds

---

## Integration Checklists

### Status Page Checklist

**Live doc (stub):** https://docs.tylerdev.io/status-page-and-sla/integration-checklists/status-page-checklist

> Official checklist content is pending. Monitor the live doc URL for publication.

Anticipated checklist items (based on platform patterns):
- [ ] Product registered in Product Registration (`productRegistrationId` confirmed)
- [ ] OAuth 2.0 client credentials obtained for target environment (TCPCI / TCPQA / TCPPROD)
- [ ] Components identified and named in client-facing language
- [ ] Component status update mechanism implemented (API calls or monitoring probe integration)
- [ ] Incident creation and resolution workflow defined for your on-call process
- [ ] Status Page surfaced to clients (or confirmed as internal-only)

### SLA Tracking Checklist

**Live doc (stub):** https://docs.tylerdev.io/status-page-and-sla/integration-checklists/sla-tracking-checklist

> Official checklist content is pending. Monitor the live doc URL for publication.

Anticipated checklist items:
- [ ] SLA commitments documented and approved by product management and client contracts
- [ ] Availability and performance metrics identified that map to SLA definitions
- [ ] OAuth 2.0 credentials and API access confirmed for SLA Tracking service
- [ ] SLA targets configured in the platform (availability %, response-time thresholds)
- [ ] Incident/outage event integration tested in TCPQA
- [ ] SLA compliance reporting output reviewed and approved
- [ ] Alerting configured for SLA breach risk thresholds

---

## Notes for the Chatbot

1. **All source pages are stubs.** As of the knowledge cutoff, every Status Page and SLA Tracking page in Blueprint Docusaurus contains only "content coming soon." There is no implementation detail available from these sources yet. Always direct users to the live docs URL and the platform team for current guidance.
2. **Do not fabricate API endpoints or SDK details.** Because the documentation is not yet published, no specific API endpoints, request payloads, or code samples are available for this area. Do not infer or invent them from analogous services like Aligned Releases.
3. **Status Page ≠ SLA Tracking.** These are two distinct capabilities that may be integrated together but serve different purposes: Status Page is about *publishing* current health; SLA Tracking is about *measuring* compliance over time.
4. **Ops Center has its own Foundry agent.** If the user's question is about Ops Center dashboards, incident management within Ops Center, or operational monitoring, direct them to: https://docs.tylerdev.io/app-guides/ops/ops-center/overview/
5. **Support Access Center (SAC) has its own Foundry agent.** For SAC questions → https://docs.tylerdev.io/ops/support-access-center/
6. **Identity questions** → https://docs.tylerdev.io/identity
7. **Check `_START_HERE.md`** for routing to other Blueprint domains (DevOps, Security, Service Architecture) that may have adjacent relevance to status and SLA topics (e.g., monitoring setup, observability instrumentation).
8. **Index hygiene note.** When the Status Page and SLA docs are published, this file must be substantially revised to replace the "stub" placeholders with real content. Update `_START_HERE.md` to reflect the expanded coverage at that time.
