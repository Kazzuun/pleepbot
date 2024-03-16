from datetime import datetime, timedelta
import random
from typing import Optional

import twitchio
from twitchio.ext import commands

import database
from database import ReminderType, EquipmentType, FishingEquipmentCatalogue
from twitch import seventv
from twitchbot import Bot


class Fish(commands.Cog):
    COG_COOLDOWN = 3

    def __init__(self, bot: Bot) -> None:
        self.bot = bot


    def level_from_exp(self, experience: int) -> int:
        level = min(int((experience / 50) ** 0.5) + 1, 100)
        return level


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.user)
    @commands.command(aliases=("fishing", "fishinge", "fishingtime", "fishh", "🐟", "🎣"))
    async def fish(self, ctx: commands.Context, *args):
        """
        You go fishing; number of fish you catch is based on luck, fishing level, and time since last fished,
        which is capped at 7 days; set a reminder to remind you to fish when the cooldown is up with -r flag
        """
        equipment_catalogue = FishingEquipmentCatalogue()
        owned = await database.owned_fishing_equipment(ctx.author.id)
        owned_equipment = equipment_catalogue.equipment_owned(owned)

        fish_flat: int = sum([e.effect for e in owned_equipment if e.equipment_type == EquipmentType.FISHFLAT])
        cooldown_flat: int = sum([e.effect for e in owned_equipment if e.equipment_type == EquipmentType.COOLDOWNFLAT])
        fish_multi: float = 1 + sum([e.effect for e in owned_equipment if e.equipment_type == EquipmentType.FISHMULTI])
        exp_multi: float = 1 + sum([e.effect for e in owned_equipment if e.equipment_type == EquipmentType.EXPMULTI])
        afk_multi: float = 1 + sum([e.effect for e in owned_equipment if e.equipment_type == EquipmentType.AFKMULTI])
        norng: bool = len([e for e in owned_equipment if e.equipment_type == EquipmentType.NORNG]) > 0

        cooldown_period = 3600 - cooldown_flat
        current_time = datetime.utcnow()
        last_fished = await database.last_fished(ctx.author.id)
        seconds_ellapsed = int((current_time - last_fished).total_seconds()) if last_fished else cooldown_period

        # Manage cooldown
        if seconds_ellapsed < cooldown_period:
            cooldown_left = cooldown_period-seconds_ellapsed

            if "-r" in args and cooldown_left >= 15:
                rem_id = await database.set_reminder(
                    ctx.channel.name, 
                    ctx.author.name, 
                    ctx.author.name, 
                    ReminderType.REMIND,
                    f"{self.bot.prefixes[0]}fish",
                    datetime.utcnow() + timedelta(seconds=cooldown_left)
                )
                reminder_msg = f" | Reminding you to fish when the time is up (ID {rem_id})"
            else:
                reminder_msg = ""

            minutes, seconds = divmod(cooldown_left, 60)
            await self.bot.message_queues.queue_command(
                ctx, 
                f"You can go fishing again in {minutes}m {seconds}s{reminder_msg}", 
                reply=True
            )
            return

        hours = seconds_ellapsed / 3600
        cooldown_hours = cooldown_period / 3600
        exp_before = await database.fishing_exp(ctx.author.id)
        level_before = self.level_from_exp(exp_before)

        if norng:
            total_fish_count = int((
                2
                + (level_before - 1) ** 0.5
                + (min(hours, 7 * 24) ** 0.4 - cooldown_hours ** 0.4) * afk_multi
                + fish_flat
            ) * fish_multi)
        else:
            # Base count of 1 or 2 fish + random number based on current level + count based on hours since last fished
            total_fish_count = int((
                random.randint(1, 2)
                + (random.random() + 1) / 2 * ((level_before - 1) ** 0.5)
                + (random.random() + 3) / 4 * (min(hours, 7 * 24) ** 0.4 - cooldown_hours ** 0.4) * afk_multi
                + fish_flat
            ) * fish_multi)

        # Check this just in case
        if total_fish_count < 1:
            await self.bot.message_queues.queue_command(ctx, "You suck at fishing...", reply=True)
            return

        channel_id = await database.channel_id(ctx.channel.name)
        channel_emotes = [emote["name"] for emote in await seventv.channel_emotes(channel_id)]
        global_emotes = [emote["name"] for emote in await seventv.global_emotes()]
        channel_emotes.extend(global_emotes)

        most_used_emotes = await database.emote_counts(ctx.channel.name, channel_emotes, ignore_bot=True)
        top_n = 10
        emotes_ordered = most_used_emotes.most_common(top_n)

        fish_caught = random.choices(
            # The most common has the smallest index
            [(i, emote[0]) for i, emote in enumerate(emotes_ordered)],
            # The most common has the highest weight
            weights=[1 / j for j in range(1, top_n + 1)], 
            k=total_fish_count
        )
        # Sort caught fish by its rarity (index), most common first
        fish_caught.sort()

        # The most common has the highest index getting the least exp
        total_exp_amount = int(sum([60 / (top_n - index) for index, _ in fish_caught]) * exp_multi)

        exp_after = exp_before + total_exp_amount
        level_after = self.level_from_exp(exp_after)
        level_up_notif = "" if level_before == level_after else f", LEVEL UP {level_before}->{level_after}!"

        await database.fish(ctx.author.id, ctx.author.name, total_fish_count, total_exp_amount)

        if "-r" in args:
            rem_id = await database.set_reminder(
                ctx.channel.name, 
                ctx.author.name, 
                ctx.author.name, 
                ReminderType.REMIND,
                f"{self.bot.prefixes[0]}fish",
                datetime.utcnow() + timedelta(seconds=cooldown_period)
            )
            minutes = cooldown_period // 60
            reminder_msg = f" | Reminding you to fish in {minutes} minutes (ID {rem_id})"
        else:
            reminder_msg = ""

        fish_caught_count = {}
        for _, name in fish_caught:
            fish_caught_count[name] = fish_caught_count.get(name, 0) + 1

        caught = " | ".join([f"{name} - {count}" for name, count in fish_caught_count.items()])
        await self.bot.message_queues.queue_command(
            ctx, 
            f"You caught {total_fish_count} fish: {caught}, exp got: {total_exp_amount}{level_up_notif}{reminder_msg}", 
            reply=True
        )


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command(aliases=("fs", "exp", "level", "fishcount"))
    async def fishstats(self, ctx: commands.Context, target: Optional[twitchio.User]):
        """
        Shows the number of fish you have caught; can be used with a target:
        {prefix}fishcount <target>
        """
        target = target if target else ctx.author
        count = await database.fish_count(target.id)
        exp = await database.fishing_exp(target.id)
        level = self.level_from_exp(exp)
        await self.bot.message_queues.queue_command(
            ctx, 
            f"_{target.name} has caught {count} fish, has {exp} exp, and is level {level}"
        )


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command(aliases=("topfish", "toplevel",))
    async def topexp(self, ctx: commands.Context, *args):
        """
        Shows the fishing stats of the top 5 people ordered by exp;
        can be ordered by fish count with -c flag
        """
        top_n = 5
        if "-c" in args or "count" in args:
            top_users = await database.top_fishing_exp(top_n, fish_count=True)
        else:
            top_users = await database.top_fishing_exp(top_n)
        user_info = []
        for i, top_fisher in enumerate(top_users):
            username, exp, fish_count = top_fisher
            level = self.level_from_exp(exp)
            user_info.append(f"{i+1}. _{username} - level {level}, {exp} exp, {fish_count} caught")
        await self.bot.message_queues.queue_command(ctx, " | ".join(user_info))


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command(aliases=("fishstore",))
    async def store(self, ctx: commands.Context, page: int = 1):
        """
        Shows every available item to be purchased; all bought items give permanent buffs to fishing 
        abilities; items have a level requirement, and they cost exp, meaning you lose levels
        when buying an item; to view possible additional pages: {prefix}store <page>
        """
        equipment_catalogue = FishingEquipmentCatalogue()
        owned_equipment = await database.owned_fishing_equipment(ctx.author.id)
        not_owned = equipment_catalogue.equipment_not_owned(owned_equipment)
        if len(not_owned) == 0:
            await self.bot.message_queues.queue_command(ctx, "The store is empty")
            return

        formatted_items = [f"({e.id}) {e.name}: {e.effect_disc} (req: lvl{e.level_req}) (cost: {e.cost/1000:0.1f}k exp)" for e in not_owned]
        pages = {}
        store_page = []
        for item in formatted_items:
            if sum([len(item) for item in store_page]) + len(item) > 350:
                pages[len(pages)+1] = store_page
                store_page = []
            store_page.append(item)
        pages[len(pages)+1] = store_page

        if page in pages:
            await self.bot.message_queues.queue_command(ctx, " | ".join(pages[page]), reply=True)
        else:
            await self.bot.message_queues.queue_command(ctx, "Page not found", reply=True)


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command()
    async def buy(self, ctx: commands.Context, item_id: int):
        """
        Buys an item from the store; item is specified by its id shown in parentheses in the store;
        see {prefix}store for the store; {prefix}buy <item_id>
        """
        equipment_catalogue = FishingEquipmentCatalogue()
        owned_equipment = await database.owned_fishing_equipment(ctx.author.id)
        not_owned = equipment_catalogue.equipment_not_owned(owned_equipment)

        target_item = [item for item in not_owned if item.id == item_id]
        if len(target_item) == 0:
            if equipment_catalogue.item_by_id(item_id) is None:
                await self.bot.message_queues.queue_command(ctx, "Invalid item", reply=True)
            else:
                await self.bot.message_queues.queue_command(ctx, "You already own that item", reply=True)
            return

        target_item = target_item[0]
        exp = await database.fishing_exp(ctx.author.id)
        level = self.level_from_exp(exp)

        if target_item.level_req > level:
            await self.bot.message_queues.queue_command(ctx, f"Your level is too low: {level}<{target_item.level_req}", reply=True)
        # Check this just in case
        elif target_item.cost > exp:
            await self.bot.message_queues.queue_command(ctx, "You don't have enough exp", reply=True)
        else:
            await database.buy_fishing_equipment(ctx.author.id, target_item.id, target_item.cost)
            exp_after = exp - target_item.cost
            level_after = self.level_from_exp(exp_after)
            await self.bot.message_queues.queue_command(
                ctx, 
                f"You bought {target_item.name} ({target_item.effect_disc}) for {target_item.cost/1000:0.1f}k exp, level {level}->{level_after}",
                reply=True
            )


    @commands.cooldown(rate=1, per=COG_COOLDOWN, bucket=commands.Bucket.member)
    @commands.command(aliases=("items",))
    async def equipment(self, ctx: commands.Context, page: int = 1):
        """Shows all your bought fishing equipment"""
        equipment_catalogue = FishingEquipmentCatalogue()
        owned_equipment = await database.owned_fishing_equipment(ctx.author.id)
        owned = equipment_catalogue.equipment_owned(owned_equipment)
        if len(owned) == 0:
            await self.bot.message_queues.queue_command(ctx, "You don't own any equipment", reply=True)
            return

        formatted_items = [f"({e.id}) {e.name}: {e.effect_disc}" for e in owned]
        pages = {}
        store_page = []
        for item in formatted_items:
            if sum([len(item) for item in store_page]) + len(item) > 350:
                pages[len(pages)+1] = store_page
                store_page = []
            store_page.append(item)
        pages[len(pages)+1] = store_page

        if page in pages:
            await self.bot.message_queues.queue_command(ctx, " | ".join(pages[page]), reply=True)
        else:
            await self.bot.message_queues.queue_command(ctx, "Page not found", reply=True)


def prepare(bot: commands.Bot):
    bot.add_cog(Fish(bot))
