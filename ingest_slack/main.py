import asyncio
import os
import re
from collections.abc import AsyncIterable
from typing import Any, cast

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

try:
    from ingest_slack.taxonomy import SkillMatcher  # type: ignore
except Exception:
    try:
        from taxonomy import SkillMatcher  # type: ignore
    except Exception:
        SkillMatcher = None  # type: ignore

try:
    import ingest_slack.classifier as classifier_mod  # type: ignore
except Exception:
    try:
        import classifier as classifier_mod  # type: ignore
    except Exception:
        classifier_mod = None  # type: ignore

if classifier_mod is not None:
    MessageCandidate = classifier_mod.MessageCandidate  # type: ignore[attr-defined]
    classify_messages = classifier_mod.classify_messages  # type: ignore[attr-defined]
else:  # pragma: no cover
    MessageCandidate = None  # type: ignore[assignment]
    classify_messages = None  # type: ignore[assignment]

EXTRACT_SKILLS = os.environ.get("EXTRACT_SKILLS") == "1"
CLASSIFY_EXPERTISE = os.environ.get("CLASSIFY_EXPERTISE") == "1"

client = AsyncWebClient(token=os.environ["SLACK_BOT_AUTH_TOKEN"])
matcher: Any = SkillMatcher() if (EXTRACT_SKILLS and SkillMatcher is not None) else None


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


def _normalize_user(member: dict[str, Any]) -> dict[str, Any]:
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

    normalized_user = {
        "id": user_id,
        "display_name": display_name,
        "slack_name": slack_name,
        "tz": tz,
        "raw_data": member,
    }

    return normalized_user


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

            users.append(_normalize_user(member))

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
        print("  channel_id | channel_name")
        for channel in channels:
            print(f"  {channel['id']} | {channel['name']}")

        # Users
        user_dict = {}
        users = await list_workspace_users()
        print(f"\nWorkspace users (active, non-bot): {len(users)}")
        print("  user_id | slack_name | display_name | tz")
        for user in users:
            print(
                f"  {user['id']} | {user['slack_name']} | "
                f"{user['display_name']} | {user['tz']}"
            )
            user_dict[user["id"]] = user

        # Messages
        for channel in channels:
            print(f"\nMessages in #{channel['name']} (including thread replies):")
            print("  ts | thread_ts | user_id | text")

            # Maintain minimal thread context so replies can inherit parent skills
            thread_context: dict[str, dict[str, Any]] = {}

            async for message in iter_public_channel_history(
                channel["id"],
                page_size=200,
            ):
                # Extract mentioned user ids and replace them by names and id
                user_ids = re.findall(
                    r"<@([A-Z0-9]+)(?:\|[^>]+)?>", message.get("text", "")
                )
                for user_id in user_ids:
                    existing_user: dict[str, Any] | None = user_dict.get(user_id)
                    if existing_user:
                        message["text"] = message["text"].replace(
                            f"<@{user_id}>",
                            f"@{existing_user['slack_name']}[slack_user_id:{user_id}]",
                        )

                print(
                    f"  {message.get('ts')} | {message.get('thread_ts')} | "
                    f"{message.get('user') or message.get('bot_id')} | "
                    f"{message.get('text')}"
                )

                if EXTRACT_SKILLS and matcher is not None:
                    text_value = cast(str, message.get("text") or "")
                    matched_keys = matcher.match_text(text_value)

                    # Cache skills/text for parent messages (to be inherited by replies)
                    reply_count = cast(int, message.get("reply_count") or 0)
                    parent_id_for_parent = cast(
                        str, message.get("thread_ts") or message.get("ts") or ""
                    )
                    if reply_count > 0 and parent_id_for_parent:
                        thread_context[parent_id_for_parent] = {
                            "text": text_value,
                            "skills": matched_keys,
                        }

                    # Inherit thread parent's skills for replies
                    parent_text: str | None = None
                    combined_keys = matched_keys
                    is_reply = bool(message.get("thread_ts")) and message.get(
                        "ts"
                    ) != message.get("thread_ts")
                    if is_reply:
                        parent_id = cast(str, message.get("thread_ts") or "")
                        parent_ctx = thread_context.get(parent_id)
                        if parent_ctx:
                            parent_text = cast(str, parent_ctx.get("text") or "")
                            inherited = cast(list[str], parent_ctx.get("skills") or [])
                            if inherited:
                                seen: set[str] = set()
                                combined_list: list[str] = []
                                for k in list(matched_keys) + list(inherited):
                                    if k not in seen:
                                        combined_list.append(k)
                                        seen.add(k)
                                combined_keys = combined_list

                    if combined_keys:
                        names = [
                            matcher.describe(k).name
                            for k in combined_keys
                            if matcher.describe(k)
                        ]
                        if names:
                            print(f"    -> skills: {', '.join(names)}")

                        if (
                            CLASSIFY_EXPERTISE
                            and classify_messages is not None
                            and MessageCandidate is not None
                        ):
                            candidate = MessageCandidate(
                                message_id=f"{channel['id']}:{message.get('ts')}",
                                author_id=cast(str, message.get("user") or ""),
                                channel_id=channel["id"],
                                text=text_value,
                                parent_text=parent_text,
                                skill_keys=tuple(combined_keys),
                            )
                            try:
                                evals = classify_messages([candidate])
                                if evals and evals[0].results:
                                    pretty = ", ".join(
                                        f"{r.skill_key}:{r.label}@{r.confidence:.2f}"
                                        for r in evals[0].results
                                    )
                                    print(f"    -> expertise: {pretty}")
                            except Exception as cls_err:
                                print(
                                    f"    -> expertise classification error: {cls_err}"
                                )

    except SlackApiError as e:
        print(f"Slack error: {e.response['error']}")


if __name__ == "__main__":
    asyncio.run(main())
