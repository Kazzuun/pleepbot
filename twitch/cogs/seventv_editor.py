import os

from dotenv import load_dotenv; load_dotenv()
import twitchio
from twitchio.ext import commands

import database
from twitchbot import Bot
from twitch import seventv
from twitch.exceptions import SevenTVException


class SevenTVEditor(commands.Cog):
    COG_COOLDOWN = 5

    def __init__(self, bot: Bot) -> None:
        self.bot = bot


    async def cog_check(self, ctx: commands.Context) -> bool:
        channel_id = await database.channel_id(ctx.channel.name)
        editors = await seventv.get_editors(channel_id)

        bot_seventv_login = os.environ['SEVEN_TV_USERNAME']
        bot_is_editor = bot_seventv_login in editors or bot_seventv_login == ctx.channel.name
        if not bot_is_editor:
            raise SevenTVException(f"The bot is not a 7tv editor of this channel")

        sender_is_editor = ctx.author.name in editors or ctx.author.is_broadcaster
        if not sender_is_editor:
            raise SevenTVException(f"You are not a 7tv editor of this channel")

        return True


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def add(self, ctx: commands.Context, emote: str, *args):
        """
        Adds the given 7tv emote to the channel; emote can be specified with its name
        or id, if a name is given, a search is done to find it (see {prefix}help search
        for more info); an alias can be given to the emote; 
        {prefix}add <emote name or id> <optional alias> <search filters>
        """
        alias = None
        if len(args) > 0 and not args[0].startswith("-"):
            alias = args[0]

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

        channel_id = await database.channel_id(ctx.channel.name)
        added_emote = await seventv.add_emote(channel_id, emote_id, alias)
        await self.bot.message_queues.queue_command(ctx, f"Added emote {added_emote}")


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def remove(self, ctx: commands.Context, emote_name: str):
        """Removes given emote from the channel; {prefix}remove <emote>"""
        channel_id = await database.channel_id(ctx.channel.name)
        emotes = await seventv.channel_emotes(channel_id, force=True)
        target_emote = [emote for emote in emotes if emote['name'] == emote_name]
        if len(target_emote) == 0:
            raise SevenTVException("No emote with given name found (you may need to wait a bit for 7tv's cache to update)")
        emote_id = target_emote[0]['id']

        await seventv.remove_emote(channel_id, emote_id)
        await self.bot.message_queues.queue_command(ctx, f"Removed emote {emote_name}")


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def rename(self, ctx: commands.Context, emote_name: str, new_name: str):
        """Renames given emote to a new name; {prefix}rename <emote> <new name>"""
        channel_id = await database.channel_id(ctx.channel.name)
        emotes = await seventv.channel_emotes(channel_id, force=True)
        target_emote = [emote for emote in emotes if emote['name'] == emote_name]
        if len(target_emote) == 0:
            raise SevenTVException("No emote with given name found (you may need to wait a bit for 7tv's cache to update)")
        emote_id = target_emote[0]['id']

        await seventv.rename_emote(channel_id, emote_id, new_name)
        await self.bot.message_queues.queue_command(ctx, f"Renamed emote {emote_name} to {new_name}")


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def yoink(self, ctx: commands.Context, target_channel: twitchio.User, emote_name: str, *args):
        """
        Yoinks an emote from the specified channel; an alias can be specified;
        the name of the emote must be an exact match but it can be searched with filters:
        -c for case insensitive, -i for the given word to be included in an emote name,
        -s for the emote to start with the given word, matching more than one emote 
        gives all the emotes it matched without adding any; use -f to force a cache update;
        {prefix}yoink <channel> <emote> <optional alias> <filters>
        """
        alias = None
        if len(args) > 0 and not args[0].startswith("-"):
            alias = args[0]

        force = "-f" in args
        channel_emotes = await seventv.channel_emotes(target_channel.id, force=force)

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
            raise SevenTVException(f"More than one emote match given query: {' '.join([emote['name'] for emote in emotes])}")
        emote = emotes[0]

        # If alias has not been specified, use the alias it has on the target channel
        if alias is None:
            alias = emote["name"]

        channel_id = await database.channel_id(ctx.channel.name)
        added_emote = await seventv.add_emote(channel_id, emote['id'], alias)
        await self.bot.message_queues.queue_command(ctx, f"Added emote {added_emote}")


def prepare(bot: commands.Bot):
    bot.add_cog(SevenTVEditor(bot))
