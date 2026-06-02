# Specification: churn-prevention-agent

> **Guidelines**: Read [guidelines.md](../guidelines.md) and [guidelines-agent.md](../guidelines-agent.md) before executing ANY tasks below. Follow all constraints described there throughout execution.

## Basic Setup

- [x] Read `product-requirements-document.md` and `intent.md` for full context before implementing
- [x] Bootstrap agent code in `assets/churn-prevention-agent/` using skill `sap-agent-bootstrap` (invoke from inside `assets/churn-prevention-agent/`, use copy commands — do NOT create files manually)
- [x] Install dependencies, validate the agent starts and responds at `/.well-known/agent.json`

## MCP Tool Wiring — Sales Order MCP Server (Path B: existing MCP server)

The Sales Order MCP server is already available. Schemas are in `specification/churn-prevention-agent/mcp-specs/`.

- [ ] Read `specification/churn-prevention-agent/mcp-specs/mcp-spec-sales-order-list-salesorder.json` — understand `list_salesorder` tool (filter by `SoldToParty` and `CreationDate` for 12-week rolling window; `select` key fields: `SalesOrder,SoldToParty,CreationDate,TotalNetAmount,TransactionCurrency,OverallSDProcessStatus,SDDocumentReason`)
- [ ] Read `specification/churn-prevention-agent/mcp-specs/mcp-spec-sales-order-list-salesorderitem.json` — understand `list_salesorderitem` tool (filter by `SalesOrder`; `select` key fields: `SalesOrder,SalesOrderItem,Material,NetAmount,SalesDocumentRjcnReason`)
- [ ] Wire MCP tool loading in `app/agent.py` using `get_mcp_tools()` from `mcp_tools.py` — lazy loading pattern per guidelines; NEVER hard-code tool names; always set `top` ≤ 100 in system prompt
- [ ] Add `sales_order_mcp_demo` to `asset.yaml` under `requires`:
  ```yaml
  requires:
    - name: sales_order_mcp_demo
      kind: mcp-server
      ordId: sap.mcpbuilder:apiResource:sales_order_mcp_demo:v1
  ```

## MCP Translation Files — Sales Cloud APIs (Path A: REST APIs without MCP server)

Two Sales Cloud REST API specs are already downloaded:
- `specification/churn-prevention-agent/api-specs/account-service.json` — SAP Sales Cloud Account Service (REST)
  - Key endpoint: `GET /sap/c4c/api/v1/account-service/accounts` — filter by `id` or query params to get account profile, owner, segment
  - Key endpoint: `GET /sap/c4c/api/v1/account-service/accounts/{id}` — get single account by ID
- `specification/churn-prevention-agent/api-specs/opportunity-service.json` — SAP Sales Cloud Opportunity Service (REST)
  - Key endpoint: `GET /sap/c4c/api/v1/opportunity-service/opportunities` — filter by account to get open opportunities with lifecycle status and forecast category

- [ ] Invoke `mcp-translation-file` skill to generate MCP translation files from both API specs:
  - `account-service.json` → MCP translation for account profile enrichment (tools needed: list accounts, get account by ID)
  - `opportunity-service.json` → MCP translation for opportunity context (tools needed: list opportunities filtered by account)
- [ ] Invoke `setup-solution` skill to create and register MCP server assets for the generated translation files
- [ ] Add the new MCP server assets to `asset.yaml` under `requires` (alongside the existing Sales Order MCP server entry)
- [ ] Invoke `mcp-mock-config` skill to generate `mcp-mock.json` incorporating all three MCP servers (Sales Order + Account + Opportunity)

## Signal Ingestion Logic (M1)

Implements requirement R1 — 12-week rolling order and complaint/return signal per customer.

- [ ] Implement `signal_ingestion.py` in `app/` with an async function `ingest_signals(customer_ids: list[str], tools: list) -> dict`:
  - For each customer ID, call `list_salesorder` tool with filter `SoldToParty eq '{id}' and CreationDate ge datetime'{12_weeks_ago}'` and `top=100`
  - For each returned order, call `list_salesorderitem` tool with filter `SalesOrder eq '{order_id}'` and `select` for rejection reason fields to detect returns/complaints
  - Compute per-customer: order frequency (count of orders), order value trend (average net amount week-over-week for last 4 weeks vs prior 8 weeks), return/complaint count (items with non-empty `SalesDocumentRjcnReason`)
  - Return dict keyed by customer ID with fields: `order_count`, `avg_net_amount_recent`, `avg_net_amount_prior`, `value_trend_pct`, `return_count`, `orders_raw`
- [ ] Emit `M1.achieved: signal ingestion complete — {account_count} accounts retrieved` on success
- [ ] Emit `M1.missed: signal ingestion failed — {error_detail} — cycle aborted` on any unrecoverable error; re-raise to abort cycle
- [ ] Add OpenTelemetry span for this step using decorator `@tracer.start_as_current_span("signal_ingestion")`

## Account Enrichment Logic

Implements account context enrichment from Sales Cloud.

- [ ] Implement `account_enrichment.py` in `app/` with async function `enrich_accounts(customer_ids: list[str], tools: list) -> dict`:
  - For each customer ID, call the Account Service MCP tool to retrieve account name, segment, assigned owner (account manager ID), and account status
  - For each customer ID, call the Opportunity Service MCP tool to retrieve open opportunities (lifecycle status ≠ closed) with forecast category and total expected revenue
  - Return dict keyed by customer ID with fields: `account_name`, `segment`, `owner_id`, `open_opportunity_count`, `total_opportunity_value`
  - If Account Service or Opportunity Service is unavailable, log a warning and return partial enrichment data — do not abort the cycle

## Churn Scoring Logic (M2)

Implements requirement R2 — AI Core model scoring.

- [ ] Implement `churn_scoring.py` in `app/` with async function `score_accounts(signals: dict, enrichment: dict, llm, threshold: int = 65) -> dict`:
  - Construct a structured prompt for the LLM containing: order frequency, value trend %, return count, open opportunity count; instruct the model to return a JSON object with `risk_score` (0–100), `confidence` (High/Medium/Low), and `top_signals` (list of up to 3 contributing signal descriptions)
  - Accounts with `order_count < 4` in the trailing 12-week window are excluded from scoring: add them to `watch_list` instead
  - Accounts with `risk_score >= threshold` are flagged as `at_risk`
  - Return: `{"scored": {customer_id: {risk_score, confidence, top_signals}}, "at_risk": [customer_ids], "watch_list": [customer_ids]}`
- [ ] Emit `M2.achieved: scoring complete — {scored_count} scored, {flagged_count} flagged >={threshold}, {watchlist_count} watch-listed`
- [ ] Emit `M2.missed: scoring incomplete — {error_detail} — affected accounts: {account_ids}` per failure; continue scoring remaining accounts
- [ ] Add OpenTelemetry span: `@tracer.start_as_current_span("churn_scoring")`

## Audit Logging (M4)

Implements requirement R4 — GDPR-compliant action logging via BTP Audit Log Service.

- [ ] Implement `audit_logger.py` in `app/` with async function `log_action(action_type: str, account_id: str, payload: dict) -> bool`:
  - Use the BTP Audit Log Service REST API (environment variable `AUDIT_LOG_URL` and `AUDIT_LOG_TOKEN`) to write a structured audit entry
  - Entry schema: `{"timestamp": ISO8601, "action_type": action_type, "account_id": account_id, "payload": payload}` — payload contains score, signals, recipients for alert actions; signal counts for scoring actions
  - PII rule: `account_name` must never appear in the payload; only `account_id` is written
  - Return `True` on success, `False` on failure
  - If log write fails, return `False` and the caller (alert dispatch) MUST NOT send the alert for the affected account
- [ ] Emit `M4.achieved: audit logging complete — {entry_count} entries written`
- [ ] Emit `M4.missed: audit write failed for {account_ids} — alert dispatch halted for affected accounts`
- [ ] Add OpenTelemetry span: `@tracer.start_as_current_span("audit_logging")`

## Alert Dispatch (M3)

Implements requirement R3 — Joule alert delivery.

- [ ] Implement `alert_dispatcher.py` in `app/` with async function `dispatch_alerts(at_risk: list[str], scores: dict, enrichment: dict, tools: list) -> dict`:
  - For each at-risk account:
    1. Call `audit_logger.log_action("ALERT_DISPATCH", account_id, ...)` — if it returns `False`, skip the alert and log a warning
    2. Construct alert content: account ID (not name — name injected only at render), risk score, confidence band, top 3 signal descriptions
    3. Deliver Joule notification to: `enrichment[account_id]["owner_id"]` (account manager), sales manager (from environment variable `SALES_MANAGER_ID`), CSM (from environment variable `CSM_ID`)
    4. Record delivery status per recipient
  - Return: `{"dispatched": count, "failed": [account_ids], "recipients_notified": total_recipient_count}`
- [ ] Emit `M3.achieved: alerts dispatched — {alert_count} alerts sent to {recipient_count} recipients`
- [ ] Emit `M3.missed: alert delivery failed for {account_ids} — fallback email triggered`
- [ ] Add OpenTelemetry span: `@tracer.start_as_current_span("alert_dispatch")`

## Portfolio Summary (M5)

Implements requirement R5 — weekly summary for sales managers.

- [ ] Implement `portfolio_summary.py` in `app/` with async function `send_portfolio_summary(scanned: int, flagged: int, alerts_sent: int, watch_listed: int) -> bool`:
  - Compose a natural-language Joule summary message: "Weekly churn scan complete. {scanned} accounts scanned, {flagged} at-risk flagged, {alerts_sent} alerts dispatched, {watch_listed} accounts on watch list."
  - Send to all sales managers (list from environment variable `SALES_MANAGER_IDS`, comma-separated)
  - Return `True` on success, `False` on failure
- [ ] Emit `M5.achieved: portfolio summary delivered — {scanned_count} scanned, {flagged_count} flagged, {alert_count} alerts sent`
- [ ] Emit `M5.missed: portfolio summary delivery failed — {error_detail}`
- [ ] Add OpenTelemetry span: `@tracer.start_as_current_span("portfolio_summary")`

## Agent Orchestration

- [ ] Implement the main orchestration flow in `app/agent.py` using the bootstrap pattern:
  - Extract all business logic into `async def _run_agent(query: str, tools: list) -> str` (NOT inside `stream()` — see guidelines instrumentation constraint)
  - `_run_agent` calls in sequence: `ingest_signals()` → `enrich_accounts()` → `score_accounts()` → `dispatch_alerts()` → `send_portfolio_summary()`
  - Pass result counts between steps; surface final portfolio summary as the agent's response
  - `stream()` calls `_run_agent()` and yields the result
- [ ] System prompt MUST include:
  - "Always set top to a maximum of 100 on every tool call that accepts a top parameter."
  - "Never invent or hallucinate customer data. If data is unavailable for an account, exclude it from scoring."
  - "Customer names must never be included in audit log payloads or intermediate tool calls — use account IDs only."
- [ ] Wire `@agent_model`, `@agent_config` (temperature=0.2), `@prompt_section` — exactly 3 decorated functions; no additional decorators
- [ ] Define plain Python constants for: `CHURN_THRESHOLD = 65`, `MIN_ORDER_COUNT = 4`, `SIGNAL_WINDOW_WEEKS = 12`, `PAGE_SIZE = 100`
- [ ] Verify `auto_instrument()` is called at top of `main.py` before any AI framework imports

## Business Step Instrumentation

- [ ] Verify all 5 milestone log patterns exist in the codebase:
  ```bash
  grep -r "M1\.achieved\|M2\.achieved\|M3\.achieved\|M4\.achieved\|M5\.achieved" assets/churn-prevention-agent/app/
  grep -r "M1\.missed\|M2\.missed\|M3\.missed\|M4\.missed\|M5\.missed" assets/churn-prevention-agent/app/
  ```
- [ ] Verify OpenTelemetry spans exist for all 5 business steps:
  ```bash
  grep -r "start_as_current_span" assets/churn-prevention-agent/app/
  ```
- [ ] Verify `auto_instrument()` call at top of `main.py`:
  ```bash
  head -5 assets/churn-prevention-agent/app/main.py
  ```

## Testing

- [ ] `conftest.py` only sets `IBD_TESTING=true` — this causes the agent to run with mock MCP tool results during tests
- [ ] Write unit tests in `assets/churn-prevention-agent/tests/` — one per tool/component:
  - `test_signal_ingestion.py` — mock `list_salesorder` and `list_salesorderitem` tools; verify 12-week filter is applied; verify return/complaint detection
  - `test_account_enrichment.py` — mock Account Service and Opportunity Service MCP tools; verify partial enrichment fallback when service unavailable
  - `test_churn_scoring.py` — mock LLM returning known risk scores; verify watch-list exclusion for accounts with < 4 orders; verify threshold gating at 65
  - `test_audit_logger.py` — mock BTP Audit Log API; verify PII rule (account_name not in payload); verify alert dispatch is blocked when log write fails
  - `test_alert_dispatcher.py` — mock audit_logger and Joule notification; verify alert skipped when audit fails; verify recipient list
  - `test_portfolio_summary.py` — mock Joule notification; verify summary content and recipient list
  - Run each test immediately after writing it
- [ ] Write one integration test `test_integration.py` executing end-to-end agent flow with mocked LLM, mocked MCP tools (via `mcp-mock.json`), and mocked external services (BTP Audit Log, Joule)
- [ ] Run `pytest` from `assets/churn-prevention-agent/` (no args) — if coverage < 70%, add tests until threshold met
- [ ] Verify exactly 3 decorated functions: `grep -c "^@agent_model\|^@agent_config\|^@prompt_section" assets/churn-prevention-agent/app/agent.py` must return 3
- [ ] Run `pytest` again from `assets/churn-prevention-agent/` (no args) to generate final `test_report.json`
- [ ] Verify `test_report.json` exists in `assets/churn-prevention-agent/`

## Validation Checklist

- [ ] Run full validation before marking implementation complete:
  ```bash
  # Instrumentation
  grep -r "M[0-9]\.achieved" assets/churn-prevention-agent/app/     # must return 5 results

  # Decorators
  grep -r "sap_cloud_sdk.agent_decorators" assets/churn-prevention-agent/app/  # must return results
  grep -c "^@agent_model\|^@agent_config\|^@prompt_section" assets/churn-prevention-agent/app/agent.py  # must return 3

  # Test report
  ls assets/churn-prevention-agent/test_report.json                  # must exist
  ```
