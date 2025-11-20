import sqlite3
from datetime import datetime, timedelta
import logging
import random
from discord import Message, Embed

logging.basicConfig(level=logging.INFO)
DB_NAME = 'data/gambling.db'

# Constants
DAILY_BONUS = 1000
MAX_BET = 1000000
RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

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


class Database:
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.conn = None
        self._create_tables()

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

    def get_user_balance(self, user_id: int) -> tuple:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT balance, last_daily FROM users WHERE user_id = ?", (user_id,))
            result = cursor.fetchone()

            if not result:
                cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
                conn.commit()
                return 0, None

            return result
        except sqlite3.Error as e:
            logging.error(f"Error getting user {user_id}: {e}")
            return 0, None

    def update_daily(self, user_id: int, amount: int, timestamp: str) -> bool:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cutoff = (datetime.fromisoformat(timestamp) - timedelta(days=1)).isoformat()
            cursor.execute('''
                UPDATE users 
                SET balance = balance + ?, 
                    last_daily = ? 
                WHERE user_id = ?
                AND (last_daily IS NULL OR last_daily < ?)
            ''', (amount, timestamp, user_id, cutoff))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logging.error(f"Daily update failed for {user_id}: {e}")
            return False

    def place_bet(self, user_id: int, amount: int) -> bool:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET balance = balance - ? 
                WHERE user_id = ? AND balance >= ?
            ''', (amount, user_id, amount))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            conn.rollback()
            logging.error(f"Bet placement failed: {e}")
            return False

    def add_winnings(self, user_id: int, amount: int) -> None:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET balance = balance + ? 
                WHERE user_id = ?
            ''', (amount * 2, user_id))
            conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Failed to add winnings for {user_id}: {e}")

    def refund_bet(self, user_id: int, amount: int) -> None:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET balance = balance + ? 
                WHERE user_id = ?
            ''', (amount, user_id))
            conn.commit()
        except sqlite3.Error as e:
            logging.error(f"Failed to refund bet for {user_id}: {e}")


db = Database(DB_NAME)


async def try_handle_flex(message: Message):
    if not message.content.startswith('$flex'):
        return

    user_id = message.author.id
    balance, _ = db.get_user_balance(user_id)

    if balance < 250:
        await message.channel.send("Kus su raha on!? 💸")
        return

    if not db.place_bet(user_id, 250):
        await message.channel.send("❌ Tekkis viga raha mahaarvamisel.")
        return

    chance = random.random()
    if chance < 0.2:
        if random.random() < 0.1:
            db.place_bet(user_id, balance)
            await message.channel.send(random.choice(BIG_FAILURE_MESSAGES))
        else:
            await message.channel.send(random.choice(FAILURE_MESSAGES))
        return

    random_gif = random.choice(FLEX_IMAGES)
    await message.channel.send(
        content=f"🎁 **{message.author.name} viskas just 250 eurot tuulde:**",
        embed=Embed().set_image(url=random_gif)
    )


async def try_handle_daily(message: Message):
    if not message.content.startswith('$daily'):
        return

    user_id = message.author.id
    balance, last_daily = db.get_user_balance(user_id)
    now = datetime.now()

    try:
        last_daily = datetime.fromisoformat(last_daily) if last_daily else None
    except ValueError:
        last_daily = None

    if last_daily and now.date() <= last_daily.date():
        await message.channel.send(f"Juba said oma raha. Proovi uuesti homme!")
        return

    if db.update_daily(user_id, DAILY_BONUS, now.isoformat()):
        new_balance = balance + DAILY_BONUS
        await message.channel.send(f"Said oma {DAILY_BONUS} eurot! Su uus balanss on {new_balance} eurot.")
    else:
        await message.channel.send("Tekkis viga päevase boonuse andmisel. Palun proovi uuesti.")


async def try_handle_balance(message: Message):
    if not message.content.startswith('$balance'):
        return

    user_id = message.author.id
    balance, _ = db.get_user_balance(user_id)
    await message.channel.send(f"Sul on hetkel {balance} eurot. Aeg võita, tšempion!")


async def try_handle_beg(message: Message):
    if not message.content.startswith('$beg'):
        return

    user_id = message.author.id
    chance = random.random()
    if chance < 0.5:
        if random.random() < 0.25:
            balance, _ = db.get_user_balance(user_id)
            if balance > 0:
                db.place_bet(user_id, balance)
                await message.channel.send("Kerjasid mustlaselt ja ta lasi kogu su raha rotti!")
            else:
                db.add_winnings(user_id, 100)
                await message.channel.send("Said Petsilt korraliku nutsu, lase edasi tšempion!")
        else:
            db.add_winnings(user_id, 5)
            await message.channel.send("Okei kerjus... saad oma 10 eurot, mine osta Bocki!")


async def try_handle_bet(message: Message):
    if not message.content.startswith('$bet'):
        return

    parts = message.content.split()
    if len(parts) < 3:
        await message.channel.send("Vale formaat! Kasuta: $bet <amount> <red/black>")
        return

    try:
        amount = int(parts[1])
        if amount <= 0 or amount > MAX_BET:
            raise ValueError
    except ValueError:
        await message.channel.send(f"Panuse summa peab olema positiivne arv (max {MAX_BET}).")
        return

    bet_choice = parts[2].lower()
    if bet_choice not in ['red', 'black', 'green']:
        await message.channel.send("Vale panuse valik! Vali 'red', 'black' või 'green'.")
        return

    user_id = message.author.id
    balance, _ = db.get_user_balance(user_id)
    if amount > balance:
        await message.channel.send("Sul pole piisavalt raha!")
        return

    if not db.place_bet(user_id, amount):
        await message.channel.send("Sa oleks peaaegu kasiinolt raha petnud!")
        return

    number = random.randint(0, 36)
    result_color = 'red' if number in RED_NUMBERS else 'black' if number != 0 else 'green'

    if result_color == bet_choice:
        if result_color == 'green':
            winnings = amount * 35
        else:
            winnings = amount
        db.add_winnings(user_id, winnings)
        result_msg = f"Pall maandus {number} ({result_color}). Võitsid {winnings} eurot!"
    else:
        result_msg = f"Pall maandus {number} ({result_color}). Kaotasid {amount} eurot."

    balance, _ = db.get_user_balance(user_id)
    await message.channel.send(f"{result_msg} Su uus balanss on {balance} eurot.")
