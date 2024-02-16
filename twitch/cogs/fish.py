from datetime import datetime
import random
from typing import Optional

import twitchio
from twitchio.ext import commands

import database
from twitch import seventv
from twitchbot import Bot


class Fish(commands.Cog):
    COG_COOLDOWN = 5

    def __init__(self, bot: Bot) -> None:
        self.bot = bot


    def level_from_exp(self, experience: int) -> int:
        return int((experience / 50) ** 0.5) + 1


    @commands.cooldown(rate=1, per=1*60*60, bucket=commands.Bucket.user)
    @commands.command(aliases=("fishinge", "🐟"))
    async def fish(self, ctx: commands.Context):
        """You go fishing; number of fish you catch is based on luck, fishing level, and time since last fished"""
        current_time = datetime.utcnow()
        last_fished = await database.last_fished(ctx.author.id)
        seconds_ellapsed = (current_time - last_fished).seconds if last_fished else 1*60*60

        minutes, _ = divmod(seconds_ellapsed, 60)
        hours, _ = divmod(minutes, 60)

        exp_before = await database.fishing_exp(ctx.author.id)
        level_before = self.level_from_exp(exp_before)

        # Base count of 1-2 fish + random number based on current level + count based on hours since last fished
        total_fish_count = int(random.randint(1, 2) + (random.random() + 1) / 2 * ((level_before - 1) ** 0.6) + (hours ** 0.4 - 1))

        if total_fish_count < 1:
            await self.bot.message_queues.queue_command(ctx, "You suck at fishing...", reply=True)
            return

        channel = await ctx.channel.user()
        channel_emotes = [emote["name"] for emote in await seventv.channel_emotes(channel.id)]
        global_emotes = [emote["name"] for emote in await seventv.global_emotes()]
        channel_emotes.extend(global_emotes)

        most_used_emotes = await database.emote_counts(ctx.channel.name, channel_emotes)
        emotes_ordered = most_used_emotes.most_common(n = 5)

        fish_caught = random.choices(
            [(emote[0], i + 1) for i, emote in enumerate(emotes_ordered)], 
            cum_weights=[j + 1 for j in range(len(emotes_ordered))], 
            k=total_fish_count
        )
        total_exp_amount = int(sum([1 / index * 30 for _, index in fish_caught]))

        exp_after = exp_before + total_exp_amount
        level_after = self.level_from_exp(exp_after)
        level_up_notif = "" if level_before == level_after else f", LEVEL UP {level_before}->{level_after}!"
        
        await database.fish(ctx.author.id, ctx.author.name, total_fish_count, total_exp_amount)

        fish_caught_count = {}
        for name, _ in fish_caught:
            fish_caught_count[name] = fish_caught_count.get(name, 0) + 1

        caught = " | ".join([f"{name} - {count}" for name, count in fish_caught_count.items()])
        await self.bot.message_queues.queue_command(
            ctx, 
            f"You caught {total_fish_count} fish: {caught}, exp got: {total_exp_amount}{level_up_notif}", 
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
            f"_{target.name} has fished {count} fish, has {exp} exp, and is level {level}"
        )


def prepare(bot: commands.Bot):
    bot.add_cog(Fish(bot))
