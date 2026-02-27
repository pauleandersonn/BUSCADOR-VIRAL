"""
Threads (Meta) scraper via Playwright.
Busca posts por palavra-chave. Usa mesma conta do Instagram.
"""
import os
import re
from typing import List, Dict

from .pw_base import (
    get_context, save_session, clear_session,
    safe_close, config_needed, log_score, is_login_page,
)


async def search_threads(niche: str, limit: int = 10) -> List[Dict]:
    # Threads usa conta do Instagram (Meta)
    email = os.getenv("THREADS_EMAIL", os.getenv("INSTAGRAM_EMAIL", "")).strip()
    password = os.getenv("THREADS_PASSWORD", os.getenv("INSTAGRAM_PASSWORD", "")).strip()

    if not email or not password:
        return [config_needed(
            "Threads",
            "Configure THREADS_EMAIL e THREADS_PASSWORD na página de configuração (mesma conta do Instagram)",
            "http://187.77.43.189:8090/config.html",
        )]

    ctx = await get_context("threads")
    results = []

    try:
        page = await ctx.new_page()
        query = niche.replace(" ", "%20")

        await page.goto(f"https://www.threads.net/search?q={query}&serp_type=default", timeout=25000)
        await page.wait_for_timeout(3000)

        # Verifica login
        if is_login_page(page.url, ["login", "accounts/login"]):
            await _do_login(page, email, password)
            await page.goto(f"https://www.threads.net/search?q={query}&serp_type=default", timeout=25000)
            await page.wait_for_timeout(3000)

        await save_session(ctx, "threads")

        # Fecha popups
        for sel in ['[aria-label="Fechar"]', '[aria-label="Close"]', 'button:has-text("Não agora")', 'button:has-text("Not now")']:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible():
                    await btn.click()
                    await page.wait_for_timeout(500)
            except Exception:
                pass

        # Scroll para carregar
        for _ in range(2):
            await page.evaluate("window.scrollBy(0, 1500)")
            await page.wait_for_timeout(1500)

        # Coleta posts — tenta múltiplos seletores
        post_containers = await page.locator('div[role="article"], div[class*="ThreadPost"], a[href*="/@"]').all()

        seen_urls = set()
        for container in post_containers[:limit * 3]:
            try:
                # URL
                href = await container.get_attribute("href") or ""
                if not href:
                    link = container.locator('a[href*="/post/"]').first
                    href = await link.get_attribute("href") or ""

                if not href:
                    continue

                url = href if href.startswith("http") else f"https://www.threads.net{href}"
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                # Autor
                author_match = re.search(r'threads\.net/@([^/]+)', url)
                author = author_match.group(1) if author_match else ""

                # Texto
                text = await container.inner_text()
                lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 10]
                title = lines[0][:200] if lines else f"Post Threads @{author}"

                # Métricas
                likes = _parse_count(text, ["curtidas", "likes", "gosto"])
                replies = _parse_count(text, ["respostas", "replies", "comentários"])

                # Thumbnail
                thumb = ""
                try:
                    img = container.locator("img").first
                    if await img.count() > 0:
                        src = await img.get_attribute("src") or ""
                        if "profile" not in src.lower():
                            thumb = src
                except Exception:
                    pass

                if "/post/" not in url and f"/@{author}" not in url:
                    continue

                results.append({
                    "source": "Threads",
                    "title": title,
                    "url": url,
                    "score": log_score(likes),
                    "raw_engagement": likes,
                    "comments": replies,
                    "subreddit": f"@{author}" if author else "",
                    "thumbnail": thumb,
                })

                if len(results) >= limit:
                    break
            except Exception:
                continue

    except Exception:
        clear_session("threads")
    finally:
        await safe_close(ctx)

    return sorted(results, key=lambda x: x["score"], reverse=True)


async def _do_login(page, email: str, password: str):
    try:
        await page.goto("https://www.threads.net/login", timeout=20000)
        await page.wait_for_timeout(2000)

        # Threads usa login do Instagram
        insta_btn = page.locator('button:has-text("Instagram"), a:has-text("Instagram")').first
        if await insta_btn.count() > 0:
            await insta_btn.click()
            await page.wait_for_timeout(2000)

        await page.fill('input[name="username"], input[autocomplete="username"]', email)
        await page.fill('input[name="password"], input[type="password"]', password)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(4000)

        # Fecha "Salvar informações de login?"
        for sel in ['button:has-text("Agora não")', 'button:has-text("Not Now")']:
            try:
                btn = page.locator(sel).first
                if await btn.is_visible():
                    await btn.click()
            except Exception:
                pass
    except Exception:
        pass


def _parse_count(text: str, keywords: list) -> int:
    for kw in keywords:
        match = re.search(r'([\d.,]+[KkMm]?)\s*' + kw, text, re.IGNORECASE)
        if match:
            s = match.group(1).replace(",", ".")
            try:
                if s.lower().endswith("m"):
                    return int(float(s[:-1]) * 1_000_000)
                if s.lower().endswith("k"):
                    return int(float(s[:-1]) * 1_000)
                return int(float(s))
            except ValueError:
                pass
    return 0
