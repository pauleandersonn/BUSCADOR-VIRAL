import httpx
import os
from typing import List, Dict

async def search_linkedin(niche: str, limit: int = 10) -> List[Dict]:
    token = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()
    if not token:
        return [{"source": "LinkedIn", "title": "⚠ Configure LINKEDIN_ACCESS_TOKEN no .env (LinkedIn Developer Portal)", "url": "https://developer.linkedin.com", "score": 0, "comments": 0, "subreddit": "", "thumbnail": "", "_config_needed": True}]

    results = []
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://api.linkedin.com/v2/ugcPosts",
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Restli-Protocol-Version": "2.0.0",
                },
                params={"q": "keywords", "keywords": niche, "count": limit},
            )
            if r.status_code == 401:
                return [{"source": "LinkedIn", "title": "⚠ Access Token inválido ou expirado", "url": "https://developer.linkedin.com", "score": 0, "comments": 0, "subreddit": "", "thumbnail": "", "_config_needed": True}]
            if r.status_code != 200:
                return []

            for post in r.json().get("elements", []):
                social = post.get("socialDetail", {})
                likes = social.get("totalSocialActivityCounts", {}).get("numLikes", 0)
                comments = social.get("totalSocialActivityCounts", {}).get("numComments", 0)
                text = post.get("specificContent", {}).get("com.linkedin.ugc.ShareContent", {}).get("shareCommentary", {}).get("text", "")
                post_id = post.get("id", "")
                results.append({
                    "source": "LinkedIn",
                    "title": text[:200] if text else f"Post LinkedIn #{post_id}",
                    "url": f"https://www.linkedin.com/feed/update/{post_id}/",
                    "score": likes,
                    "comments": comments,
                    "subreddit": "",
                    "thumbnail": "",
                })
    except Exception:
        pass

    return sorted(results, key=lambda x: x["score"], reverse=True)
