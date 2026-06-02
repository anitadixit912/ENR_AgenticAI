# Product Requirements Document (PRD)

**Title:** Invisible Exits — Detecting and Preventing Customer Churn  
**Date:** 2026-05-27  
**Owner:** Sales Operations / Customer Success  
**Solution Category:** AI Agent

---

## Product Purpose & Value Proposition

**Elevator Pitch:**  
Sales teams have no early-warning system for quietly churning accounts. This AI agent monitors every customer's buying behaviour weekly, scores churn risk automatically, and delivers personalised Joule alerts to the right sales rep — before the revenue is gone.

**Business Need:**  
Manual account monitoring is reactive, inconsistent, and only covers a fraction of the portfolio. By the time a customer's drop in purchasing appears in reports, the window for retention has often closed. Sales teams need a systematic, proactive signal that surfaces risk early and focuses human effort where it matters most.

**Expected Value:**

- Detect at-risk accounts up to 11 weeks earlier than manual review
- Eliminate manual portfolio monitoring workload for account managers and CSMs
- Focus sales effort only on accounts above the risk threshold
- Full GDPR-compliant audit trail with zero custom development overhead

**Product Objectives (Prioritised):**

1. Score the full customer portfolio weekly and flag accounts with churn risk ≥ 65 automatically
2. Deliver personalised, natural-language Joule alerts to the assigned account manager, sales manager, and CSM for every flagged account
3. Log every agent action, score, and alert to the BTP Audit Log Service for GDPR-compliant traceability
4. Exclude thin-history accounts from scoring and surface them as a separate watch list to the CSM
5. Provide a portfolio-level weekly summary (accounts scanned, flagged, alerts sent) visible to sales managers in Joule

---

## User Profiles & Personas

### Primary Persona: Alex — Account Manager

Alex is a 34-year-old enterprise account manager responsible for 60–90 accounts across a regional territory. He spends his days progressing opportunities, handling escalations, and preparing quarterly business reviews. He has no time to monitor every account proactively and relies on gut feel or customer complaints to spot churn risk. He is comfortable with Joule and SAP but frustrated by the lack of early signals. He needs actionable alerts that tell him *which* account to call and *why* — not a dashboard he has to check manually.

### Secondary Persona: Maria — Sales Manager

Maria manages a team of 12 account managers and is accountable for quarterly revenue targets. She needs portfolio-level visibility into which accounts are at risk this week without waiting for individual reps to escalate. She reviews weekly summaries in Joule and uses the risk scores to prioritise team coaching and escalation decisions. She is technically confident and wants full transparency into how scores are calculated.

### Supporting Persona: Jin — Customer Success Manager

Jin is responsible for post-sales health across a set of strategic accounts. He monitors engagement, product adoption, and renewal signals. He needs the watch list of accounts with insufficient history so he can apply judgement to those accounts the scoring model cannot yet cover. He is the primary owner of the GDPR audit trail from a compliance perspective.

---

## Goals and Non-Goals

### Goals (In Scope)

- Ingest rolling 12-week sales order history and complaint/return data from SAP S/4HANA per customer
- Score each account on a 0–100 churn risk index using a model hosted on SAP AI Core
- Flag accounts at or above a configurable threshold (default ≥ 65) as at-risk
- Deliver a Joule alert per flagged account to the account manager, sales manager, and CSM
- Provide a confidence band (High / Medium / Low) alongside each score
- Exclude accounts with fewer than 4 completed orders in the trailing 12-week window and surface them on a CSM watch list
- Write every evaluation cycle, score, and alert dispatch to the BTP Audit Log Service
- Deliver a weekly portfolio-level summary in Joule to sales managers
- Support an event-driven micro-trigger for high-value accounts with no new orders in a rolling 14-day window

### Non-Goals (Out of Scope)

- Autonomous outreach to customers — the agent alerts only; sales reps decide how to follow up
- SAP Emarsys personalised campaign execution (planned for a future phase)
- Real-time scoring outside the weekly batch and the event-driven micro-trigger
- CRM opportunity pipeline management or update
- Replacement of the account manager's existing Joule workspace tools

---

## Requirements

### Must-Have Requirements

**R1: Signal Ingestion from S/4HANA**

- **Problem to Solve**: Sales teams have no structured view of per-customer order frequency, order value trend, or return/complaint history over time.
- **User Story**: As an account manager, I need the agent to automatically pull my customers' 12-week order and complaint history from S/4HANA so that I don't have to gather data manually before every account review.
- **Acceptance Criteria**:
  - Given a weekly scheduled trigger fires, when the agent runs, then it retrieves order frequency, order value trend, and complaint/return count for every active customer in the trailing 12-week window via the Sales Order MCP server.
  - Given retrieval completes, when data is available, then the agent logs M1.achieved with a count of accounts ingested.
  - Given a retrieval failure, when the API is unavailable, then the agent logs M1.missed with error detail and aborts the cycle gracefully.
- **Maps to Objective**: Objective 1
- **Priority Rank**: 1

**R2: Churn Risk Scoring**

- **Problem to Solve**: Without a consistent scoring model, at-risk accounts are identified inconsistently and too late.
- **User Story**: As a sales manager, I need every account in the portfolio to receive a churn risk score each week so that my team focuses on the highest-risk accounts first.
- **Acceptance Criteria**:
  - Given signal data is available for an account, when the AI Core scoring model is invoked, then it returns a 0–100 risk index and a confidence band (High / Medium / Low).
  - Given an account has fewer than 4 completed orders in the trailing 12-week window, when scoring is attempted, then the account is excluded from scoring and added to the CSM watch list instead.
  - Given scoring completes, when results are available, then the agent logs M2.achieved with account count, flagged count, and watch-list count.
- **Maps to Objective**: Objective 1, Objective 4
- **Priority Rank**: 2

**R3: Joule Alert Delivery**

- **Problem to Solve**: At-risk account signals are invisible to the sales rep until the customer complains or leaves.
- **User Story**: As an account manager, I need a Joule alert for each at-risk account that summarises the specific signals and risk score so that I can take immediate, informed action.
- **Acceptance Criteria**:
  - Given an account's score is ≥ 65, when the agent dispatches alerts, then a Joule notification is delivered to the assigned account manager, sales manager, and CSM.
  - Given an alert is dispatched, when the rep views it, then the alert includes the account name, risk score, confidence band, and a natural-language summary of the top contributing signals.
  - Given alerts are dispatched, when the cycle completes, then the agent logs M3.achieved with recipient count and alert count.
  - Given the Joule delivery fails, when retries are exhausted, then the agent logs M3.missed with affected accounts and falls back to an email notification.
- **Maps to Objective**: Objective 2
- **Priority Rank**: 3

**R4: Audit Logging**

- **Problem to Solve**: GDPR requires an immutable record of every automated decision and alert involving customer personal data.
- **User Story**: As a customer success manager, I need every agent action logged in BTP Audit Log so that I can demonstrate compliance and trace any alert back to its data source.
- **Acceptance Criteria**:
  - Given any scoring or alert action occurs, when the action completes, then a structured entry is written to the BTP Audit Log Service containing timestamp, account ID, score, signals breakdown, and recipient list.
  - Given audit entries are written, when the cycle completes, then the agent logs M4.achieved with entry count.
  - Given an audit write fails, when the failure is detected, then the agent logs M4.missed and halts alert dispatch for the affected account until the audit entry is confirmed.
- **Maps to Objective**: Objective 3
- **Priority Rank**: 4

**R5: Portfolio Summary**

- **Problem to Solve**: Sales managers have no weekly view of portfolio-level churn risk without manually aggregating individual alerts.
- **User Story**: As a sales manager, I need a weekly Joule summary of accounts scanned, at-risk flagged, and alerts sent so that I can track the health of the full portfolio at a glance.
- **Acceptance Criteria**:
  - Given a weekly cycle completes, when all scoring and alerts are done, then a portfolio-level summary is delivered to all sales managers in Joule.
  - Given the summary is delivered, when the cycle closes, then the agent logs M5.achieved.
- **Maps to Objective**: Objective 5
- **Priority Rank**: 5

### High-Want Requirements

**R6: Event-Driven Micro-Trigger**

- **Problem to Solve**: A weekly batch leaves up to 7 days of latency for high-value accounts that stop ordering mid-week.
- **User Story**: As a sales manager, I need the agent to re-score a high-value account immediately when no new order has been received for 14 days so that I can act before the weekly run.
- **Acceptance Criteria**:
  - Given no new order is received from a high-value account within a rolling 14-day window, when the event fires via SAP Event Mesh, then the agent performs an on-demand re-score and dispatches a Joule alert if the threshold is breached.
- **Priority Rank**: 1

**R7: CSM Watch List**

- **Problem to Solve**: Accounts with sparse order history cannot be scored reliably but may still be at risk.
- **User Story**: As a customer success manager, I need a weekly watch list of unscored accounts so that I can apply manual judgement where the model has insufficient data.
- **Acceptance Criteria**:
  - Given accounts are excluded from scoring due to insufficient history, when the weekly cycle completes, then a watch list is delivered to the CSM via Joule with account names and available signal data.
- **Priority Rank**: 2

---

## Solution Architecture

**Architecture Overview:**  
A Python-based AI agent deployed on SAP BTP AI Core, triggered weekly by a scheduled job (and optionally by Event Mesh for high-value accounts). The agent ingests data from SAP S/4HANA via the Sales Order MCP server, enriches accounts with context from SAP Sales Cloud via custom MCP translation files, scores accounts using a churn model on AI Core, and delivers alerts via SAP Joule. All actions are written to the BTP Audit Log Service.

**Key Components:**

- **Python AI Agent (AI Core)**: Orchestration layer — runs the full signal ingestion, scoring, and alert dispatch cycle
- **SAP S/4HANA Sales Order MCP Server** (`sap.mcpbuilder:apiResource:sales_order_mcp_demo:v1`): Provides order history and complaint/return data per customer
- **SAP Sales Cloud MCP Translation Files**: Custom-generated from Account Service and Opportunity Service REST APIs for account context enrichment
- **AI Core Churn Scoring Model**: Custom model returning 0–100 risk index and confidence band per account
- **SAP Joule**: Alert and summary delivery surface for sales reps, managers, and CSMs
- **BTP Audit Log Service**: Immutable GDPR-compliant record of every agent action
- **SAP Event Mesh** (High-Want): Event source for the 14-day no-order micro-trigger

**Integration Points:**

- S/4HANA → Agent: Sales order and complaint data, read-only, weekly batch + event-driven
- Sales Cloud → Agent: Account profile and opportunity context, read-only, per scoring cycle
- Agent → AI Core: Account signals batch, inference request, per scoring cycle
- Agent → Joule: Alert and summary delivery, write, per cycle
- Agent → BTP Audit Log: Action records, write, per every agent action

### Agent Extensibility & Instrumentation

**Agent Extensibility:**  
The agent is designed with the following extension points:

- **Signal Sources**: Additional data connectors (e.g., SAP Emarsys engagement data, Sales Cloud activity history) can be added as new MCP tools without modifying the core scoring logic.
- **Scoring Models**: The AI Core model invocation is abstracted behind an interface, allowing model versions and alternative scoring approaches to be swapped independently.
- **Alert Channels**: Alert delivery is decoupled from the scoring pipeline; new channels (email, Teams, Emarsys campaign trigger) can be added without changing the scoring or audit components.
- **Trigger Mechanisms**: The weekly scheduler and event-driven trigger are separate entry points; additional triggers (e.g., CRM opportunity close lost) can be registered independently.

**Business Step Instrumentation:**  
All business logic steps emit structured log statements following the pattern `[MILESTONE_ID].[achieved|missed]: [description]`. This enables production monitoring, debugging, and SLA tracking of each step independently. See Milestones section for full log statement definitions.

### Automation & Agent Behaviour

**Automation Level:** ML-assisted autonomous agent with human-in-the-loop alert review

**Actions the system performs without human approval:**

- Query S/4HANA order and complaint history per customer
- Invoke the AI Core churn scoring model per account
- Write audit entries to BTP Audit Log Service
- Deliver Joule alerts and portfolio summary to designated recipients

**Actions that require human review or approval:**

- Any retention action or customer outreach (handled entirely by the sales rep after reviewing the alert)
- Model retraining decisions (quarterly, requires sales ops sign-off)
- Risk threshold adjustment (configurable parameter, requires sales management approval)

**Model or engine used:** Custom churn scoring model on SAP AI Core; alert summarisation via SAP Generative AI Hub (GPT-4o or equivalent)

**Knowledge & data sources accessed:**

- S/4HANA Sales Order API: 12-week order frequency, order value trend, return/complaint history — read-only
- SAP Sales Cloud Account Service: Account profile, assigned owner, segment — read-only
- SAP Sales Cloud Opportunity Service: Open opportunity context per account — read-only

**Tools or connectors invoked:**

- `sales_order_mcp_demo`: S/4HANA order history retrieval — read-only
- Sales Cloud Account MCP (custom translation): Account enrichment — read-only
- Sales Cloud Opportunity MCP (custom translation): Opportunity context — read-only
- AI Core Inference API: Churn score generation — read, compute
- Joule Notification API: Alert and summary delivery — write
- BTP Audit Log API: Action logging — write

**Guardrails & fail-safes:**

- The agent never contacts customers directly or modifies any SAP master or transactional data
- Accounts with fewer than 4 orders in the trailing 12-week window are excluded from scoring and placed on the watch list
- Customer names and PII are injected only at the final Joule rendering step and are never written to intermediate logs or LLM prompt context
- If audit logging fails for an account, alert dispatch for that account is halted until the audit entry is confirmed
- If AI Core inference is unavailable, the cycle is aborted and the sales manager receives a Joule notification of the outage

---

## Milestones

### M1: Signal Ingestion

- **Description**: Agent retrieves 12-week order history, order value trend, and complaint/return data from S/4HANA for all active customers.
- **Achieved when**: All customer records have been queried and signal data is available for the scoring step.
- **Log on achievement**: `M1.achieved: signal ingestion complete — {account_count} accounts retrieved`
- **Log on miss**: `M1.missed: signal ingestion failed — {error_detail} — cycle aborted`

### M2: Churn Scoring

- **Description**: AI Core model scores each eligible account; ineligible accounts are placed on the CSM watch list.
- **Achieved when**: All accounts with sufficient order history have received a 0–100 risk score and confidence band; ineligible accounts are identified and watch-listed.
- **Log on achievement**: `M2.achieved: scoring complete — {scored_count} scored, {flagged_count} flagged ≥{threshold}, {watchlist_count} watch-listed`
- **Log on miss**: `M2.missed: scoring incomplete — {error_detail} — affected accounts: {account_ids}`

### M3: Alert Delivery

- **Description**: Joule alerts dispatched to account manager, sales manager, and CSM for every at-risk account.
- **Achieved when**: All flagged accounts have a confirmed Joule alert delivered to all three recipient roles.
- **Log on achievement**: `M3.achieved: alerts dispatched — {alert_count} alerts sent to {recipient_count} recipients`
- **Log on miss**: `M3.missed: alert delivery failed for {account_ids} — fallback email triggered`

### M4: Audit Logging

- **Description**: Every scoring result and alert dispatch is written to BTP Audit Log Service.
- **Achieved when**: All scoring and alert actions have a confirmed audit entry in BTP Audit Log.
- **Log on achievement**: `M4.achieved: audit logging complete — {entry_count} entries written`
- **Log on miss**: `M4.missed: audit write failed for {account_ids} — alert dispatch halted for affected accounts`

### M5: Portfolio Summary

- **Description**: Weekly portfolio-level summary delivered to all sales managers in Joule.
- **Achieved when**: A confirmed Joule summary message has been delivered to all sales manager recipients.
- **Log on achievement**: `M5.achieved: portfolio summary delivered — {scanned_count} scanned, {flagged_count} flagged, {alert_count} alerts sent`
- **Log on miss**: `M5.missed: portfolio summary delivery failed — {error_detail}`

---

## Risks, Assumptions, and Dependencies

### Risks

- **AI Core model cold-start accuracy**: Accounts with thin transaction histories may produce low-confidence scores. Mitigation: minimum-data guard (< 4 orders → watch list), confidence band surfaced in every alert, quarterly model retraining.
- **Sales Cloud API coverage**: Account and Opportunity Service REST APIs require custom MCP translation files. Mitigation: generate MCP translation files during specification phase; fall back to S/4HANA Customer Master Data if Sales Cloud spec is incomplete.
- **Data freshness**: Weekly batch means up to 7-day staleness for mid-week churn signals. Mitigation: event-driven micro-trigger for high-value accounts via SAP Event Mesh.
- **GDPR compliance for alert content**: Joule alerts contain customer names and behaviour summaries. Mitigation: PII injected only at final Joule rendering step; BTP Audit Log used for all persistent storage with retention policies configured.

### Assumptions

- The Sales Order MCP server (`sap.mcpbuilder:apiResource:sales_order_mcp_demo:v1`) is accessible in the target BTP tenant.
- SAP Sales Cloud Account Service and Opportunity Service OpenAPI specs are available for MCP translation file generation.
- A dedicated AI Core deployment is available for hosting the custom churn scoring model.
- SAP Joule notification APIs are available and configured for the sales team workspace.
- BTP Audit Log Service is provisioned in the target BTP subaccount.

### Dependencies

- SAP S/4HANA: Sales order and complaint data via Sales Order MCP server
- SAP Sales Cloud: Account and opportunity context via custom MCP translation
- SAP AI Core: Churn model hosting and inference
- SAP Joule: Alert and summary delivery
- BTP Audit Log Service: GDPR-compliant action logging
- SAP Event Mesh (High-Want): Event-driven micro-trigger for high-value accounts

---

## Governance, Risk & Compliance

**Data Handling:**

- Customer names and personal identifiers are never written to intermediate agent logs or LLM prompt context; PII is injected only at the Joule rendering step.
- BTP Audit Log Service is the sole persistent store for alert content; retention policies must be configured to auto-purge records beyond the defined retention period.
- A Data Protection Impact Assessment (DPIA) checklist is a required specification deliverable before go-live.

**Compliance Frameworks:**

- GDPR: BTP Audit Log Service provides the immutable processing record; data minimisation enforced at the prompt layer.
- SAP AI Ethics Guidelines: Human-in-the-loop retained for all customer-facing actions.
