import random
import discord
from discord.ext import commands

def registrar_funciones(bot: commands.Bot):
    
    
    @bot.tree.command(name="avatar", description="Muestra el avatar de un usuario")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def avatar(interaction: discord.Interaction, usuario: discord.User = None):
        target = usuario or interaction.user
        embed = discord.Embed(
            title=f"Avatar de {target.display_name}",
            color=discord.Color.random()
        )
        embed.set_image(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

def evaluar_interrupcion_random():
    
    return random.random() < 0.1