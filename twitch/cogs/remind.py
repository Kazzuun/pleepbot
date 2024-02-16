from datetime import datetime, timedelta
import re
from typing import Optional

import twitchio
from twitchio.ext import commands

import database
from database import ReminderType
from twitchbot import Bot
from twitch import seventv


class Remind(commands.Cog):
    COG_COOLDOWN = 5

    def __init__(self, bot: Bot) -> None:
        self.bot = bot


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command(aliases=("notify",))
    async def remind(self, ctx: commands.Context, target: twitchio.PartialChatter, *args):
        """
        Sends a reminder to target; in specified amount of time 
        {prefix}remind <target> <message> in <time>, at a specific time 
        {prefix}remind <target> <message> at <unix timestamp>, 
        when they type next {prefix}remind <target> <message>
        """
        if len(args) == 0:
            return

        current_time = datetime.utcnow()

        if target.name in ("me", "myself"):
            target = ctx.author.name
        else:
            target = target.name

        in_position = -1
        for i, word in enumerate(args):
            if word == "in":
                in_position = i

        try:
            reminderType = ReminderType.REMIND
            if args[-2] == "at":
                message = " ".join(args[:-2])
                reminder_time = datetime.utcfromtimestamp(float(args[-1]))
            elif in_position != -1:
                message = " ".join(args[:in_position])
                time_args = [arg for arg in args[(in_position + 1) :] if arg != "and"]
                parsed_time_args = re.findall(
                    r"\d*\.\d+|\d+|\D+",
                    "".join([char for char in "".join(time_args) if char != ","]),
                )

                arg_length = len(parsed_time_args)
                if arg_length % 2 == 1:
                    raise Exception

                seconds = 0
                minutes = 0
                hours = 0
                days = 0
                weeks = 0

                for i in range(0, arg_length, 2):
                    multiplier = float(parsed_time_args[i])
                    unit = parsed_time_args[i + 1]
                    if unit in ("s", "sec", "secs", "second", "seconds"):
                        seconds += multiplier
                    elif unit in ("m", "min", "mins", "minute", "minutes"):
                        minutes += multiplier
                    elif unit in ("h", "hr", "hrs", "hour", "hours"):
                        hours += multiplier
                    elif unit in ("d", "day", "days"):
                        days += multiplier
                    elif unit in ("w", "week", "weeks"):
                        weeks += multiplier
                    elif unit in ("mon", "month", "months"):
                        days += multiplier * 30
                    elif unit in ("y", "year", "years"):
                        days += multiplier * 365
                    else:
                        raise Exception

                reminder_time = current_time + timedelta(
                    weeks=weeks,
                    days=days,
                    hours=hours,
                    minutes=minutes,
                    seconds=seconds,
                )
            else:
                raise Exception
        except:
            reminderType = ReminderType.NOTIFY
            message = " ".join(args)
            reminder_time = None

        min_time = current_time + timedelta(seconds=15)
        max_time = current_time + timedelta(days=3*365)
        if reminder_time and (min_time > reminder_time or max_time < reminder_time):
            await self.bot.message_queues.queue_command(
                ctx, 
                "Time is out of allowed bounds", 
                reply=True
            )
            return

        reminder_id = await database.set_reminder(
            ctx.channel.name, ctx.author.name, target, reminderType, message, reminder_time
        )

        if reminder_id is None:
            await self.bot.message_queues.queue_command(
                ctx,
                "Failed to set a reminder", 
                reply=True
            )
            return

        if reminderType == ReminderType.REMIND:
            if target == ctx.author.name:
                target = "you"
            else:
                target = "_" + target
            await self.bot.message_queues.queue_command(
                ctx,
                f"Reminding _{target} at {reminder_time.strftime('%d/%m/%Y, %H:%M:%S')} UTC (ID {reminder_id})", 
                reply=True
            )
        elif reminderType == ReminderType.NOTIFY:
            await self.bot.message_queues.queue_command(
                ctx,
                f"Sending a message to _{target} when they type next (ID {reminder_id})", 
                reply=True
            )


    @commands.cooldown(rate=1, per=60, bucket=commands.Bucket.member)
    @commands.command(aliases=("goodnight",))
    async def gn(self, ctx: commands.Context, *, message: Optional[str] = None):
        """{self.bot.nick} says goodnight to you and queues a goodmorning message to be sent when you type next"""
        await database.set_reminder(
            ctx.channel.name, ctx.author.name, ctx.author.name, ReminderType.GN, message
        )
        emote1 = await seventv.best_fitting_emote(
            await database.channel_id(ctx.channel.name), 
            lambda emote: any(choise in emote for choise in ("Pat", "Hug", "HUG", "Kiss", "KISS")),
            default="FeelsOkayMan"
        )
        emote2 = await seventv.best_fitting_emote(
            await database.channel_id(ctx.channel.name), 
            lambda emote: "Bed" in emote
        )
        await self.bot.message_queues.queue_command(
            ctx, f"Goodnight {ctx.author.name} {emote1} sleep well {emote2}", targets=(ctx.author.name,)
        )


    @commands.cooldown(rate=1, per=60, bucket=commands.Bucket.member)
    @commands.command()
    async def afk(self, ctx: commands.Context, *, message: Optional[str] = None):
        """You go afk"""
        await database.set_reminder(
            ctx.channel.name, ctx.author.name, ctx.author.name, ReminderType.AFK, message
        )
        await self.bot.message_queues.queue_command(
            ctx, f"_{ctx.author.name} is now afk"
        )


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command(aliases=("deleterem", "cancelrem", "canrem"))
    async def delrem(self, ctx: commands.Context, id: int):
        """Deletes a reminder you have set; {prefix}delrem <ID>"""
        if await database.is_admin(ctx.author.id):
            success = await database.cancel_reminder(id)
        else:
            success = await database.cancel_reminder_with_check(id, ctx.author.name)

        if success:
            emote = await seventv.best_fitting_emote(
                await database.channel_id(ctx.channel.name), 
                lambda emote: emote.lower() == "ok" or emote in ["Okayge", "Okayeg"], 
                default="FeelsOkayMan"
            )
            await self.bot.message_queues.queue_command(
                ctx, f"Reminder cancelled {emote}", reply=True
            )
        else:
            await self.bot.message_queues.queue_command(
                ctx, "Failed to cancel the reminder", reply=True
            )


    @commands.cooldown(rate=1, per=60, bucket=commands.Bucket.member)
    @commands.command(aliases=("cafk",))
    async def rafk(self, ctx: commands.Context):
        """Resumes your afk status"""
        success = await database.continue_afk(ctx.author.name, ctx.channel.name)
        if success:
            await self.bot.message_queues.queue_command(ctx, "Your afk status has been resumed", reply=True)
        else:
            await self.bot.message_queues.queue_command(ctx, "Couldn't resume your afk status", reply=True)


def prepare(bot: commands.Bot):
    bot.add_cog(Remind(bot))
