import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import string
import re
import io

PEDIDOS_CHANNEL_ID = 1525894272988217536
DEVELOPER_ROLE_ID = 1525894268651176166
TICKETS_ROLE_ID = 1525894268651176160
PANEL_CATEGORY_ID = 1525894274250707057
WEB_CATEGORY_ID = 1525894274837643331
TICKET_PANEL_CHANNEL_ID = 1525894274250707058
WEBHOOK_URL = "https://discord.com/api/webhooks/1525901334099005522/fMEAzTIH8C7cj6slpA3PDajFjkn2x3uOLgoQgHN0E_fwDgNzebJg6VbK5wFCwapzbAFo"
CREATOR_ID = 1522702606437322882
ALLOWED_GUILDS = {1525894268651176159}
MAX_TICKETS_PER_DAY = 3
_user_daily_tickets = {}


def check_daily_limit(user_id: int) -> tuple[bool, int]:
    from datetime import date
    today = date.today()
    entry = _user_daily_tickets.get(user_id)
    if entry and entry[0] == today:
        return entry[1] < MAX_TICKETS_PER_DAY, entry[1]
    return True, 0


def increment_daily_count(user_id: int):
    from datetime import date
    today = date.today()
    entry = _user_daily_tickets.get(user_id)
    if entry and entry[0] == today:
        _user_daily_tickets[user_id] = (today, entry[1] + 1)
    else:
        _user_daily_tickets[user_id] = (today, 1)


async def send_ticket_transcript(channel, creator_id, closer_id, ticket_id):
    try:
        messages = []
        async for msg in channel.history(limit=500, oldest_first=True):
            lines = []
            for m in [msg] if not msg.embeds else [msg] + [None]:
                if m:
                    ts = m.created_at.strftime("%H:%M")
                    name = m.author.display_name if m.author else "Sistema"
                    content = m.content or ""
                    if m.attachments:
                        content += " " + " ".join(a.url for a in m.attachments)
                    lines.append(f"[{ts}] {name}: {content}")
            messages.extend(lines)
            for embed in msg.embeds:
                lines = []
                if embed.title:
                    lines.append(f"[{msg.created_at.strftime('%H:%M')}] — {embed.title}")
                if embed.description:
                    lines.append(f"  {embed.description}")
                if embed.fields:
                    for f in embed.fields:
                        lines.append(f"  {f.name}: {f.value}")
                if embed.footer:
                    lines.append(f"  └ {embed.footer.text}")
                messages.extend(lines)

        header = (
            "══════════════════════════════════\n"
            f"🎫 TRANSCRIPCIÓN DEL TICKET\n"
            f"ID: {ticket_id}\n"
            f"Canal: #{channel.name}\n"
            f"Cerrado por ID: {closer_id}\n"
            "══════════════════════════════════\n\n"
        )
        body = "\n".join(messages) if messages else "(sin mensajes)"
        text = header + body

        def make_file():
            return discord.File(
                fp=io.BytesIO(text.encode("utf-8")),
                filename=f"ticket_{ticket_id}.txt"
            )

        closer = channel.guild.get_member(closer_id)
        if closer:
            try:
                await closer.send(f"📄 **Transcript del ticket {ticket_id}**", file=make_file())
            except Exception:
                pass

        creator = channel.guild.get_member(creator_id)
        if creator:
            try:
                await creator.send(f"📄 **Transcript de tu ticket {ticket_id}**", file=make_file())
            except Exception:
                pass
    except Exception:
        pass


class TicketView(discord.ui.View):
    def __init__(self, creator_id: int):
        super().__init__(timeout=None)
        self.creator_id = creator_id
        self._claimed_id = 0

    def _is_staff(self, member: discord.Member) -> bool:
        return any(role.id in (DEVELOPER_ROLE_ID, TICKETS_ROLE_ID) for role in member.roles)

    def _get_creator_from_topic(self, channel) -> int:
        if channel.topic:
            for part in channel.topic.split("|"):
                if part.startswith("creator:"):
                    try:
                        return int(part.split(":", 1)[1])
                    except ValueError:
                        pass
        return 0

    def _get_claimed_from_topic(self, channel) -> int:
        if channel.topic:
            for part in channel.topic.split("|"):
                if part.startswith("claimed:"):
                    try:
                        val = part.split(":", 1)[1]
                        return int(val) if val else 0
                    except ValueError:
                        pass
        return 0

    @discord.ui.button(label="📋 Reclamar ticket", style=discord.ButtonStyle.primary, custom_id="claim_ticket")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not self._is_staff(interaction.user):
                await interaction.response.send_message("❌ Solo el staff puede reclamar tickets.", ephemeral=True)
                return
            claimed_id = self._get_claimed_from_topic(interaction.channel)
            if claimed_id:
                claimer = interaction.guild.get_member(claimed_id)
                name = claimer.display_name if claimer else str(claimed_id)
                await interaction.response.send_message(f"⚠️ Este ticket ya fue reclamado por **{name}**.", ephemeral=True)
                return
            dev_role = interaction.guild.get_role(DEVELOPER_ROLE_ID)
            tickets_role = interaction.guild.get_role(TICKETS_ROLE_ID)
            creator_id = self._get_creator_from_topic(interaction.channel)
            creator = interaction.guild.get_member(creator_id)
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, manage_messages=True),
            }
            if dev_role:
                overwrites[dev_role] = discord.PermissionOverwrite(view_channel=True, send_messages=False)
            if tickets_role:
                overwrites[tickets_role] = discord.PermissionOverwrite(view_channel=True, send_messages=False)
            if interaction.user != creator:
                overwrites[interaction.user] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            if creator:
                overwrites[creator] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            await interaction.channel.edit(topic=f"creator:{creator_id}|claimed:{interaction.user.id}", overwrites=overwrites)
            await interaction.channel.send(f"📋 **Ticket reclamado por {interaction.user.mention}**\n> Ahora solo {interaction.user.mention} y el creador pueden escribir.")
            await interaction.response.send_message("✅ Ticket reclamado con éxito.", ephemeral=True)
        except Exception:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Error al reclamar el ticket.", ephemeral=True)
            except Exception:
                pass

    @discord.ui.button(label="🔒 Cerrar ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            member = interaction.user
            creator_id = self._get_creator_from_topic(interaction.channel)
            if not creator_id:
                creator_id = self.creator_id
            claimed_id = self._get_claimed_from_topic(interaction.channel)
            is_creator = member.id == creator_id
            if claimed_id:
                is_claimer = member.id == claimed_id
                if not is_claimer and not is_creator:
                    claimer = interaction.guild.get_member(claimed_id)
                    name = claimer.display_name if claimer else str(claimed_id)
                    await interaction.response.send_message(
                        f"❌ Este ticket está reclamado por **{name}**. Solo {name} o el creador pueden cerrarlo.", ephemeral=True
                    )
                    return
            else:
                is_staff = self._is_staff(member)
                if not is_staff and not is_creator:
                    await interaction.response.send_message(
                        "❌ Solo el creador del ticket o el staff puede cerrarlo.", ephemeral=True
                    )
                    return
            await interaction.response.defer()
            try:
                await interaction.edit_original_response(view=None)
            except Exception:
                pass
            ticket_id = interaction.channel.name.upper()
            await send_ticket_transcript(interaction.channel, creator_id, member.id, ticket_id)
            await interaction.channel.send(f"🔒 Cerrando ticket... Solicitado por {member.mention}")
            await asyncio.sleep(5)
            await interaction.channel.delete(reason=f"Ticket cerrado por {member.name} ({member.id})")
        except Exception:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Error al cerrar el ticket.", ephemeral=True)
            except Exception:
                pass


async def find_member_in_guild(guild, discord_username):
    if not discord_username:
        return None
    member = None
    if discord_username.isdigit() and len(discord_username) == 18:
        member = guild.get_member(int(discord_username))
    if not member:
        member = guild.get_member_named(discord_username)
    if not member:
        lower = discord_username.lower().lstrip('@')
        for m in guild.members:
            if m.display_name.lower() == lower or m.name.lower() == lower:
                member = m
                break
    if not member:
        for m in guild.members:
            if lower in m.name.lower() or lower in m.display_name.lower():
                member = m
                break
    return member


async def create_ticket_channel(guild, ticket_id, embed, username, category_id=None):
    member = await find_member_in_guild(guild, username)
    category = guild.get_channel(category_id) if category_id else discord.utils.get(guild.categories, name="TICKETS")
    if not category:
        category = await guild.create_category(
            TICKETS_CATEGORY_NAME,
            reason="Categoria para tickets de pedidos"
        )
    channel_name = ticket_id.lower().replace('#', '')
    existing = discord.utils.get(guild.channels, name=channel_name)
    if existing:
        return existing, False

    developer_role = guild.get_role(DEVELOPER_ROLE_ID)
    tickets_role = guild.get_role(TICKETS_ROLE_ID)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, manage_messages=True),
    }
    if developer_role:
        overwrites[developer_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
    if tickets_role:
        overwrites[tickets_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
    if member:
        overwrites[member] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    ticket_channel = await guild.create_text_channel(
        channel_name,
        category=category,
        overwrites=overwrites,
        topic=f"creator:{member.id}" if member else "creator:0",
        reason=f"Ticket {ticket_id} creado automaticamente"
    )

    welcome_embed = discord.Embed(
        title=f"🎫 Ticket {ticket_id}",
        description=(
            f"📦 **{embed.title if embed.title else 'Pedido'}**\n\n"
            f"🎯 ¡Bienvenido! Gracias por confiar en **ZentroxDev**.\n\n"
            f"Tu solicitud ha sido recibida correctamente. Un administrador "
            f"revisará los detalles y te atenderá a la brevedad.\n\n"
            f"📌 **Mientras tanto:**\n"
            f"▸ Puedes ir explicando tu pedido con más detalle aquí.\n"
            f"▸ Si tienes archivos de referencia, adjúntalos en este canal.\n"
            f"▸ Un miembro del equipo te responderá pronto."
        ),
        color=0x3b82f6,
        timestamp=discord.utils.utcnow()
    )
    welcome_embed.set_footer(text="ZentroxDev · Ticket automático")

    member_mention = member.mention if member else "*(usuario no encontrado)*"
    welcome_text = f"{member_mention}\n━━━━━━━━━━━━━━━━━━━━━━━━\n**🎟️ Bienvenido a tu ticket — ZentroxDev**"
    view = TicketView(creator_id=member.id if member else 0)
    await ticket_channel.send(content=welcome_text, embed=welcome_embed, view=view)
    return ticket_channel, True


async def send_embed_to_pedidos(guild, bot_user, ticket_id, service_name, detalle, metodo, usuario, ticket_channel):
    pedidos_channel = guild.get_channel(PEDIDOS_CHANNEL_ID)
    if not pedidos_channel:
        print("Canal de pedidos no encontrado")
        return

    embed = discord.Embed(
        title="✨ Nuevo pedido recibido",
        description=(
            f"📦 **{service_name}**\n\n"
            f"🎯 Bienvenido y gracias por confiar en **ZentroxDev**.\n"
            f"Hemos recibido tu solicitud y uno de nuestros administradores "
            f"la revisará en breve."
        ),
        color=0x3b82f6,
        timestamp=discord.utils.utcnow()
    )

    info = (
        f"**Ticket:** {ticket_id}\n"
        f"**Servicio:** {service_name}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Detalle:**\n{detalle}\n\n"
        f"**Pago:** {metodo}\n"
        f"**Discord:** {usuario}"
    )
    embed.add_field(name="📋 Información del pedido", value=info, inline=False)

    pasos = (
        "▸ Un miembro del equipo revisará tu solicitud.\n"
        "▸ Recibirás una respuesta por Discord en máximo 24 horas hábiles.\n"
        "▸ Es posible que te solicitemos información adicional.\n"
        "▸ No cierres este ticket hasta que tu pedido esté finalizado."
    )
    embed.add_field(name="📌 Próximos pasos", value=pasos, inline=False)

    gracias = (
        "💙 **Gracias por tu preferencia**\n"
        "*\"Ideas que construyen soluciones\"*\n\n"
        "El equipo de ZentroxDev se pondrá en contacto contigo pronto. "
        "Si tienes alguna urgencia, responde a este mensaje."
    )
    embed.add_field(name="\u200b", value=gracias, inline=False)

    embed.set_footer(
        text="ZentroxDev © 2026 · Los administradores te contactarán pronto",
        icon_url=bot_user.display_avatar.url if bot_user else None
    )

    await pedidos_channel.send(embed=embed)
    await pedidos_channel.send(f"📌 **Canal del ticket:** {ticket_channel.mention}")


PANEL_EMBED = discord.Embed(
    title="╔═══════ 𝐓𝐢𝐜𝐤𝐞𝐭𝐬 ═══════╗",
    description=(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**✨ ¡Bienvenido a ZentroxDev!**\n\n"
        "Selecciona el servicio que deseas contratar y crearemos un "
        "canal privado para ti.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    ),
    color=0x5865F2
)
PANEL_EMBED.add_field(
    name="🤖 **Desarrollo**",
    value=(
        "`▸` Bots personalizados para Discord, Minecraft y más\n"
        "`▸` Páginas web y sistemas a medida\n"
        "`▸` Integraciones y automatizaciones"
    ),
    inline=False
)
PANEL_EMBED.add_field(
    name="🎮 **ER:LC**",
    value=(
        "`▸` Texturas y diseños exclusivos\n"
        "`▸` Mapas personalizados\n"
        "`▸` Redacción de documentos y normativas"
    ),
    inline=False
)
PANEL_EMBED.add_field(
    name="🛡️ **Comunidad**",
    value=(
        "`▸` Configuración y moderación de servidores Discord\n"
        "`▸` Diseño gráfico (logos, banners, thumbnails)\n"
        "`▸` Alianzas y servidores educados"
    ),
    inline=False
)
PANEL_EMBED.add_field(
    name="\u200b",
    value=(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 **Al hacer clic en un botón** se creará un canal privado\n"
        "donde solo tú y nuestro equipo podrán ver y responder.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚡ **Límite:** 3 tickets por usuario al día\n"
        "📄 Recibirás una copia del ticket al cerrarse"
    ),
    inline=False
)
PANEL_EMBED.set_footer(text="ZentroxDev © 2026 · Calidad y compromiso")


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🤖 Bots Personalizados", style=discord.ButtonStyle.primary, custom_id="panel_bots", row=0)
    async def btn_bots(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self._create_ticket(interaction, "Bots Personalizados")
        except Exception as e:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
            except Exception:
                pass

    @discord.ui.button(label="🌐 Páginas Web", style=discord.ButtonStyle.primary, custom_id="panel_web", row=0)
    async def btn_web(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self._create_ticket(interaction, "Páginas Web")
        except Exception as e:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
            except Exception:
                pass

    @discord.ui.button(label="🪄 Texturas ER:LC", style=discord.ButtonStyle.success, custom_id="panel_texturas", row=1)
    async def btn_texturas(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self._create_ticket(interaction, "Texturas de ER:LC")
        except Exception as e:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
            except Exception:
                pass

    @discord.ui.button(label="🗺️ Mapas ER:LC", style=discord.ButtonStyle.success, custom_id="panel_mapas", row=1)
    async def btn_mapas(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self._create_ticket(interaction, "Mapas personalizados ER:LC")
        except Exception as e:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
            except Exception:
                pass

    @discord.ui.button(label="🛠️ Servicios Discord", style=discord.ButtonStyle.secondary, custom_id="panel_discord", row=2)
    async def btn_discord(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self._create_ticket(interaction, "Servicios de Discord")
        except Exception as e:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
            except Exception:
                pass

    @discord.ui.button(label="🤝 Alianza", style=discord.ButtonStyle.secondary, custom_id="panel_alianza", row=2)
    async def btn_alianza(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self._create_ticket(interaction, "Alianza")
        except Exception as e:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
            except Exception:
                pass

    @discord.ui.button(label="📝 Documentos ER:LC", style=discord.ButtonStyle.secondary, custom_id="panel_documentos", row=3)
    async def btn_documentos(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self._create_ticket(interaction, "Redacción de documentos ER:LC")
        except Exception as e:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
            except Exception:
                pass

    @discord.ui.button(label="🎨 Diseño Gráfico", style=discord.ButtonStyle.danger, custom_id="panel_diseno", row=3)
    async def btn_diseno(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await self._create_ticket(interaction, "Diseño gráfico")
        except Exception as e:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
            except Exception:
                pass

    async def _create_ticket(self, interaction: discord.Interaction, service_name: str):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("❌ Esto solo funciona en un servidor.", ephemeral=True)
            return
        allowed, used = check_daily_limit(interaction.user.id)
        if not allowed:
            await interaction.response.send_message(
                f"❌ Ya has usado tus **{MAX_TICKETS_PER_DAY} tickets** hoy. Vuelve mañana.", ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        ticket_id = f"ZTX-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
        dummy_embed = discord.Embed(title=f"📦 {service_name}")
        ticket_channel, created = await create_ticket_channel(guild, ticket_id, dummy_embed, interaction.user.name, category_id=PANEL_CATEGORY_ID)
        if not created:
            await interaction.followup.send(f"⚠️ Ya existe un ticket: {ticket_channel.mention}", ephemeral=True)
            return
        questions = SERVICE_QUESTIONS.get(service_name, [
            "📌 **Cuéntanos los detalles de tu solicitud**",
            "⏰ **¿Tienes algún plazo límite?**",
            "💳 **¿Cuál es tu método de pago preferido?**",
        ])
        msg = f"📝 **Cuéntanos más sobre tu solicitud de {service_name}**\n\n" + \
              "\n".join(f"{q}" for q in questions) + \
              "\n\nUn miembro del equipo te atenderá en breve. 💙"
        await ticket_channel.send(msg)
        increment_daily_count(interaction.user.id)
        await interaction.followup.send(
            f"✅ **Ticket {ticket_id}** creado → {ticket_channel.mention}",
            ephemeral=True
        )

SERVICE_QUESTIONS = {
    "Bots Personalizados": [
        "🤖 **¿Qué tipo de bot necesitas?** (Moderación, Música, Tickets, Juegos, Multipropósito...)",
        "⚙️ **¿Qué funcionalidades específicas debe tener?**",
        "💻 **¿Para qué plataforma?** (Discord, Telegram, Minecraft...)",
        "📁 **¿Tienes algún ejemplo o referencia?**",
        "⏰ **¿Cuál es tu plazo límite?**",
        "💳 **¿Cuál es tu método de pago preferido?**",
    ],
    "Páginas Web": [
        "🌐 **¿Qué tipo de página web?** (Landing page, Tienda, Blog, Portafolio, Sistema...)",
        "🎨 **¿Tienes diseño o referencia visual?** (Figma, PDF, ejemplo de otra web...)",
        "📱 **¿Necesitas que sea responsive?**",
        "🛠️ **¿Qué funcionalidades debe tener?** (Formularios, login, pasarela de pago...)",
        "⏰ **¿Cuál es tu plazo límite?**",
        "💳 **¿Cuál es tu método de pago preferido?**",
    ],
    "Texturas de ER:LC": [
        "🎨 **¿Qué tipo de textura buscas?** (Vehículos, uniformes, edificios, armas...)",
        "🖌️ **Describe el diseño o temática deseada**",
        "📸 **¿Tienes imágenes de referencia?**",
        "🎯 **¿Cantidad de texturas que necesitas?**",
        "⏰ **¿Cuál es tu plazo límite?**",
        "💳 **¿Cuál es tu método de pago preferido?**",
    ],
    "Mapas personalizados ER:LC": [
        "🗺️ **¿Qué tipo de mapa?** (Roleplay, carrera, drifting, persecución...)",
        "📐 **¿Tamaño aproximado del mapa?**",
        "🏗️ **¿Edificios o estructuras específicas?**",
        "🌆 **¿Temática o ambientación deseada?**",
        "⏰ **¿Cuál es tu plazo límite?**",
        "💳 **¿Cuál es tu método de pago preferido?**",
    ],
    "Servicios de Discord": [
        "🛡️ **¿Qué servicio necesitas?** (Configuración del servidor, moderación, roles, bots...)",
        "📋 **Describe lo que quieres implementar**",
        "👥 **¿Cuántos miembros tiene el servidor?**",
        "🔧 **¿Tienes algún bot o herramienta ya instalada?**",
        "⏰ **¿Cuál es tu plazo límite?**",
        "💳 **¿Cuál es tu método de pago preferido?**",
    ],
    "Redacción de documentos ER:LC": [
        "📝 **¿Qué tipo de documento necesitas?** (Reglas, lore, sanciones, rangos...)",
        "📄 **¿Tienes algún borrador o base?**",
        "🎯 **¿Extensión aproximada?** (Páginas o palabras)",
        "🏷️ **¿Temática o estilo del documento?**",
        "⏰ **¿Cuál es tu plazo límite?**",
        "💳 **¿Cuál es tu método de pago preferido?**",
    ],
    "Diseño gráfico": [
        "🎨 **¿Qué tipo de diseño?** (Logo, banner, portada, thumbnail, empaque...)",
        "🖼️ **¿Tienes referencias visuales?**",
        "🌈 **¿Colores o paleta deseada?**",
        "📐 **¿Tamaño o formato específico?**",
        "⏰ **¿Cuál es tu plazo límite?**",
        "💳 **¿Cuál es tu método de pago preferido?**",
    ],
    "Alianza": [
        "🤝 **¿De qué trata tu servidor o comunidad?**",
        "📋 **¿Qué tipo de alianza buscas?** (Publicidad mutua, eventos conjuntos, colaboración...)",
        "👥 **¿Cuántos miembros tiene tu comunidad?**",
        "🌐 **¿Tienes servidor de Discord o redes sociales?**",
        "📢 **¿Cómo podemos promocionar tu comunidad?**",
        "🔄 **¿Qué beneficios ofreces a cambio?**",
    ],
}


class PedidoModal(discord.ui.Modal, title="📦 Nuevo Pedido — ZentroxDev"):
    servicio = discord.ui.TextInput(
        label="¿Qué servicio necesitas?",
        placeholder="Bot de Discord, Pagina Web, Diseño Gráfico, Bot de Minecraft...",
        max_length=50
    )
    detalle = discord.ui.TextInput(
        label="Cuéntanos sobre tu proyecto",
        style=discord.TextStyle.paragraph,
        placeholder="Describe tu idea, funcionalidades, lo que necesitas...",
        max_length=1000
    )
    plazo = discord.ui.TextInput(
        label="¿Tienes algún plazo límite?",
        placeholder="Ej: 1 semana, no hay prisa, lo antes posible...",
        max_length=200,
        required=False
    )
    pago = discord.ui.TextInput(
        label="¿Cuál es tu método de pago?",
        placeholder="PayPal, Crypto, Transferencia, etc.",
        max_length=200
    )

    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        try:
            ticket_id = f"ZTX-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
            username = interaction.user.name
            guild = interaction.guild
            if not guild:
                await interaction.response.send_message("❌ Este comando solo funciona en un servidor.", ephemeral=True)
                return
            allowed, used = check_daily_limit(interaction.user.id)
            if not allowed:
                await interaction.response.send_message(
                    f"❌ Ya has usado tus **{MAX_TICKETS_PER_DAY} tickets** hoy. Vuelve mañana.", ephemeral=True
                )
                return
            await interaction.response.defer(ephemeral=True)
            detalle_completo = self.detalle.value
            if self.plazo.value:
                detalle_completo += f"\n\n**Plazo:** {self.plazo.value}"
            dummy_embed = discord.Embed(title=f"📦 {self.servicio.value}")
            ticket_channel, created = await create_ticket_channel(guild, ticket_id, dummy_embed, username, category_id=WEB_CATEGORY_ID)
            if created:
                increment_daily_count(interaction.user.id)
                await send_embed_to_pedidos(guild, self.bot.user, ticket_id, self.servicio.value, detalle_completo, self.pago.value, username, ticket_channel)
            await interaction.followup.send(
                f"✅ **Ticket {ticket_id} creado** → {ticket_channel.mention}",
                ephemeral=True
            )
        except Exception as e:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
            except Exception:
                pass


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="panel", description="Envía el panel de tickets al canal configurado")
    @app_commands.default_permissions(administrator=True)
    async def panel(self, interaction: discord.Interaction):
        try:
            channel = interaction.guild.get_channel(TICKET_PANEL_CHANNEL_ID) if interaction.guild else None
            if not channel:
                await interaction.response.send_message("❌ Canal de panel no encontrado.", ephemeral=True)
                return
            await channel.send(embed=PANEL_EMBED, view=TicketPanelView())
            await interaction.response.send_message(f"✅ Panel enviado a {channel.mention}", ephemeral=True)
        except Exception as e:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
            except Exception:
                pass

    @app_commands.command(name="pedido", description="Solicita un servicio y crea un ticket")
    async def pedido(self, interaction: discord.Interaction):
        try:
            await interaction.response.send_modal(PedidoModal(self.bot))
        except Exception as e:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
                else:
                    await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
            except Exception:
                pass

    @app_commands.command(name="close", description="Cierra el ticket actual (solo staff o creador)")
    async def close(self, interaction: discord.Interaction):
        try:
            creator_id = 0
            claimed_id = 0
            if interaction.channel.topic:
                for part in interaction.channel.topic.split("|"):
                    if part.startswith("creator:"):
                        try:
                            creator_id = int(part.split(":", 1)[1])
                        except ValueError:
                            pass
                    elif part.startswith("claimed:"):
                        try:
                            val = part.split(":", 1)[1]
                            claimed_id = int(val) if val else 0
                        except ValueError:
                            pass
            is_creator = interaction.user.id == creator_id
            if claimed_id:
                is_claimer = interaction.user.id == claimed_id
                if not is_claimer and not is_creator:
                    claimer = interaction.guild.get_member(claimed_id)
                    name = claimer.display_name if claimer else str(claimed_id)
                    await interaction.response.send_message(
                        f"❌ Este ticket está reclamado por **{name}**. Solo {name} o el creador pueden cerrarlo.", ephemeral=True
                    )
                    return
            else:
                has_role = any(role.id in (DEVELOPER_ROLE_ID, TICKETS_ROLE_ID) for role in interaction.user.roles)
                if not has_role and not is_creator:
                    await interaction.response.send_message("❌ No tienes permiso para cerrar este ticket.", ephemeral=True)
                    return
            await interaction.response.defer(ephemeral=True)
            ticket_id = interaction.channel.name.upper()
            await send_ticket_transcript(interaction.channel, creator_id, interaction.user.id, ticket_id)
            await interaction.followup.send(f"🔒 Cerrando ticket... Solicitado por {interaction.user.mention}", ephemeral=True)
            await asyncio.sleep(5)
            await interaction.channel.delete(reason=f"Ticket cerrado por {interaction.user.name} ({interaction.user.id})")
        except Exception:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("❌ Error al cerrar el ticket.", ephemeral=True)
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.channel.id != PEDIDOS_CHANNEL_ID:
            return
        if not message.webhook_id:
            return
        if not message.embeds:
            return

        embed = message.embeds[0]
        if not embed.fields:
            return

        ticket_id = None
        discord_username = None
        service_name = None

        for field in embed.fields:
            if "Información del pedido" in field.name or "Informacion del pedido" in field.name:
                value = field.value
                ticket_match = re.search(r'Ticket:\s*(\S+)', value)
                if ticket_match:
                    ticket_id = ticket_match.group(1)
                service_match = re.search(r'Servicio:\s*(.+)', value)
                if service_match:
                    service_name = service_match.group(1).strip()
                user_match = re.search(r'Discord:\s*(.+)', value)
                if user_match:
                    raw = user_match.group(1).strip().rstrip('`')
                    if raw.startswith('<@'):
                        uid = re.search(r'(\d{17,20})', raw)
                        if uid:
                            discord_username = uid.group(1)
                    else:
                        discord_username = raw
                break

        if not ticket_id:
            return

        guild = message.guild
        if not guild:
            return

        member = await find_member_in_guild(guild, discord_username)

        if not member:
            await message.delete()
            await message.channel.send(
                f"**Pedido {ticket_id} rechazado** — El usuario **{discord_username or 'desconocido'}** "
                f"no esta en el servidor de Discord. Debe unirse primero a {discord.utils.format_discord_link(guild.id)}"
            )
            return

        ticket_channel, created = await create_ticket_channel(guild, ticket_id, embed, discord_username, category_id=WEB_CATEGORY_ID)

        if not created:
            new_embed = embed.copy()
            new_embed.url = ticket_channel.jump_url
            try:
                webhook = discord.Webhook.from_url(WEBHOOK_URL, client=self.bot)
                await webhook.edit_message(message.id, embed=new_embed)
            except Exception as e:
                print(f"No se pudo editar el mensaje del webhook: {e}")
            await message.channel.send(f"El canal {ticket_channel.mention} ya existe para el ticket {ticket_id}.")
            return

        new_embed = embed.copy()
        new_embed.url = ticket_channel.jump_url
        try:
            webhook = discord.Webhook.from_url(WEBHOOK_URL, client=self.bot)
            await webhook.edit_message(message.id, embed=new_embed)
        except Exception as e:
            print(f"No se pudo editar el mensaje del webhook: {e}")

        member_mention = member.mention if member else "*(usuario no encontrado)*"
        await message.channel.send(
            f"**Ticket {ticket_id}** creado -> {ticket_channel.mention}  |  {member_mention}"
        )

    @app_commands.command(name="leave", description="[Creator only] Hace salir al bot del servidor")
    async def leave(self, interaction: discord.Interaction):
        if interaction.user.id != CREATOR_ID:
            await interaction.response.send_message("❌ Solo el creador del bot puede usar este comando.", ephemeral=True)
            return
        await interaction.response.send_message("👋 Saliendo del servidor...")
        await interaction.guild.leave()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        owner = self.bot.get_user(CREATOR_ID)
        if owner:
            try:
                await owner.send(f"📤 El bot fue removido del servidor **{guild.name}** ({guild.id})")
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        if guild.id not in ALLOWED_GUILDS:
            owner = self.bot.get_user(CREATOR_ID)
            if owner:
                try:
                    await owner.send(
                        f"🚫 Alguien intentó añadir el bot a **{guild.name}** ({guild.id}). "
                        "Saliendo automáticamente."
                    )
                except Exception:
                    pass
            await guild.leave()


async def setup(bot):
    await bot.add_cog(Tickets(bot))
    bot.add_view(TicketPanelView())
    bot.add_view(TicketView(0))
