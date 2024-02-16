from __future__ import annotations
from asyncio import Queue, sleep, Task
from typing import Union

from twitchio.ext import commands

import database
from twitch.exceptions import Filtered


class ISendableMessage:
    def __init__(self, *args, **kwargs) -> None:
        self.message: str

    async def send(self):
        pass


class CommandMessage(ISendableMessage):
    def __init__(self, ctx: commands.Context, message: str, *, reply: bool = False):
        self.ctx = ctx
        self.message = message
        self.reply = reply

    async def send(self):
        if self.reply:
            await self.ctx.reply(self.message)
        else:
            await self.ctx.send(self.message)


class Message(ISendableMessage):
    def __init__(self, bot: commands.Bot, channel: str, message: str):
        self.bot = bot
        self.channel = channel 
        self.message = message

    async def send(self):
        await self.bot.get_channel(self.channel).send(self.message)


class MessageQueues:
    def __init__(self, bot: commands.Bot, initial_channels: list[str]) -> None:
        self.bot = bot
        self._queues: dict[str, Queue[ISendableMessage]] = {}
        self._tasks: dict[str, Task] = {}
        for channel in initial_channels:
            self._queues[channel] = Queue()
            self._tasks[channel] = self.bot.loop.create_task(self.clear_queue(channel))


    async def _add_to_queue(self, channel: str, message: ISendableMessage) -> None:
        # Make sure the message is of valid length
        # Twitch allows messages upto 500 characters long
        if len(message.message) == 0:
            return
        elif len(message.message) > 495:
            message.message = message.message + " ..."

        # If bot is not mod and the message it sends is identical to the previous one
        # add an ' at the end of the message so that it doesn't get eaten by twitch
        if not self.bot.get_channel(channel)._bot_is_mod() and message.message == await database.bot_last_message(channel):
            message.message = message.message + " '"

        # Make sure the message doesn't contain any blocked words
        blocked_words = await database.blocked_words()
        for blocked_word in blocked_words:
            blocked_word = blocked_word.lower()
            message_words = message.message.lower().split()
            for word in message_words:
                if blocked_word in word and len(word) <= len(blocked_word) <= len(word) + 1:
                    raise Filtered(f"Blocked word '{blocked_word}' found in message '{message.message}'")

        await self._queues[channel].put(message)


    async def clear_queue(self, channel: str) -> None:
        while True:
            message = await self._queues[channel].get()
            await message.send()
            if not self.bot.get_channel(channel)._bot_is_mod():
                await sleep(1.2)


    def add_channel(self, channel: str) -> None:
        self._queues[channel] = Queue()
        self._tasks[channel] = self.bot.loop.create_task(self.clear_queue(channel))


    def remove_channel(self, channel: str) -> None:
        task = self._tasks[channel]
        task.cancel()
        del self._tasks[channel]
        del self._queues[channel]


    async def queue_command(self, ctx: commands.Context, message: str, *, reply: bool = False, targets: Union[tuple[str], list[str]] = tuple()) -> None:
        pings_muted = await database.silent_pings(ctx.author.name)
        if reply and pings_muted:
            message = f"_{ctx.author.name}, {message}"
            reply = False

        for target in targets:
            has_pings_muted = await database.silent_pings(target)
            if has_pings_muted:
                message = " ".join(map(lambda word: f"_{word}" if target in word and not word.startswith("_") else word, message.split()))

        await self._add_to_queue(ctx.channel.name, CommandMessage(ctx, message, reply=reply))


    async def queue_message(self, channel: str, message: str) -> None:
        await self._add_to_queue(channel, Message(self.bot, channel, message))


    async def queue_reminder(self, reminder: database.Reminder) -> None:
        await self._add_to_queue(reminder.channel, Message(self.bot, reminder.channel, await reminder.formatted_message()))

