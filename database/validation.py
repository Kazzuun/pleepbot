from enum import Enum
from typing import Optional, Union

import aiosqlite

from .db import db_path


__all__ = (
    "is_admin",
    "is_banned",
    "ban",
    "optout",
    "optin",
    "has_opted_out",
    "blocked_words",
    "block_words",
    "unblock_words",
    "silent_pings",
    "mute_pings",
    "enable_pings"
)


class Roles(Enum):
    ADMIN = "admin"
    DEFAULT = "default"
    BANNED = "banned"


async def user_role(twitch_id: Union[str, int]) -> str:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            SELECT role
            FROM users 
            WHERE twitch_id = ?;
            """,
            (str(twitch_id),),
        ) as cursor:
            result = await cursor.fetchone()
            return Roles(result[0]) if result else Roles.DEFAULT


async def is_admin(twitch_id: Union[str, int]) -> bool:
    role = await user_role(twitch_id)
    return role == Roles.ADMIN


async def is_banned(twitch_id: Union[str, int]) -> bool:
    role = await user_role(twitch_id)
    return role == Roles.BANNED


async def ban(twitch_id: Union[str, int], username: str, notes: Optional[str]) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO users (twitch_id, username, role, notes)
            VALUES (?, ?, 'banned', ?);
            """,
            (str(twitch_id), username, notes),
        )
        await db.commit()


async def optout(twitch_id: Union[str, int], username: str, commands: list[str]) -> int:
    async with aiosqlite.connect(db_path) as db:
        async with db.executemany(
            """
            INSERT OR IGNORE INTO optouts (twitch_id, username, command)
            VALUES (?, ?, ?);
            """,
            [(str(twitch_id), username, command) for command in commands],
        ) as cursor:
            await db.commit()
            return cursor.rowcount


async def optin(twitch_id: Union[str, int], commands: list[str]) -> int:
    async with aiosqlite.connect(db_path) as db:
        async with db.executemany(
            """
            DELETE FROM optouts
            WHERE twitch_id = ? AND command = ?;
            """,
            [(str(twitch_id), command) for command in commands],
        ) as cursor:
            await db.commit()
            return cursor.rowcount


async def has_opted_out(user_or_id: Union[str, int], command: str, *, username: bool = False) -> bool:
    if username:
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                f"""
                SELECT twitch_id
                FROM optouts 
                WHERE command = ?
                    {"AND username = ?" if username else "AND twitch_id = ?"};
                """,
                (str(user_or_id), command),
            ) as cursor:
                return await cursor.fetchone() is not None


async def blocked_words() -> list[str]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            SELECT word
            FROM blocked_words;
            """
        ) as cursor:
            return [word[0] for word in await cursor.fetchall()]


async def block_words(words: list[str]) -> int:
    async with aiosqlite.connect(db_path) as db:
        async with db.executemany(
            """
            INSERT INTO blocked_words (word)
            VALUES (?);
            """,
            [(word,) for word in words]
        ) as cursor:
            await db.commit()
            return cursor.rowcount


async def unblock_words(words: list[str]) -> int:
    async with aiosqlite.connect(db_path) as db:
        async with db.executemany(
            """
            DELETE FROM blocked_words
            WHERE word = ?;
            """,
            [(word,) for word in words]
        ) as cursor:
            await db.commit()
            return cursor.rowcount


async def silent_pings(username: str) -> bool:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            SELECT no_pings
            FROM users
            WHERE username = ?;
            """,
            (username,)
        ) as cursor:
            result = await cursor.fetchone()
            return result is not None and result[0] == 1


async def mute_pings(twitch_id: Union[str, int], username: str) -> bool:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO users (twitch_id, username)
            VALUES (?, ?);
            """,
            (twitch_id, username)
        )
        async with db.execute(
            """
            UPDATE OR IGNORE users
            SET no_pings = 1
            WHERE twitch_id = ?;
            """,
            (twitch_id,)
        ) as cursor:
            await db.commit()
            return cursor.rowcount > 0


async def enable_pings(twitch_id: Union[str, int]) -> bool:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            UPDATE OR IGNORE users
            SET no_pings = 1
            WHERE twitch_id = ?;
            """,
            (twitch_id,)
        ) as cursor:
            await db.commit()
            return cursor.rowcount > 0

