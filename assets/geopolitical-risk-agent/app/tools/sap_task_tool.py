"""SAP procurement task creation tool via MCP."""
import logging
from datetime import datetime, timezone
from langchain.tools import tool
from mcp_tools import get_mcp_tools

logger = logging.getLogger(__name__)

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
def create_sap_procurement_task(
    supplier_id: str,
    supplier_name: str,
    po_numbers: list,
    event_summary: str,
    severity: str,
    event_date: str
) -> dict:
    """Create a procurement review task in SAP S/4HANA for a high-risk geopolitical event.
    
    Only creates tasks for High or Critical severity events.
    
    Args:
        supplier_id: SAP supplier ID
        supplier_name: Supplier display name
        po_numbers: List of affected PO numbers
        event_summary: Short event description (max 200 chars)
        severity: Risk severity (Low/Medium/High/Critical)
        event_date: Event date string
    
    Returns:
        Dict with task_id, status, supplier_id
    """
    if severity not in ("High", "Critical"):
        return {"task_id": None, "status": "SKIPPED", "supplier_id": supplier_id, "reason": f"Severity {severity} below threshold"}

    import asyncio

    async def _run():
        try:
            tools = await _get_mcp()
            task_tool = _find_tool(tools, "SupplierActivityTask") or _find_tool(tools, "procurement_task") or _find_tool(tools, "Task")
            if not task_tool:
                logger.warning("Procurement Task MCP tool not found for supplier %s", supplier_id)
                return {"task_id": None, "status": "TOOL_NOT_FOUND", "supplier_id": supplier_id}

            po_list = ", ".join(po_numbers[:10])
            description = f"[{severity}] Geopolitical Risk Alert ({event_date}): {event_summary[:150]}. Affected POs: {po_list}"

            payload = {
                "Supplier": supplier_id,
                "TaskType": "RISK_REVIEW",
                "Description": description[:500],
                "DueDate": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "Priority": "1" if severity == "Critical" else "2",
                "Status": "OPEN"
            }
            result = await task_tool.arun(payload)
            task_id = result.get("SupplierActivityTask", result.get("task_id", "CREATED"))

            logger.info("SAP task created for supplier %s (severity=%s): %s", supplier_id, severity, task_id)
            return {"task_id": str(task_id), "status": "CREATED", "supplier_id": supplier_id}

        except Exception as e:
            logger.error("SAP task creation failed for supplier %s â %s", supplier_id, str(e))
            return {"task_id": None, "status": "FAILED", "supplier_id": supplier_id, "error": str(e)}

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, _run()).result(timeout=30)
        return loop.run_until_complete(_run())
    except Exception as e:
        logger.error("SAP task tool error â %s", str(e))
        return {"task_id": None, "status": "ERROR", "supplier_id": supplier_id}
