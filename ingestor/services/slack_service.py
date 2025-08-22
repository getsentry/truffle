import asyncio
import logging
import re
from collections.abc import AsyncIterable
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import sentry_sdk
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from config import settings

logger = logging.getLogger(__name__)


class SlackService:
    def __init__(self):
        self.client = AsyncWebClient(token=settings.slack_bot_auth_token)
        self._bot_user_id: str | None = None
        self._request_count = 0
        self._batch_size = settings.slack_batch_size
        self._batch_wait_seconds = settings.slack_batch_wait_seconds

    async def _batch_rate_limited_api_call(self, api_call, max_retries: int = 3):
        """Make API call with batch-based rate limiting (50 requests per minute)"""
        # Check if we need to wait for next batch
        if self._request_count >= self._batch_size:
            logger.info(
                f"Reached batch limit ({self._batch_size} requests), "
                f"waiting {self._batch_wait_seconds} seconds for next batch..."
            )
            await asyncio.sleep(self._batch_wait_seconds)
            self._request_count = 0
            logger.info("Starting new batch of requests")

        for attempt in range(max_retries):
            try:
                # Small delay between individual requests in batch
                await asyncio.sleep(0.1)
                result = await api_call()
                self._request_count += 1
                logger.debug(
                    f"API request {self._request_count}/{self._batch_size} in current batch"
                )
                return result
            except SlackApiError as e:
                if e.response["error"] == "ratelimited" and attempt < max_retries - 1:
                    # Get retry-after header if available, else use exponential backoff
                    retry_after = e.response.get("headers", {}).get("Retry-After")
                    if retry_after:
                        delay = float(retry_after) + 1  # Add 1 second buffer
                    else:
                        # Exponential backoff
                        delay = (2**attempt) * 2

                    logger.warning(
                        f"Rate limited by Slack API "
                        f"(attempt {attempt + 1}/{max_retries}), "
                        f"waiting {delay:.1f} seconds..."
                    )
                    await asyncio.sleep(delay)
                else:
                    raise

        raise Exception(f"Failed after {max_retries} attempts due to rate limiting")

    @sentry_sdk.trace
    async def get_public_channels(
        self, exclude_archived: bool = True
    ) -> list[dict[str, Any]]:
        """Get all public channels the bot is a member of"""
        channels: list[dict[str, Any]] = []
        cursor = None

        while True:
            resp = await self._batch_rate_limited_api_call(
                lambda c=cursor: self.client.users_conversations(
                    types="public_channel",
                    exclude_archived=exclude_archived,
                    limit=1000,
                    cursor=c,
                )
            )
            resp_data = cast(dict[str, Any], resp.data)
            channels.extend(resp_data.get("channels", []))

            cursor = resp_data.get("response_metadata", {}).get("next_cursor") or None
            if not cursor:
                break

        return channels

    @sentry_sdk.trace
    async def get_workspace_users(
        self,
        exclude_deleted: bool = True,
        exclude_bots: bool = True,
    ) -> dict[str, dict[str, Any]]:
        """Get all workspace users, returning as dict keyed by user_id"""
        users: dict[str, dict[str, Any]] = {}
        cursor = None

        while True:
            resp = await self._batch_rate_limited_api_call(
                lambda c=cursor: self.client.users_list(limit=1000, cursor=c)
            )
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

    @sentry_sdk.trace
    async def get_bot_user_id(self) -> str:
        """Get the bot's user ID using auth.test API"""
        if self._bot_user_id is None:
            # auth_test doesn't count against rate limits, so use direct call
            resp = await self.client.auth_test()
            resp_data = cast(dict[str, Any], resp.data)
            self._bot_user_id = resp_data.get("user_id")
        return self._bot_user_id or ""

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

    @sentry_sdk.trace
    async def get_recent_messages(
        self,
        channel_id: str,
        since_hours: float = 1,
        page_size: int = 200,
        thread_page_size: int = 200,
    ) -> AsyncIterable[dict[str, Any]]:
        """Get messages from the last N hours"""
        # Calculate oldest timestamp
        oldest_time = datetime.now(UTC) - timedelta(hours=since_hours)
        oldest = str(oldest_time.timestamp())

        cursor = None

        while True:
            resp = await self._batch_rate_limited_api_call(
                lambda c=cursor: self.client.conversations_history(
                    channel=channel_id,
                    oldest=oldest,
                    limit=page_size,
                    cursor=c,
                )
            )
            resp_data = cast(dict[str, Any], resp.data)

            for message in resp_data.get("messages", []):
                # Skip messages sent by Slack itself
                # See https://api.slack.com/events/message#subtypes
                if message.get("subtype") is not None:
                    continue

                # Skip messages that mention the bot
                if await self._message_mentions_bot(message):
                    continue

                # Add channel_id to message for context
                message["channel_id"] = channel_id
                yield message

                # Include replies from threads
                if message.get("reply_count", 0) > 0:
                    parent_ts = cast(str, message.get("thread_ts") or message.get("ts"))
                    thread_cursor = None

                    while True:
                        thread_response = await self._batch_rate_limited_api_call(
                            lambda ts=parent_ts, tc=thread_cursor: (
                                self.client.conversations_replies(
                                    channel=channel_id,
                                    ts=ts,
                                    limit=thread_page_size,
                                    cursor=tc,
                                )
                            )
                        )
                        thread_response_data = cast(
                            dict[str, Any], thread_response.data
                        )

                        for thread_message in thread_response_data.get("messages", []):
                            # Skip the parent message (first element)
                            if thread_message.get("ts") == parent_ts:
                                continue

                            # Skip thread messages that mention the bot
                            if await self._message_mentions_bot(thread_message):
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

    async def _message_mentions_bot(self, message: dict[str, Any]) -> bool:
        """Check if a message mentions the bot"""
        text = message.get("text", "")
        if not text:
            return False

        bot_user_id = await self.get_bot_user_id()
        if not bot_user_id:
            return False

        # Check for @mention of bot using <@USER_ID> format
        mention_pattern = f"<@{bot_user_id}(?:\\|[^>]+)?>"
        return bool(re.search(mention_pattern, text))

    def reset_batch_counter(self):
        """Reset the batch counter - useful for starting fresh batches per channel or operation"""
        self._request_count = 0
        logger.debug("Reset API request batch counter")

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
