#!/usr/bin/env python3
"""
Sync Instagram Reels for Lokesh Chanana Real Estate Website.
Maintains the latest 8 reels in public/instagram_reels.json and caches
progressive MP4 videos + cover thumbnails in /tank/re_reels/.
"""

import sys
import os
import json
import re
import urllib.request
import html as htmllib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, 'public', 'instagram_reels.json')
REELS_MEDIA_DIR = os.environ.get('REELS_MEDIA_DIR', '/tank/re_reels')
MAX_REELS = 8
TARGET_USERNAME = 'lokeshchanana_re'
DEFAULT_SEED_REEL = 'DefBayDkggh'

CRAWLER_UA = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'

KNOWN_CITIES = [
    'Seattle', 'North Seattle', 'Crown Hill', 'Blue Ridge', 'Haller Lake',
    'Bellevue', 'Kirkland', 'Redmond', 'Renton', 'Fife', 'Auburn',
    'Tacoma', 'Puyallup', 'Olympia', 'Everett', 'Bothell', 'Lynnwood',
    'Sammamish', 'Issaquah', 'Kent', 'Federal Way', 'Woodinville', 'Snohomish',
    'Mercer Island', 'Edmonds', 'Shoreline', 'Burien', 'Tukwila', 'Maple Valley'
]


def extract_reel_id(input_str):
    """Extract clean alphanumeric Instagram reel ID from a URL or raw ID."""
    match = re.search(r'instagram\.com/(?:reel|p)/([A-Za-z0-9_-]+)', input_str)
    if match:
        return match.group(1)
    return input_str.strip().strip('/')


def fetch_html(url, timeout=12):
    req = urllib.request.Request(url, headers={'User-Agent': CRAWLER_UA})
    return urllib.request.urlopen(req, timeout=timeout).read().decode('utf-8', errors='ignore')


def download_file(url, dest_path):
    """Download a remote media file if it doesn't already exist locally."""
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 10240:
        return True
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        if len(data) < 1024:
            return False
        tmp_path = dest_path + '.tmp'
        with open(tmp_path, 'wb') as f:
            f.write(data)
        os.replace(tmp_path, dest_path)
        return True
    except Exception as e:
        print(f"Warning: failed to download {dest_path}: {e}")
        return False


def parse_caption_metadata(caption, reel_id, date_str='Recent'):
    """Derive structured location, address, specs, tag, and title from caption."""
    clean_caption = re.sub(r'\s+', ' ', caption).strip()

    # Detect city/neighborhood
    found_city = 'Greater Seattle, WA'
    for city in KNOWN_CITIES:
        if re.search(r'\b' + re.escape(city) + r'\b', clean_caption, re.I):
            if city in ('Crown Hill', 'Blue Ridge', 'Haller Lake', 'North Seattle'):
                found_city = 'North Seattle, WA'
            else:
                found_city = f'{city}, WA'
            break

    # Detect street address
    address_m = re.search(
        r'(\d+[^,\n]+(?:Ave|Avenue|St|Street|Rd|Road|Ln|Lane|Way|Pl|Place|Dr|Drive|Blvd)[^,\n]*,[^,\n]+,\s*WA\s*\d{5})',
        caption,
        re.I,
    )
    address = address_m.group(1).strip() if address_m else found_city

    # Extract specs (beds, baths, sqft)
    specs_parts = []
    bed_m = re.search(r'(\d+)[\s-]*(?:bed|bedroom|beds|bedrooms|bd)\b', clean_caption, re.I)
    if bed_m:
        specs_parts.append(f'{bed_m.group(1)} Beds')
    bath_m = re.search(r'(\d+(?:\.\d+)?)[\s-]*(?:bath|bathroom|baths|bathrooms|ba)\b', clean_caption, re.I)
    if bath_m:
        specs_parts.append(f'{bath_m.group(1)} Baths')
    sqft_m = re.search(r'([\d,]+)\s*(?:finished\s+)?(?:sq\.?\s*ft\.?|sqft)\b', clean_caption, re.I)
    if sqft_m:
        specs_parts.append(f'{sqft_m.group(1)} Sq Ft')

    specs = ' • '.join(specs_parts) if specs_parts else 'Property Walkthrough'

    # Classify tour type
    lower_cap = clean_caption.lower()
    if 'open house' in lower_cap:
        tag = 'Open House Tour'
        title = f'Open House in {found_city}'
    elif 'new construction' in lower_cap:
        tag = 'New Construction Tour'
        title = f'New Construction in {found_city}'
    elif '55+' in lower_cap or 'gated' in lower_cap:
        tag = 'Gated Community Tour'
        title = f'Single-Level Home in {found_city}'
    elif 'rambler' in lower_cap:
        tag = 'Rambler Tour'
        title = f'Rambler Residence in {found_city}'
    elif 'luxury' in lower_cap or '$2.' in clean_caption or '$3.' in clean_caption or '$4.' in clean_caption:
        tag = 'Luxury Home Tour'
        title = f'Luxury Residence in {found_city}'
    else:
        tag = 'Property Walkthrough'
        title = f'Home Tour in {found_city}'

    # Build a crisp editorial title from the first line of the caption if concise
    first_line = re.split(r'(?<!\d)[.!?](?!\d)|\n', caption.strip())[0]
    first_line = re.sub(r'[^\w\s,\-\'/&+]', '', first_line).strip()
    for prefix in ('Step inside this ', 'Touring this ', 'Tour this '):
        if first_line.lower().startswith(prefix.lower()):
            first_line = first_line[len(prefix):].strip()
            if first_line:
                first_line = first_line[0].upper() + first_line[1:]
    if len(first_line) > 64:
        first_line = first_line[:61].rsplit(' ', 1)[0] + '...'
    if len(first_line) >= 12 and not first_line.lower().startswith('fresh listing alert'):
        title = first_line

    # Strip hashtags for clean modal display
    display_caption = re.sub(r'(?:#\S+\s*)+$', '', caption).strip().strip('"').strip()

    return {
        'id': reel_id,
        'url': f'https://www.instagram.com/reel/{reel_id}/',
        'videoUrl': f'/reels/{reel_id}.mp4',
        'thumbnailUrl': f'/reels/{reel_id}.jpg',
        'title': title,
        'location': found_city,
        'address': address,
        'specs': specs,
        'tag': tag,
        'caption': display_caption,
        'author': TARGET_USERNAME,
        'date': date_str,
    }


def fetch_reel_metadata(reel_id, download_media=True):
    """Fetch caption, date, thumbnail, and progressive MP4 stream for a reel."""
    url = f'https://www.instagram.com/reel/{reel_id}/'
    html_content = fetch_html(url)

    # Verify author
    user_m = re.search(r'"username":"([A-Za-z0-9_.-]+)"', html_content)
    author = user_m.group(1) if user_m else TARGET_USERNAME

    # Extract caption & date from og:description
    caption = ''
    date_str = 'Recent'
    desc_m = re.search(r'<meta property="og:description" content="([^"]+)"', html_content)
    if desc_m:
        raw_desc = htmllib.unescape(desc_m.group(1))
        cap_m = re.match(
            r'^.*?-\s*[A-Za-z0-9_.-]+\s+on\s+([A-Za-z]+\s+\d+,\s+\d{4}):\s*"?(.*?)"?\.?\s*$',
            raw_desc,
            re.DOTALL,
        )
        if cap_m:
            full_date = cap_m.group(1).strip()
            parts = full_date.replace(',', '').split()
            if len(parts) >= 2:
                date_str = f'{parts[0][:3]} {parts[1]}'
            caption = cap_m.group(2).strip().rstrip('"').strip()
        else:
            caption = raw_desc

    # Extract cover image URL
    img_url = None
    img_m = re.search(r'<meta property="og:image" content="([^"]+)"', html_content)
    if img_m:
        img_url = htmllib.unescape(img_m.group(1))

    # Extract progressive MP4 URL
    mp4_url = None
    vv_m = re.search(r'"video_versions":\[\{"type":\d+,"url":"([^"]+)"', html_content)
    if vv_m:
        mp4_url = vv_m.group(1).replace('\\/', '/').replace('\\u0026', '&')
    else:
        mp4_m = re.search(r'(https?:\\/\\/[^"\'\s<>]+\.mp4[^"\'\s<>]*)', html_content)
        if mp4_m:
            mp4_url = htmllib.unescape(mp4_m.group(1).replace('\\/', '/').replace('\\u0026', '&'))

    meta = parse_caption_metadata(caption, reel_id, date_str=date_str)
    meta['author'] = author

    if download_media:
        os.makedirs(REELS_MEDIA_DIR, exist_ok=True)
        if img_url:
            ok_img = download_file(img_url, os.path.join(REELS_MEDIA_DIR, f'{reel_id}.jpg'))
            if not ok_img:
                meta['thumbnailUrl'] = img_url
        if mp4_url:
            ok_vid = download_file(mp4_url, os.path.join(REELS_MEDIA_DIR, f'{reel_id}.mp4'))
            if not ok_vid:
                meta['videoUrl'] = ''
        else:
            meta['videoUrl'] = ''

    return meta


def discover_latest_reel_ids(seed_id=DEFAULT_SEED_REEL, limit=MAX_REELS):
    """Discover the latest reel IDs from @lokeshchanana_re via Instagram SSR timeline."""
    html_content = fetch_html(f'https://www.instagram.com/reel/{seed_id}/')
    # Extract ordered reel shortcodes belonging to TARGET_USERNAME
    found = []
    for m in re.finditer(rf'{TARGET_USERNAME}/reel/([A-Za-z0-9_-]+)/', html_content):
        rid = m.group(1)
        if rid not in found:
            found.append(rid)

    # Also check polaris_ordered_timeline_connection edges in JSON order
    timeline_idx = html_content.find('polaris_ordered_timeline_connection')
    if timeline_idx != -1:
        chunk = html_content[timeline_idx:timeline_idx + 40000]
        ordered = []
        for m in re.finditer(r'"code":"([A-Za-z0-9_-]+)"', chunk):
            rid = m.group(1)
            if rid not in ordered and len(rid) >= 8:
                ordered.append(rid)
        if ordered:
            return ordered[:limit]

    return found[:limit]


def load_reels():
    if not os.path.exists(JSON_PATH):
        return []
    with open(JSON_PATH, 'r') as f:
        return json.load(f)


def save_reels(reels):
    trimmed = reels[:MAX_REELS]
    with open(JSON_PATH, 'w') as f:
        json.dump(trimmed, f, indent=2)
    print(f'Saved {len(trimmed)} reels to {JSON_PATH}')


def prune_unused_media(active_ids):
    """Remove cached .mp4/.jpg files no longer in the active reels list."""
    if not os.path.isdir(REELS_MEDIA_DIR):
        return
    keep = set(active_ids)
    for fname in os.listdir(REELS_MEDIA_DIR):
        stem, ext = os.path.splitext(fname)
        if ext in ('.mp4', '.jpg') and stem not in keep:
            try:
                os.remove(os.path.join(REELS_MEDIA_DIR, fname))
                print(f'Pruned old media: {fname}')
            except Exception as e:
                print(f'Warning: could not prune {fname}: {e}')


def sync_auto():
    existing = load_reels()
    seed_id = existing[0]['id'] if existing else DEFAULT_SEED_REEL
    print(f'Discovering latest reels for @{TARGET_USERNAME} (seed: {seed_id})...')
    latest_ids = discover_latest_reel_ids(seed_id=seed_id, limit=MAX_REELS)
    if not latest_ids:
        print('Warning: no reels discovered; keeping existing list.')
        return

    print(f'Found {len(latest_ids)} latest reels: {", ".join(latest_ids)}')
    updated = []
    for rid in latest_ids:
        print(f'Syncing {rid}...')
        try:
            meta = fetch_reel_metadata(rid, download_media=True)
            if meta.get('author') == TARGET_USERNAME:
                updated.append(meta)
            else:
                print(f'Skipping {rid}: author is @{meta.get("author")}')
        except Exception as e:
            print(f'Error syncing {rid}: {e}')

    if updated:
        save_reels(updated)
        prune_unused_media([r['id'] for r in updated])


def add_reel(url_or_id):
    reel_id = extract_reel_id(url_or_id)
    print(f'Fetching metadata for reel ID: {reel_id}...')
    new_reel = fetch_reel_metadata(reel_id, download_media=True)

    if new_reel.get('author') != TARGET_USERNAME:
        print(f"Error: Reel {reel_id} is authored by @{new_reel.get('author')}, not @{TARGET_USERNAME}.")
        return False

    reels = [r for r in load_reels() if r.get('id') != reel_id]
    reels.insert(0, new_reel)
    save_reels(reels)
    prune_unused_media([r['id'] for r in reels[:MAX_REELS]])
    print(f"Successfully added reel: {new_reel['title']} ({new_reel['location']})")
    return True


def list_reels():
    reels = load_reels()
    print(f'--- Current Latest {len(reels)} Reels on Website ---')
    for i, r in enumerate(reels, 1):
        print(f"#{i} [{r['id']}] {r['title']} | {r['location']} | {r['specs']}")
        print(f"   URL: {r['url']}")


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
        if arg == '--auto':
            sync_auto()
            return
        elif arg == '--list':
            list_reels()
            return
        elif arg == '--refresh':
            reels = load_reels()
            updated = []
            for r in reels:
                print(f"Refreshing {r['id']}...")
                updated.append(fetch_reel_metadata(r['id'], download_media=True))
            save_reels(updated)
            prune_unused_media([r['id'] for r in updated])
            return
        else:
            add_reel(arg)
            return

    list_reels()


if __name__ == '__main__':
    main()
