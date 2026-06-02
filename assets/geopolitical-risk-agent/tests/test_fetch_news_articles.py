"""Unit tests for fetch_news_articles tool."""
import json
import os
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO


def _make_response(data: dict, status: int = 200):
    """Build a mock urllib response context-manager."""
    body = json.dumps(data).encode()
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


# ── helpers ──────────────────────────────────────────────────────────────────

SAMPLE_ARTICLES = [
    {
        "title": "Military conflict in Ukraine escalates",
        "description": "Heavy fighting reported near Kharkiv",
        "url": "https://news.test/article1",
        "publishedAt": "2024-01-15T10:00:00Z",
        "source": {"id": "ua", "name": "UA News"},
    },
    {
        "title": "Sanctions imposed on Russian energy sector",
        "description": "New US sanctions target oil exports",
        "url": "https://news.test/article2",
        "publishedAt": "2024-01-15T11:00:00Z",
        "source": {"id": "us", "name": "Reuters"},
    },
]


# ── tests ─────────────────────────────────────────────────────────────────────


def test_fetch_news_no_api_key(caplog):
    """Returns empty list when NEWSAPI_KEY is not set."""
    import logging
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("NEWSAPI_KEY", None)
        from tools.news_tool import fetch_news_articles
        with caplog.at_level(logging.WARNING):
            result = fetch_news_articles.invoke({
                "keywords": ["conflict"],
                "regions": ["eastern_europe"],
                "lookback_hours": 6,
            })
    assert result == []
    assert "NEWSAPI_KEY" in caplog.text


def test_fetch_news_returns_articles():
    """Returns formatted articles when API responds successfully."""
    api_resp = {"status": "ok", "totalResults": 2, "articles": SAMPLE_ARTICLES}
    mock_resp = _make_response(api_resp)

    with patch.dict(os.environ, {"NEWSAPI_KEY": "test-key-123"}):
        with patch("urllib.request.urlopen", return_value=mock_resp):
            from tools.news_tool import fetch_news_articles
            result = fetch_news_articles.invoke({
                "keywords": ["conflict", "sanctions"],
                "regions": ["eastern_europe", "global"],
                "lookback_hours": 6,
            })

    # With "global" in regions, all articles pass the country filter
    assert isinstance(result, list)
    for item in result:
        assert "event_id" in item
        assert "headline" in item
        assert "url" in item
        assert "date" in item
        assert "source_country" in item
        assert "tone_score" in item
        assert item["tone_score"] == 0.0
        assert item.get("source") == "newsapi"


def test_fetch_news_region_filter_applied():
    """Articles from unrelated regions are filtered out when no 'global' in regions."""
    articles = [
        {
            "title": "Conflict in Ukraine",
            "url": "https://news.test/a1",
            "publishedAt": "2024-01-15T10:00:00Z",
            "source": {"id": "ua", "name": "UA News"},
        },
        {
            "title": "Event in Japan",
            "url": "https://news.test/a2",
            "publishedAt": "2024-01-15T11:00:00Z",
            "source": {"id": "jp", "name": "JP News"},
        },
    ]
    api_resp = {"status": "ok", "articles": articles}
    mock_resp = _make_response(api_resp)

    with patch.dict(os.environ, {"NEWSAPI_KEY": "test-key-123"}):
        with patch("urllib.request.urlopen", return_value=mock_resp):
            from tools.news_tool import fetch_news_articles
            result = fetch_news_articles.invoke({
                "keywords": ["conflict"],
                "regions": ["eastern_europe"],  # UA in, JP out
                "lookback_hours": 6,
            })

    # Only UA article should pass eastern_europe filter
    urls = [r["url"] for r in result]
    assert "https://news.test/a1" in urls
    assert "https://news.test/a2" not in urls


def test_fetch_news_global_skips_filter():
    """When 'global' is in regions, all articles are returned regardless of country."""
    articles = [
        {"title": "Event A", "url": "https://news.test/a", "publishedAt": "2024-01-15T10:00:00Z",
         "source": {"id": "jp", "name": "JP News"}},
        {"title": "Event B", "url": "https://news.test/b", "publishedAt": "2024-01-15T11:00:00Z",
         "source": {"id": "br", "name": "BR News"}},
    ]
    api_resp = {"status": "ok", "articles": articles}
    mock_resp = _make_response(api_resp)

    with patch.dict(os.environ, {"NEWSAPI_KEY": "test-key-123"}):
        with patch("urllib.request.urlopen", return_value=mock_resp):
            from tools.news_tool import fetch_news_articles
            result = fetch_news_articles.invoke({
                "keywords": ["conflict"],
                "regions": ["global"],
                "lookback_hours": 6,
            })

    assert len(result) == 2


def test_fetch_news_network_error_returns_empty(caplog):
    """Returns empty list gracefully when network request fails."""
    import logging
    with patch.dict(os.environ, {"NEWSAPI_KEY": "test-key-123"}):
        with patch("urllib.request.urlopen", side_effect=Exception("connection refused")):
            from tools.news_tool import fetch_news_articles
            with caplog.at_level(logging.WARNING):
                result = fetch_news_articles.invoke({
                    "keywords": ["conflict"],
                    "regions": ["eastern_europe"],
                    "lookback_hours": 6,
                })

    assert result == []


def test_fetch_news_empty_articles_key():
    """Handles API response that returns null/missing articles key."""
    api_resp = {"status": "ok", "articles": None}
    mock_resp = _make_response(api_resp)

    with patch.dict(os.environ, {"NEWSAPI_KEY": "test-key-123"}):
        with patch("urllib.request.urlopen", return_value=mock_resp):
            from tools.news_tool import fetch_news_articles
            result = fetch_news_articles.invoke({
                "keywords": ["conflict"],
                "regions": ["global"],
                "lookback_hours": 1,
            })

    assert result == []


def test_fetch_news_default_lookback():
    """Tool can be invoked without lookback_hours using default value."""
    api_resp = {"status": "ok", "articles": SAMPLE_ARTICLES}
    mock_resp = _make_response(api_resp)

    with patch.dict(os.environ, {"NEWSAPI_KEY": "test-key-123"}):
        with patch("urllib.request.urlopen", return_value=mock_resp):
            from tools.news_tool import fetch_news_articles
            result = fetch_news_articles.invoke({
                "keywords": ["military"],
                "regions": ["global"],
            })
    assert isinstance(result, list)
