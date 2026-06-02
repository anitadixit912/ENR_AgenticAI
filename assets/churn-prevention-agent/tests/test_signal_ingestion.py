"""Unit tests for signal_ingestion.py"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(autouse=True)
def patch_path(add_agent_to_path):
    pass


def make_tool(name: str, return_value):
    tool = MagicMock()
    tool.name = name
    tool.arun = AsyncMock(return_value=return_value)
    return tool


@pytest.mark.asyncio
async def test_ingest_signals_basic():
    """Test that signal ingestion returns per-customer signal data."""
    from signal_ingestion import ingest_signals

    orders_resp = {"value": [
        {"SalesOrder": "0001", "SoldToParty": "C1001", "CreationDate": "2025-03-01T00:00:00",
         "TotalNetAmount": "45000.00", "TransactionCurrency": "EUR",
         "OverallSDProcessStatus": "C", "SDDocumentReason": ""},
        {"SalesOrder": "0002", "SoldToParty": "C1001", "CreationDate": "2025-01-15T00:00:00",
         "TotalNetAmount": "30000.00", "TransactionCurrency": "EUR",
         "OverallSDProcessStatus": "C", "SDDocumentReason": ""},
        {"SalesOrder": "0003", "SoldToParty": "C1001", "CreationDate": "2025-02-01T00:00:00",
         "TotalNetAmount": "35000.00", "TransactionCurrency": "EUR",
         "OverallSDProcessStatus": "C", "SDDocumentReason": ""},
        {"SalesOrder": "0004", "SoldToParty": "C1001", "CreationDate": "2025-02-15T00:00:00",
         "TotalNetAmount": "40000.00", "TransactionCurrency": "EUR",
         "OverallSDProcessStatus": "C", "SDDocumentReason": ""},
    ]}
    items_resp = {"value": [
        {"SalesOrder": "0001", "SalesOrderItem": "10", "SalesDocumentRjcnReason": ""},
        {"SalesOrder": "0001", "SalesOrderItem": "20", "SalesDocumentRjcnReason": "Z1"},
    ]}

    order_tool = make_tool("list_salesorder", orders_resp)
    item_tool = make_tool("list_salesorderitem", items_resp)

    result = await ingest_signals(["C1001"], [order_tool, item_tool])

    assert "C1001" in result
    sig = result["C1001"]
    assert sig["order_count"] == 4
    assert sig["return_count"] >= 0
    assert "avg_net_amount_recent" in sig
    assert "value_trend_pct" in sig


@pytest.mark.asyncio
async def test_ingest_signals_12_week_filter_applied():
    """Test that the filter passed to list_salesorder includes CreationDate ge datetime."""
    from signal_ingestion import ingest_signals

    order_tool = make_tool("list_salesorder", {"value": []})
    item_tool = make_tool("list_salesorderitem", {"value": []})

    await ingest_signals(["C9999"], [order_tool, item_tool])

    call_kwargs = order_tool.arun.call_args[0][0]
    assert "CreationDate ge" in call_kwargs.get("filter", "")
    assert "C9999" in call_kwargs.get("filter", "")


@pytest.mark.asyncio
async def test_ingest_signals_return_detection():
    """Items with non-empty SalesDocumentRjcnReason are counted as returns."""
    from signal_ingestion import ingest_signals

    orders_resp = {"value": [
        {"SalesOrder": "0001", "SoldToParty": "C2001", "CreationDate": "2025-03-01T00:00:00",
         "TotalNetAmount": "10000.00", "TransactionCurrency": "EUR",
         "OverallSDProcessStatus": "C", "SDDocumentReason": ""},
        {"SalesOrder": "0002", "SoldToParty": "C2001", "CreationDate": "2025-02-01T00:00:00",
         "TotalNetAmount": "12000.00", "TransactionCurrency": "EUR",
         "OverallSDProcessStatus": "C", "SDDocumentReason": ""},
        {"SalesOrder": "0003", "SoldToParty": "C2001", "CreationDate": "2025-01-01T00:00:00",
         "TotalNetAmount": "11000.00", "TransactionCurrency": "EUR",
         "OverallSDProcessStatus": "C", "SDDocumentReason": ""},
        {"SalesOrder": "0004", "SoldToParty": "C2001", "CreationDate": "2024-12-15T00:00:00",
         "TotalNetAmount": "9000.00", "TransactionCurrency": "EUR",
         "OverallSDProcessStatus": "C", "SDDocumentReason": ""},
    ]}
    items_resp = {"value": [
        {"SalesOrder": "0001", "SalesOrderItem": "10", "SalesDocumentRjcnReason": "A1"},
        {"SalesOrder": "0001", "SalesOrderItem": "20", "SalesDocumentRjcnReason": "A2"},
        {"SalesOrder": "0001", "SalesOrderItem": "30", "SalesDocumentRjcnReason": ""},
    ]}

    order_tool = make_tool("list_salesorder", orders_resp)
    item_tool = make_tool("list_salesorderitem", items_resp)

    result = await ingest_signals(["C2001"], [order_tool, item_tool])
    assert result["C2001"]["return_count"] == 8  # 2 per order * 4 orders


@pytest.mark.asyncio
async def test_ingest_signals_missing_tools_raises():
    """If required tools are missing, RuntimeError is raised."""
    from signal_ingestion import ingest_signals

    wrong_tool = make_tool("some_other_tool", {})

    with pytest.raises(RuntimeError):
        await ingest_signals(["C1001"], [wrong_tool])
