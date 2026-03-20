import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta, timezone
import os

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; MalayalamOTTBot/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

PLATFORM_KEYWORDS = {
    "netflix": "Netflix",
    "prime video": "Prime Video",
    "amazon prime": "Prime Video",
    "amazon": "Prime Video",
    "jiohotstar": "JioHotstar",
    "hotstar": "JioHotstar",
    "disney+": "JioHotstar",
    "sonyliv": "SonyLIV",
    "sony liv": "SonyLIV",
    "zee5": "ZEE5",
    "manorama max": "Manorama MAX",
    "sun nxt": "Sun NXT",
    "sunnxt": "Sun NXT",
}

MONTHS = {
    "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
    "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
    "jan":1,"feb":2,"mar":3,"apr":4,"jun":6,
    "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12,
}

def parse_date(text):
    if not text: return None
    text = text.strip()
    m = re.search(r'(\w+)\s+(\d{1,2}),?\s+(20\d{2})', text)
    if m:
        month = MONTHS.get(m.group(1).lower())
        if month:
            try: return datetime(int(m.group(3)), month, int(m.group(2))).strftime('%Y-%m-%d')
            except: pass
    m = re.search(r'(\d{1,2})\s+(\w+)\s+(20\d{2})', text)
    if m:
        month = MONTHS.get(m.group(2).lower())
        if month:
            try: return datetime(int(m.group(3)), month, int(m.group(1))).strftime('%Y-%m-%d')
            except: pass
    m = re.search(r'(20\d{2})-(\d{2})-(\d{2})', text)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None

def detect_platform(text):
    if not text: return None
    t = text.lower()
    for key, val in PLATFORM_KEYWORDS.items():
        if key in t: return val
    return None

def scrape_wikipedia_year(year):
    url = f"https://en.wikipedia.org/wiki/List_of_Malayalam_films_of_{year}"
    print(f"Fetching {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        print(f"HTTP {resp.status_code}")
        if resp.status_code != 200: return []
    except Exception as e:
        print(f"Error: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    movies = []
    seen = set()
    cutoff = datetime.now() - timedelta(days=92)

    tables = soup.find_all("table", class_="wikitable")
    print(f"Found {len(tables)} tables")

    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:]:
            cols = row.find_all(["td", "th"])
            if len(cols) < 2: continue

            row_text = " ".join(col.get_text(separator=" ", strip=True) for col in cols)
            platform = detect_platform(row_text)
            if not platform: continue

            title = re.sub(r'\[\d+\]', '', cols[0].get_text(strip=True)).strip()
            if len(title) < 2 or len(title) > 100: continue

            key = title.lower()
            if key in seen: continue
            seen.add(key)

            ott_date = None
            for col in cols:
                d = parse_date(col.get_text(strip=True))
                if d:
                    ott_date = d
                    break

            if not ott_date:
                ott_date = f"{year}-06-01"

            try:
                if datetime.strptime(ott_date, '%Y-%m-%d') < cutoff: continue
            except: continue

            director = re.sub(r'\[\d+\]', '', cols[1].get_text(strip=True)).strip()[:50] if len(cols) > 1 else ""

            movies.append({
                "title": title, "platform": platform, "ottDate": ott_date,
                "genre": "", "director": director, "cast": "", "desc": "",
            })
            print(f"  FOUND: {title} -> {platform} on {ott_date}")

    return movies

def main():
    all_movies = []
    seen_titles = set()
    current_year = datetime.now().year
    for year in [current_year, current_year - 1]:
        for m in scrape_wikipedia_year(year):
            key = m['title'].lower()
            if key not in seen_titles:
                seen_titles.add(key)
                all_movies.append(m)

    all_movies.sort(key=lambda x: x.get('ottDate', ''), reverse=True)
    print(f"\nTotal: {len(all_movies)} movies")

    output = {
        "updated": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        "count": len(all_movies),
        "movies": all_movies,
    }
    os.makedirs("public", exist_ok=True)
    with open("public/data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Saved public/data.json ({len(all_movies)} movies)")

if __name__ == "__main__":
    main()
