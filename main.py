import os
import threading
from flask import Flask
import discord
from discord.ext import commands
from groq import Groq
import google.generativeai as genai
from openai import OpenAI
import cohere
import re
from cerebras.cloud.sdk import Cerebras

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

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

client_cerebras = Cerebras(api_key=CEREBRAS_API_KEY) if CEREBRAS_API_KEY else None
client_groq = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

client_openrouter = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
) if OPENROUTER_API_KEY else None
client_cohere = cohere.Client(COHERE_API_KEY) if COHERE_API_KEY else None

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

def mostrar_modelos_disponibles():
    print("==================================================", flush=True)
    print("🔍 REVISANDO MODELOS DE IA DISPONIBLES EN TUS APIS...", flush=True)
    
    if GEMINI_API_KEY:
        try:
            print("--- Google Gemini ---", flush=True)
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    print(f"  • {m.name}", flush=True)
        except Exception as e:
            print(f"  ❌ Error listando Gemini: {e}", flush=True)

    if client_groq:
        try:
            print("--- Groq ---", flush=True)
            modelos_groq = client_groq.models.list().data
            for m in modelos_groq[:5]:
                print(f"  • {m.id}", flush=True)
        except Exception as e:
            print(f"  ❌ Error listando Groq: {e}", flush=True)

    if client_cerebras:
        print("--- Cerebras ---", flush=True)
        print("  • llama3.1-70b\n  • llama3.1-8b", flush=True)

    if client_cohere:
        print("--- Cohere ---", flush=True)
        print("  • command-r-08-2024", flush=True)

    if client_openrouter:
        try:
            print("--- OpenRouter (Modelos configurados) ---", flush=True)
            print("  • meta-llama/llama-3.3-70b-instruct:free\n  • google/gemma-2-9b-it:free\n  • qwen/qwen-2.5-7b-instruct:free", flush=True)
        except Exception as e:
            print(f"  ❌ Error listando OpenRouter: {e}", flush=True)

    print("==================================================", flush=True)


async def obtener_respuesta_ia(mensajes_historial, instruccion_dinamica):

    # INTENTO 0. CEREBRAS (Ultra rápido)
    if client_cerebras:
        modelos_cerebras = ["llama3.1-70b", "llama3.1-8b"]
        for mod in modelos_cerebras:
            try:
                print(f"🧠 Probando Cerebras ({mod})...", flush=True)
                payload = [{"role": "system", "content": instruccion_dinamica}] + mensajes_historial
                response = client_cerebras.chat.completions.create(
                    model=mod,
                    messages=payload,
                    max_tokens=150,
                    temperature=0.7
                )
                res = response.choices[0].message.content
                if res:
                    return res
            except Exception as e:
                print(f"⚠️ Cerebras ({mod}) falló. Probando siguiente...", flush=True)

    # INTENTO 1. GROQ
    if client_groq:
        try:
            modelos_groq = [m.id for m in client_groq.models.list().data]
            modelos_chat = [
                m for m in modelos_groq 
                if not any(x in m.lower() for x in [
                    "prompt-guard", "whisper", "guard", "deepseek", "r1", 
                    "reasoning", "orpheus", "canopylabs", "vision", "audio", "tts"
                ])
            ]
            
            modelo_groq = modelos_chat[0] if modelos_chat else "llama-3.3-70b-versatile"
            print(f"🧠 Usando Groq: {modelo_groq}", flush=True)
            payload = [{"role": "system", "content": instruccion_dinamica}] + mensajes_historial
            response = client_groq.chat.completions.create(
                model=modelo_groq,
                messages=payload,
                max_tokens=150,
                temperature=0.7,
                frequency_penalty=0.6,
                presence_penalty=0.4
            )
            res = response.choices[0].message.content
            if res:
                return res
        except Exception as e:
            print(f"⚠️ Groq falló ({e}). Pasando a Gemini...", flush=True)

    # INTENTO 2. GEMINI (Modelos actualizados 2026)
    if GEMINI_API_KEY:
        modelos_gemini = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        for mod in modelos_gemini:
            try:
                print(f"🧠 Probando Gemini: {mod}", flush=True)
                model = genai.GenerativeModel(
                    model_name=mod,
                    system_instruction=instruccion_dinamica
                )
                
                # Convertir historial al formato oficial de Gemini (user / model)
                historial_gemini = []
                for m in mensajes_historial:
                    role_gemini = "user" if m["role"] == "user" else "model"
                    historial_gemini.append({"role": role_gemini, "parts": [m["content"]]})
                
                chat = model.start_chat(history=historial_gemini[:-1] if len(historial_gemini) > 1 else [])
                ultimo_msg = historial_gemini[-1]["parts"][0] if historial_gemini else "hola"
                
                response = chat.send_message(
                    ultimo_msg,
                    generation_config=genai.types.GenerationConfig(max_output_tokens=150, temperature=0.7)
                )
                if response.text:
                    return response.text
            except Exception as e:
                print(f"⚠️ Gemini ({mod}) falló. Probando siguiente...", flush=True)

    # INTENTO 3. COHERE
    if client_cohere:
        try:
            print("🧠 Probando Cohere...", flush=True)
            prompt_texto = f"{instruccion_dinamica}\n\n" + "\n".join([f"{m['role']}: {m['content']}" for m in mensajes_historial])
            
            response = client_cohere.chat(
                message=prompt_texto,
                model="command-r-08-2024",
                temperature=0.7
            )
            if response.text:
                return response.text
        except Exception as e:
            print(f"⚠️ Cohere falló ({e}). Pasando a OpenRouter...", flush=True)

    # INTENTO 4. OPENROUTER
    if client_openrouter:
        modelos_openrouter = [
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemma-2-9b-it:free",
            "qwen/qwen-2.5-7b-instruct:free"
        ]
        import asyncio
        loop = asyncio.get_running_loop()
        
        for mod in modelos_openrouter:
            try:
                print(f"🧠 Probando OpenRouter: {mod}", flush=True)
                payload = [{"role": "system", "content": instruccion_dinamica}] + mensajes_historial
             
                response = await loop.run_in_executor(
                    None,
                    lambda: client_openrouter.chat.completions.create(
                        model=mod,
                        messages=payload,
                        max_tokens=150,
                        temperature=0.7
                    )
                )
                res = response.choices[0].message.content
                if res:
                    return res
            except Exception as e:
                print(f"⚠️ OpenRouter ({mod}) falló...", flush=True)

    return "ando mzt, me hablas al rato..."

@bot.event
async def on_ready():
    print(f'🤖 ¡Bot activo en Render como: {bot.user}!', flush=True)
    mostrar_modelos_disponibles()
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
                lista_emojis = [f":{e.name}:" for e in message.guild.emojis if not e.animated]
                if lista_emojis:
                    emojis_disponibles = f"\nEMOJIS DISPONIBLES DEL SERVIDOR: {', '.join(lista_emojis)}"
                
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

            # Guardamos la intervención del usuario
            historial_usuarios[user_id].append({
                "role": "user",
                "content": f"{nombre_usuario}: {texto_limpio}"
            })

            respuesta = await obtener_respuesta_ia(historial_usuarios[user_id][-5:], instruccion_dinamica)

            # Limpieza de etiquetas de razonamiento
            respuesta = re.sub(r'<think>.*?</think>', '', respuesta, flags=re.DOTALL)
            respuesta = re.sub(r'<think>.*', '', respuesta, flags=re.DOTALL).strip()

            if not respuesta:
                respuesta = "me dio flojera pensar, luego te respondo."

            if message.guild:
                for emoji in message.guild.emojis:
                    patron = f":{emoji.name}:"
                    if patron in respuesta:
                        formato_real = f"<:{emoji.name}:{emoji.id}>"
                        respuesta = respuesta.replace(patron, formato_real)

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

registrar_funciones(bot, obtener_respuesta_ia)

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)