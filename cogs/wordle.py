import discord
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
        "couldn't even get it lmaooo 💀",
        "skill issue.",
        "bro really said X/6 😭",
        "the wordle said no.",
        "touch grass and try again tomorrow",
        "not a single braincell was used today huh",
        "DNF. disgraceful.",
        "at this point just google it next time",
    ],
    1: [
        "...there's no way. who told you?",
        "BRO HOW 😭",
        "ok you're literally cheating i don't accept this",
        "1/6?? call the police",
        "you're not even allowed to celebrate this, that's suspicious",
        "i'm telling the wordle authorities",
    ],
    2: [
        "2/6? you're definitely using a solver lol",
        "are you cheating? be honest.",
        "no normal human being gets it in 2. sus.",
        "ok show us your starting word RIGHT NOW",
        "2/6 and you think you're better than everyone here 💀",
        "bot behavior fr",
    ],
    3: [
        "3/6, respectable. very respectable.",
        "okay actually impressive ngl",
        "three and done, clean.",
        "top tier performance today",
        "carried by the third row apparently",
    ],
    4: [
        "4/6, perfectly average. just like you.",
        "mid but in a comfortable way",
        "4/6 energy today huh",
        "getting there... slowly",
        "solid C+ effort",
    ],
    5: [
        "5/6... you almost choked there buddy",
        "cutting it close aren't we",
        "one more wrong guess and it would've been embarrassing",
        "5/6 is technically a win but let's not celebrate too hard",
        "stress run but you made it",
        "your heart must've been racing on that last one",
    ],
    6: [
        "6/6 💀 last chance energy",
        "squeaked through on the final guess lmaooo",
        "6/6... that's a moral loss honestly",
        "you survived but nobody's impressed",
        "the wordle almost beat you. it almost won.",
        "that's not a win that's an escape",
    ],
}


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


class WordleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
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

    @commands.command(name='remind')
    async def remind(self, ctx, member: discord.Member = None):
        reminders = [
            "{mention} go do your wordle you bum",
            "{mention} wordle. now. i'm not asking.",
            "{mention} the wordle isn't gonna do itself",
            "{mention} everyone's waiting on you for the wordle 🙄",
            "{mention} bro forgot the wordle exists 💀",
            "{mention} do your wordle or you're getting kicked /j",
            "{mention} the wordle board is incomplete because of YOU",
        ]
        if member is None:
            await ctx.send("Usage: `!remind @someone`")
            return
        await ctx.send(random.choice(reminders).format(mention=member.mention))

    @commands.command(name='leaderboard', aliases=['lb', 'wordle'])
    async def leaderboard(self, ctx):
        data = load_data()
        month = get_month_key()

        if month not in data or not data[month]:
            await ctx.send("No Wordle data this month yet — go share your results!")
            return

        month_data = data[month]

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
            lines.append(
                f"{prefix} **{s['name']}** — avg {avg_str} | {s['wins']}W / {s['fails']}L"
            )

        embed.description = '\n'.join(lines)
        embed.set_footer(text="Resets every month • !leaderboard or !lb")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(WordleCog(bot))
