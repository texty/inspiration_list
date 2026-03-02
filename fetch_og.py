"""
Fetches OG images for links in links.json and updates the file in-place.

Usage:
  python fetch_og.py --sample 5    # test on first 5 URLs without an image
  python fetch_og.py --all         # process all URLs without an image
  python fetch_og.py --refetch     # re-fetch even URLs that already have an image

Dependencies:
  pip install requests beautifulsoup4
"""

import argparse
import json
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
TIMEOUT = 10


def fetch_og_image(url: str) -> str:
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Try og:image first, then twitter:image
        for attr, name in [("property", "og:image"), ("name", "twitter:image")]:
            tag = soup.find("meta", attrs={attr: name})
            if tag and tag.get("content"):
                img = tag["content"].strip()
                # Make relative URLs absolute
                if img.startswith("//"):
                    img = "https:" + img
                elif img.startswith("/"):
                    parsed = urlparse(url)
                    img = f"{parsed.scheme}://{parsed.netloc}{img}"
                return img

    except Exception as e:
        print(f"  ✗ Error: {e}")

    return ""


def main():
    parser = argparse.ArgumentParser(description="Fetch OG images for links.json")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--sample", type=int, metavar="N", help="Process first N URLs missing an image")
    group.add_argument("--all", action="store_true", help="Process all URLs missing an image")
    parser.add_argument("--refetch", action="store_true", help="Re-fetch URLs that already have an image")
    args = parser.parse_args()

    with open("links.json", encoding="utf-8") as f:
        links = json.load(f)

    if args.refetch:
        to_process = list(range(len(links)))
    else:
        to_process = [i for i, l in enumerate(links) if not l.get("cover_image")]

    if args.sample:
        to_process = to_process[: args.sample]

    print(f"Processing {len(to_process)} URLs...\n")

    updated = 0
    for i, idx in enumerate(to_process):
        link = links[idx]
        short_url = link["url"][:70] + ("..." if len(link["url"]) > 70 else "")
        print(f"[{i + 1}/{len(to_process)}] {short_url}")

        img = fetch_og_image(link["url"])
        links[idx]["cover_image"] = img

        if img:
            print(f"  ✓ {img[:70]}")
            updated += 1
        else:
            print("  – no image found")

    with open("links.json", "w", encoding="utf-8") as f:
        json.dump(links, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Updated {updated}/{len(to_process)} links. Saved to links.json.")


if __name__ == "__main__":
    main()
