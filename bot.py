import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user} is online!')
    for cog in ['cogs.wordle']:
        await bot.load_extension(cog)
    print('All cogs loaded.')

bot.run(os.getenv('DISCORD_TOKEN'))
