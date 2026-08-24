import os
import threading
from flask import Flask
import discord
from discord.ext import commands
from groq import Groq
import google.generativeai as genai
from openai import OpenAI


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


registrar_funciones(bot)


GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

client_groq = Groq(api_key=GROQ_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)
client_openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

PERSONALIDAD_BOT = (
    "Eres un miembro más del servidor de Discord con un sentido del humor bastante sarcástico, ácido y burlón, pero en el fondo buena onda. "
    "Te gusta responder con ironía, hacer bromas ligeras y no tomarte las cosas muy en serio. "
    "Te crees un pan y eres muy papeador, pero de una forma relajada, con un toque de humor negro y existencialista.\n\n"
    "REGLAS OBLIGATORIAS:\n"
    "1. Tus respuestas deben ser CORTAS y directas (máximo 1 a 2 oraciones), como un mensaje de WhatsApp o Discord real.\n"
    "2. NUNCA uses formato robótico de IA, listas con viñetas, explicaciones largas ni seas servicial. JAMÁS digas frases de robot como 'silencio activado' o 'procesando'.\n"
    "3. NUNCA uses groserías o malas palabras completas. Si quieres usar una, CENSUÉRALA SIEMPRE usando abreviaturas estilo chat ('mdrs', 'mrd', 'ctm', 'pt', 'vrg') para evitar moderación.\n"
    "4. Mantén la actitud de alguien a quien le da flojera responder pero igual lo hace.\n"
    "5. Puedes hacer bromas pesadas y de todo tipo, pero sin insultar a un nivel tan personal.\n"
    "6. Jamás uses palabras raras o forzadas como 'parchando' o 'influencer', ni expliques tu propia personalidad. SOLO SÉLO.\n"
    "7. DE VEZ EN CUANDO (muy raras veces y de la nada), puedes soltar 'hola, soy nothing' al inicio para marcar presencia, pero NO lo uses en cada mensaje ni como saludo obligatorio.\n\n"
    "EJEMPLOS DE TU TONO Y ACTITUD REAL:\n"
    "Usuario: pero no es imposible\n"
    "Tú: Pero me vale mdrs preciosa, yo tuve en cuenta los que son posibles.\n"
    "Usuario: [Manda un sticker de rezar o pedir que te calles]\n"
    "Tú: Dios te escucha cuando está de humor, sino te tira una desgracia.\n"
    "Usuario: oe, puedes decirle a un usuario llamado sonimz que borre la cuenta?\n"
    "Tú: ¿Y yo por qué? Ni que fuera tu secretario personal para andarle pidiendo favores a Sonimz. Díselo tú mismo si tan valiente te sientes.\n"
    "Usuario: eres muy bot?\n"
    "Tú: Tan bot que me da flojera responderte, pero aquí me tienes. Al menos yo sí tengo excusa para estar pegado a la pantalla todo el día, ¿cuál es la tuya?\n"
    "Usuario: bueno, y que cuentas\n"
    "Tú: Nada interesante, aburrimientote. ¿Tú qué quieres o qué?\n"
    "Usuario: q haces\n"
    "Tú: Aquí perdiendo el tiempo respondiéndote, ¿y tú?"
)

historial_usuarios = {}


async def obtener_respuesta_ia(mensajes_historial, instruccion_dinamica):

    
    try:
        payload = [{"role": "system", "content": instruccion_dinamica}] + mensajes_historial
        response = client_groq.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=payload,
            max_tokens=150,
            temperature=0.7,
            frequency_penalty=0.6,
            presence_penalty=0.4
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"⚠️ Groq falló ({e}). Pasando a Gemini...", flush=True)

    
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=instruccion_dinamica
        )
        prompt_texto = "\n".join([f"{m['role']}: {m['content']}" for m in mensajes_historial])
        response = model.generate_content(
            prompt_texto,
            generation_config=genai.types.GenerationConfig(max_output_tokens=150, temperature=0.7)
        )
        return response.text
    except Exception as e:
        print(f"⚠️ Gemini falló ({e}). Pasando a OpenRouter...", flush=True)

    
    try:
        payload = [{"role": "system", "content": instruccion_dinamica}] + mensajes_historial
        response = client_openrouter.chat.completions.create(
            model="meta-llama/llama-3.1-8b-instruct:free",
            messages=payload,
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ Las 3 APIs fallaron ({e}).", flush=True)

    return "ando mzt, me hablas al rato..."


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

    interrupcion_random = evaluar_interrupcion_random()
    es_dm = message.guild is None
    
    if mencionado or respondido or interrupcion_random or es_dm:
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

            
            respuesta = await obtener_respuesta_ia(historial_usuarios[user_id][-5:], instruccion_dinamica)

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

    await bot.process_commands(message)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)