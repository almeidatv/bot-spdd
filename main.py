import discord
from discord.ext import commands
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from keep_alive import keep_alive
from collections import Counter

# Iniciar servidor web para manter o bot online
keep_alive()

# Carregar configurações
with open("config.json", "r") as f:
    config = json.load(f)

TOKEN = config["TOKEN"]
SHEET_ID = config["SHEET_ID"]
GUILD_ID = int(config["GUILD_ID"])
CHANNEL_ID = int(config["CHANNEL_ID"])
LOG_CHANNEL_ID = int(config["LOG_CHANNEL_ID"])
MENTION_ROLE_ID = int(config["MENTION_ROLE_ID"])  # Cargo que será mencionado no ranking

# Conectar ao Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("credenciais.json", scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).sheet1

# Criar bot
intents = discord.Intents.default()
intents.reactions = True
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    log_channel = bot.get_channel(LOG_CHANNEL_ID)
    print(f"🤖 Bot conectado como {bot.user}")
    if log_channel:
        await log_channel.send("<@773328699910127656> ✅ Bot iniciado e registrando reações normalmente!")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.channel_id != CHANNEL_ID:
        return

    try:
        guild = discord.utils.get(bot.guilds, id=GUILD_ID)
        channel = guild.get_channel(CHANNEL_ID)
        message = await channel.fetch_message(payload.message_id)
        user = payload.member

        sheet.append_row([
            str(user),  # Coluna 'user'
            str(payload.emoji),
            str(message.id),
            str(message.content)
        ])

        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"📥 **{user}** reagiu com {payload.emoji} à mensagem:\n> {message.content}")

    except Exception as e:
        log_channel = bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            await log_channel.send(f"❌ Erro ao registrar reação: `{e}`")
        print("Erro ao registrar reação:", e)

# Comando para contar total de reações
@bot.command(name="total")
async def total(ctx):
    registros = sheet.get_all_records()
    await ctx.send(f"📊 Total de reações registradas: **{len(registros)}**")

# Comando para gerar ranking dos usuários mais ativos
@bot.command(name="ranking")
async def ranking(ctx):
    try:
        registros = sheet.get_all_records()

        if not registros:
            await ctx.send("❌ Nenhum registro encontrado na planilha.")
            return

        # Normalizar nomes de colunas (remover espaços)
        registros_corrigidos = []
        for r in registros:
            r_corrigido = {k.strip(): v for k, v in r.items()}
            registros_corrigidos.append(r_corrigido)

        usuarios = [r["user"] for r in registros_corrigidos if r.get("user")]

        contador = Counter(usuarios)
        ranking = contador.most_common(10)

        role_mention = f"<@&{MENTION_ROLE_ID}>"
        mensagem = f"🏆 Ranking dos membros {role_mention} mais ativos:\n\n"

        for i, (usuario_nome, total) in enumerate(ranking, start=1):
            membro_mentionado = None
            for membro in ctx.guild.members:
                if str(membro) == usuario_nome:
                    membro_mentionado = membro.mention
                    break
            nome_final = membro_mentionado if membro_mentionado else usuario_nome
            mensagem += f"**{i}.** {nome_final} — **{total}** reações\n"

        await ctx.send(mensagem)

    except KeyError:
        await ctx.send("❌ Não foi possível encontrar a coluna de usuário na planilha. Verifique se a primeira linha tem uma célula chamada `user` (sem espaços).")
    except Exception as e:
        await ctx.send(f"⚠️ Erro ao gerar ranking: `{e}`")

# Iniciar bot
bot.run(TOKEN)
