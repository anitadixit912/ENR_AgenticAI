"""Unit tests for fetch_news_articles tool."""
import json
import os
import pytest
from unittest.mock import patch, MagicMock


def test_fetch_news_articles_returns_empty_without_api_key(monkeypatch):
    """Should return [] when NEWSAPI_KEY is not set."""
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    from tools.news_tool import fetch_news_articles
    result = fetch_news_articles.invoke({
        "keywords": ["conflict", "sanctions"],
        "regions": ["eastern_europe"],
        "lookback_hours": 6,
    })
    assert result == []


def test_fetch_news_articles_success(monkeypatch):
    """Should return articles when API responds successfully."""
    monkeypatch.setenv("NEWSAPI_KEY", "test-key-abc")
    mock_data = {
        "articles": [
            {
                "title": "Military conflict escalates",
                "url": "https://news.example.com/article1",
                "publishedAt": "2024-03-15T10:30:00Z",
                "source": {"id": "ua", "name": "UA Times"},
                "description": "Ongoing conflict in eastern region.",
            },
            {
                "title": "Sanctions imposed on energy sector",
                "url": "https://news.example.com/article2",
                "publishedAt": "2024-03-15T11:00:00Z",
                "source": {"id": "ru", "name": "RU Report"},
                "description": "New sanctions target oil exports.",
            },
        ]
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_data).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        from tools.news_tool import fetch_news_articles
        result = fetch_news_articles.invoke({
            "keywords": ["conflict", "sanctions"],
            "regions": ["global"],
            "lookback_hours": 6,
        })

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["headline"] == "Military conflict escalates"
    assert result[0]["source"] == "newsapi"
    assert "event_id" in result[0]
    assert "url" in result[0]


def test_fetch_news_articles_handles_api_error(monkeypatch):
    """Should return [] on network error."""
    monkeypatch.setenv("NEWSAPI_KEY", "test-key-abc")
    with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
        from tools.news_tool import fetch_news_articles
        result = fetch_news_articles.invoke({
            "keywords": ["conflict"],
            "regions": ["eastern_europe"],
            "lookback_hours": 6,
        })
    assert result == []


def test_fetch_news_articles_region_filter_global(monkeypatch):
    """Global region should not apply country filter."""
    monkeypatch.setenv("NEWSAPI_KEY", "test-key-abc")
    mock_data = {
        "articles": [
            {
                "title": "US trade tensions rise",
                "url": "https://news.example.com/us1",
                "publishedAt": "2024-03-15T09:00:00Z",
                "source": {"id": "us", "name": "US News"},
                "description": "Trade policy update.",
            },
        ]
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_data).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        from tools.news_tool import fetch_news_articles
        result = fetch_news_articles.invoke({
            "keywords": ["trade", "sanctions"],
            "regions": ["global"],
            "lookback_hours": 12,
        })

    # global region = no country filter, US article should pass
    assert len(result) == 1
    assert result[0]["source_country"] == "US"


def test_fetch_news_articles_required_fields(monkeypatch):
    """Each returned article must have all required fields."""
    monkeypatch.setenv("NEWSAPI_KEY", "test-key-abc")
    mock_data = {
        "articles": [
            {
                "title": "Conflict in Middle East",
                "url": "https://news.example.com/me1",
                "publishedAt": "2024-03-15T08:00:00Z",
                "source": {"id": "ae", "name": "Gulf News"},
                "description": "Tensions rise in the region.",
            }
        ]
    }
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_data).encode()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        from tools.news_tool import fetch_news_articles
        result = fetch_news_articles.invoke({
            "keywords": ["conflict"],
            "regions": ["global"],
            "lookback_hours": 6,
        })

    assert len(result) == 1
    article = result[0]
    required = ["event_id", "headline", "date", "url", "source_country", "tone_score", "themes", "source"]
    for field in required:
        assert field in article, f"Missing required field: {field}"
