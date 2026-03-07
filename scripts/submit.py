"""Submit results to the Zenline hackathon platform.

Usage:
    uv run python scripts/submit.py <category>
    uv run python scripts/submit.py "TV & Audio"
    uv run python scripts/submit.py "Small Appliances"

Reads session token from data/session.txt and submission from output/submission_<category>.json.
Submissions are unlimited -- submit as often as you want to check scores.
"""

import json
import sys
from pathlib import Path

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


def submit(category: str):
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

    # Get team
    team_id = get_team_id(client)
    print(f"Team ID: {team_id}")

    # Read submission
    with open(submission_path) as f:
        submission = json.load(f)

    sources = len(submission)
    links = sum(len(s.get("competitors", [])) for s in submission)
    print(f"Submitting: {sources} sources, {links} links for '{category}'")

    # Submit as multipart form (matching the frontend's FormData approach)
    files = {"file": (f"submission_{safe_name}.json", json.dumps(submission), "application/json")}
    data = {"category": category}

    r = client.post(f"{BASE_URL}/api/teams/{team_id}/submit", files=files, data=data)

    if r.status_code != 200:
        print(f"Error {r.status_code}: {r.text}")
        # Try alternate endpoint
        r = client.post(f"{BASE_URL}/api/submit", files=files, data=data)
        if r.status_code != 200:
            print(f"Alternate endpoint also failed {r.status_code}: {r.text}")
            sys.exit(1)

    result = r.json()
    print("\nSubmission result:")
    print(json.dumps(result, indent=2))

    # Check leaderboard
    r = client.get(f"{BASE_URL}/api/leaderboard")
    if r.status_code == 200:
        lb = r.json()
        print("\nLeaderboard:")
        print(json.dumps(lb, indent=2)[:500])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/submit.py <category>")
        print("Example: uv run python scripts/submit.py 'TV & Audio'")
        sys.exit(1)
    submit(sys.argv[1])
