#!/usr/bin/env python3
"""
Backdate fix for batch 3 posts that were created without timestamps.
Run locally: python3 youtube-discourse-sync/scripts/backdate_batch3.py --config config.json
"""

import json
import requests
import argparse
from datetime import datetime
from time import sleep

# Mapping from posting output - topic IDs in order they were created
# Order from batch_post.py output:
# 1k6Bzkiw48o -> 1216, 5sVEspUzpGY -> 1217, 7ufObjxCBKI -> 1218, CMh4ttABaiE -> 1219,
# FAfQTG-v0Cs -> 1220, MRxgJpEyabo -> 1221, Pwf2T_cntdg -> 1222, _auL36M33Aw -> 1223,
# _zuQYhMwTgs -> 1224, ipf-y1PaGBg -> 1225, lSkunEYX5Go -> 1226, mNKdQ1YwHPc -> 1227,
# nuEwWBGiQ4c -> 1228, p8GqOFBpR5w -> 1229, pWY2T3MqfCw -> 1230, wLB8pR4uME0 -> 1231,
# zceKtRTdgSo -> 1232

BATCH3_MAPPING = {
    "1k6Bzkiw48o": 1216,
    "5sVEspUzpGY": 1217,
    "7ufObjxCBKI": 1218,
    "CMh4ttABaiE": 1219,
    "FAfQTG-v0Cs": 1220,
    "MRxgJpEyabo": 1221,
    "Pwf2T_cntdg": 1222,
    "_auL36M33Aw": 1223,
    "_zuQYhMwTgs": 1224,
    "ipf-y1PaGBg": 1225,
    "lSkunEYX5Go": 1226,
    "mNKdQ1YwHPc": 1227,
    "nuEwWBGiQ4c": 1228,
    "p8GqOFBpR5w": 1229,
    "pWY2T3MqfCw": 1230,
    "wLB8pR4uME0": 1231,
    "zceKtRTdgSo": 1232,
}

from config_utils import load_config

def load_video_index(index_path):
    with open(index_path) as f:
        return json.load(f)

def iso_to_unix(iso_string):
    """Convert ISO 8601 timestamp to Unix timestamp"""
    dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
    return int(dt.timestamp())

def backdate_topic(base_url, api_key, api_username, topic_id, unix_timestamp):
    """Update a topic's timestamp using Discourse Admin API"""
    url = f"{base_url}/t/{topic_id}/change-timestamp"
    headers = {
        "Api-Key": api_key,
        "Api-Username": api_username,
        "Content-Type": "application/json"
    }
    data = {"timestamp": unix_timestamp}

    response = requests.put(url, headers=headers, json=data)
    return response.status_code == 200, response.text

def main():
    parser = argparse.ArgumentParser(description='Backdate batch 3 topics')
    parser.add_argument('--config', required=True, help='Path to config.json')
    args = parser.parse_args()

    config = load_config(args.config)
    index_data = load_video_index(config.get('video_index_path', 'video_index.json'))

    discourse = config['discourse']
    base_url = discourse['base_url'].rstrip('/')
    api_key = discourse['api_key']
    api_username = discourse['api_username']

    # Build video_id -> publish_at lookup
    publish_dates = {}
    for video in index_data['videos']:
        vid = video.get('video_id')
        pub = video.get('published_at')
        if vid and pub:
            publish_dates[vid] = pub

    print(f"Backdating {len(BATCH3_MAPPING)} topics...")
    print("=" * 60)

    success = 0
    failed = 0

    for video_id, topic_id in BATCH3_MAPPING.items():
        pub_date = publish_dates.get(video_id)
        if not pub_date:
            print(f"  ✗ {video_id}: No publish date found")
            failed += 1
            continue

        unix_ts = iso_to_unix(pub_date)
        ok, response = backdate_topic(base_url, api_key, api_username, topic_id, unix_ts)

        if ok:
            print(f"  ✓ Topic {topic_id} ({video_id}): backdated to {pub_date}")
            success += 1
        else:
            print(f"  ✗ Topic {topic_id} ({video_id}): FAILED - {response[:100]}")
            failed += 1

        sleep(0.5)  # Rate limit

    print("=" * 60)
    print(f"Complete: {success} success, {failed} failed")

if __name__ == "__main__":
    main()
