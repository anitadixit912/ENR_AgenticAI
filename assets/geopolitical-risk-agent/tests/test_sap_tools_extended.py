"""Extended unit tests for SAP task and supplier risk update tools.

Strategy: pre-seed `_mcp_tools_cache` with mock tools so `_get_mcp()` returns them
directly without re-fetching — avoids async-chain complexity in unit tests.
"""
import asyncio
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def event_loop_setup():
    """Ensure a current event loop is set for each test (Python 3.12+ compatibility)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()
    asyncio.set_event_loop(None)


# ── create_sap_procurement_task ───────────────────────────────────────────────


def test_create_task_skipped_for_low_severity():
    from tools.sap_task_tool import create_sap_procurement_task
    result = create_sap_procurement_task.invoke({
        "supplier_id": "SUP001", "supplier_name": "ACME Corp",
        "po_numbers": ["4500001"], "event_summary": "Minor unrest",
        "severity": "Low", "event_date": "2024-01-15",
    })
    assert result["status"] == "SKIPPED"
    assert result["task_id"] is None


def test_create_task_skipped_for_medium_severity():
    from tools.sap_task_tool import create_sap_procurement_task
    result = create_sap_procurement_task.invoke({
        "supplier_id": "SUP002", "supplier_name": "Corp B",
        "po_numbers": ["4500002"], "event_summary": "Protests reported",
        "severity": "Medium", "event_date": "2024-01-15",
    })
    assert result["status"] == "SKIPPED"


def test_create_task_high_severity_success():
    mock_tool = MagicMock()
    mock_tool.name = "SupplierActivityTask_post"
    mock_tool.arun = AsyncMock(return_value={"SupplierActivityTask": "TASK-999"})

    with patch("tools.sap_task_tool._mcp_tools_cache", [mock_tool]):
        from tools.sap_task_tool import create_sap_procurement_task
        result = create_sap_procurement_task.invoke({
            "supplier_id": "SUP001", "supplier_name": "ACME Corp",
            "po_numbers": ["4500001", "4500002"],
            "event_summary": "Military conflict near supplier facility",
            "severity": "High", "event_date": "2024-01-15",
        })

    assert result["status"] == "CREATED"
    assert result["task_id"] == "TASK-999"
    assert result["supplier_id"] == "SUP001"


def test_create_task_critical_severity_uses_priority_1():
    mock_tool = MagicMock()
    mock_tool.name = "SupplierActivityTask"
    mock_tool.arun = AsyncMock(return_value={"task_id": "TASK-CRIT-001"})

    with patch("tools.sap_task_tool._mcp_tools_cache", [mock_tool]):
        from tools.sap_task_tool import create_sap_procurement_task
        result = create_sap_procurement_task.invoke({
            "supplier_id": "SUP003", "supplier_name": "DniproChemicals",
            "po_numbers": ["4500003"], "event_summary": "Active war zone",
            "severity": "Critical", "event_date": "2024-03-10",
        })

    assert result["status"] == "CREATED"


def test_create_task_no_mcp_tool_found():
    mock_tool = MagicMock()
    mock_tool.name = "UnrelatedTool"
    mock_tool.arun = AsyncMock(return_value={})

    with patch("tools.sap_task_tool._mcp_tools_cache", [mock_tool]):
        from tools.sap_task_tool import create_sap_procurement_task
        result = create_sap_procurement_task.invoke({
            "supplier_id": "SUP001", "supplier_name": "ACME Corp",
            "po_numbers": [], "event_summary": "Conflict event",
            "severity": "High", "event_date": "2024-01-15",
        })

    assert result["status"] == "TOOL_NOT_FOUND"
    assert result["task_id"] is None


def test_create_task_mcp_exception():
    mock_tool = MagicMock()
    mock_tool.name = "SupplierActivityTask"
    mock_tool.arun = AsyncMock(side_effect=Exception("API error"))

    with patch("tools.sap_task_tool._mcp_tools_cache", [mock_tool]):
        from tools.sap_task_tool import create_sap_procurement_task
        result = create_sap_procurement_task.invoke({
            "supplier_id": "SUP001", "supplier_name": "ACME Corp",
            "po_numbers": ["4500001"], "event_summary": "Conflict",
            "severity": "High", "event_date": "2024-01-15",
        })

    assert result["status"] == "FAILED"


# ── update_supplier_risk_score ────────────────────────────────────────────────


def test_update_risk_score_skipped_for_low():
    from tools.supplier_risk_tool import update_supplier_risk_score
    result = update_supplier_risk_score.invoke({
        "supplier_id": "SUP001", "severity": "Low",
        "event_ref": "EVT-001", "justification": "Minor event",
    })
    assert result["status"] == "SKIPPED"


def test_update_risk_score_skipped_for_medium():
    from tools.supplier_risk_tool import update_supplier_risk_score
    result = update_supplier_risk_score.invoke({
        "supplier_id": "SUP002", "severity": "Medium",
        "event_ref": "EVT-002", "justification": "Moderate impact",
    })
    assert result["status"] == "SKIPPED"


def test_update_risk_score_high_success():
    mock_tool = MagicMock()
    mock_tool.name = "SupplierRisk_post"
    mock_tool.arun = AsyncMock(return_value={"PreviousRiskScore": 2})

    with patch("tools.supplier_risk_tool._mcp_tools_cache", [mock_tool]):
        from tools.supplier_risk_tool import update_supplier_risk_score
        result = update_supplier_risk_score.invoke({
            "supplier_id": "SUP001", "severity": "High",
            "event_ref": "EVT-003", "justification": "Active conflict near supplier.",
        })

    assert result["status"] == "UPDATED"
    assert result["updated_score"] == 3
    assert result["previous_score"] == 2
    assert result["supplier_id"] == "SUP001"


def test_update_risk_score_critical_maps_to_4():
    mock_tool = MagicMock()
    mock_tool.name = "RiskEngagement"
    mock_tool.arun = AsyncMock(return_value={})

    with patch("tools.supplier_risk_tool._mcp_tools_cache", [mock_tool]):
        from tools.supplier_risk_tool import update_supplier_risk_score
        result = update_supplier_risk_score.invoke({
            "supplier_id": "SUP004", "severity": "Critical",
            "event_ref": "EVT-CRIT", "justification": "War zone",
        })

    assert result["updated_score"] == 4


def test_update_risk_score_no_mcp_tool():
    mock_tool = MagicMock()
    mock_tool.name = "UnrelatedTool"
    mock_tool.arun = AsyncMock(return_value={})

    with patch("tools.supplier_risk_tool._mcp_tools_cache", [mock_tool]):
        from tools.supplier_risk_tool import update_supplier_risk_score
        result = update_supplier_risk_score.invoke({
            "supplier_id": "SUP001", "severity": "High",
            "event_ref": "EVT-001", "justification": "Test",
        })

    assert result["status"] == "TOOL_NOT_FOUND"


def test_update_risk_score_mcp_exception():
    mock_tool = MagicMock()
    mock_tool.name = "SupplierRisk"
    mock_tool.arun = AsyncMock(side_effect=Exception("Service unavailable"))

    with patch("tools.supplier_risk_tool._mcp_tools_cache", [mock_tool]):
        from tools.supplier_risk_tool import update_supplier_risk_score
        result = update_supplier_risk_score.invoke({
            "supplier_id": "SUP001", "severity": "Critical",
            "event_ref": "EVT-X", "justification": "Exception test",
        })

    assert result["status"] == "FAILED"
