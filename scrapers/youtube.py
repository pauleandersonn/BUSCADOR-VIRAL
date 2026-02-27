from youtubesearchpython import VideosSearch
from typing import List, Dict
import asyncio
import math
from datetime import datetime

CURRENT_YEAR = datetime.now().year


def _parse_views(view_count) -> int:
    """Parse viewCount field safely (can be dict, None, or missing)."""
    if not view_count:
        return 0
    text = view_count.get("text", "") if isinstance(view_count, dict) else ""
    if not text:
        return 0
    try:
        return int(text.replace(",", "").replace(".", "").split()[0])
    except Exception:
        return 0


def _log_score(views: int) -> int:
    """Convert raw view count to a log-normalized score (0–10000)."""
    if views <= 0:
        return 0
    return int(math.log10(views + 1) * 1000)


def _is_recent(published_time: str, max_days: int = 30) -> bool:
    """Return True if video was published within max_days days."""
    if not published_time:
        return True
    pt = published_time.lower()
    parts = pt.split()
    if not parts:
        return True
    try:
        n = int(parts[0])
    except ValueError:
        return True
    unit = parts[1].rstrip("s") if len(parts) > 1 else ""
    if unit in ("year", "ano"):
        return False
    if unit in ("month", "mes", "mês"):
        return n <= (max_days // 30)
    if unit in ("week", "semana"):
        return n * 7 <= max_days
    return True  # days/hours/minutes → always recent


def _build_item(video: dict) -> dict:
    views = _parse_views(video.get("viewCount"))
    channel = (video.get("channel") or {}).get("name", "")
    thumbnails = video.get("thumbnails") or []
    thumb = thumbnails[0].get("url", "") if thumbnails else ""
    return {
        "source": "YouTube",
        "title": video.get("title", ""),
        "url": video.get("link", ""),
        "score": _log_score(views),
        "raw_views": views,
        "comments": 0,
        "subreddit": channel,
        "thumbnail": thumb,
        "published_time": video.get("publishedTime", ""),
    }


async def search_youtube(niche: str, limit: int = 10) -> List[Dict]:
    results = []
    # Search original term + current-year term for more recent content
    search_terms = [niche, f"{niche} {CURRENT_YEAR}"]
    seen_urls: set = set()
    loop = asyncio.get_event_loop()

    for term in search_terms:
        try:
            def _search(t=term):
                s = VideosSearch(t, limit=limit)
                return s.result()

            data = await loop.run_in_executor(None, _search)
            for video in data.get("result", []):
                url = video.get("link", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    item = _build_item(video)
                    if item["title"]:
                        results.append(item)
        except Exception:
            continue

    return sorted(results, key=lambda x: x["score"], reverse=True)[:limit]


async def get_trending_youtube(region: str = "US", limit: int = 10, city: str = "") -> List[Dict]:
    """Get trending YouTube videos for a region or specific city.
    Only includes videos published within the last 30 days.
    """
    results = []
    if city:
        # City-specific: search for local viral/news content
        search_terms = [
            f"{city} notícias hoje",
            f"{city} viral {CURRENT_YEAR}",
            f"{city} repercussão",
        ]
    elif region == "BR":
        search_terms = [
            f"viral brasil {CURRENT_YEAR}",
            "tendência brasil hoje",
            "mais assistido brasil",
        ]
    else:
        search_terms = [
            f"trending today {CURRENT_YEAR}",
            "viral video today",
        ]

    seen_urls: set = set()
    loop = asyncio.get_event_loop()

    for term in search_terms:
        try:
            def _search(t=term):
                try:
                    s = VideosSearch(t, limit=limit, language="pt" if region == "BR" else "en", region=region)
                except TypeError:
                    s = VideosSearch(t, limit=limit)
                return s.result()

            data = await loop.run_in_executor(None, _search)
            for video in data.get("result", []):
                url = video.get("link", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    item = _build_item(video)
                    if item["title"] and _is_recent(item["published_time"], max_days=30):
                        results.append(item)
        except Exception:
            continue

    return sorted(results, key=lambda x: x["score"], reverse=True)[:limit]
