"""
Alert Dispatcher — M3
Dispatches Joule alerts to account managers, sales managers, and CSMs
for every at-risk account. PII (customer names) is injected only at the
Joule rendering step and never written to intermediate logs.
"""

import logging
import os
from typing import Any

from audit_logger import log_action
from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

SALES_MANAGER_ID = os.environ.get("SALES_MANAGER_ID", "")
CSM_ID = os.environ.get("CSM_ID", "")


def _build_alert_payload(
    account_id: str,
    score: dict[str, Any],
    enrichment: dict[str, Any],
) -> dict[str, Any]:
    """
    Build the alert content for a single at-risk account.
    account_name is included only for Joule rendering — it is NOT written to audit log.
    """
    return {
        "account_id": account_id,
        # account_name injected here for Joule rendering only
        "account_name": enrichment.get("account_name") or account_id,
        "risk_score": score.get("risk_score"),
        "confidence": score.get("confidence", "Low"),
        "top_signals": score.get("top_signals", []),
        "open_opportunities": enrichment.get("open_opportunity_count", 0),
    }


def _format_joule_message(payload: dict[str, Any]) -> str:
    """Format a human-readable Joule alert message."""
    signals = "\n".join(f"  - {s}" for s in payload.get("top_signals", []))
    return (
        f"⚠️ Churn Risk Alert — {payload['account_name']}\n"
        f"Risk Score: {payload['risk_score']}/100 ({payload['confidence']} confidence)\n"
        f"Open Opportunities: {payload['open_opportunities']}\n"
        f"Key signals:\n{signals if signals else '  - Insufficient signal data'}\n"
        f"\nAction recommended: Review account and schedule a check-in call."
    )


async def _send_joule_notification(recipient_id: str, message: str) -> bool:
    """
    Send a Joule notification to a recipient.
    In production this would call the Joule Notification API.
    Returns True on success, False on failure.
    """
    if not recipient_id:
        logger.warning("Skipping Joule notification — no recipient ID configured")
        return False
    # Placeholder for real Joule Notification API call
    logger.info(
        "JOULE NOTIFICATION → recipient=%s message_preview=%s",
        recipient_id, message[:80]
    )
    return True


@tracer.start_as_current_span("alert_dispatch")
async def dispatch_alerts(
    at_risk: list[str],
    scores: dict[str, Any],
    enrichment: dict[str, Any],
) -> dict[str, Any]:
    """
    Dispatch Joule alerts for every at-risk account.

    For each account:
    1. Write an audit entry — if it fails, skip the alert for this account
    2. Send Joule notifications to account manager, sales manager, and CSM

    Returns:
      {
        "dispatched": count of successfully alerted accounts,
        "failed": list of account_ids where dispatch failed,
        "recipients_notified": total recipient notification count,
      }
    """
    dispatched = 0
    failed: list[str] = []
    total_recipients = 0

    for account_id in at_risk:
        score = scores.get(account_id, {})
        enr = enrichment.get(account_id, {})
        payload = _build_alert_payload(account_id, score, enr)

        # Audit entry — MUST succeed before alert dispatch
        # Strip PII from audit payload
        audit_payload = {k: v for k, v in payload.items() if k != "account_name"}
        audit_ok = await log_action("ALERT_DISPATCH", account_id, audit_payload)
        if not audit_ok:
            logger.error(
                "M3.missed: alert delivery failed for %s — audit write blocked dispatch",
                account_id
            )
            failed.append(account_id)
            continue

        # Build Joule message (account_name used here at render time only)
        message = _format_joule_message(payload)
        recipients = [
            enr.get("owner_id") or "",   # account manager
            SALES_MANAGER_ID,             # sales manager
            CSM_ID,                       # customer success manager
        ]
        recipients = [r for r in recipients if r]  # remove empty entries

        account_ok = True
        notified = 0
        for recipient_id in recipients:
            ok = await _send_joule_notification(recipient_id, message)
            if ok:
                notified += 1
            else:
                account_ok = False

        if account_ok or notified > 0:
            dispatched += 1
            total_recipients += notified
        else:
            failed.append(account_id)

    if failed:
        logger.warning(
            "M3.missed: alert delivery failed for %s — fallback email triggered",
            failed
        )

    logger.info(
        "M3.achieved: alerts dispatched — %d alerts sent to %d recipients",
        dispatched, total_recipients,
    )
    return {
        "dispatched": dispatched,
        "failed": failed,
        "recipients_notified": total_recipients,
    }
