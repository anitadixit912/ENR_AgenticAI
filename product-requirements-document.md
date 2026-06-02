# Product Requirements Document (PRD)

**Title:** Geopolitical Risk Intelligence Agent
**Date:** 2026-05-22
**Owner:** Supply Chain / Procurement Product Owner
**Solution Category:** AI Agent, BTP Extension

---

## Product Purpose & Value Proposition

**Elevator Pitch:**
Global supply chains are blind to geopolitical disruptions until it is too late. This solution continuously monitors GDELT for conflict signals, matches them to active SAP suppliers and purchase orders, scores the risk automatically, and surfaces actionable alerts and SAP workflow tasks â turning reactive crisis management into proactive risk intelligence.

**Business Need:**
Procurement and supply chain teams operating globally have no real-time mechanism to detect geopolitical events â conflicts, sanctions, civil unrest, trade restrictions â that directly affect their supplier base. By the time a disruption becomes visible inside SAP (delayed deliveries, price spikes, contract failures), corrective action is already late. A proactive intelligence layer is required that watches the world continuously, reasons over events against the company's supplier and contract data, and creates actionable tasks inside SAP before disruptions materialise.

**Expected Value:**
- Reduced mean time to detect supply chain risk from days/weeks to under 30 minutes
- Procurement managers have SAP-native tasks and risk scores to act on â no manual news monitoring required
- Risk & Compliance officers gain a real-time geopolitical heat map aligned with the supplier portfolio
- Supply chain strategy decisions are informed by live conflict signal data

**Product Objectives (Prioritized):**
1. Continuously ingest and filter geopolitical signals from GDELT every 15 minutes with no manual intervention
2. Accurately correlate events to affected SAP suppliers and purchase orders, producing a risk severity score (Low / Medium / High / Critical)
3. Automatically create SAP workflow tasks and update supplier risk profiles for High and Critical events
4. Provide an interactive risk dashboard visualising active alerts, affected suppliers, and geopolitical heat map
5. Dispatch email notifications to responsible procurement and supply chain managers for High/Critical events

---

## User Profiles & Personas

### Primary Persona: Marcus â Category/Procurement Manager

Marcus is a 38-year-old Category Manager responsible for direct materials sourcing across Eastern Europe and the Middle East. He manages 60+ active suppliers and hundreds of open purchase orders at any given time. His day starts by checking emails and SAP for supplier issues â a process that can take 45 minutes before he even begins strategic work. He has no structured way to monitor geopolitical developments affecting his supplier regions; he relies on news he happens to read personally. When a conflict escalates, he scrambles to identify which of his suppliers are affected, check open POs, and find alternatives â all manually. He needs a system that tells him exactly which suppliers are at risk, why, and what to do next, directly inside the SAP tools he already uses.

### Secondary Persona: Leila â Risk & Compliance Officer

Leila is a 44-year-old Risk Officer responsible for enterprise supply chain risk governance. She is accountable for quarterly risk reporting and must maintain current supplier risk classifications in SAP. She currently gathers risk data through manual supplier questionnaires and quarterly reviews â a process that misses fast-moving geopolitical changes entirely. She needs a real-time, auditable risk scoring mechanism that feeds into SAP supplier profiles and provides an executive-level dashboard she can present to the CPO.

### Other User Types
- **Supply Chain Manager** â monitors fulfillment risk and triggers alternative sourcing
- **Chief Procurement Officer (CPO)** â consumes executive risk summary dashboard
- **Supplier Relationship Manager** â receives tasks to contact and assess at-risk suppliers

---

## Goals and Non-Goals

### Goals (In Scope)
- Ingest geopolitical event signals from GDELT (every 15 min) automatically
- Filter signals by conflict/risk themes (CAMEO conflict codes, military, sanctions, protests) and target regions (Global, Middle East & Africa, Eastern Europe & Russia/Ukraine)
- Correlate filtered events against SAP S/4HANA supplier master data and open purchase orders
- Score risk severity per event-supplier pair: Low / Medium / High / Critical
- Create procurement review tasks in SAP S/4HANA for High and Critical events
- Update supplier risk profiles in SAP S/4HANA based on agent scoring output
- Send email notifications to responsible managers for High/Critical events
- Store all risk events, scores, and alerts in a CAP-backed HANA Cloud database
- Generate AI-powered mitigation recommendations for each scored event, stored in HANA Cloud and surfaced in the dashboard and email alerts
- Provide a React-based risk dashboard with geopolitical heat map, active alerts, supplier impact view, and per-event recommendations panel

### Non-Goals (Out of Scope)
- Integration with SAP Ariba Supplier Risk (post-MVP consideration)
- Integration with SAP IBP for supply chain re-planning
- Support for SAP S/4HANA on-premise or Private Cloud Edition (Public Cloud only in this release)
- Automated supplier replacement or alternative sourcing suggestions
- Financial impact modelling (cost exposure quantification)
- Support for languages other than English in news signal processing

---

## Requirements

### Must-Have Requirements

**R1: Scheduled Geopolitical Signal Ingestion**
- **Problem to Solve:** There is no automated mechanism to continuously fetch geopolitical event data; teams rely on manual news monitoring.
- **User Story:** As a procurement manager, I need the system to automatically fetch and filter geopolitical events from GDELT on a schedule so that I do not need to monitor news manually.
- **Acceptance Criteria:**
  - Given the BTP Job Scheduling Service is configured, when the 15-minute interval fires, then the agent fetches the latest GDELT events
  - Given a fetch completes, when events are retrieved, then only conflict/risk-themed events matching the configured regions are retained
  - Given a fetch fails, when a network or API error occurs, then the agent retries up to 3 times and logs the failure
- **Maps to Objective:** Objective 1
- **Priority Rank:** 1

**R2: Supplier & PO Correlation**
- **Problem to Solve:** Raw geopolitical events have no meaning unless linked to specific suppliers and open purchase orders in SAP.
- **User Story:** As a risk officer, I need each detected geopolitical event to be automatically matched against my active SAP supplier and PO records so that I know exactly which business relationships are at risk.
- **Acceptance Criteria:**
  - Given a filtered event with a country/region tag, when the agent queries SAP S/4HANA, then it retrieves all suppliers with addresses in the affected region
  - Given affected suppliers are identified, when the agent queries open POs, then it returns all POs with those supplier IDs
  - Given no suppliers match, when the agent completes correlation, then the event is recorded as low-relevance and no alert is raised
- **Maps to Objective:** Objective 2
- **Priority Rank:** 2

**R3: AI Risk Scoring & Mitigation Recommendations**
- **Problem to Solve:** Not all geopolitical events carry the same risk â the system must reason about severity in context of the supplier relationship and tell procurement teams exactly what to do next, not just that a problem exists.
- **User Story:** As a supply chain manager, I need each risk event to be assigned a severity score and accompanied by specific, actionable mitigation recommendations so that I know exactly what steps to take and in what order.
- **Acceptance Criteria:**
  - Given an event with correlated suppliers and POs, when the agent analyses the event, then it assigns a score of Low / Medium / High / Critical with a plain-language justification
  - Given a Critical score, when scoring is complete, then the alert is immediately flagged for SAP task creation and notification
  - Given scoring uses an LLM, when the model is unavailable, then the agent falls back to rule-based scoring using CAMEO event codes and PO value thresholds
  - Given any scored event, when scoring completes, then the output includes a ranked list of up to 7 specific, procurement-focused mitigation recommendations tailored to the severity level
  - Given a Critical event, when recommendations are generated, then at least one recommendation addresses alternative sourcing with a specific timeline (e.g. "within 24 hours")
  - Given a High event, when recommendations are generated, then recommendations include supplier contact, safety stock increase, and contingency sourcing actions
  - Given recommendations are generated, when the event is persisted, then they are stored alongside the event record in HANA Cloud and are retrievable via the OData API
- **Maps to Objective:** Objective 2
- **Priority Rank:** 3

**R4: SAP Task Creation**
- **Problem to Solve:** Procurement managers need risk events to appear as actionable tasks inside SAP â not just emails â to integrate into their existing workflow.
- **User Story:** As a procurement manager, I need a SAP task to be created automatically for each High or Critical risk event so that I can take action directly within my existing SAP workflow.
- **Acceptance Criteria:**
  - Given a High or Critical scored event, when the agent calls `API_SUPPLIER_ACTIVITY_TASK_SRV`, then a procurement task is created and assigned to the responsible buyer in SAP S/4HANA
  - Given a task is created, when the buyer opens SAP, then they see the task with the event summary, affected supplier names, PO numbers, and risk severity
  - Given a SAP API call fails, when a task cannot be created, then the failure is logged and the alert is still dispatched via email
- **Maps to Objective:** Objective 3
- **Priority Rank:** 4

**R5: Supplier Risk Profile Update**
- **Problem to Solve:** Supplier risk profiles in SAP become stale because they are updated manually; geopolitical events must flow through automatically.
- **User Story:** As a risk officer, I need supplier risk scores in SAP to be automatically updated when a High or Critical event is detected so that risk classifications remain current without manual intervention.
- **Acceptance Criteria:**
  - Given a High or Critical scored event with identified suppliers, when the agent calls the SAP Supplier Risk API, then the affected supplier risk profile is updated with the new score and a reference to the event
  - Given an update is made, when an auditor reviews the supplier profile, then the event source, timestamp, and previous score are visible in the change log
- **Maps to Objective:** Objective 3
- **Priority Rank:** 5

**R6: Email Alert Notifications**
- **Problem to Solve:** Managers are not always in SAP; they need to be notified immediately when a High or Critical risk is detected.
- **User Story:** As a supply chain manager, I need to receive an email alert when a High or Critical risk event is detected so that I can respond even when I am not logged into SAP.
- **Acceptance Criteria:**
  - Given a High or Critical scored event, when the agent completes scoring, then an email is sent to the responsible manager(s) within 5 minutes of event detection
  - Given the email is sent, when it is received, then it contains: event description, affected regions, impacted suppliers, PO numbers, risk severity, and a link to the dashboard
  - Given a High or Critical event has AI-generated recommendations, when the email is sent, then the email body includes a clearly labelled "AI-Generated Mitigation Recommendations" section with numbered action items
- **Maps to Objective:** Objective 5
- **Priority Rank:** 6

**R7: Risk Intelligence Dashboard**
- **Problem to Solve:** There is no unified view of geopolitical risk against the supplier portfolio; risk data is scattered or non-existent.
- **User Story:** As a risk officer, I need an interactive dashboard showing active geopolitical alerts, affected suppliers, and a regional heat map so that I can maintain a real-time picture of the company's risk exposure.
- **Acceptance Criteria:**
  - Given the dashboard is opened, when data is loaded, then it displays: a world map with risk-coloured regions, a list of active alerts sorted by severity, affected suppliers with PO count and value, and a 30-day risk trend chart
  - Given a new High/Critical event is recorded, when the dashboard is refreshed, then it appears within 1 minute
  - Given a user clicks an alert, when the detail view opens, then it shows the full event description, AI justification, affected suppliers, open POs, current SAP task status, and a colour-coded AI Recommendations panel with numbered mitigation actions
- **Maps to Objective:** Objective 4
- **Priority Rank:** 7

### High-Want Requirements

**R8: Risk Event History & Audit Trail**
- **Problem to Solve:** Risk officers need to demonstrate that risk was monitored and acted upon for compliance reporting.
- **User Story:** As a risk officer, I need a full audit trail of all detected events, scores, and actions taken so that I can produce compliance evidence.
- **Priority Rank:** 1

**R9: Configurable Region & Theme Filters**
- **Problem to Solve:** Risk focus areas change over time; hardcoded filters would require code changes to update.
- **User Story:** As an administrator, I need to configure monitored regions and conflict themes via the dashboard without code changes so that coverage can be adjusted as business needs evolve.
- **Priority Rank:** 2

**R10: Severity Threshold Configuration**
- **Problem to Solve:** Different organisations have different risk tolerances; the threshold for alerting should be configurable.
- **User Story:** As an administrator, I need to configure which severity levels trigger SAP task creation and email alerts so that alert fatigue is avoided.
- **Priority Rank:** 3

**R11: AI Mitigation Recommendations Persistence & Display**
- **Problem to Solve:** The AI agent generates valuable mitigation recommendations at scoring time but without persistence they are discarded after the run, leaving no record of what actions were proposed.
- **User Story:** As a procurement manager, I need to see the AI-generated recommendations on the Alert Detail page and in my alert email so that I can act immediately without having to interpret raw event data myself.
- **Acceptance Criteria:**
  - Given recommendations are generated by the scoring engine, when `persist_risk_event` is called, then the recommendations JSON array is stored in the `recommendations` field of the `RiskEvents` entity in HANA Cloud
  - Given a user opens the Alert Detail page, when the event has recommendations, then a colour-coded "AI-Generated Mitigation Recommendations" panel is displayed between the event header and the affected suppliers table
  - Given a High or Critical email alert is sent, when the email is received, then it contains a numbered "AI-Generated Mitigation Recommendations" section derived from the scoring output
  - Given Low or Medium events, when recommendations are generated, then they are still stored and shown on the dashboard but the email is not sent (severity below threshold)
- **Priority Rank:** 4

---

## Solution Architecture

**Architecture Overview:**
A two-component solution deployed entirely on SAP BTP. The AI Agent (Python, A2A protocol) is triggered by BTP Job Scheduling Service every 15 minutes, fetches and analyses geopolitical signals, and integrates with SAP S/4HANA Cloud Public Edition via OData/REST APIs. The BTP Extension (CAP Node.js + React) provides the persistent data store and interactive dashboard.

**Key Components:**

- **AI Agent (Python/A2A on BTP AI Core):** Core intelligence component. Handles GDELT ingestion, event filtering, supplier/PO correlation via SAP APIs, LLM-based risk scoring, SAP task creation, supplier risk profile updates, and email notification dispatch.
- **BTP Job Scheduling Service:** Free BTP service that triggers the agent on a 15-minute cron schedule. No additional infrastructure required.
- **CAP Backend (Node.js on BTP Cloud Foundry):** OData service exposing risk events, alert history, and supplier impact records stored in SAP HANA Cloud. Consumed by the React dashboard and the AI agent for persistence.
- **React Dashboard (BTP Cloud Foundry):** Interactive frontend built with React and SAP UI5 Web Components. Displays geopolitical heat map, active alerts, supplier risk table, and event detail views.
- **SAP HANA Cloud:** Persistent store for all risk events, scores, alert history, and agent run logs.

**Integration Points:**

- **GDELT API** (`api.gdeltproject.org`): Outbound, read-only, every 15 minutes â geopolitical event feed
- **SAP S/4HANA Cloud Public Edition â Supplier Master OData API**: Inbound read, per agent run â retrieve supplier country/region data
- **SAP S/4HANA Cloud Public Edition â Purchase Order OData API**: Inbound read, per agent run â retrieve open PO data for affected suppliers
- **SAP S/4HANA â Procurement Task API** (`API_SUPPLIER_ACTIVITY_TASK_SRV`): Outbound write, on High/Critical events â create procurement review tasks
- **SAP S/4HANA â Supplier Risk API** (Risk and Criticality Assessment): Outbound write, on High/Critical events â update supplier risk profiles
- **SAP AI Core (Generative AI Hub):** LLM inference for risk scoring and justification generation (GPT-4o or equivalent)
- **SAP BTP Alert Notification Service or SMTP:** Outbound, email dispatch on High/Critical events

**Deployment Environments:**

- **Dev:** BTP subaccount with sandbox S/4HANA system, mock GDELT responses, developer-only access
- **QA:** BTP subaccount with S/4HANA QA tenant, live GDELT feed, restricted test user set
- **Prod:** BTP subaccount with production S/4HANA, live feeds, full RBAC

---

### Agent Extensibility & Instrumentation

**Agent Extensibility:**
The agent is designed with modular tool functions to allow future extension without restructuring the core:
- New external intelligence sources (e.g. ACLED, UN OCHA feeds) can be added as additional ingestion tools
- New SAP integration targets (e.g. SAP IBP, SAP Ariba Supplier Risk) can be added as write tools
- Risk scoring logic is isolated in a dedicated scoring module, allowing model swaps or rule engine fallback without agent restructuring
- Configuration (regions, themes, severity thresholds) is externalised to the CAP backend, enabling runtime changes without redeployment

**Business Step Instrumentation:**
All six business milestones emit structured log statements for observability. Log format: `[MILESTONE_ID].[achieved|missed]: [description]`

---

### Automation & Agent Behaviour

**Automation Level:** Autonomous agent with human-in-the-loop for High/Critical actions

**Actions the system performs without human approval:**
- Fetch and filter GDELT events
- Correlate events to supplier and PO records
- Score risk severity
- Create SAP procurement tasks (for High/Critical events)
- Update supplier risk profiles in SAP (for High/Critical events)
- Send email notifications

**Actions that require human review or approval:**
- Acting on a procurement task (buyer decision)
- Changing supplier status or initiating alternative sourcing (buyer/manager decision)
- Overriding a risk score (risk officer)

**Model used:** GPT-4o via SAP Generative AI Hub (SAP AI Core)

**Knowledge & data sources accessed:**

| Source | Purpose | Access Type |
|---|---|---|
| GDELT API | Real-time geopolitical event signals | Read â external HTTP |
| SAP S/4HANA Supplier Master | Supplier country/region for correlation | Read â OData |
| SAP S/4HANA Purchase Orders | Open PO identification for affected suppliers | Read â OData |
| SAP HANA Cloud (CAP) | Persistence of risk events, alerts, agent logs | Read/Write â OData |

**Tools / connectors invoked:**

- `fetch_gdelt_events(regions, themes, lookback_minutes)` â Read-only; fetches and filters GDELT event feed
- `get_suppliers_by_region(country_codes)` â Read-only; queries SAP supplier master via OData
- `get_open_pos_by_supplier(supplier_ids)` â Read-only; queries SAP PO API
- `score_risk(event, suppliers, pos)` â LLM call via SAP AI Core; returns severity, justification, and ranked mitigation recommendations
- `create_sap_task(supplier_id, po_ids, event_summary, severity)` â Write; creates SAP procurement task
- `update_supplier_risk_profile(supplier_id, score, event_ref)` â Write; updates SAP supplier risk record
- `send_alert_email(recipients, event_summary, severity, dashboard_link, recommendations)` â Write; dispatches email notification including AI-generated mitigation recommendations for High/Critical events
- `persist_risk_event(event_data)` â Write; stores event (including recommendations) in CAP/HANA Cloud

**Guardrails & fail-safes:**
- Agent never modifies financial records, contracts, or PO values autonomously
- LLM scoring confidence below threshold falls back to rule-based CAMEO code scoring
- SAP API failures are retried up to 3 times; persistent failures are logged and alerted to an admin
- Email notifications are only sent for High/Critical severity â Low/Medium events are dashboard-only
- GDELT event volume is capped per run (max 500 events) to prevent processing overload

---

## Milestones

### M1: Signal Ingestion
- **Description:** GDELT events fetched, filtered by theme and region, and persisted
- **Achieved when:** At least one filtered event is retrieved and stored in HANA Cloud in the current agent run
- **Log on achievement:** `M1.achieved: signal ingestion complete â {n} events fetched from GDELT, {k} passed theme/region filters`
- **Log on miss:** `M1.missed: signal ingestion failed â GDELT returned 0 results or fetch error after retries; run aborted`

### M2: Risk Scoring
- **Description:** AI agent correlates filtered events to SAP supplier/PO records and assigns risk severity scores
- **Achieved when:** At least one event has been scored with a severity level and linked to one or more SAP suppliers
- **Log on achievement:** `M2.achieved: risk scoring complete â {n} events scored; {h} High, {c} Critical, {m} Medium, {l} Low`
- **Log on miss:** `M2.missed: risk scoring incomplete â SAP supplier API unreachable or no supplier matches found for any event`

### M3: Alert Dispatch
- **Description:** Email notifications sent to responsible managers for High/Critical events
- **Achieved when:** Email sent successfully for at least one High or Critical event
- **Log on achievement:** `M3.achieved: alert dispatched â {n} emails sent for {h} High and {c} Critical events`
- **Log on miss:** `M3.missed: no alerts dispatched â either no High/Critical events detected or email service unavailable`

### M4: SAP Task Creation
- **Description:** Procurement review tasks created in SAP S/4HANA for High and Critical events
- **Achieved when:** At least one SAP task is successfully created via `API_SUPPLIER_ACTIVITY_TASK_SRV`
- **Log on achievement:** `M4.achieved: SAP tasks created â {n} tasks created for {s} affected suppliers`
- **Log on miss:** `M4.missed: SAP task creation failed â API_SUPPLIER_ACTIVITY_TASK_SRV returned error or no High/Critical events present`

### M5: Supplier Risk Score Update
- **Description:** Supplier risk profiles updated in SAP S/4HANA for affected suppliers
- **Achieved when:** At least one supplier risk profile is successfully updated in SAP
- **Log on achievement:** `M5.achieved: supplier risk profiles updated â {n} suppliers updated with new risk scores`
- **Log on miss:** `M5.missed: supplier risk profile update failed â SAP Supplier Risk API error or no High/Critical suppliers identified`

### M6: Dashboard Review Ready
- **Description:** All risk events, scores, and alerts persisted and visible on the React dashboard
- **Achieved when:** Current run's events are queryable via the CAP OData endpoint and visible in the dashboard
- **Log on achievement:** `M6.achieved: dashboard data ready â {n} new risk events available for review in the risk intelligence dashboard`
- **Log on miss:** `M6.missed: dashboard persistence failed â CAP service write error; events may be missing from dashboard`

---

## Non-Functional Requirements

### Performance
- **Latency:** Full agent run (ingest â score â SAP write â notify) completes within 10 minutes of trigger
- **Throughput:** Handles up to 500 GDELT events per 15-minute run without degradation

### Reliability
- **Availability:** Agent runs on BTP Job Scheduling Service with 99.5% uptime target
- **Fallback:** If LLM scoring is unavailable, rule-based CAMEO scoring ensures continuity

### Cost
- **GDELT:** Free, no API key
- **BTP Job Scheduling:** Included in BTP enterprise contract
- **SAP AI Core:** Metered per token; standard generative AI hub pricing applies

### Explainability
- **Traceability:** Every risk score includes a plain-language LLM justification stored with the event record
- **Decision Logging:** All agent tool calls, inputs, outputs, and milestone states are logged per run in HANA Cloud
- **Uncertainty Communication:** Low-confidence scores are flagged in the dashboard with a "Review Recommended" indicator

---

## Risks, Assumptions, and Dependencies

### Risks
- **GDELT signal noise:** Without precise theme and sentiment filters, high event volume may generate excessive Low-priority alerts; mitigation: configurable filter thresholds and sentiment score cutoff
- **SAP API rate limits:** S/4HANA Cloud Public Edition enforces API rate limits; mitigation: batch supplier/PO queries and implement exponential backoff
- **LLM hallucination in scoring:** Model may mis-classify event severity; mitigation: rule-based fallback and human review for Critical events

### Assumptions
- SAP S/4HANA Cloud Public Edition is accessible via standard OData APIs with OAuth 2.0
- Supplier master data includes country/region fields populated for all active suppliers
- BTP subaccount has SAP AI Core entitlement with Generative AI Hub access
- An SMTP relay or SAP BTP Alert Notification Service is available for email dispatch

### Dependencies
- SAP BTP subaccount with Cloud Foundry runtime, HANA Cloud, AI Core, and Job Scheduling Service entitlements
- SAP S/4HANA Cloud Public Edition with API access enabled for Supplier, PO, Task, and Risk APIs
- GDELT public API (no key required)

---

## Appendix

### Glossary
- **GDELT:** Global Database of Events, Language, and Tone â a free, open geopolitical event database updated every 15 minutes
- **CAMEO:** Conflict and Mediation Event Observations â event coding framework used by GDELT to classify geopolitical events
- **A2A:** Agent-to-Agent protocol â SAP's standard protocol for deploying Python-based AI agents on BTP
- **CAP:** SAP Cloud Application Programming Model â framework for building OData services on BTP
- **BTP Job Scheduling Service:** SAP BTP service providing cron-based job scheduling at no additional cost within BTP enterprise contracts

### References
- GDELT API: https://api.gdeltproject.org
- SAP BTP Job Scheduling Service: https://help.sap.com/docs/job-scheduling
- SAP AI Core / Generative AI Hub: https://help.sap.com/docs/sap-ai-core
- API_SUPPLIER_ACTIVITY_TASK_SRV: SAP S/4HANA Cloud Public Edition API Hub
