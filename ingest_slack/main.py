import os
from collections.abc import Iterable
from typing import Any

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

client = WebClient(token=os.environ["SLACK_BOT_AUTH_TOKEN"])


def list_public_channels_bot_is_in(
    exclude_archived: bool = True,
) -> list[dict[str, Any]]:
    channels: list[dict[str, Any]] = []
    cursor = None

    while True:
        resp = client.users_conversations(
            types="public_channel",
            exclude_archived=exclude_archived,
            limit=1000,
            cursor=cursor,
        )
        channels.extend(resp.get("channels", []))
        cursor = resp.get("response_metadata", {}).get("next_cursor") or None
        if not cursor:
            break

    return channels


def iter_public_channel_history(
    channel_id: str,
    oldest: float | None = None,
    latest: float | None = None,
    page_size: int = 200,
) -> Iterable[dict[str, Any]]:
    cursor = None

    while True:
        resp = client.conversations_history(
            channel=channel_id,
            oldest=oldest,
            latest=latest,
            limit=page_size,
            cursor=cursor,
        )
        yield from resp.get("messages", [])
        cursor = resp.get("response_metadata", {}).get("next_cursor") or None
        if not cursor:
            break


if __name__ == "__main__":
    try:
        channels = list_public_channels_bot_is_in()
        print(f"Bot is in {len(channels)} public channels:")
        for ch in channels:
            print(f"- {ch['name']} ({ch['id']})")

        # Example: fetch and print the last 10 messages of each channel
        for ch in channels:
            print(f"\nLast messages in #{ch['name']}:")
            last_ten = []
            for m in iter_public_channel_history(ch["id"], page_size=200):
                last_ten.append(m)
                if len(last_ten) > 10:
                    last_ten.pop(0)
            for m in last_ten:
                print(
                    f"{m.get('ts')} | {m.get('user') or m.get('bot_id')} | {m.get('text')}"
                )
    except SlackApiError as e:
        print(f"Slack error: {e.response['error']}")
