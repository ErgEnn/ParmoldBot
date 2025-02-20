import discord
from discord.ext import commands, tasks
import os
import sys
import traceback
import seqlog
import logging
import gzip
import random
from datetime import datetime, date

from reminder import try_handle_remind_me, load_reminders
from gym import try_handle_mhm
from reputation import try_handle_bad_bot, try_handle_good_bot, try_handle_reaction_bot, try_handle_greeting
from timeteller import try_handle_risto_time, try_handle_silver_time
from instantmeme import try_handle_instant_meme
from ace import try_handle_ace
from impersonate import try_handle_impersonation
from ai import try_handle_ai

logging.basicConfig(level=logging.INFO)
handler = seqlog.log_to_seq(
   server_url="http://seq:5341/",
   api_key="5gFywFBgqKr5OzJhvydH",
   level=logging.INFO,
   batch_size=10,
   auto_flush_timeout=10,
   override_root_logger=True)

intents = discord.Intents.default()
intents.message_content = True
start_time: datetime = None
bot = commands.Bot(intents=intents, command_prefix="$")

WORD_LIST_FILE = "data/estonian-words.txt.gz"
startup_channel_id = int(os.environ.get('STARTUP_CHANNEL', '1297656271092187237'))
last_sent_date = None
cached_channel = None

try:
    with gzip.open(WORD_LIST_FILE, "rt", encoding="utf-8") as f:
        word_list = [line.strip() for line in f if line.strip()]
    logging.info(f"Loaded {len(word_list)} words from {WORD_LIST_FILE}")
except Exception as e:
    logging.error(f"Error loading word list from {WORD_LIST_FILE}: {e}")
    word_list = ["putsis"]


async def try_handle_help(message):
    if message.content.startswith('$help'):
        await message.channel.send('KYS')


async def try_handle_uptime(message: discord.Message):
    if message.content.startswith('$uptime'):
        uptime = datetime.now() - start_time
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        await message.channel.send(
            f"Ma näen kõwwa vaeva juba: "
            f"{days}d {hours}h {minutes}m {seconds}s\n"
            f"Alates: {start_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )


@bot.event
async def on_ready():
    global start_time, cached_channel
    start_time = datetime.now()

    logging.info(f'We have logged in as {bot.user}')
    activity = discord.Activity(type=discord.ActivityType.listening, name="AI-Podcast: Poopoo Peepee")
    await bot.change_presence(status=discord.Status.online, activity=activity)
    await load_reminders(bot)
    try:
        await bot.load_extension("bank")
        await bot.load_extension("blackjack")
        await bot.load_extension("roulette")
        await bot.tree.sync()
    except Exception as e:
        logging.error(f"Error loading extensions: {e}")

    cached_channel = bot.get_channel(startup_channel_id)
    if cached_channel:
        word_of_the_day_task.start()
        await cached_channel.send(f"🔄 PIRRRAAAKIII, ma olen tagasi {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        logging.error(f"Could not find channel with ID {startup_channel_id}")


@tasks.loop(minutes=5.0)
async def word_of_the_day_task():
    global last_sent_date, cached_channel
    if last_sent_date == date.today():
        return

    now = datetime.now()
    total_minutes = now.hour * 60 + now.minute
    # Target time is 8:00 AM (480 minutes). Allow a window of ±10 minutes (470 to 490 minutes).
    if 470 <= total_minutes <= 490:
        word = random.choice(word_list)
        await cached_channel.send(f"Tänase päeva sõna on **{word}**")
        last_sent_date = date.today()


@bot.listen()
async def on_message(message):
    if message.author == bot.user:
        return
    try:
        await try_handle_uptime(message)

        await try_handle_mhm(message)

        await try_handle_remind_me(bot, message)

        await try_handle_bad_bot(message)

        await try_handle_good_bot(bot, message)

        await try_handle_reaction_bot(bot, message)

        await try_handle_risto_time(message)

        await try_handle_silver_time(message)

        await try_handle_help(message)

        await try_handle_instant_meme(message)

        await try_handle_ace(message)

        await try_handle_impersonation(bot, message)

        await try_handle_greeting(message)

        #await try_handle_flex(message)

        #await try_handle_beg(message)

        #await try_handle_daily(message)

        #await try_handle_bet(message)

        #await try_handle_balance(message)

        await try_handle_ai(bot, message)

    except Exception:
        logging.exception(traceback.format_exc())
        await message.reply('UPSI WUPSI!! Uwu ma tegin nussi-vussi!! Wäikese kebo bongo! Ergo näeb KÕWA WAEWA, et see ära parandada nii kiiresti kui ta heaks arvab.')

    sys.stdout.flush()


bot.run(os.environ.get('TOKEN'), log_handler=handler)
