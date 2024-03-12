import random
from typing import Optional

import twitchio
from twitchio.ext import commands

import database
from twitchbot import Bot
from twitch import seventv


class SevenTV(commands.Cog):
    COG_COOLDOWN = 3

    def __init__(self, bot: Bot) -> None:
        self.bot = bot


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def emote(self, ctx: commands.Context, emote_id: str):
        """Sends the name of the emote matching the id; {prefix}emote <emote id>"""
        if not seventv.is_valid_emoteid(emote_id):
            await self.bot.message_queues.queue_command(ctx, "Invalid emote id", reply=True)
            return
        emote_info = await seventv.emote_from_id(emote_id)
        await self.bot.message_queues.queue_command(ctx, f"{emote_info['name']}")


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def emotes(self, ctx: commands.Context, target: twitchio.PartialChatter):
        """Sends a link to a page that shows all emotes of the channel"""
        await self.bot.message_queues.queue_command(ctx, f"https://emotes.raccatta.cc/twitch/{target.name.lower()}")


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def topemotes(self, ctx: commands.Context, *args):
        """Shows top 10 emotes from the past 1000 messages"""
        channel_id = await database.channel_id(ctx.channel.name)
        emotes = await seventv.channel_emotes(channel_id)
        global_emotes = await seventv.global_emotes()
        emotes.extend(global_emotes)

        ignore_bot = not ("all" in args or "-a" in args)
        emote_count = await database.emote_counts(ctx.channel.name, [emote["name"] for emote in emotes], ignore_bot=ignore_bot)
        top_10 = emote_count.most_common(10)
        await self.bot.message_queues.queue_command(ctx, " | ".join([f"{i + 1}. {emote[0]} - {emote[1]}" for i, emote in enumerate(top_10)]))


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command(aliases=("randomemote", "randemote"))
    async def re(self, ctx: commands.Context, count: Optional[int] = 1):
        """Sends random emotes(s) from the channel; {prefix}re <count>"""
        count = min(max(count, 1), 20)
        channel_id = await database.channel_id(ctx.channel.name)
        emotes = await seventv.channel_emotes(channel_id)
        if len(emotes) == 0:
            await self.bot.message_queues.queue_command(ctx, "Current channel doesn't have any 7tv emotes", reply=True)
            return
        emote_names = [emote["name"] for emote in emotes]
        await self.bot.message_queues.queue_command(ctx, " ".join(random.choices(emote_names, k=count)))


    @commands.cooldown(rate=1, per=5, bucket=commands.Bucket.member)
    @commands.command()
    async def search(self, ctx: commands.Context, emote_name: str, *args):
        """
        Searches for the given 7tv emote; filters can be specified: -e for exact match, 
        -c for case sensitive, -t to ignore tags, -z for zero width emotes 
        (as of 14/02/2024 filters in the 7tv api seem to be broken and may not work); 
        {prefix}search <emote> <filters>
        """
        exact_match = "-e" in args
        case_sensitive = "-c" in args
        ignore_tags = "-i" in args or "-t" in args
        zero_width = "-z" in args

        emotes = await seventv.search_emote_by_name(
            emote_name,
            exact_match=exact_match,
            case_sensitive=case_sensitive,
            ignore_tags=ignore_tags,
            zero_width=zero_width,
        )
        max_emotes = 6
        links = [f"{emote_info['name']} - 7tv.app/emotes/{emote_info['id']}" for emote_info in emotes][:max_emotes]
        await self.bot.message_queues.queue_command(ctx, " | ".join(links))


def prepare(bot: commands.Bot):
    bot.add_cog(SevenTV(bot))
