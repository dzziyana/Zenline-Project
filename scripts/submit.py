"""Submit results to the Zenline hackathon platform.

Usage:
    uv run python scripts/submit.py <category> [submission_type]
    uv run python scripts/submit.py "TV & Audio" matching
    uv run python scripts/submit.py "TV & Audio" scraping
    uv run python scripts/submit.py "Small Appliances" scraping
    uv run python scripts/submit.py "TV & Audio"              # submits both matching + scraping

Reads session token from data/session.txt and submission from output/ directory.
Submissions are unlimited -- submit as often as you want to check scores.
"""

import json
import sys
from pathlib import Path
from urllib.parse import urlencode

import httpx

BASE_URL = "https://hackathon-production-49ca.up.railway.app"
ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"


def get_session_token() -> str:
    token_path = DATA_DIR / "session.txt"
    if not token_path.exists():
        print("Error: No session token found at data/session.txt")
        sys.exit(1)
    return token_path.read_text().strip()


def get_team_id(client: httpx.Client) -> str:
    r = client.get(f"{BASE_URL}/api/my-team")
    r.raise_for_status()
    team = r.json().get("team")
    if not team:
        print("Error: No team found. Create/join a team on the platform first:")
        print(f"  {BASE_URL}")
        sys.exit(1)
    return team["id"]


def split_submission(submission: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split a submission into matching (visible pool) and scraping (scraped) entries."""
    matching = []
    scraping = []
    for entry in submission:
        match_comps = []
        scrape_comps = []
        for comp in entry.get("competitors", []):
            ref = comp.get("reference", "")
            if ref.startswith("SCRAPED_"):
                scrape_comps.append(comp)
            else:
                match_comps.append(comp)
        if match_comps:
            matching.append({"source_reference": entry["source_reference"], "competitors": match_comps})
        if scrape_comps:
            scraping.append({"source_reference": entry["source_reference"], "competitors": scrape_comps})
    return matching, scraping


def do_submit(client: httpx.Client, team_id: str, category: str, submission: list[dict], submission_type: str):
    """Submit to the platform."""
    safe_name = category.lower().replace(" & ", "_").replace(" ", "_")
    sources = len(submission)
    links = sum(len(s.get("competitors", [])) for s in submission)
    print(f"\nSubmitting {submission_type}: {sources} sources, {links} links for '{category}'")

    file_content = json.dumps(submission)
    files = {"file": (f"submission_{safe_name}_{submission_type}.json", file_content, "application/json")}

    # Use the correct endpoint format: /api/submit/{team_id}?category=...&submission_type=...
    query = urlencode({"category": category, "submission_type": submission_type})
    url = f"{BASE_URL}/api/submit/{team_id}?{query}"
    r = client.post(url, files=files)

    if r.status_code != 200:
        print(f"  Endpoint 1 failed ({r.status_code}): {r.text[:200]}")
        # Try alternate endpoints
        for alt_url in [
            f"{BASE_URL}/api/teams/{team_id}/submit?category={category}&submission_type={submission_type}",
            f"{BASE_URL}/api/submit/{team_id}",
        ]:
            files = {"file": (f"submission_{safe_name}_{submission_type}.json", file_content, "application/json")}
            r = client.post(alt_url, files=files, data={"category": category, "submission_type": submission_type})
            if r.status_code == 200:
                break
            print(f"  Alt endpoint failed ({r.status_code}): {r.text[:200]}")

    if r.status_code == 200:
        result = r.json()
        print(f"  Result: {json.dumps(result)}")
    else:
        print(f"  All endpoints failed. Last status: {r.status_code}")


def submit(category: str, submission_type: str | None = None):
    safe_name = category.lower().replace(" & ", "_").replace(" ", "_")
    submission_path = OUTPUT_DIR / f"submission_{safe_name}.json"

    if not submission_path.exists():
        print(f"Error: No submission file at {submission_path}")
        print("Run the pipeline first to generate it.")
        sys.exit(1)

    token = get_session_token()
    client = httpx.Client(cookies={"hackathon_session": token}, timeout=30)

    # Check auth
    r = client.get(f"{BASE_URL}/api/auth/me")
    r.raise_for_status()
    user = r.json()
    if not user.get("authenticated"):
        print("Error: Session token expired. Get a new one from your browser.")
        sys.exit(1)
    print(f"Authenticated as: {user['user']}")

    team_id = get_team_id(client)
    print(f"Team ID: {team_id}")

    with open(submission_path) as f:
        submission = json.load(f)

    matching, scraping = split_submission(submission)
    total_links = sum(len(s.get("competitors", [])) for s in submission)
    print(f"Loaded: {len(submission)} sources, {total_links} total links")
    print(f"  Matching: {len(matching)} sources, {sum(len(s['competitors']) for s in matching)} links")
    print(f"  Scraping: {len(scraping)} sources, {sum(len(s['competitors']) for s in scraping)} links")

    if submission_type in (None, "matching") and matching:
        do_submit(client, team_id, category, matching, "matching")
    if submission_type in (None, "scraping") and scraping:
        do_submit(client, team_id, category, scraping, "scraping")

    # Show leaderboard
    r = client.get(f"{BASE_URL}/api/leaderboard")
    if r.status_code == 200:
        lb = r.json()
        print("\nLeaderboard (top 5):")
        for team in lb["leaderboard"][:5]:
            scores = {f"{s['category']}_{s['submission_type']}": s["score"] for s in team.get("category_scores", [])}
            print(f"  {team['name']:25s} total={team['best_score']:5.1f}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/submit.py <category> [matching|scraping]")
        print("Example: uv run python scripts/submit.py 'TV & Audio'")
        print("         uv run python scripts/submit.py 'TV & Audio' scraping")
        sys.exit(1)
    sub_type = sys.argv[2] if len(sys.argv) > 2 else None
    submit(sys.argv[1], sub_type)
