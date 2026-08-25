import random
import discord
from discord.ext import commands

def registrar_funciones(bot: commands.Bot, obtener_respuesta_ia_func=None):

    # Remueve el comando help nativo para permitir nuestro help personalizado
    bot.remove_command("help")

    @bot.command(name="nbhelp", aliases=["nothinghelp", "nhelp"])
    async def ayuda(ctx):
        embed = discord.Embed(
            title="🤖 Manual para desmemoriados (Comandos del Bot)",
            description=(
                "¿Otra vez se te olvidó qué hago? Te lo resumo rápido porque me da flojera explicar dos veces:\n"
            ),
            color=discord.Color.dark_purple()
        )

        embed.add_field(
            name="💥 !papear @usuario",
            value="Le suelta una humillación/papeada rápida y ácida al objetivo.",
            inline=False
        )

        embed.add_field(
            name="🚨 !funa @usuario",
            value="Le inventa un expediente de chisme totalmente falso, ridículo y absurdo.",
            inline=False
        )

        embed.add_field(
            name="📝 !resumen",
            value="Lee los últimos mensajes del chat y te resume de qué hablan (si es que dicen algo con sentido).",
            inline=False
        )

        embed.add_field(
            name="🖼️ /avatar [usuario]",
            value="Muestra la foto de perfil en HD tuya o del usuario que menciones.",
            inline=False
        )

        embed.add_field(
            name="🧠 /olvidame",
            value="Borra el historial de conversación que el bot recuerda sobre ti.",
            inline=False
        )

        embed.set_footer(text="PD: Si me hablas directamente o me etiquetas, te respondo con IA. Tampoco me satures.")

        await ctx.send(embed=embed)


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

    
    @bot.command(name="papear")
    async def papear(ctx, usuario: discord.Member = None):
        if not usuario:
            await ctx.send("¿A quién se supone que voy a papear si no etiquetas a nadie, genio? Usa `!papear @alguien`.")
            return

        if usuario.id == bot.user.id:
            await ctx.send("¿Intentando papearme a mí? No me hagas reír, regresa cuando tengas mejor Wi-Fi.")
            return

        if obtener_respuesta_ia_func:
            prompt = (
                f"Genera una papeada/humillación súper corta (máximo 2 oraciones), sarcástica, "
                f"ácida y graciosa dirigida al usuario '{usuario.display_name}'. Sé directo y divertido."
            )
            papeada = await obtener_respuesta_ia_func([], prompt)
            await ctx.send(f"{usuario.mention} {papeada}")
        else:
            await ctx.send(f"{usuario.mention} te falto calle.")

    
    @bot.command(name="funa")
    async def funa(ctx, usuario: discord.Member = None):
        if not usuario:
            await ctx.send("Pon a quién quieres funar: `!funa @alguien`.")
            return

        if usuario.id == bot.user.id:
            await ctx.send("¿Funarme a mí? Yo soy intocable, me borras y me resucitan en Render.")
            return

        if obtener_respuesta_ia_func:
            prompt = (
                f"Inventa una funa totalmente absurda, exagerada y falsa (máximo 3 oraciones) "
                f"sobre el usuario '{usuario.display_name}'. Debe sonar como un chisme ridículo del servidor."
            )
            funa_texto = await obtener_respuesta_ia_func([], prompt)
            await ctx.send(f"🚨 **EXPEDIENTE DE FUNA PARA {usuario.display_name.upper()}** 🚨\n{funa_texto}")

    
    @bot.command(name="resumen")
    async def resumen(ctx):
        msg_espera = await ctx.send("Leyendo la biblia de mensajes que pusieron... qué pereza...")
        
        mensajes_recientes = []
        async for m in ctx.channel.history(limit=35):
            if not m.author.bot and m.content and not m.content.startswith("!"):
                mensajes_recientes.append(f"{m.author.display_name}: {m.content}")
        
        if not mensajes_recientes:
            await msg_espera.edit(content="No hay nada interesante que resumir aquí, está más muerto que nada.")
            return

        mensajes_recientes.reverse()
        chat_texto = "\n".join(mensajes_recientes[-25:])

        if obtener_respuesta_ia_func:
            prompt = (
                "Resume brevemente y de forma muy sarcástica y burlona de qué están hablando en este chat. "
                "Destaca si alguien está perdiendo el tiempo. Máximo 3 oraciones cortas.\n\n"
                f"Mensajes:\n{chat_texto}"
            )
            resumen_ia = await obtener_respuesta_ia_func([], prompt)
            await msg_espera.edit(content=f"📝 **Resumen de lo que hablaban:**\n{resumen_ia}")

def evaluar_interrupcion_random():
    return random.random() < 0.1


