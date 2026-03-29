import discord
from discord.ext import commands
import os
import asyncio
from aiohttp import web
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)


GUILD_ID = int(os.getenv('GUILD_ID', 0))

@bot.event
async def on_ready():
    print(f'{bot.user} is online!')
    guild = discord.Object(id=GUILD_ID)
    bot.tree.copy_global_to(guild=guild)
    synced = await bot.tree.sync(guild=guild)
    print(f'Synced {len(synced)} slash commands to guild.')


async def health_check(request):
    return web.Response(text="OK")


async def start_health_server():
    port = int(os.getenv('PORT', 8080))
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f'Health server running on port {port}')


async def main():
    await start_health_server()
    async with bot:
        for cog in ['cogs.wordle']:
            await bot.load_extension(cog)
        await bot.start(os.getenv('DISCORD_TOKEN'))


asyncio.run(main())
