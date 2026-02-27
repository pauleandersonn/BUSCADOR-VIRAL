import httpx
import math
from typing import List, Dict

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; viral-search-bot/1.1)"
}

# Subreddits brasileiros relevantes por categoria de nicho
BRAZILIAN_SUBREDDITS = {
    "futebol": ["futebol", "brasil"],
    "tecnologia": ["brdev", "brasil", "programação"],
    "programacao": ["brdev", "programação"],
    "política": ["brasil", "geopolitica"],
    "economia": ["brasil", "investimentos", "financaspessoais"],
    "investimentos": ["investimentos", "financaspessoais", "brasil"],
    "saude": ["brasil", "medicina"],
    "fitness": ["fitness", "brasil"],
    "games": ["gamesEcultura", "brasil"],
    "entretenimento": ["brasil", "huestation"],
    "humor": ["huestation", "brasil"],
    "noticias": ["brasil", "worldnews"],
    "musica": ["brasil", "musica"],
}


def _niche_subreddits(niche: str) -> List[str]:
    """Return relevant subreddits for the given niche."""
    niche_lower = niche.lower()
    for keyword, subs in BRAZILIAN_SUBREDDITS.items():
        if keyword in niche_lower:
            return subs
    return ["all", "popular", "brasil"]


def _log_score(upvotes: int) -> int:
    """Normalize Reddit upvotes to log scale (0–10000) to match YouTube."""
    if upvotes <= 0:
        return 0
    return int(math.log10(upvotes + 1) * 1000)


async def search_reddit(niche: str, limit: int = 10) -> List[Dict]:
    results = []
    subreddits = _niche_subreddits(niche)
    # Also always include r/all for global reach
    if "all" not in subreddits:
        subreddits = subreddits + ["all"]

    per_sub = max(5, limit)

    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
        for sub in subreddits:
            try:
                url = f"https://www.reddit.com/r/{sub}/search.json"
                params = {
                    "q": niche,
                    "sort": "top",
                    "t": "week",
                    "limit": per_sub,
                    "restrict_sr": False,
                }
                r = await client.get(url, params=params)
                if r.status_code != 200:
                    continue
                data = r.json()
                for post in data.get("data", {}).get("children", []):
                    p = post["data"]
                    raw_score = p.get("score", 0)
                    results.append({
                        "source": "Reddit",
                        "title": p.get("title", ""),
                        "url": f"https://reddit.com{p.get('permalink', '')}",
                        "score": _log_score(raw_score),
                        "raw_upvotes": raw_score,
                        "comments": p.get("num_comments", 0),
                        "subreddit": p.get("subreddit", ""),
                        "thumbnail": p.get("thumbnail", "") if p.get("thumbnail", "").startswith("http") else "",
                    })
            except Exception:
                continue

    seen = set()
    unique = []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)

    return sorted(unique, key=lambda x: x["score"], reverse=True)[:limit]


async def get_trending_reddit(subreddits: List[str], limit: int = 15) -> List[Dict]:
    """Get top posts from specific subreddits (for Mundo/País/Cidades trending sections)."""
    results = []
    per_sub = max(5, limit // max(1, len(subreddits)))

    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
        for sub in subreddits:
            try:
                url = f"https://www.reddit.com/r/{sub}/top.json"
                params = {"t": "day", "limit": per_sub}
                r = await client.get(url, params=params)
                if r.status_code != 200:
                    continue
                data = r.json()
                for post in data.get("data", {}).get("children", []):
                    p = post["data"]
                    raw_score = p.get("score", 0)
                    results.append({
                        "source": "Reddit",
                        "title": p.get("title", ""),
                        "url": f"https://reddit.com{p.get('permalink', '')}",
                        "score": _log_score(raw_score),
                        "raw_upvotes": raw_score,
                        "comments": p.get("num_comments", 0),
                        "subreddit": p.get("subreddit", ""),
                        "thumbnail": p.get("thumbnail", "") if p.get("thumbnail", "").startswith("http") else "",
                    })
            except Exception:
                continue

    seen = set()
    unique = []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)

    return sorted(unique, key=lambda x: x["score"], reverse=True)
