import asyncio
from playwright.async_api import async_playwright
import json

SEARCH_CONFIG = [
    {
        "name": "Toyota Yaris Hybrid",
        "urls": [
            "https://suchen.mobile.de/fahrzeuge/search.html?vc=Car&makeModelVariant1.makeId=24100&makeModelVariant1.modelId=14&fuels=HYBRID&maxPrice=8000&minYear=2017&maxMileage=150000&scopeId=C&zipcode=38690&radius=300",
            "https://www.autoscout24.de/lst/toyota/yaris?fuel=hybrid&price_to=8000&year_from=2017&km_to=150000&zip=38690&radius=300"
        ]
    },
    {
        "name": "Toyota Auris Hybrid",
        "urls": [
            "https://suchen.mobile.de/fahrzeuge/search.html?vc=Car&makeModelVariant1.makeId=24100&makeModelVariant1.modelId=19&fuels=HYBRID&maxPrice=8000&minYear=2016&maxMileage=180000&scopeId=C&zipcode=38690&radius=300",
            "https://www.autoscout24.de/lst/toyota/auris?fuel=hybrid&price_to=8000&year_from=2016&km_to=180000&zip=38690&radius=300"
        ]
    },
    {
        "name": "Kia Stonic 1.4 MPI",
        "urls": [
            "https://suchen.mobile.de/fahrzeuge/search.html?vc=Car&makeModelVariant1.makeId=17200&makeModelVariant1.modelId=57&maxPrice=8000&minYear=2018&maxMileage=150000&scopeId=C&zipcode=38690&radius=300",
            "https://www.autoscout24.de/lst/kia/stonic?price_to=8000&year_from=2018&km_to=150000&zip=38690&radius=300"
        ]
    },
    {
        "name": "Skoda Rapid 1.6 MPI",
        "urls": [
            "https://suchen.mobile.de/fahrzeuge/search.html?vc=Car&makeModelVariant1.makeId=25200&makeModelVariant1.modelId=39&maxPrice=8000&minYear=2016&maxMileage=180000&scopeId=C&zipcode=38690&radius=300",
            "https://www.autoscout24.de/lst/skoda/rapid?price_to=8000&year_from=2016&km_to=180000&zip=38690&radius=300"
        ]
    },
    {
        "name": "Kia Ceed 1.4/1.6 MPI",
        "urls": [
            "https://suchen.mobile.de/fahrzeuge/search.html?vc=Car&makeModelVariant1.makeId=17200&makeModelVariant1.modelId=16&maxPrice=8000&minYear=2016&maxMileage=180000&scopeId=C&zipcode=38690&radius=300",
            "https://www.autoscout24.de/lst/kia/ceed?price_to=8000&year_from=2016&km_to=180000&zip=38690&radius=300"
        ]
    }
]

async def scrape_page(page, url, model_name):
    await page.goto(url)
    await page.wait_for_timeout(5000)

    listings = []

    items = await page.query_selector_all("article, div.list-item, div.result-item")
    for item in items:
        try:
            title_el = await item.query_selector("h2, h3")
            price_el = await item.query_selector(".price, .listing-price")
            link_el = await item.query_selector("a")

            title = await title_el.inner_text() if title_el else ""
            price = await price_el.inner_text() if price_el else ""
            url_rel = await link_el.get_attribute("href") if link_el else ""

            listings.append({
                "model": model_name,
                "title": title.strip(),
                "price": price.strip(),
                "url": url_rel,
                "source": url
            })
        except:
            continue

    return listings

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        all_listings = []

        for config in SEARCH_CONFIG:
            model_name = config["name"]
            for url in config["urls"]:
                listings = await scrape_page(page, url, model_name)
                all_listings.extend(listings)

        with open("top5_listings.json", "w", encoding="utf-8") as f:
            json.dump(all_listings, f, indent=4, ensure_ascii=False)

        await browser.close()

asyncio.run(main())
