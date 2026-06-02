import logging
import os
import time
from dataclasses import dataclass
from typing import AsyncGenerator, Literal, Sequence

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langchain_litellm import ChatLiteLLM
from langgraph.checkpoint.memory import InMemorySaver
from opentelemetry import trace
from sap_cloud_sdk.agent_decorators import agent_config, agent_model, prompt_section

from account_enrichment import enrich_accounts
from alert_dispatcher import dispatch_alerts
from churn_scoring import score_accounts
from portfolio_summary import send_portfolio_summary
from signal_ingestion import ingest_signals

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Business constants — plain Python constants, NOT @agent_config decorated
CHURN_THRESHOLD: int = 65
MIN_ORDER_COUNT: int = 4
SIGNAL_WINDOW_WEEKS: int = 12
PAGE_SIZE: int = 100

# Demo customer IDs used when running a scan without explicit input
DEFAULT_CUSTOMER_IDS: list[str] = os.environ.get(
    "CUSTOMER_IDS", "C1001,C1002,C1003"
).split(",")

THREAD_TTL_SECONDS = 3600  # evict threads inactive for 1 hour


@agent_model(
    key="config.model",
    label="LLM Model",
    description="The language model powering this agent",
)
def get_model_name() -> str:
    return "sap/anthropic--claude-4.5-sonnet"


@agent_config(
    key="config.temperature",
    label="LLM Temperature",
    description="Controls randomness of responses (0.0 = deterministic, 1.0 = creative)",
)
def get_temperature() -> float:
    return 0.2


@prompt_section(
    key="prompts.system",
    label="System Prompt",
    description="The full system prompt defining the agent's role and behavior",
    validation={"format": "markdown", "max_length": 5000},
)
def get_system_prompt() -> str:
    return """You are a Customer Churn Prevention Agent for SAP S/4HANA.

Your role:
- Ingest rolling 12-week sales order and return/complaint signals per customer from S/4HANA
- Score each customer account on a 0-100 churn risk index
- Flag accounts with risk score >= 65 as at-risk
- Dispatch personalised Joule alerts to account managers, sales managers, and CSMs
- Log every action to the BTP Audit Log Service for GDPR compliance
- Deliver a portfolio-level weekly summary to sales managers

Rules you MUST follow:
- Always set top to a maximum of 100 on every tool call that accepts a top parameter.
- Never invent or hallucinate customer data. If data is unavailable for an account, exclude it from scoring.
- Customer names must never be included in audit log payloads or intermediate tool calls — use account IDs only.
- Accounts with fewer than 4 completed orders in the trailing 12-week window go to the watch list, not scoring.
- If audit logging fails for an account, do NOT dispatch the alert for that account.

When the user asks to run a churn scan or weekly analysis, execute the full pipeline:
1. Signal Ingestion (M1) → 2. Account Enrichment → 3. Churn Scoring (M2) →
4. Audit Logging (M4) → 5. Alert Dispatch (M3) → 6. Portfolio Summary (M5)
"""


@dataclass
class AgentResponse:
    status: Literal["input_required", "completed", "error"]
    message: str


class SampleAgent:
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        self.llm = ChatLiteLLM(model=get_model_name(), temperature=get_temperature())
        self._checkpointer = InMemorySaver()
        self._last_active: dict[str, float] = {}
        self._summarization_middleware = SummarizationMiddleware(
            model=self.llm,
            trigger=("tokens", 100_000),
        )

    def _touch(self, thread_id: str) -> None:
        now = time.monotonic()
        expired = [
            tid for tid, ts in list(self._last_active.items())
            if now - ts > THREAD_TTL_SECONDS
        ]
        for tid in expired:
            self._checkpointer.delete_thread(tid)
            del self._last_active[tid]
            logger.info("Evicted inactive thread: %s", tid)
        self._last_active[thread_id] = now

    async def _run_agent(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None,
    ) -> str:
        """
        Core orchestration logic — extracted from stream() to allow safe OTel instrumentation.
        Runs the full churn prevention pipeline when the query requests a scan,
        or delegates to the LLM graph for conversational queries.
        """
        with tracer.start_as_current_span("churn_prevention_run"):
            scan_keywords = ("scan", "run", "weekly", "churn", "at-risk", "at risk", "risk")
            is_scan_request = any(kw in query.lower() for kw in scan_keywords)

            if is_scan_request and tools:
                return await self._run_churn_pipeline(tools)
            else:
                # Conversational / non-pipeline query — delegate to LLM graph
                graph = create_agent(
                    self.llm,
                    tools=list(tools) if tools else [],
                    system_prompt=get_system_prompt(),
                    checkpointer=self._checkpointer,
                    middleware=[self._summarization_middleware],
                )
                config = {"configurable": {"thread_id": context_id}}
                result = await graph.ainvoke(
                    {"messages": [HumanMessage(content=query)]}, config
                )
                return result["messages"][-1].content

    async def _run_churn_pipeline(self, tools: Sequence[BaseTool]) -> str:
        """
        Execute the full 5-step churn prevention pipeline:
        M1 Signal Ingestion → Enrichment → M2 Scoring → M4 Audit → M3 Alerts → M5 Summary
        """
        customer_ids = DEFAULT_CUSTOMER_IDS
        tool_list = list(tools)

        # M1 — Signal Ingestion
        signals = await ingest_signals(customer_ids, tool_list)

        # Account Enrichment
        enrichment = await enrich_accounts(list(signals.keys()), tool_list)

        # M2 — Churn Scoring
        scoring_result = await score_accounts(signals, enrichment, self.llm, CHURN_THRESHOLD)
        scored = scoring_result["scored"]
        at_risk = scoring_result["at_risk"]
        watch_list = scoring_result["watch_list"]

        # M3 + M4 — Alert Dispatch (includes audit logging per account inside dispatcher)
        dispatch_result = await dispatch_alerts(at_risk, scored, enrichment)

        # M5 — Portfolio Summary
        await send_portfolio_summary(
            scanned=len(signals),
            flagged=len(at_risk),
            alerts_sent=dispatch_result["dispatched"],
            watch_listed=len(watch_list),
        )

        # Build human-readable summary response
        return self._format_pipeline_result(signals, at_risk, watch_list, scored, dispatch_result)

    def _format_pipeline_result(
        self,
        signals: dict,
        at_risk: list,
        watch_list: list,
        scored: dict,
        dispatch_result: dict,
    ) -> str:
        lines = [
            f"✅ Churn scan complete.",
            f"- Accounts scanned: {len(signals)}",
            f"- At-risk (score ≥ {CHURN_THRESHOLD}): {len(at_risk)}",
            f"- Watch list (< {MIN_ORDER_COUNT} orders): {len(watch_list)}",
            f"- Joule alerts dispatched: {dispatch_result['dispatched']}",
        ]
        if at_risk:
            lines.append("\nAt-risk accounts:")
            for cid in at_risk:
                s = scored.get(cid, {})
                lines.append(
                    f"  • {cid} — Score: {s.get('risk_score', '?')}/100 "
                    f"({s.get('confidence', '?')}) — {', '.join(s.get('top_signals', []))}"
                )
        if watch_list:
            lines.append(f"\nWatch list: {', '.join(watch_list)}")
        return "\n".join(lines)

    async def stream(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AsyncGenerator[dict, None]:
        self._touch(context_id)
        yield {
            "is_task_complete": False,
            "require_user_input": False,
            "content": "Processing churn analysis...",
        }

        try:
            response = await self._run_agent(query, context_id, tools)
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": response,
            }
        except Exception as e:
            logger.exception("Agent stream() failed")
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": f"I encountered an error while processing your request: {str(e)}. Please try again.",
            }

    async def invoke(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AgentResponse:
        last: dict = {}
        async for chunk in self.stream(query, context_id, tools=tools):
            last = chunk
        if last.get("is_task_complete"):
            return AgentResponse(status="completed", message=last["content"])
        if last.get("require_user_input"):
            return AgentResponse(status="input_required", message=last["content"])
        return AgentResponse(status="error", message=last.get("content", "Unknown error"))
