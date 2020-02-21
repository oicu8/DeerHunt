import discord
from discord.ext import commands
from discord.ext.commands import BucketType

from cogs.helpers import checks
from cogs import spawning
import argparse
import tabulate

from cogs.helpers import deer


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, aliases=['gameban'])
    @checks.is_server_admin()
    @checks.is_channel_enabled()
    async def game_ban(self, ctx, member: discord.Member):
        """Ban someone from the bot on the current channel
        !game_ban [member]"""
        _ = self.bot._
        language = await self.bot.db.get_pref(ctx.channel, "language")

        await self.bot.db.set_stat(ctx.channel, member, "banned", True)
        await self.bot.send_message(ctx=ctx, message=_(":ok: Done, user banned. :gun:", language))

    @commands.command(pass_context=True, aliases=['gameunban'])
    @checks.is_server_admin()
    @checks.is_channel_enabled()
    async def game_unban(self, ctx, member: discord.Member):
        """Unban someone from the bot on the current channel
        !game_unban [member]"""
        _ = self.bot._
        language = await self.bot.db.get_pref(ctx.channel, "language")

        await self.bot.db.set_stat(ctx.channel, member, "banned", False)
        await self.bot.send_message(ctx=ctx, message=_(":ok: Done, user unbanned. :eyes:", language))

    @commands.command(aliases=["planning", "deer_planning", "deerplanning"])
    @checks.is_server_admin()
    @checks.is_channel_enabled()
    @commands.cooldown(1, 120, BucketType.channel)
    async def deer(self, ctx):
        topr = ""
        for deer in self.bot.deer_spawned:
            if deer.channel == ctx.channel:
                topr += str(deer) + "\n"

        if topr == "":
            topr = "No deer on channel \n"

        topr += f"And {self.bot.deer_planning[ctx.channel]} deer left to spawn today"

        await self.bot.send_message(ctx=ctx, message=topr, force_pm=True)

    @commands.command(aliases=["add_channel", "addchannel"])
    @checks.is_server_admin()
    async def enable_channel(self, ctx):
        _ = self.bot._
        language = await self.bot.db.get_pref(ctx.channel, "language")
        await ctx.bot.db.enable_channel(ctx.channel)
        await spawning.planifie(self.bot, ctx.channel, new_day=False)
        await self.bot.send_message(ctx=ctx, message=_("<:cmd_ChannelAdded_01:439546719143723019> Done, channel {channel} added to the game! Have fun!", language).format(**{"channel": ctx.channel.mention}))

    @commands.command(aliases=["del_channel", "delchannel"])
    @checks.is_server_admin()
    @checks.is_channel_enabled()
    async def disable_channel(self, ctx):
        _ = self.bot._
        language = await self.bot.db.get_pref(ctx.channel, "language")
        await ctx.bot.db.disable_channel(ctx.channel)

        self.bot.deer_planning.pop(ctx.channel, None)

        for deer in self.bot.deer_spawned[:]:
            if deer.channel == ctx.channel:
                deer.delete()

        await self.bot.send_message(ctx=ctx, message=_("<:cmd_ChannelRemoved_01:439546718737137674> Done, channel {channel} removed from the game. Bye!", language).format(**{"channel": ctx.channel.mention}))
        await self.bot.hint(ctx=ctx, message="This does not remove the scores. Use `dh!removeallscoresandstatsonthischannel` to remove them.")

    @commands.command(aliases=["addadmin"])
    @checks.is_server_admin()
    async def add_admin(self, ctx, new_admin: discord.Member):
        _ = self.bot._
        language = await self.bot.db.get_pref(ctx.channel, "language")
        await ctx.bot.db.add_admin(ctx.guild, new_admin)
        await self.bot.send_message(ctx=ctx, message=_("<:cmd_AdminAdded_01:439549846622568466> {admin} added as an admin to the guild!", language).format(**{"admin": new_admin.mention}))

    @commands.command(aliases=["deladmin"])
    @checks.is_server_admin()
    async def del_admin(self, ctx, old_admin: discord.Member):
        _ = self.bot._;
        language = await self.bot.db.get_pref(ctx.channel, "language")
        await ctx.bot.db.del_admin(ctx.guild, old_admin)
        await self.bot.send_message(ctx=ctx, message=_("<:cmd_AdminRemoved_01:439549845519335440> {admin} removed from the guild admins.", language).format(**{"admin": old_admin.mention}))

    @commands.command(aliases=["spawndeer", "coin"])
    @checks.is_server_admin()
    @checks.is_channel_enabled()
    @commands.cooldown(5, 30, BucketType.guild)
    async def spawn_deer(self, ctx, *, args: str = ""):
        args = args.replace("—", "--")  #Fix for mobile users
        args = args.split()
        parser = argparse.ArgumentParser(description='Parse the spawn deer command.')
        parser.add_argument('--super-deer', dest='super_deer', action='store_true', help='Is the deer a super deer ?')
        parser.add_argument('--baby-deer', dest='baby_deer', action='store_true', help='Is the deer a baby deer ?')
        parser.add_argument('--moad', dest='moad', action='store_true', help='Is the deer a moad ?')
        parser.add_argument('--life', dest='life', type=int, default=1)

        try:
            args = parser.parse_args(args)
        except SystemExit:
            await self.bot.hint(ctx=ctx, message=f"You have to use `--super-deer`, `--baby-deer`, `--moad` & `--life X` here.\n For example `{ctx.prefix}coin --super-deer --life 4` for a super deer "
            f"with 4 HP")
            return

        if args.baby_deer:
            type = deer.BabyDeer
        elif args.super_deer:
            type = deer.SuperDeer
        elif args.moad:
            type = deer.MotherOfAllDeer
        else:
            type = deer.Deer

        deer = await type.create(self.bot, ctx.channel, life=args.life)

        await spawning.spawn_deer(self.bot, ctx.channel, instance=deer)

    @commands.command(aliases=["reset_user"])
    @checks.is_server_admin()
    @checks.is_channel_enabled()
    @commands.cooldown(1, 20, BucketType.guild)
    async def del_user(self, ctx, user: discord.Member):
        _ = self.bot._;
        language = await self.bot.db.get_pref(ctx.channel, "language")

        await ctx.bot.db.delete_stats(ctx.channel, user=user)

        await self.bot.send_message(ctx=ctx, message=_("Done. User removed from the database, if he was in.", language))
        await self.bot.hint(ctx=ctx, message="You can delete a user that left if you have his ID. Use `dh!del_user_id`")

    @commands.command(
        aliases=["remove_all_scores_and_stats_on_this_channel", "remove_scores_and_stats_on_this_channel", "delete_all_scores_and_stats_on_this_channel", "delete_scores_and_stats_on_this_channel"])
    @checks.is_server_admin()
    @commands.cooldown(1, 20, BucketType.guild)
    async def removeallscoresandstatsonthischannel(self, ctx):
        _ = self.bot._;
        language = await self.bot.db.get_pref(ctx.channel, "language")

        await ctx.bot.db.delete_channel_stats(ctx.channel)

        await self.bot.send_message(ctx=ctx, message=_("Done. All channel data was removed.", language))
        await self.bot.hint(ctx=ctx, message="This does not stop the game. Use `dh!remove_channel` to stop it.")

    @commands.command(aliases=["reset_user_id"])
    @checks.is_channel_enabled()
    @checks.is_server_admin()
    @commands.cooldown(1, 20, BucketType.guild)
    async def del_user_id(self, ctx, user_to_delete_id: int):

        _ = self.bot._;
        language = await self.bot.db.get_pref(ctx.channel, "language")

        await ctx.bot.db.delete_stats(ctx.channel, user_id=user_to_delete_id)
        await self.bot.send_message(ctx=ctx, message=_("Done. User removed from the database, if he was in.", language))

    # > SETTINGS < #

    @commands.group()
    @checks.is_channel_enabled()

    async def settings(self, ctx):
        _ = self.bot._;
        language = await self.bot.db.get_pref(ctx.channel, "language")

        if not ctx.invoked_subcommand:
            await self.bot.send_message(ctx=ctx, message=_(":x: Incorrect syntax. Use the command this way: `!settings [view/set/reset] [setting]`", language))

    @settings.command(name='view')
    @commands.cooldown(5, 20, BucketType.guild)
    async def settings_get(self, ctx, pref: str):
        """!settings get"""
        _ = self.bot._
        language = await self.bot.db.get_pref(ctx.channel, "language")

        if pref not in self.bot.db.settings_dict.keys():
            await self.bot.send_message(ctx=ctx, message=_("Unknown setting...", language))
            return

        await self.bot.send_message(ctx=ctx, message=_(":ok: The setting {pref} is set to `{value}` on this guild.", language).format(
            **{"value": await self.bot.db.get_pref(ctx.message.channel, pref), "pref": pref}))

    @settings.command(name='set')
    @commands.cooldown(5, 20, BucketType.guild)
    @checks.is_server_admin()
    async def settings_set(self, ctx, pref: str, value: str):
        """!settings set"""
        _ = self.bot._;
        language = await self.bot.db.get_pref(ctx.channel, "language")

        if pref not in self.bot.db.settings_dict.keys():
            await self.bot.send_message(ctx=ctx, message=_("Unknown setting...", language))
            return

        # Special cases
        try:
            if pref == "deer_per_day":
                maxCJ = int(125 + (ctx.message.guild.member_count / (5 + (ctx.message.guild.member_count / 300))))
                if int(value) > maxCJ:
                    if ctx.message.author.id in self.bot.admins:
                        await self.bot.send_message(ctx=ctx,
                                                    message=_("Bypassing the max_deer_per_day check as you are the bot owner. It would have been `{max}`.", language).format(**{"max": maxCJ}))
                    elif await self.bot.db.get_pref(ctx.channel, "vip"):
                        await self.bot.send_message(ctx=ctx, message=_(
                            "Bypassing the max_deer_per_day check as you are in a VIP guild. Please don't abuse that. For information, the limit would have been set at `{max}` deer per day.",
                            language).format(**{"max": maxCJ}))
                    else:
                        value = maxCJ

            elif pref == "vip":
                if ctx.message.author.id in self.bot.admins:
                    await self.bot.send_message(ctx=ctx, message=_("<:official_Deer_01_reversed:439576463436546050> Authorised to set the VIP status!", language))
                else:
                    await self.bot.send_message(ctx=ctx, message=_(":x: Unauthorised to set the VIP status! You are not an owner.", language))
                    return False
            elif pref == "time_before_deer_leave":
                if int(value) > 3600:
                    value = 3600
        except (ValueError, TypeError):
            await self.bot.send_message(ctx=ctx, message=_(":x: Incorrect value.", language))
            return False

        if await self.bot.db.set_pref(ctx.message.channel, pref=pref, value=value):
            if pref == "deer_per_day":
                await spawning.planifie(self.bot, channel=ctx.message.channel, new_day=False)

            await self.bot.send_message(ctx=ctx, message=_(":ok: The setting {pref} has been set to `{value}` on this guild.", language).format(
                **{"value": await self.bot.db.get_pref(ctx.message.channel, pref), "pref": pref}))
            return True
        else:
            await self.bot.send_message(ctx=ctx, message=_(":x: Incorrect value.", language))
            return False

    @settings.command(name='reset')
    @commands.cooldown(5, 20, BucketType.guild)
    @checks.is_server_admin()
    async def settings_reset(self, ctx, pref: str):
        """!settings reset"""
        _ = self.bot._;
        language = await self.bot.db.get_pref(ctx.channel, "language")

        if pref not in self.bot.db.settings_dict.keys():
            await self.bot.send_message(ctx=ctx, message=_("Unknown setting...", language))
            return

        value = self.bot.db.settings_dict[pref]["Default"]

        if await self.bot.db.set_pref(ctx.message.channel, pref=pref, value=value):
            if pref == "deer_per_day":
                await spawning.planifie(self.bot, channel=ctx.message.channel, new_day=False)

            await self.bot.send_message(ctx=ctx, message=_(":ok: The setting {pref} has been set to `{value}` on this guild.", language).format(
                **{"value": await self.bot.db.get_pref(ctx.message.channel, pref), "pref": pref}))
            return True
        else:
            await self.bot.send_message(ctx=ctx, message=_(":x: Incorrect value.", language))
            return False



def setup(bot):
    bot.add_cog(Admin(bot))
