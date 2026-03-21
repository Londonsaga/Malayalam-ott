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

PLATFORM_MAP = {
    "netflix": "Netflix",
    "prime video": "Prime Video", "amazon prime": "Prime Video",
    "jiohotstar": "JioHotstar", "hotstar": "JioHotstar", "jiohoststar": "JioHotstar",
    "sonyliv": "SonyLIV", "sony liv": "SonyLIV",
    "zee5": "ZEE5", "zee 5": "ZEE5",
    "manorama max": "Manorama MAX",
    "sun nxt": "Sun NXT", "sunnxt": "Sun NXT",
}

MONTHS = {
    "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
    "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
    "jan":1,"feb":2,"mar":3,"apr":4,"jun":6,
    "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12,
}

DUBBED = {
    "nari nari naduma murari","made in korea","lucky: the superstar",
    "mirai","tourist family","khajuraho dreams",
}

def is_platform(text):
    t = text.lower().strip()
    for key in PLATFORM_MAP:
        if key in t:
            return PLATFORM_MAP[key]
    return None

def is_date(text):
    text = text.strip()
    # "March 13" or "January 30" — month + day, no year
    m = re.match(r'^(\w+)\s+(\d{1,2})$', text)
    if m:
        month = MONTHS.get(m.group(1).lower())
        if month:
            year = datetime.now().year
            # If month is ahead of current month by a lot, it's previous year
            try:
                d = datetime(year, month, int(m.group(2)))
                # If date is more than 3 months in future, use previous year
                if d > datetime.now() + timedelta(days=30):
                    d = datetime(year - 1, month, int(m.group(2)))
                return d.strftime('%Y-%m-%d')
            except: pass
    # "March 13, 2026"
    m = re.search(r'(\w+)\s+(\d{1,2}),?\s+(20\d{2})', text)
    if m:
        month = MONTHS.get(m.group(1).lower())
        if month:
            try: return datetime(int(m.group(3)), month, int(m.group(2))).strftime('%Y-%m-%d')
            except: pass
    return None

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        print(f"  HTTP {r.status_code}")
        if r.status_code == 200: return r.text
    except Exception as e:
        print(f"  Error: {e}")
    return None

def scrape_ottplay(html):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator='\n')
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    movies = []
    seen = set()
    cutoff = datetime.now() - timedelta(days=92)
    i = 0

    while i < len(lines) - 2:
        title = lines[i]
        date_str = lines[i+1]
        platform_str = lines[i+2]

        ott_date = is_date(date_str)
        platform = is_platform(platform_str)

        if ott_date and platform:
            # Clean title
            title = re.sub(r'\[\d+\]', '', title).strip()
            if 2 < len(title) < 100 and title.lower() not in DUBBED:
                try:
                    if datetime.strptime(ott_date, '%Y-%m-%d') >= cutoff:
                        key = title.lower()
                        if key not in seen:
                            seen.add(key)
                            movies.append({
                                "title": title,
                                "platform": platform,
                                "ottDate": ott_date,
                                "genre": "", "director": "", "cast": "", "desc": "",
                            })
                            print(f"  FOUND: {title} -> {platform} on {ott_date}")
                except: pass
            i += 3
        else:
            i += 1

    return movies

def main():
    url = "https://www.ottplay.com/news/latest-malayalam-movies-web-series-2022-on-ott-netflix-prime-video-disney-hotstar-neestream-and-others/451777f0f1884/1000"
    print(f"Fetching OTTplay...")
    html = fetch(url)

    movies = []
    if html:
        movies = scrape_ottplay(html)
        print(f"Found {len(movies)} movies")
    else:
        print("Failed to fetch")

    movies.sort(key=lambda x: x.get('ottDate',''), reverse=True)

    os.makedirs("public", exist_ok=True)
    with open("public/data.json", "w", encoding="utf-8") as f:
        json.dump({
            "updated": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "count": len(movies),
            "movies": movies,
        }, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(movies)} movies to public/data.json")

if __name__ == "__main__":
    main()
