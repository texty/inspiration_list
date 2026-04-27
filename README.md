# Link Saver Bot

Slack bot that scans a channel for URLs, fetches OG metadata (title + cover image), and saves everything to `links.json`. A static front-end (`index.html`) renders the collected links.

## How it works

1. Someone posts a URL in the Slack channel, optionally tagging it with a `#category`
2. The bot picks it up, scrapes OG title + image, and appends it to `links.json`
3. Changes are committed and pushed to `main` automatically

---

## Setup

### 1. GitHub Secrets

Go to **Settings → Secrets and variables → Actions** in the repository and add:

| Secret | Description |
|---|---|
| `SLACK_BOT_TOKEN` | Bot OAuth token (`xoxb-...`) |
| `SLACK_CHANNEL_ID` | Channel ID (`C12345678`) — found in the channel URL or right-click → Copy link |

### 2. Slack App permissions

The bot token needs these OAuth scopes:
- `channels:history`
- `users:read`

---

## Automatic sync (cron)

The workflow runs **every Monday at 09:00 UTC** via GitHub Actions.

File: `.github/workflows/slack-sync.yml`

It:
1. Installs dependencies
2. Runs `bot.py` to fetch new Slack messages since the last run
3. Commits `links.json` and `bot_state.json` if anything changed

No manual action needed — just merge to `main` and it runs on schedule.

---

## Manual trigger (without running locally)

To run the sync outside the Monday schedule, use the **GitHub UI**:

1. Go to the repository on GitHub
2. Click **Actions** tab
3. Select **Slack Link Sync** workflow on the left
4. Click **Run workflow** → **Run workflow**

This triggers the exact same job as the cron — no local setup required.

---

## Local run

Useful for debugging or running between cron jobs from your machine.

### Install dependencies

```bash
pip install slack-sdk requests beautifulsoup4
```

Or with a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install slack-sdk requests beautifulsoup4
```

### Run the bot

```bash
SLACK_BOT_TOKEN=xoxb-... SLACK_CHANNEL_ID=C12345678 python bot.py
```

After it runs, commit and push the updated files:

```bash
git add links.json bot_state.json
git commit -m "bot: manual sync"
git push
```

---

## Utility scripts

### Re-fetch missing cover images

Run this when links are missing cover images (e.g. sites that blocked the bot on first scrape):

```bash
# Test on first 5 links without an image
python fetch_og.py --sample 5

# Process all links without an image
python fetch_og.py --all

# Re-fetch even links that already have an image
python fetch_og.py --refetch
```

Then commit:

```bash
git add links.json
git commit -m "fix: update cover images"
git push
```

### Merge Pocket collections

Import links from JSON files in the `collections/` directory:

```bash
# Merge all collections
python merge.py
```

Each file in `collections/` must follow this structure:

```json
{
  "title": "Category Name",
  "items": [
    { "url": "https://...", "title": "...", "excerpt": "..." }
  ]
}
```

---

## Project structure

```
.
├── bot.py                  # Main sync script
├── fetch_og.py             # Utility: re-fetch OG images
├── merge.py                # Utility: import Pocket collections
├── links.json              # Link data store
├── bot_state.json          # Last run timestamp
├── index.html              # Static front-end
├── app.js
├── style.css
├── collections/            # Pocket export JSONs
└── .github/workflows/
    └── slack-sync.yml      # GitHub Actions workflow
```

---

## Message format in Slack

```
https://example.com/article  #categoryname
```

- One URL per message
- `#tag` sets the category — defaults to `uncategorized` if omitted
- Thread replies are ignored
- Duplicate URLs are skipped automatically