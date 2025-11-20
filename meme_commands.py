import discord
from discord.ext import commands
from discord import app_commands
from typing import Literal
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.python.solutions.drawing_utils import _normalized_to_pixel_coordinates
import io
import logging

from instantmeme import (
    get_img_from_attachment,
    get_faces,
    draw_masks_on_faces,
    draw_specific_points_on_faces,
    draw_letters_on_faces,
    send_img_to_channel
)


class MemeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="mask")
    async def mask_cmd(self, interaction: discord.Interaction, image: discord.Attachment):
        """Draw masks on all face landmarks
        
        Parameters
        -----------
        image: discord.Attachment
            The image to process
        """
        if not any(image.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg']):
            await interaction.response.send_message(content="Please provide a valid image file (PNG, JPG, or JPEG).")
            return

        await interaction.response.defer()
        
        try:
            img = await get_img_from_attachment(image)
            faces = get_faces(img)

            if not faces.multi_face_landmarks:
                await interaction.followup.send(content="No faces detected in the image.")
                return

            draw_masks_on_faces(img, faces)
            
            _, buffer = cv2.imencode('.png', img)
            output_bytes = buffer.tobytes()
            await interaction.followup.send(file=discord.File(fp=io.BytesIO(output_bytes), filename='output.png'))
        except Exception as e:
            logging.error(f"Error processing mask command: {e}")
            await interaction.followup.send(content="Error processing the image.")

    @app_commands.command(name="eyes")
    async def eyes_cmd(self, interaction: discord.Interaction, image: discord.Attachment):
        """Draw specific points on face (eyes)
        
        Parameters
        -----------
        image: discord.Attachment
            The image to process
        """
        if not any(image.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg']):
            await interaction.response.send_message(content="Please provide a valid image file (PNG, JPG, or JPEG).")
            return

        await interaction.response.defer()
        
        try:
            img = await get_img_from_attachment(image)
            faces = get_faces(img)

            if not faces.multi_face_landmarks:
                await interaction.followup.send(content="No faces detected in the image.")
                return

            draw_specific_points_on_faces(img, faces)
            
            _, buffer = cv2.imencode('.png', img)
            output_bytes = buffer.tobytes()
            await interaction.followup.send(file=discord.File(fp=io.BytesIO(output_bytes), filename='output.png'))
        except Exception as e:
            logging.error(f"Error processing eyes command: {e}")
            await interaction.followup.send(content="Error processing the image.")

    @app_commands.command(name="explain")
    async def explain_cmd(self, interaction: discord.Interaction, image: discord.Attachment, mode: Literal['minimal', 'full']):
        """Draw letters on face landmarks for debugging
        
        Parameters
        -----------
        image: discord.Attachment
            The image to process
        mode: Literal['minimal', 'full']
            Minimal shows only key points, full shows all landmarks
        """
        if not any(image.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg']):
            await interaction.response.send_message(content="Please provide a valid image file (PNG, JPG, or JPEG).")
            return

        await interaction.response.defer()
        
        try:
            img = await get_img_from_attachment(image)
            faces = get_faces(img)

            if not faces.multi_face_landmarks:
                await interaction.followup.send(content="No faces detected in the image.")
                return

            if mode == 'minimal':
                draw_letters_on_faces(img, faces, '')
            else:
                draw_letters_on_faces(img, faces)
            
            _, buffer = cv2.imencode('.png', img)
            output_bytes = buffer.tobytes()
            await interaction.followup.send(file=discord.File(fp=io.BytesIO(output_bytes), filename='output.png'))
        except Exception as e:
            logging.error(f"Error processing explain command: {e}")
            await interaction.followup.send(content="Error processing the image.")


async def setup(bot: commands.Bot):
    await bot.add_cog(MemeCog(bot))
