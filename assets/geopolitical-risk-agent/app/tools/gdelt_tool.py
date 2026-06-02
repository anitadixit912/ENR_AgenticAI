"""GDELT geopolitical event ingestion tool."""
import logging
import urllib.request
import urllib.parse
import json
from langchain.tools import tool

logger = logging.getLogger(__name__)

GDELT_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

CONFLICT_THEMES = [
    "CONFLICT", "MILITARY_ATTACK", "PROTEST", "SANCTION",
    "HOSTILITY", "MILITARY", "CRISISLEX_CRISISLEXREC"
]

REGION_COUNTRY_CODES = {
    "middle_east_africa": ["AE", "SA", "IR", "IQ", "IL", "SY", "YE", "LY", "EG", "NG", "ZA", "KE", "ET", "JO", "LB"],
    "eastern_europe": ["UA", "RU", "BY", "PL", "MD", "RO", "GE", "AM", "AZ"],
    "global": []  # empty means all regions
}


@tool
def fetch_gdelt_events(regions: list, themes: list, lookback_minutes: int = 60) -> list:
    """Fetch and filter geopolitical events from GDELT API v2.
    
    Args:
        regions: List of region keys to monitor (e.g. ['middle_east_africa', 'eastern_europe', 'global'])
        themes: List of CAMEO conflict themes to filter by (e.g. ['CONFLICT', 'MILITARY_ATTACK'])
        lookback_minutes: Number of minutes to look back for events (default: 60)
    
    Returns:
        List of filtered event dicts with fields: event_id, date, headline, url, source_country, tone_score, themes
    """
    try:
        query_themes = themes if themes else CONFLICT_THEMES[:3]
        theme_query = " OR ".join(f'theme:{t}' for t in query_themes[:5])
        
        params = {
            "query": theme_query,
            "mode": "ArtList",
            "maxrecords": "250",
            "format": "json",
            "timespan": f"{lookback_minutes}min"
        }
        url = f"{GDELT_API_URL}?{urllib.parse.urlencode(params)}"
        
        req = urllib.request.Request(url, headers={"User-Agent": "GeopoliticalRiskAgent/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        
        articles = raw.get("articles", [])
        events = []
        for i, article in enumerate(articles[:500]):
            source_country = article.get("sourcecountry", "")
            
            # Filter by region if specific regions requested
            if regions and "global" not in regions:
                allowed_codes = []
                for region_key in regions:
                    allowed_codes.extend(REGION_COUNTRY_CODES.get(region_key, []))
                if source_country and source_country.upper() not in allowed_codes:
                    continue
            
            events.append({
                "event_id": f"gdelt_{i}_{article.get('seendate', '')}",
                "date": article.get("seendate", ""),
                "headline": article.get("title", "")[:500],
                "url": article.get("url", ""),
                "source_country": source_country,
                "tone_score": float(article.get("tone", 0)),
                "themes": article.get("themes", ""),
                "domain": article.get("domain", ""),
                "language": article.get("language", "")
            })
        
        logger.info("M1.achieved: GDELT fetch complete â %d events retrieved, %d passed filters", len(articles), len(events))
        return events

    except Exception as e:
        logger.error("M1.missed: GDELT fetch failed â %s", str(e))
        return []
