import httpx
from typing import List, Dict


async def search_hackernews(niche: str, limit: int = 10) -> List[Dict]:
    results = []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            url = "https://hn.algolia.com/api/v1/search"
            params = {
                "query": niche,
                "tags": "story",
                "hitsPerPage": limit,
                "numericFilters": "points>10"
            }
            r = await client.get(url, params=params)
            if r.status_code != 200:
                return []
            data = r.json()
            for hit in data.get("hits", []):
                results.append({
                    "source": "HackerNews",
                    "title": hit.get("title", ""),
                    "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                    "score": hit.get("points", 0),
                    "comments": hit.get("num_comments", 0),
                    "subreddit": "",
                    "thumbnail": "",
                })
    except Exception:
        pass

    return sorted(results, key=lambda x: x["score"], reverse=True)


async def get_top_hackernews(limit: int = 10) -> List[Dict]:
    """Get top HackerNews front-page stories (no niche needed)."""
    results = []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            url = "https://hn.algolia.com/api/v1/search"
            params = {
                "tags": "story,front_page",
                "hitsPerPage": limit,
            }
            r = await client.get(url, params=params)
            if r.status_code != 200:
                return []
            data = r.json()
            for hit in data.get("hits", []):
                results.append({
                    "source": "HackerNews",
                    "title": hit.get("title", ""),
                    "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                    "score": hit.get("points", 0),
                    "comments": hit.get("num_comments", 0),
                    "subreddit": "",
                    "thumbnail": "",
                })
    except Exception:
        pass

    return sorted(results, key=lambda x: x["score"], reverse=True)
