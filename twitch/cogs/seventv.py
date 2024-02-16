import os
import random
from typing import Optional

from dotenv import load_dotenv; load_dotenv()
import twitchio
from twitchio.ext import commands

import database
from twitchbot import Bot
from twitch import seventv
from twitch.exceptions import SevenTVException


class SevenTV(commands.Cog):
    COG_COOLDOWN = 5

    def __init__(self, bot: Bot) -> None:
        self.bot = bot


    async def cog_check(self, ctx: commands.Context) -> bool:
        ctx.channel_id = await database.channel_id(ctx.channel.name)

        if ctx.command.name not in ("add", "remove", "rename", "yoink"):
            return True

        editors = await seventv.get_editors(ctx.channel_id)

        bot_seventv_login = os.environ['SEVEN_TV_USERNAME']
        bot_is_editor = bot_seventv_login in editors or bot_seventv_login == ctx.channel.name
        if not bot_is_editor:
            raise SevenTVException(f"_{bot_seventv_login} is not an editor of this channel")

        sender_is_editor = ctx.author.name in editors or ctx.author.is_broadcaster
        if not sender_is_editor:
            raise SevenTVException(f"_{ctx.author.name} is not an editor of this channel")

        return True


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def emote(self, ctx: commands.Context, emote_id: str):
        """Sends the name of the emote matching the id; ?emote <emote id>"""
        if not seventv.is_valid_emoteid(emote_id):
            await self.bot.message_queues.queue_command(ctx, "Invalid emote id", reply=True)
            return
        emote_info = await seventv.emote_from_id(emote_id)
        await self.bot.message_queues.queue_command(ctx, f"{emote_info['name']}")


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def emotes(self, ctx: commands.Context, target: twitchio.PartialChatter):
        """Sends a link to a page that shows all emotes of the channel"""
        await self.bot.message_queues.queue_command(ctx, f"https://emotes.raccatta.cc/twitch/{target.name}")


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command(aliases=("randomemote", "randemote"))
    async def re(self, ctx: commands.Context, count: int):
        """Sends random emotes(s) from the channel; ?re <count>"""
        count = min(max(count, 1), 20)
        emotes = await seventv.channel_emotes(ctx.channel_id)
        if len(emotes) == 0:
            await self.bot.message_queues.queue_command(ctx, "Current channel doesn't have any 7tv emotes", reply=True)
            return
        emote_names = [emote["name"] for emote in emotes]
        await self.bot.message_queues.queue_command(ctx, " ".join(random.choices(emote_names, k=count)))


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def search(self, ctx: commands.Context, emote_name: str, *args):
        """
        Searches for the given 7tv emote; filters can be specified: -e for exact match, 
        -c for case sensitive, -t to ignore tags, -z for zero width emotes 
        (as of 14/02/2024 filters in the 7tv api seem to be broken and may not work); 
        ?search <emote> <filters>
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


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def add(self, ctx: commands.Context, emote: str, alias: Optional[str], *args):
        """
        Adds the given 7tv emote to the channel; emote can be specified with its name
        or id, if a name is given, a search is done to find it (see ?help search
        for more info); an alias can be given to the emote; 
        ?add <emote name or id> <optional alias> <search filters>
        """
        if alias and alias.startswith("-"):
            args = args + (alias,)
            alias = None

        if seventv.is_valid_emoteid(emote):
            emote_id = emote
        else:
            exact_match = "-e" in args
            case_sensitive = "-c" in args
            ignore_tags = "-i" in args or "-t" in args
            zero_width = "-z" in args

            emotes = await seventv.search_emote_by_name(
                emote,
                exact_match=exact_match,
                case_sensitive=case_sensitive,
                ignore_tags=ignore_tags,
                zero_width=zero_width,
            )
            emote_id = emotes[0]['id']

        added_emote = await seventv.add_emote(ctx.channel_id, emote_id, alias)
        await self.bot.message_queues.queue_command(ctx, f"Added emote {added_emote}")


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def remove(self, ctx: commands.Context, emote_name: str):
        """Removes given emote from the channel; ?remove <emote>"""
        emotes = await seventv.channel_emotes(ctx.channel_id)
        target_emote = [emote for emote in emotes if emote['name'] == emote_name]
        if len(target_emote) == 0:
            raise SevenTVException("No emote with given name found")
        emote_id = target_emote[0]['id']

        await seventv.remove_emote(ctx.channel_id, emote_id)
        await self.bot.message_queues.queue_command(ctx, f"Removed emote {emote_name}")


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def rename(self, ctx: commands.Context, emote_name: str, new_name: str):
        """Renames given emote to a new name; ?rename <emote> <new name>"""
        emotes = await seventv.channel_emotes(ctx.channel_id)
        target_emote = [emote for emote in emotes if emote['name'] == emote_name]
        if len(target_emote) == 0:
            raise SevenTVException("No emote with given name found")
        emote_id = target_emote[0]['id']

        await seventv.rename_emote(ctx.channel_id, emote_id, new_name)
        await self.bot.message_queues.queue_command(ctx, f"Renamed emote {emote_name} to {new_name}")


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def yoink(self, ctx: commands.Context, target_channel: twitchio.User, emote_name: str, alias: Optional[str], *args):
        """
        Yoinks an emote from the specified channel; a new alias can be specified;
        the name of the emote must be an exact match but it can be searched with filters:
        -c for case insensitive, -i for the given word to be included in an emote name,
        -s for the emote to start with the given word, matching more than one emote 
        results in an error; ?yoink <channel> <emote> <optinal alias> <filters>
        """
        if alias and alias.startswith("-"):
            args = args + (alias,)
            alias = None

        channel_emotes = await seventv.channel_emotes(target_channel.id)

        def emotes_match(emote: str, emote_query: str) -> bool:
            if "-c" in args:
                emote = emote.lower()
                emote_query = emote_query.lower()
            if "-i" in args:
                return emote_query in emote
            elif "-s" in args:
                return emote.startswith(emote_query)
            else:
                return emote == emote_query

        emotes = [emote for emote in channel_emotes if emotes_match(emote['name'], emote_name)]

        if len(emotes) == 0:
            raise SevenTVException("No emote with given query found")
        elif len(emotes) > 1:
            raise SevenTVException(f"More than one emote match given query: {', '.join([emote['name'] for emote in emotes])}")
        emote = emotes[0]
        alias = alias if alias else emote['name']

        added_emote = await seventv.add_emote(ctx.channel_id, emote['id'], alias)
        await self.bot.message_queues.queue_command(ctx, f"Added emote {added_emote}")


def prepare(bot: commands.Bot):
    bot.add_cog(SevenTV(bot))
