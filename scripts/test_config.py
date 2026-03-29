#!/usr/bin/env python3
"""
Test configuration for YouTube and Discourse APIs.

Usage:
    python test_config.py --config config.json
"""

import argparse
import json
import sys

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests --break-system-packages")
    sys.exit(1)


def load_config(config_path: str) -> dict:
    """Load configuration from JSON file."""
    with open(config_path) as f:
        return json.load(f)


def test_youtube(config: dict) -> bool:
    """Test YouTube API connection."""
    print("\n=== Testing YouTube API ===")

    api_key = config.get("youtube", {}).get("api_key")
    channel_id = config.get("youtube", {}).get("channel_id")

    if not api_key:
        print("ERROR: youtube.api_key not configured")
        return False

    if not channel_id:
        print("ERROR: youtube.channel_id not configured")
        return False

    url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "key": api_key,
        "id": channel_id,
        "part": "snippet"
    }

    try:
        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()
            if data.get("items"):
                channel_name = data["items"][0]["snippet"]["title"]
                print(f"SUCCESS: Connected to YouTube")
                print(f"  Channel: {channel_name}")
                print(f"  ID: {channel_id}")
                return True
            else:
                print(f"ERROR: Channel not found: {channel_id}")
                return False
        elif response.status_code == 403:
            print("ERROR: API key invalid or quota exceeded")
            print(response.json().get("error", {}).get("message", ""))
            return False
        else:
            print(f"ERROR: API returned {response.status_code}")
            return False

    except Exception as e:
        print(f"ERROR: {e}")
        return False


def test_discourse_admin(base_url: str, api_key: str, api_username: str) -> bool:
    """Test if API key has admin privileges (required for backdating)."""
    print("\n  Checking admin privileges...")

    # Try to access an admin-only endpoint
    url = f"{base_url}/admin/users/list/active.json"
    headers = {
        "Api-Key": api_key,
        "Api-Username": api_username
    }

    try:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            print("  ADMIN ACCESS: Yes (backdating will work)")
            return True
        elif response.status_code == 403:
            print("  ADMIN ACCESS: No")
            print("  WARNING: Backdating posts requires admin privileges!")
            print("  To fix: Admin > Users > [bot account] > Grant Admin")
            return False
        else:
            print(f"  ADMIN ACCESS: Unknown (status {response.status_code})")
            return False

    except Exception as e:
        print(f"  ADMIN ACCESS: Could not verify ({e})")
        return False


def test_discourse(config: dict) -> bool:
    """Test Discourse API connection."""
    print("\n=== Testing Discourse API ===")

    discourse = config.get("discourse", {})
    base_url = discourse.get("base_url")
    api_key = discourse.get("api_key")
    api_username = discourse.get("api_username")

    if not base_url:
        print("ERROR: discourse.base_url not configured")
        return False

    if not api_key:
        print("ERROR: discourse.api_key not configured")
        return False

    if not api_username:
        print("ERROR: discourse.api_username not configured")
        return False

    # Test by fetching categories
    url = f"{base_url}/categories.json"
    headers = {
        "Api-Key": api_key,
        "Api-Username": api_username
    }

    try:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            categories = data.get("category_list", {}).get("categories", [])
            print(f"SUCCESS: Connected to Discourse")
            print(f"  URL: {base_url}")
            print(f"  Categories found: {len(categories)}")

            # Check if target category exists
            target_cat = discourse.get("category_id")
            if target_cat:
                cat_names = {c["id"]: c["name"] for c in categories}
                if target_cat in cat_names:
                    print(f"  Target category: {cat_names[target_cat]} (ID: {target_cat})")
                else:
                    print(f"  WARNING: Category ID {target_cat} not found")
                    print(f"  Available: {cat_names}")

            # Check for admin privileges (required for backdating)
            admin_ok = test_discourse_admin(base_url, api_key, api_username)

            return True

        elif response.status_code == 403:
            print("ERROR: API key invalid or insufficient permissions")
            return False
        else:
            print(f"ERROR: API returned {response.status_code}")
            return False

    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test API configuration")
    parser.add_argument("--config", required=True, help="Path to config.json")
    args = parser.parse_args()

    config = load_config(args.config)

    youtube_ok = test_youtube(config)
    discourse_ok = test_discourse(config)

    print("\n=== Summary ===")
    print(f"YouTube:  {'OK' if youtube_ok else 'FAILED'}")
    print(f"Discourse: {'OK' if discourse_ok else 'FAILED'}")

    if youtube_ok and discourse_ok:
        print("\nConfiguration is valid. Ready to sync!")
        sys.exit(0)
    else:
        print("\nPlease fix the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
