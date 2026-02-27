"""
LinkedIn scraper via Playwright.
Busca posts públicos por palavra-chave.
"""
import os
import re
from typing import List, Dict

from .pw_base import (
    get_context, save_session, clear_session,
    safe_close, config_needed, log_score, is_login_page,
)


async def search_linkedin(niche: str, limit: int = 10) -> List[Dict]:
    email = os.getenv("LINKEDIN_EMAIL", "").strip()
    password = os.getenv("LINKEDIN_PASSWORD", "").strip()

    if not email or not password:
        return [config_needed(
            "LinkedIn",
            "Configure LINKEDIN_EMAIL e LINKEDIN_PASSWORD na página de configuração",
            "http://187.77.43.189:8090/config.html",
        )]

    ctx = await get_context("linkedin")
    results = []

    try:
        page = await ctx.new_page()
        query = niche.replace(" ", "%20")

        await page.goto(
            f"https://www.linkedin.com/search/results/content/?keywords={query}&sortBy=date_posted",
            timeout=25000,
        )
        await page.wait_for_timeout(3000)

        # Verifica login
        if is_login_page(page.url, ["login", "authwall", "checkpoint"]):
            await _do_login(page, email, password)
            await page.goto(
                f"https://www.linkedin.com/search/results/content/?keywords={query}&sortBy=date_posted",
                timeout=25000,
            )
            await page.wait_for_timeout(3000)

        await save_session(ctx, "linkedin")

        # Scroll para carregar posts
        for _ in range(2):
            await page.evaluate("window.scrollBy(0, 1500)")
            await page.wait_for_timeout(1500)

        # Coleta posts
        posts = await page.locator('.search-results-container .reusable-search__result-container').all()
        if not posts:
            # Seletor alternativo
            posts = await page.locator('[data-view-name="search-entity-result-universal-template"]').all()

        for post in posts[:limit * 2]:
            try:
                # Texto do post
                text_el = post.locator('.feed-shared-update-v2__description, .update-components-text').first
                text = ""
                try:
                    text = await text_el.inner_text()
                except Exception:
                    pass

                if not text:
                    text_el = post.locator('span[dir="ltr"]').first
                    try:
                        text = await text_el.inner_text()
                    except Exception:
                        pass

                if not text:
                    continue

                # URL do post
                url = ""
                link = post.locator('a[href*="/feed/update/"]').first
                try:
                    href = await link.get_attribute("href") or ""
                    url = href if href.startswith("http") else f"https://www.linkedin.com{href}"
                except Exception:
                    url = f"https://www.linkedin.com/search/results/content/?keywords={query}"

                # Autor
                author = ""
                author_el = post.locator('.app-aware-link .feed-shared-actor__name, .update-components-actor__name').first
                try:
                    author = await author_el.inner_text()
                except Exception:
                    pass

                # Métricas (reações)
                reactions = 0
                comments = 0
                social_el = post.locator('.social-details-social-counts').first
                try:
                    social_text = await social_el.inner_text()
                    r_match = re.search(r'([\d.,]+[KkMm]?)\s*(reações|reactions|likes)', social_text, re.IGNORECASE)
                    c_match = re.search(r'([\d.,]+[KkMm]?)\s*(comentários|comments)', social_text, re.IGNORECASE)
                    if r_match:
                        reactions = _human_to_int(r_match.group(1))
                    if c_match:
                        comments = _human_to_int(c_match.group(1))
                except Exception:
                    pass

                # Thumbnail
                thumb = ""
                try:
                    img = post.locator('img.ivm-view-attr__img--centered').first
                    if await img.count() > 0:
                        thumb = await img.get_attribute("src") or ""
                except Exception:
                    pass

                results.append({
                    "source": "LinkedIn",
                    "title": text[:200],
                    "url": url,
                    "score": log_score(reactions),
                    "raw_engagement": reactions,
                    "comments": comments,
                    "subreddit": author[:50] if author else "",
                    "thumbnail": thumb,
                })

                if len(results) >= limit:
                    break
            except Exception:
                continue

    except Exception:
        clear_session("linkedin")
    finally:
        await safe_close(ctx)

    return sorted(results, key=lambda x: x["score"], reverse=True)


async def _do_login(page, email: str, password: str):
    try:
        await page.goto("https://www.linkedin.com/login", timeout=20000)
        await page.wait_for_timeout(2000)
        await page.fill('input#username', email)
        await page.fill('input#password', password)
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(4000)
    except Exception:
        pass


def _human_to_int(s: str) -> int:
    s = str(s).strip().replace(",", ".")
    try:
        if s.lower().endswith("m"):
            return int(float(s[:-1]) * 1_000_000)
        if s.lower().endswith("k"):
            return int(float(s[:-1]) * 1_000)
        return int(float(s))
    except ValueError:
        return 0
