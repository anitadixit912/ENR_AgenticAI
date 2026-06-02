"""CAP persistence tool â stores risk events in HANA Cloud via OData."""
import logging
import os
import json
import uuid
import urllib.request
from datetime import datetime, timezone
from langchain.tools import tool

logger = logging.getLogger(__name__)


@tool
def persist_risk_event(
    event_data: dict,
    risk_score: dict,
    affected_suppliers: list,
    affected_pos: list,
    task_ids: list
) -> dict:
    """Persist a scored risk event to the CAP OData service (HANA Cloud).

    Args:
        event_data: Raw event dict from GDELT/NewsAPI
        risk_score: Score dict from score_risk tool (includes recommendations list)
        affected_suppliers: List of affected supplier dicts
        affected_pos: List of affected PO dicts
        task_ids: List of SAP task IDs created for this event

    Returns:
        Dict with persisted_id, status
    """
    cap_url = os.environ.get("CAP_SERVICE_URL", "http://localhost:4004")
    endpoint = f"{cap_url}/risk/RiskEvents"

    total_po_value = sum(po.get("net_value", 0) for po in affected_pos)
    event_id = str(uuid.uuid4())

    # Serialise recommendations list to JSON string for storage
    recommendations = risk_score.get("recommendations", [])
    recommendations_json = json.dumps(recommendations) if recommendations else "[]"

    payload = {
        "ID": event_id,
        "eventId": event_data.get("event_id", ""),
        "eventDate": event_data.get("date", datetime.now(timezone.utc).isoformat()),
        "headline": event_data.get("headline", "")[:500],
        "sourceUrl": event_data.get("url", "")[:2000],
        "region": event_data.get("source_country", ""),
        "country": event_data.get("source_country", ""),
        "severity": risk_score.get("severity", "Low"),
        "scoreNumeric": risk_score.get("score_numeric", 1),
        "justification": risk_score.get("justification", "")[:1000],
        "recommendations": recommendations_json,
        "affectedSupplierCount": risk_score.get("affected_supplier_count", 0),
        "affectedPoCount": risk_score.get("affected_po_count", 0),
        "totalPoValue": total_po_value,
        "currency": "USD",
        "sapTaskIds": ",".join(str(t) for t in task_ids if t),
        "agentRunId": os.environ.get("AGENT_RUN_ID", str(uuid.uuid4())),
        "createdAt": datetime.now(timezone.utc).isoformat()
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=data,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            response_body = json.loads(resp.read().decode("utf-8"))
            persisted_id = response_body.get("ID", event_id)

        logger.info("M6.achieved: risk event persisted â ID=%s severity=%s", persisted_id, payload["severity"])
        return {"persisted_id": persisted_id, "status": "PERSISTED"}

    except Exception as e:
        logger.error("M6.missed: dashboard persistence failed â CAP write error: %s", str(e))
        return {"persisted_id": event_id, "status": "FAILED", "error": str(e)}
