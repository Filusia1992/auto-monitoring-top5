import json
import requests
from bs4 import BeautifulSoup

URL = "https://www.kleinanzeigen.de/s-autos/toyota-yaris/k0"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
}

def fetch_html(url):
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.text

def parse_html(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    cars = soup.select("article.aditem")

    for car in cars:
        try:
            title = car.select_one(".text-module-begin")
            title = title.get_text(strip=True) if title else None

            price = car.select_one(".aditem-main--middle--price-shipping--price")
            price = price.get_text(strip=True) if price else None

            img = car.select_one("img")
            image_url = img["src"] if img and "src" in img.attrs else None

            link = car.select_one("a")
            detail_url = "https://www.kleinanzeigen.de" + link["href"] if link else None

            results.append({
                "title": title,
                "price": price,
                "image": image_url,
                "url": detail_url,
                "platform": "kleinanzeigen"
            })
        except:
            continue

    return results

def main():
    html = fetch_html(URL)
    results = parse_html(html)

    with open("results_kleinanzeigen.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()
