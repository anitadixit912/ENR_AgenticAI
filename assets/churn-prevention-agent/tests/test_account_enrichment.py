"""Unit tests for account_enrichment.py"""

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
async def test_enrich_accounts_basic():
    """Returns account name, segment, owner, and opportunity data."""
    from account_enrichment import enrich_accounts

    account_tool = make_tool("queryaccountservice_accounts", {
        "value": [{"id": "C1001", "displayName": "Acme Corp", "segmentCode": "ENTERPRISE", "ownerID": "USR-001"}]
    })
    opp_tool = make_tool("queryopportunityservice_opportunit", {
        "value": [
            {"id": "OPP-1", "accountID": "C1001", "expectedValue": "50000", "lifeCycleStatusCode": "2"},
            {"id": "OPP-2", "accountID": "C1001", "expectedValue": "30000", "lifeCycleStatusCode": "3"},
        ]
    })

    result = await enrich_accounts(["C1001"], [account_tool, opp_tool])

    assert "C1001" in result
    enr = result["C1001"]
    assert enr["account_name"] == "Acme Corp"
    assert enr["segment"] == "ENTERPRISE"
    assert enr["owner_id"] == "USR-001"
    assert enr["open_opportunity_count"] == 2
    assert enr["total_opportunity_value"] == 80000.0


@pytest.mark.asyncio
async def test_enrich_accounts_graceful_fallback_when_service_unavailable():
    """If Account Service tool raises, partial enrichment is returned (no exception)."""
    from account_enrichment import enrich_accounts

    account_tool = MagicMock()
    account_tool.name = "queryaccountservice_accounts"
    account_tool.arun = AsyncMock(side_effect=ConnectionError("Service unavailable"))

    opp_tool = MagicMock()
    opp_tool.name = "queryopportunityservice_opportunit"
    opp_tool.arun = AsyncMock(return_value={"value": []})

    # Must NOT raise
    result = await enrich_accounts(["C1001"], [account_tool, opp_tool])

    assert "C1001" in result
    # Partial enrichment: account fields are None
    assert result["C1001"]["account_name"] is None
    assert result["C1001"]["owner_id"] is None


@pytest.mark.asyncio
async def test_enrich_accounts_no_tools():
    """If neither tool is found, returns default empty enrichment without raising."""
    from account_enrichment import enrich_accounts

    result = await enrich_accounts(["C1001"], [])

    assert "C1001" in result
    assert result["C1001"]["open_opportunity_count"] == 0
    assert result["C1001"]["account_name"] is None


@pytest.mark.asyncio
async def test_enrich_accounts_closed_opportunities_excluded():
    """Closed opportunities (status 4, 5, 6) are NOT counted in open_opportunity_count."""
    from account_enrichment import enrich_accounts

    opp_tool = make_tool("queryopportunityservice_opportunit", {
        "value": [
            {"id": "OPP-1", "accountID": "C1001", "expectedValue": "10000", "lifeCycleStatusCode": "2"},  # open
            {"id": "OPP-2", "accountID": "C1001", "expectedValue": "20000", "lifeCycleStatusCode": "4"},  # closed/won
            {"id": "OPP-3", "accountID": "C1001", "expectedValue": "15000", "lifeCycleStatusCode": "5"},  # closed/lost
        ]
    })

    result = await enrich_accounts(["C1001"], [opp_tool])
    assert result["C1001"]["open_opportunity_count"] == 1
    assert result["C1001"]["total_opportunity_value"] == 10000.0
