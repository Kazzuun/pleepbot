import sys

import twitchio
from twitchio.ext import commands

import database
from twitchbot import Bot


class Admin(commands.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot


    async def cog_check(self, ctx: commands.Context) -> bool:
        return await database.is_admin(ctx.author.id)


    @commands.command(no_global_checks=True)
    async def plonk(self, ctx: commands.Context):
        """It's just plonk"""
        await self.bot.message_queues.queue_command(ctx, "plonk")


    @commands.command(no_global_checks=True)
    async def join(self, ctx: commands.Context, *channels):
        """Joins specified channels"""
        if len(channels) == 0:
            return

        channels = await self.bot.fetch_users(channels)
        if len(channels) == 0:
            await self.bot.message_queues.queue_command(ctx, "Invalid users")
            return

        bot_connected_channels = [channel.name for channel in self.bot.connected_channels]

        log_only_channels = [channel for channel in channels if await database.channel_is_log_only(channel.name)]
        not_connected_channels = [channel for channel in channels if channel.name not in bot_connected_channels]

        # Joins channels that are log-only or not connected
        joinable_channels = [(str(channel.id), channel.name) for channel in log_only_channels + not_connected_channels]

        if len(joinable_channels) == 0:
            await self.bot.message_queues.queue_command(ctx, "Bot already joined in all given channels")
            return

        await self.bot.join_channels([channel.name for channel in not_connected_channels])
        await database.join_channels(joinable_channels)
        for _, channel in joinable_channels:
            self.bot.message_queues.add_channel(channel)

        joined_channel_names = [channel[1] for channel in joinable_channels]
        await self.bot.message_queues.queue_command(ctx, f"Joined {', '.join(joined_channel_names)}", targets=joined_channel_names)


    @commands.command(aliases=("leave", "depart"), no_global_checks=True)
    async def part(self, ctx: commands.Context, *channels):
        """Leaves specified channels"""
        if len(channels) == 0:
            return

        channels = [channel.lower().replace("_", "") for channel in channels]
        if len(channels) == 0:
            await self.bot.message_queues.queue_command(ctx, "Invalid users", reply=True)
            return

        bot_connected_channels = [channel.name for channel in self.bot.connected_channels]
        connected_channels = [channel for channel in channels if channel in bot_connected_channels]
        connected_not_log_only = [channel for channel in connected_channels if not await database.channel_is_log_only(channel)]

        # Parts channels that are connected
        if len(connected_channels) == 0:
            await self.bot.message_queues.queue_command(ctx, "Bot isn't connected to any given channel", reply=True)
            return

        await self.bot.message_queues.queue_command(ctx, f"Parted {', '.join(connected_channels)}", targets=connected_channels)
        # Log only channels don't have message queues
        for channel in connected_not_log_only:
            self.bot.message_queues.remove_channel(channel)
        await self.bot.part_channels(connected_channels)
        await database.part_channels(connected_channels)


    @commands.command(no_global_checks=True)
    async def logonly(self, ctx: commands.Context, *channels):
        """Joins specified channels in log-only mode"""
        if len(channels) == 0:
            return

        channels = [channel for channel in await self.bot.fetch_users(channels)]
        channel_names = [channel.name for channel in channels]
        if len(channels) == 0:
            await self.bot.message_queues.queue_command(ctx, "Invalid users", reply=True)
            return

        bot_connected_channels = [channel.name for channel in self.bot.connected_channels]
        connected = [channel for channel in channel_names if channel in bot_connected_channels]

        not_connected = [channel for channel in channel_names if channel not in bot_connected_channels]
        connected_not_log_only = [channel for channel in connected if not await database.channel_is_log_only(channel)]

        # Joins log-only to channels that not connected or are connected but not log-only
        joinable_channels = not_connected + connected_not_log_only

        if len(joinable_channels) == 0:
            await self.bot.message_queues.queue_command(ctx, "Bot is already log-only in given channels", reply=True)
            return

        await self.bot.join_channels(not_connected)
        await self.bot.message_queues.queue_command(ctx, f"Joined log-only to channels: {', '.join(joinable_channels)}", targets=joinable_channels)
        await database.join_channels_log_only([(str(channel.id), channel.name) for channel in channels])
        for channel in connected_not_log_only:
            self.bot.message_queues.remove_channel(channel)


    @commands.command(aliases=("bonk",), no_global_checks=True)
    async def ban(self, ctx: commands.Context, target: twitchio.User, *args):
        """Bans given user from using the bot"""
        note = None if len(args) == 0 else " ".join(args)
        await database.ban(target.id, target.name, note)
        await database.cancel_all_reminders(target.name)


    @commands.command(no_global_checks=True)
    async def block(self, ctx: commands.Context, *words):
        """Blocks given words"""
        if len(words) == 0:
            return
        count = await database.block_words(words)
        await self.bot.message_queues.queue_command(ctx, f"Blocked {count} word(s)")


    @commands.command(no_global_checks=True)
    async def unblock(self, ctx: commands.Context, *words):
        """Unblocks given words"""
        if len(words) == 0:
            return
        count = await database.unblock_words(words)
        await self.bot.message_queues.queue_command(ctx, f"Unblocked {count} word(s)")


    @commands.command(aliases=("kill", "sd"), no_global_checks=True)
    async def shutdown(self, ctx: commands.Context):
        """Shuts the bot down"""
        for task in self.bot.message_queues._tasks.values():
            task.cancel()
        await self.bot.close()
        sys.exit(0)


def prepare(bot: commands.Bot):
    bot.add_cog(Admin(bot))