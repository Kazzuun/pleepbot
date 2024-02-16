from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from dataclasses import dataclass

import aiosqlite

from .db import db_path
from .channels import channel_id
from twitch import seventv


__all__ = (
    "ReminderType",
    "Reminder",
    "set_reminder",
    "set_reminder_as_sent",
    "sendable_reminders",
    "sendable_notifications",
    "cancel_reminder",
    "cancel_reminder_with_check",
    "cancel_all_reminders",
    "continue_afk"
)


class ReminderType(Enum):
    REMIND = "remind"
    NOTIFY = "notify"
    GN = "gn"
    AFK = "afk"


@dataclass
class Reminder:
    id: int
    channel: str
    sender: str
    target: str
    reminder_type: ReminderType
    message: str
    created_at: datetime
    scheduled_at: Optional[datetime]

    def __post_init__(self) -> None:
        self.time_ellapsed: timedelta = datetime.utcnow() - self.created_at
        self.time_ellapsed_str: str = str(self.time_ellapsed).split(".")[0]

    async def formatted_message(self) -> str:
        if self.reminderType == ReminderType.GN:
            if self.time_ellapsed < timedelta(minutes=15):
                message = "Go back to bed"
            elif self.time_ellapsed < timedelta(hours=3):
                message = "Hope you had a nice nap"
            elif self.time_ellapsed > timedelta(days=1):
                message = "Hope you had a nice nap"
            elif self.time_ellapsed > timedelta(hours=20):
                message = "Good evening"
            else:
                message = "Good morning"
            emote = await seventv.best_fitting_emote(
                await channel_id(self.channel), 
                lambda emote: any(choise in emote for choise in ("Pat", "Hug", "HUG", "Kiss", "KISS")),
                default="FeelsOkayMan"
            )
            message = f"{message} _{self.target} {emote} ({self.time_ellapsed_str})"
            return message

        elif self.reminderType == ReminderType.AFK:
            emote = await seventv.best_fitting_emote(
                await channel_id(self.channel),
                lambda emote: ":d" in emote.lower() or "Happy" in emote or emote in ("happy", "YAAAY"),
                default="peepoHappy"
            )
            if self.message == None:
                return f"Welcome back _{self.sender} {emote} ({self.time_ellapsed_str})"
            else:
                length_limit = 300
                if len(self.message) > length_limit:
                    self.message = self.message[:length_limit] + " ..."
                return f"Welcome back _{self.sender} {emote} - {self.message} ({self.time_ellapsed_str})"

        else:
            if not self.message:
                self.message = "(no message)"

            if self.sender == self.target:
                self.sender = "yourself"
            else:
                self.sender = f"_{self.sender}"

            if self.reminderType == ReminderType.REMIND:
                remind_type = "reminder"
            else:
                remind_type = "message"

            return f"@{self.target}, {remind_type} from {self.sender} ({self.time_ellapsed_str} ago): {self.message}"



async def set_reminder(
    channel: str,
    sender: str,
    target: str,
    reminder_type: ReminderType,
    message: str,
    scheduled_at: Optional[datetime] = None,
) -> Optional[int]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            f"""
            INSERT INTO reminders (channel, sender, target, type, message, scheduled_at)
            SELECT ?, ?, ?, ?, ?, ?
            WHERE (
                SELECT COUNT(*)
                FROM reminders 
                WHERE target = ? AND scheduled_at is NULL AND sent = 0 AND cancelled = 0
            ) < 15 AND (
                SELECT COUNT(*) 
                FROM reminders 
                WHERE target = ? AND channel = ? AND (type = '{reminder_type.AFK.value}' OR type = '{reminder_type.GN.value}') AND sent = 0 AND cancelled = 0
            ) < 1;
            """,
            (channel, sender, target, reminder_type.value, message, scheduled_at, 
             target, 
             target, channel)
        ) as cursor:
            await db.commit()
            return cursor.lastrowid


async def set_reminder_as_sent(id: int) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            UPDATE reminders
            SET sent = 1, processed_at = DATETIME()
            WHERE id = ?;
            """,
            (id,),
        )
        await db.commit()


async def sendable_reminders() -> list[Reminder]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            SELECT id, channel, sender, target, type, message, created_at, scheduled_at 
            FROM reminders 
            WHERE scheduled_at IS NOT NULL AND scheduled_at < DATETIME() AND sent = 0 AND cancelled = 0;
            """
        ) as cursor:
            return [
                Reminder(
                    notif[0],
                    notif[1],
                    notif[2],
                    notif[3],
                    ReminderType(notif[4]),
                    notif[5],
                    datetime.fromisoformat(notif[6]),
                    datetime.fromisoformat(notif[7]),
                )
                for notif in await cursor.fetchall()
            ]


async def sendable_notifications(channel: str, target: str) -> list[Reminder]:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            f"""
            SELECT id, channel, sender, target, type, message, created_at, scheduled_at
            FROM reminders
            WHERE target = ? 
                AND scheduled_at IS NULL
                AND created_at < DATETIME('now', '-5 seconds')
                AND sent = 0 
                AND cancelled = 0 
                AND ((type != '{ReminderType.NOTIFY.value}' AND channel = ?) OR type = '{ReminderType.NOTIFY.value}');
            """,
            (target, channel),
        ) as cursor:
            return [
                Reminder(
                    notif[0],
                    notif[1],
                    notif[2],
                    notif[3],
                    ReminderType(notif[4]),
                    notif[5],
                    datetime.fromisoformat(notif[6]),
                    notif[7],
                )
                for notif in await cursor.fetchall()
            ]


async def cancel_reminder(id: int) -> bool:
    async with aiosqlite.connect(db_path) as db:
        async with  db.execute(
            """
            UPDATE reminders
            SET cancelled = 1, processed_at = DATETIME()
            WHERE id = ? AND sent = 0 AND cancelled = 0;
            """,
            (id,)
        ) as cursor:
            await db.commit()
            return cursor.rowcount > 0


async def cancel_reminder_with_check(id: int, sender: str) -> bool:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            """
            UPDATE reminders
            SET cancelled = 1, processed_at = DATETIME()
            WHERE id = ? AND sender = ? AND sent = 0;
            """,
            (id, sender)
        ) as cursor:
            await db.commit()
            return cursor.rowcount > 0


async def cancel_all_reminders(target: str) -> bool:
    async with aiosqlite.connect(db_path) as db:
        async with  db.execute(
            """
            UPDATE reminders
            SET cancelled = 1, processed_at = DATETIME()
            WHERE sent = 0 AND cancelled = 0 AND (sender = ? OR target = ?);
            """,
            (target, target)
        ) as cursor:
            await db.commit()
            return cursor.rowcount > 0


async def continue_afk(sender: str, channel: str) -> bool:
    async with aiosqlite.connect(db_path) as db:
        async with db.execute(
            f"""
            UPDATE reminders
            SET sent = 0, processed_at = NULL
            WHERE id = (
                SELECT id 
                FROM reminders
                WHERE sender = ? 
                    AND channel = ? 
                    AND processed_at > DATETIME('now', '-5 minutes') 
                    AND (type = '{ReminderType.AFK.value}' OR type = '{ReminderType.GN.value}')
                ORDER BY processed_at DESC
                LIMIT 1
            );
            """,
            (sender, channel),
        ) as cursor:
            await db.commit()
            return cursor.rowcount > 0

