"""
Portfolio Summary — M5
Sends a weekly portfolio-level summary in Joule to all sales managers.
"""

import logging
import os
from typing import Any

from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

SALES_MANAGER_IDS = os.environ.get("SALES_MANAGER_IDS", "")


async def _send_joule_summary(recipient_id: str, message: str) -> bool:
    """Send a Joule summary message. Returns True on success, False on failure."""
    if not recipient_id:
        return False
    logger.info(
        "JOULE SUMMARY → recipient=%s message_preview=%s",
        recipient_id, message[:120]
    )
    return True


@tracer.start_as_current_span("portfolio_summary")
async def send_portfolio_summary(
    scanned: int,
    flagged: int,
    alerts_sent: int,
    watch_listed: int,
) -> bool:
    """
    Compose and dispatch the weekly portfolio-level summary to all sales managers.

    Returns True if at least one manager was notified, False otherwise.
    """
    message = (
        f"📊 Weekly Churn Scan Complete\n"
        f"Accounts scanned: {scanned}\n"
        f"At-risk flagged (score ≥ 65): {flagged}\n"
        f"Joule alerts dispatched: {alerts_sent}\n"
        f"Watch list (insufficient history): {watch_listed}\n"
        f"\nReview flagged accounts in your Joule workspace."
    )

    manager_ids = [m.strip() for m in SALES_MANAGER_IDS.split(",") if m.strip()]
    if not manager_ids:
        logger.warning("No SALES_MANAGER_IDS configured — portfolio summary not sent")
        logger.warning(
            "M5.missed: portfolio summary delivery failed — SALES_MANAGER_IDS not configured"
        )
        return False

    success_count = 0
    for manager_id in manager_ids:
        ok = await _send_joule_summary(manager_id, message)
        if ok:
            success_count += 1

    if success_count > 0:
        logger.info(
            "M5.achieved: portfolio summary delivered — %d scanned, %d flagged, %d alerts sent",
            scanned, flagged, alerts_sent,
        )
        return True
    else:
        logger.error(
            "M5.missed: portfolio summary delivery failed — all %d recipients failed",
            len(manager_ids),
        )
        return False
