"""Google News RSS scraper — regional news without API key."""
import httpx
import math
import xml.etree.ElementTree as ET
from typing import List, Dict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; viral-search-bot/1.1)",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.5",
}


def _recency_score(pub_date_str: str) -> int:
    """Score 0–5000 based on how recent the article is.
    Most recent = 5000, 7+ days old = 500.
    """
    try:
        dt = parsedate_to_datetime(pub_date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        age_hours = (now - dt).total_seconds() / 3600
        if age_hours < 1:
            return 5000
        if age_hours < 6:
            return 4500
        if age_hours < 24:
            return 4000
        if age_hours < 48:
            return 3500
        if age_hours < 72:
            return 3000
        if age_hours < 120:
            return 2500
        if age_hours < 168:
            return 2000
        return 500
    except Exception:
        return 1000


async def get_city_news(city: str, state: str = "BR", limit: int = 10) -> List[Dict]:
    """Fetch recent news articles about a city from Google News RSS."""
    # Build search queries: city name + state to avoid wrong cities
    queries = [
        f"{city}",
        f"{city} {state} notícias",
    ]
    results = []
    seen_urls: set = set()

    async with httpx.AsyncClient(headers=HEADERS, timeout=12, follow_redirects=True) as client:
        for q in queries:
            try:
                url = "https://news.google.com/rss/search"
                params = {
                    "q": q,
                    "hl": "pt-BR",
                    "gl": "BR",
                    "ceid": "BR:pt-419",
                }
                r = await client.get(url, params=params)
                if r.status_code != 200:
                    continue

                root = ET.fromstring(r.text)
                ns = {"media": "http://search.yahoo.com/mrss/"}
                channel = root.find("channel")
                if channel is None:
                    continue

                for item in channel.findall("item")[:limit]:
                    title_el = item.find("title")
                    link_el = item.find("link")
                    pub_el = item.find("pubDate")
                    source_el = item.find("source")

                    title = title_el.text if title_el is not None else ""
                    link = link_el.text if link_el is not None else ""
                    pub_date = pub_el.text if pub_el is not None else ""
                    outlet = source_el.text if source_el is not None else "Notícias"

                    if not title or not link or link in seen_urls:
                        continue
                    # Filter: only keep articles that mention the city name
                    if city.lower() not in title.lower() and q == queries[0]:
                        # First pass: skip if city not in title (second query is already filtered)
                        pass

                    seen_urls.add(link)
                    score = _recency_score(pub_date)
                    results.append({
                        "source": "Notícias",
                        "title": title,
                        "url": link,
                        "score": score,
                        "raw_recency_score": score,
                        "comments": 0,
                        "subreddit": outlet,
                        "thumbnail": "",
                        "pub_date": pub_date,
                    })
            except Exception:
                continue

    # Deduplicate and sort by recency
    seen2: set = set()
    unique = []
    for r in results:
        if r["url"] not in seen2:
            seen2.add(r["url"])
            unique.append(r)

    return sorted(unique, key=lambda x: x["score"], reverse=True)[:limit]


async def search_news(niche: str, limit: int = 10) -> List[Dict]:
    """Search Google News RSS for a niche/topic."""
    results = []
    seen_urls: set = set()

    async with httpx.AsyncClient(headers=HEADERS, timeout=12, follow_redirects=True) as client:
        try:
            url = "https://news.google.com/rss/search"
            params = {
                "q": niche,
                "hl": "pt-BR",
                "gl": "BR",
                "ceid": "BR:pt-419",
            }
            r = await client.get(url, params=params)
            if r.status_code != 200:
                return []

            root = ET.fromstring(r.text)
            channel = root.find("channel")
            if channel is None:
                return []

            for item in channel.findall("item")[:limit]:
                title_el = item.find("title")
                link_el = item.find("link")
                pub_el = item.find("pubDate")
                source_el = item.find("source")

                title = title_el.text if title_el is not None else ""
                link = link_el.text if link_el is not None else ""
                pub_date = pub_el.text if pub_el is not None else ""
                outlet = source_el.text if source_el is not None else "Notícias"

                if not title or not link or link in seen_urls:
                    continue

                seen_urls.add(link)
                score = _recency_score(pub_date)
                results.append({
                    "source": "Notícias",
                    "title": title,
                    "url": link,
                    "score": score,
                    "raw_recency_score": score,
                    "comments": 0,
                    "subreddit": outlet,
                    "thumbnail": "",
                    "pub_date": pub_date,
                })
        except Exception:
            pass

    return sorted(results, key=lambda x: x["score"], reverse=True)[:limit]
