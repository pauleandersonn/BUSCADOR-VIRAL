"""
Twitter/X scraper via Playwright.
Busca tweets recentes por nicho. Login necessário para métricas.
"""
import os
import re
from typing import List, Dict

from .pw_base import (
    get_context, save_session, clear_session,
    safe_close, config_needed, log_score, is_login_page,
)


async def search_twitter(niche: str, limit: int = 10) -> List[Dict]:
    email = os.getenv("TWITTER_EMAIL", "").strip()
    password = os.getenv("TWITTER_PASSWORD", "").strip()

    if not email or not password:
        return [config_needed(
            "Twitter/X",
            "Configure TWITTER_EMAIL e TWITTER_PASSWORD na página de configuração",
            "http://187.77.43.189:8090/config.html",
        )]

    ctx = await get_context("twitter")
    results = []

    try:
        page = await ctx.new_page()
        query = niche.replace(" ", "%20")

        await page.goto(f"https://x.com/search?q={query}&f=live&src=typed_query", timeout=25000)
        await page.wait_for_timeout(3000)

        # Verifica login
        if is_login_page(page.url, ["login", "i/flow/login"]):
            await _do_login(page, email, password)
            await page.goto(f"https://x.com/search?q={query}&f=live&src=typed_query", timeout=25000)
            await page.wait_for_timeout(3000)

        await save_session(ctx, "twitter")

        # Scroll para carregar tweets
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, 1500)")
            await page.wait_for_timeout(1500)

        # Coleta tweets
        tweets = await page.locator('article[data-testid="tweet"]').all()

        for tweet in tweets[:limit * 2]:
            try:
                # Texto do tweet
                text_el = tweet.locator('[data-testid="tweetText"]').first
                text = await text_el.inner_text() if await text_el.count() > 0 else ""
                if not text:
                    continue

                # URL do tweet
                time_link = tweet.locator("time").locator("..").first
                href = await time_link.get_attribute("href") or ""
                url = f"https://x.com{href}" if href.startswith("/") else href or "https://x.com"

                # Autor
                author_el = tweet.locator('[data-testid="User-Name"]').first
                author = ""
                try:
                    author_text = await author_el.inner_text()
                    match = re.search(r'@(\w+)', author_text)
                    author = match.group(1) if match else ""
                except Exception:
                    pass

                # Métricas
                likes = await _get_metric(tweet, "like")
                replies = await _get_metric(tweet, "reply")
                retweets = await _get_metric(tweet, "retweet")
                raw = likes + retweets * 2

                # Thumbnail
                thumb = ""
                try:
                    img = tweet.locator('img[src*="pbs.twimg.com/media"]').first
                    if await img.count() > 0:
                        thumb = await img.get_attribute("src") or ""
                except Exception:
                    pass

                if url and url not in [r["url"] for r in results]:
                    results.append({
                        "source": "Twitter/X",
                        "title": text[:200],
                        "url": url,
                        "score": log_score(raw),
                        "raw_engagement": raw,
                        "comments": replies,
                        "subreddit": f"@{author}" if author else "",
                        "thumbnail": thumb,
                    })

                if len(results) >= limit:
                    break
            except Exception:
                continue

    except Exception:
        clear_session("twitter")
    finally:
        await safe_close(ctx)

    return sorted(results, key=lambda x: x["score"], reverse=True)


async def _do_login(page, email: str, password: str):
    try:
        await page.goto("https://x.com/i/flow/login", timeout=20000)
        await page.wait_for_timeout(2000)

        # Email/usuário
        await page.fill('input[autocomplete="username"]', email)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(2000)

        # Às vezes pede usuário adicional
        unusual = page.locator('input[data-testid="ocfEnterTextTextInput"]')
        if await unusual.count() > 0:
            username = email.split("@")[0]
            await unusual.fill(username)
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(2000)

        # Senha
        await page.fill('input[name="password"]', password)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(4000)
    except Exception:
        pass


async def _get_metric(tweet, metric_name: str) -> int:
    try:
        el = tweet.locator(f'[data-testid="{metric_name}"]').first
        if await el.count() == 0:
            return 0
        aria = await el.get_attribute("aria-label") or ""
        match = re.search(r'(\d[\d,.]*)', aria)
        if match:
            return int(match.group(1).replace(",", "").replace(".", ""))
        return 0
    except Exception:
        return 0
