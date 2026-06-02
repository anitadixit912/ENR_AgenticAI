# Geopolitical Risk Intelligence Agent

Real-time geopolitical event monitoring and supply chain risk intelligence powered by GDELT integrated with SAP S/4HANA Cloud Public Edition.

## Business challenge

Organizations operating global supply chains face increasing exposure to geopolitical disruptions â conflicts, sanctions, civil unrest, and trade restrictions â that affect suppliers, procurement contracts, and logistics routes. Procurement and supply chain teams currently lack a real-time, automated mechanism to detect these events, assess their impact on active suppliers and purchase orders, and take corrective action within SAP before disruptions materialize. The goal is to connect GDELT to continuously monitor global conflict signals, correlate them with known supplier locations, and surface actionable risk intelligence into SAP S/4HANA Cloud Public Edition workflows.

## Key Milestones

1. **Signal Ingestion** â GDELT events are fetched on a scheduled basis, filtered by conflict/risk themes, and persisted in the platform.
2. **Risk Scoring** â The AI agent evaluates each event against active supplier and purchase order records, assigns a risk severity score, and identifies affected SAP entities.
3. **Alert Dispatch** â High-risk events trigger email/push notifications to procurement and supply chain managers with contextual summaries.
4. **SAP Task Creation** â Workflow items are created in SAP S/4HANA for each impacted supplier or PO, routed to the responsible buyer for review.
5. **Supplier Risk Score Update** â Supplier risk profiles in SAP are automatically updated based on the agent's scoring output.
6. **Dashboard Review** â Risk managers access an interactive dashboard displaying a geopolitical heat map, active alerts, affected suppliers, and recommended actions.

## Business Architecture (RBA)

### End-to-End Process

Source to Pay (E2E)

### Process Hierarchy

```
Source to Pay (E2E)
âââ Plan to Optimize Sourcing and Procurement
    âââ Develop spend strategy and plans (BPS-324)
        âââ Analyze organization's spend profile
âââ Manage Suppliers and Collaboration
    âââ Manage suppliers and networked collaboration (BPS-332)
        âââ Evaluate supplier performance
âââ Source to Contract
    âââ Manage procurement contracts (BPS-328)
        âââ Manage procurement contracts
âââ Plan to Optimize Fulfillment
    âââ Develop supply chain strategy (BPS-335)
        âââ Implement supply chain strategy
    âââ Monitor and optimize supply chain performance (BPS-340)
        âââ Control and monitor supply chain
```

### Summary

The challenge maps to the Source to Pay E2E process, specifically supplier risk management, supply chain performance monitoring, and spend strategy â where external geopolitical signals must be correlated with active SAP procurement and supply chain data to trigger risk-mitigating actions.

## Fit Gap Analysis

| Requirement (business) | Standard asset(s) found | API ORD ID | MCP Server ORD ID | Gap? | Notes / assumptions |
| ----------------------- | ------------------------ | ---------- | ----------------- | ---- | ------------------- |
| Real-time geopolitical event ingestion (GDELT) | None | â | â | Yes | No SAP standard product ingests external news/geopolitical feeds; custom integration required via GDELT API |
| Supplier risk scoring based on geopolitical events | SAP Ariba Supplier Risk (SC341), SAP S/4HANA Supplier Risk Management (SC5369) | Risk Exposure API (no ORD ID) | â | Maybe | SAP Ariba Supplier Risk covers standard scoring; gap is enrichment with real-time GDELT signals |
| Procurement risk alerting for POs/contracts in conflict zones | SAP Ariba Sourcing, SAP S/4HANA Cloud Public | `sap.s4:apiResource:API_SUPPLIER_ACTIVITY_TASK_SRV:v1` | â | Maybe | Procurement task API exists; gap is geo-risk trigger logic from external data sources |
| Supply chain disruption detection | SAP IBP â Supply Chain Risk Management (SC759) | â | â | Maybe | IBP covers planning-level risk; gap is real-time event-driven detection from external intelligence |
| SAP task/workflow creation for human review | SAP S/4HANA Cloud Public | `sap.s4:apiResource:API_SUPPLIER_ACTIVITY_TASK_SRV:v1` | â | No | Procurement-Related Task API can be used to create review tasks in SAP |
| Interactive risk dashboard | SAP Analytics Cloud | â | â | Maybe | SAC covers analytics; a lightweight BTP-hosted React dashboard provides faster real-time UX with custom geo-visualization |
| AI-driven risk analysis and reasoning | SAP AI Core | â | â | Yes | No standard product reasons over GDELT events + supplier master data; requires custom AI agent on BTP |
| Supplier risk profile update in SAP | SAP Ariba Supplier Risk, SAP S/4HANA | Risk and Criticality Assessment API, Risk Snapshot Service API | â | Maybe | SAP Ariba Supplier Risk API available; mapping from GDELT event scores to SAP risk categories requires custom logic |

### Key findings

- No SAP standard product ingests or processes external geopolitical signals from GDELT â custom ingestion layer is required.
- SAP Ariba Supplier Risk (SC341) and S/4HANA Supplier Risk Management (SC5369) provide the downstream target for risk score updates; they can receive structured risk input via API.
- The Procurement-Related Task API (`API_SUPPLIER_ACTIVITY_TASK_SRV:v1`) enables creation of SAP workflow tasks for human review â no MCP server exists, so direct REST calls required.
- SAP IBP covers supply chain risk at a planning level; real-time event-driven disruption detection requires a custom layer.
- The solution requires an AI agent to reason over unstructured event data, correlate with SAP supplier/PO master data, and produce structured risk signals â this is handled entirely within the AI agent running on BTP Job Scheduling Service.
- GDELT is free and updates every 15 minutes, making it the primary signal source.

## Recommendations

### Geopolitical Risk Intelligence Agent â Integrated with SAP S/4HANA

#### Executive Summary

AI agent with BTP Job Scheduling ingesting GDELT to deliver real-time risk intelligence into SAP

#### Recommended Solution

A three-component solution deployed on SAP BTP:

1. **AI Agent (Python, A2A on BTP) with BTP Job Scheduling**: Triggered every 15 minutes via SAP BTP Job Scheduling Service, the agent polls GDELT directly, filters events by conflict/geopolitical themes and target regions (Global, Middle East & Africa, Eastern Europe & Russia/Ukraine), correlates them with supplier master data and open POs in SAP S/4HANA Cloud Public Edition via REST APIs, scores risk severity (Low / Medium / High / Critical), and produces structured risk assessments. The agent also drafts notification content and creates SAP task payloads.

2. **BTP Extension â React Dashboard + CAP Backend**: A CAP service stores risk events, supplier impact records, and alert history in SAP HANA Cloud. A React frontend visualizes a geopolitical heat map, active alerts by region and supplier, risk trend charts, and recommended actions.

**Integration touchpoints with SAP S/4HANA Cloud Public Edition:**
- Read supplier master data and open PO/contract records via OData APIs
- Create procurement-related tasks via `API_SUPPLIER_ACTIVITY_TASK_SRV` for human review
- Push risk scores to supplier risk profiles via Supplier Risk APIs

#### Problem Statement

Procurement and supply chain teams cannot detect geopolitical events affecting their supplier base in real time, leading to reactive rather than proactive risk management. By the time disruptions are visible in SAP, contracts are already impacted, alternative sourcing is too late, and escalation paths are unclear.

#### Affected User Roles

- Supply Chain Manager
- Category/Procurement Manager
- Chief Procurement Officer (CPO)
- Risk & Compliance Officer
- Supplier Relationship Manager

#### Important factors

##### Real-time, always-on monitoring
GDELT updates every 15 minutes. The solution must run on a reliable schedule with no manual triggering required.

##### SAP-native task and risk integration
Alerts must result in actionable SAP artifacts (tasks, updated risk scores) â not just emails â so that procurement managers work within their existing SAP workflow.

##### AI reasoning over unstructured data
GDELT event codes and news headlines require contextual interpretation against specific supplier geographies and commodity types; a static rule engine is insufficient.

#### Potential risks

##### GDELT event volume and noise
GDELT produces millions of events per day globally. Without effective filtering on themes (CONFLICT, PROTEST, MILITARY), countries, and sentiment scores, the agent will be overwhelmed with low-signal data.

##### SAP API rate limits and authentication
S/4HANA Cloud Public Edition APIs are subject to rate limits. Batch processing and OAuth credential management must be built carefully to avoid throttling.

#### Recommended solution category

AI Agent, BTP Extension

#### Intent fit
88%
