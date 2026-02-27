import httpx
import os
from typing import List, Dict

async def search_instagram(niche: str, limit: int = 10) -> List[Dict]:
    token = os.getenv("FACEBOOK_ACCESS_TOKEN", "").strip()
    if not token:
        return [{"source": "Instagram", "title": "⚠ Configure FACEBOOK_ACCESS_TOKEN no .env (mesmo token do Facebook/Meta)", "url": "https://developers.facebook.com", "score": 0, "comments": 0, "subreddit": "", "thumbnail": "", "_config_needed": True}]

    results = []
    tag = niche.replace(" ", "").lower()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Buscar hashtag ID
            r = await client.get(
                "https://graph.facebook.com/v19.0/ig_hashtag_search",
                params={"user_id": "me", "q": tag, "access_token": token},
            )
            if r.status_code != 200:
                return []

            hashtag_id = r.json().get("data", [{}])[0].get("id", "")
            if not hashtag_id:
                return []

            # Buscar posts da hashtag
            posts_r = await client.get(
                f"https://graph.facebook.com/v19.0/{hashtag_id}/top_media",
                params={
                    "fields": "id,caption,like_count,comments_count,media_url,permalink",
                    "access_token": token,
                    "limit": limit,
                },
            )
            if posts_r.status_code != 200:
                return []

            for post in posts_r.json().get("data", []):
                results.append({
                    "source": "Instagram",
                    "title": (post.get("caption", "") or f"Post #{post.get('id', '')}")[:200],
                    "url": post.get("permalink", "https://instagram.com"),
                    "score": post.get("like_count", 0),
                    "comments": post.get("comments_count", 0),
                    "subreddit": f"#{tag}",
                    "thumbnail": post.get("media_url", ""),
                })
    except Exception:
        pass

    return sorted(results, key=lambda x: x["score"], reverse=True)
