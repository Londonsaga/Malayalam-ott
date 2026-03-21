import json, re, os
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

MONTHS = {
    "january":1,"february":2,"march":3,"april":4,"may":5,"june":6,
    "july":7,"august":8,"september":9,"october":10,"november":11,"december":12,
    "jan":1,"feb":2,"mar":3,"apr":4,"jun":6,
    "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12,
}

PLATFORM_MAP = {
    "netflix":"Netflix","prime video":"Prime Video","amazon prime":"Prime Video",
    "jiohotstar":"JioHotstar","hotstar":"JioHotstar","disney+":"JioHotstar",
    "sonyliv":"SonyLIV","sony liv":"SonyLIV","zee5":"ZEE5",
    "manorama max":"Manorama MAX","sun nxt":"Sun NXT","sunnxt":"Sun NXT",
}

DUBBED = {"nari nari naduma murari","made in korea","lucky: the superstar","mirai"}

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

def scrape():
    url = "https://www.filmibeat.com/top-listing/new-ott-release-movies-in-malayalam-this-week-4-1087.html"
    movies = []
    seen = set()
    cutoff = datetime.now() - timedelta(days=92)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36")
        print(f"Opening {url}")
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)
        content = page.inner_text("body")
        browser.close()

    print(f"Got {len(content)} chars")
    lines = [l.strip() for l in content.split('\n') if l.strip()]

    pattern = re.compile(
        r'^(.+?)\s+(?:started|began|will start)\s+streaming\s+on\s+(.+?)\s+(?:on|from|in)\s+(.+)',
        re.IGNORECASE
    )

    for i, line in enumerate(lines):
        m = pattern.match(line)
        if not m: continue
        title = re.sub(r'^[^a-zA-Z]+', '', m.group(1)).strip()
        platform = detect_platform(m.group(2))
        ott_date = parse_date(m.group(3))
        if not title or not platform or not ott_date: continue
        if title.lower() in DUBBED: continue
        if len(title) < 2 or len(title) > 100: continue
        try:
            if datetime.strptime(ott_date, '%Y-%m-%d') < cutoff: continue
        except: continue
        key = title.lower()
        if key in seen: continue
        seen.add(key)
        desc = ""
        for j in range(i+1, min(i+4, len(lines))):
            if len(lines[j]) > 40 and not pattern.match(lines[j]):
                desc = lines[j][:200]
                break
        movies.append({"title":title,"platform":platform,"ottDate":ott_date,"genre":"","director":"","cast":"","desc":desc})
        print(f"  FOUND: {title} -> {platform} on {ott_date}")

    movies.sort(key=lambda x: x['ottDate'], reverse=True)
    print(f"Total: {len(movies)} movies")
    return movies

def main():
    movies = scrape()
    os.makedirs("public", exist_ok=True)
    with open("public/data.json", "w", encoding="utf-8") as f:
        json.dump({"updated": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), "count": len(movies), "movies": movies}, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(movies)} movies")

if __name__ == "__main__":
    main()
