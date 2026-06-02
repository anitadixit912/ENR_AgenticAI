"""Unit tests for persist_risk_event tool."""
import json
import os
from unittest.mock import patch, MagicMock

SAMPLE_EVENT = {"event_id": "gdelt_001", "headline": "Conflict detected", "date": "2024-01-15", "url": "http://test.com", "source_country": "UA"}
SAMPLE_SCORE = {"severity": "High", "score_numeric": 3, "justification": "Active conflict.", "affected_supplier_count": 2, "affected_po_count": 3}
SAMPLE_SUPPLIERS = [{"supplier_id": "SUP001", "name": "ACME Corp", "country": "UA"}]
SAMPLE_POS = [{"po_number": "4500001", "supplier_id": "SUP001", "net_value": 50000.0}]


def test_persist_success():
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"ID": "test-uuid-1234"}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch.dict(os.environ, {"CAP_SERVICE_URL": "http://localhost:4004"}):
        with patch("urllib.request.urlopen", return_value=mock_resp):
            from tools.persistence_tool import persist_risk_event
            result = persist_risk_event.invoke({
                "event_data": SAMPLE_EVENT,
                "risk_score": SAMPLE_SCORE,
                "affected_suppliers": SAMPLE_SUPPLIERS,
                "affected_pos": SAMPLE_POS,
                "task_ids": ["TASK-001"]
            })

    assert result["status"] == "PERSISTED"
    assert "persisted_id" in result


def test_persist_handles_failure():
    with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
        with patch.dict(os.environ, {"CAP_SERVICE_URL": "http://localhost:4004"}):
            from tools.persistence_tool import persist_risk_event
            result = persist_risk_event.invoke({
                "event_data": SAMPLE_EVENT,
                "risk_score": SAMPLE_SCORE,
                "affected_suppliers": [],
                "affected_pos": [],
                "task_ids": []
            })

    assert result["status"] == "FAILED"
    assert "error" in result


def test_persist_uses_odata_v4_endpoint():
    """Verifies the tool posts to the correct OData v4 path."""
    captured_urls = []
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"ID": "uuid-path-check"}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    def capture_request(req, timeout=None):
        captured_urls.append(req.full_url)
        return mock_resp

    with patch.dict(os.environ, {"CAP_SERVICE_URL": "http://localhost:4004"}):
        with patch("urllib.request.urlopen", side_effect=capture_request):
            from tools.persistence_tool import persist_risk_event
            persist_risk_event.invoke({
                "event_data": SAMPLE_EVENT, "risk_score": SAMPLE_SCORE,
                "affected_suppliers": [], "affected_pos": [], "task_ids": []
            })

    assert len(captured_urls) == 1
    assert "/risk/RiskEvents" in captured_urls[0]


def test_persist_calculates_total_po_value():
    pos = [{"net_value": 10000.0}, {"net_value": 20000.0}, {"net_value": 30000.0}]
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"ID": "uuid-5678"}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    captured_payload = {}

    def capture_request(req, timeout=None):
        captured_payload.update(json.loads(req.data.decode()))
        return mock_resp

    with patch.dict(os.environ, {"CAP_SERVICE_URL": "http://localhost:4004"}):
        with patch("urllib.request.urlopen", side_effect=capture_request):
            from tools.persistence_tool import persist_risk_event
            persist_risk_event.invoke({
                "event_data": SAMPLE_EVENT, "risk_score": SAMPLE_SCORE,
                "affected_suppliers": [], "affected_pos": pos, "task_ids": []
            })

    assert captured_payload.get("totalPoValue") == 60000.0


# ââ Recommendations field tests âââââââââââââââââââââââââââââââââââââââââââââââ

def test_persist_includes_recommendations_in_payload():
    """Recommendations list must be JSON-serialised and included in the OData POST payload."""
    recs = [
        "IMMEDIATE: Activate emergency procurement protocol within 24 hours.",
        "Initiate alternative sourcing from backup suppliers outside conflict zone.",
        "Expedite open POs with delivery dates within 30 days.",
    ]
    score_with_recs = {**SAMPLE_SCORE, "recommendations": recs}
    captured_payload = {}

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"ID": "uuid-recs-test"}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    def capture_request(req, timeout=None):
        captured_payload.update(json.loads(req.data.decode()))
        return mock_resp

    with patch.dict(os.environ, {"CAP_SERVICE_URL": "http://localhost:4004"}):
        with patch("urllib.request.urlopen", side_effect=capture_request):
            from tools.persistence_tool import persist_risk_event
            result = persist_risk_event.invoke({
                "event_data": SAMPLE_EVENT,
                "risk_score": score_with_recs,
                "affected_suppliers": SAMPLE_SUPPLIERS,
                "affected_pos": SAMPLE_POS,
                "task_ids": ["TASK-001"],
            })

    assert result["status"] == "PERSISTED"
    assert "recommendations" in captured_payload
    stored = json.loads(captured_payload["recommendations"])
    assert isinstance(stored, list)
    assert len(stored) == 3
    assert "24 hours" in stored[0]


def test_persist_recommendations_defaults_to_empty_array_when_missing():
    """When risk_score has no recommendations key, payload must contain '[]'."""
    captured_payload = {}

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"ID": "uuid-no-recs"}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    def capture_request(req, timeout=None):
        captured_payload.update(json.loads(req.data.decode()))
        return mock_resp

    with patch.dict(os.environ, {"CAP_SERVICE_URL": "http://localhost:4004"}):
        with patch("urllib.request.urlopen", side_effect=capture_request):
            from tools.persistence_tool import persist_risk_event
            persist_risk_event.invoke({
                "event_data": SAMPLE_EVENT,
                "risk_score": SAMPLE_SCORE,  # no recommendations key
                "affected_suppliers": [],
                "affected_pos": [],
                "task_ids": [],
            })

    assert "recommendations" in captured_payload
    stored = json.loads(captured_payload["recommendations"])
    assert stored == []
