import asyncio
import random
from playwright.async_api import async_playwright, Page, Browser
from playwright_stealth import Stealth
from .user_agents import get_desktop_user_agent
from .proxy import get_proxy, has_proxies


async def get_browser(playwright) -> Browser:
    proxy = get_proxy() if has_proxies() else None

    launch_args = {
        "headless": True,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-infobars",
            "--disable-background-timer-throttling",
            "--diable-popup-blocking",
            "--disable-backgrounding-occluded-windows",
        ]
    }

    if proxy:
        launch_args["proxy"] = proxy.to_playwright()

    return await playwright.chromium.launch(**launch_args)


async def get_page(browser: Browser) -> Page:
    context = await browser.new_context(
        user_agent=get_desktop_user_agent(),
        locale="en-US",
        viewport={"width": 1366, "height": 768},
        java_script_enabled=True,
        has_touch=False,
        is_mobile=False,
    )
    page = await context.new_page()
    await Stealth().apply_stealth_async(page)
    return page


async def fetch_page(url: str) -> str | None:
    async with asynce_playwright() as p:
        browser = await get_browser(p)
        try:
            page = await get_page(browser)
            await asyncio.sleep(random.uniform(1.5, 4.0))
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(random.uniform(0.5, 2.0))
            return await page.content()
        except Exception as e:
            print(f"scraper error: {e}")
            return None
        finally:
            await browser.close()


async def fetch_page_with_js(url: str, js: str) -> dict | None:
    async with async_playwright() as p:
        browser = await get_browser(p)
        try:
            page = await get_page(browser)
            await asyncio.sleep(random.uniform(1.5, 4.0))
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(random.uniform(0.5, 2.0))
            return await page.evaluate(js)
        except Exception as e:
            print(f"scraper js error: {e}")
            return None
        finally:
            await browser.close()