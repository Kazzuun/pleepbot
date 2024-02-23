from datetime import datetime
from typing import Optional, Union

import aiosqlite

from .db import db_path


__all__ = (
    "fish",
    "fish_count",
    "fishing_exp",
    "last_fished",
    "top_fishing_exp"
)


async def fish(twitch_id: Union[str, int], username: str, fish_count: int, exp_amount: int) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO fish (twitch_id, username)
            VALUES (?, ?);
            """,
            (twitch_id, username)
        )
        await db.execute(
            """
            UPDATE fish
            SET fish_count = fish_count + ?, exp = exp + ?, last_fished = DATETIME()
            WHERE twitch_id = ?;
            """,
            (fish_count, exp_amount, twitch_id)
        )
        await db.commit()


async def last_fished(twitch_id: Union[str, int]) -> Optional[datetime]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            SELECT last_fished
            FROM fish
            WHERE twitch_id = ?;
            """,
            (twitch_id,)
        ) as cursor:
            last_fished = await cursor.fetchone()
            if last_fished is None:
                return None
            return datetime.fromisoformat(last_fished[0])


async def fish_count(twitch_id: Union[str, int]) -> int:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            SELECT fish_count
            FROM fish
            WHERE twitch_id = ?;
            """,
            (twitch_id,)
        ) as cursor:
            count = await cursor.fetchone()
            return count[0] if count else 0


async def fishing_exp(twitch_id: Union[str, int]) -> int:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            SELECT exp
            FROM fish
            WHERE twitch_id = ?;
            """,
            (twitch_id,)
        ) as cursor:
            exp = await cursor.fetchone()
            return exp[0] if exp else 0


async def top_fishing_exp(top_n: int) -> list[tuple[str, int, int]]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            SELECT username, exp, fish_count
            FROM fish
            ORDER BY exp DESC
            LIMIT ?;
            """,
            (top_n,)
        ) as cursor:
            return list(await cursor.fetchall())
