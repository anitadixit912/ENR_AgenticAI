"""
Signal Ingestion — M1
Fetches 12-week rolling sales order and return/complaint signals per customer from S/4HANA
via the Sales Order MCP server tools. All API calls go through MCP tools only.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

# Business constants
SIGNAL_WINDOW_WEEKS = 12
PAGE_SIZE = 100
RECENT_WEEKS = 4  # weeks for "recent" trend comparison
PRIOR_WEEKS = 8   # weeks for "prior" trend comparison


def _weeks_ago_iso(weeks: int) -> str:
    """Return an OData-compatible datetime string N weeks ago."""
    dt = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    return dt.strftime("datetime'%Y-%m-%dT%H:%M:%S'")


def _find_tool(tools: list, name_fragment: str):
    """Find the first tool whose name contains name_fragment (case-insensitive)."""
    for t in tools:
        if name_fragment.lower() in t.name.lower():
            return t
    return None


@tracer.start_as_current_span("signal_ingestion")
async def ingest_signals(customer_ids: list[str], tools: list) -> dict[str, Any]:
    """
    Ingest 12-week rolling order and complaint/return signals for each customer.

    Returns a dict keyed by customer_id with:
      - order_count: total orders in the 12-week window
      - avg_net_amount_recent: average net amount in the most recent 4 weeks
      - avg_net_amount_prior: average net amount in weeks 5-12
      - value_trend_pct: % change in avg order value (recent vs prior, None if no prior data)
      - return_count: number of order items with a rejection/return reason code
      - orders_raw: list of raw order dicts from S/4HANA
    """
    list_order_tool = _find_tool(tools, "list_salesorder")
    list_item_tool = _find_tool(tools, "list_salesorderitem")

    if not list_order_tool or not list_item_tool:
        msg = "Required MCP tools not found: list_salesorder or list_salesorderitem"
        logger.error("M1.missed: signal ingestion failed — %s — cycle aborted", msg)
        raise RuntimeError(msg)

    window_start = _weeks_ago_iso(SIGNAL_WINDOW_WEEKS)
    recent_start = _weeks_ago_iso(RECENT_WEEKS)
    results: dict[str, Any] = {}
    failed_ids: list[str] = []

    for customer_id in customer_ids:
        try:
            # Fetch orders for this customer in the 12-week window
            order_filter = (
                f"SoldToParty eq '{customer_id}' and "
                f"CreationDate ge {window_start}"
            )
            orders_resp = await list_order_tool.arun({
                "filter": order_filter,
                "select": (
                    "SalesOrder,SoldToParty,CreationDate,TotalNetAmount,"
                    "TransactionCurrency,OverallSDProcessStatus,SDDocumentReason"
                ),
                "top": PAGE_SIZE,
                "orderby": "CreationDate desc",
            })

            orders: list[dict] = []
            if isinstance(orders_resp, dict):
                orders = orders_resp.get("value", [])
            elif isinstance(orders_resp, list):
                orders = orders_resp

            # Fetch order items to detect return/rejection reason codes
            return_count = 0
            for order in orders:
                order_id = order.get("SalesOrder", "")
                if not order_id:
                    continue
                items_resp = await list_item_tool.arun({
                    "filter": f"SalesOrder eq '{order_id}'",
                    "select": "SalesOrder,SalesOrderItem,SalesDocumentRjcnReason",
                    "top": PAGE_SIZE,
                })
                items: list[dict] = []
                if isinstance(items_resp, dict):
                    items = items_resp.get("value", [])
                elif isinstance(items_resp, list):
                    items = items_resp
                return_count += sum(
                    1 for item in items
                    if item.get("SalesDocumentRjcnReason")
                )

            # Compute order value trends
            recent_amounts = []
            prior_amounts = []
            for order in orders:
                try:
                    net = float(order.get("TotalNetAmount") or 0)
                    creation = order.get("CreationDate", "")
                    if creation >= recent_start:
                        recent_amounts.append(net)
                    else:
                        prior_amounts.append(net)
                except (ValueError, TypeError):
                    pass

            avg_recent = sum(recent_amounts) / len(recent_amounts) if recent_amounts else 0.0
            avg_prior = sum(prior_amounts) / len(prior_amounts) if prior_amounts else 0.0
            value_trend_pct = (
                ((avg_recent - avg_prior) / avg_prior * 100) if avg_prior > 0 else None
            )

            results[customer_id] = {
                "order_count": len(orders),
                "avg_net_amount_recent": round(avg_recent, 2),
                "avg_net_amount_prior": round(avg_prior, 2),
                "value_trend_pct": round(value_trend_pct, 1) if value_trend_pct is not None else None,
                "return_count": return_count,
                "orders_raw": orders,
            }

        except Exception as exc:
            logger.warning("Signal ingestion failed for customer %s: %s", customer_id, exc)
            failed_ids.append(customer_id)

    if failed_ids and not results:
        msg = f"all {len(failed_ids)} customer(s) failed signal ingestion"
        logger.error("M1.missed: signal ingestion failed — %s — cycle aborted", msg)
        raise RuntimeError(msg)

    logger.info(
        "M1.achieved: signal ingestion complete — %d accounts retrieved",
        len(results),
    )
    return results
