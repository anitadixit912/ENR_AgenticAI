"""Unit tests for fetch_gdelt_events tool."""
import pytest
from unittest.mock import patch, MagicMock
import json


def test_fetch_gdelt_events_success():
    mock_response_data = {
        "articles": [
            {"seendate": "20240101", "title": "Conflict in region", "url": "http://test.com",
             "sourcecountry": "UA", "tone": "-5.2", "themes": "CONFLICT;MILITARY", "domain": "test.com", "language": "English"}
        ]
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_response_data).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        from tools.gdelt_tool import fetch_gdelt_events
        result = fetch_gdelt_events.invoke({"regions": ["eastern_europe"], "themes": ["CONFLICT"], "lookback_minutes": 60})

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["source_country"] == "UA"
    assert result[0]["headline"] == "Conflict in region"


def test_fetch_gdelt_events_filters_by_region():
    mock_response_data = {
        "articles": [
            {"seendate": "20240101", "title": "Event A", "url": "http://a.com", "sourcecountry": "UA", "tone": "-3", "themes": "CONFLICT", "domain": "a.com", "language": "English"},
            {"seendate": "20240101", "title": "Event B", "url": "http://b.com", "sourcecountry": "US", "tone": "-1", "themes": "PROTEST", "domain": "b.com", "language": "English"},
        ]
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_response_data).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        from tools.gdelt_tool import fetch_gdelt_events
        result = fetch_gdelt_events.invoke({"regions": ["eastern_europe"], "themes": ["CONFLICT"], "lookback_minutes": 60})

    # Only UA should pass eastern_europe filter
    countries = [e["source_country"] for e in result]
    assert "UA" in countries
    assert "US" not in countries


def test_fetch_gdelt_events_handles_api_error():
    with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
        from tools.gdelt_tool import fetch_gdelt_events
        result = fetch_gdelt_events.invoke({"regions": ["global"], "themes": ["CONFLICT"], "lookback_minutes": 60})
    assert result == []


def test_fetch_gdelt_events_caps_at_500():
    mock_articles = [
        {"seendate": "20240101", "title": f"Event {i}", "url": f"http://test{i}.com",
         "sourcecountry": "UA", "tone": "-3", "themes": "CONFLICT", "domain": "test.com", "language": "English"}
        for i in range(600)
    ]
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"articles": mock_articles}).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        from tools.gdelt_tool import fetch_gdelt_events
        result = fetch_gdelt_events.invoke({"regions": ["global"], "themes": ["CONFLICT"], "lookback_minutes": 60})

    assert len(result) <= 500
