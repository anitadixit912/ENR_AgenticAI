"""
Churn Scoring — M2
Scores each customer account on a 0-100 churn risk index using the LLM as the
scoring engine. Accounts with fewer than MIN_ORDER_COUNT orders are excluded
and placed on the watch list instead.
"""

import json
import logging
from typing import Any

from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Business constants
CHURN_THRESHOLD = 65
MIN_ORDER_COUNT = 4


def _build_scoring_prompt(signals: dict, enrichment: dict) -> str:
    """Build a structured scoring prompt for the LLM."""
    accounts_data = []
    for customer_id, sig in signals.items():
        enr = enrichment.get(customer_id, {})
        accounts_data.append({
            "account_id": customer_id,
            "order_count": sig.get("order_count", 0),
            "value_trend_pct": sig.get("value_trend_pct"),
            "return_count": sig.get("return_count", 0),
            "avg_net_amount_recent": sig.get("avg_net_amount_recent", 0),
            "avg_net_amount_prior": sig.get("avg_net_amount_prior", 0),
            "open_opportunity_count": enr.get("open_opportunity_count", 0),
            "total_opportunity_value": enr.get("total_opportunity_value", 0),
        })

    return f"""You are a customer churn risk analyst. For each account below, output a JSON array where each element has:
- "account_id": the account identifier
- "risk_score": integer 0-100 (100 = highest churn risk)
- "confidence": "High", "Medium", or "Low"
- "top_signals": array of up to 3 strings describing the main risk signals

Scoring guidance:
- A declining value trend (negative value_trend_pct) increases risk
- A high return_count relative to order_count increases risk
- Zero or very low recent order count increases risk
- Open opportunities reduce risk slightly

Accounts data:
{json.dumps(accounts_data, indent=2)}

Respond ONLY with a valid JSON array. No explanation outside the JSON.
"""


@tracer.start_as_current_span("churn_scoring")
async def score_accounts(
    signals: dict[str, Any],
    enrichment: dict[str, Any],
    llm,
    threshold: int = CHURN_THRESHOLD,
) -> dict[str, Any]:
    """
    Score each account and classify as at_risk, watch_list, or safe.

    Returns:
      {
        "scored":     {customer_id: {risk_score, confidence, top_signals}},
        "at_risk":    [customer_ids with risk_score >= threshold],
        "watch_list": [customer_ids excluded due to insufficient history],
      }
    """
    from langchain_core.messages import HumanMessage

    watch_list: list[str] = []
    eligible: dict[str, Any] = {}

    # Separate eligible accounts from watch-list candidates
    for customer_id, sig in signals.items():
        if sig.get("order_count", 0) < MIN_ORDER_COUNT:
            watch_list.append(customer_id)
            logger.info(
                "Customer %s added to watch list (order_count=%d < %d)",
                customer_id, sig.get("order_count", 0), MIN_ORDER_COUNT
            )
        else:
            eligible[customer_id] = sig

    scored: dict[str, Any] = {}
    failed_ids: list[str] = []

    if eligible:
        try:
            prompt = _build_scoring_prompt(eligible, enrichment)
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            raw_content = response.content if hasattr(response, "content") else str(response)

            # Parse JSON from response
            score_list = json.loads(raw_content)
            for item in score_list:
                cid = item.get("account_id")
                if cid and cid in eligible:
                    scored[cid] = {
                        "risk_score": int(item.get("risk_score", 0)),
                        "confidence": item.get("confidence", "Low"),
                        "top_signals": item.get("top_signals", []),
                    }

        except json.JSONDecodeError as exc:
            logger.error("M2.missed: scoring incomplete — JSON parse error: %s", exc)
            failed_ids = list(eligible.keys())
        except Exception as exc:
            logger.error(
                "M2.missed: scoring incomplete — %s — affected accounts: %s",
                exc, list(eligible.keys())
            )
            failed_ids = list(eligible.keys())

    at_risk = [cid for cid, s in scored.items() if s["risk_score"] >= threshold]

    logger.info(
        "M2.achieved: scoring complete — %d scored, %d flagged >=%d, %d watch-listed",
        len(scored), len(at_risk), threshold, len(watch_list),
    )

    return {
        "scored": scored,
        "at_risk": at_risk,
        "watch_list": watch_list,
        "failed": failed_ids,
    }
