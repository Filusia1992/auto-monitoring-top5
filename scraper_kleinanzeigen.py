import json
import re
import time
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.kleinanzeigen.de"
LIST_URL = "https://www.kleinanzeigen.de/s-autos/k0"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
}

# MODELE – dopasowanie po słowach w tytule
MODEL_KEYWORDS = [
    "yaris hybrid",
    "auris hybrid",
    "stonic",
    "rapid",
    "ceed",
    "corsa",
    "mazda 2",
    "mazda 3",
    "cx-3",
]

def title_matches_model(title):
    t = title.lower()
    return any(keyword in t for keyword in MODEL_KEYWORDS)


def fetch_html(url):
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.text


def parse_list(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    cars = soup.find_all("article", class_="aditem")
    for car in cars:
        try:
            title_el = car.find("a", class_="ellipsis")
            if not title_el:
                title_el = car.find("h2")
            if not title_el:
                title_el = car.find("a", class_="aditem-main--title")
            title = title_el.get_text(strip=True) if title_el else None

            price_el = car.find("p", class_="aditem-main--price")
            if not price_el:
                price_el = car.find("p", class_="aditem-main--middle--price")
            if not price_el:
                price_el = car.find("p", class_="aditem-main--middle--price-shipping--price")
            price = price_el.get_text(strip=True) if price_el else None

            link = car.find("a", href=True)
            detail_url = BASE_URL + link["href"] if link else None

            img = car.find("img")
            image_url = img["src"] if img and "src" in img.attrs else None

            if not title or not detail_url:
                continue

            results.append({
                "title": title,
                "price": price,
                "image": image_url,
                "url": detail_url,
            })
        except:
            continue

    return results


def get_detail_fields(soup):
    details = {}

    vip = soup.find("div", class_="vip-details")
    if vip:
        for row in vip.find_all("div", class_="vip-detail"):
            label = row.find("span", class_="vip-detail-label")
            value = row.find("span", class_="vip-detail-value")
            if label and value:
                details[label.get_text(strip=True).lower()] = value.get_text(strip=True)

    for dt, dd in zip(soup.find_all("dt"), soup.find_all("dd")):
        details[dt.get_text(strip=True).lower()] = dd.get_text(strip=True)

    return details


def extract_year(details, desc, title):
    # VIP-details
    for key, value in details.items():
        if any(k in key for k in ["ez", "erstzulassung", "baujahr", "bj"]):
            m = re.search(r"(19[8-9]\d|20[0-3]\d)", value)
            if m:
                return int(m.group(1))

    # description
    m = re.search(r"(19[8-9]\d|20[0-3]\d)", desc)
    if m:
        return int(m.group(1))

    # title
    m = re.search(r"(19[8-9]\d|20[0-3]\d)", title)
    if m:
        return int(m.group(1))

    return None


def parse_price(price):
    if not price:
        return None
    cleaned = re.sub(r"[^\d]", "", price)
    if cleaned.isdigit():
        return int(cleaned)
    return None


def fetch_and_enrich(item):
    try:
        html = fetch_html(item["url"])
    except:
        return None

    soup = BeautifulSoup(html, "html.parser")

    desc_el = soup.find("div", class_=re.compile("ad-description|description"))
    description = desc_el.get_text(" ", strip=True) if desc_el else ""

    details = get_detail_fields(soup)

    year = extract_year(details, description, item["title"])
    price_value = parse_price(item["price"])

    item["year"] = year
    item["price_value"] = price_value

    return item


def passes_filters(item):
    # model dopasowany po tytule
    if not title_matches_model(item["title"]):
        return False

    # cena ≤ 8000
    if item.get("price_value") is None or item["price_value"] > 8000:
        return False

    # rocznik ≥ 2017
    if item.get("year") is None or item["year"] < 2017:
        return False

    return True


def main():
    all_items = []

    for page in range(1, 6):
        url = LIST_URL if page == 1 else f"{LIST_URL}?page={page}"
        try:
            html = fetch_html(url)
        except:
            continue

        items = parse_list(html)
        print(f"Strona {page}: {len(items)} ogłoszeń")
        all_items.extend(items)
        time.sleep(1)

    # deduplikacja
    unique = {item["url"]: item for item in all_items}
    all_items = list(unique.values())

    final = []
    for item in all_items:
        detail = fetch_and_enrich(item)
        if detail and passes_filters(detail):
            final.append(detail)
        time.sleep(1)

    with open("results_kleinanzeigen.json", "w", encoding="utf-8") as f:
        json.dump(final, f, indent=4, ensure_ascii=False)

    print(f"Zapisano results_kleinanzeigen.json — znaleziono {len(final)} aut")


if __name__ == "__main__":
    main()
