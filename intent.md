# Invisible Exits â Detecting and Preventing Customer Churn

Customer churn prevention AI agent + operational dashboard that detects early buying-behaviour signals in SAP, scores at-risk accounts, generates personalised retention actions, and surfaces them to sales teams â both in Joule alerts and a dedicated risk dashboard.

## Business challenge

Retaining an existing customer costs five times less than acquiring a new one â every account the agent saves is a direct financial win with no extra sales or marketing spend. Sales teams get back hours of productive time every week by eliminating manual account monitoring, focusing only on high-risk customers where human judgment truly matters. Every at-risk customer receives a personalised, timely response based on their actual buying behaviour rather than a generic discount â dramatically increasing the chances of saving the relationship. The agent detects churn signals up to 11 weeks earlier than any manual process would, giving the business a meaningful window to act before revenue is lost. Every action is fully logged inside SAP with a complete audit trail, ensuring GDPR compliance and giving management complete visibility into what the agent did, when, and why.

Sales reps and managers need a centralised, at-a-glance view of all at-risk accounts and the personalised retention actions the agent has prepared â without switching between Joule alerts and their CRM. The dashboard surfaces the same intelligence in a structured, filterable UI optimised for portfolio review and daily task prioritisation.

## Key Milestones

1. **Signal Ingestion** â Agent queries S/4HANA Sales Order API and complaint data to retrieve per-customer order frequency, order value trend, and return/complaint history for the trailing 12-week window.
2. **Churn Scoring** â AI Core model scores each account on a 0â100 churn risk index; accounts crossing a configurable threshold (default â¥ 65) are flagged as at-risk.
3. **Alert Surfacing** â Joule alert delivered to the assigned account manager, sales manager, and customer success manager with a natural-language summary of the signals and the risk score.
4. **Audit Logging** â Every agent evaluation cycle, account scored, and alert dispatched is written back to SAP with timestamp, signal breakdown, score, and recipient â ensuring GDPR-compliant traceability.
5. **Cycle Completion** â Weekly scheduled run completes with a portfolio-level summary (accounts scanned, at-risk flagged, alerts sent) visible to sales managers in Joule and the risk dashboard.

## Business Architecture (RBA)

### End-to-End Process

Lead to Cash (generic)

### Process Hierarchy

```
Lead to Cash (generic)
âââ Market to Lead (generic)
    âââ Market products and services (BPS-368)
        âââ Analyze and respond to customer insight
        âââ Execute promotional activities
âââ Opportunity to Quote (generic)
    âââ Sell products and services (BPS-360)
        âââ Manage leads and opportunities
        âââ Key account management
        âââ Activity and visit management
```

### Summary

Customer churn prevention maps to the Lead to Cash E2E process â detecting signals and scoring accounts in the Market-to-Lead phase, then surfacing prioritised at-risk accounts to sales teams in the Opportunity-to-Quote phase for targeted retention activity. The risk dashboard is the operational front end for that Opportunity-to-Quote phase.

## Fit Gap Analysis

| Requirement (business) | Standard asset(s) found | API ORD ID | MCP Server ORD ID | Gap? | Notes / assumptions |
| ---------------------- | ----------------------- | ---------- | ----------------- | ---- | ------------------- |
| Read S/4HANA sales order history per customer | SAP S/4HANA Cloud | `sap.s4:apiResource:API_SALES_ORDER_SRV:v1` | `sap.mcpbuilder:apiResource:sales_order_mcp_demo:v1` â | No | MCP server available for Sales Order A2X |
| Read customer complaints / returns data | SAP S/4HANA Cloud | â | â | Maybe | EDMX spec available; MCP server not found â custom MCP translation required |
| Customer account & profile data | SAP Sales Cloud V2 | â | â | Maybe | Account Service REST API; custom MCP translation built |
| Churn risk scoring model | SAP AI Core | â | â | Yes | Custom model deployed on AI Core; no out-of-box churn scoring asset |
| Alert surfacing to sales reps / managers | SAP Joule | â | â | Yes | Joule agent required; no standard churn alert skill out-of-box |
| Key account & opportunity context | SAP Sales Cloud V2 | â | â | Maybe | Opportunity Service REST API; custom MCP translation built |
| Audit trail logging (GDPR, management visibility) | SAP BTP Audit Log Service | â | â | No | BTP Audit Log Service covers this natively |
| Dashboard: at-risk account list with scores + signals | â | â | â | Yes | No out-of-box SAP product; custom BTP Extension (CAP + React/UI5) required |
| Dashboard: pre-computed personalised retention actions | â | â | â | Yes | Agent writes actions to CAP data store during scoring run; dashboard reads via OData |
| Dashboard: on-demand retention action refresh per customer | â | â | â | Yes | CAP backend triggers A2A call to agent for single-account re-score and action regeneration |
| Dashboard: rep view (own accounts) and manager portfolio view | SAP Sales Cloud V2 â role-based data access | â | â | Maybe | Role filtering handled in CAP layer using user principal; no additional API needed |

### Key findings

- A dedicated **Sales Order MCP server** is already available, covering the primary S/4HANA data ingestion requirement without custom integration work.
- **Custom MCP translation files** for the SAP Sales Cloud Account Service and Opportunity Service have already been built and validated.
- The landscape has a **"Churn Risk Monitoring"** business capability (LeanIX) but current applications are legacy on-premise systems at end-of-life â confirming a genuine greenfield gap.
- **SAP AI Core** will host the custom churn scoring and retention-action generation model; no out-of-box SAP churn scoring or action recommendation asset exists.
- **BTP Audit Log Service** natively satisfies the GDPR audit trail requirement.
- A new **CAP persistence layer** (HANA Cloud) is required to bridge the agent's scoring output to the dashboard; the agent writes at the end of each weekly run, and the dashboard reads via a standard OData v4 service.
- **On-demand refresh** of retention actions (sales rep triggered) requires the CAP backend to invoke the agent's A2A endpoint for a single account, keeping the agent as the single source of truth for all AI-generated content.

## Recommendations

### AI Agent + Risk Dashboard for Customer Churn Prevention

#### Executive Summary

Python AI agent on BTP + React/UI5 dashboard surfacing at-risk accounts and personalised retention actions.

#### Recommended Solution

A Python-based AI agent (A2A protocol) deployed on SAP BTP AI Core, paired with a CAP + React/UI5 operational risk dashboard on BTP. The agent runs on a weekly scheduled trigger, ingests sales order history from S/4HANA via the Sales Order MCP server, enriches each account with profile and opportunity context from SAP Sales Cloud, scores churn risk using a model on SAP AI Core, and generates personalised retention actions for each at-risk account. Results â churn scores, signal breakdowns, and retention actions â are persisted to a SAP HANA Cloud database via the CAP backend. Joule alerts are dispatched to assigned account managers and sales managers for immediate notification. The React/UI5 dashboard provides a structured, filterable portfolio view of all at-risk accounts with their scores, signal details, and pre-computed retention actions. Sales reps see only their assigned accounts by default; managers can toggle to a full portfolio view. Any rep can trigger an on-demand retention action refresh for a specific customer, which invokes the agent's A2A endpoint for a single-account re-score. All agent evaluation cycles, scores, and alerts are written to the BTP Audit Log Service for GDPR-compliant traceability. No write-back to Sales Cloud is required at this stage.

#### Problem Statement

Sales teams have no systematic, early-warning mechanism to identify customers who are quietly reducing purchasing activity. Manual account monitoring is reactive and inconsistent. When churn signals are detected and Joule alerts sent, sales reps still lack a persistent, browsable view of all flagged accounts and the specific actions they should take â forcing them to rely on ephemeral alert notifications that disappear from their flow.

#### Affected User Roles

- Account managers / sales representatives (dashboard rep view, on-demand refresh)
- Sales managers (portfolio-wide manager view, weekly run summary)
- Customer success managers (Joule alerts and dashboard visibility)

#### Important factors

##### Detects signals up to 11 weeks earlier than manual processes
Weekly 12-week rolling analysis of order frequency, value trends, and complaint spikes surfaces deteriorating accounts while a targeted conversation can still reverse the trend.

##### Persistent dashboard closes the gap between alerts and action
Joule alerts are ephemeral â sales reps miss them or cannot retrieve them later. The dashboard gives reps a durable, structured view of every at-risk account and their specific recommended actions, available at any time.

##### On-demand refresh keeps retention actions current
Pre-computed actions cover the weekly baseline; the on-demand refresh allows reps to regenerate actions for a specific customer immediately before a call or meeting, using the latest available data.

##### Dual audience design with role-based filtering
Rep view (own accounts only) keeps the dashboard focused and actionable; manager toggle unlocks the full portfolio for pipeline review meetings without requiring two separate applications.

##### Full GDPR audit trail with no extra development
BTP Audit Log Service ensures every agent action is immutably logged. Customer names are never written to agent logs or intermediate data stores; account IDs are used throughout the persistence layer.

#### Potential risks

##### AI Core model cold-start accuracy
Accounts with fewer than 4 completed orders in the trailing 12-week window may produce low-confidence scores. Minimum-data guard and confidence band (High / Medium / Low) mitigate this.

##### Dashboard data freshness between weekly runs
Dashboard reflects last weekly run; data can be up to 7 days stale. On-demand refresh mitigates this for individual accounts; a banner showing last-run timestamp keeps users informed.

##### CAPâAgent A2A latency for on-demand refresh
Single-account re-score involves an A2A round trip to AI Core; response may take 5â15 seconds. A loading indicator and async polling pattern in the React UI prevent perceived hangs.

#### Recommended solution category

AI Agent, BTP Extension

#### Intent fit
92%
