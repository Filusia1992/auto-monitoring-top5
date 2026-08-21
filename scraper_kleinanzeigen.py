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

GOOD_MODELS = [
    "yaris", "auris", "stonic", "rapid", "ceed",
    "astra", "corsa", "fiesta", "focus", "cupra",
    "pulsar", "nissan pulsar"
]

BAD_KEYWORDS = [
    "scheinwerfer", "kotflügel", "rücklicht", "felge", "stoßstange",
    "lenkgetriebe", "schaltknauf", "instandsetzung", "blenden",
    "konsole", "motorhaube", "fensterheberschalter", "traggelenk",
    "rad", "konsolenumrandung", "xp", "pdc", "ankauf", "suche"
]

BAD_ENGINES = ["ecoboost"]


def fetch_html(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print("fetch_html error:", e)
        return ""


def parse_list(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    cars = soup.find_all("article", class_="aditem")
    for car in cars:
        try:
            title_el = car.find("a", class_="ellipsis")
            if not title_el:
                title_el = car.find("h2")
            title = title_el.get_text(strip=True) if title_el else None

            price_el = car.find("p", class_="aditem-main--middle--price")
            if not price_el:
                price_el = car.find("p", class_="aditem-main--middle--price-shipping--price")
            price = price_el.get_text(strip=True) if price_el else None

            link = car.find("a")
            detail_url = BASE_URL + link["href"] if link and "href" in link.attrs else None

            img = car.find("img")
            image_url = img["src"] if img and "src" in img.attrs else None

            if not title or not detail_url:
                continue

            results.append({
                "title": title,
                "price": price,
                "image": image_url,
                "url": detail_url,
                "platform": "kleinanzeigen"
            })
        except Exception as e:
            print("parse_list error:", e)
            continue

    return results


def get_detail_fields(soup):
    details = {}
    dts = soup.find_all("dt")
    dds = soup.find_all("dd")
    for dt, dd in zip(dts, dds):
        key = dt.get_text(strip=True).lower()
        value = dd.get_text(strip=True)
        details[key] = value
    return details


def extract_year(text):
    m = re.search(r"(19[8-9]\d|20[0-3]\d)", text)
    return int(m.group(1)) if m else None


def extract_mileage(text):
    patterns = [
        r"(\d{1,3})\s*tkm",
        r"(\d{1,3})\s*t\s*km",
        r"(\d{1,3}[.]\d{3})",
        r"(\d{2,3}[.\s]?\d{3})\s*(km|KM|Km)"
    ]
    for p in patterns:
        m = re.search(p, text.lower())
        if m:
            raw = m.group(1).replace(".", "").replace(" ", "")
            if raw.isdigit():
                return int(raw)
    return None


def extract_fuel(text):
    t = text.lower()
    if any(x in t for x in ["cdti", "tdi", "dci", "hdi"]):
        return "diesel"
    if any(x in t for x in ["1.0", "1.2", "1.3", "1.4", "1.6", "2.0"]):
        return "benzin"
    if "benzin" in t:
        return "benzin"
    if "diesel" in t:
        return "diesel"
    return None


def extract_location(soup):
    loc_el = soup.find(string=re.compile("Standort"))
    if loc_el:
        parent = loc_el.parent
        next_el = parent.find_next("span")
        if next_el:
            return next_el.get_text(strip=True)
    return None


def extract_equipment(soup, desc):
    equip = []

    equip_section = soup.find("ul", class_=re.compile("vip-features|features"))
    if equip_section:
        for li in equip_section.find_all("li"):
            equip.append(li.get_text(strip=True).lower())

    dl = desc.lower()
    if "carplay" in dl:
        equip.append("carplay")
    if "android auto" in dl:
        equip.append("android auto")
    if "armlehne" in dl or "mittelarmlehne" in dl:
        equip.append("armlehne")

    return equip


def is_car_basic(item):
    title = item["title"].lower()

    if any(bad in title for bad in BAD_KEYWORDS):
        return False

    if any(engine in title for engine in BAD_ENGINES):
        return False

    if not any(model in title for model in GOOD_MODELS):
        return False

    return True


def parse_price(price):
    if not price:
        return None
    p = price.lower()
    p = re.sub(r"vb", "", p)
    p = re.sub(r"[€\s]", "", p)
    p = p.replace(".", "")
    m = re.search(r"(\d+)", p)
    return int(m.group(1)) if m else None


def fetch_and_enrich(item):
    html = fetch_html(item["url"])
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    desc_el = soup.find("div", class_=re.compile("description"))
    description = desc_el.get_text(" ", strip=True) if desc_el else ""

    details = get_detail_fields(soup)
    title = item["title"]

    year = extract_year(title) or extract_year(description) or extract_year(str(details))
    mileage = extract_mileage(title) or extract_mileage(description) or extract_mileage(str(details))
    fuel = extract_fuel(title) or extract_fuel(description) or extract_fuel(str(details))
    location = extract_location(soup)
    equipment = extract_equipment(soup, description)

    item["year"] = year
    item["mileage"] = mileage
    item["fuel"] = fuel
    item["location"] = location
    item["equipment"] = equipment
    item["has_carplay"] = "carplay" in equipment
    item["has_armrest"] = "armlehne" in equipment

    return item


def score_item(item):
    score = 0
    title = item["title"].lower()
    price_value = parse_price(item["price"])
    year = item.get("year")
    mileage = item.get("mileage")
    fuel = item.get("fuel")
    location = item.get("location") or ""

    if not is_car_basic(item):
        return -100

    if price_value is None or price_value > 9000:
        return -50

    score += 10
    score += max(0, 10 - (price_value // 1000))

    if year:
        score += 10 if year >= 2017 else 5 if year >= 2010 else -5

    if mileage:
        score += 10 if mileage <= 150000 else 3 if mileage <= 220000 else -5

    if fuel:
        score += 5 if fuel == "benzin" else -2 if fuel == "diesel" else 0

    if "wenig km" in title:
        score += 5
    if "rentner" in title:
        score += 5
    if "1.hand" in title or "1. hand" in title:
        score += 5
    if "scheckheft" in title:
        score += 5
    if "unfallfrei" in title:
        score += 4

    loc_lower = location.lower()
    if "goslar" in loc_lower:
        score += 8
    elif any(city in loc_lower for city in ["braunschweig", "hannover", "magdeburg", "kassel", "halle", "leipzig"]):
        score += 4

    item["price_value"] = price_value
    item["score"] = score
    return score


def main():
    all_items = []

    for page in range(1, 6):
        url = LIST_URL if page == 1 else f"{LIST_URL}?page={page}"
        html = fetch_html(url)
        items = parse_list(html)
        all_items.extend(items)
        time.sleep(1)

    enriched = []
    for item in all_items:
        if not is_car_basic(item):
            continue
        detail = fetch_and_enrich(item)
        if detail:
            enriched.append(detail)
        time.sleep(1)

    for item in enriched:
        score_item(item)

    with open("results_kleinanzeigen.json", "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=4, ensure_ascii=False)

    print("Zapisano results_kleinanzeigen.json")


if __name__ == "__main__":
    main()
