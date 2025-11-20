import discord
from discord.ext import commands
from discord import app_commands
import io
import logging


class ImpersonateCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="react")
    async def react_cmd(self, interaction: discord.Interaction, message_id: str, emoji: str):
        """Add a reaction to a message
        
        Parameters
        -----------
        message_id: str
            The ID of the message to react to
        emoji: str
            The emoji ID to react with
        """
        try:
            message = await interaction.channel.fetch_message(int(message_id))
            emoji_obj = self.bot.get_emoji(int(emoji))
            
            if not emoji_obj:
                await interaction.response.send_message(content="Invalid emoji ID.", ephemeral=True)
                return
            
            await message.add_reaction(emoji_obj)
            await interaction.response.send_message(content="Reaction added!", ephemeral=True)
            
            logging.debug('react command called by {author_name}({author_id})', 
                         author_name=interaction.user.global_name, 
                         author_id=interaction.user.id, 
                         msg_id=message_id, 
                         emoji_id=emoji)
        except discord.NotFound:
            await interaction.response.send_message(content="Message not found.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message(content="Invalid message ID or emoji ID.", ephemeral=True)
        except Exception as e:
            logging.error(f"Error in react command: {e}")
            await interaction.response.send_message(content="An error occurred.", ephemeral=True)

    @app_commands.command(name="impersonate")
    async def impersonate_cmd(self, interaction: discord.Interaction, text: str = None, image: discord.Attachment = None):
        """Send a message and delete the command
        
        Parameters
        -----------
        text: str
            The text to send (optional)
        image: discord.Attachment
            The image to send (optional)
        """
        logging.debug('impersonate command called by {author_name}({author_id})', 
                     author_name=interaction.user.global_name, 
                     author_id=interaction.user.id)
        
        if not text and not image:
            await interaction.response.send_message(content="Please provide either text or an image.", ephemeral=True)
            return
        
        # Respond ephemerally first to acknowledge the command
        await interaction.response.send_message(content="Message sent!", ephemeral=True)
        
        # Send the actual message
        files = []
        if image:
            image_bytes = await image.read()
            files.append(discord.File(fp=io.BytesIO(image_bytes), filename=image.filename))
        
        await interaction.channel.send(content=text, files=files if files else None)


async def setup(bot: commands.Bot):
    await bot.add_cog(ImpersonateCog(bot))
