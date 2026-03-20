import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta, timezone
import os
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

PLATFORM_MAP = {
    "netflix": "Netflix",
    "prime video": "Prime Video",
    "amazon prime": "Prime Video",
    "jiohotstar": "JioHotstar",
    "hotstar": "JioHotstar",
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
}

def parse_date(text):
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
    return None

def normalise_platform(text):
    t = text.strip().lower()
    for key, val in PLATFORM_MAP.items():
        if key in t:
            return val
    return None

def scrape():
    url = "https://www.filmibeat.com/top-listing/new-ott-release-movies-in-malayalam-this-week-4-1087.html"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.google.com/",
    }
    
    print(f"Fetching {url}")
    resp = requests.get(url, headers=headers, timeout=30)
    print(f"HTTP {resp.status_code}")
    
    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Print first 3000 chars of page text so we can see the structure
    text = soup.get_text(separator='\n')
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    print("\n--- FIRST 50 LINES OF PAGE ---")
    for i, line in enumerate(lines[:50]):
        print(f"{i}: {line}")
    print("--- END SAMPLE ---\n")
    
    movies = []
    seen = set()
    cutoff = datetime.now() - timedelta(days=92)

    # Try multiple patterns to match FilmiBeat's text
    patterns = [
        re.compile(r'^(.+?)\s+(?:started|began)\s+streaming\s+on\s+(.+?)\s+(?:on|from)\s+(.+)', re.IGNORECASE),
        re.compile(r'^(.+?)\s+(?:will\s+start|starts?)\s+streaming\s+on\s+(.+?)\s+(?:on|from|in)\s+(.+)', re.IGNORECASE),
        re.compile(r'^(.+?)\s+(?:is\s+now\s+streaming|now\s+streaming)\s+on\s+(.+)', re.IGNORECASE),
        re.compile(r'^(.+?)\s+OTT\s+(?:release|premiere).+?(?:on|via)\s+(.+?)\s+(?:on|from)\s+(.+)', re.IGNORECASE),
    ]
    
    for i, line in enumerate(lines):
        for pattern in patterns:
            m = pattern.match(line)
            if not m:
                continue
            
            groups = m.groups()
            raw_title = groups[0].strip()
            raw_platform = groups[1].strip() if len(groups) > 1 else ""
            raw_date = groups[2].strip() if len(groups) > 2 else ""
            
            title = re.sub(r'^[^a-zA-Z]+', '', raw_title).strip()
            if len(title) < 2 or len(title) > 100:
                continue
            
            platform = normalise_platform(raw_platform)
            if not platform:
                continue
            
            ott_date = parse_date(raw_date)
            if not ott_date:
                continue
            
            try:
                if datetime.strptime(ott_date, '%Y-%m-%d') < cutoff:
                    continue
            except:
                continue
            
            key = title.lower()
            if key in seen:
                continue
            seen.add(key)
            
            movies.append({
                "title": title, "platform": platform, "ottDate": ott_date,
                "genre": "", "director": "", "cast": "", "desc": "",
            })
            print(f"  FOUND: {title} → {platform} on {ott_date}")
            break
    
    movies.sort(key=lambda x: x['ottDate'], reverse=True)
    print(f"\nTotal: {len(movies)} movies found")
    return movies

def main():
    movies = scrape()
    output = {
        "updated": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        "count": len(movies),
        "movies": movies,
    }
    os.makedirs("public", exist_ok=True)
    with open("public/data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Saved public/data.json ({len(movies)} movies)")

if __name__ == "__main__":
    main()
