"""
Base Playwright session manager.
Handles browser lifecycle, session persistence and login detection.
"""
import asyncio
import json
import math
import os
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, BrowserContext, Browser, Page

SESSIONS_DIR = Path(__file__).parent.parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

# Shared browser instance (one per process)
_browser: Optional[Browser] = None
_pw_instance = None
_lock = asyncio.Lock()


def log_score(raw: int) -> int:
    if raw <= 0:
        return 0
    return int(math.log10(raw + 1) * 1000)


def config_needed(source: str, message: str, url: str) -> dict:
    return {
        "source": source,
        "title": f"⚠ {message}",
        "url": url,
        "score": 0,
        "comments": 0,
        "subreddit": "",
        "thumbnail": "",
        "_config_needed": True,
    }


async def get_browser() -> Browser:
    global _browser, _pw_instance
    async with _lock:
        if _browser is None or not _browser.is_connected():
            _pw_instance = await async_playwright().start()
            _browser = await _pw_instance.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    "--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                ],
            )
    return _browser


async def get_context(platform: str) -> BrowserContext:
    """Return a browser context with saved session state if available."""
    browser = await get_browser()
    state_file = SESSIONS_DIR / f"{platform}_state.json"

    if state_file.exists():
        try:
            ctx = await browser.new_context(
                storage_state=str(state_file),
                viewport={"width": 1280, "height": 800},
                locale="pt-BR",
                extra_http_headers={"Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"},
            )
            return ctx
        except Exception:
            state_file.unlink(missing_ok=True)

    return await browser.new_context(
        viewport={"width": 1280, "height": 800},
        locale="pt-BR",
        extra_http_headers={"Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"},
    )


async def save_session(ctx: BrowserContext, platform: str):
    state_file = SESSIONS_DIR / f"{platform}_state.json"
    try:
        await ctx.storage_state(path=str(state_file))
    except Exception:
        pass


def clear_session(platform: str):
    state_file = SESSIONS_DIR / f"{platform}_state.json"
    state_file.unlink(missing_ok=True)


def is_login_page(url: str, keywords: list[str]) -> bool:
    url_lower = url.lower()
    return any(k in url_lower for k in keywords)


async def safe_close(ctx: BrowserContext):
    try:
        await ctx.close()
    except Exception:
        pass
