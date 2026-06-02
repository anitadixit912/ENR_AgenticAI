"""Unit tests for update_supplier_risk_score tool."""
from unittest.mock import patch, AsyncMock


def test_update_high_severity():
    mock_tool = AsyncMock()
    mock_tool.name = "SupplierRisk"
    mock_tool.arun = AsyncMock(return_value={"PreviousRiskScore": 2})

    with patch("tools.supplier_risk_tool.get_mcp_tools", return_value=AsyncMock(return_value=[mock_tool])):
        with patch("tools.supplier_risk_tool._mcp_tools_cache", None):
            from tools.supplier_risk_tool import update_supplier_risk_score
            result = update_supplier_risk_score.invoke({
                "supplier_id": "SUP001",
                "severity": "High",
                "event_ref": "gdelt_001",
                "justification": "Active conflict near supplier facility."
            })

    assert isinstance(result, dict)


def test_update_skipped_low_severity():
    from tools.supplier_risk_tool import update_supplier_risk_score
    result = update_supplier_risk_score.invoke({
        "supplier_id": "SUP001",
        "severity": "Low",
        "event_ref": "gdelt_002",
        "justification": "Minor event."
    })
    assert result["status"] == "SKIPPED"


def test_update_skipped_medium_severity():
    from tools.supplier_risk_tool import update_supplier_risk_score
    result = update_supplier_risk_score.invoke({
        "supplier_id": "SUP002",
        "severity": "Medium",
        "event_ref": "gdelt_003",
        "justification": "Moderate disruption."
    })
    assert result["status"] == "SKIPPED"


def test_update_no_tool():
    with patch("tools.supplier_risk_tool.get_mcp_tools", return_value=AsyncMock(return_value=[])):
        with patch("tools.supplier_risk_tool._mcp_tools_cache", None):
            from tools.supplier_risk_tool import update_supplier_risk_score
            result = update_supplier_risk_score.invoke({
                "supplier_id": "SUP001",
                "severity": "Critical",
                "event_ref": "gdelt_004",
                "justification": "Critical conflict."
            })
    assert isinstance(result, dict)
