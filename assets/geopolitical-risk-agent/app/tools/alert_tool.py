"""Email alert notification tool — BTP Alert Notification Service (primary) + SMTP (fallback)."""
import logging
import os
import json
import uuid
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from langchain.tools import tool

logger = logging.getLogger(__name__)


def _get_ans_oauth_token(token_url: str, client_id: str, client_secret: str) -> str:
    """Fetch an OAuth 2.0 client-credentials token from the ANS UAA endpoint."""
    data = urllib.parse.urlencode({
        "grant_type":    "client_credentials",
        "client_id":     client_id,
        "client_secret": client_secret,
    }).encode("utf-8")
    req = urllib.request.Request(
        token_url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        token_data = json.loads(resp.read().decode("utf-8"))
    access_token = token_data.get("access_token")
    if not access_token:
        raise ValueError(f"No access_token in ANS OAuth response: {token_data}")
    return access_token


def _post_ans_event(ans_url: str, token: str, event_payload: dict) -> str:
    """POST a resource event to BTP Alert Notification Service. Returns message ID."""
    events_url = ans_url.rstrip("/") + "/cf/producer/v1/resource-events"
    data = json.dumps(event_payload).encode("utf-8")
    req = urllib.request.Request(
        events_url,
        data=data,
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode("utf-8")
        # ANS returns 202 Accepted with an event ID in the body
        try:
            return json.loads(body).get("id", f"ans_{resp.status}")
        except Exception:
            return f"ans_{resp.status}"


@tool
def send_alert_email(
    recipients: list,
    event_title: str,
    severity: str,
    affected_suppliers: list,
    affected_po_count: int,
    total_po_value: float,
    dashboard_url: str,
    recommendations: list = None,
) -> dict:
    """Send alert to procurement managers for High/Critical risk events via BTP ANS or SMTP.

    Only sends for High or Critical severity events.

    Args:
        recipients: List of email addresses
        event_title: Short event headline
        severity: Risk severity (Low/Medium/High/Critical)
        affected_suppliers: List of affected supplier dicts
        affected_po_count: Number of open POs affected
        total_po_value: Total value of affected POs
        dashboard_url: URL to the risk dashboard
        recommendations: Optional list of AI-generated mitigation action strings

    Returns:
        Dict with sent (bool), recipient_count, message_id
    """
    if severity not in ("High", "Critical"):
        return {
            "sent": False, "recipient_count": 0, "message_id": None,
            "reason": f"Severity {severity} below alert threshold",
        }

    if not recipients:
        return {
            "sent": False, "recipient_count": 0, "message_id": None,
            "reason": "No recipients provided",
        }

    # ── Plain-language content ────────────────────────────────────────────────
    urgency_label = {
        "Critical": "Urgent — Immediate Action Required",
        "High":     "Important — Please Review Today",
    }.get(severity, "Heads Up — Please Review")

    urgency_intro = {
        "Critical": (
            "Our monitoring system has detected a serious situation that is very likely "
            "to disrupt your supply chain. Please review this immediately and take action."
        ),
        "High": (
            "Our monitoring system has flagged a significant event in a region where some "
            "of your suppliers are located. We recommend reviewing this today."
        ),
    }.get(severity, "")

    supplier_lines = "\n".join(
        f"  • {s.get('name', s.get('supplier_id', 'Unknown'))} — based in {s.get('country', 'unknown location')}"
        for s in affected_suppliers[:10]
    )
    more_suppliers = (
        f"\n  … and {len(affected_suppliers) - 10} more supplier(s). See the dashboard for the full list."
        if len(affected_suppliers) > 10 else ""
    )

    action_steps = {
        "Critical": (
            "1. Log in to SAP and check if any of the listed suppliers have open orders.\n"
            "2. Contact your procurement team lead to discuss alternative sourcing options.\n"
            "3. Consider placing the affected purchase orders on hold until the situation is clearer.\n"
            "4. Check the dashboard for the latest updates and AI-generated risk assessment."
        ),
        "High": (
            "1. Review the affected suppliers and their open orders listed below.\n"
            "2. Keep an eye on the situation — it may escalate over the next 24–48 hours.\n"
            "3. Speak with your supplier relationship manager if you have active deliveries pending.\n"
            "4. Check the dashboard for more details and recommended next steps."
        ),
    }.get(severity, "Please log in to the dashboard to review the details.")

    if total_po_value >= 1_000_000:
        value_str = f"${total_po_value / 1_000_000:.1f} million"
    elif total_po_value >= 1_000:
        value_str = f"${total_po_value / 1_000:,.0f}k"
    else:
        value_str = f"${total_po_value:,.0f}"

    detected_at = datetime.now(timezone.utc).strftime("%B %d, %Y at %H:%M UTC")

    # Build AI recommendations block when available
    rec_list = recommendations or []
    if rec_list:
        rec_lines = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(rec_list[:7]))
        recommendations_section = (
            "\n\nAI-GENERATED MITIGATION RECOMMENDATIONS\n"
            "----------------------------------------\n"
            "Based on the event details and your affected supplier portfolio,\n"
            "the AI risk engine proposes the following actions:\n\n"
            f"{rec_lines}\n\n"
            "These recommendations should be reviewed by your procurement team\n"
            "before acting. See the dashboard for full context."
        )
    else:
        recommendations_section = ""

    body = f"""Hello,

{urgency_intro}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ⚠  {urgency_label.upper()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WHAT HAPPENED
─────────────
{event_title}

Risk level:  {severity}
Detected on: {detected_at}


WHO IS AFFECTED
───────────────
{len(affected_suppliers)} of your supplier(s) are located in the impacted area:

{supplier_lines}{more_suppliers}

Active orders at risk:  {affected_po_count} purchase order(s)
Estimated order value:  {value_str}


WHAT YOU SHOULD DO
──────────────────
{action_steps}{recommendations_section}


VIEW FULL DETAILS
─────────────────
See the complete risk report, affected supplier list, and recommended actions here:
👉  {dashboard_url}


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This alert was generated automatically by your Geopolitical Risk Monitor,
which watches global news and conflict signals 24/7 on your behalf.

If you believe this alert was sent in error or have questions,
please contact your procurement team.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    subject = {
        "Critical": f"🚨 Urgent Supply Chain Risk — {event_title[:70]}",
        "High":     f"⚠️  Supply Chain Alert — {event_title[:70]}",
    }.get(severity, f"[{severity}] Supply Chain Notice — {event_title[:70]}")

    # ANS severity mapping: Critical → CRITICAL, High → MAJOR
    ans_severity_map = {"Critical": "CRITICAL", "High": "MAJOR"}

    # ── Option A: BTP Alert Notification Service (OAuth 2.0) ─────────────────
    ans_url        = os.environ.get("BTP_ANS_URL", "")
    ans_token_url  = os.environ.get("BTP_ANS_TOKEN_URL", "")
    ans_client_id  = os.environ.get("BTP_ANS_CLIENT_ID", "")
    ans_client_secret = os.environ.get("BTP_ANS_CLIENT_SECRET", "")

    if ans_url and ans_token_url and ans_client_id and ans_client_secret:
        try:
            token = _get_ans_oauth_token(ans_token_url, ans_client_id, ans_client_secret)

            # Build one ANS resource event per recipient (ANS routes to email via subscriptions)
            event_id = str(uuid.uuid4())
            ans_event = {
                "eventType":  "GeopoliticalRiskAlert",
                "severity":   ans_severity_map.get(severity, "MAJOR"),
                "category":   "ALERT",
                "subject":    subject,
                "body":       body,
                "priority":   1 if severity == "Critical" else 2,
                "tags": {
                    "ans:ims:sourceEventId": event_id,
                    "recipients":            ",".join(recipients),
                    "riskLevel":             severity,
                },
                "resource": {
                    "resourceName":     "GeopoliticalRiskMonitor",
                    "resourceType":     "application",
                    "resourceInstance": "georisk-agent",
                    "tags":             {},
                    "metadata":         {
                        "affectedSuppliers": str(len(affected_suppliers)),
                        "affectedPOs":       str(affected_po_count),
                        "totalPOValue":      value_str,
                    },
                },
            }

            msg_id = _post_ans_event(ans_url, token, ans_event)
            logger.info(
                "M3.achieved: alert dispatched via BTP ANS — %d recipients, event_id=%s",
                len(recipients), msg_id,
            )
            return {"sent": True, "recipient_count": len(recipients), "message_id": msg_id}

        except Exception as e:
            logger.warning("BTP ANS dispatch failed — falling back to SMTP: %s", str(e))

    # ── Option B: SMTP fallback ───────────────────────────────────────────────
    smtp_host = os.environ.get("SMTP_HOST", "")
    if smtp_host:
        try:
            import smtplib
            from email.mime.text import MIMEText
            smtp_port = int(os.environ.get("SMTP_PORT", "587"))
            smtp_user = os.environ.get("SMTP_USER", "")
            smtp_pass = os.environ.get("SMTP_PASS", "")
            msg_obj          = MIMEText(body)
            msg_obj["Subject"] = subject
            msg_obj["From"]    = smtp_user or "risk-agent@sap.com"
            msg_obj["To"]      = ", ".join(recipients)
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                if smtp_user and smtp_pass:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                server.sendmail(msg_obj["From"], recipients, msg_obj.as_string())
            msg_id = str(uuid.uuid4())
            logger.info("M3.achieved: alert dispatched via SMTP — %d recipients", len(recipients))
            return {"sent": True, "recipient_count": len(recipients), "message_id": msg_id}
        except Exception as e:
            logger.error("SMTP alert failed — %s", str(e))

    logger.warning(
        "M3.missed: no alert service configured — "
        "set BTP_ANS_URL/BTP_ANS_TOKEN_URL/BTP_ANS_CLIENT_ID/BTP_ANS_CLIENT_SECRET "
        "or SMTP_HOST in .env"
    )
    return {"sent": False, "recipient_count": 0, "message_id": None, "reason": "No alert service configured"}
