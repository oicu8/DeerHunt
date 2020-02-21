import asyncio
from datetime import datetime, timedelta, timezone
import dateutil.parser
import random

import discord
import time
from discord.ext import commands
from cogs.helpers import checks

from cogs.helpers.deer import DeerWrapper

DIAG_SLOWNESS = True

if DIAG_SLOWNESS:
    def diag_slowness(starting_time, ctx, message):
        now = time.time()
        delta = round(now - starting_time,2)
        print(f"[+{delta} | {ctx.channel.id} | {ctx.author.id}] {message}")
else:
    def diag_slowness(starting_time, ctx, message):
        return


class User(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def sendBangMessage(self, ctx, string: str):
        lag = await self.bot.db.get_pref(ctx.channel, "bang_lag")
        if ctx.bot.current_event['id'] == 2:
            lag += ctx.bot.current_event['seconds_of_lag_added']

        if lag > 0:
            tmp = await ctx.channel.send(str(ctx.message.author.mention) + " > BANG")
            await asyncio.sleep(lag)
            await tmp.edit(content=str(ctx.message.author.mention) + " > " + string)

        else:
            await self.bot.send_message(ctx=ctx, can_pm=False, message=string)

    @commands.command()
    @checks.is_channel_enabled()
    @checks.had_giveback()
    async def reload(self, ctx):

        message = ctx.message
        channel = message.channel
        author = message.author
        guild = message.guild
        level = await self.bot.db.get_level(channel=channel, player=author)

        # Coroutines
        get_stat = self.bot.db.get_stat
        set_stat = self.bot.db.set_stat
        add_to_stat = self.bot.db.add_to_stat

        get_pref = self.bot.db.get_pref

        _ = self.bot._
        language = await get_pref(channel, "language")

        balles = await get_stat(channel, author, "balles")
        balles_max = level["balles"]
        chargeurs = await get_stat(channel, author, "chargeurs")
        chargeurs_max = level["chargeurs"]
        should_reload = balles == 0
        can_reload = chargeurs > 0

        # 1/ Do he have a weapon ?
        if await get_stat(channel, author, "confisque"):
            await self.bot.send_message(ctx=ctx, message=_("You don't have a weapon.", language))
            # await add_to_stat(channel, author, "reloads_without_weapon", 1)
            return

        # 2/ Need to unjam ?
        if await get_stat(channel, message.author, "enrayee"):
            await self.bot.send_message(ctx=ctx, message=_("You unjammed your weapon.", language))
            await set_stat(channel, message.author, "enrayee", False)

            if not should_reload:
                return

        # 3/ Reloading
        if should_reload:
            if can_reload:
                await set_stat(channel, message.author, "balles", balles_max)
                await add_to_stat(channel, message.author, "chargeurs", -1)
                await add_to_stat(channel, message.author, "reloads", 1)
                chargeurs -= 1
                balles = balles_max
                greet = _("You reloaded your weapon.", language)
            else:
                greet = _("You don't have any ammo left!", language)
                await add_to_stat(channel, message.author, "reloads_without_chargers", 1)
        else:
            greet = _("You don't need to reload your weapon.", language)
            await add_to_stat(channel, message.author, "unneeded_reloads", 1)

        await self.bot.send_message(ctx=ctx, message=_(
            "{greet} | Ammo in weapon: {balles_actuelles}/{balles_max} | Magazines left: {chargeurs_actuels}/{chargeurs_max}",
            language).format(
            **{"greet": greet, "balles_actuelles": balles, "balles_max": balles_max, "chargeurs_actuels": chargeurs,
               "chargeurs_max": chargeurs_max}))

    @commands.command(
        aliases=["pan", "pew", "pang", "shoot", "kablam", "pow", "bong", "bonk", "itshighnoon", "its_high_noon",
                 "killthatfuckingdeer", "kill_that_fucking_deer", "kill_that_fucking_deer_omg"])
    @checks.is_channel_enabled()
    @checks.had_giveback()
    async def bang(self, ctx, target: discord.Member = None):
        now = time.time()
        diag_slowness(now, ctx, "Starting bang")
        message = ctx.message
        channel = message.channel
        author = message.author
        guild = message.guild
        diag_slowness(now, ctx, "Got basic objects")
        level = await self.bot.db.get_level(channel=channel, player=author)
        diag_slowness(now, ctx, "Got author level")

        # Coroutines
        get_stat = self.bot.db.get_stat
        set_stat = self.bot.db.set_stat
        add_to_stat = self.bot.db.add_to_stat

        get_pref = self.bot.db.get_pref

        _ = self.bot._
        diag_slowness(now, ctx, "Got some utils functions")

        language = await get_pref(channel, "language")

        diag_slowness(now, ctx, "Got language")


        # Long and complicated function.
        # Broken in a few parts :
        #
        # 1/ Pre-bang checks : can the user shoot ? Will he miss ?
        # 2/ Deer finding : what deer will the user shoot ? What's the exp cost ? Removing it from the deer_spawned
        # 3/ Bushes : Finding random objects after having killed the deer

        # > Pre-bang checks < #

        # 1/ Is the user wet ?
        mouille = await get_stat(channel, author, "mouille")
        if mouille > int(now):
            await self.bot.send_message(ctx=ctx, message=_(
                "Your clothes are wet, you can't go hunting! Wait {temps_restant} minutes.", language).format(
                **{"temps_restant": int((mouille - int(time.time())) / 60)}))
            await add_to_stat(channel, author, "shoots_tried_while_wet", 1)
            return

        diag_slowness(now, ctx, "Check user wet")

        # 2/ Do he have a weapon ?
        if await get_stat(channel, author, "confisque"):
            await self.bot.send_message(ctx=ctx, message=_("You don't have a weapon.", language))
            await add_to_stat(channel, author, "shoots_without_weapon", 1)
            return

        diag_slowness(now, ctx, "Check weapon")

        # 3/ Is the weapon jammed ?
        if await get_stat(channel, author, "enrayee"):
            await self.bot.send_message(ctx=ctx,
                                        message=_("Your weapon is jammed, it must be reloaded to unjam it.", language))
            await add_to_stat(channel, author, "shoots_with_jammed_weapon", 1)
            return

        diag_slowness(now, ctx, "Check jam")

        # 4/ Is the weapon sabotaged ?
        sabotaged_by = await get_stat(channel, author, "sabotee")
        if sabotaged_by != "-":
            await self.bot.send_message(ctx=ctx,
                                        message=_("Your weapon is sabotaged, thank {assaillant} for this bad joke.",
                                                  language).format(**{"assaillant": sabotaged_by}))

            await add_to_stat(channel, author, "shoots_sabotaged", 1)
            await set_stat(channel, author, "enrayee", True)
            await set_stat(channel, author, "sabotee", "-")
            return

        diag_slowness(now, ctx, "Check sabotage")

        # 5/ Do he have bullets ?
        bullets = await get_stat(channel, author, "balles")
        if bullets <= 0:  # No more bullets in charger
            await self.bot.send_message(ctx=ctx, message=_("** MAGAZINE EMPTY ** | "
                                                           "Ammunition in the weapon: {balles_actuelles} / {balles_max} | "
                                                           "Magazines remaining: {chargeurs_actuels} / {chargeurs_max}",
                                                           language).format(
                **{"balles_actuelles": bullets, "balles_max": level["balles"],
                   "chargeurs_actuels": await get_stat(channel, author, "chargeurs"),
                   "chargeurs_max": level["chargeurs"]}))
            await add_to_stat(channel, author, "shoots_without_bullets", 1)
            return

        diag_slowness(now, ctx, "Check bullets")

        # Now, we are sure that the user can shoot.
        # We'll see if he misses.
        # 6/ Weapon fiability - jamming
        fiability = level["fiabilitee"]

        # 6a/ Sand
        if await get_stat(channel, author, "sand"):
            fiability /= 2
            await set_stat(channel, author, "sand", False)

        diag_slowness(now, ctx, "Check sand")

        # 6b/ Chance computing
        chance = random.randint(0, 100)

        can_shoot = chance <= fiability
        can_shoot = can_shoot or await get_stat(channel, message.author, "graisse") > time.time()

        diag_slowness(now, ctx, "Compute chance")

        # 6c/ Jamming
        if not can_shoot:
            await self.bot.send_message(ctx=ctx, message=_("Your weapon just jammed, reload it to unjam it.", language))
            await add_to_stat(channel, author, "shoots_jamming_weapon", 1)
            await set_stat(channel, author, "enrayee", True)
            return

        diag_slowness(now, ctx, "Check jamming")

        # > Deer Finding < #

        # 7/ Is there a deer on the channel ?


        for deer in self.bot.deer_spawned:
            if deer.channel == channel and not deer.killed:
                # Yes! There is a deer here!
                current_deer = deer
                diag_slowness(now, ctx, "Found deer")
                break

        else:
            diag_slowness(now, ctx, "No deer")
            # No! There is no deer in there!
            if await self.bot.db.get_stat(message.channel, message.author,
                                          "detecteurInfra") > time.time() and await get_stat(channel, author,
                                                                                             "detecteur_infra_shots_left") > 0:
                # Infrared detector : No bullets wasted
                await self.bot.send_message(ctx=ctx,
                                            message=_(
                                                "There isn't any deer in here, but the bullet wasn't fired because the infrared detector you added to your weapon is doing its job!",
                                                language))
                diag_slowness(now, ctx, "Sent infrared message")
                await add_to_stat(channel, author, "shoots_infrared_detector", 1)
                await add_to_stat(channel, author, "detecteur_infra_shots_left", -1)
                diag_slowness(now, ctx, "Saved infrared detect stats")
                return
            else:
                # No infrared detector, no deer, we'll loose a bullet AND experience.
                await add_to_stat(channel, author, "balles", -1)
                await add_to_stat(channel, author, "shoots_fired", 1)
                await add_to_stat(channel, author, "exp", -2)
                await add_to_stat(channel, author, "shoots_no_deer", 1)
                diag_slowness(now, ctx, "Wasted bullets")
                await self.sendBangMessage(ctx, _(
                    "Luckily you missed, but what were you aiming at exactly? There isn't any deer in here... [missed: -1 xp] [wild shot: -1 xp]",
                    language))
                diag_slowness(now, ctx, "Sent no deer message")
                # TODO : kill people here too ?
                return

        # Now that we have the deer, We'll use a warpper to ease up the syntax for the rest of this function
        deer_wrapper = DeerWrapper(current_deer, ctx)
        diag_slowness(now, ctx, "Wrapped deer")

        # 8/ Bullet fired
        await add_to_stat(channel, author, "balles", -1)
        await add_to_stat(channel, author, "shoots_fired", 1)
        diag_slowness(now, ctx, "Saved shot stats")

        # 9/ Will the deer stay ?
        chance = random.randint(0, 100)
        deer_will_leave = chance < await deer.get_frighten_chance()
        deer_will_leave = deer_will_leave and not await get_stat(channel, author, "silencieux") > time.time()

        if deer_will_leave:
            await self.sendBangMessage(ctx, await deer_wrapper.frightened())
            return
        diag_slowness(now, ctx, "Deer didn't leave")

        # 10/ Will the deer be shot ?

        # 10a/ Base accuracy
        # Let's start with the base-accuracy of the hunter
        accuracy = level["precision"]

        # 10b/ Dazzling
        if await get_stat(channel, author, "dazzled"):
            accuracy /= 2
            await set_stat(channel, author, "dazzled", False)

        diag_slowness(now, ctx, "Check dazzled")

        # 10c/ Sight on weapon
        sight = await get_stat(channel, author, "sight")
        if sight:
            accuracy += max((100 - accuracy) / 3,
                            0)  # To ensure no negativity even if it shouldn't happen (but maybe because of an event or something that will be added later)
            await set_stat(channel, author, "sight", sight - 1)

        diag_slowness(now, ctx, "Check sight")

        # 10d/ Chance (will need to be smaller than accuracy to shoot properly)
        chance = random.randint(0, 100)
        if ctx.bot.current_event['id'] == 8:
            chance += ctx.bot.current_event['miss_chance_to_add']

        diag_slowness(now, ctx, "Got event")

        # 10e/ Miss_chance multiplier
        miss_multiplier = await get_pref(channel, "multiplier_miss_chance")
        chance *= miss_multiplier

        if target:
            await add_to_stat(channel, author, "murders", 1)

        diag_slowness(now, ctx, "Got multiplier")

        # 11/ Deer missed

        if (chance > accuracy and deer.can_miss) or target:
            diag_slowness(now, ctx, "Deer missed")

            kill_on_miss_chance = await get_pref(channel, "chance_to_kill_on_missed")
            chance_kill = random.randint(0, 100)

            if target:
                chance_kill = kill_on_miss_chance - 1  # Force killing

            if ctx.bot.current_event['id'] == 4:
                chance_kill -= ctx.bot.current_event['kill_chance_added']

            if chance_kill < kill_on_miss_chance:
                # 11a/ Bad luck. We killed someone too.
                await add_to_stat(channel, author, "exp", -3)
                await add_to_stat(channel, author, "shoots_missed", 1)
                await add_to_stat(channel, author, "killed_players", 1)
                await set_stat(channel, author, "confisque", True)
                diag_slowness(now, ctx, "Killed someone saved")

                if not target:

                    online_players = [p for p in guild.members if
                                      p.status in [discord.Status.online, discord.Status.idle, discord.Status.dnd]]
                    online_players += guild.members if len(online_players) <= 5 else [author]
                    try:
                        online_players.remove(guild.me)
                    except ValueError:
                        # Who cares if we are not in the list :)
                        pass

                    # Double the chances of the author being selected, and add every possible member if we see less than 5 of them online

                    player_killed = random.choice(online_players)
                    diag_slowness(now, ctx, "Computed target for murder")

                else:
                    player_killed = target

                if player_killed == author:
                    # 11b/ How unlucky can you be ? You shot yourself!
                    await add_to_stat(channel, author, "self_killing_shoots", 1)
                    await self.sendBangMessage(ctx, _(
                        "**BANG**\tYou missed the deer... and shot **yourself**! Maybe you should turn your weapon a little before shooting the next time? "
                        "[missed: -1 xp] [hunting accident: -2 xp] [**weapon confiscated**]", language))
                    diag_slowness(now, ctx, "Sent self kill message")

                else:
                    # 11c/ Just shot someone else
                    await self.sendBangMessage(ctx, _(
                        "**BANG**\tYou missed the deer... and shot {player}! [missed: -1 xp] [hunting accident: -2 xp] [**weapon confiscated**]",
                        language).format(
                        **{"player": player_killed.mention if await get_pref(channel,
                                                                             "killed_mentions") else player_killed.name}))
                    diag_slowness(now, ctx, "Sent someone killed message")

                    # TODO : Life insurence

                await self.bot.hint(ctx=ctx, message=_("You can buy your weapon back in the store (`dh!shop 5`) "
                                                       "or wait until you get it back for free (check when with `!freetime`)",
                                                       language))
                diag_slowness(now, ctx, "Sent hint")
                return
            else:  # Missed and none was shot
                await add_to_stat(channel, author, "exp", -1)
                await add_to_stat(channel, author, "shoots_missed", 1)
                await self.sendBangMessage(ctx, _("**PIEWW**\tYou missed the deer! [missed: -1 xp]", language))
                diag_slowness(now, ctx, "Sent missed")
                return

        diag_slowness(now, ctx, "SHOOTING")
        await self.sendBangMessage(ctx, await deer_wrapper.shoot())

        # > Bushes < #

        # TODO : Stockage des items trouvés et les afficher

    @commands.command(aliases=["calin", "<3", ":heart:", "wizzz"])
    @checks.is_channel_enabled()
    @checks.had_giveback()
    async def hug(self, ctx, target: discord.Member = None):

        message = ctx.message
        channel = message.channel
        author = message.author
        guild = message.guild

        # Coroutines
        add_to_stat = self.bot.db.add_to_stat

        get_pref = self.bot.db.get_pref

        _ = self.bot._
        language = await get_pref(channel, "language")

        if target:
            await add_to_stat(channel, author, "hugs_human", 1)
            await self.bot.send_message(ctx=ctx,
                                        message=_(
                                            "You hugged {mention} as strongly as you could. They are filled with determination.",
                                            language).format(mention=target.mention))
            return

        for deer in self.bot.deer_spawned:
            if deer.channel == channel and not deer.killed:
                current_deer = deer
                break
        else:
            await add_to_stat(channel, author, "hugs_no_deer", 1)
            if author.id == 296573428293697536:  # ⚜WistfulWizzz⚜#5928
                await self.bot.send_message(ctx=ctx,
                                            message=_("You hugged a tree, Wizzz?!", language))
            else:
                await self.bot.send_message(ctx=ctx,
                                            message=_(
                                                "There isn't any deer in here, what did you plan to hug, a tree?!",
                                                language))

            return

        await add_to_stat(channel, author, "hugs", 1)

        await self.bot.send_message(ctx=ctx, message=await current_deer.hug(ctx))

    @commands.command(aliases=["currentevent", "event", "events"])
    @checks.is_channel_enabled()
    async def current_event(self, ctx):
        _ = self.bot._
        language = await self.bot.db.get_pref(ctx.channel, "language")
        event = ctx.bot.current_event
        ce = _('**Current event**', language)
        string = f"""{ce} :\n{_(event['name'], language)} — {_(event['description'], language)}"""
        await self.bot.send_message(ctx=ctx, message=string)


def setup(bot):
    bot.add_cog(User(bot))
