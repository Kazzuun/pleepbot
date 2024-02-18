from datetime import timedelta
import random
import re
from typing import Union, Callable

import aiohttp

from twitch.exceptions import SevenTVException
from .cache import memoize_async


__all__ = (
    "global_emotes",
    "emote_from_id",
    "seventv_user_id",
    "emoteset_id",
    "channel_emotes",
    "is_valid_emoteid",
    "best_fitting_emote",
)

ENDPOINT = "https://7tv.io/v3"
TIMEOUT = aiohttp.ClientTimeout(total=7)


# TODO: Document your code: https://numpydoc.readthedocs.io/en/latest/format.html

@memoize_async()
async def global_emotes() -> list[dict[str, str]]:
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        url = f"{ENDPOINT}/emote-sets/global"
        try:
            async with session.get(url) as resp:
                response = await resp.json()
                emotes = [
                    {key: emote[key] for key in ("id", "name")}
                    for emote in response["emotes"]
                ]
                return emotes
        except TimeoutError:
            raise SevenTVException("Failed to fetch global emotes (request timed out)")


@memoize_async(ttl=timedelta(hours=3))
async def _channel_info(twitch_id: Union[str, int], *, force: bool = False) -> dict:
    """
    """
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        url = f"{ENDPOINT}/users/twitch/{twitch_id}"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    response = await resp.json()
                    return response
                elif resp.status == 404:
                    return None
                else:
                    raise SevenTVException(f"Something went wrong with fetching from api (status {resp.status})")
        except TimeoutError:
            raise SevenTVException("Failed to fetch 7tv info (request timed out)")


@memoize_async()
async def emote_from_id(emote_id: str) -> dict:
    """
    """
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        url = f"{ENDPOINT}/emotes/{emote_id}"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    response = await resp.json()
                    return response
                else:
                    raise SevenTVException(f"Something went wrong with fetching from api (status {resp.status})")
        except TimeoutError:
            raise SevenTVException("Failed to fetch the emote (request timed out)")


@memoize_async()
async def seventv_user_id(twitch_id: Union[str, int]) -> str:
    """
    This function makes an api call to the 7tv REST api and fetches
    the 7tv user id belonging to the given twitch user id.
    Results are cached indefinitely.

    Parameters
    ----------
    twitch_id : Union[:class:`str`, :class:`int`]

    Returns
    -------
    str
        User's 7tv account id

    Raises
    ------
    SevenTVException
        If the user doesn't have a 7tv account or if something went wrong with the api request
    """
    response = await _channel_info(twitch_id)
    if response is None:
        raise SevenTVException("Channel does not have twitch linked with a 7tv account")
    userid = response["user"]["id"]
    return userid


@memoize_async()
async def emoteset_id(twitch_id: Union[str, int]) -> str:
    response = await _channel_info(twitch_id)
    if response is None:
        raise SevenTVException("Channel does not have an emoteset")
    emoteset_id = response["emote_set"]["id"]
    return emoteset_id


async def channel_emotes(twitch_id: Union[str, int], *, force: bool = False) -> list[dict[str, str]]:
    response = await _channel_info(twitch_id, force=force)
    if response is None:
        return []
    emotes = [
        {key: emote[key] for key in ("id", "name")}
        for emote in response["emote_set"]["emotes"]
    ]
    return emotes


def is_valid_emoteid(emote_id: str) -> bool:
    """
    7tv emotes use a mongodb object id as an identifier.
    This verifies that the given string is of the correct form.
    """
    mongoid_pattern = re.compile(r'^[0-9a-fA-F]{24}$')
    # ulid coming soon
    # ulid_pattern = re.compile(r'[0-7][0-9A-HJKMNP-TV-Z]{25}')
    return bool(mongoid_pattern.match(emote_id)) # or bool(ulid_pattern.match(emote_id))


async def best_fitting_emote(
    twitch_id: Union[str, int], filter_func: Callable[[str], bool], *, default: str = ""
) -> str:
    emotes = [emote["name"] for emote in await channel_emotes(twitch_id)]
    filtered_emotes = list(filter(filter_func, emotes))
    if len(filtered_emotes) == 0:
        return default
    return random.choice(filtered_emotes)
