"""
Scrapes FilmiBeat's Malayalam OTT releases page and saves to public/data.json
Runs daily via GitHub Actions - completely free, no API keys needed
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta
import os

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

URL = "https://www.filmibeat.com/top-listing/new-ott-release-movies-in-malayalam-this-week-4-1087.html"

# Map platform name variations to our standard names
PLATFORM_MAP = {
    "netflix": "Netflix",
    "amazon prime video": "Prime Video",
    "prime video": "Prime Video",
    "amazon prime": "Prime Video",
    "jiohotstar": "JioHotstar",
    "hotstar": "JioHotstar",
    "disney+ hotstar": "JioHotstar",
    "disney+hotstar": "JioHotstar",
    "sonyliv": "SonyLIV",
    "sony liv": "SonyLIV",
    "zee5": "ZEE5",
    "manorama max": "Manorama MAX",
    "manoramamax": "Manorama MAX",
    "sun nxt": "Sun NXT",
    "sunnxt": "Sun NXT",
}

# Films known to be dubbed (not original Malayalam) - skip these
DUBBED = {
    "nari nari naduma murari", "made in korea", "lucky: the superstar",
    "mana shankara vara prasad garu", "mirai", "tourist family",
    "kantara chapter 1", "bison", "chatha pacha (telugu)",
}

# Month name to number
MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def parse_date(text):
    """Extract a YYYY-MM-DD date from a string like 'March 13, 2026' or 'February 2026'"""
    text = text.strip().lower()
    # Try "Month DD, YYYY" or "Month DD YYYY"
    m = re.search(r'(\w+)\s+(\d{1,2}),?\s+(20\d{2})', text)
    if m:
        month = MONTHS.get(m.group(1).lower())
        if month:
            try:
                return datetime(int(m.group(3)), month, int(m.group(2))).strftime('%Y-%m-%d')
            except ValueError:
                pass
    # Try "DD Month YYYY"
    m = re.search(r'(\d{1,2})\s+(\w+)\s+(20\d{2})', text)
    if m:
        month = MONTHS.get(m.group(2).lower())
        if month:
            try:
                return datetime(int(m.group(3)), month, int(m.group(1))).strftime('%Y-%m-%d')
            except ValueError:
                pass
    # Try "Month YYYY" (no day - use 1st)
    m = re.search(r'(\w+)\s+(20\d{2})', text)
    if m:
        month = MONTHS.get(m.group(1).lower())
        if month:
            try:
                return datetime(int(m.group(2)), month, 1).strftime('%Y-%m-%d')
            except ValueError:
                pass
    return None


def normalise_platform(text):
    """Map raw platform text to our standard name"""
    t = text.strip().lower()
    for key, val in PLATFORM_MAP.items():
        if key in t:
            return val
    return None


def scrape():
    print(f"Fetching {URL}")
    try:
        resp = requests.get(URL, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"ERROR fetching page: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    movies = []
    seen_titles = set()

    # FilmiBeat page structure:
    # Each movie has a section. The text pattern is:
    # "TITLE started streaming on PLATFORM on DATE" or
    # "TITLE began streaming on PLATFORM from DATE" or
    # "TITLE will start streaming on PLATFORM in DATE"

    full_text = soup.get_text(separator='\n')
    lines = [l.strip() for l in full_text.split('\n') if l.strip()]

    stream_pattern = re.compile(
        r'^(.+?)\s+(?:started|began|will start|starts?)\s+streaming\s+on\s+(.+?)\s+'
        r'(?:on|from|starting|in)\s+(.+)',
        re.IGNORECASE
    )

    # 3-month cutoff
    cutoff = datetime.now() - timedelta(days=92)

    for line in lines:
        m = stream_pattern.match(line)
        if not m:
            continue

        raw_title    = m.group(1).strip()
        raw_platform = m.group(2).strip()
        raw_date     = m.group(3).strip()

        # Clean title
        title = re.sub(r'^[^a-zA-Z\u0D00-\u0D7F]+', '', raw_title).strip()
        if len(title) < 2 or len(title) > 100:
            continue

        # Skip dubbed films
        if title.lower() in DUBBED:
            continue

        # Skip if paragraph mentions it's a Telugu/Tamil/Hindi/Kannada film
        context = line.lower()
        if any(f'{lang} film' in context or f'originally in {lang}' in context
               for lang in ['telugu', 'tamil', 'hindi', 'kannada', 'korean']):
            continue

        platform = normalise_platform(raw_platform)
        if not platform:
            continue

        ott_date = parse_date(raw_date)
        if not ott_date:
            continue

        # Only last 3 months
        try:
            if datetime.strptime(ott_date, '%Y-%m-%d') < cutoff:
                continue
        except ValueError:
            continue

        # Deduplicate
        key = title.lower()
        if key in seen_titles:
            continue
        seen_titles.add(key)

        # Try to get description from nearby text
        desc = ""
        idx = lines.index(line) if line in lines else -1
        if idx > 0:
            # Look at lines after the streaming line for description
            for i in range(idx + 1, min(idx + 5, len(lines))):
                candidate = lines[i]
                if (len(candidate) > 40 and
                    not stream_pattern.match(candidate) and
                    candidate[0].isupper()):
                    desc = candidate[:200]
                    break

        movies.append({
            "title":    title,
            "platform": platform,
            "ottDate":  ott_date,
            "genre":    "",
            "director": "",
            "cast":     "",
            "desc":     desc,
        })
        print(f"  ✓ {title} → {platform} on {ott_date}")

    # Sort newest first
    movies.sort(key=lambda x: x['ottDate'], reverse=True)
    print(f"\nTotal: {len(movies)} movies found")
    return movies


def main():
    movies = scrape()

    # Always write the file even if empty (so the site doesn't break)
    output = {
        "updated": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        "count":   len(movies),
        "movies":  movies,
    }

    os.makedirs("public", exist_ok=True)
    with open("public/data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nSaved to public/data.json ({len(movies)} movies)")


if __name__ == "__main__":
    main()
