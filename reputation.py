import logging
import random
import re


_guild_emoji_cache = {}


def _is_usable_emoji(emoji):
    if not getattr(emoji, "available", True):
        return False

    is_usable = getattr(emoji, "is_usable", None)
    if not is_usable:
        return True

    try:
        return is_usable()
    except Exception:
        logging.exception("Failed to check emoji usability for %s", getattr(emoji, "id", emoji))
        return False


def load_guild_emojis(guild):
    emojis = tuple(emoji for emoji in getattr(guild, "emojis", []) if _is_usable_emoji(emoji))
    _guild_emoji_cache[guild.id] = emojis
    logging.info("Loaded %s autoreact emojis for guild %s", len(emojis), guild.id)
    return emojis


async def try_handle_bad_bot(message):
    bad_words = [
        "bad bot", "halb bot", "loll bot", "rumal bot", "idioot", "tüütu", "munn", "perse",
        "debiilik", "lollakas", "põmmpea", "tolvan", "värdjas", "mölakas", "idikas", "idioot bot"
    ]
    if any(word in message.content.lower() for word in bad_words):
        await message.add_reaction('😢')


async def try_handle_good_bot(client, message):
    good_words = [
        "good bot", "hea bot", "tubli bot", "aitäh", "tubli", "suurepärane", "vinge",
        "äge", "mulle meeldib", "fantastiline", "tänan", "tänud", "huvä"
    ]
    if any(word in message.content.lower() for word in good_words):
        emoji = client.get_emoji(1291820499420053677)
        await message.add_reaction(emoji)


async def try_handle_reaction_bot(message):
    if random.randint(1, 1000) <= 10:  # 1 in 100
        guild = getattr(message, "guild", None)
        if guild is None:
            return

        emojis = _guild_emoji_cache.get(guild.id)
        if emojis is None:
            emojis = load_guild_emojis(guild)
        if not emojis:
            return

        emoji = random.choice(emojis)
        try:
            await message.add_reaction(emoji)
        except Exception:
            logging.exception("Failed to add autoreact emoji %s", getattr(emoji, "id", emoji))


async def try_handle_greeting(message):
    pattern = r'(?i)t+e+r+e+\s+h+o+m+m+i+k+u*s*t*[!?.]*$'
    match = re.match(pattern, message.content.strip(), re.IGNORECASE)
    if not match:
        return
    tere = f"ter{'e' * random.randint(1, 8)} hommik{'u' * random.randint(1, 8)}st"
    await message.channel.send(tere)
