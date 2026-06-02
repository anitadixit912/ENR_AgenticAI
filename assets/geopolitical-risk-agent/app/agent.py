"""Geopolitical Risk Intelligence Agent â main agent definition."""
import logging
import os
from typing import AsyncIterable

from sap_cloud_sdk.agent_decorators import agent_config, agent_model, prompt_section
from opentelemetry import trace

from tools.gdelt_tool import fetch_gdelt_events
from tools.news_tool import fetch_news_articles
from tools.supplier_tool import get_suppliers_by_region, get_open_pos_by_supplier
from tools.risk_scoring_tool import score_risk
from tools.sap_task_tool import create_sap_procurement_task
from tools.supplier_risk_tool import update_supplier_risk_score
from tools.alert_tool import send_alert_email
from tools.persistence_tool import persist_risk_event
from mcp_tools import get_mcp_tools
from aicore_config import build_llm, validate_aicore_credentials

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

DEFAULT_REGIONS = ["middle_east_africa", "eastern_europe", "global"]
DEFAULT_THEMES = ["CONFLICT", "MILITARY_ATTACK", "PROTEST", "SANCTION", "HOSTILITY"]
ALERT_RECIPIENTS = [r.strip() for r in os.environ.get("ALERT_RECIPIENTS", "anita.dixit@sap.com").split(",") if r.strip()]
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "http://localhost:4004")


@agent_model(key="config.model", label="LLM Model", description="AI model for risk scoring")
def get_model():
    return build_llm(temperature=0.1)


@agent_config(key="config.temperature", label="Temperature", description="LLM temperature for risk scoring (0.0-1.0)")
def get_temperature():
    return 0.1


@prompt_section(key="system.prompt", label="System Prompt", description="Core instructions for the geopolitical risk agent")
def get_system_prompt():
    return """You are a geopolitical risk intelligence agent. You monitor real-time conflict signals from GDELT and NewsAPI, correlate them with active SAP supplier and purchase order data, and produce structured risk assessments.

Always use real data from tools â never hallucinate supplier names, PO numbers, or event details.
Always set $top=100 on every SAP API call that accepts it to prevent context overflow, and inform the user when this limit is applied.
When scoring risk, consider both event severity (CAMEO codes) and business impact (number of affected suppliers and total PO value at risk).
Only create SAP tasks and update supplier risk profiles for High and Critical severity events.
"""


class GeopoliticalRiskAgent:
    def __init__(self):
        self._tools = None
        self._graph = None

    async def _get_tools(self) -> list:
        if self._tools is None:
            mcp_tools = await get_mcp_tools()
            self._tools = [
                fetch_gdelt_events,
                fetch_news_articles,
                get_suppliers_by_region,
                get_open_pos_by_supplier,
                score_risk,
                create_sap_procurement_task,
                update_supplier_risk_score,
                send_alert_email,
                persist_risk_event,
                *mcp_tools
            ]
        return self._tools

    async def _run_agent(self, query: str, context_id: str) -> dict:
        """Core pipeline: ingest â correlate â score â act â persist."""
        run_summary = {
            "events_processed": 0,
            "high_critical_count": 0,
            "tasks_created": 0,
            "suppliers_updated": 0,
            "emails_sent": 0,
            "errors": []
        }

        # M1: Signal Ingestion
        with tracer.start_as_current_span("m1_signal_ingestion"):
            gdelt_events = fetch_gdelt_events.invoke({
                "regions": DEFAULT_REGIONS,
                "themes": DEFAULT_THEMES,
                "lookback_minutes": 60
            })
            news_articles = fetch_news_articles.invoke({
                "keywords": ["conflict", "sanctions", "military", "civil unrest"],
                "regions": DEFAULT_REGIONS,
                "lookback_hours": 6
            })
            all_signals = gdelt_events + news_articles
            if not all_signals:
                logger.warning("M1.missed: signal ingestion returned 0 events â no data to process")
                return run_summary
            logger.info("M1.achieved: signal ingestion complete â %d GDELT events, %d news articles, %d total",
                        len(gdelt_events), len(news_articles), len(all_signals))
            run_summary["events_processed"] = len(all_signals)

        # M2: Risk Scoring â correlate events with suppliers and POs
        scored_events = []
        with tracer.start_as_current_span("m2_risk_scoring"):
            country_codes = list({e.get("source_country", "").upper() for e in gdelt_events if e.get("source_country")})
            if not country_codes:
                country_codes = ["UA", "RU", "IL", "SA", "AE", "IR"]

            suppliers = get_suppliers_by_region.invoke({"country_codes": country_codes[:20]})
            supplier_ids = [s["supplier_id"] for s in suppliers if s.get("supplier_id")]
            open_pos = get_open_pos_by_supplier.invoke({"supplier_ids": supplier_ids[:50]}) if supplier_ids else []

            if not suppliers:
                logger.warning("M2.missed: risk scoring incomplete â no SAP supplier matches found")

            for event in all_signals[:50]:
                event_country = event.get("source_country", "").upper()
                event_suppliers = [s for s in suppliers if s.get("country", "").upper() == event_country] or suppliers[:5]
                event_pos = [po for po in open_pos if po.get("supplier_id") in [s["supplier_id"] for s in event_suppliers]]

                score = score_risk.invoke({
                    "event": event,
                    "affected_suppliers": event_suppliers,
                    "affected_pos": event_pos
                })
                scored_events.append((event, score, event_suppliers, event_pos))

            high_critical = [(e, s, sup, pos) for e, s, sup, pos in scored_events if s.get("severity") in ("High", "Critical")]
            run_summary["high_critical_count"] = len(high_critical)

            severity_counts = {}
            for _, s, _, _ in scored_events:
                sev = s.get("severity", "Low")
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
            logger.info("M2.achieved: risk scoring complete â %d events scored; %s",
                        len(scored_events), severity_counts)

        # M3: Alert Dispatch
        with tracer.start_as_current_span("m3_alert_dispatch"):
            emails_sent = 0
            for event, score, event_suppliers, event_pos in high_critical:
                if ALERT_RECIPIENTS and any(r.strip() for r in ALERT_RECIPIENTS):
                    result = send_alert_email.invoke({
                        "recipients": [r.strip() for r in ALERT_RECIPIENTS if r.strip()],
                        "event_title": event.get("headline", "Geopolitical event detected"),
                        "severity": score["severity"],
                        "affected_suppliers": event_suppliers,
                        "affected_po_count": score.get("affected_po_count", 0),
                        "total_po_value": score.get("total_po_value", 0),
                        "dashboard_url": DASHBOARD_URL,
                        "recommendations": score.get("recommendations", []),
                    })
                    if result.get("sent"):
                        emails_sent += 1
            run_summary["emails_sent"] = emails_sent
            if emails_sent > 0:
                logger.info("M3.achieved: alert dispatched â %d emails sent for %d High/Critical events",
                            emails_sent, len(high_critical))
            else:
                logger.info("M3.missed: no alerts dispatched â either no High/Critical events or email service unavailable")

        # M4: SAP Task Creation
        tasks_created = 0
        with tracer.start_as_current_span("m4_sap_task_creation"):
            for event, score, event_suppliers, event_pos in high_critical:
                for supplier in event_suppliers[:3]:
                    po_numbers = [po["po_number"] for po in event_pos if po.get("supplier_id") == supplier.get("supplier_id")]
                    result = create_sap_procurement_task.invoke({
                        "supplier_id": supplier.get("supplier_id", ""),
                        "supplier_name": supplier.get("name", ""),
                        "po_numbers": po_numbers,
                        "event_summary": event.get("headline", "")[:200],
                        "severity": score["severity"],
                        "event_date": event.get("date", "")
                    })
                    if result.get("status") == "CREATED":
                        tasks_created += 1
            run_summary["tasks_created"] = tasks_created
            if tasks_created > 0:
                logger.info("M4.achieved: SAP tasks created â %d tasks for High/Critical events", tasks_created)
            else:
                logger.info("M4.missed: SAP task creation failed or no High/Critical events present")

        # M5: Supplier Risk Score Update
        suppliers_updated = 0
        with tracer.start_as_current_span("m5_supplier_risk_update"):
            updated_supplier_ids = set()
            for event, score, event_suppliers, _ in high_critical:
                for supplier in event_suppliers[:3]:
                    sid = supplier.get("supplier_id", "")
                    if sid and sid not in updated_supplier_ids:
                        result = update_supplier_risk_score.invoke({
                            "supplier_id": sid,
                            "severity": score["severity"],
                            "event_ref": event.get("event_id", ""),
                            "justification": score.get("justification", "")
                        })
                        if result.get("status") == "UPDATED":
                            suppliers_updated += 1
                            updated_supplier_ids.add(sid)
            run_summary["suppliers_updated"] = suppliers_updated
            if suppliers_updated > 0:
                logger.info("M5.achieved: supplier risk profiles updated â %d suppliers", suppliers_updated)
            else:
                logger.info("M5.missed: supplier risk profile update â no High/Critical suppliers or API error")

        # M6: Dashboard Persistence
        persisted_count = 0
        with tracer.start_as_current_span("m6_dashboard_persistence"):
            for event, score, event_suppliers, event_pos in scored_events[:50]:
                result = persist_risk_event.invoke({
                    "event_data": event,
                    "risk_score": score,
                    "affected_suppliers": event_suppliers,
                    "affected_pos": event_pos,
                    "task_ids": []
                })
                if result.get("status") == "PERSISTED":
                    persisted_count += 1
            if persisted_count > 0:
                logger.info("M6.achieved: dashboard data ready â %d new risk events available", persisted_count)
            else:
                logger.warning("M6.missed: dashboard persistence failed â CAP write errors")

        return run_summary

    async def stream(self, query: str, context_id: str, ext_impl=None) -> AsyncIterable[str]:
        """Stream agent responses for a given query."""
        from langchain.agents import AgentExecutor, create_tool_calling_agent
        from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

        # ââ Pre-flight: check AI Core credentials ââââââââââââââââââââââââââââ
        creds_ok, missing_vars = validate_aicore_credentials()
        if not creds_ok:
            missing_list = "\n".join(missing_vars)
            error_msg = (
                "â ï¸ **LLM unavailable â SAP AI Core credentials are not configured.**\n\n"
                "The following environment variables are missing or empty:\n"
                f"{missing_list}\n\n"
                "**How to fix:**\n"
                "- **Local development:** fill in `.env` with values from your AI Core service key "
                "(BTP Cockpit â Instances â AI Core â Service Keys).\n"
                "- **BTP deployment:** inject credentials as Kubernetes secrets via the platform. "
                "The `cred-customer-agent` secret must include the AI Core binding.\n\n"
                "Scheduled pipeline runs will still use rule-based scoring as a fallback."
            )
            logger.error(
                "LLM request blocked â AI Core credentials missing: %s",
                ", ".join(v.split("â")[0].strip().lstrip("â¢ ") for v in missing_vars),
            )
            yield error_msg
            return
        # âââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââââ

        # For scheduled runs, execute the full pipeline (no LLM agent executor needed)
        if "run geopolitical risk scan" in query.lower() or "scheduled" in query.lower():
            try:
                summary = await self._run_agent(query, context_id)
            except Exception as exc:
                logger.exception("Scheduled pipeline failed: %s", exc)
                yield f"â Geopolitical risk scan failed: {exc}"
                return
            yield (
                f"Geopolitical risk scan complete.\n"
                f"- Events processed: {summary['events_processed']}\n"
                f"- High/Critical alerts: {summary['high_critical_count']}\n"
                f"- SAP tasks created: {summary['tasks_created']}\n"
                f"- Supplier profiles updated: {summary['suppliers_updated']}\n"
                f"- Alert emails sent: {summary['emails_sent']}"
            )
            return

        # For conversational queries, build and run the LangChain agent executor
        try:
            llm = build_llm(temperature=get_temperature())
        except RuntimeError as exc:
            logger.error("Failed to build LLM: %s", exc)
            yield f"â ï¸ {exc}"
            return

        try:
            tools = await self._get_tools()

            prompt = ChatPromptTemplate.from_messages([
                ("system", get_system_prompt()),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ])

            agent = create_tool_calling_agent(llm, tools, prompt)
            executor = AgentExecutor(agent=agent, tools=tools, verbose=False, max_iterations=10)

            async for chunk in executor.astream({"input": query}):
                if "output" in chunk:
                    yield chunk["output"]
                elif "messages" in chunk:
                    for msg in chunk["messages"]:
                        if hasattr(msg, "content") and msg.content:
                            yield msg.content

        except Exception as exc:
            logger.exception("Agent executor failed for query %r: %s", query, exc)
            yield (
                f"â An error occurred while processing your request: {exc}\n\n"
                "Please check the agent logs for details."
            )
