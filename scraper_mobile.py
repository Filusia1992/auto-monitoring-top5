import asyncio
from playwright.async_api import async_playwright
import json
import re

SEARCH_URLS = [
    "https://suchen.mobile.de/fahrzeuge/search.html?vc=Car&makeModelVariant1.makeId=24100&makeModelVariant1.modelId=14&fuels=HYBRID&maxPrice=8000&minYear=2017&maxMileage=150000&scopeId=C&zipcode=38690&radius=300",
    "https://suchen.mobile.de/fahrzeuge/search.html?vc=Car&makeModelVariant1.makeId=24100&makeModelVariant1.modelId=19&fuels=HYBRID&maxPrice=8000&minYear=2016&maxMileage=180000&scopeId=C&zipcode=38690&radius=300",
    "https://suchen.mobile.de/fahrzeuge/search.html?vc=Car&makeModelVariant1.makeId=17200&makeModelVariant1.modelId=57&maxPrice=8000&minYear=2018&maxMileage=150000&scopeId=C&zipcode=38690&radius=300",
    "https://suchen.mobile.de/fahrzeuge/search.html?vc=Car&makeModelVariant1.makeId=25200&makeModelVariant1.modelId=39&maxPrice=8000&minYear=2016&maxMileage=180000&scopeId=C&zipcode=38690&radius=300",
    "https://suchen.mobile.de/fahrzeuge/search.html?vc=Car&makeModelVariant1.makeId=17200&makeModelVariant1.modelId=16&maxPrice=8000&minYear=2016&maxMileage=180000&scopeId=C&zipcode=38690&radius=300"
]

async def auto_scroll(page):
    """Scrolls the page to load dynamic content."""
    await page.evaluate("""
        async () => {
            await new Promise((resolve) => {
                let totalHeight = 0;
                const distance = 800;
                const timer = setInterval(() => {
                    const scrollHeight = document.body.scrollHeight;
                    window.scrollBy(0, distance);
                    totalHeight += distance;

                    if (totalHeight >= scrollHeight) {
                        clearInterval(timer);
                        resolve();
                    }
                }, 300);
            });
        }
    """)

async def scrape_details(page, url):
    """Scrapes year from the detail page."""
    try:
        await page.goto(url)
        await page.wait_for_timeout(3000)
        details_text = await page.inner_text("body")
        match = re.search(r"(20\\d{2})", details_text)
        return int(match.group(1)) if match else None
    except:
        return None

async def scrape_mobile(page, url):
    await page.goto(url)
    await page.wait_for_timeout(3000)

    # Accept cookies if visible
    try:
        await page.click("button#gdpr-consent-accept-button", timeout=3000)
    except:
        pass

    # Scroll to load listings
    await auto_scroll(page)

    # Mobile.de listings are inside an iframe
    frames = page.frames
    listings_frame = None

    for f in frames:
        if "fahrzeuge" in f.url:
            listings_frame = f
            break

    if not listings_frame:
        return []

    items = await listings_frame.query_selector_all("div.cBox-body.cBox-body--resultitem")
    results = []

    for item in items:
        try:
            title_el = await item.query_selector("h3")
            price_el = await item.query_selector("span.price-block__price")
            link_el = await item.query_selector("a")
            img_el = await item.query_selector("img")

            title = await title_el.inner_text() if title_el else ""
            price = await price_el.inner_text() if price_el else ""
            link = await link_el.get_attribute("href") if link_el else ""
            img = await img_el.get_attribute("src") if img_el else ""

            full_link = f"https://suchen.mobile.de{link}" if link else None
            year = await scrape_details(page, full_link) if full_link else None

            results.append({
                "title": title.strip(),
                "price": price.strip(),
                "url": full_link,
                "image": img,
                "year": year,
                "source": url,
                "platform": "mobile.de"
            })
        except:
            continue

    return results

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        all_results = []

        for url in SEARCH_URLS:
            listings = await scrape_mobile(page, url)
            all_results.extend(listings)

        with open("results_mobile.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=4, ensure_ascii=False)

        await browser.close()

asyncio.run(main())
