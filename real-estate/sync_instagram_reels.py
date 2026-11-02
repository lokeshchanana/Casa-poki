#!/usr/bin/env python3
"""
Sync Instagram Reels for Lokesh Chanana Real Estate Website.
Maintains the latest 6 reels in public/instagram_reels.json,
which is mounted directly into the live web container.
"""

import sys
import os
import json
import re
import urllib.request
import html as htmllib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, 'public', 'instagram_reels.json')

KNOWN_CITIES = [
    'Seattle', 'Bellevue', 'Kirkland', 'Redmond', 'Renton', 'Fife', 'Auburn',
    'Tacoma', 'Puyallup', 'Olympia', 'Everett', 'Bothell', 'Lynnwood',
    'Sammamish', 'Issaquah', 'Kent', 'Federal Way', 'Woodinville', 'Snohomish',
    'Mercer Island', 'Edmonds', 'Shoreline', 'Burien', 'Tukwila', 'Maple Valley'
]

def extract_reel_id(input_str):
    """Extract clean alphanumeric Instagram reel ID from a URL or raw ID."""
    match = re.search(r'instagram\.com/(?:reel|p)/([A-Za-z0-9_-]+)', input_str)
    if match:
        return match.group(1)
    cleaned = input_str.strip().strip('/')
    return cleaned

def fetch_reel_metadata(reel_id):
    """Fetch caption, location, and specs for an Instagram reel."""
    url = f'https://www.instagram.com/reel/{reel_id}/embed/captioned/'
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    
    caption = ''
    try:
        html_content = urllib.request.urlopen(req, timeout=8).read().decode('utf-8', errors='ignore')
        matches = re.findall(r'<div class=\"[^\"]*Caption[^\"]*\"[^>]*>(.*?)</div>', html_content, re.DOTALL | re.IGNORECASE)
        if matches:
            caption = re.sub(r'<[^>]+>', ' ', matches[0]).strip()
            caption = htmllib.unescape(caption)
    except Exception as e:
        print(f"Warning: could not fetch full caption for {reel_id}: {e}")

    # Detect city
    found_city = "Greater Seattle, WA"
    for city in KNOWN_CITIES:
        if re.search(r'\b' + city + r'\b', caption, re.I):
            found_city = f"{city}, WA"
            break

    # Detect address
    address_m = re.search(r'(\d+[^,\n]+(?:Ave|Avenue|St|Street|Rd|Road|Ln|Lane|Way|Pl|Place|Dr|Drive|Blvd)[^,\n]*,[^,\n]+,\s*WA\s*\d{5})', caption, re.I)
    address = address_m.group(1).strip() if address_m else f"{found_city}"

    # Extract specs (beds, baths, sqft)
    specs_parts = []
    bed_m = re.search(r'(\d+)\s*(?:bed|bedroom|bd)', caption, re.I)
    if bed_m:
        specs_parts.append(f"{bed_m.group(1)} Beds")
    bath_m = re.search(r'(\d+(?:\.\d+)?)\s*(?:bath|bathroom|ba)', caption, re.I)
    if bath_m:
        specs_parts.append(f"{bath_m.group(1)} Baths")
    sqft_m = re.search(r'([\d,]+)\s*(?:sq\s*ft|sqft)', caption, re.I)
    if sqft_m:
        specs_parts.append(f"{sqft_m.group(1)} Sq Ft")

    specs = " • ".join(specs_parts) if specs_parts else "Property Walkthrough"

    # Generate title
    if "open house" in caption.lower():
        tag = "Open House Tour"
        title = f"Open House in {found_city}"
    elif "new construction" in caption.lower():
        tag = "New Construction Tour"
        title = f"New Construction in {found_city}"
    elif "luxury" in caption.lower() or "$2." in caption or "$3." in caption or "$4." in caption:
        tag = "Luxury Home Tour"
        title = f"Luxury Residence in {found_city}"
    else:
        tag = "Property Walkthrough"
        title = f"Home Walkthrough in {found_city}"

    # If first sentence of caption has property description
    first_sentence = caption.split('.')[0].replace('lokeshchanana_re', '').strip()
    if len(first_sentence) > 15 and len(first_sentence) < 70:
        title = first_sentence

    authors = re.findall(r'instagram\.com/([A-Za-z0-9_.-]+)/\?utm_source=ig_embed', html_content)
    author = authors[0] if authors else "lokeshchanana_re"

    return {
        "id": reel_id,
        "url": f"https://www.instagram.com/reel/{reel_id}/",
        "title": title,
        "location": found_city,
        "address": address,
        "specs": specs,
        "tag": tag,
        "author": author,
        "date": "Recent"
    }

def load_reels():
    if not os.path.exists(JSON_PATH):
        return []
    with open(JSON_PATH, 'r') as f:
        return json.load(f)

def save_reels(reels):
    # Ensure always max 6
    trimmed = reels[:6]
    with open(JSON_PATH, 'w') as f:
        json.dump(trimmed, f, indent=2)
    print(f"Saved {len(trimmed)} reels to {JSON_PATH}")

def add_reel(url_or_id):
    reel_id = extract_reel_id(url_or_id)
    print(f"Fetching metadata for reel ID: {reel_id}...")
    new_reel = fetch_reel_metadata(reel_id)

    if new_reel.get('author') != 'lokeshchanana_re':
        print(f"Error: Reel {reel_id} is authored by @{new_reel.get('author')}, not @lokeshchanana_re.")
        print("Only reels published by @lokeshchanana_re are permitted.")
        return False

    reels = load_reels()
    # Remove if existing to avoid duplicates
    reels = [r for r in reels if r.get('id') != reel_id]
    # Prepend new reel
    reels.insert(0, new_reel)
    save_reels(reels)
    print(f"Successfully added reel: {new_reel['title']} ({new_reel['location']})")
    return True

def list_reels():
    reels = load_reels()
    print(f"--- Current Latest {len(reels)} Reels on Website ---")
    for i, r in enumerate(reels, 1):
        print(f"#{i} [{r['id']}] {r['title']} | {r['location']} | {r['specs']}")
        print(f"   URL: {r['url']}")

def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip()
        if arg == '--list':
            list_reels()
            return
        elif arg == '--refresh':
            reels = load_reels()
            updated = []
            for r in reels:
                print(f"Refreshing {r['id']}...")
                updated.append(fetch_reel_metadata(r['id']))
            save_reels(updated)
            return
        else:
            add_reel(arg)
            return

    # Default display
    list_reels()

if __name__ == '__main__':
    main()
