import asyncio
from playwright.async_api import async_playwright
import json

SEARCH_URLS = [
    "https://suchen.mobile.de/fahrzeuge/search.html?vc=Car&makeModelVariant1.makeId=24100&makeModelVariant1.modelId=14&fuels=HYBRID&maxPrice=8000&minYear=2017&maxMileage=150000&scopeId=C&zipcode=38690&radius=300",
    "https://suchen.mobile.de/fahrzeuge/search.html?vc=Car&makeModelVariant1.makeId=24100&makeModelVariant1.modelId=19&fuels=HYBRID&maxPrice=8000&minYear=2016&maxMileage=180000&scopeId=C&zipcode=38690&radius=300",
    "https://suchen.mobile.de/fahrzeuge/search.html?vc=Car&makeModelVariant1.makeId=17200&makeModelVariant1.modelId=57&maxPrice=8000&minYear=2018&maxMileage=150000&scopeId=C&zipcode=38690&radius=300",
    "https://suchen.mobile.de/fahrzeuge/search.html?vc=Car&makeModelVariant1.makeId=25200&makeModelVariant1.modelId=39&maxPrice=8000&minYear=2016&maxMileage=180000&scopeId=C&zipcode=38690&radius=300",
    "https://suchen.mobile.de/fahrzeuge/search.html?vc=Car&makeModelVariant1.makeId=17200&makeModelVariant1.modelId=16&maxPrice=8000&minYear=2016&maxMileage=180000&scopeId=C&zipcode=38690&radius=300"
]

async def scrape_mobile(page, url):
    await page.goto(url)
    await page.wait_for_timeout(5000)

    listings = []

    items = await page.query_selector_all("article")
    for item in items:
        try:
            title_el = await item.query_selector("h3")
            price_el = await item.query_selector(".price-block__price")
            link_el = await item.query_selector("a")
            img_el = await item.query_selector("img")

            title = await title_el.inner_text() if title_el else ""
            price = await price_el.inner_text() if price_el else ""
            link = await link_el.get_attribute("href") if link_el else ""
            img = await img_el.get_attribute("src") if img_el else ""

            listings.append({
                "title": title.strip(),
                "price": price.strip(),
                "url": link,
                "image": img,
                "source": url
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
