"""
Audit Logger — M4
Writes GDPR-compliant audit entries to the BTP Audit Log Service.
PII rule: account_name must NEVER appear in the payload — only account_id.
If a log write fails, the caller must NOT dispatch the alert for that account.
"""

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from opentelemetry import trace

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

AUDIT_LOG_URL = os.environ.get("AUDIT_LOG_URL", "")
AUDIT_LOG_TOKEN = os.environ.get("AUDIT_LOG_TOKEN", "")


@tracer.start_as_current_span("audit_logging")
async def log_action(
    action_type: str,
    account_id: str,
    payload: dict[str, Any],
) -> bool:
    """
    Write a structured audit entry to the BTP Audit Log Service.

    The payload must NOT contain customer names or any PII — only account_id,
    numerical signals, and recipient IDs.

    Returns True on success, False on failure.
    The caller must halt alert dispatch for this account if False is returned.
    """
    # PII guard: strip any accidentally included account_name
    sanitised = {k: v for k, v in payload.items() if k not in ("account_name", "customer_name")}
    sanitised["account_id"] = account_id  # ensure account_id is always present

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action_type": action_type,
        "account_id": account_id,
        "payload": sanitised,
    }

    # In environments without Audit Log Service configured, log locally only
    if not AUDIT_LOG_URL:
        logger.info(
            "AUDIT [%s] account=%s payload=%s",
            action_type, account_id, json.dumps(sanitised)
        )
        return True

    try:
        body = json.dumps(entry).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AUDIT_LOG_TOKEN}",
        }
        req = urllib.request.Request(AUDIT_LOG_URL, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 201, 204):
                logger.debug("Audit entry written for account %s action %s", account_id, action_type)
                return True
            logger.error(
                "M4.missed: audit write failed for %s — HTTP %d", account_id, resp.status
            )
            return False

    except (urllib.error.URLError, OSError) as exc:
        logger.error(
            "M4.missed: audit write failed for %s — %s — alert dispatch halted for affected account",
            account_id, exc
        )
        return False


async def log_batch(
    action_type: str,
    account_ids: list[str],
    payloads: dict[str, dict[str, Any]],
) -> dict[str, bool]:
    """
    Write audit entries for a batch of accounts.
    Returns dict mapping account_id -> success bool.
    """
    results: dict[str, bool] = {}
    for account_id in account_ids:
        results[account_id] = await log_action(
            action_type, account_id, payloads.get(account_id, {})
        )

    successful = sum(1 for v in results.values() if v)
    failed_ids = [k for k, v in results.items() if not v]

    if failed_ids:
        logger.error(
            "M4.missed: audit write failed for %s — alert dispatch halted for affected accounts",
            failed_ids,
        )
    else:
        logger.info("M4.achieved: audit logging complete — %d entries written", successful)

    return results
