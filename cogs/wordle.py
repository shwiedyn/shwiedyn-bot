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

ROASTS = [
    "genuinely what are you doing.",
    "i've seen better.",
    "you're trying so hard and it shows.",
    "the confidence is impressive given the circumstances.",
    "not your best moment.",
    "we don't have to talk about it.",
    "i'm not mad, just disappointed.",
    "respectfully, no.",
    "bold of you to let people see that.",
    "i'd say keep trying but.",
]

COMPLIMENTS = [
    "you on the other hand? immaculate.",
    "meanwhile {mention} is doing great as always.",
    "at least {mention} has it together.",
    "{mention} would never.",
    "good thing {mention} exists to balance things out.",
    "not everyone can be {mention} i guess.",
    "{mention} is built different honestly.",
    "the real W is {mention} for having to witness this.",
]

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


def get_week_key():
    now = datetime.now()
    return f"{now.strftime('%Y')}-W{now.strftime('%W')}"


def build_leaderboard_embed(data, week):
    week_data = data.get(week, {})
    if not week_data:
        return None

    stats = []
    for user_id, entry in week_data.items():
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

    now = datetime.now()
    week_label = f"Week {now.strftime('%W')} — {now.strftime('%B %Y')}"
    embed = discord.Embed(
        title=f"Wordle Leaderboard — {week_label}",
        color=0x538d4e
    )

    medals = ['🥇', '🥈', '🥉']
    lines = []
    for i, s in enumerate(stats):
        prefix = medals[i] if i < 3 else f"{i + 1}."
        avg_str = f"{s['avg']:.2f}" if s['avg'] is not None else "—"
        lines.append(f"{prefix} **{s['name']}** — avg {avg_str} | {s['wins']}W / {s['fails']}L")

    embed.description = '\n'.join(lines)
    embed.set_footer(text="Resets every week • /leaderboard")
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

        # Build full text from message + embeds
        parts = [message.content or '']
        for embed in message.embeds:
            parts += [embed.title or '', embed.description or '']
            for field in embed.fields:
                parts.append(field.value or '')
        text = '\n'.join(parts)

        # Format 1: Wordle bot summary — "4/6: <@userid>" per line
        group_pattern = r'([1-6X])/6[^\n<]*<@!?(\d+)>'
        group_matches = re.findall(group_pattern, text)

        if group_matches:
            # Build a lookup of mentioned users by ID
            mention_map = {str(u.id): u for u in message.mentions}
            replies = []
            for score_str, user_id in group_matches:
                user = mention_map.get(user_id)
                if not user:
                    continue
                score = 'fail' if score_str == 'X' else int(score_str)
                self.update_leaderboard(user, score)
                response = random.choice(RESPONSES[score])
                replies.append(f"{user.mention} {response}")
            if replies:
                await message.reply('\n'.join(replies))
            return

        # Format 2: Standard Wordle share — "Wordle 1,234 3/6"
        single_pattern = r'Wordle\s+[\d,]+\s+([1-6X])/6'
        match = re.search(single_pattern, text)
        if not match:
            return

        score_str = match.group(1)
        score = 'fail' if score_str == 'X' else int(score_str)
        author = message.author
        self.update_leaderboard(author, score)
        response = random.choice(RESPONSES[score])
        await message.reply(response)

    def update_leaderboard(self, user, score):
        data = load_data()
        month = get_week_key()

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

    @app_commands.command(name='roast', description='Roast someone')
    async def roast(self, interaction: discord.Interaction, member: discord.Member):
        roast = random.choice(ROASTS)
        compliment = random.choice(COMPLIMENTS).format(mention=interaction.user.mention)
        await interaction.response.send_message(f"{member.mention} {roast}\n{compliment}")

    @app_commands.command(name='remind', description='Tell someone to go do their Wordle')
    async def remind_slash(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(
            random.choice(REMINDERS).format(mention=member.mention)
        )

    @app_commands.command(name='got1', description='React to a 1/6')
    async def got1(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(f"{member.mention} {random.choice(RESPONSES[1])}")

    @app_commands.command(name='got2', description='React to a 2/6')
    async def got2(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(f"{member.mention} {random.choice(RESPONSES[2])}")

    @app_commands.command(name='got3', description='React to a 3/6')
    async def got3(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(f"{member.mention} {random.choice(RESPONSES[3])}")

    @app_commands.command(name='got4', description='React to a 4/6')
    async def got4(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(f"{member.mention} {random.choice(RESPONSES[4])}")

    @app_commands.command(name='got5', description='React to a 5/6')
    async def got5(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(f"{member.mention} {random.choice(RESPONSES[5])}")

    @app_commands.command(name='got6', description='React to a 6/6')
    async def got6(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(f"{member.mention} {random.choice(RESPONSES[6])}")

    @app_commands.command(name='gotfail', description='React to a failed Wordle')
    async def gotfail(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.send_message(f"{member.mention} {random.choice(RESPONSES['fail'])}")

    @app_commands.command(name='leaderboard', description='Show the monthly Wordle leaderboard')
    async def leaderboard_slash(self, interaction: discord.Interaction):
        data = load_data()
        month = get_week_key()
        embed = build_leaderboard_embed(data, month)
        if embed is None:
            await interaction.response.send_message("No Wordle data this month yet.")
            return
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(WordleCog(bot))
