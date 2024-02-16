import os
import sqlite3

import aiosqlite


__all__ = (
    "initialize_tables",
    "backup_database"
)


dir = os.path.realpath(os.path.dirname(__file__))
db_path = f"{dir}/database.db"
backup_db_path = f"{dir}/backup.db"


def initialize_tables() -> None:
    with sqlite3.connect(db_path) as db:
        with open(f"{dir}/schema.sql", "r") as file:
            db.executescript(file.read())
            db.commit()


async def backup_database() -> None:
    async with aiosqlite.connect(db_path) as db:
        async with aiosqlite.connect(backup_db_path) as backup_db:
            await db.backup(backup_db)
