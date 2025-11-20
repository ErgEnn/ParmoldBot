import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import pytz


class UtilityCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Get start_time from the bot or set it now
        if not hasattr(bot, 'start_time'):
            bot.start_time = datetime.now()
        self.start_time = bot.start_time

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
