import aiosqlite

from .db import db_path


__all__ = (
    "fortune",
)


async def fortune() -> str:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            SELECT fortune
            FROM fortunes 
            ORDER BY RANDOM()
            LIMIT 1;
            """,
        ) as cursor:
            result = await cursor.fetchone()
            if result is None:
                return None
            return result[0]