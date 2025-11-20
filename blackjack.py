import discord
from discord import app_commands
from discord.ext import commands
import random
from bank import BankCog

def create_deck():
    suits = ['♠', '♥', '♦', '♣']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    deck = [f"{rank}{suit}" for suit in suits for rank in ranks]
    random.shuffle(deck)
    return deck

def card_value(card):
    rank = card[:-1]  # drop the suit
    if rank in ['J', 'Q', 'K']:
        return 10
    if rank == 'A':
        return 11  # will adjust later for aces
    return int(rank)

def hand_value(hand):
    total = sum(card_value(card) for card in hand)
    aces = sum(1 for card in hand if card[:-1] == 'A')
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total

class BlackjackView(discord.ui.View):
    def __init__(self, player, bank, bot, deck, player_hand, dealer_hand, bet:int):
        super().__init__(timeout=60)
        self.player = player
        self.bank: BankCog = bank
        self.bot = bot
        self.deck = deck
        self.player_hand = player_hand
        self.dealer_hand = dealer_hand
        self.game_over = False
        self.bet = bet

    async def update_message(self, interaction: discord.Interaction):
        p_score = hand_value(self.player_hand)
        d_score = hand_value(self.dealer_hand)

        content = (
            f"**Sinu kaardid:** {' '.join(self.player_hand)} (kokku: {p_score})\n"
            f"**Diileri kaardid:** {' '.join(self.dealer_hand)} (kokku: {d_score})"
        )
        if self.game_over:
            if p_score > 21:
                content += f"\n💦 Bust! 💸 Kaotasid {self.bet} eurot!"
                self.bank.deposit(self.bot.user, self.bet*2)
            elif d_score > 21:
                content += f"\n💦 Diiler bustis! Sa võitsid {self.bet} eurot!"
                self.bank.deposit(self.player, self.bet*2)
            elif d_score < p_score:
                content += f"\n🎉 Sa võitsid {self.bet} eurot!"
                self.bank.deposit(self.player, self.bet*2)
            elif d_score > p_score:
                content += f"\n💸 Kaotasid {self.bet} eurot. Diiler võitis!"
                self.bank.deposit(self.bot.user, self.bet*2)
            else:
                content += "\n🤝 Viik! Sa said panuse tagasi."
                self.bank.deposit(self.player, self.bet)
                self.bank.deposit(self.bot.user, self.bet)
            
            for child in self.children:
                child.disabled = True

            self.clear_items()
        await interaction.response.edit_message(content=content, view=self)

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button,):
        if interaction.user.id != self.player.id:
            await interaction.response.send_message("Otsi omale oma laud! See laud on täis.", ephemeral=True)
            return
        # Deal another card
        if self.deck:
            self.player_hand.append(self.deck.pop())
        # If busted, end game
        if hand_value(self.player_hand) > 21:
            self.game_over = True
        await self.update_message(interaction)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.player.id:
            await interaction.response.send_message("Nii väikese raha kogusega siia lauda ei saa!", ephemeral=True)
            return
        # Dealer draws until reaching 17 or more
        while hand_value(self.dealer_hand) < 17 and self.deck:
            self.dealer_hand.append(self.deck.pop())
        self.game_over = True
        await self.update_message(interaction)

    async def on_timeout(self):
        self.clear_items()

class BlackjackCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="blackjack")
    async def blackjack(self, interaction: discord.Interaction, bet:int):
        bank: BankCog = self.bot.get_cog('BankCog')
        
        if bet < 1:
            await interaction.response.send_message(content="Nii väikese panusega sind mängu ei võeta!")
            return
        
        balance = bank.get_balance(interaction.user)
        if bet > balance:
            await interaction.response.send_message(content=f"Jää oma võimekuse piiridesse! (max panus sulle: {balance})")
            return

        bank.withdraw(interaction.user, bet)
        bank.withdraw_limitless(self.bot.user, bet)

        deck = create_deck()
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop()]
        content = (
            f"**Sinu kaardid:** {' '.join(player_hand)} (kokku: {hand_value(player_hand)})\n"
            f"**Diileri kaardid:** {' '.join(dealer_hand)}"
        )
        view = BlackjackView(interaction.user, bank, self.bot, deck, player_hand, dealer_hand, bet)
        view.message = await interaction.response.send_message(content=content, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(BlackjackCog(bot))