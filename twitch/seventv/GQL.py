# from aiohttp_sse_client import client as sse_client
from datetime import timedelta
from enum import Enum
import os
from typing import Optional

from dotenv import load_dotenv; load_dotenv()
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.exceptions import TransportQueryError

from .cache import memoize_async
from .REST import emoteset_id, seventv_user_id
from twitch.exceptions import SevenTVException


__all__ = (
    "get_editors",
    "search_emote_by_name",
    "add_emote",
    "remove_emote",
    "rename_emote",
)


class Action(Enum):
    ADD = "ADD"
    REMOVE = "REMOVE"
    UPDATE = "UPDATE"


ENDPOINT = "https://7tv.io/v3/gql"
TIMEOUT = 7

transport = AIOHTTPTransport(url=ENDPOINT, timeout=TIMEOUT)

async def _get_editors(seventv_id: str) -> list[str]:
    async with Client(transport=transport) as session:
        query = gql(
            """
        query GetCurrentUser ($id: ObjectID!) {
            user (id: $id) {
                editors {
                    user {
                        username
                    }
                }
            }
        }
        """
        )
        variables = {"id": seventv_id}

        try:
            query_results = await session.execute(query, variable_values=variables)
        except TransportQueryError as tqe:
            message = tqe.errors[0]['message'].lower()
            if message.split()[0].isdigit():
                message = " ".join(message.split()[1:])
            raise SevenTVException(f"Failed to fetch channel editors ({message})")
        except TimeoutError:
            raise SevenTVException(f"Failed to fetch channel editors (request timed out)")

        editors = [
            editor["user"]["username"] for editor in query_results["user"]["editors"]
        ]
        return editors


@memoize_async(ttl=timedelta(hours=6))
async def get_editors(twitch_id: int) -> list[str]:
    seventv_id = await seventv_user_id(twitch_id)
    editors = await _get_editors(seventv_id)
    return editors


async def search_emote_by_name(
    emote: str,
    *,
    exact_match: bool = False,
    case_sensitive: bool = False,
    ignore_tags: bool = False,
    zero_width: bool = False,
) -> list[dict[str, str]]:
    async with Client(transport=transport) as session:
        query = gql(
            """
            query SearchEmotes($query: String!, $limit: Int, $filter: EmoteSearchFilter) {
                emotes(query: $query, limit: $limit, filter: $filter) {
                    items {
                        id
                        name
                    }
                }
            }
        """
        )
        variables = {
            "query": emote,
            "limit": 20,
            "page": 1,
            "filter": {
                "exact_match": exact_match,
                "case_sensitive": case_sensitive,
                "ignore_tags": ignore_tags,
                "zero_width": zero_width,
            },
        }
        try:
            query_results = await session.execute(query, variable_values=variables)
        except TransportQueryError as tqe:
            message = tqe.errors[0]['message'].lower()
            if message.split()[0].isdigit():
                message = " ".join(message.split()[1:])
            raise SevenTVException(f"Failed to search for emote ({message})")
        except TimeoutError:
            raise SevenTVException(f"Failed to search for emote (request timed out)")
        return query_results["emotes"]["items"]


async def _modify_emoteset(
    emoteset_id: str, action: Action, emote_id: str, alias: Optional[str] = None
) -> Optional[str]:
    headers = {
        "Authorization": f"Bearer {os.environ['SEVEN_TV_TOKEN']}",
        "Content-Type": "application/json",
    }
    transport = AIOHTTPTransport(url=ENDPOINT, headers=headers, timeout=TIMEOUT)
    async with Client(transport=transport) as session:
        query = gql(
            """
        mutation ChangeEmoteInSet($id: ObjectID! $action: ListItemAction! $emote_id: ObjectID!, $name: String) {
            emoteSet(id: $id) {
                id
                emotes(id: $emote_id action: $action, name: $name) {
                    id
                    name
                }
            }
        }
        """
        )

        variables = {
            "id": emoteset_id,
            "action": action.value,
            "emote_id": emote_id,
            "name": alias,
        }
        try:
            query_results = await session.execute(query, variable_values=variables)
        except TransportQueryError as tqe:
            message = tqe.errors[0]['message'].lower()
            if message.split()[0].isdigit():
                message = " ".join(message.split()[1:])
            raise SevenTVException(f"Failed to {action.value.lower()} emote ({message})")
        except TimeoutError:
            raise SevenTVException(f"Failed to {action.value.lower()} emote (request timed out)")

        if action == Action.ADD:
            added_emote = [
                emote["name"]
                for emote in query_results["emoteSet"]["emotes"]
                if emote["id"] == emote_id
            ][0]
            return added_emote


async def add_emote(
    twitch_id: str | int, emote_id: str, alias: Optional[str] = None
) -> str:
    emoteset = await emoteset_id(twitch_id)
    added_emote = await _modify_emoteset(emoteset, Action.ADD, emote_id, alias)
    return added_emote


async def remove_emote(twitch_id: str | int, emote_id: str) -> None:
    emoteset = await emoteset_id(twitch_id)
    await _modify_emoteset(emoteset, Action.REMOVE, emote_id)


async def rename_emote(twitch_id: str | int, emote_id: str, new_name: str) -> None:
    emoteset = await emoteset_id(twitch_id)
    await _modify_emoteset(emoteset, Action.UPDATE, emote_id, new_name)

