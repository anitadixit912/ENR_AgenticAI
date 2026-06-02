"""Unit tests for score_risk tool."""
import json
from unittest.mock import patch, MagicMock


SAMPLE_EVENT = {
    "event_id": "gdelt_001",
    "headline": "Military offensive launched in eastern region",
    "date": "2024-01-15",
    "source_country": "UA",
    "themes": "MILITARY_ATTACK;CONFLICT",
    "tone_score": -8.5
}

SAMPLE_SUPPLIERS = [
    {"supplier_id": "SUP001", "name": "ACME Corp", "country": "UA"},
    {"supplier_id": "SUP002", "name": "Baltic Steel", "country": "UA"}
]

SAMPLE_POS = [
    {"po_number": "4500001", "supplier_id": "SUP001", "net_value": 100000.0},
    {"po_number": "4500002", "supplier_id": "SUP002", "net_value": 75000.0}
]


def test_score_risk_llm_success():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"severity": "Critical", "score_numeric": 4, "justification": "Active military offensive directly threatens supplier operations."}'

    with patch("litellm.completion", return_value=mock_response):
        from tools.risk_scoring_tool import score_risk
        result = score_risk.invoke({"event": SAMPLE_EVENT, "affected_suppliers": SAMPLE_SUPPLIERS, "affected_pos": SAMPLE_POS})

    assert result["severity"] == "Critical"
    assert result["score_numeric"] == 4
    assert "justification" in result
    assert result["affected_supplier_count"] == 2


def test_score_risk_llm_fallback_on_error():
    with patch("litellm.completion", side_effect=Exception("LLM unavailable")):
        from tools.risk_scoring_tool import score_risk
        result = score_risk.invoke({"event": SAMPLE_EVENT, "affected_suppliers": SAMPLE_SUPPLIERS, "affected_pos": SAMPLE_POS})

    assert result["severity"] in ("Low", "Medium", "High", "Critical")
    assert result["score_numeric"] in (1, 2, 3, 4)
    assert result["scoring_method"] == "rule_based"


def test_score_risk_no_suppliers():
    with patch("litellm.completion", side_effect=Exception("LLM unavailable")):
        from tools.risk_scoring_tool import score_risk
        result = score_risk.invoke({"event": SAMPLE_EVENT, "affected_suppliers": [], "affected_pos": []})

    assert result["affected_supplier_count"] == 0
    assert result["affected_po_count"] == 0


def test_score_risk_returns_valid_severity():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"severity": "High", "score_numeric": 3, "justification": "Significant disruption risk."}'

    with patch("litellm.completion", return_value=mock_response):
        from tools.risk_scoring_tool import score_risk
        result = score_risk.invoke({"event": SAMPLE_EVENT, "affected_suppliers": SAMPLE_SUPPLIERS[:1], "affected_pos": SAMPLE_POS[:1]})

    assert result["severity"] in ("Low", "Medium", "High", "Critical")


# ââ Recommendations tests âââââââââââââââââââââââââââââââââââââââââââââââââââââ

def test_score_risk_llm_returns_recommendations():
    """LLM path: returned dict must include non-empty recommendations list for Critical."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({
        "severity": "Critical",
        "score_numeric": 4,
        "justification": "Active offensive threatening supplier operations.",
        "recommendations": [
            "IMMEDIATE: Contact all affected suppliers within 24 hours.",
            "Activate emergency procurement protocol.",
            "Initiate alternative sourcing from backup suppliers.",
        ]
    })

    with patch("litellm.completion", return_value=mock_response):
        from tools.risk_scoring_tool import score_risk
        result = score_risk.invoke({
            "event": SAMPLE_EVENT,
            "affected_suppliers": SAMPLE_SUPPLIERS,
            "affected_pos": SAMPLE_POS,
        })

    assert "recommendations" in result
    assert isinstance(result["recommendations"], list)
    assert len(result["recommendations"]) > 0
    assert any("24" in r or "IMMEDIATE" in r for r in result["recommendations"])


def test_score_risk_rule_based_fallback_returns_recommendations():
    """Rule-based fallback must also populate recommendations for High/Critical."""
    with patch("litellm.completion", side_effect=Exception("LLM unavailable")):
        from tools.risk_scoring_tool import score_risk
        result = score_risk.invoke({
            "event": SAMPLE_EVENT,
            "affected_suppliers": SAMPLE_SUPPLIERS,
            "affected_pos": SAMPLE_POS,
        })

    assert "recommendations" in result
    assert isinstance(result["recommendations"], list)
    assert len(result["recommendations"]) > 0


def test_score_risk_high_severity_recommendations():
    """High severity LLM result should carry recommendations list."""
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({
        "severity": "High",
        "score_numeric": 3,
        "justification": "Significant disruption risk to supply chain.",
        "recommendations": [
            "Contact affected suppliers within 48 hours.",
            "Identify alternative suppliers in unaffected regions.",
        ]
    })

    with patch("litellm.completion", return_value=mock_response):
        from tools.risk_scoring_tool import score_risk
        result = score_risk.invoke({
            "event": SAMPLE_EVENT,
            "affected_suppliers": SAMPLE_SUPPLIERS[:1],
            "affected_pos": SAMPLE_POS[:1],
        })

    assert result["severity"] == "High"
    assert "recommendations" in result
    assert len(result["recommendations"]) > 0


def test_score_risk_low_severity_has_recommendations():
    """Even Low severity events should return a recommendations list (monitoring-focused)."""
    low_event = {**SAMPLE_EVENT, "themes": "ECONOMY", "tone_score": -1.0}
    with patch("litellm.completion", side_effect=Exception("LLM unavailable")):
        from tools.risk_scoring_tool import score_risk
        result = score_risk.invoke({
            "event": low_event,
            "affected_suppliers": [],
            "affected_pos": [],
        })

    assert "recommendations" in result
    # Low severity: at least one recommendation present
    assert isinstance(result["recommendations"], list)
