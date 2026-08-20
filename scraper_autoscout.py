import json
import requests
from bs4 import BeautifulSoup

URL = "https://m.autoscout24.com/lst/toyota/yaris?sort=standard&desc=0&fuel=hybrid&pricefrom=1000&priceto=8000&yearfrom=2016&yearto=2023&kmto=150000"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15A372 Safari/604.1",
}

def fetch_html(url):
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.text

def parse_html(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    cars = soup.select("div.list-item")  # mobilny selektor

    for car in cars:
        try:
            title = car.select_one(".title")
            title = title.get_text(strip=True) if title else None

            price = car.select_one(".price")
            price = price.get_text(strip=True) if price else None

            year = car.select_one(".first-registration")
            year = year.get_text(strip=True) if year else None

            mileage = car.select_one(".mileage")
            mileage = mileage.get_text(strip=True) if mileage else None

            img = car.select_one("img")
            image_url = img.get("src") if img else None

            link = car.select_one("a")
            detail_url = "https://m.autoscout24.com" + link.get("href") if link else None

            results.append({
                "title": title,
                "price": price,
                "year": year,
                "mileage": mileage,
                "image": image_url,
                "url": detail_url,
                "platform": "autoscout24"
            })
        except:
            continue

    return results

def main():
    html = fetch_html(URL)
    results = parse_html(html)

    with open("results_autoscout.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()
