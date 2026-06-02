"""Extended unit tests for supplier and PO tools — improves coverage of MCP async paths.

Strategy: pre-seed `_mcp_tools_cache` with mock tools so `_get_mcp()` skips the
`get_mcp_tools()` call entirely and returns the pre-built list directly.
This avoids the async-fetch path while still exercising all business logic.
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


def _make_bp_tool(name="BusinessPartner", response=None):
    if response is None:
        response = {"value": []}
    t = MagicMock()
    t.name = name
    t.arun = AsyncMock(return_value=response)
    return t


def _make_po_tool(name="PurchaseOrder", response=None):
    if response is None:
        response = {"value": []}
    t = MagicMock()
    t.name = name
    t.arun = AsyncMock(return_value=response)
    return t


# ── get_suppliers_by_region ───────────────────────────────────────────────────


def test_suppliers_list_response():
    """Handles raw list response (not dict with 'value' key)."""
    mock_tool = _make_bp_tool(response=[
        {"BusinessPartner": "SUP010", "BusinessPartnerFullName": "Test Supplier",
         "BusinessPartnerCountry": "IL", "CityName": "Tel Aviv", "PostalCode": "6100001"}
    ])
    with patch("tools.supplier_tool._mcp_tools_cache", [mock_tool]):
        from tools.supplier_tool import get_suppliers_by_region
        result = get_suppliers_by_region.invoke({"country_codes": ["IL"]})

    assert isinstance(result, list)
    assert any(s.get("supplier_id") == "SUP010" for s in result)


def test_suppliers_mcp_exception_returns_empty():
    """Returns empty list when MCP tool raises an exception."""
    mock_tool = MagicMock()
    mock_tool.name = "BusinessPartner"
    mock_tool.arun = AsyncMock(side_effect=Exception("MCP timeout"))

    with patch("tools.supplier_tool._mcp_tools_cache", [mock_tool]):
        from tools.supplier_tool import get_suppliers_by_region
        result = get_suppliers_by_region.invoke({"country_codes": ["UA"]})

    assert result == []


def test_suppliers_multiple_countries():
    """Returns all matched suppliers across multiple country codes."""
    mock_tool = _make_bp_tool(response={"value": [
        {"BusinessPartner": "SUP001", "BusinessPartnerFullName": "Corp A",
         "BusinessPartnerCountry": "UA", "CityName": "Kyiv", "PostalCode": "01001"},
        {"BusinessPartner": "SUP002", "BusinessPartnerFullName": "Corp B",
         "BusinessPartnerCountry": "RU", "CityName": "Moscow", "PostalCode": "101000"},
    ]})

    with patch("tools.supplier_tool._mcp_tools_cache", [mock_tool]):
        from tools.supplier_tool import get_suppliers_by_region
        result = get_suppliers_by_region.invoke({"country_codes": ["UA", "RU"]})

    assert len(result) == 2


def test_suppliers_no_mcp_tool_returns_empty():
    """Returns empty list when no matching BP tool is in cache."""
    mock_tool = _make_bp_tool(name="SomethingElse", response={"value": []})

    with patch("tools.supplier_tool._mcp_tools_cache", [mock_tool]):
        from tools.supplier_tool import get_suppliers_by_region
        result = get_suppliers_by_region.invoke({"country_codes": ["UA"]})

    assert result == []


# ── get_open_pos_by_supplier ──────────────────────────────────────────────────


def test_pos_success():
    """Returns mapped PO list from MCP dict response."""
    mock_tool = _make_po_tool(response={"value": [
        {"PurchaseOrder": "4500001", "Supplier": "SUP001", "Material": "MAT-A",
         "NetPriceAmount": "50000.00", "DocumentCurrency": "USD",
         "ScheduleLine": "2024-06-01", "Plant": "1000"}
    ]})

    with patch("tools.supplier_tool._mcp_tools_cache", [mock_tool]):
        from tools.supplier_tool import get_open_pos_by_supplier
        result = get_open_pos_by_supplier.invoke({"supplier_ids": ["SUP001"]})

    assert len(result) == 1
    assert result[0]["po_number"] == "4500001"
    assert result[0]["net_value"] == 50000.0
    assert result[0]["currency"] == "USD"


def test_pos_no_tool_returns_empty():
    """Returns empty list when PO MCP tool not found."""
    mock_tool = _make_po_tool(name="SomethingElse")

    with patch("tools.supplier_tool._mcp_tools_cache", [mock_tool]):
        from tools.supplier_tool import get_open_pos_by_supplier
        result = get_open_pos_by_supplier.invoke({"supplier_ids": ["SUP001"]})

    assert result == []


def test_pos_list_response():
    """Handles raw list response (no 'value' wrapper) from MCP."""
    mock_tool = _make_po_tool(response=[
        {"PurchaseOrder": "4500002", "Supplier": "SUP002", "Material": "MAT-B",
         "NetPriceAmount": None, "DocumentCurrency": "EUR",
         "ScheduleLine": "2024-07-01", "Plant": "2000"}
    ])

    with patch("tools.supplier_tool._mcp_tools_cache", [mock_tool]):
        from tools.supplier_tool import get_open_pos_by_supplier
        result = get_open_pos_by_supplier.invoke({"supplier_ids": ["SUP002"]})

    assert len(result) == 1
    assert result[0]["net_value"] == 0.0  # None coerced to 0.0


def test_pos_exception_returns_empty():
    """Returns empty list when MCP arun raises."""
    mock_tool = MagicMock()
    mock_tool.name = "PurchaseOrder"
    mock_tool.arun = AsyncMock(side_effect=RuntimeError("timeout"))

    with patch("tools.supplier_tool._mcp_tools_cache", [mock_tool]):
        from tools.supplier_tool import get_open_pos_by_supplier
        result = get_open_pos_by_supplier.invoke({"supplier_ids": ["SUP001"]})

    assert result == []
