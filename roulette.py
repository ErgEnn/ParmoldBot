import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
from bank import BankCog
import random

RED_NUMBERS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

class RouletteCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @app_commands.command(name="bet")
    async def bet(self, interaction: discord.Interaction, amount:int, color: Literal['red','black','green']):
        bank: BankCog = self.bot.get_cog('BankCog')
        
        if amount < 1:
            await interaction.response.send_message(content="Nii väikese panusega sind mängu ei võeta!")
            return
      
        balance = bank.get_balance(interaction.user)
        if amount > balance:
            await interaction.response.send_message(content=f"Jää oma võimekuse piiridesse! (max panus sulle: {balance})")
            return

        if not bank.withdraw(interaction.user, amount):
            await interaction.response.send_message(sontent = "Sa oleks peaaegu kasiinolt raha petnud!")
            return
      
        bank.withdraw_limitless(self.bot.user, amount)

        number = random.randint(0, 36)
        result_color = 'red' if number in RED_NUMBERS else 'black' if number != 0 else 'green'

        if result_color == color:
            if result_color == 'green':
                winnings = amount * 35
            else:
                winnings = amount
            
            bank.deposit(interaction.user, winnings*2)
            result_msg = f"Pall maandus {number} ({result_color}). Võitsid {winnings} eurot!"
        else:
            bank.deposit(self.bot.user, amount*2)
            result_msg = f"Pall maandus {number} ({result_color}). Kaotasid {amount} eurot."

        balance = bank.get_balance(interaction.user)
        await interaction.response.send_message(content=f"{result_msg} Su uus balanss on {balance} eurot.")

async def setup(bot: commands.Bot):
    await bot.add_cog(RouletteCog(bot))