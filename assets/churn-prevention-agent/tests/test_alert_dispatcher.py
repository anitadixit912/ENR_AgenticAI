"""Unit tests for alert_dispatcher.py"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture(autouse=True)
def patch_path(add_agent_to_path):
    pass


@pytest.mark.asyncio
async def test_dispatch_alerts_success():
    """Alerts are dispatched when audit log write succeeds."""
    from alert_dispatcher import dispatch_alerts

    at_risk = ["C1001"]
    scores = {"C1001": {"risk_score": 78, "confidence": "High", "top_signals": ["declining trend"]}}
    enrichment = {"C1001": {"account_name": "Acme Corp", "owner_id": "USR-001", "open_opportunity_count": 2}}

    with patch("alert_dispatcher.log_action", new=AsyncMock(return_value=True)):
        with patch("alert_dispatcher.SALES_MANAGER_ID", "MGR-001"):
            with patch("alert_dispatcher.CSM_ID", "CSM-001"):
                result = await dispatch_alerts(at_risk, scores, enrichment)

    assert result["dispatched"] == 1
    assert result["failed"] == []
    assert result["recipients_notified"] > 0


@pytest.mark.asyncio
async def test_dispatch_alerts_skipped_when_audit_fails():
    """Alert is skipped (and account goes to failed list) when audit write returns False."""
    from alert_dispatcher import dispatch_alerts

    at_risk = ["C1001"]
    scores = {"C1001": {"risk_score": 78, "confidence": "High", "top_signals": ["declining trend"]}}
    enrichment = {"C1001": {"account_name": "Acme Corp", "owner_id": "USR-001", "open_opportunity_count": 0}}

    with patch("alert_dispatcher.log_action", new=AsyncMock(return_value=False)):
        result = await dispatch_alerts(at_risk, scores, enrichment)

    assert result["dispatched"] == 0
    assert "C1001" in result["failed"]


@pytest.mark.asyncio
async def test_dispatch_alerts_pii_not_in_audit_payload():
    """account_name must not appear in the payload passed to log_action."""
    from alert_dispatcher import dispatch_alerts

    captured_payloads = []

    async def mock_log_action(action_type, account_id, payload):
        captured_payloads.append(payload)
        return True

    at_risk = ["C1001"]
    scores = {"C1001": {"risk_score": 75, "confidence": "Medium", "top_signals": []}}
    enrichment = {"C1001": {"account_name": "Secret Corp Name", "owner_id": "USR-001", "open_opportunity_count": 0}}

    with patch("alert_dispatcher.log_action", side_effect=mock_log_action):
        with patch("alert_dispatcher.SALES_MANAGER_ID", "MGR-001"):
            with patch("alert_dispatcher.CSM_ID", "CSM-001"):
                await dispatch_alerts(at_risk, scores, enrichment)

    assert len(captured_payloads) == 1
    audit_payload = captured_payloads[0]
    assert "account_name" not in audit_payload
    assert "Secret Corp Name" not in str(audit_payload)


@pytest.mark.asyncio
async def test_dispatch_alerts_empty_at_risk():
    """If at_risk is empty, no alerts are dispatched."""
    from alert_dispatcher import dispatch_alerts

    result = await dispatch_alerts([], {}, {})

    assert result["dispatched"] == 0
    assert result["failed"] == []
    assert result["recipients_notified"] == 0
