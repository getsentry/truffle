import asyncio
import os
import re
from collections.abc import AsyncIterable
from typing import Any, cast

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

client = AsyncWebClient(token=os.environ["SLACK_BOT_AUTH_TOKEN"])


async def list_public_channels_bot_is_in(
    exclude_archived: bool = True,
) -> list[dict[str, Any]]:
    channels: list[dict[str, Any]] = []
    cursor = None

    while True:
        resp = await client.users_conversations(
            types="public_channel",
            exclude_archived=exclude_archived,
            limit=1000,
            cursor=cursor,
        )
        resp_data = cast(dict[str, Any], resp.data)
        channels.extend(resp_data.get("channels", []))
        cursor = resp_data.get("response_metadata", {}).get("next_cursor") or None
        if not cursor:
            break

    return channels


async def list_workspace_users(
    exclude_deleted: bool = True,
    exclude_bots: bool = True,
) -> list[dict[str, str]]:
    users: list[dict[str, str]] = []
    cursor = None

    while True:
        resp = await client.users_list(limit=1000, cursor=cursor)
        resp_data = cast(dict[str, Any], resp.data)
        for member in resp_data.get("members", []):
            if exclude_deleted and member.get("deleted"):
                continue
            if exclude_bots and (
                member.get("is_bot")
                or member.get("is_app_user")
                or member.get("id") == "USLACKBOT"
            ):
                continue

            user_id = cast(str, member.get("id"))
            profile = cast(dict[str, Any], member.get("profile") or {})
            display_name = cast(
                str,
                profile.get("display_name")
                or profile.get("real_name")
                or member.get("name")
                or user_id,
            )
            slack_name = cast(str, member.get("name"))
            tz = cast(str, member.get("tz"))
            users.append(
                {
                    "id": user_id,
                    "display_name": display_name,
                    "slack_name": slack_name,
                    "tz": tz,
                    "raw_data": member,
                }
            )

        cursor = resp_data.get("response_metadata", {}).get("next_cursor") or None
        if not cursor:
            break

    return users


async def iter_public_channel_history(
    channel_id: str,
    oldest: str | None = None,
    latest: str | None = None,
    page_size: int = 200,
    thread_page_size: int = 200,
) -> AsyncIterable[dict[str, Any]]:
    cursor = None

    while True:
        resp = await client.conversations_history(
            channel=channel_id,
            oldest=oldest,
            latest=latest,
            limit=page_size,
            cursor=cursor,
        )
        resp_data = cast(dict[str, Any], resp.data)
        for message in resp_data.get("messages", []):
            # Skip channel join messages
            if message.get("subtype") == "channel_join":
                continue

            yield message

            # Include replies from threads
            if message.get("reply_count", 0) > 0:
                parent_ts = cast(str, message.get("thread_ts") or message.get("ts"))
                thread_cursor = None
                while True:
                    thread_response = await client.conversations_replies(
                        channel=channel_id,
                        ts=parent_ts,
                        limit=thread_page_size,
                        cursor=thread_cursor,
                    )
                    thread_response_data = cast(dict[str, Any], thread_response.data)
                    for thread_message in thread_response_data.get("messages", []):
                        # Skip the parent message (first element)
                        skip_parent_message = thread_message.get("ts") == parent_ts
                        if skip_parent_message:
                            continue

                        yield thread_message

                    thread_cursor = (
                        thread_response_data.get("response_metadata", {}).get(
                            "next_cursor"
                        )
                        or None
                    )
                    if not thread_cursor:
                        break

        cursor = resp_data.get("response_metadata", {}).get("next_cursor") or None
        if not cursor:
            break


async def main() -> None:
    try:
        # Channels
        channels = await list_public_channels_bot_is_in()
        print(f"Bot is in {len(channels)} public channels:")
        for channel in channels:
            print(f"- {channel['name']} ({channel['id']})")

        # Users
        user_dict = {}
        users = await list_workspace_users()
        print(f"\nWorkspace users (active, non-bot): {len(users)}")
        for u in users:
            print(
                f"- <@{u['id']}> | {u['id']} | {u['slack_name']} | "
                f"{u['display_name']} | {u['tz']}"
            )
            user_dict[u["id"]] = u

        import ipdb

        ipdb.set_trace()
        # Messages
        for channel in channels:
            print(f"\nMessages in #{channel['name']} (including thread replies):")
            async for message in iter_public_channel_history(
                channel["id"],
                page_size=200,
            ):
                # Extract mentioned user ids and replace them by names and id
                user_ids = re.findall(
                    r"<@([A-Z0-9]+)(?:\|[^>]+)?>", message.get("text", "")
                )
                for user_id in user_ids:
                    user = user_dict.get(user_id)
                    if user:
                        message["text"] = message["text"].replace(
                            f"<@{user_id}>",
                            f"@{user['slack_name']} (User ID: {user_id})",
                        )

                print(
                    f"{message.get('ts')} | {message.get('thread_ts')} | "
                    f"{message.get('user') or message.get('bot_id')} | "
                    f"{message.get('text')}"
                )

    except SlackApiError as e:
        print(f"Slack error: {e.response['error']}")


if __name__ == "__main__":
    asyncio.run(main())
