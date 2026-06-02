"""Unit tests for get_suppliers_by_region tool."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock


def test_get_suppliers_by_region_success():
    mock_tool = AsyncMock()
    mock_tool.name = "BusinessPartner"
    mock_tool.arun = AsyncMock(return_value={"value": [
        {"BusinessPartner": "SUP001", "BusinessPartnerFullName": "ACME Corp", "BusinessPartnerCountry": "UA", "CityName": "Kyiv", "PostalCode": "01001"}
    ]})

    with patch("tools.supplier_tool.get_mcp_tools", return_value=AsyncMock(return_value=[mock_tool])):
        with patch("tools.supplier_tool._mcp_tools_cache", None):
            from tools.supplier_tool import get_suppliers_by_region
            result = get_suppliers_by_region.invoke({"country_codes": ["UA"]})

    assert isinstance(result, list)


def test_get_suppliers_by_region_no_mcp_tool():
    with patch("tools.supplier_tool.get_mcp_tools", return_value=AsyncMock(return_value=[])):
        with patch("tools.supplier_tool._mcp_tools_cache", None):
            from tools.supplier_tool import get_suppliers_by_region
            result = get_suppliers_by_region.invoke({"country_codes": ["UA"]})
    assert result == []


def test_get_suppliers_by_region_empty_codes():
    mock_tool = AsyncMock()
    mock_tool.name = "BusinessPartner"
    mock_tool.arun = AsyncMock(return_value={"value": []})

    with patch("tools.supplier_tool.get_mcp_tools", return_value=AsyncMock(return_value=[mock_tool])):
        with patch("tools.supplier_tool._mcp_tools_cache", None):
            from tools.supplier_tool import get_suppliers_by_region
            result = get_suppliers_by_region.invoke({"country_codes": []})
    assert isinstance(result, list)
