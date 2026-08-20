import json
import requests

URL = "https://www.autoscout24.com/api/vehiclelisting/search?make=toyota&model=yaris&fuel=hybrid&pricefrom=1000&priceto=8000&yearfrom=2016&yearto=2023&kmto=150000"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

def main():
    r = requests.get(URL, headers=HEADERS)
    r.raise_for_status()
    data = r.json()

    results = []

    for item in data.get("listings", []):
        results.append({
            "title": item.get("title"),
            "price": item.get("price", {}).get("raw"),
            "year": item.get("vehicle", {}).get("firstRegistrationYear"),
            "mileage": item.get("vehicle", {}).get("mileage"),
            "image": item.get("images", [{}])[0].get("url"),
            "url": "https://www.autoscout24.com" + item.get("url", ""),
            "platform": "autoscout24"
        })

    with open("results_autoscout.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()
