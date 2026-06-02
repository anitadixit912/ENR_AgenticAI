"""Integration test: full agent pipeline with mocked tools."""
import sys
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


@pytest.mark.asyncio
async def test_agent_full_pipeline_scheduled_run():
    """Full _run_agent() pipeline with all externals mocked."""
    gdelt_events = [
        {"event_id": "gdelt_001", "headline": "Military conflict in Ukraine", "date": "2024-01-15",
         "url": "http://test.com", "source_country": "UA", "tone_score": -8.0, "themes": "MILITARY_ATTACK;CONFLICT"}
    ]
    suppliers    = [{"supplier_id": "SUP001", "name": "ACME Corp", "country": "UA", "city": "Kyiv", "postal_code": "01001"}]
    open_pos     = [{"po_number": "4500001", "supplier_id": "SUP001", "net_value": 100000.0, "currency": "USD"}]
    score_result = {"severity": "High", "score_numeric": 3, "justification": "Active conflict.",
                    "affected_supplier_count": 1, "affected_po_count": 1, "total_po_value": 100000.0}

    mock_gdelt   = MagicMock(); mock_gdelt.invoke   = MagicMock(return_value=gdelt_events)
    mock_sup     = MagicMock(); mock_sup.invoke     = MagicMock(return_value=suppliers)
    mock_pos     = MagicMock(); mock_pos.invoke     = MagicMock(return_value=open_pos)
    mock_score   = MagicMock(); mock_score.invoke   = MagicMock(return_value=score_result)
    mock_task    = MagicMock(); mock_task.invoke    = MagicMock(return_value={"task_id": "T001", "status": "CREATED", "supplier_id": "SUP001"})
    mock_risk    = MagicMock(); mock_risk.invoke    = MagicMock(return_value={"supplier_id": "SUP001", "status": "UPDATED"})
    mock_email   = MagicMock(); mock_email.invoke   = MagicMock(return_value={"sent": False, "recipient_count": 0})
    mock_persist = MagicMock(); mock_persist.invoke = MagicMock(return_value={"persisted_id": "uuid-001", "status": "PERSISTED"})

    # app/ is on sys.path (added by conftest), so agent modules are top-level imports.
    # Patch targets must match the runtime import namespace (no "app." prefix).
    with patch("agent.fetch_gdelt_events",          mock_gdelt), \
         patch("agent.get_suppliers_by_region",     mock_sup), \
         patch("agent.get_open_pos_by_supplier",    mock_pos), \
         patch("agent.score_risk",                  mock_score), \
         patch("agent.create_sap_procurement_task", mock_task), \
         patch("agent.update_supplier_risk_score",  mock_risk), \
         patch("agent.send_alert_email",            mock_email), \
         patch("agent.persist_risk_event",          mock_persist), \
         patch("agent.get_mcp_tools", new_callable=AsyncMock, return_value=[]):

        from agent import GeopoliticalRiskAgent
        agent = GeopoliticalRiskAgent()
        summary = await agent._run_agent("run geopolitical risk scan", "ctx-001")

    assert summary["events_processed"] >= 1
    assert "high_critical_count" in summary
    assert "tasks_created" in summary
    assert "suppliers_updated" in summary


@pytest.mark.asyncio
async def test_agent_handles_empty_signals():
    """Agent exits early and skips all SAP writes when GDELT returns no events."""
    mock_gdelt = MagicMock(); mock_gdelt.invoke = MagicMock(return_value=[])
    mock_news  = MagicMock(); mock_news.invoke  = MagicMock(return_value=[])

    with patch("agent.fetch_gdelt_events",  mock_gdelt), \
         patch("agent.fetch_news_articles", mock_news), \
         patch("agent.get_mcp_tools", new_callable=AsyncMock, return_value=[]):

        from agent import GeopoliticalRiskAgent
        agent = GeopoliticalRiskAgent()
        summary = await agent._run_agent("scheduled risk scan", "ctx-002")

    # When no signals, pipeline exits early â events_processed stays 0 and no SAP writes
    assert summary["tasks_created"] == 0
    assert summary["suppliers_updated"] == 0
