import json
import requests
from bs4 import BeautifulSoup

URL = "https://suchen.mobile.de/fahrzeuge/search.html?isSearchRequest=true&s=Car&vc=Car&cn=DE&dam=false&fr=2016%3A2023&ml=%3A150000&p=4500%3A8500&gn=30823%2C+Garbsen%2C+Niedersachsen&rd=300&ll=52.4158598%2C9.5850153&asl=true&ft=PETROL&ft=HYBRID&ref=dsp"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}

def fetch_html(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print("HTML error:", e)
        return None

def parse_html(html):
    soup = BeautifulSoup(html, "html.parser")
    results = []

    # Każde ogłoszenie jest w <article>
    cars = soup.find_all("article")

    for car in cars:
        try:
            title = car.find("h3")
            title = title.get_text(strip=True) if title else None

            price = car.find("span", {"class": "price-block__price"})
            price = price.get_text(strip=True) if price else None

            year = car.find("span", {"class": "vehicle-data__year"})
            year = year.get_text(strip=True) if year else None

            mileage = car.find("span", {"class": "vehicle-data__mileage"})
            mileage = mileage.get_text(strip=True) if mileage else None

            img = car.find("img")
            image_url = img["src"] if img and "src" in img.attrs else None

            link = car.find("a")
            detail_url = "https://suchen.mobile.de" + link["href"] if link and "href" in link.attrs else None

            results.append({
                "title": title,
                "price": price,
                "year": year,
                "mileage": mileage,
                "image": image_url,
                "url": detail_url,
                "platform": "mobile.de"
            })
        except:
            continue

    return results

def main():
    html = fetch_html(URL)
    results = parse_html(html)

    with open("results_mobile.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    main()
