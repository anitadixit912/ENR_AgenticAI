"""Unit tests for audit_logger.py"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(autouse=True)
def patch_path(add_agent_to_path):
    pass


@pytest.mark.asyncio
async def test_log_action_no_url_returns_true():
    """When AUDIT_LOG_URL is not configured, log_action logs locally and returns True."""
    from audit_logger import log_action

    with patch("audit_logger.AUDIT_LOG_URL", ""):
        result = await log_action("SCORING", "C1001", {"risk_score": 75})

    assert result is True


@pytest.mark.asyncio
async def test_log_action_pii_stripped():
    """account_name is stripped from payload before logging."""
    from audit_logger import log_action

    with patch("audit_logger.AUDIT_LOG_URL", ""):
        with patch("audit_logger.logger") as mock_logger:
            result = await log_action(
                "ALERT_DISPATCH",
                "C1001",
                {"risk_score": 80, "account_name": "Acme Corp", "recipients": ["USR-001"]}
            )
            # Verify logger was called without account_name in message
            assert result is True
            log_call = str(mock_logger.info.call_args_list)
            assert "Acme Corp" not in log_call


@pytest.mark.asyncio
async def test_log_action_http_failure_returns_false():
    """When the HTTP call fails, log_action returns False."""
    from audit_logger import log_action
    import urllib.error

    with patch("audit_logger.AUDIT_LOG_URL", "http://fake-audit-log/api"):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
            result = await log_action("ALERT_DISPATCH", "C1001", {"risk_score": 80})

    assert result is False


@pytest.mark.asyncio
async def test_log_batch_all_success():
    """log_batch returns True for all accounts on success."""
    from audit_logger import log_batch

    with patch("audit_logger.AUDIT_LOG_URL", ""):
        results = await log_batch(
            "SCORING",
            ["C1001", "C1002"],
            {"C1001": {"risk_score": 70}, "C1002": {"risk_score": 40}},
        )

    assert results["C1001"] is True
    assert results["C1002"] is True


@pytest.mark.asyncio
async def test_log_batch_partial_failure():
    """log_batch returns False for accounts where audit write fails."""
    from audit_logger import log_action, log_batch
    import urllib.error

    call_count = [0]

    def fake_urlopen(req, timeout=None):
        call_count[0] += 1
        if call_count[0] == 1:
            raise urllib.error.URLError("network error")
        resp = MagicMock()
        resp.status = 201
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("audit_logger.AUDIT_LOG_URL", "http://fake-audit-log/api"):
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            results = await log_batch(
                "SCORING",
                ["C1001", "C1002"],
                {"C1001": {"risk_score": 70}, "C1002": {"risk_score": 40}},
            )

    assert results["C1001"] is False
    assert results["C1002"] is True
