import json
import re
import requests
from bs4 import BeautifulSoup

URL = "https://www.kleinanzeigen.de/s-autos/k0"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
}

# MODELE, KTÓRE CIĘ INTERESUJĄ
GOOD_MODELS = [
    "yaris", "auris", "stonic", "rapid", "ceed",
    "astra", "corsa", "fiesta", "focus", "cupra"
]

# Słowa kluczowe dla części i śmieci
BAD_KEYWORDS = [
    "scheinwerfer", "kotflügel", "rücklicht", "felge", "stoßstange",
    "lenkgetriebe", "schaltknauf", "instandsetzung", "blenden",
    "konsole", "motorhaube", "fensterheberschalter", "traggelenk",
    "rad", "konsolenumrandung", "xp", "pdc"
]

# Złe silniki (Ford EcoBoost)
BAD_ENGINES = [
    "ecoboost", "1.0", "1,0", "1.5 ecoboost", "1,5 ecoboost"
]

def fetch_html(url):
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    return r.text

def parse_html(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    cars = soup.select("article.aditem")

    for car in cars:
        try:
            title = car.select_one(".text-module-begin")
            title = title.get_text(strip=True) if title else None

            price = car.select_one(".aditem-main--middle--price-shipping--price")
            price = price.get_text(strip=True) if price else None

            img = car.select_one("img")
            image_url = img["src"] if img and "src" in img.attrs else None

            link = car.select_one("a")
            detail_url = "https://www.kleinanzeigen.de" + link["href"] if link else None

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

# --- FILTRY TWOICH KRYTERIÓW ---

def is_car(item):
    title = item["title"].lower()

    if any(bad in title for bad in BAD_KEYWORDS):
        return False

    if "gr yaris" in title:
        return False

    if "suche" in title:
        return False

    if any(engine in title for engine in BAD_ENGINES):
        return False

    if any(model in title for model in GOOD_MODELS):
        return True

    return False

def parse_price(price):
    price = price.lower().replace("€", "").replace("vb", "").replace(".", "").replace(" ", "")
    try:
        return int(price)
    except:
        return None

def extract_year(title):
    years = re.findall(r"\b(20[0-3][0-9])\b", title)
    if not years:
        return None
    try:
        return int(years[0])
    except:
        return None

def extract_mileage(title):
    match = re.search(r"(\d{2,3}[.\s]?\d{3})\s*km", title.lower())
    if not match:
        return None
    raw = match.group(1).replace(".", "").replace(" ", "")
    try:
        return int(raw)
    except:
        return None

def filter_results(data):
    cars = []

    for item in data:
        if not is_car(item):
            continue

        title = item["title"]
        price_value = parse_price(item["price"])
        year = extract_year(title)
        mileage = extract_mileage(title)

        # cena ≤ 9000
        if price_value is None or price_value > 9000:
            continue

        # rocznik ≥ 2017
        if year is not None and year < 2017:
            continue

        # przebieg ≤ 150000
        if mileage is not None and mileage > 150000:
            continue

        item["price_value"] = price_value
        item["year"] = year
        item["mileage"] = mileage
        cars.append(item)

    cars.sort(key=lambda x: x["price_value"])
    return cars

# --- MAIN ---

def main():
    html = fetch_html(URL)
    raw_results = parse_html(html)

    # zapis surowych danych
    with open("results_kleinanzeigen.json", "w", encoding="utf-8") as f:
        json.dump(raw_results, f, indent=4, ensure_ascii=False)

    # analiza wg Twoich kryteriów
    filtered = filter_results(raw_results)

    print("\n=== Auta pasujące do Twoich kryteriów (Kleinanzeigen) ===\n")
    if not filtered:
        print("Brak aut spełniających Twoje kryteria w dzisiejszych wynikach.")
    else:
        for car in filtered:
            year_str = f"{car['year']}" if car.get("year") else "brak rocznika"
            mileage_str = f"{car['mileage']} km" if car.get("mileage") else "brak przebiegu"
            print(f"{car['title']} — {car['price']} — {year_str} — {mileage_str} — {car['url']}")

if __name__ == "__main__":
    main()
