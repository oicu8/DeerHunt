import time

import psutil
from aiohttp import web
import os
from cogs.helpers import deer

routes = web.RouteTableDef()

bot = None


class Api:
    """

    The DeerHunt API, primarly designed for use with highcharts

    """
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        self.runner = web.AppRunner(self.app)

    @routes.get('/deer_spawned')
    async def deer_spawned(self):
        """
        A simple API request to get the number of deer spawned, including the number of super deer

        :return: [current milis in unix (epoch) time, number of normal deer, number of super deer, number of babies, number of moad]
        """
        bot.logger.debug("[API] Request for deer_spawned!")
        await bot.wait_until_ready()

        total_deer_spawned = len(bot.deer_spawned)
        super_deer_spawned = sum(isinstance(d, deer.SuperDeer) for d in bot.deer_spawned)
        baby_deer_spawned = sum(isinstance(d, deer.BabyDeer) for d in bot.deer_spawned)
        moad_spawned = sum(isinstance(d, deer.MotherOfAllDeer) for d in bot.deer_spawned)

        res = [int(time.time() * 1000), total_deer_spawned - super_deer_spawned, super_deer_spawned, baby_deer_spawned, moad_spawned]

        return web.json_response(res)

    @routes.get('/user_count')
    async def user_count(self):
        """
        A simple API request to get the number of users the bot currenly sees

        :return: [current milis in unix (epoch) time, number of users]
        """
        bot.logger.debug("[API] Request for user_count!")
        await bot.wait_until_ready()

        users = len(bot.users)

        res = [int(time.time() * 1000), users]

        return web.json_response(res)

    @routes.get('/guild_count')
    async def guild_count(self):
        """
        A simple API request to get the number of guilds the bot currenly sees

        :return: [current milis in unix (epoch) time, number of guilds]
        """
        bot.logger.debug("[API] Request for guild_count!")
        await bot.wait_until_ready()

        users = len(bot.guilds)

        res = [int(time.time() * 1000), users]

        return web.json_response(res)

    @routes.get('/enabled_channels_count')
    async def enabled_channels_count(self):
        """
        A simple API request to get the number of channels enabled on DeerHunt

        :return: [current milis in unix (epoch) time, number of channels]
        """
        bot.logger.debug("[API] Request for enabled_channels_count!")
        await bot.wait_until_ready()

        channels = len(bot.deer_planning.keys())

        res = [int(time.time() * 1000), channels]

        return web.json_response(res)


    @routes.get('/memory_usage')
    async def memory_usage(self):
        """
        A simple API request to get the memory usage of the bot, in MB

        :return: [current milis in unix (epoch) time, memory used]
        """
        bot.logger.debug("[API] Request for memory_usage!")

        memory_used = round(psutil.Process(os.getpid()).memory_info()[0] / 2. ** 30 * 1000, 5)

        res = [int(time.time() * 1000), memory_used]

        return web.json_response(res)


    @routes.get('/latency')
    async def latency(self):
        """
        A simple API request to get the memory usage of the bot, in seconds.
        This number is the time left unused in the mainloop. It should be as close as possible to 1 second

        :return: [current milis in unix (epoch) time, time left, discord_ping]
        """
        bot.logger.debug("[API] Request for latency!")

        res = [int(time.time() * 1000), bot.loop_latency, max(0,bot.latency)]

        return web.json_response(res)

    async def run(self):
        self.app.add_routes(routes)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '0.0.0.0', 6872)
        await site.start()
        self.bot.logger.debug("API started")

def setup(bot_):
    global bot
    bot = bot_

    api = Api(bot)

    bot.loop.create_task(api.run())
