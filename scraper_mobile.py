async def auto_scroll(page):
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

async def scrape_details(page, url):
    """Scrapes year from the detail page."""
    await page.goto(url)
    await page.wait_for_timeout(3000)

    details_text = await page.inner_text("body")
    match = re.search(r"(20\d{2})", details_text)
    return int(match.group(1)) if match else None

async def scrape_mobile(page, url):
    await page.goto(url)
    await auto_scroll(page)

    listings = []

    items = await page.query_selector_all("article")
    for item in items:
        try:
            title_el = await item.query_selector("h3.vehicle-title")
            price_el = await item.query_selector("span.vehicle-price")
            link_el = await item.query_selector("a.vehicle-link")
            img_el = await item.query_selector("img.vehicle-image")

            title = await title_el.inner_text() if title_el else ""
            price = await price_el.inner_text() if price_el else ""
            link = await link_el.get_attribute("href") if link_el else ""
            img = await img_el.get_attribute("src") if img_el else ""

            full_link = f"https://suchen.mobile.de{link}" if link else None

            # get year from detail page
            year = await scrape_details(page, full_link) if full_link else None

            listings.append({
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

    return listings

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        all_results = []

        for url in SEARCH_URLS:
            results = await scrape_mobile(page, url)
            all_results.extend(results)

        with open("results_mobile.json", "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=4, ensure_ascii=False)

        await browser.close()

asyncio.run(main())
