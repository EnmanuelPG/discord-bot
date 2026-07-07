import discord
from discord.ext import commands
from discord import app_commands
import config

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix=None, intents=intents)

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
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

async def main():
    async with bot:
        await bot.load_extension("cogs.music")
        await bot.load_extension("cogs.ai_chat")
        await bot.start(config.DISCORD_TOKEN)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
