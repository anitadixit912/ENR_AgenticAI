"""
Account Enrichment
Enriches customer accounts with profile and opportunity context from SAP Sales Cloud
via custom MCP translation tools (Account Service and Opportunity Service).
Falls back gracefully if Sales Cloud services are unavailable.
"""

import logging
from typing import Any

from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

PAGE_SIZE = 100


def _find_tool(tools: list, name_fragment: str):
    """Find the first tool whose name contains name_fragment (case-insensitive)."""
    for t in tools:
        if name_fragment.lower() in t.name.lower():
            return t
    return None


@tracer.start_as_current_span("account_enrichment")
async def enrich_accounts(
    customer_ids: list[str], tools: list
) -> dict[str, Any]:
    """
    Enrich accounts with profile data from Sales Cloud Account Service
    and open opportunity context from Sales Cloud Opportunity Service.

    Returns dict keyed by customer_id:
      - account_name: display name from Sales Cloud (None if unavailable)
      - segment: account segment/classification (None if unavailable)
      - owner_id: ID of the assigned account manager (None if unavailable)
      - open_opportunity_count: number of open opportunities
      - total_opportunity_value: total expected revenue from open opportunities
    """
    account_tool = _find_tool(tools, "accounts")
    opportunity_tool = _find_tool(tools, "opportunit")

    results: dict[str, Any] = {}

    for customer_id in customer_ids:
        account_name = None
        segment = None
        owner_id = None
        open_opportunity_count = 0
        total_opportunity_value = 0.0

        # Account enrichment — graceful fallback if tool unavailable
        if account_tool:
            try:
                resp = await account_tool.arun({
                    "filter": f"id eq '{customer_id}'",
                    "top": 1,
                })
                records: list[dict] = []
                if isinstance(resp, dict):
                    records = resp.get("value", []) or resp.get("data", [])
                elif isinstance(resp, list):
                    records = resp
                if records:
                    rec = records[0]
                    account_name = rec.get("displayName") or rec.get("name") or rec.get("accountName")
                    segment = rec.get("segmentCode") or rec.get("segment") or rec.get("customerClassification")
                    owner_id = rec.get("ownerID") or rec.get("ownerId") or rec.get("responsibleEmployee")
            except Exception as exc:
                logger.warning(
                    "Account enrichment unavailable for %s (Account Service): %s",
                    customer_id, exc
                )
        else:
            logger.debug("Account tool not found — skipping account enrichment for %s", customer_id)

        # Opportunity enrichment — graceful fallback if tool unavailable
        if opportunity_tool:
            try:
                resp = await opportunity_tool.arun({
                    "filter": f"accountID eq '{customer_id}'",
                    "select": "id,expectedValue,lifeCycleStatusCode",
                    "top": PAGE_SIZE,
                })
                opps: list[dict] = []
                if isinstance(resp, dict):
                    opps = resp.get("value", []) or resp.get("data", [])
                elif isinstance(resp, list):
                    opps = resp

                # Count only open opportunities (not won/lost/cancelled)
                closed_statuses = {"4", "5", "6", "Z3", "Z4"}
                for opp in opps:
                    status = str(opp.get("lifeCycleStatusCode") or opp.get("status") or "")
                    if status not in closed_statuses:
                        open_opportunity_count += 1
                        try:
                            total_opportunity_value += float(
                                opp.get("expectedValue") or opp.get("revenue") or 0
                            )
                        except (ValueError, TypeError):
                            pass
            except Exception as exc:
                logger.warning(
                    "Opportunity enrichment unavailable for %s (Opportunity Service): %s",
                    customer_id, exc
                )
        else:
            logger.debug("Opportunity tool not found — skipping opportunity enrichment for %s", customer_id)

        results[customer_id] = {
            "account_name": account_name,
            "segment": segment,
            "owner_id": owner_id,
            "open_opportunity_count": open_opportunity_count,
            "total_opportunity_value": round(total_opportunity_value, 2),
        }

    logger.info("Account enrichment complete for %d customers", len(results))
    return results
