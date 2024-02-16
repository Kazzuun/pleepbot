from datetime import datetime
import os
import platform
import re
from typing import Optional

import psutil
from twitchio.ext import commands

import database
from twitchbot import Bot


class Util(commands.Cog):
    COG_COOLDOWN = 3

    def __init__(self, bot: Bot) -> None:
        self.bot = bot


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def ping(self, ctx: commands.Context):
        """Pings the bot showing stats from the machine it's running on"""
        p = psutil.Process(os.getpid())
        system = f"System: {platform.uname().system}"
        memory = f"Memory: {p.memory_info().rss // 1024 ** 2}MB"
        cpu = f"CPU: {p.cpu_percent()}%"
        uptime = f"Uptime: {str(datetime.utcnow() - datetime.utcfromtimestamp(p.create_time())).split('.')[0]}"
        temp = psutil.sensors_temperatures().get("cpu_thermal")
        if temp is not None:
            temperature = f"Temperature: {temp[0].current}°C"
        else:
            temperature = f"Temperature: Unknown"
        await self.bot.message_queues.queue_command(ctx, ", ".join([system, memory, cpu, uptime, temperature]))


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def silent(self, ctx: commands.Context, switch: Optional[str]):
        """Silences pings from commands; can be toggled back on with {prefix}silent of"""
        if switch in ("off", "disable"):
            success = await database.enable_pings(ctx.author.id)
            if success:
                await self.bot.message_queues.queue_command(ctx, "Pings are no longer silent", reply=True)
            else:
                await self.bot.message_queues.queue_command(ctx, "Your pings are already enabled", reply=True)
        else:
            success = await database.mute_pings(ctx.author.id, ctx.author.name)
            if success:
                await self.bot.message_queues.queue_command(ctx, "Pings are now silent", reply=True)
            else:
                await self.bot.message_queues.queue_command(ctx, "Your pings are already silent", reply=True)


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def optout(self, ctx: commands.Context, *args):
        """
        Opts out of getting targeted with commands; {prefix}optout <command1> <command2>...
        or to optout from every possible command {prefix}optout all
        """
        if len(args) == 0:
            return

        if args[0] == "all":
            args = tuple(self.bot.commands.keys())

        optoutables = []
        for command in args:
            cmd = self.bot.get_command(command)
            # Make sure command exists, it's not an admin command, and the command has some kind of param that is a target
            if cmd and not cmd.no_global_checks and any(["target" in param.name for param in cmd.params.values()]):
                optoutables.append(cmd.name)

        if len(optoutables) == 0:
            await self.bot.message_queues.queue_command(ctx, "None of the given commands are optoutable", reply=True)
            return

        nof_successes = await database.optout(ctx.author.id, ctx.author.name, optoutables)
        if nof_successes == 0:
            await self.bot.message_queues.queue_command(ctx, "You have already opted out of all the given commands", reply=True)
        else:
            await self.bot.message_queues.queue_command(ctx, f"Opted out of {nof_successes} command(s) successfully", reply=True)


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def optin(self, ctx: commands.Context, *args):
        """
        Opts in to be able to be target with commands again; {prefix}optin <command1> <command2>...
        or to optin to every possible command {prefix}optout all
        """
        if len(args) == 0:
            return

        if args[0] == "all":
            args = tuple(self.bot.commands.keys())

        nof_successes = await database.optin(ctx.author.id, args)
        if nof_successes == 0:
            await self.bot.message_queues.queue_command(ctx, "You have not opted out of any of the given commands", reply=True)
        else:
            await self.bot.message_queues.queue_command(ctx, f"Opted in to {nof_successes} command(s) successfully", reply=True)


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command(aliases=("cmd", "command", "commands"))
    async def cmds(self, ctx: commands.Context):
        """Lists all the commands"""
        not_included = ("Admin",)
        filtered_cogs = [cog for cog in self.bot.cogs.values() if cog.name not in not_included]
        await self.bot.message_queues.queue_command(ctx, " | ".join([", ".join(cog.commands.keys()) for cog in filtered_cogs]))


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def help(self, ctx: commands.Context, command: str):
        """Shows help for the given command; {prefix}help <command>"""
        cmd = self.bot.get_command(command)
        if cmd is None:
            await self.bot.message_queues.queue_command(ctx, "Given command doesn't exist", reply=True)
            return
        elif cmd.no_global_checks:
            return

        description = self.bot.commands[cmd.name]._callback.__doc__
        if description is None:
            await self.bot.message_queues.queue_command(ctx, "No command description", reply=True)
        else:
            cleaned = re.sub(f"\s+", " ", description.strip())
            add_prefix = cleaned.replace("{prefix}", self.bot.prefixes[0])
            await self.bot.message_queues.queue_command(ctx, add_prefix, reply=True)


def prepare(bot: commands.Bot):
    bot.add_cog(Util(bot))
