"""Supplier risk profile update tool via MCP."""
import logging
from datetime import datetime, timezone
from langchain.tools import tool
from mcp_tools import get_mcp_tools

logger = logging.getLogger(__name__)

SEVERITY_TO_SCORE = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}

_mcp_tools_cache = None


async def _get_mcp():
    global _mcp_tools_cache
    if _mcp_tools_cache is None:
        _mcp_tools_cache = await get_mcp_tools()
    return _mcp_tools_cache


def _find_tool(tools, name_fragment):
    for t in tools:
        if name_fragment.lower() in t.name.lower():
            return t
    return None


@tool
def update_supplier_risk_score(
    supplier_id: str,
    severity: str,
    event_ref: str,
    justification: str
) -> dict:
    """Update the risk profile for a SAP supplier based on a geopolitical event.
    
    Only updates for High or Critical severity events.
    
    Args:
        supplier_id: SAP supplier ID
        severity: Risk severity (Low/Medium/High/Critical)
        event_ref: Event identifier for audit trail
        justification: AI-generated justification for the score
    
    Returns:
        Dict with supplier_id, updated_score, previous_score, timestamp
    """
    if severity not in ("High", "Critical"):
        return {"supplier_id": supplier_id, "status": "SKIPPED", "reason": f"Severity {severity} below threshold"}

    import asyncio

    async def _run():
        try:
            tools = await _get_mcp()
            risk_tool = _find_tool(tools, "SupplierRisk") or _find_tool(tools, "supplier_risk") or _find_tool(tools, "RiskEngagement")
            if not risk_tool:
                logger.warning("Supplier Risk MCP tool not found for supplier %s", supplier_id)
                return {"supplier_id": supplier_id, "status": "TOOL_NOT_FOUND", "updated_score": None}

            score = SEVERITY_TO_SCORE.get(severity, 1)
            payload = {
                "Supplier": supplier_id,
                "RiskScore": score,
                "RiskCategory": "GEOPOLITICAL",
                "RiskDescription": justification[:500],
                "EventReference": event_ref[:100],
                "AssessmentDate": datetime.now(timezone.utc).strftime("%Y-%m-%d")
            }
            result = await risk_tool.arun(payload)
            prev_score = result.get("PreviousRiskScore", None)

            logger.info("Supplier risk updated: %s â score=%d (was %s)", supplier_id, score, prev_score)
            return {
                "supplier_id": supplier_id,
                "updated_score": score,
                "previous_score": prev_score,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "UPDATED"
            }

        except Exception as e:
            logger.error("Supplier risk update failed for %s â %s", supplier_id, str(e))
            return {"supplier_id": supplier_id, "status": "FAILED", "error": str(e)}

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, _run()).result(timeout=30)
        return loop.run_until_complete(_run())
    except Exception as e:
        logger.error("Supplier risk tool error â %s", str(e))
        return {"supplier_id": supplier_id, "status": "ERROR"}
