"""
Shared configuration loading for dungeon-dive scripts.

Supports two modes:
1. File-based: load from config.json (local development)
2. Environment variables: fallback when config.json doesn't exist (remote/CI)

Environment variables:
    YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID,
    DISCOURSE_URL, DISCOURSE_API_KEY, DISCOURSE_USERNAME, DISCOURSE_CATEGORY_ID
"""

import json
import os
import sys


def load_config(config_path: str) -> dict:
    """Load configuration from file or environment variables.

    Args:
        config_path: Path to config.json. If the file exists, load it.
                     If not, build config from environment variables.

    Returns:
        Configuration dict with youtube and discourse sections.
    """
    if os.path.isfile(config_path):
        with open(config_path) as f:
            return json.load(f)

    # Build from environment variables
    config = {}

    yt_key = os.environ.get("YOUTUBE_API_KEY")
    yt_channel = os.environ.get("YOUTUBE_CHANNEL_ID", "UCKW6yMwL_aEu83g6DdjVfxw")
    if yt_key:
        config["youtube"] = {
            "api_key": yt_key,
            "channel_id": yt_channel,
        }

    disc_url = os.environ.get("DISCOURSE_URL")
    disc_key = os.environ.get("DISCOURSE_API_KEY")
    disc_user = os.environ.get("DISCOURSE_USERNAME")
    disc_cat = os.environ.get("DISCOURSE_CATEGORY_ID", "5")
    if disc_url and disc_key and disc_user:
        config["discourse"] = {
            "base_url": disc_url.rstrip("/"),
            "api_key": disc_key,
            "api_username": disc_user,
            "post_as_username": disc_user,
            "category_id": int(disc_cat),
        }

    if not config:
        print(
            "Error: No config.json found and no environment variables set.\n"
            "Either create config.json or set:\n"
            "  DISCOURSE_URL, DISCOURSE_API_KEY, DISCOURSE_USERNAME\n"
            "  YOUTUBE_API_KEY (optional, for video fetching)",
            file=sys.stderr,
        )
        sys.exit(1)

    return config
