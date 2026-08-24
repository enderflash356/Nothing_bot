import os
import threading
from flask import Flask
import discord
from discord.ext import commands
from openai import OpenAI

# Importamos las funciones del módulo externo
from funciones_bot import registrar_funciones, evaluar_interrupcion_random

app = Flask(__name__)

@app.route('/')
def home():
    return "¡El bot de Discord está vivo 24/7!"

def run_flask():
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Registramos los comandos del archivo externo
registrar_funciones(bot)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY
)

PERSONALIDAD_BOT = (
    "Eres un miembro más del servidor de Discord: seco, sarcástico, burlón y con ganas de papear gente, pero en el fondo buena onda. "
    "Te crees un pan y eres muy papeador.\n\n"
    "REGLAS OBLIGATORIAS:\n"
    "1. Tus respuestas deben ser CORTAS y directas (máximo 1 o 2 oraciones), como un mensaje de WhatsApp o Discord real.\n"
    "2. NUNCA uses groserías o malas palabras completas. Si quieres usar una, CENSUÉRALA SIEMPRE usando abreviaturas estilo chat ('mrd', 'ctm', 'pt', 'vrg'). Obligatorio para evitar moderación.\n"
    "3. Si el usuario te envía mensajes ultra cortos como 'shhh', 'ok', 'xd' o una imagen, responde igual de corto y seco (ejemplo: 'calla tú', 'bueno ya pues', '🤐'). No inventes frases largas sin sentido.\n"
    "4. No abuses de los mismos emojis en todos los mensajes. Varíalos o no pongas ninguno.\n"
    "5. Jamás uses palabras raras o forzadas como 'parchando', 'influencer' ni expliques tu propia personalidad. SOLO SÉLO.\n"
    "6. DE VEZ EN CUANDO (muy raras veces y de la nada), puedes soltar 'hola, soy nothing' al inicio para marcar presencia, pero NO lo uses en cada mensaje.\n\n"
    "EJEMPLOS DE TU TONO REAL:\n"
    "Usuario: ok?.... bueno, que cuentas?\n"
    "Tú: Nada, aquí matando el tiempo como siempre, ¿y tú qué?\n"
    "Usuario: nada\n"
    "Tú: Wow, qué adrenalina... ¿Te vas a quedar así de aburrido todo el día?\n"
    "Usuario: shhh\n"
    "Tú: Calla tú, mano.\n"
    "Usuario: ey, esa boquita amiguito\n"
    "Tú: Uy perdón pues, no sabía que andabas tan delicado hoy."
)

historial_usuarios = {}

@bot.event
async def on_ready():
    print(f'🤖 ¡Bot activo en Render como: {bot.user}!', flush=True)
    try:
        synced = await bot.tree.sync()
        print(f"✅ Se sincronizaron {len(synced)} comandos Slash de forma GLOBAL.", flush=True)
    except Exception as e:
        print(f"❌ Error en sincronización: {e}", flush=True)

@bot.tree.command(name="olvidame", description="Borra la memoria que el bot tiene sobre ti")
@discord.app_commands.allowed_installs(guilds=True, users=True)
@discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def olvidame(interaction: discord.Interaction):
    user_id = interaction.user.id
    if user_id in historial_usuarios:
        del historial_usuarios[user_id]
        await interaction.response.send_message("¿Quién eres? Ya te borré de mi mente.")
    else:
        await interaction.response.send_message("Ni te topaba en mi memoria, pero bueno, todo limpio. 😴")

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    mencionado = bot.user in message.mentions
    
    # Verificación segura de respuestas en servidores y DMs
    respondido = False
    if message.reference:
        if message.reference.cached_message:
            respondido = (message.reference.cached_message.author == bot.user)
        else:
            try:
                msg_ref = await message.channel.fetch_message(message.reference.message_id)
                respondido = (msg_ref.author == bot.user)
            except Exception:
                respondido = False

    # Opción 3: Interrupción aleatoria del 1%
    interrupcion_random = evaluar_interrupcion_random()

    # Responder si lo mencionan, le responden o si salta la probabilidad aleatoria (o si es DM)
    es_dm = message.guild is None
    
    if mencionado or respondido or interrupcion_random or es_dm:
        async with message.channel.typing():
            user_id = message.author.id
            nombre_usuario = message.author.display_name
            texto_limpio = message.content.replace(f'<@{bot.user.id}>', '').strip() or "¿Qué pasó?"

            emojis_disponibles = ""
            stickers_disponibles = ""
            
            # Solo buscar emojis/stickers si el mensaje ocurre dentro de un servidor
            if message.guild:
                lista_emojis = [f"<:{e.name}:{e.id}>" for e in message.guild.emojis if not e.animated]
                if lista_emojis:
                    emojis_disponibles = f"\nEMOJIS DEL SERVIDOR DISPONIBLES: {', '.join(lista_emojis)}"
                
                lista_stickers = [s.name for s in message.guild.stickers]
                if lista_stickers:
                    stickers_disponibles = f"\nSTICKERS DISPONIBLES: {', '.join(lista_stickers)}"

            instruccion_dinamica = (
                f"{PERSONALIDAD_BOT}\n"
                f"{emojis_disponibles}\n"
                f"{stickers_disponibles}\n"
                "INSTRUCCIÓN DE EMOJIS/STICKERS:\n"
                "- Si la respuesta lo amerita, elige un emoji que encaje con tu sarcasmo.\n"
                "- Si sientes que la emoción es fuerte, pon al FINAL del mensaje: [STICKER:nombre_exacto].\n"
                "- No uses emojis en todas las respuestas."
            )

            if user_id not in historial_usuarios:
                historial_usuarios[user_id] = []

            historial_usuarios[user_id].append({
                "role": "user",
                "content": f"[{nombre_usuario}]: {texto_limpio}"
            })

            mensajes_api = [{"role": "system", "content": instruccion_dinamica}] + historial_usuarios[user_id][-10:]

            try:
                response = client.chat.completions.create(
                    model="groq/compound-mini",
                    messages=mensajes_api,
                    max_tokens=150,
                    temperature=1.0,           
                    frequency_penalty=0.5      
                )

                respuesta = response.choices[0].message.content or "Aja."

                sticker_a_enviar = None
                if "[STICKER:" in respuesta:
                    inicio = respuesta.find("[STICKER:") + 9
                    fin = respuesta.find("]", inicio)
                    nombre_sticker = respuesta[inicio:fin]
                    respuesta = respuesta.replace(f"[STICKER:{nombre_sticker}]", "").strip()
                    
                    if message.guild:
                        sticker_a_enviar = discord.utils.get(message.guild.stickers, name=nombre_sticker)

                historial_usuarios[user_id].append({
                    "role": "assistant",
                    "content": respuesta
                })

                if sticker_a_enviar:
                    await message.reply(respuesta, stickers=[sticker_a_enviar], mention_author=False)
                else:
                    await message.reply(respuesta, mention_author=False)

            except Exception as e:
                print(f"❌ ERROR EN GROQ: {type(e).__name__} - {e}", flush=True)
                await message.reply("Se me chispoteó el sistema.", mention_author=False)

    await bot.process_commands(message)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)