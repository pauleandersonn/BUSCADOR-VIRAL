import httpx
import os
import asyncio
from typing import List, Dict

BASE = "https://graph.facebook.com/v19.0"

def _config_error(msg: str) -> List[Dict]:
    return [{"source": "Facebook", "title": f"⚠ {msg}", "url": "https://developers.facebook.com", "score": 0, "comments": 0, "subreddit": "", "thumbnail": "", "_config_needed": True}]

async def search_facebook(niche: str, limit: int = 10) -> List[Dict]:
    token = os.getenv("FACEBOOK_ACCESS_TOKEN", "").strip()
    if not token:
        return _config_error("Configure FACEBOOK_ACCESS_TOKEN no .env (Meta for Developers)")

    results = []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Step 1: get pages managed by the user (works with any user token)
            pages_r = await client.get(
                f"{BASE}/me/accounts",
                params={"fields": "id,name,access_token", "limit": 20, "access_token": token},
            )
            if pages_r.status_code == 401:
                return _config_error("Access Token inválido ou expirado")
            if pages_r.status_code != 200:
                err = pages_r.json().get("error", {}).get("message", "Erro desconhecido")
                return _config_error(err)

            pages = pages_r.json().get("data", [])
            if not pages:
                return []

            # Step 2: fetch recent posts from each page using its own page token
            posts_per_page = max(5, limit)

            async def fetch_page_posts(page: Dict) -> List[Dict]:
                page_id = page["id"]
                page_name = page.get("name", "")
                page_token = page.get("access_token", token)
                try:
                    r = await client.get(
                        f"{BASE}/{page_id}/posts",
                        params={
                            "fields": "message,full_picture,permalink_url,shares",
                            "access_token": page_token,
                            "limit": posts_per_page,
                        },
                    )
                    if r.status_code != 200:
                        return []
                    page_results = []
                    for post in r.json().get("data", []):
                        msg = (post.get("message") or "").strip()
                        if not msg:
                            continue
                        shares = post.get("shares", {}).get("count", 0)
                        page_results.append({
                            "source": "Facebook",
                            "title": msg[:200],
                            "url": post.get("permalink_url", f"https://facebook.com/{page_id}"),
                            "score": shares,
                            "comments": 0,
                            "subreddit": page_name,
                            "thumbnail": post.get("full_picture", ""),
                        })
                    return page_results
                except Exception:
                    return []

            gathered = await asyncio.gather(*[fetch_page_posts(p) for p in pages])
            for page_posts in gathered:
                results.extend(page_posts)

    except Exception:
        pass

    return sorted(results, key=lambda x: x["score"], reverse=True)[:limit]
