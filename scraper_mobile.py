import asyncio
from playwright.async_api import async_playwright
import json

SEARCH_URL = "https://suchen.mobile.de/fahrzeuge/search.html?vc=Car&makeModelVariant1.makeId=24100&makeModelVariant1.modelId=14&maxPrice=8000&minYear=2018&maxMileage=150000&scopeId=C&zipcode=38690&radius=300"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Go to search page
        await page.goto(SEARCH_URL)

        # Wait for page to load
        await page.wait_for_timeout(5000)

        # Take screenshot of what Playwright sees
        await page.screenshot(path="mobile_debug.png", full_page=True)

        # Save empty results for now
        with open("results_mobile.json", "w", encoding="utf-8") as f:
            json.dump([], f, indent=4)

        await browser.close()

asyncio.run(main())
