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

# ============================
#   TOP 10 MODELE
# ============================
TOP10_MODELS = [
    "toyota yaris hybrid",
    "toyota auris hybrid",
    "kia stonic 1.4",
    "skoda rapid 1.6",
    "kia ceed 1.4",
    "kia ceed 1.6",
    "opel corsa 1.2",
    "opel corsa 1.4",
    "mazda 2 1.5",
    "mazda 3 2.0",
    "mazda cx-3 2.0",
]

def match_top10_model(title):
    t = title.lower()
    for model in TOP10_MODELS:
        if model in t:
            return model
    return None


# ============================
#   FILTR TOP 10 (bez segmentu/silnika/wyposażenia)
# ============================
def is_top10(item):
    title = item.get("title", "").lower()

    # 1. Model musi być w TOP 10
    model = match_top10_model(title)
    if not model:
        return False

    # 2. Cena ≤ 8000 €
    price_value = item.get("price_value")
    if price_value is None or price_value > 8000:
        return False

    # 3. Rocznik ≥ 2017
    year = item.get("year")
    if year is None or year < 2017:
        return False

    # UWAGA: usunięte filtry:
    # - segment
    # - typ silnika (wolnossący/hybrydowy)
    # - wyposażenie (CarPlay / PDC / podłokietnik)

    return True


# ============================
#   SCORING TOP 10
# ============================
def score_top10(item):
    score = 0

    model = match_top10_model(item.get("title", ""))
    if model:
        score += 20

    year = item.get("year")
    if year:
        if year >= 2020:
            score += 10
        elif year >= 2017:
            score += 5

    mileage = item.get("mileage")
    if mileage:
        if mileage <= 120000:
            score += 10
        elif mileage <= 160000:
            score += 5

    if item.get("has_carplay"):
        score += 5
    if item.get("has_armrest"):
        score += 3

    item["score_top10"] = score
    return score


# ============================
#   SCRAPER 2.0
# ============================
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
                "platform": "kleinanzeigen"
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
                key = label.get_text(strip=True).lower()
                val = value.get_text(strip=True)
                details[key] = val

    for dt, dd in zip(soup.find_all("dt"), soup.find_all("dd")):
        key = dt.get_text(strip=True).lower()
        value = dd.get_text(strip=True)
        details[key] = value

    return details


def extract_year_from_details(details):
    for key, value in details.items():
        if any(k in key for k in ["ez", "baujahr", "bj"]):
            m = re.search(r"(19[8-9]\d|20[0-3]\d)", value)
            if m:
                return int(m.group(1))
    return None


def extract_year_from_description(desc):
    m = re.search(r"(EZ|Baujahr|Bj\.?)\s*(19[8-9]\d|20[0-3]\d)", desc, re.IGNORECASE)
    if m:
        return int(m.group(2))
    return None


def extract_year_from_title(title):
    m = re.search(r"(Bj\.?\s*(19[8-9]\d|20[0-3]\d))", title, re.IGNORECASE)
    if m:
        return int(m.group(2))
    return None


def extract_mileage_from_details(details):
    for key, value in details.items():
        m = re.search(r"(\d{2,3}[.\s]?\d{3})\s*(km|KM|Km)", value)
        if m:
            raw = m.group(1).replace(".", "").replace(" ", "")
            if raw.isdigit():
                return int(raw)
    return None


def extract_mileage_from_description(desc):
    m = re.search(r"(\d{2,3}[.\s]?\d{3})\s*(km|KM|Km)", desc)
    if m:
        raw = m.group(1).replace(".", "").replace(" ", "")
        if raw.isdigit():
            return int(raw)
    return None


def extract_mileage_from_title(title):
    t = title.lower()

    patterns = [
        r"(\d{1,3})\s*tkm",
        r"(\d{1,3})\s*t\s*km",
        r"(\d{1,3}[.]\d{3})",
        r"(\d{2,3}[.\s]?\d{3})\s*km"
    ]

    for p in patterns:
        m = re.search(p, t)
        if m:
            raw = m.group(1).replace(".", "").replace(" ", "")
            if raw.isdigit():
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


def extract_fuel_from_title(title):
    t = title.lower()
    if any(x in t for x in ["tdi", "dci", "cdti", "hdi"]):
        return "diesel"
    if any(x in t for x in ["benz", "benzin"]):
        return "benzin"
    if "hybrid" in t:
        return "hybrid"
    if "elektro" in t or "ev" in t:
        return "strom"
    return None


def extract_location(soup, desc):
    loc_el = soup.find(string=re.compile("Standort"))
    if loc_el:
        parent = loc_el.parent
        next_el = parent.find_next("span")
        if next_el:
            txt = next_el.get_text(strip=True)
            if re.search(r"\d{2,3}[.\s]?\d{3}\s*km", txt.lower()):
                return None
            return txt

    m = re.search(r"(steht in|location|ort)\s*([A-Za-zäöüÄÖÜß ]+)", desc, re.IGNORECASE)
    if m:
        candidate = m.group(2).strip()
        if not re.search(r"\d", candidate):
            return candidate

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


def parse_price(price):
    if not price:
        return None

    cleaned = re.sub(r"[^\d.]", "", price)

    if "." in cleaned:
        parts = cleaned.split(".")
        if len(parts) > 2:
            cleaned = parts[0] + parts[1]
        else:
            cleaned = cleaned.replace(".", "")

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
        or extract_fuel_from_title(title)
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


# ============================
#   MAIN
# ============================
def main():
    all_list_items = []

    for page in range(1, 6):
        url = LIST_URL if page == 1 else f"{LIST_URL}?page={page}"

        try:
            list_html = fetch_html(url)
        except:
            continue

        page_items = parse_list(list_html)
        print(f"Strona {page}: znaleziono {len(page_items)} ogłoszeń")
        all_list_items.extend(page_items)
        time.sleep(1)

    unique = {}
    for item in all_list_items:
        unique[item["url"]] = item
    all_list_items = list(unique.values())

    enriched = []
    for item in all_list_items:
        detail = fetch_and_enrich(item)
        if detail:
            detail["price_value"] = parse_price(detail["price"])
            if is_top10(detail):
                enriched.append(detail)
        time.sleep(1)

    for item in enriched:
        score_top10(item)

    enriched.sort(key=lambda x: x.get("score_top10", 0), reverse=True)

    with open("results_kleinanzeigen.json", "w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=4, ensure_ascii=False)

    print("Zapisano results_kleinanzeigen.json — FILTR TOP 10 (bez segmentu/silnika/wyposażenia)")


if __name__ == "__main__":
    main()
