"""Scrape report URLs using Playwright with persistent auth (Microsoft SSO).

Known issues & solutions:
- HITS note pages (/note/) are SPAs that render content in React containers,
  not plain <p> tags. We extract from the full body text and filter boilerplate.
- HITS study pages (/study/) render similarly but often have more visible <p> content.
- SharePoint PowerPoint links (:p:) render in an Office Online iframe that needs
  extra wait time and frame-level extraction.
- aka.ms links are redirects — follow them, then scrape based on the landing domain.
"""
import asyncio
import json
import re
import sys
from playwright.async_api import async_playwright

# Known HITS boilerplate phrases to filter out
HITS_BOILERPLATE = [
    "Tap the edit button in the top right",
    "Make sure any names (including first name)",
    "Third-party policies are sometimes more lenient",
    "The collection is locked because one or more users",
    "Please feel free to reach out to them",
    "Report: Make sure any names",
    "Third-party data:",
]

URLS = {
    # Map: GitHub issue URL -> report URL
    # Updated by the caller before each run
    # FoundryIQ & Tools - Foundational Customer Interviews - SharePoint
    "https://github.com/coreai-microsoft/caidr/issues/320": "https://microsoft-my.sharepoint.com/:p:/p/irsmoke/cQr3lsnIzemZQ6sFSmVyE9gwEgUCDAvtRMpeNiWs6ZH2105Gqg",
    # Embr (Startup Cloud) UXR Collaboration with Azure Core - SharePoint
    "https://github.com/coreai-microsoft/caidr/issues/550": "https://microsoft-my.sharepoint.com/:p:/p/pujapandya/IQA-5Jn_VhxATJ_U1tIqOWpfATILagNlMqMFMn-bRjVPU0c?e=sE6hSb",
    # Custom code training Foundry IA - SharePoint
    "https://github.com/coreai-microsoft/caidr/issues/600": "https://microsoft-my.sharepoint.com/:w:/p/anfulcer/cQoviVxBKUg7QohaVVDxcyjSEgUCCPMqUwfd6DW0gOhpTbzsug",
    # AITK Foundry Extensions Study - SharePoint
    "https://github.com/coreai-microsoft/caidr/issues/595": "https://microsoft-my.sharepoint.com/:p:/p/anfulcer/cQo3kW9FxUIcT5UuMx8-JytWEgUCE00RX4RXvYQ5hp-JtUtIzQ",
    # Dev Workflow and Cloud Deployment Pilot Studies - SharePoint Phase 2 URL (Phase 1 access removed)
    "https://github.com/coreai-microsoft/caidr/issues/794": "https://microsoft-my.sharepoint.com/:p:/p/v-hwelliver/cQo3of_5EU_gRZWaujs1GNfHEgUDb7sZG9rvgHVEI8Ye4emneA",
}


def is_boilerplate(text):
    """Return True if the text is known HITS boilerplate."""
    for phrase in HITS_BOILERPLATE:
        if phrase in text:
            return True
    return False


def clean_hits_text(raw):
    """Remove boilerplate lines and return meaningful content."""
    lines = raw.split("\n")
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line or len(line) < 30:
            continue
        if is_boilerplate(line):
            continue
        cleaned.append(line)
    return "\n\n".join(cleaned)


async def scrape_hits(page, url):
    """HITS pages are React SPAs. Wait for content, grab all visible text,
    then filter out boilerplate. Works for both /note/ and /study/ pages."""
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(12000)

    # Strategy 1: Try article/section/main containers first (most specific)
    text = await page.evaluate("""() => {
        const containers = document.querySelectorAll('article, [role="main"], main, .note-content, .study-content, .report-content, [class*="content"], [class*="body"]');
        const texts = [];
        const seen = new Set();
        for (const c of containers) {
            for (const el of c.querySelectorAll('p, li, h1, h2, h3, h4, h5, h6, blockquote, figcaption')) {
                const t = el.textContent.trim();
                if (t.length > 30 && !seen.has(t)) {
                    seen.add(t);
                    texts.push(t);
                }
            }
        }
        return texts.join('\\n');
    }""")

    cleaned = clean_hits_text(text)
    if len(cleaned) > 150:
        return cleaned

    # Strategy 2: Grab ALL text from all meaningful elements on the page
    text = await page.evaluate("""() => {
        const els = document.querySelectorAll('p, li, h1, h2, h3, h4, h5, h6, blockquote, td, th, figcaption, span, div');
        const texts = [];
        const seen = new Set();
        for (const el of els) {
            const t = el.textContent.trim();
            // Only grab leaf-ish text (avoid giant parent divs that duplicate child text)
            if (t.length > 30 && t.length < 2000 && !seen.has(t)) {
                seen.add(t);
                texts.push(t);
            }
        }
        return texts.join('\\n');
    }""")

    cleaned = clean_hits_text(text)
    if len(cleaned) > 150:
        return cleaned

    # Strategy 3: Full body innerText as last resort
    text = await page.evaluate("() => document.body.innerText")
    cleaned = clean_hits_text(text)
    return cleaned


async def scrape_sharepoint(page, url):
    """SharePoint docs — try main page, then all iframes (Office Online viewer).
    PowerPoint links (:p:) need the iframe to fully render."""
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(15000)

    # Try main page first
    text = await page.evaluate("""() => {
        const els = document.querySelectorAll('p, li, h1, h2, h3, h4, td, th, span, div');
        const texts = [];
        const seen = new Set();
        for (const el of els) {
            const t = el.textContent.trim();
            if (t.length > 40 && t.length < 2000 && !seen.has(t)) {
                seen.add(t);
                texts.push(t);
            }
        }
        return texts.slice(0, 40).join('\\n\\n');
    }""")
    if text and len(text) > 200:
        return text

    # Try all iframes (Office Online renders PPT/Word in iframes)
    for frame in page.frames:
        try:
            frame_text = await frame.evaluate("""() => {
                const els = document.querySelectorAll('p, li, h1, h2, h3, h4, td, th, span, div, [class*="slide"], [class*="text"]');
                const texts = [];
                const seen = new Set();
                for (const el of els) {
                    const t = el.textContent.trim();
                    if (t.length > 20 && t.length < 2000 && !seen.has(t)) {
                        seen.add(t);
                        texts.push(t);
                    }
                }
                return texts.slice(0, 60).join('\\n\\n');
            }""")
            if frame_text and len(frame_text) > 200:
                return frame_text
        except:
            continue

    # Last resort: try body innerText from all frames
    all_text = []
    for frame in page.frames:
        try:
            ft = await frame.evaluate("() => document.body ? document.body.innerText : ''")
            if ft and len(ft) > 100:
                all_text.append(ft)
        except:
            continue
    if all_text:
        return "\n\n".join(all_text)[:5000]

    return text or ""


async def scrape_figma(page, url):
    """Figma decks — canvas-based SPA, results are often empty."""
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(12000)
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


async def scrape_generic(page, url):
    """Generic fallback — follow any redirects, wait, grab all text."""
    await page.goto(url, wait_until="domcontentloaded")
    await page.wait_for_timeout(8000)
    final_url = page.url

    # If we redirected to a known domain, use the specialized scraper
    if "hits.microsoft.com" in final_url:
        return await scrape_hits(page, final_url)
    if "sharepoint.com" in final_url:
        return await scrape_sharepoint(page, final_url)
    if "figma.com" in final_url:
        return await scrape_figma(page, final_url)

    text = await page.evaluate("""() => {
        const els = document.querySelectorAll('p, li, h1, h2, h3, h4, td, th');
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


def pick_scraper(report_url):
    """Route to the right scraper based on URL domain."""
    if "hits.microsoft.com" in report_url:
        return scrape_hits
    if "sharepoint.com" in report_url:
        return scrape_sharepoint
    if "figma.com" in report_url:
        return scrape_figma
    # aka.ms, short URLs, or anything else — use generic (follows redirects)
    return scrape_generic


async def main():
    async with async_playwright() as p:
        user_data = r"C:\Users\dagottl\AppData\Local\Temp\pw-profile"
        context = await p.chromium.launch_persistent_context(
            user_data,
            headless=False,
            channel="msedge",
        )

        results = {}
        for issue_url, report_url in URLS.items():
            print(f"Scraping: {report_url[:80]}...")
            # Use a fresh page per URL to prevent cascading navigation errors
            page = await context.new_page()
            try:
                scraper = pick_scraper(report_url)
                text = await scraper(page, report_url)
                results[issue_url] = text
                char_count = len(text)
                status = "OK" if char_count > 150 else "LOW" if char_count > 0 else "EMPTY"
                print(f"  [{status}] {char_count} chars")
            except Exception as e:
                print(f"  [ERROR] {e}")
                results[issue_url] = ""
            finally:
                await page.close()

        await context.close()

    with open("scraped_reports.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Summary
    ok = sum(1 for v in results.values() if len(v) > 150)
    low = sum(1 for v in results.values() if 0 < len(v) <= 150)
    empty = sum(1 for v in results.values() if len(v) == 0)
    print(f"\nSaved {len(results)} results to scraped_reports.json")
    print(f"  OK (>150 chars): {ok}  |  LOW: {low}  |  EMPTY: {empty}")

if __name__ == "__main__":
    asyncio.run(main())
