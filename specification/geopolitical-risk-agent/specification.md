# Specification: geopolitical-risk-agent

> **Guidelines**: Read [guidelines.md](../guidelines.md) and [guidelines-agent.md](../guidelines-agent.md) before executing ANY tasks below. Follow all constraints described there throughout execution.

## Basic Setup

- [x] Read `product-requirements-document.md` and `intent.md` from the project root
- [x] Bootstrap agent code in `assets/geopolitical-risk-agent/` using skill `sap-agent-bootstrap` (invoke from inside `assets/geopolitical-risk-agent/`, use copy commands — do NOT create files manually)
- [x] Install dependencies, validate the agent starts and responds at `/.well-known/agent.json`

## Signal Ingestion Tools (R1)

- [x] Implement `fetch_gdelt_events(regions: list[str], themes: list[str], lookback_minutes: int) -> list[dict]` tool
  - Query GDELT API v2: `https://api.gdeltproject.org/api/v2/doc/doc?query=<themes>&mode=ArtList&maxrecords=250&format=json`
  - Filter by CAMEO conflict themes: CONFLICT, MILITARY_ATTACK, PROTEST, SANCTION, HOSTILITY
  - Filter by target regions: ISO country codes for Global, Middle East & Africa (AE, SA, IR, IQ, IL, SY, YE, LY, EG, NG, ZA, KE, ET), Eastern Europe (UA, RU, BY, PL, MD, RO)
  - Cap results at 500 events per run to prevent overload
  - Return list of dicts with fields: event_id, date, headline, url, source_country, tone_score, themes
- [x] Implement `fetch_news_articles(keywords: list[str], regions: list[str], lookback_hours: int) -> list[dict]` tool
  - Query NewsAPI: `https://newsapi.org/v2/everything?q=<keywords>&language=en&sortBy=publishedAt`
  - Keywords: conflict, sanctions, supply chain disruption, trade restriction, military, civil unrest
  - Return list of dicts with fields: article_id, title, description, url, published_at, source_name, country

## SAP Supplier & PO Correlation Tools (R2)

- [x] Implement `get_suppliers_by_region(country_codes: list[str]) -> list[dict]` tool
  - Must use MCP tool (from `mcp-translation-file` generated server) — NO direct HTTP calls
  - Query Business Partner OData API filtered by `BusinessPartnerCountry in (country_codes)` and `BusinessPartnerCategory eq '2'` (suppliers)
  - Set `$top=100` on every call
  - Return list of dicts: supplier_id, name, country, city, postal_code
- [x] Implement `get_open_pos_by_supplier(supplier_ids: list[str]) -> list[dict]` tool
  - Must use MCP tool — NO direct HTTP calls
  - Query Purchase Order OData API: filter by `Supplier in (supplier_ids)` and `PurchaseOrderStatus ne 'CLOSED'`
  - Set `$top=100` on every call
  - Return list of dicts: po_number, supplier_id, material, net_value, currency, delivery_date, plant

## Risk Scoring Tool (R3)

- [x] Implement `score_risk(event: dict, affected_suppliers: list[dict], affected_pos: list[dict]) -> dict` tool
  - Call SAP AI Core via LiteLLM (GPT-4o via Generative AI Hub)
  - System prompt must instruct model to: (1) assess conflict severity, (2) consider supplier count and PO value at risk, (3) assign score: Low/Medium/High/Critical, (4) provide 2-sentence plain-language justification, (5) generate up to 7 numbered, procurement-focused mitigation recommendations ordered by urgency
  - Fallback to rule-based scoring if LLM unavailable: Critical if CAMEO code 19+ AND >5 suppliers, High if CAMEO 14-18 OR >2 suppliers, Medium if CAMEO 10-13, Low otherwise
  - Return dict: severity (Low/Medium/High/Critical), score_numeric (1-4), justification, affected_supplier_count, affected_po_count, total_po_value, recommendations (list[str], up to 7 items)
  - Recommendations must be specific and actionable: include supplier contact timelines, alternative sourcing regions, safety stock targets, and PO freeze guidance calibrated to severity level
  - Critical severity: at least one recommendation must contain a 24-hour escalation action
  - Low severity: recommendations focus on monitoring and audit-trail logging only

## SAP Write Tools (R4, R5)

- [x] Implement `create_sap_procurement_task(supplier_id: str, supplier_name: str, po_numbers: list[str], event_summary: str, severity: str, event_date: str) -> dict` tool
  - Must use MCP tool for `API_SUPPLIER_ACTIVITY_TASK_SRV` — NO direct HTTP calls
  - Create task with: TaskType='RISK_REVIEW', Description=f"[{severity}] Geopolitical Risk: {event_summary}", SupplierID=supplier_id
  - Only call for High or Critical severity
  - Return dict: task_id, status, supplier_id
- [x] Implement `update_supplier_risk_score(supplier_id: str, severity: str, event_ref: str, justification: str) -> dict` tool
  - Must use MCP tool — NO direct HTTP calls
  - Update supplier risk profile via Supplier Risk Engagements API
  - Map severity to SAP risk levels: Critical->4, High->3, Medium->2, Low->1
  - Only call for High or Critical severity
  - Return dict: supplier_id, updated_score, previous_score, timestamp

## Notification Tool (R6)

- [x] Implement `send_alert_email(recipients: list[str], event_title: str, severity: str, affected_suppliers: list[dict], affected_po_count: int, total_po_value: float, dashboard_url: str, recommendations: list[str] = None) -> dict` tool
  - Use SAP BTP Alert Notification Service REST API or SMTP via environment variables
  - Only send for High or Critical severity
  - Email body must include: severity badge, event title, region, affected supplier list, PO count + value, link to dashboard
  - When `recommendations` is provided and non-empty, include a clearly labelled "AI-GENERATED MITIGATION RECOMMENDATIONS" section in the email body with numbered action items (up to 7)
  - Return dict: sent (bool), recipient_count, message_id

## Persistence Tool (R7, R8, R11)

- [x] Implement `persist_risk_event(event_data: dict, risk_score: dict, affected_suppliers: list[dict], affected_pos: list[dict], task_ids: list[str]) -> dict` tool
  - POST to CAP OData service at `{CAP_SERVICE_URL}/risk/RiskEvents` (service is mounted at `/risk` via `@(path: '/risk')` annotation — NOT `/odata/v4/risk/RiskEvents`)
  - Payload: event_id, event_date, headline, source_url, severity, score_numeric, justification, affected_supplier_count, affected_po_count, total_po_value, sap_task_ids (CSV), agent_run_id, created_at, recommendations (JSON-serialised string from `risk_score.get("recommendations", [])`)
  - The `recommendations` field is serialised as a JSON array string before persisting (HANA stores it as LargeString/CLOB)
  - Return dict: persisted_id, status

## Agent Orchestration (Main Flow)

- [x] Implement main agent orchestration logic in `app/agent.py` `stream()` method — extract all business logic into `_run_agent()` helper
- [x] `_run_agent()` must execute the full pipeline in order:
  1. Call `fetch_gdelt_events` and `fetch_news_articles` — collect raw signals
  2. Deduplicate events by region/theme cluster
  3. For each unique region with events, call `get_suppliers_by_region`
  4. For each affected supplier batch, call `get_open_pos_by_supplier`
  5. For each event+supplier pair, call `score_risk`
  6. For High/Critical: call `create_sap_procurement_task`, `update_supplier_risk_score`, `send_alert_email` (pass `recommendations=score.get("recommendations", [])`)
  7. Call `persist_risk_event` for all scored events (recommendations are included via the `risk_score` dict which already contains the `recommendations` key)
  8. Return structured summary: events_processed, high_critical_count, tasks_created, suppliers_updated, emails_sent
- [x] Add agent system prompt instructing: never hallucinate supplier or PO data, always set $top=100 on SAP queries, explain when result limits are applied, process only real data from tools
- [x] BTP Job Scheduling Service integration: agent must accept scheduled trigger input (run_id, trigger_time) in addition to natural language queries

## Business Step Instrumentation (Milestones M1–M6)

- [x] Instrument M1 (Signal Ingestion): log `M1.achieved` with event counts after successful fetch+filter; log `M1.missed` on fetch failure with error details
- [x] Instrument M2 (Risk Scoring): log `M2.achieved` with severity breakdown after all events scored; log `M2.missed` if SAP supplier API unreachable or zero matches
- [x] Instrument M3 (Alert Dispatch): log `M3.achieved` with email count; log `M3.missed` if no High/Critical events or email service unavailable
- [x] Instrument M4 (SAP Task Creation): log `M4.achieved` with task count and supplier names; log `M4.missed` on API error or no High/Critical events
- [x] Instrument M5 (Supplier Risk Update): log `M5.achieved` with updated supplier count; log `M5.missed` on API error
- [x] Instrument M6 (Dashboard Ready): log `M6.achieved` with persisted event count; log `M6.missed` on CAP write failure
- [x] Add OpenTelemetry spans for each milestone using decorator or context-manager form on `_run_agent()` and sub-methods — NEVER inside async generators
- [x] Verify `auto_instrument()` called at top of `main.py` before any AI framework imports

## API Specs – MCP Translation

- [x] Verify `specification/geopolitical-risk-agent/api-specs/` contains:
  - `procurement-task.json` (API_SUPPLIER_ACTIVITY_TASK_SRV — create procurement review tasks)
  - `purchase-order.json` (CE_PURCHASEORDER_0001 — read open POs)
  - `business-partner.json` (Master Data for Business Partner — read supplier country/region)
- [x] Invoke `mcp-translation-file` skill for each API spec file to generate MCP translation files and server cards
- [x] Invoke `setup-solution` skill to register MCP server assets for each generated translation file
- [x] Invoke `mcp-mock-config` skill to generate `mcp-mock.json` (required before tests run)

## Testing

- [x] `conftest.py` only sets `IBD_TESTING=true`
- [x] Write unit test for each tool (9 tools total): `test_fetch_gdelt_events.py`, `test_fetch_news_articles.py`, `test_get_suppliers_by_region.py`, `test_get_open_pos_by_supplier.py`, `test_score_risk.py`, `test_create_sap_procurement_task.py`, `test_update_supplier_risk_score.py`, `test_send_alert_email.py`, `test_persist_risk_event.py`
- [x] Mock all LLM calls (AI Core) in unit tests — use canned score responses
- [x] Mock all MCP tool calls using `mcp-mock.json` fixture data
- [x] `test_send_alert_email.py`: verify recommendations block appears in email body when passed for High/Critical severity; verify no recommendations section for Low/Medium
- [x] `test_persist_risk_event.py`: verify recommendations JSON string is included in OData POST payload
- [x] `test_score_risk.py`: assert returned dict contains `recommendations` key with a non-empty list for High and Critical severities
- [x] Write one integration test `test_agent_integration.py`: trigger full `_run_agent()` flow with mocked MCP + mocked LLM, verify M1–M6 milestones all log `achieved`, verify returned summary has expected structure
- [x] Run `pytest` from `assets/geopolitical-risk-agent/` (no args) — fix failures before proceeding
- [x] If coverage < 70%, add targeted tests until threshold met
- [x] Verify `grep -c "^@agent_model\|^@agent_config\|^@prompt_section" assets/geopolitical-risk-agent/app/agent.py` returns exactly 3
- [x] Run `pytest` again (no args) to generate final `test_report.json`
- [x] Verify `test_report.json` exists in `assets/geopolitical-risk-agent/`

## Agent Evaluation

- [x] Invoke `sap-aeval-generate-tool-schema` skill from `assets/geopolitical-risk-agent/` to generate `tools.json`
- [x] Invoke `sap-aeval-generate-testcase` skill passing `specification/geopolitical-risk-agent/specification.md` and `tools.json`
- [x] Review generated test cases in `aeval/testcases/` and replace placeholder values with realistic geopolitical risk scenarios
