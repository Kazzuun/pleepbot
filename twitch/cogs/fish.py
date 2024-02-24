from datetime import datetime, timedelta
import random
from typing import Optional

import twitchio
from twitchio.ext import commands

import database
from twitch import seventv
from twitchbot import Bot


class Fish(commands.Cog):
    COG_COOLDOWN = 3

    def __init__(self, bot: Bot) -> None:
        self.bot = bot


    def level_from_exp(self, experience: int) -> int:
        return int((experience / 50) ** 0.5) + 1


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.user)
    @commands.command(aliases=("fishing", "fishinge", "fishingtime", "fishh", "🐟", "🎣"))
    async def fish(self, ctx: commands.Context, *args):
        """
        You go fishing; number of fish you catch is based on luck, fishing level, and time since last fished;
        set a reminder to remind you to fish in 1 hour with -r flag
        """
        cooldown_period = 3600
        current_time = datetime.utcnow()
        last_fished = await database.last_fished(ctx.author.id)
        seconds_ellapsed = (current_time - last_fished).seconds if last_fished else cooldown_period

        # Manage cooldown
        if seconds_ellapsed < cooldown_period:
            await self.bot.message_queues.queue_command(
                ctx, 
                f"You can go fishing again in {cooldown_period-seconds_ellapsed}s", 
                reply=True
            )
            return

        hours = seconds_ellapsed / 3600

        exp_before = await database.fishing_exp(ctx.author.id)
        level_before = self.level_from_exp(exp_before)

        # Base count of 1 or 2 fish + random number based on current level + count based on hours since last fished
        total_fish_count = int(
            random.randint(1, 2) + 
            (random.random() + 1) / 2 * ((level_before - 1) ** 0.6) + 
            (hours ** 0.4 - cooldown_period / 3600)
        )

        # Not reachable but in case of changes
        if total_fish_count < 1:
            await self.bot.message_queues.queue_command(ctx, "You suck at fishing...", reply=True)
            return

        channel_id = await database.channel_id(ctx.channel.name)
        channel_emotes = [emote["name"] for emote in await seventv.channel_emotes(channel_id)]
        global_emotes = [emote["name"] for emote in await seventv.global_emotes()]
        channel_emotes.extend(global_emotes)

        most_used_emotes = await database.emote_counts(ctx.channel.name, channel_emotes, ignore_bot=True)
        top_n = 10
        emotes_ordered = most_used_emotes.most_common(top_n)

        fish_caught = random.choices(
            # The most common has the smallest index
            [(i, emote[0]) for i, emote in enumerate(emotes_ordered)],
            # The most common has the highest weight
            weights=[1 / j for j in range(1, top_n + 1)], 
            k=total_fish_count
        )
        # Sort caught fish by its rarity (index), most common first
        fish_caught.sort()

        # The most common has the highest index getting the least exp
        total_exp_amount = int(sum([60 / (top_n - index) for index, _ in fish_caught]))

        exp_after = exp_before + total_exp_amount
        level_after = self.level_from_exp(exp_after)
        level_up_notif = "" if level_before == level_after else f", LEVEL UP {level_before}->{level_after}!"

        await database.fish(ctx.author.id, ctx.author.name, total_fish_count, total_exp_amount)

        if "-r" in args:
            rem_id = await database.set_reminder(
                ctx.channel.name, 
                ctx.author.name, 
                ctx.author.name, 
                database.ReminderType.REMIND,
                f"{self.bot.prefixes[0]}fish",
                datetime.utcnow() + timedelta(hours=1)
            )
            reminder_msg = f" | Reminding you to fish in 1 hour (ID {rem_id})"
        else:
            reminder_msg = ""

        fish_caught_count = {}
        for _, name in fish_caught:
            fish_caught_count[name] = fish_caught_count.get(name, 0) + 1

        caught = " | ".join([f"{name} - {count}" for name, count in fish_caught_count.items()])
        await self.bot.message_queues.queue_command(
            ctx, 
            f"You caught {total_fish_count} fish: {caught}, exp got: {total_exp_amount}{level_up_notif}{reminder_msg}", 
            reply=True
        )


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command(aliases=("fs",))
    async def fishstats(self, ctx: commands.Context, target: Optional[twitchio.User]):
        """
        Shows the number of fish you have caught; can be used with a target:
        {prefix}fishcount <target>
        """
        target = target if target else ctx.author
        count = await database.fish_count(target.id)
        exp = await database.fishing_exp(target.id)
        level = self.level_from_exp(exp)
        await self.bot.message_queues.queue_command(
            ctx, 
            f"_{target.name} has caught {count} fish, has {exp} exp, and is level {level}"
        )


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command(aliases=("topfish", "toplevel"))
    async def topexp(self, ctx: commands.Context):
        """Shows the fishing stats of the top 5 people ordered by exp"""
        top_exp = await database.top_fishing_exp(5)
        user_info = []
        for i, top_fisher in enumerate(top_exp):
            username, exp, fish_count = top_fisher
            level = self.level_from_exp(exp)
            user_info.append(f"{i+1}. _{username} - level {level}, {exp} exp, {fish_count} caught")
        await self.bot.message_queues.queue_command(ctx, " | ".join(user_info))


def prepare(bot: commands.Bot):
    bot.add_cog(Fish(bot))
