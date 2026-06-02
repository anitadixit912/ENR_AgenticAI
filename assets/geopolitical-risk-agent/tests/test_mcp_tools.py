"""Unit tests for mcp_tools module (mock path and production path)."""
import json
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock


# ── helpers ───────────────────────────────────────────────────────────────────

MOCK_DATA = {
    "servers": {
        "business-partner": {
            "tools": {
                "BusinessPartner_get": {
                    "description": "Get business partner data",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "$filter": {"type": "string"},
                            "$top": {"type": "integer"},
                        },
                        "required": ["$filter"],
                    },
                    "mock_response": {"value": [{"BusinessPartner": "SUP001"}]},
                }
            }
        },
        "purchase-order": {
            "tools": {
                "PurchaseOrder_get": {
                    "description": "Get purchase orders",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "$filter": {"type": "string"},
                        },
                    },
                    "mock_response": {"value": []},
                }
            }
        },
    }
}

MOCK_DATA_WITH_TYPES = {
    "servers": {
        "test-server": {
            "tools": {
                "AllTypes_tool": {
                    "description": "Tool with all field types",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "str_field": {"type": "string"},
                            "int_field": {"type": "integer"},
                            "float_field": {"type": "number"},
                            "bool_field": {"type": "boolean"},
                            "required_str": {"type": "string"},
                        },
                        "required": ["required_str"],
                    },
                    "mock_response": {"status": "ok"},
                }
            }
        }
    }
}


# ── tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_mcp_tools_returns_mock_tools(tmp_path):
    """In IBD_TESTING mode, get_mcp_tools returns StructuredTool instances from mcp-mock.json."""
    mock_file = tmp_path / "mcp-mock.json"
    mock_file.write_text(json.dumps(MOCK_DATA))

    with patch.dict(os.environ, {"IBD_TESTING": "1"}):
        import importlib
        import mcp_tools
        # Patch the _MOCK_FILE path to point to our temp file
        with patch.object(mcp_tools, "_MOCK_FILE", mock_file):
            tools = await mcp_tools.get_mcp_tools()

    assert len(tools) == 2
    tool_names = [t.name for t in tools]
    assert "BusinessPartner_get" in tool_names
    assert "PurchaseOrder_get" in tool_names


@pytest.mark.asyncio
async def test_get_mcp_tools_missing_mock_file(tmp_path):
    """Returns empty list when mcp-mock.json does not exist."""
    missing = tmp_path / "does_not_exist.json"

    with patch.dict(os.environ, {"IBD_TESTING": "1"}):
        import mcp_tools
        with patch.object(mcp_tools, "_MOCK_FILE", missing):
            tools = await mcp_tools.get_mcp_tools()

    assert tools == []


@pytest.mark.asyncio
async def test_get_mcp_tools_invalid_json(tmp_path):
    """Returns empty list when mcp-mock.json contains invalid JSON."""
    bad_file = tmp_path / "mcp-mock.json"
    bad_file.write_text("{ invalid json !!!")

    with patch.dict(os.environ, {"IBD_TESTING": "1"}):
        import mcp_tools
        with patch.object(mcp_tools, "_MOCK_FILE", bad_file):
            tools = await mcp_tools.get_mcp_tools()

    assert tools == []


@pytest.mark.asyncio
async def test_mock_tools_all_field_types(tmp_path):
    """_build_mock_tools correctly handles string/int/float/bool field types."""
    mock_file = tmp_path / "mcp-mock.json"
    mock_file.write_text(json.dumps(MOCK_DATA_WITH_TYPES))

    with patch.dict(os.environ, {"IBD_TESTING": "1"}):
        import mcp_tools
        with patch.object(mcp_tools, "_MOCK_FILE", mock_file):
            tools = await mcp_tools.get_mcp_tools()

    assert len(tools) == 1
    tool = tools[0]
    assert tool.name == "AllTypes_tool"
    schema = tool.args_schema.model_fields
    assert "str_field" in schema
    assert "int_field" in schema
    assert "float_field" in schema
    assert "bool_field" in schema
    assert "required_str" in schema


@pytest.mark.asyncio
async def test_mock_tool_returns_mock_response(tmp_path):
    """Mock tool coroutine returns serialized mock_response JSON."""
    mock_file = tmp_path / "mcp-mock.json"
    mock_file.write_text(json.dumps(MOCK_DATA))

    with patch.dict(os.environ, {"IBD_TESTING": "1"}):
        import mcp_tools
        with patch.object(mcp_tools, "_MOCK_FILE", mock_file):
            tools = await mcp_tools.get_mcp_tools()

    bp_tool = next(t for t in tools if t.name == "BusinessPartner_get")
    # Tools expose a coroutine; call it via arun
    raw = await bp_tool.arun({"$filter": "BusinessPartnerCountry eq 'UA'", "$top": 10})
    parsed = json.loads(raw)
    assert parsed["value"][0]["BusinessPartner"] == "SUP001"


@pytest.mark.asyncio
async def test_get_mcp_tools_production_mcp_client_failure():
    """In production mode, returns empty list when MCPClient raises."""
    import mcp_tools
    import importlib

    mock_client_instance = MagicMock()
    mock_client_instance.get_mcp_tools = AsyncMock(side_effect=Exception("network error"))
    mock_client_class = MagicMock(return_value=mock_client_instance)

    mock_mcp_client_module = MagicMock()
    mock_mcp_client_module.MCPClient = mock_client_class
    mock_mcp_client_module.MCPToolConverter = MagicMock()

    env_without_testing = {k: v for k, v in os.environ.items() if k != "IBD_TESTING"}
    with patch.dict(os.environ, env_without_testing, clear=True):
        with patch.dict("sys.modules", {"mcp_client": mock_mcp_client_module}):
            # Reload to pick up the env change
            importlib.reload(mcp_tools)
            tools = await mcp_tools.get_mcp_tools()

    # Restore IBD_TESTING for subsequent tests
    os.environ["IBD_TESTING"] = "1"
    importlib.reload(mcp_tools)

    assert tools == []
