"""Unit tests for get_open_pos_by_supplier tool."""
from unittest.mock import patch, AsyncMock


def test_get_open_pos_success():
    mock_tool = AsyncMock()
    mock_tool.name = "PurchaseOrder"
    mock_tool.arun = AsyncMock(return_value={"value": [
        {"PurchaseOrder": "4500001", "Supplier": "SUP001", "Material": "RAW-001",
         "NetPriceAmount": "50000", "DocumentCurrency": "USD", "ScheduleLine": "2024-03-01", "Plant": "1000"}
    ]})

    with patch("tools.supplier_tool.get_mcp_tools", return_value=AsyncMock(return_value=[mock_tool])):
        with patch("tools.supplier_tool._mcp_tools_cache", None):
            from tools.supplier_tool import get_open_pos_by_supplier
            result = get_open_pos_by_supplier.invoke({"supplier_ids": ["SUP001"]})

    assert isinstance(result, list)


def test_get_open_pos_no_tool():
    with patch("tools.supplier_tool.get_mcp_tools", return_value=AsyncMock(return_value=[])):
        with patch("tools.supplier_tool._mcp_tools_cache", None):
            from tools.supplier_tool import get_open_pos_by_supplier
            result = get_open_pos_by_supplier.invoke({"supplier_ids": ["SUP001"]})
    assert result == []


def test_get_open_pos_empty_suppliers():
    mock_tool = AsyncMock()
    mock_tool.name = "PurchaseOrder"
    mock_tool.arun = AsyncMock(return_value={"value": []})

    with patch("tools.supplier_tool.get_mcp_tools", return_value=AsyncMock(return_value=[mock_tool])):
        with patch("tools.supplier_tool._mcp_tools_cache", None):
            from tools.supplier_tool import get_open_pos_by_supplier
            result = get_open_pos_by_supplier.invoke({"supplier_ids": []})
    assert isinstance(result, list)
