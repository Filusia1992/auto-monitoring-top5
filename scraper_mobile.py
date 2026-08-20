import json
from playwright.sync_api import sync_playwright

URL = "https://suchen.mobile.de/fahrzeuge/search.html?isSearchRequest=true&s=Car&vc=Car&cn=DE&dam=false&fr=2016%3A2023&ml=%3A150000&p=4500%3A8500&gn=30823%2C+Garbsen%2C+Niedersachsen&rd=300&ll=52.4158598%2C9.5850153&asl=true&ft=PETROL&ft=HYBRID&ref=dsp"

def main():
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(URL, timeout=60000)

        # Akceptacja cookies (jeśli są)
        try:
            page.click("button:has-text('Akzeptieren')", timeout=3000)
        except:
            pass

        page.wait_for_selector("article", timeout=20000)

        cars = page.query_selector_all("article")

        for car in cars:
            try:
                title = car.query_selector("h3")
                title = title.inner_text().strip() if title else None

                price = car.query_selector(".price-block__price")
                price = price.inner_text().strip() if price else None

                year = car.query_selector(".vehicle-data__year")
                year = year.inner_text().strip() if year else None

                mileage = car.query_selector(".vehicle-data__mileage")
                mileage = mileage.inner_text().strip() if mileage else None

                img = car.query_selector("img")
                image_url = img.get_attribute("src") if img else None

                link = car.query_selector("a")
                detail_url = "https://suchen.mobile.de" + link.get_attribute("href") if link else None

                results.append({
                    "title": title,
                    "price": price,
                    "year": year,
                    "mileage": mileage,
                    "image": image_url,
                    "url": detail_url,
                    "platform": "mobile.de"
                })
            except:
                continue

        browser.close()

    with open("results_mobile.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()
