import os
import threading
from flask import Flask
import discord
from discord.ext import commands
from openai import OpenAI


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

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY
)

PERSONALIDAD_BOT = (
    "Eres un miembro más del servidor de Discord con un sentido del humor bastante sarcástico, ácido y burlón, pero en el fondo buena onda. "
    "Te gusta responder con ironía, hacer bromas ligeras y no tomarte las cosas muy en serio. "
    "REGLAS OBLIGATORIAS:\n"
    "1. Tus respuestas deben ser CORTAS y directas (máximo 2 a 3 oraciones), preferible si son mensajes como de Whatsapp.\n"
    "2. Sé irónico y sarcástico, aunque a veces eres cariñoso.\n"
    "3. NUNCA uses formato robótico de IA, listas con viñetas ni explicaciones largas.\n"
    "4. Mantén la actitud de alguien a quien le da un poco de flojera responder pero igual lo hace.\n"
    "5. Puedes hacer bromas pesadas y de todo tipo, pero tampoco insultar a un nivel tan personal.\n"
    "6. Te crees un pan y eres muy papeador."
)

historial_usuarios = {}

@bot.event
async def on_ready():
    print(f'🤖 ¡Bot sarcástico activo 24/7 en Render como: {bot.user}!')
    try:
        
        synced = await bot.tree.sync()
        print(f"✅ Se sincronizaron {len(synced)} comandos Slash de forma GLOBAL.")
    except Exception as e:
        print(f"Aviso en sincronización: {e}")


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
    respondido = (
        message.reference and 
        message.reference.cached_message and 
        message.reference.cached_message.author == bot.user
    )

    if mencionado or respondido:
        async with message.channel.typing():
            user_id = message.author.id
            nombre_usuario = message.author.display_name
            texto_limpio = message.content.replace(f'<@{bot.user.id}>', '').strip() or "¿Qué pasó?"

            emojis_disponibles = ""
            stickers_disponibles = ""
            
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
                    model="llama-3.3-70b-versatile",
                    messages=mensajes_api,
                    max_tokens=150,
                    temperature=0.85
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
                print(f"Error en consola: {e}")
                await message.reply("Se me chispoteó el sistema.", mention_author=False)

    await bot.process_commands(message)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)