import json
import requests

SEARCH_URLS = [
    # Kia Stonic
    "https://suchen.mobile.de/fahrzeuge/api/search?vc=Car&makeModelVariant1.makeId=24100&makeModelVariant1.modelId=14&maxPrice=8000&minYear=2018&maxMileage=150000&zipcode=38690&radius=300",
    
    # Skoda Rapid
    "https://suchen.mobile.de/fahrzeuge/api/search?vc=Car&makeModelVariant1.makeId=24100&makeModelVariant1.modelId=19&maxPrice=8000&minYear=2016&maxMileage=180000&zipcode=38690&radius=300",
    
    # Kia Ceed
    "https://suchen.mobile.de/fahrzeuge/api/search?vc=Car&makeModelVariant1.makeId=17200&makeModelVariant1.modelId=57&maxPrice=8000&minYear=2018&maxMileage=150000&zipcode=38690&radius=300"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
}

def fetch_api(url):
    """Fetches JSON data from mobile.de API."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def parse_results(data, source_url):
    """Extracts car listings from API JSON."""
    results = []

    if not data or "items" not in data:
        return results

    for item in data["items"]:
        try:
            title = item.get("title", "")
            price = item.get("price", {}).get("price", None)
            year = item.get("firstRegistrationYear", None)
            mileage = item.get("mileage", None)
            images = item.get("images", [])
            image_url = images[0]["url"] if images else None
            detail_url = item.get("url", None)

            results.append({
                "title": title,
                "price": price,
                "year": year,
                "mileage": mileage,
                "image": image_url,
                "url": f"https://suchen.mobile.de{detail_url}" if detail_url else None,
                "source": source_url,
                "platform": "mobile.de"
            })
        except:
            continue

    return results

def main():
    all_results = []

    for url in SEARCH_URLS:
        data = fetch_api(url)
        parsed = parse_results(data, url)
        all_results.extend(parsed)

    with open("results_mobile.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()
