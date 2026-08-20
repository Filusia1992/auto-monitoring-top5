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

    cars = soup.select("article.cldt-summary-full-item")

    for car in cars:
        try:
            title = car.select_one(".cldt-summary-makemodel")
            title = title.get_text(strip=True) if title else None

            price = car.select_one(".cldt-price")
            price = price.get_text(strip=True) if price else None

            mileage = car.select_one(".cldt-summary-vehicle-data li:nth-child(1)")
            mileage = mileage.get_text(strip=True) if mileage else None

            year = car.select_one(".cldt-summary-vehicle-data li:nth-child(2)")
            year = year.get_text(strip=True) if year else None

            img = car.select_one("img")
            image_url = img["src"] if img and "src" in img.attrs else None

            link = car.select_one("a")
            detail_url = "https://www.autoscout24.com" + link["href"] if link else None

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
