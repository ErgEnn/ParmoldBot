import discord
from discord import app_commands, Message, Embed
from discord.ext import commands
import typing
import sqlite3
import logging
from datetime import datetime, timedelta
import random

FAILURE_MESSAGES = [
    "Su raha kadus nagu E36 karbid! ☀️💸",
    "Proovige mõne aja pärast uuesti! 🐈⬛🍽️",
    "Keskmine Eesti kasiino kogemus 🇪🇪🎰",
    "HÄÄÄÄ! Varastasin su raha ära! 💸"
]

BIG_FAILURE_MESSAGES = [
    "Flexisid rottide seas ja jäid kogu rahast ilma!",
    "Maksuamet külmutas su konto maksupettuste tõttu!",
    "Keskerakonnal oli vaja trahvi maksta ja see oli oodatust suurem.",
    "Yoink!"
]

FLEX_IMAGES = [
    "https://c.tenor.com/YjPBups7H48AAAAC/tenor.gif",
    "https://c.tenor.com/JHRDfmi9BIgAAAAC/tenor.gif",
    "https://c.tenor.com/4HoVpVyd5P8AAAAC/tenor.gif",
    "https://c.tenor.com/E_OfJ1RCwWoAAAAd/tenor.gif",
    "https://c.tenor.com/BjYGnd9fh-IAAAAd/tenor.gif",
    "https://c.tenor.com/AmvPSQ4TirwAAAAd/tenor.gif",
    "https://c.tenor.com/OAST4gjK3w0AAAAC/tenor.gif",
    "https://c.tenor.com/cvHHLzrQ4ZgAAAAd/tenor.gif",
    "https://c.tenor.com/oCxcur4d32wAAAAd/tenor.gif",
    "https://c.tenor.com/eyX1fMHj4G0AAAAd/tenor.gif",
    "https://c.tenor.com/25IUy_ha-lQAAAAC/tenor.gif",
    "https://c.tenor.com/v_qPOJw06Q0AAAAd/tenor.gif",
    "https://c.tenor.com/dfdxodtK4_YAAAAC/tenor.gif"
]

class BankCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_name = 'data/gambling.db'
        self.conn = None
        self._create_tables()


        self.ctx_menu = app_commands.ContextMenu(
            name='Balance',
            callback=self._get_balance_ctxmenu
        )
        self.bot.tree.add_command(self.ctx_menu)

    def _create_tables(self):
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    balance INTEGER DEFAULT 0,
                    last_daily TEXT
                )
            ''')
            conn.commit()

    def _get_connection(self):
        if not self.conn:
            self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        return self.conn

    def withdraw(self, user: discord.User | discord.Member, amount: int)->bool:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET balance = balance - ? 
                WHERE user_id = ? AND balance >= ?
            ''', (amount, user.id, amount))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            conn.rollback()
            logging.error(f"Failed to withdraw: {e}")
            return False

    def withdraw_limitless(self, user: discord.User | discord.Member, amount: int):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET balance = balance - ? 
                WHERE user_id = ?
            ''', (amount, user.id))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            conn.rollback()
            logging.error(f"Failed to withdraw: {e}")
            return False

    def deposit(self, user: discord.User | discord.Member, amount: int):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET balance = balance + ? 
                WHERE user_id = ?
            ''', (amount, user.id))
            conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Failed to deposit {user.id}: {e}")

    def get_balance(self, user: discord.User | discord.Member)->int:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user.id,))
            result = cursor.fetchone()[0]

            if not result:
                cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user.id,))
                conn.commit()
                return 0

            return result
        except sqlite3.Error as e:
            logging.error(f"Error getting user {user.id}: {e}")
            return 0
    
    def update_daily(self, user: discord.User | discord.Member, amount: int, now: datetime) -> tuple[bool, datetime]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT last_daily FROM users WHERE user_id = ?", (user.id,))
            last_daily = datetime.fromisoformat(cursor.fetchone()[0])
            diff = now - last_daily
            if diff < timedelta(days=1):
                return (False, last_daily)
            
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET balance = balance + ?, 
                    last_daily = ? 
                WHERE user_id = ?
            ''', (amount, now.isoformat(), user.id))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logging.error(f"Daily update failed for {user.id}: {e}")
            return False
    
    async def _get_balance_ctxmenu(self, interaction: discord.Interaction, member: discord.Member):
        balance = self.get_balance(member)
        await interaction.response.send_message(content=f'{member} omab {balance} eurot.')

    @app_commands.command(name="balance")
    async def _get_balance_cmd(self, interaction: discord.Interaction, member: typing.Optional[discord.Member]=None):
        user = interaction.user if member is None else member
        balance = self.get_balance(user)
        await interaction.response.send_message(content=f'{user} omab {balance} eurot.')
    
    @app_commands.command(name="flex")
    async def _flex_cmd(self, interaction: discord.Interaction):
        balance = self.get_balance(interaction.user)

        if balance < 250:
            await interaction.response.send_message(content="Kus su raha on!? 💸")
            return

        if not self.bank.withdraw(interaction.user, 250):
            await interaction.response.send_message(content="❌ Tekkis viga raha mahaarvamisel.")
            return

        chance = random.random()
        if chance < 0.2:
            if random.random() < 0.1:
                self.bank.withdraw(interaction.user, balance-250)
                await interaction.response.send_message(content=random.choice(BIG_FAILURE_MESSAGES))
            else:
                await interaction.response.send_message(content=random.choice(FAILURE_MESSAGES))
            return

        random_gif = random.choice(FLEX_IMAGES)
        await interaction.response.send_message(
            content=f"🎁 **{interaction.user.name} viskas just 250 eurot tuulde:**",
            embed=Embed().set_image(url=random_gif)
        )
    
    @app_commands.command(name="daily")
    async def _daily_cmd(self, interaction: discord.Interaction):
        now = datetime.now()
        DAILY_BONUS = 1000

        success, last_daily = self.update_daily(interaction.user, DAILY_BONUS, now)
        
        if success:
            balance = self.get_balance(interaction.user)
            await interaction.response.send_message(content=f"Said oma {DAILY_BONUS} eurot! Su uus balanss on {balance} eurot.")
            return

        remaining = timedelta(days=1) - (now - last_daily)
        hours, remainder = divmod(remaining.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        await interaction.response.send_message(f"Juba said oma raha. Proovi uuesti {hours}h {minutes}m pärast!")
        
    @commands.hybrid_command(name="beg")
    async def _beg_dmc(self, ctx: commands.Context):
        chance = random.random()
        if chance < 0.5:
            if random.random() < 0.25:
                balance = self.get_balance(ctx.author)
                if balance > 0:
                    self.withdraw(ctx.author, balance)
                    await ctx.send("Kerjasid mustlaselt ja ta lasi kogu su raha rotti!")
                else:
                    self.deposit(ctx.author, 200)
                    await ctx.send("Said Petsilt korraliku nutsu, lase edasi tšempion!")
            else:
                self.deposit(ctx.author, 10)
                await ctx.send("Okei kerjus... saad oma 10 eurot, mine osta Bocki!")
    

async def setup(bot: commands.Bot):
    await bot.add_cog(BankCog(bot))