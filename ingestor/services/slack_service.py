import re
from collections.abc import AsyncIterable
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from slack_sdk.web.async_client import AsyncWebClient

from config import settings


class SlackService:
    def __init__(self):
        self.client = AsyncWebClient(token=settings.slack_bot_auth_token)

    async def get_public_channels(
        self, exclude_archived: bool = True
    ) -> list[dict[str, Any]]:
        """Get all public channels the bot is a member of"""
        channels: list[dict[str, Any]] = []
        cursor = None

        while True:
            resp = await self.client.users_conversations(
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

    async def get_workspace_users(
        self,
        exclude_deleted: bool = True,
        exclude_bots: bool = True,
    ) -> dict[str, dict[str, Any]]:
        """Get all workspace users, returning as dict keyed by user_id"""
        users: dict[str, dict[str, Any]] = {}
        cursor = None

        while True:
            resp = await self.client.users_list(limit=1000, cursor=cursor)
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

                normalized_user = self._normalize_user(member)
                users[normalized_user["slack_id"]] = normalized_user

            cursor = resp_data.get("response_metadata", {}).get("next_cursor") or None
            if not cursor:
                break

        return users

    def _normalize_user(self, member: dict[str, Any]) -> dict[str, Any]:
        """Normalize user data from Slack API"""
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

        return {
            "slack_id": user_id,
            "display_name": display_name,
            "slack_name": slack_name,
            "timezone": tz,
            "raw_data": member,
        }

    async def get_recent_messages(
        self,
        channel_id: str,
        since_hours: int = 1,
        page_size: int = 200,
        thread_page_size: int = 200,
    ) -> AsyncIterable[dict[str, Any]]:
        """Get messages from the last N hours"""
        # Calculate oldest timestamp
        oldest_time = datetime.now(UTC) - timedelta(hours=since_hours)
        oldest = str(oldest_time.timestamp())

        cursor = None

        while True:
            resp = await self.client.conversations_history(
                channel=channel_id,
                oldest=oldest,
                limit=page_size,
                cursor=cursor,
            )
            resp_data = cast(dict[str, Any], resp.data)

            for message in resp_data.get("messages", []):
                # Skip channel join messages
                if message.get("subtype") == "channel_join":
                    continue

                # Add channel_id to message for context
                message["channel_id"] = channel_id
                yield message

                # Include replies from threads
                if message.get("reply_count", 0) > 0:
                    parent_ts = cast(str, message.get("thread_ts") or message.get("ts"))
                    thread_cursor = None

                    while True:
                        thread_response = await self.client.conversations_replies(
                            channel=channel_id,
                            ts=parent_ts,
                            limit=thread_page_size,
                            cursor=thread_cursor,
                        )
                        thread_response_data = cast(
                            dict[str, Any], thread_response.data
                        )

                        for thread_message in thread_response_data.get("messages", []):
                            # Skip the parent message (first element)
                            if thread_message.get("ts") == parent_ts:
                                continue

                            thread_message["channel_id"] = channel_id
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

    def replace_user_mentions(self, text: str, users: dict[str, dict[str, Any]]) -> str:
        """Replace Slack user mentions with readable format"""
        user_ids = re.findall(r"<@([A-Z0-9]+)(?:\|[^>]+)?>", text)

        for user_id in user_ids:
            user = users.get(user_id)
            if user:
                text = text.replace(
                    f"<@{user_id}>",
                    f"@{user['slack_name']}[slack_user_id:{user_id}]",
                )

        return text
