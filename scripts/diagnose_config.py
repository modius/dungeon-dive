#!/usr/bin/env python3
"""
Diagnose what config_utils.load_config() actually loaded.

Prints fingerprints (length + first 4 + last 4 chars) and integrity flags
for each loaded value, never the full secret. Safe to paste output into
logs, GitHub issues, or chat for troubleshooting.

Use this on the remote runner when API auth fails — it shows whether the
loaded value matches what you intended (length, fingerprint) and whether
defensive cleanup found anything suspicious (whitespace, quotes, non-ASCII).

Usage:
    python3 scripts/diagnose_config.py
    python3 scripts/diagnose_config.py --config config.json
"""

import argparse
import os
import sys

# Allow running from project root or scripts/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config_utils import load_config


def fingerprint(value: str) -> dict:
    """Return non-revealing diagnostic info about a string."""
    if value is None:
        return {"present": False}
    fp_head = value[:4] if len(value) >= 4 else value
    fp_tail = value[-4:] if len(value) >= 4 else ""
    return {
        "present": True,
        "length": len(value),
        "fingerprint": f"{fp_head}...{fp_tail}" if len(value) > 8 else f"({len(value)} chars)",
        "has_leading_space": value != value.lstrip(),
        "has_trailing_space": value != value.rstrip(),
        "has_internal_whitespace": any(ch.isspace() for ch in value.strip()),
        "starts_with_quote": value[:1] in ("'", '"') if value else False,
        "ends_with_quote": value[-1:] in ("'", '"') if value else False,
        "ascii_only": all(ord(c) < 128 for c in value),
    }


def print_fp(label: str, value):
    fp = fingerprint(value)
    if not fp["present"]:
        print(f"  {label}: <not loaded>")
        return
    flags = []
    if fp.get("has_leading_space"):
        flags.append("LEADING_WHITESPACE")
    if fp.get("has_trailing_space"):
        flags.append("TRAILING_WHITESPACE")
    if fp.get("has_internal_whitespace"):
        flags.append("INTERNAL_WHITESPACE")
    if fp.get("starts_with_quote") or fp.get("ends_with_quote"):
        flags.append("QUOTED")
    if not fp.get("ascii_only"):
        flags.append("NON_ASCII")
    flag_str = f"  [⚠ {' '.join(flags)}]" if flags else ""
    print(f"  {label}: len={fp['length']} fingerprint={fp['fingerprint']}{flag_str}")


def main():
    parser = argparse.ArgumentParser(description="Diagnose loaded config values")
    parser.add_argument("--config", default="config.json", help="Path to config.json (may be missing)")
    args = parser.parse_args()

    print(f"Diagnosing config — path={args.config}, exists={os.path.isfile(args.config)}")
    print(f"Source: {'file' if os.path.isfile(args.config) else 'environment variables'}\n")

    # Show env-var presence even when file mode wins, so users can spot mismatches
    print("Environment variables seen by this process:")
    for name in (
        "YOUTUBE_API_KEY", "YOUTUBE_CHANNEL_ID",
        "DISCOURSE_URL", "DISCOURSE_API_KEY",
        "DISCOURSE_USERNAME", "DISCOURSE_CATEGORY_ID",
    ):
        raw = os.environ.get(name)
        if raw is None:
            print(f"  {name}: <unset>")
        else:
            print_fp(name, raw)
    print()

    config = load_config(args.config)
    print("Loaded configuration:")
    if "youtube" in config:
        print("  youtube:")
        print_fp("    api_key", config["youtube"].get("api_key"))
        print_fp("    channel_id", config["youtube"].get("channel_id"))
    else:
        print("  youtube: <not loaded>")

    if "discourse" in config:
        print("  discourse:")
        print_fp("    base_url", config["discourse"].get("base_url"))
        print_fp("    api_key", config["discourse"].get("api_key"))
        print_fp("    api_username", config["discourse"].get("api_username"))
        print(f"    category_id: {config['discourse'].get('category_id')}")
    else:
        print("  discourse: <not loaded>")


if __name__ == "__main__":
    main()
