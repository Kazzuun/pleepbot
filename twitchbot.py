from datetime import datetime, timedelta
import os
import random
import re
import traceback

from dotenv import load_dotenv; load_dotenv()
import twitchio
from twitchio.ext import commands, routines

import database
from twitch.message_queues import MessageQueues
from twitch.exceptions import SevenTVException, Filtered
from twitch import logging
from twitch.logging import logger


class Bot(commands.Bot):
    def __init__(self) -> None:
        # Setup logging
        logging.setup_logging()

        # Initialize database tables
        database.initialize_tables()

        self.prefixes = tuple(os.environ["BOT_PREFIXES"].split())
        self.initial_channels = database.initial_channels()

        super().__init__(
            token=os.environ["TMI_TOKEN"],
            client_id=os.environ["CLIENT_ID"],
            nick=os.environ["BOT_NICK"],
            prefix=self.prefixes,
            initial_channels=self.initial_channels,
        )
        # Initialize the message queues
        self.message_queues = MessageQueues(self, self.initial_channels)

        # Add the global check
        self.check(self.global_check)

        # Load cogs
        for filename in os.listdir("./twitch/cogs"):
            if filename.endswith('.py'):
                self.load_module(f'twitch.cogs.{filename[:-3]}')


    async def event_ready(self) -> None:
        # In case there aren't any channels in the database, add the bot's channel and join it
        if len(self.initial_channels) == 0:
            await self.join_channels([self.nick])
            self.message_queues.add_channel(self.nick)
            await database.join_channels([(self.user_id, self.nick)])

        self.check_reminders.start()
        self.database_backup.start()
        logger.info("Bot started")


    async def event_message(self, message: twitchio.Message) -> None:
        # Remove unnecessary whitespace and empty characters from chatterino
        message.content = re.sub(f"\s+", " ", message.content.strip()).replace(u"\U000E0000", "")
        channel = message.channel.name
        if message.echo:
            await database.log_message(channel, self.nick, message.content)
            return

        sender = message.author.name
        # Log the message
        await database.log_message(channel, sender, message.content)

        # Check if a channel is logging only and should not allow commands
        if await database.channel_is_log_only(channel):
            return

        # Disallow banned users to use the bot
        if await database.is_banned(message.author.id):
            if message.content.startswith(self.prefixes):
                logger.info("Banned user %s (%s) tried to use a command '%s' in #%s", sender, str(message.author.id), message.content, channel)
            return

        # Handle the command
        await self.handle_commands(message)

        # Queue possible notifications for the user
        for notif in await database.sendable_notifications(channel, sender):
            if notif.reminderType == database.ReminderType.NOTIFY:
                notif.channel = channel
            try:
                await self.message_queues.queue_reminder(notif)
                await database.set_reminder_as_sent(notif.id)
            except KeyError:
                await database.cancel_reminder(notif.id)
                logger.warning("Notification not sent: %s", str(notif))

        if (random.random() < 0.15 and 
            not message.content.startswith(self.prefixes) and 
            self.message_queues._queues[channel].qsize() == 0 and 
            "pleep" in message.content
        ):
            await self.message_queues.queue_message(channel, "pleep")


    async def handle_commands(self, message: twitchio.Message) -> None:
        # Allow a whitespace between prefix and the command name
        if message.content.startswith(tuple(f"{prefix} " for prefix in self.prefixes)):
            message.content = message.content.replace(" ", "", 1)
        elem = message.content.split(maxsplit=1)

        # Make commands case insensitive
        message.content = f"{elem[0].lower()} {' '.join(elem[1:])}"

        # Allow specifying a target with an underscore as not to ping the target
        if len(message.content.split()) > 1:
            first_arg = message.content.split()[1]
            if first_arg.startswith("_"):
                message.content = message.content.replace(first_arg, first_arg[1:], 1)
        await super().handle_commands(message)


    async def event_command_error(self, ctx: commands.Context, error: Exception) -> None:
        if isinstance(error, SevenTVException):
            await self.message_queues.queue_command(ctx, error.message)

        elif isinstance(error, Filtered):
            pass

        elif isinstance(error, commands.MissingRequiredArgument):
            await self.message_queues.queue_command(ctx, "You're missing an argument: " + error.name, reply=True)

        elif isinstance(error, commands.CommandOnCooldown):
            if ctx.command.name in ("fortune", "fish"):
                await self.message_queues.queue_command(ctx, error.args[0])

        elif isinstance(error, commands.ArgumentParsingFailed):
            pass

        elif isinstance(error, commands.BadArgument):
            pass

        elif isinstance(error, commands.CommandNotFound):
            pass

        else:
            logger.warning(
                "[#%s] an error occured during the execution of %s's command <%s>: %s", 
                ctx.channel.name, ctx.author.name, ctx.command.name, error
            )
            return

        logger.debug("[#%s] %s's command <%s> failed: %s", ctx.channel.name, ctx.author.name, ctx.command.name, error)


    async def global_check(self, ctx: commands.Context) -> bool:
        """Global check if a target has opted out of the command or is banned"""
        if len(ctx.args) == 0:
            return True
        for arg in ctx.args:
            if isinstance(arg, twitchio.User):
                if ctx.author.name != arg.name and await database.has_opted_out(arg.id, ctx.command.name):
                    await self.message_queues.queue_command(ctx, "Target has opted out of that command")
                    return False
                elif await database.is_banned(arg.id):
                    return False
            elif isinstance(arg, twitchio.PartialChatter) and ctx.author.name != arg.name and await database.has_opted_out(arg.name, ctx.command.name, username=True):
                await self.message_queues.queue_command(ctx, "Target has opted out of that command")
                return False

        return True


    @routines.routine(seconds=1)
    async def check_reminders(self):
        """Routine to poll for reminders every second and send any found."""
        reminders = await database.sendable_reminders()
        for reminder in reminders:
            try:
                await self.message_queues.queue_reminder(reminder)
                await database.set_reminder_as_sent(reminder.id)
            except KeyError:
                await database.cancel_reminder(reminder.id)
                logger.warning("Reminder not sent: %s", str(reminder))


    @routines.routine(time=datetime(2024, 1, 1))
    async def database_backup(self):
        """Backup database once a day"""
        await database.backup_database()
        logger.info("Database backed up")


    async def global_before_invoke(self, ctx: commands.Context) -> None:
        ctx.exec_time = datetime.utcnow()


    async def global_after_invoke(self, ctx: commands.Context) -> None:
        time_ellapsed: timedelta = datetime.utcnow() - ctx.exec_time
        logger.debug(f"[#%s] %s executed command <%s>. Time taken: %s", ctx.channel.name, ctx.author.name, ctx.command.name, f"{time_ellapsed.microseconds/1000:.2f}ms")


if __name__ == "__main__":
    bot = Bot()
    bot.run()
