import requests
from bs4 import BeautifulSoup
import json, re, os
from datetime import datetime, timedelta, timezone

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.google.com/",
}

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        print(f"  {url} -> HTTP {r.status_code}")
        if r.status_code == 200: return r.text
    except Exception as e:
        print(f"  Error: {e}")
    return None

def main():
    sources = [
        "https://www.ottplay.com/news/latest-malayalam-movies-web-series-2022-on-ott-netflix-prime-video-disney-hotstar-neestream-and-others/451777f0f1884/1000",
        "https://cinebuds.com/malayalam-movies-ott-release-dates/",
    ]

    for url in sources:
        print(f"\n=== {url} ===")
        html = fetch(url)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator='\n')
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        print(f"Total lines: {len(lines)}")
        print("--- LINES 100 to 200 ---")
        for i, line in enumerate(lines[100:200], start=100):
            print(f"{i}: {line}")

    os.makedirs("public", exist_ok=True)
    with open("public/data.json", "w") as f:
        json.dump({"updated": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), "count": 0, "movies": []}, f)

if __name__ == "__main__":
    main()
