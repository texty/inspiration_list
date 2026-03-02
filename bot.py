"""
Slack link bot — weekly sync for GitHub Actions.

Scans a Slack channel for messages containing URLs.
Category is read from a hashtag in the message text, e.g.:
  https://example.com/article  #dataviz

If no hashtag → saved as "uncategorized".

Required environment variables:
  SLACK_BOT_TOKEN   — Bot OAuth token (xoxb-...)
  SLACK_CHANNEL_ID  — Channel ID (e.g. C12345678)

Run locally:
  pip install slack-sdk requests beautifulsoup4
  SLACK_BOT_TOKEN=... SLACK_CHANNEL_ID=... python bot.py
"""

import json
import os
import re
import time

import requests
from bs4 import BeautifulSoup
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_CHANNEL_ID = os.environ["SLACK_CHANNEL_ID"]

STATE_FILE = "bot_state.json"
LINKS_FILE = "links.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; link-saver-bot/1.0)"}

client = WebClient(token=SLACK_BOT_TOKEN)
_user_cache: dict[str, str] = {}


# ── State & data I/O ─────────────────────────────────────────────────────────

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    # First run: look back 90 days to catch existing messages
    return {"last_run_ts": str(time.time() - 90 * 86400)}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def load_links() -> list:
    if os.path.exists(LINKS_FILE):
        with open(LINKS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_links(links: list) -> None:
    with open(LINKS_FILE, "w", encoding="utf-8") as f:
        json.dump(links, f, indent=2, ensure_ascii=False)


# ── Slack helpers ─────────────────────────────────────────────────────────────

def get_bot_user_id() -> str:
    return client.auth_test()["user_id"]


def get_username(user_id: str) -> str:
    if user_id in _user_cache:
        return _user_cache[user_id]
    try:
        info = client.users_info(user=user_id)
        profile = info["user"].get("profile", {})
        name = profile.get("display_name") or info["user"].get("name") or user_id
    except SlackApiError:
        name = user_id
    _user_cache[user_id] = name
    return name


def fetch_messages(channel: str, oldest: str) -> list:
    """Fetch all messages since `oldest` timestamp, in chronological order."""
    messages = []
    cursor = None
    while True:
        kwargs: dict = {"channel": channel, "oldest": oldest, "limit": 200}
        if cursor:
            kwargs["cursor"] = cursor
        resp = client.conversations_history(**kwargs)
        messages.extend(resp["messages"])
        if resp.get("has_more") and resp.get("response_metadata", {}).get("next_cursor"):
            cursor = resp["response_metadata"]["next_cursor"]
        else:
            break
    return list(reversed(messages))  # oldest first


# ── Parsing ───────────────────────────────────────────────────────────────────

def extract_url(text: str) -> str | None:
    """Extract first URL from a Slack message.
    Slack wraps links as <https://...> or <https://...|label>.
    """
    match = re.search(r"<(https?://[^|>\s]+)(?:\|[^>]*)?>", text)
    return match.group(1) if match else None


def extract_category(text: str) -> str:
    """Extract category from a hashtag, e.g. '#dataviz' → 'dataviz'.
    Returns 'uncategorized' if no hashtag found.
    Ignores Slack channel mentions like <#C12345|channel-name>.
    """
    # Remove Slack channel mentions first
    cleaned = re.sub(r"<#[A-Z0-9]+\|[^>]+>", "", text)
    match = re.search(r"#([A-Za-z][A-Za-z0-9_-]*)", cleaned)
    return match.group(1) if match else "uncategorized"


# ── OG metadata ───────────────────────────────────────────────────────────────

def fetch_og(url: str) -> dict:
    result = {"title": "", "cover_image": ""}
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for prop in ("og:title", "twitter:title"):
            tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            if tag and tag.get("content"):
                result["title"] = tag["content"].strip()
                break
        if not result["title"]:
            tag = soup.find("title")
            if tag:
                result["title"] = tag.get_text().strip()

        for prop in ("og:image", "twitter:image"):
            tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
            if tag and tag.get("content"):
                img = tag["content"].strip()
                if img.startswith("//"):
                    img = "https:" + img
                result["cover_image"] = img
                break

    except Exception as e:
        print(f"  OG error for {url}: {e}")

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    state = load_state()
    links = load_links()
    existing_urls = {l["url"] for l in links}

    bot_user_id = get_bot_user_id()
    print(f"Bot: {bot_user_id}")

    messages = fetch_messages(SLACK_CHANNEL_ID, state["last_run_ts"])
    print(f"Fetched {len(messages)} messages\n")

    saved = 0

    for msg in messages:
        # Skip bot's own messages and thread replies
        if msg.get("user") == bot_user_id:
            continue
        if msg.get("thread_ts") and msg["thread_ts"] != msg["ts"]:
            continue

        text = msg.get("text", "")
        url = extract_url(text)
        if not url:
            continue
        if url in existing_urls:
            continue

        category = extract_category(text)
        author = get_username(msg.get("user", "unknown"))

        print(f"→ {url}")
        print(f"  category: {category} | author: {author}")

        og = fetch_og(url)
        print(f"  title: {og['title'][:60] or '(none)'}")
        print(f"  image: {'✓' if og['cover_image'] else '–'}")

        links.append({
            "url": url,
            "title": og["title"],
            "excerpt": "",
            "note": "",
            "category": category,
            "author": author,
            "cover_image": og["cover_image"],
            "date": msg["ts"],
        })
        existing_urls.add(url)
        saved += 1

    state["last_run_ts"] = str(time.time())
    save_state(state)
    save_links(links)

    print(f"\nSaved {saved} new link(s). Total: {len(links)}.")


if __name__ == "__main__":
    main()
