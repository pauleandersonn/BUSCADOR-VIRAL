"""
Instagram scraper via Playwright.
Busca posts por hashtag do nicho.
"""
import os
from typing import List, Dict

from .pw_base import (
    get_context, save_session, clear_session,
    safe_close, config_needed, log_score, is_login_page,
)


async def search_instagram(niche: str, limit: int = 10) -> List[Dict]:
    email = os.getenv("INSTAGRAM_EMAIL", "").strip()
    password = os.getenv("INSTAGRAM_PASSWORD", "").strip()

    if not email or not password:
        return [config_needed(
            "Instagram",
            "Configure INSTAGRAM_EMAIL e INSTAGRAM_PASSWORD na página de configuração",
            "http://187.77.43.189:8090/config.html",
        )]

    ctx = await get_context("instagram")
    results = []

    try:
        page = await ctx.new_page()
        hashtag = niche.replace(" ", "").lower()

        # Vai direto para a hashtag
        await page.goto(f"https://www.instagram.com/explore/tags/{hashtag}/", timeout=20000)
        await page.wait_for_timeout(3000)

        # Verifica se está na página de login
        if is_login_page(page.url, ["login", "accounts/login"]):
            await _do_login(page, email, password)
            await page.goto(f"https://www.instagram.com/explore/tags/{hashtag}/", timeout=20000)
            await page.wait_for_timeout(3000)

        # Fecha popups
        for selector in ['[aria-label="Fechar"]', '[aria-label="Close"]', 'button:has-text("Agora não")', 'button:has-text("Not Now")']:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(500)
            except Exception:
                pass

        # Salva sessão após login bem-sucedido
        await save_session(ctx, "instagram")

        # Coleta posts
        posts = await page.locator("article a[href*='/p/']").all()
        seen_urls = set()

        for post in posts[:limit * 2]:
            try:
                href = await post.get_attribute("href")
                if not href or href in seen_urls:
                    continue
                seen_urls.add(href)

                url = f"https://www.instagram.com{href}" if href.startswith("/") else href

                # Tenta extrair métricas do aria-label
                label = await post.get_attribute("aria-label") or ""
                likes = _parse_metric(label, ["curtidas", "likes", "gosto"])
                comments = _parse_metric(label, ["comentários", "comments"])

                # Tenta pegar imagem
                img = post.locator("img").first
                thumb = ""
                try:
                    thumb = await img.get_attribute("src") or ""
                    caption = await img.get_attribute("alt") or f"Post Instagram #{hashtag}"
                except Exception:
                    caption = f"Post Instagram #{hashtag}"

                results.append({
                    "source": "Instagram",
                    "title": caption[:200],
                    "url": url,
                    "score": log_score(likes),
                    "raw_engagement": likes,
                    "comments": comments,
                    "subreddit": f"#{hashtag}",
                    "thumbnail": thumb,
                })

                if len(results) >= limit:
                    break
            except Exception:
                continue

    except Exception:
        clear_session("instagram")
    finally:
        await safe_close(ctx)

    return sorted(results, key=lambda x: x["score"], reverse=True)


async def _do_login(page, email: str, password: str):
    try:
        await page.goto("https://www.instagram.com/accounts/login/", timeout=20000)
        await page.wait_for_timeout(2000)
        await page.fill('input[name="username"]', email)
        await page.fill('input[name="password"]', password)
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(4000)
        # Fecha "Salvar informações de login?"
        for sel in ['button:has-text("Agora não")', 'button:has-text("Not Now")', 'button:has-text("Save Info")']:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(1000)
            except Exception:
                pass
    except Exception:
        pass


def _parse_metric(text: str, keywords: list) -> int:
    import re
    text_lower = text.lower()
    for kw in keywords:
        if kw in text_lower:
            # Procura número antes da palavra-chave
            match = re.search(r'([\d.,]+)\s*' + kw, text_lower)
            if match:
                num_str = match.group(1).replace(".", "").replace(",", "")
                try:
                    return int(num_str)
                except ValueError:
                    pass
    return 0
