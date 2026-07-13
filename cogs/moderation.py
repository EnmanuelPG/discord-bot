import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from datetime import timedelta, datetime

WARNINGS_FILE = "warnings.json"
MOD_CATEGORY_NAME = "🛡️ Moderación"
SANCTIONS_CHANNEL_NAME = "sanciones"
APPEALS_CHANNEL_NAME = "apelaciones"

SANCTIONS_CHANNEL_ID = None
APPEALS_CHANNEL_ID = None

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

def _load_config():
    global SANCTIONS_CHANNEL_ID, APPEALS_CHANNEL_ID
    if os.path.exists("mod_config.json"):
        try:
            with open("mod_config.json") as f:
                cfg = json.load(f)
                SANCTIONS_CHANNEL_ID = cfg.get("sanctions")
                APPEALS_CHANNEL_ID = cfg.get("appeals")
        except Exception:
            pass

def _save_config():
    with open("mod_config.json", "w") as f:
        json.dump({"sanctions": SANCTIONS_CHANNEL_ID, "appeals": APPEALS_CHANNEL_ID}, f)

async def _log_to_sanctions(guild, embed):
    if not SANCTIONS_CHANNEL_ID:
        return
    ch = guild.get_channel(SANCTIONS_CHANNEL_ID)
    if ch:
        try:
            await ch.send(embed=embed)
        except Exception:
            pass


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        _load_config()

    def _es_staff(self, member: discord.Member) -> bool:
        return (
            member.guild_permissions.administrator
            or member.guild_permissions.moderate_members
            or member.guild_permissions.manage_messages
        )

    @app_commands.command(name="setup-moderation", description="Crea la categoria y canales de moderacion")
    async def setup_moderation(self, interaction: discord.Interaction):
        if interaction.user.id != 1257780268719411260:
            return await interaction.response.send_message("❌ Solo el creador del bot puede usar este comando.", ephemeral=True)
        if not interaction.guild:
            return await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        existing = discord.utils.get(guild.categories, name=MOD_CATEGORY_NAME)
        category = existing or await guild.create_category(MOD_CATEGORY_NAME, reason="Creacion categoria moderacion")

        everyone_view = discord.PermissionOverwrite(
            view_channel=True, send_messages=False, read_message_history=True
        )
        everyone_full = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, read_message_history=True
        )
        bot_perms = discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_channels=True, read_message_history=True
        )

        sanc_overwrites = {guild.default_role: everyone_view, guild.me: bot_perms}
        for role in guild.roles:
            if role.permissions.moderate_members or role.permissions.administrator:
                sanc_overwrites[role] = discord.PermissionOverwrite(send_messages=True)

        sanc_name = f"🔒┃{SANCTIONS_CHANNEL_NAME}"
        sanc = discord.utils.get(guild.channels, name=sanc_name)
        if not sanc:
            sanc = await guild.create_text_channel(
                sanc_name, category=category,
                overwrites=sanc_overwrites,
                reason="Canal de sanciones"
            )

        apel_name = f"📌┃{APPEALS_CHANNEL_NAME}"
        apel = discord.utils.get(guild.channels, name=apel_name)
        if not apel:
            apel = await guild.create_text_channel(
                apel_name, category=category,
                overwrites={guild.default_role: everyone_full, guild.me: bot_perms},
                reason="Canal de apelaciones"
            )

        global SANCTIONS_CHANNEL_ID, APPEALS_CHANNEL_ID
        SANCTIONS_CHANNEL_ID = sanc.id
        APPEALS_CHANNEL_ID = apel.id
        _save_config()

        appeal_embed = discord.Embed(
            title="📌 Apelaciones",
            description=(
                "Si has recibido una sanción (mute, regaño, etc.) y consideras\n"
                "que fue injusta o deseas explicar tu situación, puedes apelar aquí.\n\n"
                "**¿Cómo apelar?**\n"
                "Escribe tu caso de forma clara y respetuosa. Incluye:\n"
                "• Tu **usuario** exacto\n"
                "• La **sanción** que recibiste\n"
                "• El **motivo** por el que crees que debe revisarse\n\n"
                "Un miembro del staff evaluará tu apelación y te responderá.\n"
                "**No** abuses de este canal ni envíes spam."
            ),
            color=0x8b5cf6,
        )
        appeal_embed.set_footer(text="ZentroxDev · El staff revisará tu caso")
        try:
            await apel.send(embed=appeal_embed)
        except Exception:
            pass

        await interaction.followup.send(
            f"✅ Moderacion configurada:\n"
            f"{category.mention}\n"
            f"{sanc.mention} — visible, solo staff escribe\n"
            f"{apel.mention} — publico para apelar\n\n"
            f"💡 Usa `/setup-ticket-log` en el canal donde quieras los logs de tickets.",
            ephemeral=True
        )

    mod = app_commands.Group(name="mod", description="Comandos de moderacion")

    @mod.command(name="mute", description="Silencia a un usuario por tiempo")
    async def mute(self, interaction: discord.Interaction, usuario: discord.Member, minutos: int, razon: str = None):
        if not interaction.guild or not self._es_staff(interaction.user):
            return await interaction.response.send_message("❌ No tienes permiso.", ephemeral=True)
        if not interaction.guild.me.guild_permissions.moderate_members:
            return await interaction.response.send_message("❌ No tengo permiso para mutear.", ephemeral=True)
        if usuario.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            return await interaction.response.send_message("❌ No puedes mutear a alguien con igual o mayor rol.", ephemeral=True)
        if minutos < 1 or minutos > 40320:
            return await interaction.response.send_message("❌ El tiempo debe estar entre 1 minuto y 28 dias.", ephemeral=True)

        try:
            await usuario.timeout(timedelta(minutes=minutos), reason=razon)
            txt = f"🔇 **{usuario.mention} silenciado por {minutos} minuto(s)**"
            if razon:
                txt += f"\n📝 Razon: {razon}"
            await interaction.response.send_message(txt)
            embed = discord.Embed(
                title="🔇 Mute",
                color=0xef4444,
                timestamp=datetime.utcnow(),
            )
            embed.add_field(name="Usuario", value=usuario.mention, inline=True)
            embed.add_field(name="Moderador", value=interaction.user.mention, inline=True)
            embed.add_field(name="Duracion", value=f"{minutos} minuto(s)", inline=True)
            if razon:
                embed.add_field(name="Razon", value=razon, inline=False)
            await _log_to_sanctions(interaction.guild, embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error al mutear: {e}", ephemeral=True)

    @mod.command(name="unmute", description="Quita el silencio a un usuario")
    async def unmute(self, interaction: discord.Interaction, usuario: discord.Member):
        if not interaction.guild or not self._es_staff(interaction.user):
            return await interaction.response.send_message("❌ No tienes permiso.", ephemeral=True)
        if not interaction.guild.me.guild_permissions.moderate_members:
            return await interaction.response.send_message("❌ No tengo permiso.", ephemeral=True)
        if usuario.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            return await interaction.response.send_message("❌ No puedes quitar mute a alguien con igual o mayor rol.", ephemeral=True)

        try:
            await usuario.timeout(None)
            await interaction.response.send_message(f"🔊 **{usuario.mention} ya no esta silenciado.**")
            embed = discord.Embed(
                title="🔊 Unmute",
                color=0x22c55e,
                timestamp=datetime.utcnow(),
            )
            embed.add_field(name="Usuario", value=usuario.mention, inline=True)
            embed.add_field(name="Moderador", value=interaction.user.mention, inline=True)
            await _log_to_sanctions(interaction.guild, embed)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

    @mod.command(name="warn", description="Anade un regano a un usuario")
    async def warn(self, interaction: discord.Interaction, usuario: discord.Member, razon: str = None):
        if not interaction.guild or not self._es_staff(interaction.user):
            return await interaction.response.send_message("❌ No tienes permiso.", ephemeral=True)
        if usuario.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            return await interaction.response.send_message("❌ No puedes advertir a alguien con igual o mayor rol.", ephemeral=True)

        total = _add_warning(interaction.guild.id, usuario.id, interaction.user.id, razon)
        embed = discord.Embed(
            title="⚠️ Regano",
            description=f"**Usuario:** {usuario.mention}\n**Moderador:** {interaction.user.mention}",
            color=0xf59e0b,
        )
        if razon:
            embed.add_field(name="📝 Razon", value=razon, inline=False)
        embed.add_field(name="📊 Total", value=str(total), inline=False)
        embed.set_footer(text=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))
        await interaction.response.send_message(embed=embed)

        log = discord.Embed(
            title="⚠️ Regano",
            color=0xf59e0b,
            timestamp=datetime.utcnow(),
        )
        log.add_field(name="Usuario", value=usuario.mention, inline=True)
        log.add_field(name="Moderador", value=interaction.user.mention, inline=True)
        log.add_field(name="Total", value=str(total), inline=True)
        if razon:
            log.add_field(name="Razon", value=razon, inline=False)
        await _log_to_sanctions(interaction.guild, log)

        if total == 3:
            try:
                await usuario.timeout(timedelta(hours=1), reason="3 reganos automatico")
                await interaction.channel.send(f"🔇 **{usuario.mention} silenciado 1h por 3 reganos.**")
                auto = discord.Embed(
                    title="🔇 Auto-mute (3 reganos)",
                    color=0xef4444,
                    timestamp=datetime.utcnow(),
                )
                auto.add_field(name="Usuario", value=usuario.mention, inline=True)
                auto.add_field(name="Duracion", value="1 hora", inline=True)
                await _log_to_sanctions(interaction.guild, auto)
            except Exception:
                pass

    @mod.command(name="clear-warnings", description="Elimina los reganos de un usuario")
    async def clear_warnings(self, interaction: discord.Interaction, usuario: discord.Member):
        if not interaction.guild or not self._es_staff(interaction.user):
            return await interaction.response.send_message("❌ No tienes permiso.", ephemeral=True)
        _clear_warnings(interaction.guild.id, usuario.id)
        await interaction.response.send_message(f"✅ Reganos de **{usuario.mention}** eliminados.")

    @mod.command(name="warnings", description="Muestra los reganos de un usuario")
    async def warnings(self, interaction: discord.Interaction, usuario: discord.Member):
        if not interaction.guild:
            return await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)

        warns = _get_warnings(interaction.guild.id, usuario.id)
        if not warns:
            return await interaction.response.send_message(f"✅ **{usuario.display_name}** no tiene reganos.", ephemeral=True)

        embed = discord.Embed(
            title=f"⚠️ Reganos de {usuario.display_name}",
            color=0xf59e0b,
        )
        embed.description = f"**Total: {len(warns)}**"
        for i, w in enumerate(warns, 1):
            mod = interaction.guild.get_member(int(w["mod"]))
            mod_name = mod.mention if mod else f"<@{w['mod']}>"
            fecha = w["fecha"][:19].replace("T", " ")
            embed.add_field(
                name=f"#{i} — {fecha}",
                value=f"**Mod:** {mod_name}\n**Razon:** {w['razon']}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
