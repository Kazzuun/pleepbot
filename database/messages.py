from collections import Counter
from datetime import datetime
import os
from typing import Optional

import aiosqlite
from dotenv import load_dotenv; load_dotenv()

from .db import db_path


__all__ = (
    "log_message", 
    "bot_last_message", 
    "emote_count",
    "emote_counts",
    "random_message",
    "nofmessages",
    "lastseen",
    "stalk"
)


async def log_message(channel: str, sender: str, message: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO messages (channel, sender, message) 
            VALUES (?, ?, ?);
            """,
            (channel, sender, message),
        )
        await db.commit()


async def bot_last_message(channel: str) -> str:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            SELECT message 
            FROM messages 
            WHERE channel = ? AND sender = ? and sent_at > DATETIME('now', '-30 seconds')
            ORDER BY id DESC;
            """,
            (channel, os.environ["BOT_NICK"]),
        ) as cursor:
            message = await cursor.fetchone()
            if message is None:
                return ""
            return message[0]


async def emote_count(channel: str, emote: str, *, ignore_bot = False) -> int:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            f"""
            SELECT message 
            FROM messages 
            WHERE channel = ? AND message LIKE ?
                {"AND sender != ?" if ignore_bot else ""};
            """,
            (channel, f"%{emote}%", os.environ["BOT_NICK"]) if ignore_bot else (channel, f"%{emote}%"),
        ) as cursor:
            count = 0
            for message in await cursor.fetchall():
                count += message[0].split().count(emote)
            return count


async def emote_counts(channel: str, emotes: list[str], *, nof_messages_counted = 1000, ignore_bot: bool = False) -> Counter[str]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            f"""
            SELECT message
            FROM messages
            WHERE channel = ?
                {"AND sender != ?" if ignore_bot else ""}
            ORDER BY id DESC
            LIMIT ?;
            """,
            (channel, os.environ["BOT_NICK"], nof_messages_counted) if ignore_bot else (channel, nof_messages_counted)
        ) as cursor:
            messages = await cursor.fetchall()
            emote_counts = Counter()
            for emote in emotes:
                count = 0
                for message in messages:
                    count += message[0].split().count(emote)
                emote_counts[emote] = count
            return emote_counts


def search_queries(
    user: Optional[str], 
    lt: Optional[int], 
    gt: Optional[int], 
    included: Optional[str], 
    excluded: Optional[str]
):
    return f"""
        {"AND sender = ?" if user else ""}
        {"AND LENGTH(message) < ?" if lt else ""}
        {"AND LENGTH(message) > ?" if gt else ""}
        {"AND message LIKE ?" if included else ""}
        {"AND message NOT LIKE ?" if excluded else ""}
        """


async def random_message(
    channel: str, 
    user: Optional[str], 
    *, 
    lt: Optional[int] = None, 
    gt: Optional[int] = None, 
    included: Optional[str] = None, 
    excluded: Optional[str] = None
) -> Optional[tuple[str, str, datetime]]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            f"""
            SELECT sender, message, sent_at
            FROM messages
            WHERE channel = ? 
                {search_queries(user, lt, gt, included, excluded)}
            ORDER BY RANDOM()
            LIMIT 1;
            """,
            (channel,) + tuple(arg for arg in (user, lt, gt, included, excluded) if arg is not None)
        ) as cursor:
            result = await cursor.fetchone()
            if result is None:
                return None
            return (result[0], result[1], datetime.fromisoformat(result[2]))


async def nofmessages(
    channel: str, 
    user: Optional[str], 
    *, 
    lt: Optional[int] = None, 
    gt: Optional[int] = None, 
    included: Optional[str] = None, 
    excluded: Optional[str] = None
) -> int:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            f"""
            SELECT COUNT(*) 
            FROM messages
            WHERE channel = ?
                {search_queries(user, lt, gt, included, excluded)};
            """,
            (channel,) + tuple(arg for arg in (user, lt, gt, included, excluded) if arg is not None)
        ) as cursor:
            count = await cursor.fetchone()
            return count[0] if count[0] else 0


async def lastseen(channel: str, user: str) -> Optional[tuple[str, datetime]]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            SELECT message, sent_at
            FROM messages 
            WHERE channel = ? AND sender = ?
            ORDER BY id DESC
            LIMIT 1;
            """,
            (channel, user)
        ) as cursor:
            seen = await cursor.fetchone()
            if seen is None:
                return None
            return (seen[0], datetime.fromisoformat(seen[1]))


async def stalk(user: str) -> Optional[tuple[str, str, datetime]]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            SELECT channel, message, sent_at
            FROM messages 
            WHERE sender = ?
            ORDER BY id DESC
            LIMIT 1;
            """,
            (user,)
        ) as cursor:
            seen = await cursor.fetchone()
            if seen is None:
                return None
            return (seen[0], seen[1], datetime.fromisoformat(seen[2]))
