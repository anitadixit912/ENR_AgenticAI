"""Unit tests for create_sap_procurement_task tool."""
from unittest.mock import patch, AsyncMock


def test_create_task_high_severity():
    mock_tool = AsyncMock()
    mock_tool.name = "SupplierActivityTask"
    mock_tool.arun = AsyncMock(return_value={"SupplierActivityTask": "TASK-001"})

    with patch("tools.sap_task_tool.get_mcp_tools", return_value=AsyncMock(return_value=[mock_tool])):
        with patch("tools.sap_task_tool._mcp_tools_cache", None):
            from tools.sap_task_tool import create_sap_procurement_task
            result = create_sap_procurement_task.invoke({
                "supplier_id": "SUP001",
                "supplier_name": "ACME Corp",
                "po_numbers": ["4500001"],
                "event_summary": "Military conflict in Ukraine",
                "severity": "High",
                "event_date": "2024-01-15"
            })

    assert isinstance(result, dict)


def test_create_task_skipped_for_low_severity():
    from tools.sap_task_tool import create_sap_procurement_task
    result = create_sap_procurement_task.invoke({
        "supplier_id": "SUP001",
        "supplier_name": "ACME Corp",
        "po_numbers": [],
        "event_summary": "Minor protest",
        "severity": "Low",
        "event_date": "2024-01-15"
    })
    assert result["status"] == "SKIPPED"


def test_create_task_skipped_for_medium_severity():
    from tools.sap_task_tool import create_sap_procurement_task
    result = create_sap_procurement_task.invoke({
        "supplier_id": "SUP002",
        "supplier_name": "Baltic Steel",
        "po_numbers": ["4500002"],
        "event_summary": "Trade disruption",
        "severity": "Medium",
        "event_date": "2024-01-15"
    })
    assert result["status"] == "SKIPPED"


def test_create_task_critical_severity():
    mock_tool = AsyncMock()
    mock_tool.name = "SupplierActivityTask"
    mock_tool.arun = AsyncMock(return_value={"SupplierActivityTask": "TASK-002"})

    with patch("tools.sap_task_tool.get_mcp_tools", return_value=AsyncMock(return_value=[mock_tool])):
        with patch("tools.sap_task_tool._mcp_tools_cache", None):
            from tools.sap_task_tool import create_sap_procurement_task
            result = create_sap_procurement_task.invoke({
                "supplier_id": "SUP003",
                "supplier_name": "Eastern Metals",
                "po_numbers": ["4500003", "4500004"],
                "event_summary": "Active military offensive",
                "severity": "Critical",
                "event_date": "2024-01-15"
            })

    assert isinstance(result, dict)
