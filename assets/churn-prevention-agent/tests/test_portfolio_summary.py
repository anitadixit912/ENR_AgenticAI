"""Unit tests for portfolio_summary.py"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture(autouse=True)
def patch_path(add_agent_to_path):
    pass


@pytest.mark.asyncio
async def test_send_portfolio_summary_success():
    """Returns True when at least one manager is notified."""
    from portfolio_summary import send_portfolio_summary

    with patch("portfolio_summary.SALES_MANAGER_IDS", "MGR-001,MGR-002"):
        result = await send_portfolio_summary(scanned=100, flagged=12, alerts_sent=12, watch_listed=5)

    assert result is True


@pytest.mark.asyncio
async def test_send_portfolio_summary_no_managers_configured():
    """Returns False when SALES_MANAGER_IDS is empty."""
    from portfolio_summary import send_portfolio_summary

    with patch("portfolio_summary.SALES_MANAGER_IDS", ""):
        result = await send_portfolio_summary(scanned=50, flagged=3, alerts_sent=3, watch_listed=2)

    assert result is False


@pytest.mark.asyncio
async def test_send_portfolio_summary_message_content():
    """Joule message contains scan, flagged, and alert counts."""
    from portfolio_summary import send_portfolio_summary

    captured_messages = []

    async def fake_send(recipient_id, message):
        captured_messages.append(message)
        return True

    with patch("portfolio_summary.SALES_MANAGER_IDS", "MGR-001"):
        with patch("portfolio_summary._send_joule_summary", side_effect=fake_send):
            await send_portfolio_summary(scanned=80, flagged=7, alerts_sent=6, watch_listed=4)

    assert len(captured_messages) == 1
    msg = captured_messages[0]
    assert "80" in msg
    assert "7" in msg
    assert "6" in msg
    assert "4" in msg
