"""
Integration test — end-to-end agent flow with mocked LLM and MCP tools.
Tests the full pipeline: signal ingestion → enrichment → scoring → alerts → summary.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(autouse=True)
def patch_path(add_agent_to_path):
    pass


def make_mcp_tool(name: str, return_value):
    tool = MagicMock()
    tool.name = name
    tool.arun = AsyncMock(return_value=return_value)
    return tool


def make_llm_mock():
    """Mock LLM that returns a realistic scoring response for test accounts."""
    llm = MagicMock()

    # The churn scoring prompt response
    scoring_response = MagicMock()
    scoring_response.content = json.dumps([
        {
            "account_id": "C1001",
            "risk_score": 72,
            "confidence": "High",
            "top_signals": ["40% decline in order value", "3 returns in 12 weeks", "no recent orders"],
        },
        {
            "account_id": "C1002",
            "risk_score": 28,
            "confidence": "Low",
            "top_signals": ["stable order frequency"],
        },
    ])

    # For conversational LLM invocations (agent graph)
    chat_response = MagicMock()
    chat_response.content = "Churn scan complete."

    llm.ainvoke = AsyncMock(return_value=scoring_response)
    return llm


@pytest.fixture
def mock_tools():
    """MCP tools fixture with realistic S/4HANA response data."""
    orders_resp = {"value": [
        {
            "SalesOrder": f"000{i:04d}", "SoldToParty": "C1001",
            "CreationDate": f"2025-0{(i % 3) + 1}-15T00:00:00",
            "TotalNetAmount": str(30000 - i * 2000), "TransactionCurrency": "EUR",
            "OverallSDProcessStatus": "C", "SDDocumentReason": "",
        }
        for i in range(1, 7)
    ]}
    items_resp = {"value": [
        {"SalesOrder": "00001", "SalesOrderItem": "10", "SalesDocumentRjcnReason": "Z1"},
        {"SalesOrder": "00001", "SalesOrderItem": "20", "SalesDocumentRjcnReason": ""},
    ]}

    return [
        make_mcp_tool("list_salesorder", orders_resp),
        make_mcp_tool("list_salesorderitem", items_resp),
        make_mcp_tool("queryaccountservice_accounts", {"value": [
            {"id": "C1001", "displayName": "Acme Corp", "segmentCode": "ENTERPRISE", "ownerID": "USR-001"},
        ]}),
        make_mcp_tool("queryopportunityservice_opportunit", {"value": [
            {"id": "OPP-1", "accountID": "C1001", "expectedValue": "50000", "lifeCycleStatusCode": "2"},
        ]}),
    ]


@pytest.mark.asyncio
async def test_full_pipeline_produces_result(mock_tools):
    """Full pipeline runs without error and returns a non-empty string."""
    from agent import SampleAgent

    agent = SampleAgent()
    agent.llm = make_llm_mock()

    with patch("agent.DEFAULT_CUSTOMER_IDS", ["C1001", "C1002"]):
        with patch("agent.SALES_MANAGER_IDS", "MGR-001", create=True):
            with patch("alert_dispatcher.SALES_MANAGER_ID", "MGR-001"):
                with patch("alert_dispatcher.CSM_ID", "CSM-001"):
                    with patch("portfolio_summary.SALES_MANAGER_IDS", "MGR-001"):
                        # C1002 has no signal data — it will go to watch list (order_count=0)
                        result = await agent._run_churn_pipeline(mock_tools)

    assert isinstance(result, str)
    assert len(result) > 0
    assert "scanned" in result.lower() or "churn" in result.lower()


@pytest.mark.asyncio
async def test_pipeline_at_risk_account_in_output(mock_tools):
    """At-risk account C1001 appears in the pipeline output."""
    from agent import SampleAgent

    agent = SampleAgent()
    agent.llm = make_llm_mock()

    with patch("agent.DEFAULT_CUSTOMER_IDS", ["C1001"]):
        with patch("alert_dispatcher.SALES_MANAGER_ID", "MGR-001"):
            with patch("alert_dispatcher.CSM_ID", "CSM-001"):
                with patch("portfolio_summary.SALES_MANAGER_IDS", "MGR-001"):
                    result = await agent._run_churn_pipeline(mock_tools)

    assert "C1001" in result


@pytest.mark.asyncio
async def test_invoke_scan_query(mock_tools):
    """agent.invoke() with a scan query returns completed status."""
    from agent import SampleAgent

    agent = SampleAgent()
    agent.llm = make_llm_mock()

    with patch("agent.DEFAULT_CUSTOMER_IDS", ["C1001"]):
        with patch("alert_dispatcher.SALES_MANAGER_ID", "MGR-001"):
            with patch("alert_dispatcher.CSM_ID", "CSM-001"):
                with patch("portfolio_summary.SALES_MANAGER_IDS", "MGR-001"):
                    response = await agent.invoke(
                        "Run the weekly churn scan", "test-ctx-001", tools=mock_tools
                    )

    assert response.status == "completed"
    assert len(response.message) > 0
