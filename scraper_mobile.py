import json
import requests

API_URL = "https://suchen.mobile.de/fahrzeuge/api/search?isSearchRequest=true&vc=Car&cn=DE&dam=false&fr=2016:2023&ml=:150000&p=4500:8500&gn=30823&rd=300&ft=PETROL&ft=HYBRID"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
}

def fetch_api(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print("API error:", e)
        return None

def parse_results(data):
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
                "platform": "mobile.de"
            })
        except:
            continue

    return results

def main():
    data = fetch_api(API_URL)
    results = parse_results(data)

    with open("results_mobile.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()
