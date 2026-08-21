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

TELEGRAM_TOKEN = ""   # wstaw swój token
TELEGRAM_CHAT_ID = "" # wstaw swój chat_id

GOSLAR_COORDS = (51.904, 10.427)

def send_telegram(msg):
    if TELEGRAM_TOKEN == "" or TELEGRAM_CHAT_ID == "":
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})

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
        details[dt.get_text(strip=True).lower()] = dd.get_text(strip=True)
    return details

def extract_mileage_from_image(image_url):
    try:
        img_data = requests.get(image_url, timeout=5).content
        img = Image.open(BytesIO(img_data))
        text = pytesseract.image_to_string(img)
        m = re.search(r"(\d{2,3}[.\s]?\d{3})", text)
        if m:
            return int(m.group(1).replace(".", "").replace(" ", ""))
    except:
        return None
    return None

def extract_year_from_title(title):
    m = re.search(r"(19[8-9]\d|20[0-3]\d)", title)
    return int(m.group(1)) if m else None

def extract_tuv_year(desc):
    m = re.search(r"TÜV\s*(\d{2})/(\d{2})", desc, re.IGNORECASE)
    return int("20" + m.group(2)) if m else None

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
            return int(raw) if raw.isdigit() else None
    return None

def extract_fuel_from_title(title):
    t = title.lower()
    if any(x in t for x in ["cdti", "tdi", "dci", "hdi"]):
        return "diesel"
    if any(x in t for x in ["1.0", "1.2", "1.3", "1.4", "1.6", "2.0"]):
        return "benzin"
    return None

geolocator = Nominatim(user_agent="scraper24")

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

def is_car_basic(item):
    title = item["title"].lower()

    if any(bad in title for bad in BAD_KEYWORDS):
        return False

    if any(engine in title for engine in BAD_ENGINES):
        return False

    # zamiast odrzucać — zapisujemy, ale score = -999
    if not any(model in title for model in GOOD_MODELS):
        item["score"] = -999
        return True

    return True

def parse_price(price):
    if not price:
        return None
    p = re.sub(r"[€\s]|vb", "", price.lower()).replace(".", "")
    m = re.search(r"(\d+)", p)
    return int(m.group(1)) if m else None

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

    year = extract_year_from_title(title)
    mileage = extract_mileage_from_title(title)
    fuel = extract_fuel_from_title(title)
    tuv_year = extract_tuv_year(description)

    if mileage is None and item["image"]:
        mileage = extract_mileage_from_image(item["image"])

    location = None
    loc_el = soup.find(string=re.compile("Standort"))
    if loc_el:
        parent = loc_el.parent
        next_el = parent.find_next("span")
        if next_el:
            location = next_el.get_text(strip=True)

    distance = compute_distance(location)

    item["year"] = year
    item["mileage"] = mileage
    item["fuel"] = fuel
    item["tuv_year"] = tuv_year
    item["location"] = location
    item["distance_km"] = distance

    return item

def score_item(item):
    if item.get("score") == -999:
        return -999

    score = 0
    title = item["title"].lower()
    price_value = parse_price(item["price"])
    year = item.get("year")
    mileage = item.get("mileage")
    fuel = item.get("fuel")
    tuv_year = item.get("tuv_year")
    distance = item.get("distance_km")

    if price_value is None or price_value > 9000:
        return -50

    score += 10
    score += max(0, 10 - (price_value // 1000))

    if year:
        score += 10 if year >= 2017 else 5 if year >= 2010 else -5

    if mileage:
        score += 10 if mileage <= 150000 else 3 if mileage <= 220000 else -5

    if fuel:
        score += 5 if fuel in ["benzin", "hybrid", "strom"] else -2

    if tuv_year:
        score += 5 if tuv_year >= 2027 else 0
        score += 8 if tuv_year >= 2028 else 0

    if distance:
        score += 10 if distance <= 50 else 5 if distance <= 150 else 2 if distance <= 300 else 0

    item["score"] = score
    return score

def main():
    all_items = []

    for page in range(1, 6):
        url = LIST_URL if page == 1 else f"{LIST_URL}?page={page}"
        try:
            list_html = fetch_html(url)
        except:
            continue
        all_items.extend(parse_list(list_html))
        time.sleep(1)

    seen = set()
    unique_items = []
    for item in all_items:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique_items.append(item)

    enriched = []
    for item in unique_items:
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
