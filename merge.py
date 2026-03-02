"""
Merge Pocket collection JSONs into links.json.

Usage:
  python merge.py                          # all categories
  python merge.py --only "dj & dataviz" SIGMA   # specific categories only
"""

import argparse
import json
import os

COLLECTIONS_DIR = "collections"
OUTPUT_FILE = "links.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", nargs="+", metavar="CATEGORY",
                        help="Include only these category titles (case-sensitive)")
    args = parser.parse_args()

    keep = set(args.only) if args.only else None
    links = []

    for filename in sorted(os.listdir(COLLECTIONS_DIR)):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(COLLECTIONS_DIR, filename)
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)

        category = data.get("title", filename.replace(".json", ""))

        if keep and category not in keep:
            continue

        for item in data.get("items", []):
            links.append({
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "excerpt": item.get("excerpt", ""),
                "note": item.get("note") or "",
                "category": category,
                "cover_image": "",
            })

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(links, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(links)} links to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
