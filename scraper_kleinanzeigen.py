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

BAD_ENGINES = [
    "ecoboost"
]

def fetch_html(url):
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.text

def parse_list(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    cars = soup.select("article.aditem")
    for car in cars:
        try:
            title_el = car.select_one(".text-module-begin")
            title = title_el.get_text(strip=True) if title_el else None

            price_el = car.select_one(".aditem-main--middle--price-shipping--price")
            price = price_el.get_text(strip=True) if price_el else None

            link = car.select_one("a")
            detail_url = BASE_URL + link["href"] if link and "href" in link.attrs else None

            img = car.select_one("img")
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
        except:
            continue

    return results

def get_detail_fields(soup):
    details = {}
    for dt, dd in zip(soup.find_all("dt"), soup.find_all("dd")):
        key = dt.get_text(strip=True).lower()
        value = dd.get_text(strip=True)
        details[key] = value
    return details

def extract_year_from_details(details):
    for key, value in details.items():
        m = re.search(r"(19[8-9]\d|20[0-3]\d)", value)
        if m:
            return int(m.group(1))
    return None

def extract_year_from_description(desc):
    m = re.search(r"(EZ|Baujahr|Bj\.?)\s*(19[8-9]\d|20[0-3]\d)", desc, re.IGNORECASE)
    if m:
        return int(m.group(2))
    m2 = re.search(r"(19[8-9]\d|20[0-3]\d)", desc)
    if m2:
        return int(m2.group(1))
    return None

def extract_year_from_title(title):
    m = re.search(r"(19[8-9]\d|20[0-3]\d)", title)
    if m:
        return int(m.group(1))
    return None

def extract_mileage_from_details(details):
    for key, value in details.items():
        m = re.search(r"(\d{2,3}[.\s]?\d{3})", value)
        if m:
            raw = m.group(1).replace(".", "").replace(" ", "")
            return int(raw)
    return None

def extract_mileage_from_description(desc):
    m = re.search(r"(\d{2,3}[.\s]?\d{3})\s*(km|KM|Km)", desc)
    if m:
        raw = m.group(1).replace(".", "").replace(" ", "")
        return int(raw)
    return None

def extract_mileage_from_title(title):
    m = re.search(r"(\d{2,3}[.\s]?\d{3})\s*(km|KM|Km)", title)
    if m:
        raw = m.group(1).replace(".", "").replace(" ", "")
        return int(raw)
    return None

def extract_fuel_from_details(details):
    for key, value in details.items():
        if "kraftstoff" in key:
            return value.lower()
    return None

def extract_fuel_from_description(desc):
    dl = desc.lower()
    if "benzin" in dl:
        return "benzin"
    if "diesel" in dl:
        return "diesel"
    if "hybrid" in dl:
        return "hybrid"
    if "elektro" in dl or "strom" in dl:
        return "strom"
    return None

def extract_location(soup, desc):
    loc_el = soup.find(string=re.compile("Standort"))
    if loc_el:
        parent = loc_el.parent
        next_el = parent.find_next("span")
        if next_el:
            return next_el.get_text(strip=True)

    m = re.search(r"(steht in|location|ort)\s*([A-Za-zäöüÄÖÜß ]+)", desc, re.IGNORECASE)
    if m:
        return m.group(2).strip()

    return None

def extract_equipment(soup, desc):
    equip = []

    equip_section = soup.find("ul", class_=re.compile("vip-features|features"))
    if equip_section:
        for li in equip_section.find_all("li"):
            txt = li.get_text(strip=True).lower()
            equip.append(txt)

    dl = desc.lower()
    if "carplay" in dl or "apple carplay" in dl:
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

    if any(model in title for model in GOOD_MODELS):
        return True

    return False

def parse_price(price):
    if not price:
        return None
    p = price.lower()
    p = re.sub(r"vb", "", p)
    p = re.sub(r"[€\s]", "", p)
    p = p.replace(".", "")
    m = re.search(r"(\d+)", p)
    if not m:
        return None
    try:
        return int(m.group(1))
    except:
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
    title = item["title"]

    year = (
        extract_year_from_details(details)
        or extract_year_from_description(description)
        or extract_year_from_title(title)
    )

    mileage = (
        extract_mileage_from_details(details)
        or extract_mileage_from_description(description)
        or extract_mileage_from_title(title)
    )

    fuel = (
        extract_fuel_from_details(details)
        or extract_fuel_from_description(description)
    )

    location = extract_location(soup, description)
    equipment = extract_equipment(soup, description)

    item["year"] = year
    item["mileage"] = mileage
    item["fuel"] = fuel
    item["location"] = location
    item["equipment"] = equipment
    item["has_carplay"] = "carplay" in equipment or "android auto" in equipment
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

    score += 10  # dobry model
    score += max(0, 10 - (price_value // 1000))  # im taniej, tym lepiej

    if year is not None:
        if year >= 2017:
            score += 10
        elif year >= 2010:
            score += 5
        else:
            score -= 5

    if mileage is not None:
        if mileage <= 150000:
            score += 10
        elif mileage <= 220000:
            score += 3
        else:
            score -= 5

    if fuel is not None:
        if "benzin" in fuel or "hybrid" in fuel or "strom" in fuel:
            score += 5
        elif "diesel" in fuel:
            score -= 2

    if item.get("has_carplay"):
        score += 3
    if item.get("has_armrest"):
        score += 2

    loc_lower = location.lower()
    if "goslar" in loc_lower:
        score += 8
    elif any(city in loc_lower for city in ["braunschweig", "hannover", "magdeburg", "kassel", "halle", "leipzig"]):
        score += 4

    item["price_value"] = price_value
    item["score"] = score
    return score

def main():
    all_list_items = []

    for page in range(1, 6):
        if page == 1:
            url = LIST_URL
        else:
            url = f"{LIST_URL}?page={page}"

        try:
            list_html = fetch_html(url)
        except:
            continue

        page_items = parse_list(list_html)
        all_list_items.extend(page_items)
        time.sleep(1)

    enriched = []
    for item in all_list_items:
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

    filtered = [item for item in enriched if item.get("score", -100) > 0]
    filtered.sort(key=lambda x: x["score"], reverse=True)

    print("\n=== Auta pasujące do Twoich kryteriów (scraper 2.0 – scoring) ===\n")
    if not filtered:
        print("Brak aut z dodatnim wynikiem w dzisiejszych wynikach.")
    else:
        for car in filtered:
            year_str = car["year"] if car.get("year") else "brak rocznika"
            mileage_str = f"{car['mileage']} km" if car.get("mileage") else "brak przebiegu"
            loc_str = car["location"] if car.get("location") else "brak lokalizacji"
            print(f"[{car['score']}] {car['title']} — {car['price']} — {year_str} — {mileage_str} — {loc_str} — {car['url']}")

if __name__ == "__main__":
    main()
