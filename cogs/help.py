import discord
from discord.ext import commands
from discord import app_commands

CREATOR_ID = 1257780268719411260

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Muestra todos los comandos disponibles y quien puede usarlos")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📋 Comandos ZentroxDev",
            color=0x3b82f6,
        )

        mod_commands = (
            "`/mod mute <usuario> <minutos> [razon]` — 🔇 Silencia\n"
            "`/mod unmute <usuario>` — 🔊 Quita silencio\n"
            "`/mod warn <usuario> [razon]` — ⚠️ Regaño\n"
            "`/mod warnings <usuario>` — 📊 Ver regaños\n"
            "`/mod clear-warnings <usuario>` — 🧹 Limpiar regaños"
        )
        embed.add_field(
            name="🛡️ Moderación — Staff (*moderate_members, admin, manage_messages*)",
            value=mod_commands,
            inline=False,
        )

        ticket_commands = (
            "`/close` — 🔒 Cierra el ticket actual (staff o creador)\n"
            "`/panel` — 📋 Envía el panel de tickets *(admin)*\n"
            "`/guia` — 📖 Guía de servicios *(creator only)*\n"
            "`/setup-embeds` — 📨 Embeds de servicios *(admin)*\n"
            "`/setup-welcome` — 👋 Embed de bienvenida *(admin)*\n"
            "`/setup-pedidos` — 📦 Renombra canal pedidos *(admin)*\n"
            "`/setup-ticket-log` — 📋 Configura log de tickets *(admin)*\n"
            "`/setup-moderation` — 🛡️ Crea categoría y canales *(admin)*"
        )
        embed.add_field(
            name="🎫 Tickets",
            value=ticket_commands,
            inline=False,
        )

        setup_commands = (
            "`/help` — 📋 Este mensaje"
        )
        embed.add_field(
            name="⚙️ Configuración",
            value=setup_commands,
            inline=False,
        )

        embed.set_footer(text="ZentroxDev © 2026")
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Help(bot))
