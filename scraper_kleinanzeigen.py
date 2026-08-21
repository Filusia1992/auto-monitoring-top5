import json
import re
import time
import requests
from bs4 import BeautifulSoup
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from PIL import Image
import pytesseract
from io import BytesIO
from datetime import datetime

BASE_URL = "https://www.kleinanzeigen.de"
LIST_URL = "https://www.kleinanzeigen.de/s-autos/k0"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

GOOD_MODELS = [
    "yaris", "auris", "stonic", "rapid", "ceed",
    "astra", "corsa", "fiesta", "focus", "cupra",
    "pulsar", "nissan pulsar"
]

BAD_KEYWORDS = ["scheinwerfer", "kotflügel", "rücklicht", "felge", "stoßstange"]
BAD_ENGINES = ["ecoboost"]

geolocator = Nominatim(user_agent="scraper24")
GOSLAR_COORDS = (51.904, 10.427)

def safe_print(msg):
    print(msg, flush=True)

def fetch_html(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.text
    except Exception as e:
        safe_print(f"fetch_html error: {e}")
        return ""

def parse_list(html):
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for car in soup.select("article.aditem"):
        try:
            title = car.select_one(".text-module-begin").get_text(strip=True)
            price = car.select_one(".aditem-main--middle--price-shipping--price").get_text(strip=True)
            link = car.select_one("a")["href"]
            img = car.select_one("img")["src"]
            items.append({
                "title": title,
                "price": price,
                "url": BASE_URL + link,
                "image": img
            })
        except:
            continue
    return items

def extract_mileage_from_title(title):
    t = title.lower()
    patterns = [
        r"(\d{1,3})\s*tkm",
        r"(\d{1,3})\s*t\s*km",
        r"(\d{1,3}[.]\d{3})",
        r"(\d{2,3}[.\s]?\d{3})\s*(km|KM|Km)"
    ]
    for p in patterns:
        m = re.search(p, t)
        if m:
            raw = m.group(1).replace(".", "").replace(" ", "")
            if raw.isdigit():
                return int(raw)
    return None

def extract_year_from_title(title):
    m = re.search(r"(19[8-9]\d|20[0-3]\d)", title)
    return int(m.group(1)) if m else None

def extract_fuel_from_title(title):
    t = title.lower()
    if any(x in t for x in ["cdti", "tdi", "dci", "hdi"]):
        return "diesel"
    if any(x in t for x in ["1.0", "1.2", "1.3", "1.4", "1.6", "2.0"]):
        return "benzin"
    return None

def extract_mileage_from_image(url):
    try:
        img_data = requests.get(url, timeout=5).content
        img = Image.open(BytesIO(img_data))
        text = pytesseract.image_to_string(img)
        m = re.search(r"(\d{2,3}[.\s]?\d{3})", text)
        if m:
            return int(m.group(1).replace(".", "").replace(" ", ""))
    except:
        return None
    return None

def compute_distance(location):
    if not location:
        return None
    try:
        loc = geolocator.geocode(location)
        if loc:
            return geodesic(GOSLAR_COORDS, (loc.latitude, loc.longitude)).km
    except:
        return None
    return None

def enrich(item):
    html = fetch_html(item["url"])
    if not html:
        return item

    soup = BeautifulSoup(html, "html.parser")
    desc_el = soup.find("div", class_=re.compile("description"))
    desc = desc_el.get_text(" ", strip=True) if desc_el else ""

    item["year"] = extract_year_from_title(item["title"])
    item["mileage"] = extract_mileage_from_title(item["title"])
    item["fuel"] = extract_fuel_from_title(item["title"])

    if item["mileage"] is None:
        item["mileage"] = extract_mileage_from_image(item["image"])

    loc_el = soup.find(string=re.compile("Standort"))
    if loc_el:
        parent = loc_el.parent
        next_el = parent.find_next("span")
        if next_el:
            item["location"] = next_el.get_text(strip=True)
        else:
            item["location"] = None
    else:
        item["location"] = None

    item["distance_km"] = compute_distance(item["location"])
    return item

def score(item):
    title = item["title"].lower()

    if any(bad in title for bad in BAD_KEYWORDS):
        return -999

    if any(engine in title for engine in BAD_ENGINES):
        return -999

    if not any(model in title for model in GOOD_MODELS):
        return -999

    score = 0
    price = item.get("price", "")
    price_val = int(re.sub(r"[^\d]", "", price)) if re.search(r"\d", price) else None

    if price_val:
        score += max(0, 10 - price_val // 1000)

    if item.get("year"):
        score += 5

    if item.get("mileage"):
        score += 5

    if item.get("fuel") == "benzin":
        score += 3

    if item.get("distance_km") is not None:
        if item["distance_km"] <= 50:
            score += 10
        elif item["distance_km"] <= 150:
            score += 5

    return score

def main():
    safe_print("Start scraper 2.4.2")

    all_items = []
    for page in range(1, 6):
        url = LIST_URL if page == 1 else f"{LIST_URL}?page={page}"
        html = fetch_html(url)
        items = parse_list(html)
        safe_print(f"Page {page}: {len(items)} items")
        all_items.extend(items)
        time.sleep(1)

    enriched = []
    for item in all_items:
        enriched_item = enrich(item)
        enriched_item["score"] = score(enriched_item)
        enriched.append(enriched_item)

    enriched.append({"timestamp": datetime.utcnow().isoformat()})

    with open("results_kleinanzeigen.json", "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=4, ensure_ascii=False)

    safe_print("Zapisano results_kleinanzeigen.json")

if __name__ == "__main__":
    main()
