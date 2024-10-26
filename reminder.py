import asyncio
import sqlite3
import re
from datetime import datetime, timedelta

conn = sqlite3.connect('data/reminders.db')
c = conn.cursor()

# Create a table to store reminders if it doesn't exist
c.execute('''CREATE TABLE IF NOT EXISTS reminders (
    user_id INTEGER,
    channel_id INTEGER,
    reminder_message TEXT,
    remind_at DATETIME
)''')
conn.commit()


# Function to convert time with units into seconds
def convert_time_to_seconds(time_str):
    time_regex = r"(\d+)\s*(second|minute|hour|day|month|year)s?"
    match = re.match(time_regex, time_str.lower())

    if not match:
        return None

    value, unit = int(match.group(1)), match.group(2)

    time_multipliers = {
        'second': 1,
        'minute': 60,
        'hour': 3600,
        'day': 86400,
        'month': 2592000,  # Assuming 30 days in a month
        'year': 31536000  # 365 days
    }

    return value * time_multipliers.get(unit, 0)


# Function to save a reminder to the database
def save_reminder(user_id, channel_id, message, remind_at):
    try:
        c.execute("INSERT INTO reminders (user_id, channel_id, reminder_message, remind_at) VALUES (?, ?, ?, ?)",
                  (user_id, channel_id, message, remind_at))
        conn.commit()
    except sqlite3.Error as e:
        await message.channel.send(f"Täitsa kuradi jama! Kutsuge on-call: {str(e)}")


# Function to load reminders and resume waiting for them
async def load_reminders(client):
    try:
        c.execute("SELECT rowid, * FROM reminders")
        reminders = c.fetchall()
        now = datetime.now()

        for reminder in reminders:
            rowid, user_id, channel_id, message, remind_at = reminder
            remind_at_dt = datetime.strptime(remind_at, '%Y-%m-%d %H:%M:%S')
            remaining_seconds = (remind_at_dt - now).total_seconds()

            if remaining_seconds > 0:
                asyncio.create_task(schedule_reminder(rowid, user_id, channel_id, message, remaining_seconds, client))
            else:
                await send_reminder(rowid, user_id, channel_id, message, client)
    except sqlite3.Error as e:
        print(f"Raisk! Error loading reminders: {e}")


# Function to wait and send the reminder
async def schedule_reminder(rowid, user_id, channel_id, message, wait_time, client):
    await asyncio.sleep(wait_time)
    await send_reminder(rowid, user_id, channel_id, message, client)


# Function to send the reminder
async def send_reminder(rowid, user_id, channel_id, message, client):
    channel = client.get_channel(channel_id)
    if channel:
        await channel.send(f"<@{user_id}>, {message}")

    # Delete reminder from database after sending
    try:
        c.execute("DELETE FROM reminders WHERE rowid = ?", (rowid,))
        conn.commit()
    except sqlite3.Error as e:
        await message.channel.send(f"Täitsa loll lugu! Ei kustu ju ära: {str(e)}")


async def try_handle_remind_me(client, message):
    if message.content.startswith('$remindme'):
        try:
            # Format: $remindme "Your reminder message" 3 days
            command_pattern = r'\$remindme\s*"(.+)"\s*(\d+\s*\w+)'
            match = re.match(command_pattern, message.content)

            if not match:
                await message.channel.send("Putsis! Proovi: $remindme \"türa tulistab tühja...\" time (ntks, 3 days).")
                return

            reminder_message = match.group(1)
            time_str = match.group(2)
            time_in_seconds = convert_time_to_seconds(time_str)
            if time_in_seconds is None:
                await message.channel.send(
                    "Aeg on vittus ju! Number ja unit (seconds, minutes, hours, days, months, or years).")
                return

            # Calculate when the reminder should be triggered
            remind_at = datetime.now() + timedelta(seconds=time_in_seconds)

            # Save the reminder to the database
            save_reminder(message.author.id, message.channel.id, reminder_message,
                          remind_at.strftime('%Y-%m-%d %H:%M:%S'))
            asyncio.create_task(
                schedule_reminder(None, message.author.id, message.channel.id, reminder_message, time_in_seconds,
                                  client))

            await message.channel.send(f"Paras idikas, tuletan siis meelde! \"{reminder_message}\" - {time_str}")

        except Exception as e:
            await message.channel.send(f"Johhaidii, mingi jama juhtus: {str(e)}")
