import json
import requests
from bs4 import BeautifulSoup

URL = "https://www.autoscout24.com/lst/toyota/yaris?sort=standard&desc=0&fuel=hybrid&pricefrom=1000&priceto=8000&yearfrom=2016&yearto=2023&kmto=150000"

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

    # NOWE selektory AutoScout24
    cars = soup.select("div.cldt-summary-full-item")  # poprawiony selektor

    for car in cars:
        try:
            title = car.select_one("h2")
            title = title.get_text(strip=True) if title else None

            price = car.select_one(".cldt-price")
            price = price.get_text(strip=True) if price else None

            details = car.select("ul.cldt-summary-vehicle-data li")
            year = details[1].get_text(strip=True) if len(details) > 1 else None
            mileage = details[0].get_text(strip=True) if len(details) > 0 else None

            img = car.select_one("img")
            image_url = img.get("src") if img else None

            link = car.select_one("a")
            detail_url = "https://www.autoscout24.com" + link.get("href") if link else None

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
