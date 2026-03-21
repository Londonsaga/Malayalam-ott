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
    "prime video": "Prime Video", "amazon prime": "Prime Video", "amazon": "Prime Video",
    "jiohotstar": "JioHotstar", "hotstar": "JioHotstar", "disney+": "JioHotstar",
    "sonyliv": "SonyLIV", "sony liv": "SonyLIV",
    "zee5": "ZEE5",
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
    "mirai","tourist family","kantara chapter 1","bison",
}

def parse_date(text):
    if not text: return None
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

def detect_platform(text):
    t = text.lower()
    for key, val in PLATFORM_MAP.items():
        if key in t: return val
    return None

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        print(f"  {url} -> HTTP {r.status_code}")
        if r.status_code == 200: return r.text
    except Exception as e:
        print(f"  Error: {e}")
    return None

def extract_movies(html, cutoff):
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator='\n')
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    movies = []
    seen = set()
    
    stream_pattern = re.compile(
        r'^(.+?)\s+(?:started|begins?|began|will\s+start|starts?|is\s+now)\s+streaming\s+on\s+(.+?)\s+(?:on|from|starting)?\s*((?:\w+\s+\d{1,2},?\s+20\d{2}|\d{1,2}\s+\w+\s+20\d{2}))',
        re.IGNORECASE
    )
    on_pattern = re.compile(
        r'^(.+?)\s+(?:on|via|streaming\s+on|available\s+on)\s+(.+?)\s+(?:from|on|starting)?\s*((?:\w+\s+\d{1,2},?\s+20\d{2}|\d{1,2}\s+\w+\s+20\d{2}))',
        re.IGNORECASE
    )

    for i, line in enumerate(lines):
        for pattern in [stream_pattern, on_pattern]:
            m = pattern.match(line)
            if not m: continue
            
            title = re.sub(r'\[\d+\]', '', m.group(1)).strip()
            title = re.sub(r'^[^a-zA-Z]+', '', title).strip()
            platform = detect_platform(m.group(2))
            ott_date = parse_date(m.group(3))
            
            if not title or not platform or not ott_date: continue
            if len(title) < 2 or len(title) > 100: continue
            if title.lower() in DUBBED: continue
            
            try:
                if datetime.strptime(ott_date, '%Y-%m-%d') < cutoff: continue
            except: continue
            
            key = title.lower()
            if key in seen: continue
            seen.add(key)
            
            desc = ""
            for j in range(i+1, min(i+4, len(lines))):
                if len(lines[j]) > 40 and not stream_pattern.match(lines[j]):
                    desc = lines[j][:200]
                    break
            
            movies.append({
                "title": title, "platform": platform, "ottDate": ott_date,
                "genre": "", "director": "", "cast": "", "desc": desc,
            })
            print(f"  FOUND: {title} -> {platform} on {ott_date}")
            break
    
    return movies

def main():
    cutoff = datetime.now() - timedelta(days=92)
    all_movies = []
    seen_titles = set()

    # Try multiple sources
    sources = [
        "https://www.ottplay.com/news/latest-malayalam-movies-web-series-2022-on-ott-netflix-prime-video-disney-hotstar-neestream-and-others/451777f0f1884/1000",
        "https://cinebuds.com/malayalam-movies-ott-release-dates/",
        "https://telugu-kathalu.com/new-malayalam-ott-releases-march-2026-latest-streaming-movies-must-watch-updates/",
    ]

    for url in sources:
        print(f"\nTrying: {url}")
        html = fetch(url)
        if not html:
            print("  Failed to fetch")
            continue
        
        movies = extract_movies(html, cutoff)
        print(f"  Extracted {len(movies)} movies")
        
        for m in movies:
            key = m['title'].lower()
            if key not in seen_titles:
                seen_titles.add(key)
                all_movies.append(m)

    all_movies.sort(key=lambda x: x.get('ottDate',''), reverse=True)
    print(f"\nTotal: {len(all_movies)} movies")

    os.makedirs("public", exist_ok=True)
    with open("public/data.json", "w", encoding="utf-8") as f:
        json.dump({
            "updated": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "count": len(all_movies),
            "movies": all_movies,
        }, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(all_movies)} movies to public/data.json")

if __name__ == "__main__":
    main()
