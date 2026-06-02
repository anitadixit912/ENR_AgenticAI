"""NewsAPI tool â fetches recent news articles for given keywords and regions."""
import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from langchain.tools import tool

logger = logging.getLogger(__name__)

# Country codes per region (matches gdelt_tool.py regions)
REGION_COUNTRIES: dict[str, list[str]] = {
    "middle_east_africa": ["SA", "AE", "IL", "IR", "IQ", "SY", "YE", "LB", "EG", "ZA", "NG", "ET", "KE"],
    "eastern_europe":     ["UA", "RU", "PL", "RO", "CZ", "HU", "BY", "MD", "GE", "AM", "AZ"],
    "asia_pacific":       ["CN", "JP", "KR", "IN", "PK", "AF", "MM", "TH", "VN", "ID", "PH"],
    "global":             [],  # empty = no country filter
}

NEWSAPI_BASE = "https://newsapi.org/v2/everything"


def _build_url(keywords: list[str], from_dt: str, api_key: str) -> str:
    q = " OR ".join(f'"{kw}"' for kw in keywords[:5])
    params = urllib.parse.urlencode({
        "q": q,
        "from": from_dt,
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": 100,
        "apiKey": api_key,
    })
    return f"{NEWSAPI_BASE}?{params}"


@tool
def fetch_news_articles(
    keywords: list[str],
    regions: list[str],
    lookback_hours: int = 6,
) -> list[dict]:
    """Fetch recent news articles from NewsAPI for given keywords and regions.

    Args:
        keywords: Search keywords, e.g. ["conflict", "sanctions", "military"]
        regions: Region filters from REGION_COUNTRIES keys, e.g. ["eastern_europe"]
        lookback_hours: How many hours back to search (default 6)

    Returns:
        List of article dicts with keys: event_id, headline, date, url,
        source_country, tone_score, themes, source
    """
    import urllib.parse  # noqa: PLC0415

    api_key = os.environ.get("NEWSAPI_KEY", "").strip()
    if not api_key:
        logger.warning(
            "NEWSAPI_KEY is not set â skipping NewsAPI fetch. "
            "Set NEWSAPI_KEY in .env to enable real news ingestion."
        )
        return []

    from_dt = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    # Collect allowed country codes for the requested regions
    allowed_countries: set[str] = set()
    global_requested = False
    for region in regions:
        codes = REGION_COUNTRIES.get(region, [])
        if not codes:
            global_requested = True  # "global" means no country filter
        else:
            allowed_countries.update(codes)

    try:
        url = _build_url(keywords, from_dt, api_key)
        req = urllib.request.Request(url, headers={"User-Agent": "geopolitical-risk-agent/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        logger.warning("NewsAPI fetch failed: %s", exc)
        return []

    articles = data.get("articles") or []
    results: list[dict] = []

    for idx, art in enumerate(articles[:200]):
        source_country = (art.get("source", {}).get("id") or "").upper()[:2]

        # Apply region filter unless "global" was requested
        if not global_requested and allowed_countries and source_country not in allowed_countries:
            continue

        results.append({
            "event_id":      f"news_{idx:04d}_{abs(hash(art.get('url', str(idx)))) % 100000:05d}",
            "headline":      (art.get("title") or "")[:300],
            "date":          (art.get("publishedAt") or "")[:10],
            "url":           art.get("url", ""),
            "source_country": source_country,
            "tone_score":    0.0,  # NewsAPI doesn't provide tone; default neutral
            "themes":        " ".join(kw.upper() for kw in keywords),
            "source":        "newsapi",
        })

    logger.info("NewsAPI: fetched %d articles (after region filter: %d)", len(articles), len(results))
    return results
