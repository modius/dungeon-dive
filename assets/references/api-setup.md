# API Setup Guide

> **Important**: Backdating posts to match YouTube publish dates requires **admin privileges** on your Discourse API key. See the Discourse API section below for details.

## Configuration File

Create `config.json` in your workspace folder:

```json
{
  "youtube": {
    "api_key": "YOUR_YOUTUBE_API_KEY",
    "channel_id": "UC_DUNGEON_DIVE_CHANNEL_ID"
  },
  "discourse": {
    "base_url": "https://dungeondive.quest",
    "api_key": "YOUR_DISCOURSE_API_KEY",
    "api_username": "archive_bot",
    "post_as_username": "archive_bot",
    "category_id": 5
  }
}
```

---

## YouTube Data API v3

### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (e.g., "Dungeon Dive Sync")
3. Navigate to **APIs & Services** > **Library**
4. Search for "YouTube Data API v3" and **Enable** it

### Step 2: Create API Key

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **API Key**
3. Copy the key to your `config.json`
4. (Optional) Restrict the key to YouTube Data API v3 only

### Step 3: Find Channel ID

The channel ID is in the channel URL or can be found via:
- Channel URL: `youtube.com/channel/UC...` — the `UC...` part is the ID
- If using a custom URL, visit the channel, click **About**, and look for the channel ID

### Quota Notes

- Free tier: 10,000 units/day
- `playlistItems.list`: 1 unit per call (50 videos per call)
- Sufficient for cataloguing hundreds of videos daily

---

## Discourse API

### Step 1: Create Bot Account with Admin Privileges

To backdate posts to match YouTube publish dates, your bot account needs **admin privileges**:

1. Create a new user account (e.g., `archive_bot`)
2. Give it a recognisable name like "Archive Bot" or "Dungeon Dive Archive"
3. Optionally add an avatar to distinguish automated posts
4. **Grant admin privileges**: Go to **Admin** > **Users** > find your bot > click **Grant Admin**

Without admin privileges, topics will be created but will have the current date instead of the video's publish date.

### Step 2: Create API Key

1. Log into Discourse as an **admin**
2. Go to **Admin** > **API** > **API Keys**
3. Click **New API Key**
4. Settings:
   - **Description**: "YouTube Archive Sync"
   - **User Level**: **Single User** — Select the bot account
   - **Scope**: Global (or restrict to specific endpoints)
5. Copy the key to your `config.json`

**Why Single User?** The API key inherits the bot account's admin privileges, allowing it to backdate posts. An "All Users" key would also work but grants broader access than needed.

### Posting as a Specific User

**Option A: Bot's own API key**
Set `post_as_username` to match the API key owner. Posts appear from that account.

**Option B: Admin key + username override**
With an admin-level API key, set `post_as_username` to any valid username. The API will create posts as that user.

### Step 3: Find Category ID

1. Go to your target category in Discourse
2. Look at the URL: `dungeondive.quest/c/videos/5` — the number at the end is the category ID
3. Or use the API: `GET /categories.json`

### API Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `POST /posts` | Create new topic |
| `PUT /t/{id}/change-timestamp` | Backdate the topic (admin only) |
| `GET /categories.json` | List categories |

### Backdating Posts (Critical Feature)

This sync tool backdates Discourse topics so they appear in the forum timeline at the same date the video was originally published on YouTube. This is essential for maintaining chronological integrity when importing historical videos.

The script automatically calls this endpoint after creating each topic:

```
PUT /t/{topic_id}/change-timestamp
{ "timestamp": 1718452800 }  ← Unix timestamp
```

**Requirements:**
- The API key must belong to a user with **admin privileges**
- If backdating fails, the topic is still created but retains the current date
- The script will warn you if backdating fails due to insufficient permissions

---

## Testing Your Configuration

Run the test script to verify both APIs:

```bash
python3 scripts/test_config.py
```

This will:
1. Fetch channel info from YouTube
2. List categories from Discourse
3. Report any authentication issues
