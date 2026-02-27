"""
TikTok scraper via Playwright.
Busca vídeos por palavra-chave. Login opcional (conteúdo público).
"""
import os
import re
from typing import List, Dict

from .pw_base import (
    get_context, save_session, clear_session,
    safe_close, config_needed, log_score,
)


async def search_tiktok(niche: str, limit: int = 10) -> List[Dict]:
    ctx = await get_context("tiktok")
    results = []

    try:
        page = await ctx.new_page()

        # Intercepta respostas de API do TikTok para capturar dados reais
        api_results = []

        async def handle_response(response):
            if "search" in response.url and "tiktok" in response.url:
                try:
                    data = await response.json()
                    items = (
                        data.get("data", []) or
                        data.get("item_list", []) or
                        data.get("aweme_list", [])
                    )
                    for item in items:
                        api_results.append(item)
                except Exception:
                    pass

        page.on("response", handle_response)

        query = niche.replace(" ", "+")
        await page.goto(f"https://www.tiktok.com/search?q={query}", timeout=25000)
        await page.wait_for_timeout(4000)

        # Scroll para carregar mais
        for _ in range(2):
            await page.evaluate("window.scrollBy(0, 1000)")
            await page.wait_for_timeout(1500)

        # Salva sessão
        await save_session(ctx, "tiktok")

        # Tenta dados da API interceptada primeiro
        if api_results:
            for item in api_results[:limit]:
                try:
                    desc = item.get("desc", "") or item.get("title", "") or "Vídeo TikTok"
                    stats = item.get("statistics", item.get("stats", {}))
                    views = int(stats.get("play_count", stats.get("playCount", 0)))
                    likes = int(stats.get("digg_count", stats.get("diggCount", 0)))
                    comments = int(stats.get("comment_count", stats.get("commentCount", 0)))
                    author = (item.get("author", {}) or {}).get("unique_id", "")
                    video_id = item.get("id", item.get("aweme_id", ""))
                    thumb = ((item.get("video", {}) or {}).get("cover", {}) or {}).get("url_list", [""])[0]

                    results.append({
                        "source": "TikTok",
                        "title": desc[:200],
                        "url": f"https://www.tiktok.com/@{author}/video/{video_id}" if author and video_id else "https://www.tiktok.com",
                        "score": log_score(views),
                        "raw_engagement": views,
                        "comments": comments,
                        "subreddit": f"@{author}" if author else "",
                        "thumbnail": thumb,
                    })
                except Exception:
                    continue
        else:
            # Fallback: scraping direto do DOM
            cards = await page.locator('[data-e2e="search_top-item"], [class*="DivItemContainerV2"], a[href*="/video/"]').all()

            for card in cards[:limit * 2]:
                try:
                    href = await card.get_attribute("href") or ""
                    if "/video/" not in href:
                        continue

                    url = href if href.startswith("http") else f"https://www.tiktok.com{href}"
                    author_match = re.search(r'/@([^/]+)/video', url)
                    author = author_match.group(1) if author_match else ""

                    # Texto do card
                    text = await card.inner_text()
                    title = text[:200].strip() or f"Vídeo TikTok @{author}"

                    # Métricas via texto
                    views = _parse_count(text, ["views", "visualizações"])
                    likes = _parse_count(text, ["likes", "curtidas"])
                    comments = _parse_count(text, ["comments", "comentários"])

                    # Thumbnail
                    img = card.locator("img").first
                    thumb = ""
                    try:
                        thumb = await img.get_attribute("src") or ""
                    except Exception:
                        pass

                    if url not in [r["url"] for r in results]:
                        results.append({
                            "source": "TikTok",
                            "title": title,
                            "url": url,
                            "score": log_score(views or likes),
                            "raw_engagement": views or likes,
                            "comments": comments,
                            "subreddit": f"@{author}" if author else "",
                            "thumbnail": thumb,
                        })

                    if len(results) >= limit:
                        break
                except Exception:
                    continue

    except Exception:
        clear_session("tiktok")
    finally:
        await safe_close(ctx)

    return sorted(results, key=lambda x: x["score"], reverse=True)[:limit]


def _parse_count(text: str, keywords: list) -> int:
    import re
    for kw in keywords:
        match = re.search(r'([\d.,]+[KkMm]?)\s*' + kw, text, re.IGNORECASE)
        if match:
            return _human_to_int(match.group(1))
    return 0


def _human_to_int(s: str) -> int:
    s = s.strip().replace(",", ".")
    try:
        if s.lower().endswith("m"):
            return int(float(s[:-1]) * 1_000_000)
        if s.lower().endswith("k"):
            return int(float(s[:-1]) * 1_000)
        return int(float(s))
    except ValueError:
        return 0
