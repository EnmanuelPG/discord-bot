import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import timedelta, datetime

WARNINGS_FILE = "warnings.json"

def _load_warnings():
    if not os.path.exists(WARNINGS_FILE):
        return {}
    try:
        with open(WARNINGS_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def _save_warnings(data):
    with open(WARNINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def _get_warnings(guild_id, user_id):
    data = _load_warnings()
    return data.get(str(guild_id), {}).get(str(user_id), [])

def _add_warning(guild_id, user_id, moderator_id, reason):
    data = _load_warnings()
    g = data.setdefault(str(guild_id), {})
    u = g.setdefault(str(user_id), [])
    u.append({
        "mod": moderator_id,
        "razon": reason or "No especificada",
        "fecha": datetime.utcnow().isoformat(),
    })
    _save_warnings(data)
    return len(u)

def _clear_warnings(guild_id, user_id):
    data = _load_warnings()
    g = data.get(str(guild_id))
    if g:
        g.pop(str(user_id), None)
    _save_warnings(data)


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="mute", description="Mutea a un usuario por tiempo")
    @app_commands.default_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, usuario: discord.Member, minutos: int, razon: str = None):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
        if not interaction.guild.me.guild_permissions.moderate_members:
            return await interaction.response.send_message("❌ No tengo permiso para mutear.", ephemeral=True)
        if usuario.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            return await interaction.response.send_message("❌ No puedes mutear a alguien con igual o mayor rol.", ephemeral=True)
        if minutos < 1 or minutos > 40320:
            return await interaction.response.send_message("❌ El tiempo debe estar entre 1 minuto y 28 días.", ephemeral=True)

        try:
            await usuario.timeout(timedelta(minutes=minutos), reason=razon)
            txt = f"🔇 **{usuario.mention} muteado por {minutos} minuto(s)**"
            if razon:
                txt += f"\n📝 Razón: {razon}"
            await interaction.response.send_message(txt)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error al mutear: {e}", ephemeral=True)

    @app_commands.command(name="warn", description="Añade un regaño/advertencia a un usuario")
    @app_commands.default_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, usuario: discord.Member, razon: str = None):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
        if usuario.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            return await interaction.response.send_message("❌ No puedes advertir a alguien con igual o mayor rol.", ephemeral=True)

        total = _add_warning(interaction.guild.id, usuario.id, interaction.user.id, razon)
        embed = discord.Embed(
            title="⚠️ Regaño / Advertencia",
            description=f"**Usuario:** {usuario.mention}\n**Moderador:** {interaction.user.mention}",
            color=0xf59e0b,
        )
        if razon:
            embed.add_field(name="📝 Razón", value=razon, inline=False)
        embed.add_field(name="📊 Total de regaños", value=str(total), inline=False)
        embed.set_footer(text=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
        await interaction.response.send_message(embed=embed)

        if total == 3:
            try:
                await usuario.timeout(timedelta(hours=1), reason=f"3 regaños automático")
                await interaction.channel.send(f"🔇 **{usuario.mention} muteado 1 hora por acumular 3 regaños.**")
            except Exception:
                pass

    @app_commands.command(name="warnings", description="Muestra los regaños de un usuario")
    async def warnings(self, interaction: discord.Interaction, usuario: discord.Member):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)

        warns = _get_warnings(interaction.guild.id, usuario.id)
        if not warns:
            return await interaction.response.send_message(f"✅ **{usuario.display_name}** no tiene regaños.", ephemeral=True)

        embed = discord.Embed(
            title=f"⚠️ Regaños de {usuario.display_name}",
            description=f"**Total: {len(warns)}**",
            color=0xf59e0b,
        )
        for i, w in enumerate(warns, 1):
            mod = interaction.guild.get_member(int(w["mod"]))
            mod_name = mod.mention if mod else f"<@{w['mod']}>"
            fecha = w["fecha"][:19].replace("T", " ")
            embed.add_field(
                name=f"#{i} — {fecha}",
                value=f"**Mod:** {mod_name}\n**Razón:** {w['razon']}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
