import discord
from discord.ext import commands
from discord import app_commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Muestra los comandos disponibles para miembros")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📋 Comandos disponibles",
            color=0x3b82f6,
        )

        music = (
            "`/play <nombre o url>` — Reproducir música\n"
            "`/spotify <url>` — Reproducir playlist de Spotify\n"
            "`/skip` — Saltar canción\n"
            "`/stop` — Detener y salir\n"
            "`/queue` — Ver cola\n"
            "`/pause` — Pausar\n"
            "`/resume` — Reanudar"
        )
        embed.add_field(name="🎵 Música", value=music, inline=False)

        ia = (
            "`/ask <pregunta>` — Preguntar a la IA\n"
            "`/reset` — Reiniciar conversación\n"
            "`/imagine <texto>` — Generar imagen"
        )
        embed.add_field(name="🤖 IA", value=ia, inline=False)

        otros = (
            "`/close` — Cerrar tu ticket\n"
            "`/mod warnings <usuario>` — Ver regaños\n"
            "`/help` — Este mensaje"
        )
        embed.add_field(name="📌 Otros", value=otros, inline=False)

        embed.set_footer(text="ZentroxDev © 2026")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Help(bot))
