"""Fetch all data from the Zenline hackathon platform API."""

import json
import sys
from pathlib import Path

import httpx

BASE_URL = "https://hackathon-production-49ca.up.railway.app"
DATA_DIR = Path(__file__).parent.parent / "data"


def fetch_all(session_token: str):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cookies = {"hackathon_session": session_token}
    client = httpx.Client(cookies=cookies, timeout=30)

    # Categories
    print("Fetching categories...")
    r = client.get(f"{BASE_URL}/api/categories")
    r.raise_for_status()
    categories = r.json()
    save(categories, "categories.json")
    print(f"  Categories: {[c['name'] for c in categories['categories']]}")

    # Challenge info
    print("Fetching challenge info...")
    r = client.get(f"{BASE_URL}/api/challenge-info")
    r.raise_for_status()
    save(r.json(), "challenge_info.json")

    # Known competitors
    print("Fetching known competitors...")
    r = client.get(f"{BASE_URL}/api/known-competitors")
    r.raise_for_status()
    save(r.json(), "known_competitors.json")

    # Sample products
    print("Fetching sample products...")
    r = client.get(f"{BASE_URL}/api/sample-products")
    r.raise_for_status()
    save(r.json(), "sample_products.json")

    # Per-category data
    for cat in categories["categories"]:
        name = cat["name"]
        safe_name = name.lower().replace(" & ", "_").replace(" ", "_")
        print(f"\nFetching category: {name}")

        # Source products
        r = client.get(f"{BASE_URL}/api/products", params={"category": name})
        r.raise_for_status()
        data = r.json()
        save(data, f"sources_{safe_name}.json")
        print(f"  Sources: {data.get('total', len(data.get('products', [])))} products")

        # Target pool
        r = client.get(f"{BASE_URL}/api/target-pool/{name}")
        r.raise_for_status()
        data = r.json()
        save(data, f"targets_{safe_name}.json")
        print(f"  Targets: {data.get('total', len(data.get('targets', [])))} products")

    # Also save flat versions for the pipeline
    for cat in categories["categories"]:
        name = cat["name"]
        safe_name = name.lower().replace(" & ", "_").replace(" ", "_")

        with open(DATA_DIR / f"sources_{safe_name}.json") as f:
            sources = json.load(f)
        with open(DATA_DIR / f"targets_{safe_name}.json") as f:
            targets = json.load(f)

        # Flat lists for pipeline consumption
        save(sources.get("products", []), f"source_products_{safe_name}.json")
        save(targets.get("targets", []), f"target_products_{safe_name}.json")

    print("\nDone! All data saved to", DATA_DIR)


def save(data, filename):
    path = DATA_DIR / filename
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Saved {path} ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fetch_data.py <session_token>")
        print("Get the token from your browser cookie 'hackathon_session'")
        sys.exit(1)
    fetch_all(sys.argv[1])
