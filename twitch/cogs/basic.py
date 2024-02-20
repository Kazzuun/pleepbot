import numpy
import random
from typing import Optional

import twitchio
from twitchio.ext import commands

import database
from twitch import seventv
from twitchbot import Bot


class Basic(commands.Cog):
    COG_COOLDOWN = 1

    def __init__(self, bot: Bot) -> None:
        self.bot = bot


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def pleep(self, ctx: commands.Context):
        """It's just pleep"""
        await self.bot.message_queues.queue_command(ctx, "pleep")


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command(aliases=("chatters",))
    async def lurkers(self, ctx: commands.Context):
        """A number of users connected to the chat fetched from cache"""
        emote = await seventv.best_fitting_emote(
            await database.channel_id(ctx.channel.name), 
            lambda emote: emote.lower() in ("uuh", "urm", "erm", "orm"),
            default="Stare"
        )
        await self.bot.message_queues.queue_command(ctx, f"{len(ctx.chatters)} lurkers {emote}")


    @commands.cooldown(rate=1, per=3*60*60, bucket=commands.Bucket.user)
    @commands.command(aliases=("cookie", "🍪", "🥠"))
    async def fortune(self, ctx: commands.Context):
        """Tells a random fortune"""
        fortune = await database.fortune()
        if fortune is None:
            await self.bot.message_queues.queue_command(ctx, "There are no fortunes to tell", reply=True)
            return
        await self.bot.message_queues.queue_command(ctx, fortune, reply=True)


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command(aliases=("coin",))
    async def flip(self, ctx: commands.Context):
        """Flips a 50/50 coin heads or tails (yes or no)"""
        await self.bot.message_queues.queue_command(ctx, random.choice(["Heads (Yes)", "Tails (No)"]), reply=True)


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command(aliases=("%",))
    async def chance(self, ctx: commands.Context):
        """A random percentage between 0% and 100%"""
        await self.bot.message_queues.queue_command(ctx, f"{random.randint(0, 100)}%", reply=True)


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def choose(self, ctx: commands.Context, *args):
        """Picks one of the given choises; {prefix}choose <choise1> <choise1> <choise1>..."""
        if len(args) == 0:
            return
        await self.bot.message_queues.queue_command(ctx, random.choice(args))


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def shuffle(self, ctx: commands.Context, word: str):
        """Shuffles the given word randomly; {prefix}shuffle <word>"""
        letters = list(word)
        random.shuffle(letters)
        await self.bot.message_queues.queue_command(ctx, "".join(letters))


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def iq(self, ctx: commands.Context, target: Optional[twitchio.PartialChatter]):
        """
        A random number from a normal distribution with standard deviation of 15 
        and mean of 100; can be used with a target: {prefix}iq <target>
        """
        target = target.name if target else ctx.author.name
        await self.bot.message_queues.queue_command(ctx, f"_{target}'s IQ is {round(numpy.random.normal(100, 15))}")


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def slap(self, ctx: commands.Context, target: Optional[twitchio.PartialChatter]):
        """Slaps the given target: {prefix}slap <target>"""
        target = ctx.author.name if target is None or target.name == self.bot.nick else target.name
        await self.bot.message_queues.queue_command(ctx, f"/me slaps {target} around with a large trout", targets=(target,))


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def tuck(self, ctx: commands.Context, target: Optional[twitchio.PartialChatter], emote: Optional[str]):
        """Tucks the target to bed; {prefix}tuck <target> <optional emote>"""
        target = target.name if target else "themselves"
        channel_id = await database.channel_id(ctx.channel.name)
        emotes = await seventv.channel_emotes(channel_id)
        if emote is None or emote not in [channel_emote["name"] for channel_emote in emotes]:
            emote = "FeelsOkayMan"
        await self.bot.message_queues.queue_command(ctx, f"_{ctx.author.name} tucked {target} to bed {emote} 👉 🛏", targets=(target,))


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def hug(self, ctx: commands.Context, target: Optional[twitchio.PartialChatter]):
        """Hugs the target; {prefix}hug <target>"""
        target = target.name if target else "themselves"

        emote = await seventv.best_fitting_emote(
            await database.channel_id(ctx.channel.name),
            lambda emote: "Hug" in emote or "HUG" in emote or "hugg" in emote
        )
        await self.bot.message_queues.queue_command(ctx, f"_{ctx.author.name} hugged {target} {emote}", targets=(target,))


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def roll(self, ctx: commands.Context, *rolls):
        """
        Rolls dice: {prefix}roll for default 20 sided roll; 
        {prefix}roll <number of rolls>d<sides on die>...
        """
        rolled = []
        for roll in rolls:
            try:
                counts = roll.split("d")
                if len(counts) == 2:
                    mult = int(counts[0]) if counts[0] else 1
                    number = int(counts[1])

                    if mult < 1 or number < 1 or mult > 1_000 or number > 1_000_000:
                        break

                    for _ in range(mult):
                        rolled.append(random.randint(1, number))
                else:
                    break
            except ValueError:
                break

        default_roll = 20
        username = ctx.author.name

        if len(rolled) == 0:
            number = random.randint(1, default_roll)
            message = f"_{username} rolled {number} (1-{default_roll})"
        elif len(rolled) == 1:
            message = f"_{username} rolled {rolled[0]} (1-{rolls[0].split('d')[1]})"
        elif len(rolled) > 20:
            message = f"_{username} rolled total: {sum(rolled)}"
        else:
            message = f"_{username} rolled {', '.join(map(str, rolled))} | total: {sum(rolled)}"
        await self.bot.message_queues.queue_command(ctx, message)


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def fill(self, ctx: commands.Context, *words):
        """Sends a message randomly filled with the given words"""
        if len(words) == 0:
            return
        max_length = 350
        message = ""
        word = random.choice(words)
        while len(message) + len(word) < max_length:
            message += f"{word} "
            word = random.choice(words)
        if not message:
            return
        await self.bot.message_queues.queue_command(ctx, message, targets=words)


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def repeat(self, ctx: commands.Context, count: int, *words):
        """Repeats a given message specified number of times; {prefix}repeat <count> <message>"""
        if len(words) == 0 or count < 1:
            return
        message = " ".join(words)
        max_total_length = 350
        max_count = max_total_length // len(message)
        count = min(count, max_count)
        await self.bot.message_queues.queue_command(ctx, f"{message} " * count, targets=words)


def prepare(bot: commands.Bot):
    bot.add_cog(Basic(bot))
