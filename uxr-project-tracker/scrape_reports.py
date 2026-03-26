"""Scrape report URLs using Playwright with persistent auth (Microsoft SSO)."""
import asyncio
import json
import sys
from playwright.async_api import async_playwright

URLS = {
    # SharePoint pages
    "https://github.com/coreai-microsoft/caidr/issues/596": "https://microsoft-my.sharepoint.com/:p:/p/anfulcer/IQBgqFREl8dvQqXeAJdIhVVyARyzYhyqOOJ3zeXeMnRAemQ?e=0csOme",
}

async def scrape_hits(page, url):
    """HITS pages load via SPA — wait 5s then grab paragraphs."""
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(8000)
    text = await page.evaluate("""() => {
        const paragraphs = document.querySelectorAll('p');
        const texts = [];
        for (const p of paragraphs) {
            const text = p.textContent.trim();
            if (text.length > 80) texts.push(text);
        }
        return texts.slice(0, 12).join('\\n\\n');
    }""")
    return text

async def scrape_sharepoint(page, url):
    """SharePoint docs have content in iframes."""
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(10000)
    # Try main page first
    text = await page.evaluate("""() => {
        const paras = document.querySelectorAll('p');
        const texts = [];
        for (const p of paras) {
            const t = p.textContent.trim();
            if (t.length > 60) texts.push(t);
        }
        return texts.slice(0, 20).join('\\n\\n');
    }""")
    if text and len(text) > 100:
        return text
    # Try iframes
    for frame in page.frames:
        try:
            frame_text = await frame.evaluate("""() => {
                const paras = document.querySelectorAll('p');
                const texts = [];
                for (const p of paras) {
                    const t = p.textContent.trim();
                    if (t.length > 60) texts.push(t);
                }
                return texts.slice(0, 20).join('\\n\\n');
            }""")
            if frame_text and len(frame_text) > 100:
                return frame_text
        except:
            continue
    return text or ""

async def scrape_figma(page, url):
    """Figma decks — wait for content to load, grab any visible text."""
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(10000)
    text = await page.evaluate("""() => {
        const els = document.querySelectorAll('div, span, p, h1, h2, h3, h4, h5, h6');
        const texts = [];
        const seen = new Set();
        for (const el of els) {
            const t = el.textContent.trim();
            if (t.length > 40 && !seen.has(t)) {
                seen.add(t);
                texts.push(t);
            }
        }
        return texts.slice(0, 30).join('\\n\\n');
    }""")
    return text

async def main():
    async with async_playwright() as p:
        # Use persistent context to reuse Microsoft auth
        user_data = r"C:\Users\dagottl\AppData\Local\Temp\pw-profile"
        context = await p.chromium.launch_persistent_context(
            user_data,
            headless=False,
            channel="msedge",
        )
        page = context.pages[0] if context.pages else await context.new_page()

        results = {}
        for issue_url, report_url in URLS.items():
            print(f"Scraping: {report_url[:80]}...")
            try:
                if "hits.microsoft.com" in report_url:
                    text = await scrape_hits(page, report_url)
                elif "sharepoint.com" in report_url:
                    text = await scrape_sharepoint(page, report_url)
                elif "figma.com" in report_url:
                    text = await scrape_figma(page, report_url)
                else:
                    text = ""
                results[issue_url] = text
                print(f"  Got {len(text)} chars")
            except Exception as e:
                print(f"  Error: {e}")
                results[issue_url] = ""

        await context.close()

    with open("scraped_reports.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(results)} results to scraped_reports.json")

asyncio.run(main())
