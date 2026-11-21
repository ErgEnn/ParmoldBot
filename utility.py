import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import asyncio
import logging
import os
import pytz
import requests
from urllib.parse import quote

WOM_URL = 'https://api.wiseoldman.net/v2/players/'


def format_osrs_skills(player: dict, emojis: dict) -> str:
    skills = dict(player['latestSnapshot']['data']['skills'])
    overall = skills.pop('overall')
    # 3 columns, like the in-game skill panel; inline code keeps the numbers the same width
    cells = [f"{emojis.get(name, name.capitalize())} `{max(s['level'], 1):>2}`" for name, s in skills.items()]
    rows = ['\u2003'.join(cells[i:i + 3]) for i in range(0, len(cells), 3)]
    return (
        f"**{player['displayName']}** (combat {player['combatLevel']}, total {overall['level']})\n"
        + '\n'.join(rows) +
        f"\n-# Wise Old Man, uuendatud {player['updatedAt'][:10]}"
    )


def fetch_osrs_icon(skill: str) -> bytes:
    name = 'Runecraft' if skill == 'runecrafting' else skill.capitalize()
    response = requests.get(
        f'https://oldschool.runescape.wiki/images/{name}_icon.png',
        headers={'User-Agent': 'ParmoldBot (Discord bot)'}, timeout=10,
    )
    response.raise_for_status()
    return response.content


def fetch_osrs_player(ign: str):
    url = WOM_URL + quote(ign, safe='')
    headers = {'User-Agent': 'ParmoldBot'}
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 404:
        # Not tracked by WOM yet: POST makes WOM pull it from the hiscores
        response = requests.post(url, headers=headers, timeout=30)
    if not response.ok or not response.json().get('latestSnapshot'):
        return None
    return response.json()


class UtilityCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Get start_time from the bot or set it now
        if not hasattr(bot, 'start_time'):
            bot.start_time = datetime.now()
        self.start_time = bot.start_time
        self.osrs_emojis = {}
        self.osrs_emoji_lock = asyncio.Lock()

    async def get_osrs_emojis(self, skills) -> dict:
        """Skill name -> emoji markup. Missing icons are uploaded once as application emojis
        (not guild emojis, which autoreact picks from at random)."""
        async with self.osrs_emoji_lock:
            missing = [s for s in skills if s not in self.osrs_emojis]
            if not missing:
                return self.osrs_emojis
            try:
                existing = {e.name: e for e in await self.bot.fetch_application_emojis()}
                for skill in missing:
                    emoji = existing.get(f'osrs_{skill}')
                    if emoji is None:
                        image = await asyncio.to_thread(fetch_osrs_icon, skill)
                        emoji = await self.bot.create_application_emoji(name=f'osrs_{skill}', image=image)
                    self.osrs_emojis[skill] = str(emoji)
            except Exception:
                # Icons are decoration: fall back to skill names for whatever is missing
                logging.exception("Failed to load OSRS skill emojis")
            return self.osrs_emojis

    @app_commands.command(name="help")
    async def help_cmd(self, interaction: discord.Interaction):
        """KYS"""
        await interaction.response.send_message(content="KYS")

    @app_commands.command(name="uptime")
    async def uptime_cmd(self, interaction: discord.Interaction):
        """Show bot uptime"""
        uptime = datetime.now() - self.start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        await interaction.response.send_message(
            content=f"Ma näen kõwwa vaeva juba: "
            f"{days}d {hours}h {minutes}m {seconds}s\n"
            f"Alates: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    @app_commands.command(name="version")
    async def version_cmd(self, interaction: discord.Interaction):
        """Show the commit hash of the currently running code"""
        commit = os.environ.get('GIT_COMMIT', 'unknown')
        await interaction.response.send_message(content=f"Jooksen commitil `{commit}`")

    @app_commands.command(name="osrs")
    async def osrs_cmd(self, interaction: discord.Interaction, ign: str):
        """Show OSRS skill levels of a player

        Parameters
        -----------
        ign: str
            Old School RuneScape in-game name
        """
        await interaction.response.defer()  # WOM can take longer than Discord's 3s limit
        try:
            player = await asyncio.to_thread(fetch_osrs_player, ign)
        except requests.RequestException:
            player = None
        if player is None:
            await interaction.followup.send(
                content=f"Ei leidnud mängijat `{ign}`", allowed_mentions=discord.AllowedMentions.none()
            )
            return
        skills = [s for s in player['latestSnapshot']['data']['skills'] if s != 'overall']
        emojis = await self.get_osrs_emojis(skills)
        await interaction.followup.send(content=format_osrs_skills(player, emojis))

    @app_commands.command(name="timeat")
    async def timeat_cmd(self, interaction: discord.Interaction, user: discord.Member):
        """Show time at a user's location
        
        Parameters
        -----------
        user: discord.Member
            The user whose timezone you want to check
        """
        if user.id == 145929101482524672:
            # Silver's timezone
            sydney_timezone = pytz.timezone('Australia/Sydney')
            sydney_time = datetime.now(sydney_timezone)
            await interaction.response.send_message(
                content=f"Time in Sydney, Australia is {sydney_time.strftime('%H:%M')}"
            )
        elif user.id == 359332609769340938:
            # Risto's timezone
            ams_tz = pytz.timezone('Europe/Amsterdam')
            ams_time = datetime.now(ams_tz)
            await interaction.response.send_message(
                content=f"Time in Maaskantje, Netherlands is {ams_time.strftime('%H:%M')}"
            )
        elif user.id == 193076206562836490:
            # Märjamaa timezone (same as Tallinn)
            tallinn_tz = pytz.timezone('Europe/Tallinn')
            tallinn_time = datetime.now(tallinn_tz)
            await interaction.response.send_message(
                content=f"Time in Märjamaa, Estonia is {tallinn_time.strftime('%H:%M')}"
            )
        else:
            # Default to Tallinn time for others
            tallinn_tz = pytz.timezone('Europe/Tallinn')
            tallinn_time = datetime.now(tallinn_tz)
            await interaction.response.send_message(
                content=f"Time in Tallinn, Estonia is {tallinn_time.strftime('%H:%M')}"
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(UtilityCog(bot))
