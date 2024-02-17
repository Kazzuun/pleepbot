from collections import Counter
from datetime import datetime
from typing import Optional

import twitchio
from twitchio.ext import commands

import database
from twitch import seventv
from twitchbot import Bot


class Message(commands.Cog):
    COG_COOLDOWN = 3

    def __init__(self, bot: Bot) -> None:
        self.bot = bot


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command(aliases=("randommessage", "randomessage", "randmsg"))
    async def rm(self, ctx: commands.Context, target: Optional[twitchio.PartialChatter], *args):
        """
        Sends a random message from chat logs from target, no target for your own, "all" for everyone;
        filters can be added to reduce possible messages: > or < followed by a number to specify 
        length of the message, + or - followed by a word to include or exclude the word, 
        only one of each can be used; {prefix}rm <optional target> <optional filters>
        """
        filters = ("<", ">", "+", "-")

        if target is None:
            target = ctx.author.name
        elif target.name in ("all",):
            target = None
        else:
            if target.name.startswith(filters):
                args = args + (target.name,)
                target = ctx.author.name
            else:
                target = target.name.lower()

        lt = None
        gt = None
        included = None
        excluded = None
        for arg in args:
            try:
                if arg.startswith("<"):
                    num = int(arg[1:])
                    if 501 > num > 1:
                        lt = num
                elif arg.startswith(">"):
                    num = int(arg[1:])
                    if 499 > num > 1:
                        gt = num
                elif arg.startswith("+"):
                    included = f"%{arg[1:]}%"
                elif any(arg == f"-{prefix}" for prefix in self.bot.prefixes):
                    excluded = f"{arg[1:]}%"
                elif arg.startswith("-"):
                    excluded = f"%{arg[1:]}%"
            except ValueError:
                pass

        nof_filters = len([fil for fil in (lt, gt, included, excluded) if fil is not None])
        result = await database.random_message(ctx.channel.name, target, lt=lt, gt=gt, included=included, excluded=excluded)
        if result is None and nof_filters == 0:
            await self.bot.message_queues.queue_command(ctx, "User hasn't sent any message in this channel", reply=True)
            return
        elif result is None:
            await self.bot.message_queues.queue_command(ctx, "No message found with given filters", reply=True)
            return
        
        sender, message, sentAt = result
        filter_info = "" if nof_filters == 0 else f"({nof_filters} filter(s))"
        await self.bot.message_queues.queue_command(ctx, f"({sentAt.strftime('%d/%m/%Y, %H:%M:%S')}) {filter_info} _{sender}: {message}")


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command(aliases=("nofmessages",))
    async def nofm(self, ctx: commands.Context, target: Optional[twitchio.PartialChatter], *args):
        """
        Sends the number of messages sent by target, no target for your own, "all" for everyone;
        filters can be added to reduce possible messages: < or > followed by a number to specify 
        length of the message, + or - followed by a word to include or exclude words; 
        only one of each can be used; {prefix}nofm <optional target> <optional filters>
        """
        filters = ("<", ">", "+", "-")

        if target is None:
            target = ctx.author.name
        elif target.name in ("all",):
            target = None
        else:
            if target.name.startswith(filters):
                args = args + (target.name,)
                target = ctx.author.name
            else:
                target = target.name.lower()

        lt = None
        gt = None
        included = None
        excluded = None
        for arg in args:
            try:
                if arg.startswith("<"):
                    num = int(arg[1:])
                    if 501 > num > 1:
                        lt = num
                elif arg.startswith(">"):
                    num = int(arg[1:])
                    if 499 > num > 1:
                        gt = num
                elif arg.startswith("+"):
                    included = f"%{arg[1:]}%"
                elif any(arg == f"-{prefix}" for prefix in self.bot.prefixes):
                    excluded = f"{arg[1:]}%"
                elif arg.startswith("-"):
                    excluded = f"%{arg[1:]}%"
            except ValueError:
                pass

        nof_filters = len([fil for fil in (lt, gt, included, excluded) if fil is not None])
        count = await database.nofmessages(ctx.channel.name, target, lt=lt, gt=gt, included=included, excluded=excluded)
        if count == 0 and nof_filters == 0:
            await self.bot.message_queues.queue_command(ctx, "User hasn't sent any message in this channel", reply=True)
            return
        elif count == 0:
            await self.bot.message_queues.queue_command(ctx, f"User hasn't sent any messages matching the {nof_filters} filter(s)", reply=True)
            return

        filter_info = "" if nof_filters == 0 else f" ({nof_filters} filter(s))"
        if target is None:
            await self.bot.message_queues.queue_command(ctx, f"Total messages sent{filter_info}: {count}")
        else:
            await self.bot.message_queues.queue_command(ctx, f"Messages sent by _{target}{filter_info}: {count}")


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command(aliases=("emotecount",))
    async def ecount(self, ctx: commands.Context, emote: str):
        """Shows the number of times an emote has been used; {prefix}ecount <emote>"""
        channel = await ctx.channel.user()
        global_emotes = await seventv.global_emotes()
        channel_emotes = await seventv.channel_emotes(channel.id)

        if emote not in [emote['name'] for emote in global_emotes + channel_emotes]:
            await self.bot.message_queues.queue_command(ctx, "Only 7tv emotes can be used", reply=True)
            return

        count = await database.emote_count(ctx.channel.name, emote)
        await self.bot.message_queues.queue_command(ctx, f"{emote} has been used {count} times")


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command(aliases=("lastseen",))
    async def ls(self, ctx: commands.Context, target: twitchio.User):
        """
        Tells how much time since the target's last message in the current chat, 
        includes the last message; {prefix}ls <target>
        """
        user = target.name
        if user == ctx.author.name:
            await self.bot.message_queues.queue_command(ctx, "You were here just now", reply=True)
            return

        seen = await database.lastseen(ctx.channel.name, user)

        if seen is None:
            await self.bot.message_queues.queue_command(ctx, f"_{user} has not been seen in this chat")
        else:
            message, time = seen
            ellapsed_time = datetime.utcnow() - time
            await self.bot.message_queues.queue_command(ctx, f"_{user} was last seen in chat {str(ellapsed_time).split('.')[0]} ago: {message}")


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def stalk(self, ctx: commands.Context, target: twitchio.User):
        """
        Tells how much time since the target's last message in any chat the bot is in, 
        includes the last message; {prefix}stalk <target>
        """
        user = target.name
        if user == ctx.author.name:
            await self.bot.message_queues.queue_command(ctx, "You were here just now", reply=True)
            return

        seen = await database.stalk(user)

        if seen is None:
            await self.bot.message_queues.queue_command(ctx, f"_{user} has not been seen in any chat the bot is in")
        else:
            channel, message, time = seen
            ellapsed_time = datetime.utcnow() - time
            await self.bot.message_queues.queue_command(ctx, f"_{user} was last seen in #{channel} {str(ellapsed_time).split('.')[0]} ago: {message}")


def prepare(bot: commands.Bot):
    bot.add_cog(Message(bot))
