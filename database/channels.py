import sqlite3

import aiosqlite

from .db import db_path


__all__ = (
    "initial_channels",
    "join_channels",
    "part_channels",
    "join_channels_log_only",
    "channel_is_log_only",
    "channel_id"
)


def initial_channels() -> list[str]:
    with sqlite3.connect(db_path) as db:
        cursor = db.execute(
            """
            SELECT channel
            FROM channels;
            """
        )
        channels = cursor.fetchall()
        return [channel[0] for channel in channels]


async def join_channels(channels: list[tuple[str, str]]) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.executemany(
            """
            INSERT OR REPLACE INTO channels (twitch_id, channel, log_only)
            VALUES (?, ?, 0);
            """,
            channels
        )
        await db.commit()


async def part_channels(channels: list[str]) -> None:
    async with aiosqlite.connect(db_path) as db:
        async with db.executemany(
            """
            DELETE FROM channels
            WHERE channel = ?;
            """,
           [(channel,) for channel in channels]
        ) as cursor:
            await db.commit()


async def join_channels_log_only(channels: list[tuple[str, str]]) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.executemany(
            """
            INSERT OR REPLACE INTO channels (twitch_id, channel, log_only)
            VALUES (?, ?, 1);
            """,
            channels
        )
        await db.commit()


async def channel_is_log_only(channel: str) -> bool:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            SELECT channel
            FROM channels
            WHERE channel = ? AND log_only = 1;
            """,
            (channel,)
        ) as cursor:
            result = await cursor.fetchone()
            return result is not None


async def channel_id(channel: str) -> str:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            SELECT twitch_id
            FROM channels
            WHERE channel = ?;
            """,
            (channel,)
        ) as cursor:
            result = await cursor.fetchone()
            return result[0]
