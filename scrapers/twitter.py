import httpx
import math
import os
from typing import List, Dict


def _log_score(raw: int) -> int:
    if raw <= 0:
        return 0
    return int(math.log10(raw + 1) * 1000)

async def search_twitter(niche: str, limit: int = 10) -> List[Dict]:
    token = os.getenv("TWITTER_BEARER_TOKEN", "").strip()
    if not token:
        return [{"source": "Twitter/X", "title": "⚠ Configure TWITTER_BEARER_TOKEN no .env", "url": "https://developer.twitter.com", "score": 0, "comments": 0, "subreddit": "", "thumbnail": "", "_config_needed": True}]

    results = []
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "query": f"{niche} -is:retweet lang:pt OR lang:en",
        "max_results": min(limit, 10),
        "tweet.fields": "public_metrics,author_id,created_at",
        "expansions": "author_id",
        "user.fields": "username,name",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://api.twitter.com/2/tweets/search/recent", headers=headers, params=params)
            if r.status_code == 401:
                return [{"source": "Twitter/X", "title": "⚠ Bearer Token inválido", "url": "https://developer.twitter.com", "score": 0, "comments": 0, "subreddit": "", "thumbnail": "", "_config_needed": True}]
            if r.status_code != 200:
                return []

            data = r.json()
            users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}

            for tweet in data.get("data", []):
                metrics = tweet.get("public_metrics", {})
                raw = metrics.get("like_count", 0) + metrics.get("retweet_count", 0) * 2
                score = _log_score(raw)
                user = users.get(tweet.get("author_id", ""), {})
                username = user.get("username", "")
                results.append({
                    "source": "Twitter/X",
                    "title": tweet.get("text", "")[:200],
                    "url": f"https://twitter.com/{username}/status/{tweet['id']}" if username else f"https://twitter.com/i/web/status/{tweet['id']}",
                    "score": score,
                    "comments": metrics.get("reply_count", 0),
                    "subreddit": f"@{username}" if username else "",
                    "thumbnail": "",
                })
    except Exception:
        pass

    return sorted(results, key=lambda x: x["score"], reverse=True)
