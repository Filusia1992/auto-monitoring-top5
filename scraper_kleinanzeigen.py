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

# MODELE, KTÓRE CIĘ INTERESUJĄ (dodano Nissan Pulsar)
GOOD_MODELS = [
    "yaris", "auris", "stonic", "rapid", "ceed",
    "astra", "corsa", "fiesta", "focus", "cupra",
    "pulsar", "nissan pulsar"
]

# Słowa kluczowe dla części i śmieci
BAD_KEYWORDS = [
    "scheinwerfer", "kotflügel", "rücklicht", "felge", "stoßstange",
    "lenkgetriebe", "schaltknauf", "instandsetzung", "blenden",
    "konsole", "motorhaube", "fensterheberschalter", "traggelenk",
    "rad", "konsolenumrandung", "xp", "pdc", "ankauf", "suche"
]

# Złe silniki (Ford EcoBoost)
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

def extract_year(details):
    for key, value in details.items():
        if "erstzulassung" in key or "baujahr" in key:
            m = re.search(r"(20[0-3][0-9])", value)
            if m:
                return int(m.group(1))
    return None

def extract_mileage(details):
    for key, value in details.items():
        if "kilometerstand" in key or "laufleistung" in key:
            m = re.search(r"(\d{2,3}[.\s]?\d{3})", value)
            if m:
                raw = m.group(1).replace(".", "").replace(" ", "")
                return int(raw)
    return None

def extract_fuel(details):
    for key, value in details.items():
        if "kraftstoffart" in key or "kraftstoff" in key:
            return value.lower()
    return None

def extract_location(soup):
    loc_el = soup.find(string=re.compile("Standort"))
    if loc_el:
        parent = loc_el.parent
        next_el = parent.find_next("span")
        if next_el:
            return next_el.get_text(strip=True)
    addr = soup.find("div", class_=re.compile("vip-address|address"))
    if addr:
        return addr.get_text(strip=True)
    return None

def extract_equipment(soup):
    equip_section = soup.find("ul", class_=re.compile("vip-features|features"))
    if not equip_section:
        return []
    items = []
    for li in equip_section.find_all("li"):
        txt = li.get_text(strip=True)
        if txt:
            items.append(txt.lower())
    return items

def has_carplay_or_android_auto(equipment):
    text = " ".join(equipment)
    return "android auto" in text or "apple carplay" in text or "carplay" in text

def has_armrest(equipment):
    text = " ".join(equipment)
    return "armlehne" in text or "mittelarmlehne" in text or "armrest" in text

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
    price = price.lower().replace("€", "").replace("vb", "").replace(".", "").replace(" ", "")
    try:
        return int(price)
    except:
        return None

def fetch_and_enrich(item):
    try:
        html = fetch_html(item["url"])
    except:
        return None

    soup = BeautifulSoup(html, "html.parser")
    details = get_detail_fields(soup)

    item["year"] = extract_year(details)
    item["mileage"] = extract_mileage(details)
    item["fuel"] = extract_fuel(details)
    item["location"] = extract_location(soup)
    item["equipment"] = extract_equipment(soup)
    item["has_carplay"] = has_carplay_or_android_auto(item["equipment"])
    item["has_armrest"] = has_armrest(item["equipment"])

    return item

def filter_item(item):
    price_value = parse_price(item["price"])
    year = item.get("year")
    mileage = item.get("mileage")
    fuel = item.get("fuel")

    if not is_car_basic(item):
        return False

    if price_value is None or price_value > 9000:
        return False

    if year is not None and year < 2017:
        return False

    if mileage is not None and mileage > 150000:
        return False

    if fuel is not None and not any(x in fuel for x in ["benzin", "hybrid", "strom"]):
        return False

    item["price_value"] = price_value
    return True

def main():
    list_html = fetch_html(LIST_URL)
    raw_list = parse_list(list_html)

    with open("results_kleinanzeigen_raw.json", "w", encoding="utf-8") as f:
        json.dump(raw_list, f, indent=4, ensure_ascii=False)

    enriched = []
    for item in raw_list:
        if not is_car_basic(item):
            continue
        detail = fetch_and_enrich(item)
        if detail:
            enriched.append(detail)
        time.sleep(1)

    with open("results_kleinanzeigen_detailed.json", "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=4, ensure_ascii=False)

    filtered = [item for item in enriched if filter_item(item)]
    filtered.sort(key=lambda x: x["price_value"])

    print("\n=== Auta pasujące do Twoich kryteriów (szczegółowy scraper) ===\n")
    if not filtered:
        print("Brak aut spełniających Twoje kryteria w dzisiejszych wynikach.")
    else:
        for car in filtered:
            year_str = car["year"] if car.get("year") else "brak rocznika"
            mileage_str = f"{car['mileage']} km" if car.get("mileage") else "brak przebiegu"
            loc_str = car["location"] if car.get("location") else "brak lokalizacji"
            print(f"{car['title']} — {car['price']} — {year_str} — {mileage_str} — {loc_str} — {car['url']}")

if __name__ == "__main__":
    main()
