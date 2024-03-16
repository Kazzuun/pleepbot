from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Union
from enum import Enum

import aiosqlite

from .db import db_path


__all__ = (
    "EquipmentType",
    "FishingEquipmentCatalogue",
    "fish",
    "fish_count",
    "fishing_exp",
    "last_fished",
    "top_fishing_exp",
    "owned_fishing_equipment",
    "buy_fishing_equipment"
)


class EquipmentType(Enum):
    FISHFLAT = 1
    FISHMULTI = 2
    EXPMULTI = 3
    AFKMULTI = 4
    COOLDOWNFLAT = 5
    NORNG = 6


@dataclass
class FishingEquipment:
    id: int
    name: str
    cost: int
    level_req: int
    effect: Optional[int]
    effect_disc: str
    equipment_type: EquipmentType


class FishingEquipmentCatalogue:
    def __init__(self) -> None:
        self._equipment = [
            FishingEquipment(1, "fishing socks", 1500, 10, 0.15, "+15% exp", EquipmentType.EXPMULTI),
            FishingEquipment(2, "canned worms", 2500, 10, 1, "+1 fish", EquipmentType.FISHFLAT),
            FishingEquipment(3, "fishing rod holder", 5000, 20, 1.0, "+100% afk fishing", EquipmentType.AFKMULTI),
            FishingEquipment(4, "unbreakable fishing line", 7500, 20, None, "max number of fish every time", EquipmentType.NORNG),
            FishingEquipment(5, "alarm clock", 10000, 30, 600, "-10 min cooldown", EquipmentType.COOLDOWNFLAT),
            FishingEquipment(6, "exquisite fish food", 15000, 30, 3, "+3 fish", EquipmentType.FISHFLAT),
            FishingEquipment(7, "cool fishing hat", 15000, 30, 0.35, "+35% exp", EquipmentType.EXPMULTI),
            FishingEquipment(8, "a dog", 20000, 40, 600, "-10 min cooldown", EquipmentType.COOLDOWNFLAT),
            FishingEquipment(9, "fishing boat", 30000, 40, 0.3, "+30% fish", EquipmentType.FISHMULTI),
            FishingEquipment(10, "a cat", 30000, 50, 600, "-10 min cooldown", EquipmentType.COOLDOWNFLAT),
        ]

    def item_by_id(self, id: int) -> Optional[FishingEquipment]:
        target_item = [item for item in self._equipment if item.id == id]
        if len(target_item) > 0:
            return target_item[0]


    def equipment_owned(self, owned_equipment_num: int) -> list[FishingEquipment]:
        owned = []
        for item in self._equipment:
            if owned_equipment_num & (1 << (item.id - 1)) != 0:
                owned.append(item)
        return owned


    def equipment_not_owned(self, owned_equipment_num: int) -> list[FishingEquipment]:
        not_owned = []
        for item in self._equipment:
            if owned_equipment_num & (1 << (item.id - 1)) == 0:
                not_owned.append(item)
        return not_owned


    def all_equipment(self) -> list[FishingEquipment]:
        return self._equipment



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


async def top_fishing_exp(top_n: int, fish_count: bool = False) -> list[tuple[str, int, int]]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            f"""
            SELECT username, exp, fish_count
            FROM fish
            ORDER BY {"fish_count" if fish_count else "exp"} DESC
            LIMIT ?;
            """,
            (top_n,)
        ) as cursor:
            return list(await cursor.fetchall())


async def owned_fishing_equipment(twitch_id: Union[str, int]) -> int:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            SELECT equipment
            FROM fish
            WHERE twitch_id = ?;
            """,
            (twitch_id,)
        ) as cursor:
            owned = await cursor.fetchone()
            return owned[0] if owned else 0


async def buy_fishing_equipment(twitch_id: Union[str, int], equipment_id: int, cost: int) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            UPDATE fish
            SET equipment = equipment + ?, exp = exp - ?
            WHERE twitch_id = ?;
            """,
            (1 << (equipment_id-1), cost, twitch_id)
        )
        await db.commit()
