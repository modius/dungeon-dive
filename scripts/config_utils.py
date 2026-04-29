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


def _clean_env(name: str) -> str:
    """Read an env var and strip surrounding whitespace.

    Schedulers' secret managers commonly pick up trailing newlines or spaces
    from web-form paste, which then break API auth in ways that are hard to
    diagnose. We strip defensively — any actual secret with leading/trailing
    whitespace is invalid anyway.

    Returns "" for unset vars (so callers can use a single truthiness check).
    """
    return (os.environ.get(name) or "").strip()


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

    # YouTube section — only api_key is required
    yt_key = _clean_env("YOUTUBE_API_KEY")
    yt_channel = _clean_env("YOUTUBE_CHANNEL_ID") or "UCKW6yMwL_aEu83g6DdjVfxw"
    if yt_key:
        config["youtube"] = {
            "api_key": yt_key,
            "channel_id": yt_channel,
        }

    # Discourse section — all three of URL/KEY/USERNAME are required together.
    # If any are set but not all (post-strip), that's a partial setup — fail
    # loud rather than silently dropping the section and crashing later.
    disc_url = _clean_env("DISCOURSE_URL")
    disc_key = _clean_env("DISCOURSE_API_KEY")
    disc_user = _clean_env("DISCOURSE_USERNAME")
    disc_present = [
        ("DISCOURSE_URL", disc_url),
        ("DISCOURSE_API_KEY", disc_key),
        ("DISCOURSE_USERNAME", disc_user),
    ]
    set_count = sum(1 for _, v in disc_present if v)
    if 0 < set_count < 3:
        missing = [n for n, v in disc_present if not v]
        print(
            f"Error: Partial Discourse env-var setup — missing or empty: {', '.join(missing)}\n"
            "Set all three of DISCOURSE_URL, DISCOURSE_API_KEY, DISCOURSE_USERNAME "
            "or none. Values are stripped of surrounding whitespace before checking.",
            file=sys.stderr,
        )
        sys.exit(1)

    if disc_url and disc_key and disc_user:
        cat_raw = _clean_env("DISCOURSE_CATEGORY_ID") or "5"
        try:
            cat_id = int(cat_raw)
        except ValueError as e:
            print(f"Error: DISCOURSE_CATEGORY_ID must be an integer ({e})", file=sys.stderr)
            sys.exit(1)
        config["discourse"] = {
            "base_url": disc_url.rstrip("/"),
            "api_key": disc_key,
            "api_username": disc_user,
            "post_as_username": disc_user,
            "category_id": cat_id,
        }

    if not config:
        print(
            f"Error: No config file at {config_path} and no environment variables set.\n"
            "Either create config.json or set:\n"
            "  YOUTUBE_API_KEY (required for video fetching), YOUTUBE_CHANNEL_ID (optional)\n"
            "  DISCOURSE_URL, DISCOURSE_API_KEY, DISCOURSE_USERNAME (all required for posting)\n"
            "  DISCOURSE_CATEGORY_ID (optional, defaults to 5)",
            file=sys.stderr,
        )
        sys.exit(1)

    return config
