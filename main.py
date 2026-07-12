import os
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import config
from aiohttp import web
from cogs.tickets import PEDIDOS_CHANNEL_ID

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

bot = commands.Bot(command_prefix=None, intents=intents)
GUILD_ID = int(config.GUILD_ID) if config.GUILD_ID else None

_target_guild = None
_bot_ready = asyncio.Event()

async def get_target_guild():
    if _target_guild:
        return _target_guild
    try:
        await asyncio.wait_for(_bot_ready.wait(), timeout=30)
    except asyncio.TimeoutError:
        return _target_guild
    return _target_guild

@bot.event
async def on_ready():
    global _target_guild
    print(f"Bot conectado como {bot.user}")
    if GUILD_ID:
        _target_guild = bot.get_guild(GUILD_ID)
    if not _target_guild:
        channel = bot.get_channel(PEDIDOS_CHANNEL_ID)
        if channel and channel.guild:
            _target_guild = channel.guild
    if not _target_guild and bot.guilds:
        _target_guild = bot.guilds[0]
    _bot_ready.set()
    try:
        synced_global = await bot.tree.sync()
        print(f"Comandos globales sincronizados: {len(synced_global)}")
        if config.GUILD_ID:
            guild = discord.Object(id=int(config.GUILD_ID))
            bot.tree.copy_global_to(guild=guild)
            synced_guild = await bot.tree.sync(guild=guild)
            print(f"Comandos sincronizados al servidor {config.GUILD_ID}: {len(synced_guild)}")
    except Exception as e:
        print(f"Error al sincronizar comandos: {e}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    error_msg = f"Error inesperado: {error}"
    print(error_msg)
    try:
        if not interaction.response.is_done():
            await interaction.response.send_message(error_msg, ephemeral=True)
        else:
            await interaction.followup.send(error_msg, ephemeral=True)
    except:
        pass

async def find_member(guild, username):
    if not username:
        return None
    if username.isdigit() and len(username) == 18:
        m = guild.get_member(int(username))
        if m: return m
    m = guild.get_member_named(username)
    if m: return m
    lower = username.lower().lstrip('@')
    for m in guild.members:
        if m.name.lower() == lower or m.display_name.lower() == lower:
            return m
    for m in guild.members:
        if lower in m.name.lower() or lower in m.display_name.lower():
            return m
    return None

async def handle_verify_user(request):
    try:
        data = await request.json()
        username = data.get("username", "").strip()
    except:
        return cors_response(web.json_response({"exists": False, "error": "Invalid JSON"}, status=400))
    if not username:
        return cors_response(web.json_response({"exists": False, "error": "Username required"}, status=400))
    guild = await get_target_guild()
    if not guild:
        return cors_response(web.json_response({"exists": False, "error": "Guild not found"}, status=500))
    member = await find_member(guild, username)
    return cors_response(web.json_response({
        "exists": member is not None,
        "username": member.name if member else None,
        "display_name": member.display_name if member else None,
        "id": str(member.id) if member else None,
    }))

async def handle_create_order(request):
    from cogs.tickets import create_ticket_channel, WEB_CATEGORY_ID, check_daily_limit, increment_daily_count, MAX_TICKETS_PER_DAY
    try:
        data = await request.json()
    except:
        return cors_response(web.json_response({"ok": False, "error": "Invalid JSON"}, status=400))
    ticket_id = data.get("ticket_id", "").strip()
    service_name = data.get("service_name", "").strip()
    detalle = data.get("detalle", "").strip()
    metodo = data.get("metodo", "").strip()
    usuario = data.get("usuario", "").strip()
    if not all([ticket_id, service_name, usuario]):
        return cors_response(web.json_response({"ok": False, "error": "Missing required fields"}, status=400))
    guild = await get_target_guild()
    if not guild:
        return cors_response(web.json_response({"ok": False, "error": "Guild not found"}, status=500))
    member = await find_member(guild, usuario)
    if not member:
        return cors_response(web.json_response({
            "ok": False, "error": "USER_NOT_FOUND",
            "message": f"El usuario '{usuario}' no está en el servidor de Discord."
        }, status=400))
    allowed, used = check_daily_limit(member.id)
    if not allowed:
        return cors_response(web.json_response({
            "ok": False, "error": "LIMIT_REACHED",
            "message": f"Ya has usado tus {MAX_TICKETS_PER_DAY} tickets hoy. Vuelve mañana."
        }, status=429))
    dummy_embed = discord.Embed(title=f"📦 {service_name}")
    ticket_channel, created = await create_ticket_channel(guild, ticket_id, dummy_embed, usuario, category_id=WEB_CATEGORY_ID)
    if not created:
        return cors_response(web.json_response({
            "ok": True, "channel_id": str(ticket_channel.id),
            "channel_mention": ticket_channel.mention,
            "channel_url": ticket_channel.jump_url,
            "message": f"El canal {ticket_channel.mention} ya existía.",
        }))
    from cogs.tickets import send_embed_to_pedidos
    await send_embed_to_pedidos(guild, bot.user, ticket_id, service_name, detalle, metodo, usuario, ticket_channel)
    increment_daily_count(member.id)
    return cors_response(web.json_response({
        "ok": True, "channel_id": str(ticket_channel.id),
        "channel_mention": ticket_channel.mention,
        "channel_url": ticket_channel.jump_url,
        "message": f"✅ Ticket {ticket_id} creado → {ticket_channel.mention}",
    }))

async def handle_root(request):
    return web.json_response({"status": "ok", "bot": "running"})

def cors_response(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

async def handle_options(request):
    return cors_response(web.Response())

async def init_http_server():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_post("/api/verify-user", handle_verify_user)
    app.router.add_post("/api/order", handle_create_order)
    app.router.add_route("OPTIONS", "/api/verify-user", handle_options)
    app.router.add_route("OPTIONS", "/api/order", handle_options)
    port = int(os.environ.get("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"HTTP server running on port {port}")
    return runner

async def run_bot():
    for cog in ("cogs.music", "cogs.ai_chat", "cogs.tickets"):
        try:
            await bot.load_extension(cog)
        except Exception as e:
            print(f"Error loading {e}: {e}")
    try:
        await bot.start(config.DISCORD_TOKEN)
    except Exception as e:
        print(f"Bot error (HTTP server keeps running): {e}")

async def main():
    http_runner = await init_http_server()
    bot_task = asyncio.create_task(run_bot())
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        try:
            await bot.close()
        except Exception:
            pass
        bot_task.cancel()
    finally:
        await http_runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
