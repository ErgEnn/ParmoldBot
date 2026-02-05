from discord.ext import commands, tasks
import datetime
import logging
import runedle_solver


utc = datetime.timezone.utc
time = datetime.time(hour=7, minute=00, tzinfo=utc)

class RunedleCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.runedle_task.start()
    
    def send_to_channel(self, channel, mode):
        solution = runedle_solver.solve_runedle(mode)
        lines = [f"{runedle_solver.bitmask_to_string(bm)} ||{npc['name']}|| ({no_of_npcs} NPCs left)" for bm, npc, no_of_npcs in solution]
        lines.insert(0, f"Runedle({mode}) in {len(solution)} attempts")
        message = "\n".join(lines)
        channel.send(message)
    
    @tasks.loop(minutes=5.0)
    async def runedle_task(self):
        channel_id = 1378318355320279081
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            logging.error(f"Could not find channel with ID {channel_id}")
            return
        self.send_to_channel(channel, "normal")
        self.send_to_channel(channel, "expert")


async def setup(bot: commands.Bot):
    await bot.add_cog(RunedleCog(bot))