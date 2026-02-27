import httpx
import os
from typing import List, Dict

async def search_tiktok(niche: str, limit: int = 10) -> List[Dict]:
    client_key = os.getenv("TIKTOK_CLIENT_KEY", "").strip()
    client_secret = os.getenv("TIKTOK_CLIENT_SECRET", "").strip()

    if not client_key or not client_secret:
        return [{"source": "TikTok", "title": "⚠ Configure TIKTOK_CLIENT_KEY e TIKTOK_CLIENT_SECRET no .env (pesquise: TikTok for Developers)", "url": "https://developers.tiktok.com", "score": 0, "comments": 0, "subreddit": "", "thumbnail": "", "_config_needed": True}]

    # Obter access token via Client Credentials
    results = []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            token_r = await client.post(
                "https://open.tiktokapis.com/v2/oauth/token/",
                data={
                    "client_key": client_key,
                    "client_secret": client_secret,
                    "grant_type": "client_credentials",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if token_r.status_code != 200:
                return []

            access_token = token_r.json().get("access_token", "")
            if not access_token:
                return []

            search_r = await client.post(
                "https://open.tiktokapis.com/v2/research/video/query/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "query": {
                        "and": [{"operation": "IN", "field_name": "keyword", "field_values": [niche]}]
                    },
                    "max_count": limit,
                    "fields": "id,title,like_count,comment_count,share_count,view_count,author_name",
                },
            )
            if search_r.status_code != 200:
                return []

            for video in search_r.json().get("data", {}).get("videos", []):
                results.append({
                    "source": "TikTok",
                    "title": video.get("title", f"TikTok por @{video.get('author_name', '')}"),
                    "url": f"https://www.tiktok.com/@{video.get('author_name', '')}/video/{video.get('id', '')}",
                    "score": video.get("view_count", 0),
                    "comments": video.get("comment_count", 0),
                    "subreddit": f"@{video.get('author_name', '')}",
                    "thumbnail": "",
                })
    except Exception:
        pass

    return sorted(results, key=lambda x: x["score"], reverse=True)
