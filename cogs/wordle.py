import discord
from discord import app_commands
from discord.ext import commands
import re
import json
import os
from datetime import datetime
import random

WORDLE_CHANNEL = os.getenv('WORDLE_CHANNEL', 'wordle')
DATA_FILE = os.getenv('DATA_FILE', 'data/leaderboard.json')

RESPONSES = {
    'fail': [
        "didn't get it.",
        "L.",
        "so close yet so far. actually no, not even close.",
        "happens to the best of us. not really though.",
        "you had 6 tries.",
        "maybe tomorrow.",
        "yeah that's rough.",
    ],
    1: [
        "no way that was luck.",
        "how.",
        "ok who told you.",
        "that doesn't count and you know it.",
        "show me your starting word right now.",
    ],
    2: [
        "either you cheated or you're not telling us something.",
        "suspicious.",
        "using a solver is still losing imo.",
        "ok but how.",
        "2/6 is insane. i don't trust you.",
    ],
    3: [
        "clean.",
        "yeah that's good.",
        "solid.",
        "nice one.",
        "respectable.",
    ],
    4: [
        "fine.",
        "ok.",
        "could be worse.",
        "average but in a fine way.",
        "yeah alright.",
    ],
    5: [
        "that was close.",
        "nearly didn't make it.",
        "cutting it a bit close there.",
        "you got it but don't act like you weren't sweating.",
        "5/6 is still a W technically.",
    ],
    6: [
        "last guess. really.",
        "you scraped through.",
        "that was genuinely stressful to watch.",
        "a win is a win i guess.",
        "you got lucky and you know it.",
    ],
}

REMINDERS = [
    "{mention} wordle.",
    "{mention} you haven't done your wordle.",
    "{mention} go do your wordle.",
    "{mention} wordle isn't gonna do itself.",
    "{mention} still waiting on your wordle.",
    "{mention} everyone else has done their wordle.",
]


def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, 'r') as f:
        return json.load(f)


def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def get_month_key():
    return datetime.now().strftime('%Y-%m')


def build_leaderboard_embed(data, month):
    month_data = data.get(month, {})
    if not month_data:
        return None

    stats = []
    for user_id, entry in month_data.items():
        scores = entry['scores']
        fails = entry['fails']
        avg = sum(scores) / len(scores) if scores else None
        stats.append({
            'name': entry['name'],
            'avg': avg,
            'wins': len(scores),
            'fails': fails,
        })

    stats.sort(key=lambda x: (x['avg'] is None, x['avg'] or 999, -x['wins']))

    month_name = datetime.now().strftime('%B %Y')
    embed = discord.Embed(
        title=f"Wordle Leaderboard — {month_name}",
        color=0x538d4e
    )

    medals = ['🥇', '🥈', '🥉']
    lines = []
    for i, s in enumerate(stats):
        prefix = medals[i] if i < 3 else f"{i + 1}."
        avg_str = f"{s['avg']:.2f}" if s['avg'] is not None else "—"
        lines.append(f"{prefix} **{s['name']}** — avg {avg_str} | {s['wins']}W / {s['fails']}L")

    embed.description = '\n'.join(lines)
    embed.set_footer(text="Resets every month • /leaderboard")
    return embed


class WordleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        if message.channel.name != WORDLE_CHANNEL:
            return

        pattern = r'Wordle\s+[\d,]+\s+([1-6X])/6'
        match = re.search(pattern, message.content)
        if not match:
            return

        score_str = match.group(1)
        score = 'fail' if score_str == 'X' else int(score_str)

        self.update_leaderboard(message.author, score)

        response = random.choice(RESPONSES[score])
        await message.reply(response)

    def update_leaderboard(self, user, score):
        data = load_data()
        month = get_month_key()

        if month not in data:
            data[month] = {}

        user_id = str(user.id)
        if user_id not in data[month]:
            data[month][user_id] = {
                'name': user.display_name,
                'scores': [],
                'fails': 0,
            }

        entry = data[month][user_id]
        entry['name'] = user.display_name

        if score == 'fail':
            entry['fails'] += 1
        else:
            entry['scores'].append(score)

        save_data(data)

    # --- Slash commands ---

    @app_commands.command(name='remind', description='Tell someone to go do their Wordle')
    async def remind_slash(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            random.choice(REMINDERS).format(mention=member.mention)
        )

    @app_commands.command(name='react', description='Send a dry reply to someone\'s Wordle score')
    @app_commands.describe(
        member='Who to reply to',
        score='Their score (1-6 or 0 for fail)'
    )
    @app_commands.choices(score=[
        app_commands.Choice(name='1/6', value=1),
        app_commands.Choice(name='2/6', value=2),
        app_commands.Choice(name='3/6', value=3),
        app_commands.Choice(name='4/6', value=4),
        app_commands.Choice(name='5/6', value=5),
        app_commands.Choice(name='6/6', value=6),
        app_commands.Choice(name='X/6 (fail)', value=0),
    ])
    async def react_slash(self, interaction: discord.Interaction, member: discord.Member, score: int):
        key = 'fail' if score == 0 else score
        response = random.choice(RESPONSES[key])
        await interaction.response.send_message(f"{member.mention} {response}")

    @app_commands.command(name='leaderboard', description='Show the monthly Wordle leaderboard')
    async def leaderboard_slash(self, interaction: discord.Interaction):
        data = load_data()
        month = get_month_key()
        embed = build_leaderboard_embed(data, month)
        if embed is None:
            await interaction.response.send_message("No Wordle data this month yet — go share your results!")
            return
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(WordleCog(bot))
