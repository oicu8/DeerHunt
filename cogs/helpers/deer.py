"""
In this helper, every kind of deer the bot can spawn is defined.
"""
#from datetime import datetime, timedelta, timezone
import datetime

import dateutil.parser

import logging
import random
import time
MINUTE = 60
HOUR = MINUTE * 60
DAY = HOUR * 24

# That function is here to mark items as "to be translated"
import dateutil.easter


def _(string):
    return string


class BushObject:
    name = None
    db = 'trashFound'

    async def give(self, bot, ctx):
        """
        Try and give the item if possible, then returns True. If not possible (invetory full), return False
        """
        return True


class Nothing(BushObject):
    name = _('Nothing')


class Bushes(BushObject):
    name = _('a lot of bushes.')

class DeerPin(BushObject):
    name = _('a deer pin.')


class Bullet(BushObject):
    name = _('a bullet')
    db = 'found_bullets'

    async def give(self, bot, ctx):
        if await bot.db.get_stat(ctx.message.channel, ctx.message.author, "balles") < (await bot.db.get_level(channel=ctx.message.channel, player=ctx.message.author))["balles"]:
            await bot.db.add_to_stat(ctx.message.channel, ctx.message.author, "balles", 1)
            return True
        else:
            return False


class Charger(BushObject):
    name = _('a full magazine')
    db = 'found_chargers'

    async def give(self, bot, ctx):
        if await bot.db.get_stat(ctx.message.channel, ctx.message.author, "chargeurs") < (await bot.db.get_level(channel=ctx.message.channel, player=ctx.message.author))["chargeurs"]:
            await bot.db.add_to_stat(ctx.message.channel, ctx.message.author, "chargeurs", 1)
            return True
        else:
            return False


class ExplosiveAmmo(BushObject):
    name = _('a box of explosive ammo')
    db = 'found_explosive_ammo'

    async def give(self, bot, ctx):
        current = await bot.db.get_stat(ctx.message.channel, ctx.message.author, "explosive_ammo")
        if current < int(time.time() + 86400):
            await bot.db.set_stat(ctx.message.channel, ctx.message.author, "explosive_ammo", int(time.time() + 86400))
        else:
            await bot.db.set_stat(ctx.message.channel, ctx.message.author, "explosive_ammo", int(current + 86400))
        return True


class PartialExplosiveAmmo(BushObject):
    name = _('an almost empty box of explosive ammo')
    db = 'found_almost_empty_explosive_ammo'

    async def give(self, bot, ctx):
        current = await bot.db.get_stat(ctx.message.channel, ctx.message.author, "explosive_ammo")
        if current < int(time.time() + 86400 / 4):
            await bot.db.set_stat(ctx.message.channel, ctx.message.author, "explosive_ammo", int(time.time() + 86400 / 4))
        else:
            await bot.db.set_stat(ctx.message.channel, ctx.message.author, "explosive_ammo", int(current + 86400 / 4))

        return True


class Grease(BushObject):
    name = _('some deer-grease')
    db = 'found_grease'

    async def give(self, bot, ctx):
        await bot.db.set_stat(ctx.message.channel, ctx.message.author, "graisse", time.time() + DAY)
        return True


class Silencer(BushObject):
    name = _('a full-featured silencer')
    db = 'found_silencers'

    async def give(self, bot, ctx):
        await bot.db.set_stat(ctx.message.channel, ctx.message.author, "silencieux", time.time() + DAY)
        return True


class InfraredDetector(BushObject):
    name = _('a fully functional infrared detector')
    db = 'found_infrared_detectors'

    async def give(self, bot, ctx):
        await bot.db.set_stat(ctx.message.channel, ctx.message.author, "detecteurInfra", time.time() + DAY)
        await bot.db.set_stat(ctx.message.channel, ctx.message.author, "detecteur_infra_shots_left", 6)
        return True
del _

# noinspection PyInterpreter
bushes = {
    Nothing: 20, Bushes: 20, DeerPin: 1,
    Bullet: 20,
    Charger: 15,
    ExplosiveAmmo: 2, PartialExplosiveAmmo: 6,
    Grease: 15,
    Silencer: 7,
    InfraredDetector: 7,
 }


bushes_objects = []
bushes_weights = []

for object_, weight in bushes.items():
    bushes_objects.append(object_)
    bushes_weights.append(weight)


class DeerWrapper:
    """Class used to pass a player as an argument to some deer functions in user_commands.py"""

    def __init__(self, deer, ctx):
        self.deer = deer
        self.ctx = ctx
        self.shooter = ctx.author

    def __getattr__(self, name, *args, **kwargs):
        """ In case we can't see the function, redirect to the deer object"""
        return getattr(self.deer, name)(self, *args, **kwargs)

    async def frightened(self):
        return await self.deer.frightened(self.shooter)

    async def shoot(self):
        return await self.deer.shoot(self.ctx)


class BaseDeer:
    """
    Just a dummy deer type to highlight the required values a Deer subclass must provide
    """

    def __init__(self, bot, channel):

        self.bot = bot
        self.channel = channel

        self._logger = None

        self.starting_life = 1
        self.life = 1

        self.spawned_at = int(time.time())

        # Optional settings that probably won't get changed often
        self.can_miss = True
        self.can_use_clover = True

        # Dummy values that should be replaced... Probably
        self.exp_value = 0
        self.staying_until = self.spawned_at
        self.discord_spawn_str = "-,_,.-'\`'°-,_,.-'\`'° \\_O< COIN"
        self.discord_leave_str = "·°'\`'°-.,¸¸.·°'\`"

        self.logger.debug(f"{self.__class__.__name__} created -> {self}")

    @property
    def logger(self):
        if not self._logger:
            extra = {"channelid": self.channel.id, "userid": 0}
            self._logger = logging.LoggerAdapter(self.bot.base_logger, extra)

        return self._logger

    @property
    def killed(self):
        if self.life <= 0:
            return True
        else:
            return False

    @property
    def time(self):
        return self.spawned_at

    @classmethod
    async def create(cls, bot, channel, life=None, ignore_event=False):
        raise RuntimeError("Trying to create an instance of BaseDeer, or subclass not re-implementing create")

    def delete(self):
        self.bot.deer_spawned.remove(self)

    async def frightened(self, player):
        _ = self.bot._
        language = await self.bot.db.get_pref(self.channel, "language")

        await self.bot.db.add_to_stat(self.channel, player, "exp", -1)
        try:
            self.delete()
        except ValueError:
            # Deer was removed elsewhere (race condition)
            # Just be like, yup, you missed
            await self.bot.db.add_to_stat(self.channel, player, "shoots_missed", 1)
            return _("**PIEWW**\tYou missed the deer! [missed: -1 xp]", language)

        await self.bot.db.add_to_stat(self.channel, player, "shoots_frightened", 1)
        return _("**FLAPP**\tFrightened by so much noise, the deer fled! CONGRATS! [missed: -1 xp]", language)

    async def _process_super_ammo(self, author):
        channel = self.channel
        now = time.time()
        _ = self.bot._
        language = await self.bot.db.get_pref(self.channel, "language")

        if await self.bot.db.get_stat(channel, author, "explosive_ammo") > int(now):
            self.life -= 3
            vieenmoins = 3
            ono = _("BPAM", language)
        elif await self.bot.db.get_stat(channel, author, "ap_ammo") > int(now):
            self.life -= 2
            vieenmoins = 2
            ono = _("BAAM", language)
        else:
            self.life -= 1
            vieenmoins = 1
            ono = random.choice([_("BOUM", language), _("SPROTCH", language)])

        return vieenmoins, ono

    async def _get_experience_spent(self, author):
        channel = self.channel
        now = time.time()

        # 13a/ Experience
        exp = self.exp_value

        # 13b/ Clover
        trefle = 0
        if await self.bot.db.get_stat(channel, author, "trefle") > now and self.can_use_clover:
            trefle = await self.bot.db.get_stat(channel, author, "trefle_exp")
            await self.bot.db.add_to_stat(channel, author, "exp_won_with_clover", trefle)
            exp += trefle

        # 13c/ Rounding experience
        return int(exp), trefle

    async def _update_best_time_taken(self, author):
        now = time.time()

        # 13e/ Best time
        time_taken = round(now - self.time, 6)
        if await self.bot.db.get_stat(self.channel, author, "best_time") > time_taken:
            await self.bot.db.set_stat(self.channel, author, "best_time", time_taken)

        return time_taken

    async def pre_shoot(self, author):
        pass

    async def _bushes(self, ctx):
        if random.randint(0, 5) == 1:
            choosen = random.choices(bushes_objects, bushes_weights)[0]()
            result = await choosen.give(ctx.bot, ctx)

            ctx.logger.info("Found in bushes : " + choosen.name)

            if choosen.db:
                db_name = choosen.db
                if not result:
                    db_name += '_not_taken'

                await ctx.bot.db.add_to_stat(ctx.message.channel, ctx.message.author, db_name, 1)

            _ = self.bot._
            language = await self.bot.db.get_pref(ctx.channel, "language")

            if result:
                await self.bot.send_message(ctx=ctx, message=(_("Searching the bushes around the deer, you found...", language) + "**" + _(choosen.name, language) + "**"))
            else:
                await self.bot.send_message(ctx=ctx, message=(
                        _("Searching the bushes around the deer, you found...", language) + "**" + choosen.name + "**, " + _("that you unfortunately couldn't take, because your backpack is full.",
                                                                                                                             language)))

    async def post_kill(self, ctx, exp):
        await self._bushes(ctx)
        pass

    async def post_harmed(self, author):
        # Harmed but not killed
        await self.bot.db.add_to_stat(self.channel, author, "shoots_harmed_deer", 1)

    async def shoot(self, ctx):
        author = ctx.author
        channel = self.channel
        _ = self.bot._
        language = await self.bot.db.get_pref(self.channel, "language")

        await self.pre_shoot(author)

        # 12/ Super ammo
        vieenmoins, ono = await self._process_super_ammo(author)

        # 13/ Deer killed ?
        if self.killed:
            try:
                self.delete()
            except ValueError:
                # Deer was removed elsewhere (race condition)
                # Just be like, yup, you missed
                # It never happen anyway
                # Well, it could but never saw it in real life

                await self.bot.db.add_to_stat(channel, author, "exp", -1)
                await self.bot.db.add_to_stat(channel, author, "shoots_missed", 1)
                await self.bot.db.add_to_stat(channel, author, "shoots_almost_killed", 1)
                return _("That was close, you almost killed the deer, but the other hunter got it first! [missed: -1 xp]", language)

            exp, trefle = await self._get_experience_spent(author)
            # 13d/ Give experience
            await self.bot.db.add_to_stat(channel, author, "exp", exp)
            await self.bot.db.add_to_stat(channel, author, "killed_deer", 1)

            time_taken = await self._update_best_time_taken(author)

            # 13f/ Communicate

            if trefle == 0:
                exp_str = f"[{exp} exp]"
            else:
                exp_str = f"[{exp - trefle} exp + **{trefle} clover**]"

            await self.post_kill(ctx, exp)

            return (await self.get_killed_string()).format(**{"time": round(time_taken, 4), "total": await self.bot.db.get_stat(channel, author, "killed_deer"), "channel": channel.mention, "exp": exp_str,
                                                              "supercanards": await self.bot.db.get_stat(channel, author, "killed_super_deer"), "onomatopoeia": ono})

        else:
            await self.post_harmed(author)

            return (await self.get_harmed_message()).format(**{"vie": vieenmoins, "current_life": self.life, "max_life": self.starting_life})

    async def hug(self, ctx):

        author = ctx.author
        _ = self.bot._
        language = await self.bot.db.get_pref(self.channel, "language")
        await self.bot.db.add_to_stat(self.channel, author, "hugged_nohug_deer", 1)

        if author.id == 296573428293697536:  # ⚜WistfulWizzz⚜#5928
            return _("<:Wizzz:365870248554921985> Wizzz huggy deery!", language)

        await self.bot.db.add_to_stat(self.channel, author, "exp", -2)

        if await self.bot.db.get_stat(self.channel, author, "confisque"):
            return _(":heart: You try to hug the deer, but it knows you killed its brother, so it fled from you and jumped back into the woods![-2 exp]", language)
        elif await self.bot.db.get_stat(self.channel, author, "killed_deer") == 0:
            return _(":heart: You try to hug the deer, but it feels someting wrong about you, so it fled from you and jumped back into the woods![-2 exp]", language)
        else:
            return _(":heart: You try to hug the deer, but it saw the weapon you hid behind your back, so it fled from you and jumped back into the woods! [-2 exp]", language)

    async def get_frighten_chance(self):
        return await self.bot.db.get_pref(self.channel, "deer_frighten_chance")

    async def get_killed_string(self):
        _ = self.bot._
        language = await self.bot.db.get_pref(self.channel, "language")

        return _(":skull_crossbones: **{onomatopoeia}**\tYou killed the deer in {time} seconds, you are now at a grand total of {total} deer (of which {supercanards} "
                 "were super-deer) killed on {channel}.     \\_X<   *COUAC*   {exp}", language)

    async def get_harmed_message(self):
        _ = self.bot._
        language = await self.bot.db.get_pref(self.channel, "language")

        if await self.bot.db.get_pref(self.channel, "show_super_deer_life"):
            return _(":gun: The deer survived, try again! *SUPER DEER DETECTED* [life: -{vie} ({current_life} / {max_life})]", language)
        else:
            return _(":gun: The deer survived, try again! *SUPER DEER DETECTED* [life: -{vie}]", language)

    def __repr__(self):
        now = int(time.time())
        return f"{self.__class__.__name__} spawned {now - self.spawned_at} seconds ago on #{self.channel.name} | " \
            f"Life: {self.life} / {self.starting_life}, and an exp value of {self.exp_value}"

    def __str__(self):
        now = int(time.time())
        return f"{self.__class__.__name__} spawned {now - self.spawned_at} seconds ago on #{self.channel.name} @ {self.channel.guild.name} | " \
            f"Life: {self.life} / {self.starting_life}, and an exp value of {self.exp_value}"


class Deer(BaseDeer):
    """
    The common deer, with a life of one that can spawn in the game
    """

    def __init__(self, bot, channel, exp, ttl):
        super().__init__(bot, channel)

        self.staying_until = self.spawned_at + ttl
        self.exp_value = exp

    async def _gen_discord_str(self):
        _ = self.bot._
        language = await self.bot.db.get_pref(self.channel, "language")

        trace = random.choice(self.bot.canards_trace)

        n = datetime.datetime.now()

        april_fools = n.day == 1 and n.month == 4
        easter_eggs = n.date() in [dateutil.easter.easter(n.year), dateutil.easter.easter(n.year) + datetime.timedelta(days=1)]

        if april_fools:
            corps = "🐟"
        elif easter_eggs:
            corps = random.choice(["🐰", "🍫", "🔔", "🧺", "🐝", "🥕", "🌸", "🐇", "🐰"])
        else:
            corps = await self.bot.db.get_pref(self.channel, "emoji_used")

        cri = _(random.choice(self.bot.canards_cri), language=language)

        self.discord_spawn_str = f"{trace} {corps} < {cri}"
        self.discord_leave_str = _(random.choice(self.bot.canards_bye), language)

    @classmethod
    async def create(cls, bot, channel, life=None, ignore_event=False):
        # Base deer time to live
        ttl = await bot.db.get_pref(channel, "time_before_deer_leave")

        # Base deer exp
        exp_value = await bot.db.get_pref(channel, "exp_won_per_deer_killed")

        deer = cls(bot, channel, exp=exp_value, ttl=ttl)
        await deer._gen_discord_str()
        if life:
            deer.life = life
        return deer

    async def post_kill(self, ctx, exp):
        await super().post_kill(ctx, exp)
        author = ctx.message.author

        await self.bot.db.add_to_stat(self.channel, author, "killed_normal_deer", 1)


class SuperDeer(BaseDeer):
    """
    A special deer with more than one life point
    """

    def __init__(self, bot, channel, life, exp, ttl):
        super().__init__(bot, channel)
        self.staying_until = self.spawned_at + ttl
        self.exp_value = exp

        self.life = life
        self.starting_life = life

    async def _gen_discord_str(self):
        # Same as for the Normal Deer because they shouldn't be distinguished

        _ = self.bot._
        language = await self.bot.db.get_pref(self.channel, "language")

        trace = random.choice(self.bot.canards_trace)

        n = datetime.datetime.now()

        april_fools = n.day == 1 and n.month == 4
        easter_eggs = n.date() in [dateutil.easter.easter(n.year), dateutil.easter.easter(n.year) + datetime.timedelta(days=1)]

        if april_fools:
            corps = "🐟"
        elif easter_eggs:
            corps = random.choice(["🐰", "🍫", "🔔", "🧺", "🐝", "🥕", "🌸", "🐇", "🐰"])
        else:
            corps = await self.bot.db.get_pref(self.channel, "emoji_used")

        cri = _(random.choice(self.bot.canards_cri), language=language)

        if self.channel.id == 449726041548783636:  # Deer Enigma
            cri = _(random.choice(self.bot.canards_cri + ["I Really Wanna See You Now", "I Really Wanna See You Now", "I Really Wanna See You Now", "I Really Wanna See You Now"]), language=language)

        self.discord_spawn_str = f"{trace} {corps} < {cri}"
        self.discord_leave_str = _(random.choice(self.bot.canards_bye), language)

    async def post_kill(self, ctx, exp):
        await super().post_kill(ctx, exp)
        author = ctx.message.author
        await self.bot.db.add_to_stat(self.channel, author, "killed_super_deer", 1)

    @classmethod
    async def create(cls, bot, channel, life=None, ignore_event=False):
        # Base deer time to live
        ttl = await bot.db.get_pref(channel, "time_before_deer_leave")

        # Base deer exp
        exp_value = await bot.db.get_pref(channel, "exp_won_per_deer_killed")

        # Super deer life
        min_life = await bot.db.get_pref(channel, "super_deer_minlife")
        max_life = await bot.db.get_pref(channel, "super_deer_maxlife")

        # Choosen life for this one
        if life is None:
            life = random.randint(min(min_life, max_life), max(min_life, max_life))
            if not ignore_event and bot.current_event['id'] == 7:
                life += bot.current_event['life_to_add']

        # Choosen exp for this life
        exp_value = int(exp_value * await bot.db.get_pref(channel, "super_deer_exp_multiplier") * life)

        deer = cls(bot, channel, life=life, exp=exp_value, ttl=ttl)
        await deer._gen_discord_str()

        return deer


class MechanicalDeer(BaseDeer):
    """
    Special deer "already killed" just to troll other hunters
    """

    def __init__(self, bot, channel, ttl=30, user=None):
        self.user = user
        super().__init__(bot, channel)
        self.life = 1
        self.exp_value = -1
        self.staying_until = self.spawned_at + ttl
        self.can_miss = False
        self.can_use_clover = False

    @property
    def user_name(self):
        if self.user:
            return self.user.name + "#" + self.user.discriminator
        else:
            return None

    @property
    def user_mention(self):
        if self.user:
            return self.user.mention
        else:
            return None

    async def _gen_discord_str(self):

        _ = self.bot._
        language = await self.bot.db.get_pref(self.channel, "language")
        guild = self.channel.guild

        trace = random.choice(self.bot.canards_trace) if await self.bot.db.get_pref(self.channel, "randomize_mechanical_deer") >= 1 else "-_-'\`'°-_-.-'\`'°"
        corps = await self.bot.db.get_pref(self.channel, "emoji_used") if await self.bot.db.get_pref(self.channel, "randomize_mechanical_deer") >= 2 else await self.bot.db.get_pref(
            self.channel, "emoji_used")  # TODO : Insert here a proper Mechanical Deer Emoji!
        cri = _(random.choice(self.bot.canards_cri), language=language) if await self.bot.db.get_pref(self.channel, "randomize_mechanical_deer") >= 3 else "*BZAACK*"

        self.discord_spawn_str = f"{trace} {corps} < {cri}"

        self.discord_leave_str = None

    @classmethod
    async def create(cls, bot, channel, life=None, ignore_event=False, user=None):
        deer = cls(bot, channel, user=user)
        await deer._gen_discord_str()
        if life:
            deer.life = life
        return deer

    async def get_killed_string(self):
        _ = self.bot._
        language = await self.bot.db.get_pref(self.channel, "language")

        return _("You have been tricked by {user_mention} to kill a mechanical deer. It obviously won't work, and you lost 1 exp for this missed shot", language).format(user_mention=self.user_mention)

    async def get_frighten_chance(self):
        return 0

    def __repr__(self):
        now = int(time.time())
        return f"Mechanical Deer spawned {now - self.spawned_at} seconds ago on #{self.channel.name}" \
            f"Made by {self.user_name}"

    def __str__(self):
        now = int(time.time())
        return f"Mechanical Deer spawned {now - self.spawned_at} seconds ago on #{self.channel.name} @ {self.channel.guild.name}" \
            f"Made by {self.user_name}"

    async def post_kill(self, ctx, exp):
        await super().post_kill(ctx, exp)
        author = ctx.message.author
        await self.bot.db.add_to_stat(self.channel, author, "killed_mechanical_deer", 1)


class BabyDeer(BaseDeer):
    """
    A deer that you shouldn't kill because you'll loose exp if you do
    """

    def __init__(self, bot, channel, exp, ttl):
        super().__init__(bot, channel)

        self.staying_until = self.spawned_at + ttl
        self.exp_value = exp
        self.can_use_clover = False

    async def _gen_discord_str(self):
        _ = self.bot._
        language = await self.bot.db.get_pref(self.channel, "language")

        trace = random.choice(self.bot.canards_trace)
        n = datetime.datetime.now()
        easter_eggs = n.date() in [dateutil.easter.easter(n.year), dateutil.easter.easter(n.year) + datetime.timedelta(days=1)]

        if easter_eggs:
            corps = "🥚"
        else:
            corps = random.choice(["<:BabyDeer_01:439546718263050241>", "<:BabyDeer_02:439551472762355724>", " <:official_BabyDeer_01:439546718527160322>", "<a:a_BabyDeer_01:439546761091088385>",
                                   " <a:a_BabyDeer_02:574299816155414531>"])

        cri = "**COIN**"

        self.discord_spawn_str = f"{trace} {corps} < {cri}"
        self.discord_leave_str = _("The baby deer left to take a little nap somewhere ·°'\`'°-.,¸¸.·°'\`", language)

    @classmethod
    async def create(cls, bot, channel, life=None, ignore_event=False):
        # Base deer time to live
        ttl = await bot.db.get_pref(channel, "time_before_deer_leave")

        # Base deer exp
        exp_value = - await bot.db.get_pref(channel, "exp_won_per_deer_killed")

        deer = cls(bot, channel, exp=exp_value, ttl=ttl)
        await deer._gen_discord_str()
        if life:
            deer.life = life
        return deer

    async def get_killed_string(self):
        _ = self.bot._
        language = await self.bot.db.get_pref(self.channel, "language")

        return _(":skull_crossbones: **{onomatopoeia}**\tYou killed the baby deer in {time} seconds, and you shouldn't have done this!"
                 " You'll lose some exp, because you shouldn't kill babies"
                 "\_X<   *COUAC*   {exp}", language)

    async def post_kill(self, ctx, exp):
        await super().post_kill(ctx, exp)
        author = ctx.message.author
        await self.bot.db.add_to_stat(self.channel, author, "killed_baby_deer", 1)

    async def hug(self, ctx):
        _ = self.bot._
        language = await self.bot.db.get_pref(self.channel, "language")
        author = ctx.author
        await self.bot.db.add_to_stat(self.channel, author, "hugged_baby_deer", 1)
        await self.bot.db.add_to_stat(self.channel, author, "exp", 3)
        self.delete()
        return _("<:cmd_Hug_01:442695336348221451> **SMACK**\tYou hugged the baby deer, and now it is really happy! [3 exp]\n"
                 "The baby deer left, feeling loved", language)


class MotherOfAllDeer(SuperDeer):

    async def _gen_discord_str(self):
        _ = self.bot._
        language = await self.bot.db.get_pref(self.channel, "language")

        trace = random.choice(self.bot.canards_trace)

        n = datetime.datetime.now()

        april_fools = n.day == 1 and n.month == 4
        easter_eggs = n.date() in [dateutil.easter.easter(n.year), dateutil.easter.easter(n.year) + datetime.timedelta(days=1)]

        if april_fools:
            corps = "🐟"
        elif easter_eggs:
            corps = "🍳"
        else:
            corps = await self.bot.db.get_pref(self.channel, "emoji_used")

        cri = _("**I AM...** Your mother", language)

        self.discord_spawn_str = f"{trace} {corps} < {cri}"
        self.discord_leave_str = _(random.choice(self.bot.canards_bye), language)

    async def get_killed_string(self):
        _ = self.bot._
        language = await self.bot.db.get_pref(self.channel, "language")
        return _(":skull_crossbones: **{onomatopoeia}**\t You killed me in {time} seconds, but you won't kill my children! \_X<   *COUAC*   {exp}", language)

    async def post_kill(self, ctx, exp):
        await BaseDeer.post_kill(self, ctx, exp)
        author = ctx.message.author
        await self.bot.db.add_to_stat(self.channel, author, "killed_mother_of_all_deer", 1)

        from cogs import spawning
        self.logger.info("A mother of all deer were killed, spawning two new deer! ")
        await spawning.spawn_deer(self.bot, self.channel)
        await spawning.spawn_deer(self.bot, self.channel)
