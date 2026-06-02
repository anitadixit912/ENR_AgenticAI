"""Unit tests for churn_scoring.py"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(autouse=True)
def patch_path(add_agent_to_path):
    pass


def make_llm_mock(response_json: list):
    llm = MagicMock()
    msg = MagicMock()
    msg.content = json.dumps(response_json)
    llm.ainvoke = AsyncMock(return_value=msg)
    return llm


@pytest.mark.asyncio
async def test_score_accounts_above_threshold_flagged():
    """Accounts with risk_score >= 65 appear in at_risk list."""
    from churn_scoring import score_accounts

    signals = {
        "C1001": {"order_count": 6, "value_trend_pct": -40.0, "return_count": 3,
                  "avg_net_amount_recent": 10000, "avg_net_amount_prior": 18000},
        "C1002": {"order_count": 8, "value_trend_pct": 5.0, "return_count": 0,
                  "avg_net_amount_recent": 22000, "avg_net_amount_prior": 21000},
    }
    enrichment = {
        "C1001": {"open_opportunity_count": 0, "total_opportunity_value": 0},
        "C1002": {"open_opportunity_count": 2, "total_opportunity_value": 50000},
    }
    llm_response = [
        {"account_id": "C1001", "risk_score": 78, "confidence": "High", "top_signals": ["declining order value"]},
        {"account_id": "C1002", "risk_score": 22, "confidence": "Low", "top_signals": ["stable orders"]},
    ]
    llm = make_llm_mock(llm_response)

    result = await score_accounts(signals, enrichment, llm, threshold=65)

    assert "C1001" in result["at_risk"]
    assert "C1002" not in result["at_risk"]
    assert result["scored"]["C1001"]["risk_score"] == 78
    assert result["scored"]["C1001"]["confidence"] == "High"


@pytest.mark.asyncio
async def test_score_accounts_watch_list_for_sparse_history():
    """Accounts with fewer than 4 orders go to watch_list, not scored."""
    from churn_scoring import score_accounts

    signals = {
        "C3001": {"order_count": 2, "value_trend_pct": None, "return_count": 0,
                  "avg_net_amount_recent": 5000, "avg_net_amount_prior": 0},
        "C3002": {"order_count": 5, "value_trend_pct": -10.0, "return_count": 1,
                  "avg_net_amount_recent": 8000, "avg_net_amount_prior": 9000},
    }
    enrichment = {
        "C3001": {"open_opportunity_count": 0, "total_opportunity_value": 0},
        "C3002": {"open_opportunity_count": 1, "total_opportunity_value": 20000},
    }
    llm_response = [
        {"account_id": "C3002", "risk_score": 45, "confidence": "Medium", "top_signals": ["slight decline"]},
    ]
    llm = make_llm_mock(llm_response)

    result = await score_accounts(signals, enrichment, llm, threshold=65)

    assert "C3001" in result["watch_list"]
    assert "C3001" not in result["scored"]
    assert "C3002" in result["scored"]


@pytest.mark.asyncio
async def test_score_accounts_invalid_json_from_llm():
    """If LLM returns invalid JSON, failed list is populated and no exception raised."""
    from churn_scoring import score_accounts

    signals = {
        "C4001": {"order_count": 6, "value_trend_pct": -20.0, "return_count": 1,
                  "avg_net_amount_recent": 5000, "avg_net_amount_prior": 7000},
    }
    enrichment = {"C4001": {"open_opportunity_count": 0, "total_opportunity_value": 0}}

    llm = MagicMock()
    bad_msg = MagicMock()
    bad_msg.content = "This is not JSON at all"
    llm.ainvoke = AsyncMock(return_value=bad_msg)

    result = await score_accounts(signals, enrichment, llm, threshold=65)

    assert "C4001" in result["failed"]
    assert "C4001" not in result["scored"]
    assert "C4001" not in result["at_risk"]


@pytest.mark.asyncio
async def test_score_accounts_all_watch_list_no_llm_call():
    """If all accounts are below min order count, LLM is never called."""
    from churn_scoring import score_accounts

    signals = {
        "C5001": {"order_count": 1, "value_trend_pct": None, "return_count": 0,
                  "avg_net_amount_recent": 0, "avg_net_amount_prior": 0},
    }
    enrichment = {"C5001": {"open_opportunity_count": 0, "total_opportunity_value": 0}}

    llm = MagicMock()
    llm.ainvoke = AsyncMock()

    result = await score_accounts(signals, enrichment, llm, threshold=65)

    llm.ainvoke.assert_not_called()
    assert "C5001" in result["watch_list"]
    assert len(result["scored"]) == 0
