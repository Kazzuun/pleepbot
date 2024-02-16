import asyncio

from twitchio.ext import commands

import database
from twitchbot import Bot


class Moderator(commands.Cog):
    COG_COOLDOWN = 15
    
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return ctx.author.is_mod or ctx.author.is_vip or await database.is_admin(ctx.author.id)


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def pyramid(self, ctx: commands.Context, size: int, *words):
        f"""Makes a pyramid of given size with given message; {self.bot.prefixes[0]}pyramid <size> <message>"""
        if len(words) == 0:
            return
        message = " ".join(words)
        max_size = 15 if ctx._bot_is_mod() else 5
        size = min(max(size, 2), min(350 // len(message), max_size))
        for i in range(1, size + 1):
            await self.bot.message_queues.queue_command(ctx, f"{message} " * i, targets=words)
        for j in range(size - 1, 0, -1):
            await self.bot.message_queues.queue_command(ctx, f"{message} " * j, targets=words)


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def countdown(self, ctx: commands.Context, start: int, interval: int = 1):
        f"""
        Counts down to 1 from given starting point (min 3, max 10); 
        waits a specified number of seconds between counts (min 1, max 10);
        {self.bot.prefixes[0]}countdown <start> <interval>
        """
        start = max(min(start, 10), 3)
        interval = max(min(interval, 10), 1)
        for i in range(start, 0, -1):
            await asyncio.sleep(interval)
            await self.bot.message_queues.queue_command(ctx, f"{i}")


def prepare(bot: commands.Bot):
    bot.add_cog(Moderator(bot))