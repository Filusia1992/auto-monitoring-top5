import json
import re

# Wczytaj dane z Kleinanzeigen
with open("results_kleinanzeigen.json", "r", encoding="utf-8") as f:
    data = json.load(f)

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

# Filtr: czy to jest samochód z Twojej listy
def is_car(item):
    title = item["title"].lower()

    # odrzucamy części/akcesoria
    if any(bad in title for bad in BAD_KEYWORDS):
        return False

    # odrzucamy GR Yaris (sportowy)
    if "gr yaris" in title:
        return False

    # odrzucamy ogłoszenia "suche"
    if "suche" in title:
        return False

    # odrzucamy złe silniki (EcoBoost)
    if any(engine in title for engine in BAD_ENGINES):
        return False

    # akceptujemy tylko modele z Twojej listy
    if any(model in title for model in GOOD_MODELS):
        return True

    return False

# Konwersja ceny na liczbę (w euro)
def parse_price(price):
    price = price.lower().replace("€", "").replace("vb", "").replace(".", "").replace(" ", "")
    try:
        return int(price)
    except:
        return None

# Próba wyciągnięcia rocznika z tytułu
def extract_year(title):
    years = re.findall(r"\b(20[0-3][0-9])\b", title)
    if not years:
        return None
    try:
        return int(years[0])
    except:
        return None

# Próba wyciągnięcia przebiegu z tytułu
def extract_mileage(title):
    match = re.search(r"(\d{2,3}[.\s]?\d{3})\s*km", title.lower())
    if not match:
        return None
    raw = match.group(1)
    raw = raw.replace(".", "").replace(" ", "")
    try:
        return int(raw)
    except:
        return None

# Filtrowanie samochodów zgodnie z Twoimi kryteriami
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

    # rocznik ≥ 2017 (jeśli podany)
    if year is not None and year < 2017:
        continue

    # przebieg ≤ 150000 km (jeśli podany)
    if mileage is not None and mileage > 150000:
        continue

    item["price_value"] = price_value
    item["year"] = year
    item["mileage"] = mileage
    cars.append(item)

# Sortowanie po cenie
cars.sort(key=lambda x: x["price_value"])

# Wynik końcowy
print("\n=== Auta pasujące do Twoich kryteriów (Kleinanzeigen) ===\n")
if not cars:
    print("Brak aut spełniających Twoje kryteria w dzisiejszych wynikach.")
else:
    for car in cars:
        year_str = f"{car['year']}" if car.get("year") else "brak rocznika"
        mileage_str = f"{car['mileage']} km" if car.get("mileage") else "brak przebiegu"
        print(f"{car['title']} — {car['price']} — {year_str} — {mileage_str} — {car['url']}")
