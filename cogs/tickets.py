import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import string
import re
import io
from datetime import date

PEDIDOS_CHANNEL_ID = 1525894272988217536
DEVELOPER_ROLE_ID = 1525894268651176166
TICKETS_ROLE_ID = 1525894268651176160
PANEL_CATEGORY_ID = 1525894274250707057
WEB_CATEGORY_ID = 1525894274837643331
TICKET_PANEL_CHANNEL_ID = 1525894274250707058
WEBHOOK_URL = "https://discord.com/api/webhooks/1525901334099005522/fMEAzTIH8C7cj6slpA3PDajFjkn2x3uOLgoQgHN0E_fwDgNzebJg6VbK5wFCwapzbAFo"
CREATOR_ID = 1257780268719411260
ALLOWED_GUILDS = {1525894268651176159}
MAX_TICKETS_PER_DAY = 3
_user_daily_tickets = {}

SERVICE_PRICES = {
    "Bots Personalizados": {
        "paquetes": [
            "**Básico** `$10` — Bot con hasta 5 comandos personalizados",
            "**Estándar** `$20` — Bot con 10+ comandos, economía o moderación",
            "**Profesional** `$35` — Bot completo con BD, logs, niveles, temporizadores",
            "**Premium** `$60+` — Bot con panel web, dashboard, APIs externas",
        ],
        "monthy": "Estándar `$10/mes` · Profesional `$15/mes` · Premium `$25/mes`"
    },
    "Páginas Web": {
        "paquetes": [
            "**Landing Page** `$15` — 1 página, diseño moderno responsive",
            "**Institucional** `$25` — 3-5 páginas, formulario, SEO",
            "**Profesional** `$45` — Panel admin, base de datos, auth",
            "**Tienda / App** `$80+` — E-commerce, pasarela de pago, APIs",
        ],
        "monthy": "Desde `$10/mes` (hosting + dominio + mantenimiento)"
    },
    "Texturas de ER:LC": {
        "paquetes": [
            "**Pack básico** `$10` — 2 texturas personalizadas (32×32)",
            "**Pack estándar** `$15` — 5 texturas (64×64)",
            "**Pack premium** `$25` — 10 texturas (64×64) + variantes",
            "**Pack completo** `$40` — Texturas para todo tu servidor ER:LC",
        ],
        "monthy": None
    },
    "Mapas personalizados ER:LC": {
        "paquetes": [
            "**Mapa pequeño** `$20` — Estación, comisaría o base pequeña",
            "**Mapa mediano** `$40` — Mapa con interiores detallados",
            "**Mapa grande** `$70` — Mapa extenso + edificios + paisaje",
            "**Mapa personalizado** `$100+` — Diseño 100% desde 0 a tu medida",
        ],
        "monthy": None
    },
    "Servicios de Discord": {
        "paquetes": [
            "**Configuración** `$10` — Roles, canales, bots, bienvenidas",
            "**Moderación** `$20` — Sistema de warns, logs, tickets, anti-raid",
            "**Comunidad** `$30` — Todo + economía, niveles, sorteos",
            "**Servidor completo** `$50+` — Servidor optimizado con bots a medida",
        ],
        "monthy": "`$10/mes` — Actualizaciones + soporte + nuevas features"
    },
    "Redacción de documentos ER:LC": {
        "paquetes": [
            "**Documento simple** `$10` — Plantilla de reglas o rangos",
            "**Documento completo** `$15` — Reglamento + sanciones + rangos + lore",
            "**Pack de documentos** `$25` — Sistema legal completo del servidor",
            "**Personalizado** `$35+` — Redacción profesional con glosario y guías",
        ],
        "monthy": None
    },
    "Diseño gráfico": {
        "paquetes": [
            "**Logo / Icono** `$10` — Diseño simple con tu idea",
            "**Banner / Portada** `$15` — Banner para servidor o redes",
            "**Pack gráfico** `$25` — Logo + banner + emojis + fondos",
            "**Branding completo** `$40+` — Identidad visual completa, mockups",
        ],
        "monthy": None
    },
    "Alianza": {"paquetes": None, "monthy": None},
}

MAINTENANCE_PLANS = {
    "Básico ($5/mes)": "Hosting + monitoreo + backups semanales",
    "Estándar ($15/mes)": "Todo lo anterior + bugs + cambios menores + soporte prioritario",
    "Premium ($30/mes)": "Todo + hosting dedicado + cambios ilimitados + 1 feature/mes + backups diarios",
}


def check_daily_limit(user_id: int) -> tuple[bool, int]:
    if user_id == CREATOR_ID:
        return True, 0
    today = date.today()
    entry = _user_daily_tickets.get(user_id)
    if entry and entry[0] == today:
        return entry[1] < MAX_TICKETS_PER_DAY, entry[1]
    return True, 0


def increment_daily_count(user_id: int):
    if user_id == CREATOR_ID:
        return
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

    async def _run_questionnaire(self, channel, member, service_name):
        questions = SERVICE_QUESTIONS.get(service_name, [])
        if not questions:
            return

        answers = []
        intro = (
            f"📋 **Cuestionario interactivo — {service_name}**\n\n"
            f"Te haré **{len(questions)} preguntas** para entender mejor tu proyecto. "
            f"Responde una por una en este canal.\n"
            f"⏰ Tienes **10 minutos** por respuesta.\n\n"
            f"*Comenzamos en unos segundos...*"
        )
        await channel.send(intro)
        await asyncio.sleep(2)

        for i, question in enumerate(questions):
            await channel.send(f"**❓ Pregunta {i+1}/{len(questions)}**\n{question}")

            def check(m):
                return m.channel == channel and m.author == member and not m.author.bot

            try:
                msg = await self.bot.wait_for('message', timeout=600.0, check=check)
                answers.append(msg.content)
                try:
                    await msg.add_reaction('✅')
                except Exception:
                    pass
            except asyncio.TimeoutError:
                await channel.send(
                    "⏰ **Tiempo agotado.** No te preocupes, puedes seguir escribiendo "
                    "tus respuestas en el canal y un miembro del equipo las revisará."
                )
                return

        summary_lines = []
        for i, (q, a) in enumerate(zip(questions, answers)):
            clean_q = q.replace('**', '')
            if ' ' in clean_q:
                clean_q = clean_q.split(' ', 1)[1] if len(clean_q.split(' ', 1)) > 1 else clean_q
            summary_lines.append(f"**{i+1}.** {clean_q}\n➡ {a}")

        summary = (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 **Resumen de tu pedido — {service_name}**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            + "\n\n".join(summary_lines) +
            "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✅ **¡Cuestionario completado!**\n"
            "Un miembro del equipo revisará tus respuestas y te atenderá pronto.\n"
            "Si necesitas agregar algo más, puedes escribir libremente en este canal."
        )
        await channel.send(summary)

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
        await send_pricing_info(ticket_channel, service_name)
        increment_daily_count(interaction.user.id)
        await interaction.followup.send(
            f"✅ **Ticket {ticket_id}** creado → {ticket_channel.mention}",
            ephemeral=True
        )
        await self._run_questionnaire(ticket_channel, interaction.user, service_name)

SERVICE_QUESTIONS = {
    "Bots Personalizados": [
        "🤖 **¿Qué tipo de bot necesitas?** (Moderación, economía, tickets, música, juegos, IA, multipropósito...)",
        "⚙️ **Describe en detalle TODAS las funcionalidades y comandos que debe tener**",
        "💻 **¿Para qué plataforma es?** (Discord, Telegram, Minecraft, WhatsApp...)",
        "📊 **¿Necesitas panel web o dashboard para administrar el bot?**",
        "🐍 **¿Qué lenguaje prefieres?** (Python, JavaScript, o lo dejamos a nuestra elección)",
        "👥 **¿Cuántos usuarios estimas que usarán el bot aproximadamente?**",
        "🗄️ **¿Necesitas integración con base de datos?** (MySQL, MongoDB, PostgreSQL...)",
        "📁 **¿Tienes ejemplos de bots similares o ideas de referencia?**",
        "⏰ **¿Cuentas con algún plazo límite o fecha de entrega deseada?**",
        "💳 **¿Cuál es tu método de pago preferido?** (PayPal, Crypto, Transferencia...)",
    ],
    "Páginas Web": [
        "🌐 **¿Qué tipo de página web necesitas?** (Landing page, tienda online, blog, portafolio, panel...)",
        "📐 **Describe las secciones que debe incluir** (Inicio, servicios, contacto, login, dashboard...)",
        "🎨 **¿Tienes diseño o referencia visual?** (Figma, PDF, URL de ejemplo...)",
        "📱 **¿Necesitas que sea responsive y adaptada a móviles?**",
        "🛠️ **¿Qué funcionalidades debe tener?** (Formularios, login, pasarela de pago, panel admin...)",
        "🗄️ **¿Necesitas base de datos y backend para gestionar contenido?**",
        "🔗 **¿Tienes dominio propio o necesitas ayuda para conseguirlo?**",
        "📝 **¿Tienes los textos e imágenes listos o prefieres que los creemos?**",
        "⏰ **¿Cuentas con algún plazo límite o fecha de entrega deseada?**",
        "💳 **¿Cuál es tu método de pago preferido?** (PayPal, Crypto, Transferencia...)",
    ],
    "Texturas de ER:LC": [
        "🎨 **¿Qué tipo de textura necesitas?** (Vehículos, uniformes, edificios, armas, accesorios...)",
        "🖌️ **Describe el diseño, colores y temática deseada con el mayor detalle posible**",
        "📸 **¿Tienes imágenes de referencia, concept art o ejemplos visuales?**",
        "🔢 **¿Cuántas texturas necesitas en total y para qué modelos?**",
        "📐 **¿Qué resolución prefieres?** (16×16, 32×32, 64×64 — o déjalo a nuestra recomendación)",
        "🎨 **¿Necesitas variantes de color o diseño?** (Ej: varias unidades con distintos colores)",
        "🏷️ **¿Para qué servidor, facción o comunidad de ER:LC es?**",
        "📁 **¿Tienes referencias de texturas que te gusten para inspirarnos?**",
        "⏰ **¿Cuentas con algún plazo límite o fecha de entrega deseada?**",
        "💳 **¿Cuál es tu método de pago preferido?** (PayPal, Crypto, Transferencia...)",
    ],
    "Mapas personalizados ER:LC": [
        "🗺️ **¿Qué tipo de mapa deseas?** (Base, ciudad, comisaría, hospital, estación, aeropuerto...)",
        "📐 **Describe el tamaño y dimensiones aproximadas que imaginas**",
        "🏗️ **¿Qué edificios, estructuras o zonas específicas debe incluir?**",
        "🌆 **¿Cuál es la temática o ambientación?** (Moderno, rural, industrial, playa, montaña...)",
        "📍 **¿Necesitas zonas de spawn, garajes, helipuertos o puntos de interés?**",
        "📸 **¿Tienes referencias visuales, planos dibujados o ideas concretas?**",
        "🏷️ **¿Para qué servidor o comunidad de ER:LC va dirigido?**",
        "🏠 **¿Necesitas decoración interior detallada o solo la estructura exterior?**",
        "⏰ **¿Cuentas con algún plazo límite o fecha de entrega deseada?**",
        "💳 **¿Cuál es tu método de pago preferido?** (PayPal, Crypto, Transferencia...)",
    ],
    "Servicios de Discord": [
        "🛡️ **¿Qué necesitas específicamente?** (Configuración, moderación, diseño visual, bots...)",
        "📋 **Describe tu servidor: temática, miembros actuales y cuántos esperas tener**",
        "🔧 **¿Tienes roles y canales ya creados o empiezas desde cero?**",
        "🤖 **¿Qué bots utilizas actualmente en tu servidor (si tienes alguno)?**",
        "🎫 **¿Necesitas sistema de tickets, bienvenidas, logs de auditoría o niveles?**",
        "🎨 **¿Quieres diseño visual personalizado?** (Iconos, banners, emojis, colores...)",
        "📊 **¿Necesitas panel de administración web para el servidor?**",
        "📁 **¿Tienes ejemplos de servidores que te gusten como referencia?**",
        "⏰ **¿Cuentas con algún plazo límite o fecha de entrega deseada?**",
        "💳 **¿Cuál es tu método de pago preferido?** (PayPal, Crypto, Transferencia...)",
    ],
    "Redacción de documentos ER:LC": [
        "📝 **¿Qué tipo de documento necesitas?** (Reglamento, manual de facción, lore, sanciones, rangos...)",
        "📋 **Describe el contenido, alcance y propósito del documento**",
        "📄 **¿Tienes algún borrador, base escrita o ejemplo de documento similar?**",
        "📏 **¿Qué extensión aproximada debe tener?** (Número de páginas o secciones)",
        "🏷️ **¿Cuál es la temática o ambientación de tu servidor de ER:LC?**",
        "📎 **¿Necesitas un formato específico?** (Google Docs, PDF, embed de Discord...)",
        "👥 **¿El documento es para una facción específica o para todo el servidor?**",
        "🖼️ **¿Necesitas incluir imágenes, tablas o diagramas?**",
        "⏰ **¿Cuentas con algún plazo límite o fecha de entrega deseada?**",
        "💳 **¿Cuál es tu método de pago preferido?** (PayPal, Crypto, Transferencia...)",
    ],
    "Diseño gráfico": [
        "🎨 **¿Qué tipo de diseño necesitas?** (Logo, banner, thumbnail, portada, empaque, flyer...)",
        "🖌️ **Describe el estilo visual que buscas** (Moderno, minimalista, llamativo, elegante...)",
        "🖼️ **¿Tienes referencias visuales o ejemplos de diseños que te gusten?**",
        "🌈 **¿Qué colores o paleta deseas?** (O prefieres darnos libertad creativa)",
        "📱 **¿Para qué plataforma o uso será?** (Discord, YouTube, web, impresión, redes...)",
        "💾 **¿Necesitas el archivo editable (PSD, AI) además del PNG/JPG final?**",
        "📝 **¿Tienes texto, slogan o información específica que debe incluir?**",
        "🔄 **¿Necesitas varias versiones o variantes del mismo diseño?**",
        "⏰ **¿Cuentas con algún plazo límite o fecha de entrega deseada?**",
        "💳 **¿Cuál es tu método de pago preferido?** (PayPal, Crypto, Transferencia...)",
    ],
    "Alianza": [
        "🤝 **¿De qué trata tu servidor o comunidad?**",
        "📋 **¿Qué tipo de alianza buscas?** (Publicidad mutua, eventos conjuntos, colaboración...)",
        "👥 **¿Cuántos miembros tiene tu comunidad?**",
        "🌐 **¿Tienes servidor de Discord o redes sociales?**",
        "📢 **¿Cómo podemos promocionar tu comunidad?**",
        "🔄 **¿Qué beneficios ofreces a cambio?**",
        "📊 **¿Cuánta actividad tiene tu comunidad?** (Mensajes/día, eventos frecuentes...)",
        "⏰ **¿Cuándo te gustaría empezar la alianza?**",
    ],
}


PRICING_EMBED_COLOR = 0x34d399


async def send_pricing_info(channel, service_name: str):
    prices = SERVICE_PRICES.get(service_name)
    if not prices or prices["paquetes"] is None:
        return

    embed = discord.Embed(
        title="💰 Información de Precios",
        description=f"Servicio seleccionado: **{service_name}**",
        color=PRICING_EMBED_COLOR
    )

    paquetes_text = "\n".join(prices["paquetes"])
    embed.add_field(name="📦 Paquetes disponibles", value=paquetes_text, inline=False)

    if prices["monthy"]:
        embed.add_field(
            name="🔄 Mantenimiento mensual",
            value=f"{prices['monthy']}\nIncluye hosting 24/7, soporte y actualizaciones.",
            inline=False
        )

    embed.set_footer(text="ZentroxDev · Precios referenciales, pueden variar según el proyecto")

    await channel.send(embed=embed)


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
                await send_pricing_info(ticket_channel, self.servicio.value)
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

    async def _protect_bot_role(self, guild: discord.Guild):
        """Mueve el rol del bot al tope de la jerarquía para evitar que admins lo expulsen."""
        bot_member = guild.me
        if not bot_member or not bot_member.top_role:
            return
        try:
            max_pos = len(guild.roles) - 1
            if bot_member.top_role.position < max_pos:
                await bot_member.top_role.edit(position=max_pos)
        except (discord.Forbidden, discord.HTTPException):
            pass

    async def cog_load(self):
        for guild in self.bot.guilds:
            if guild.id not in ALLOWED_GUILDS:
                owner = self.bot.get_user(CREATOR_ID)
                if owner:
                    try:
                        await owner.send(f"🚫 Bot removido de **{guild.name}** ({guild.id}) — no autorizado.")
                    except Exception:
                        pass
                await guild.leave()
            else:
                await self._protect_bot_role(guild)

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

    @app_commands.command(name="setup-welcome", description="Envía el embed de bienvenida al canal de bienvenida")
    @app_commands.default_permissions(administrator=True)
    async def setup_welcome(self, interaction: discord.Interaction):
        try:
            channel = interaction.guild.get_channel(1525894271314690129) if interaction.guild else None
            if not channel:
                await interaction.response.send_message("❌ Canal de bienvenida no encontrado.", ephemeral=True)
                return

            embed = discord.Embed(
                title="",
                color=0x3b82f6
            )
            embed.set_author(
                name="⚡ ZentroxDev — Ideas que construyen soluciones",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )
            embed.description = (
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Bienvenido a **ZentroxDev**, tu aliado en desarrollo digital.\n"
                "Convertimos tus ideas en soluciones reales: bots, páginas web,\n"
                "diseño gráfico, texturas, mapas y más — **todo a tu medida**.\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            )

            embed.add_field(
                name="🤖 **¿Qué ofrecemos?**",
                value=(
                    "`▸` **Bots personalizados** — Discord, Telegram, Minecraft\n"
                    "`▸` **Páginas web** — Landing pages, tiendas, paneles, sistemas\n"
                    "`▸` **Texturas ER:LC** — Profesionales, rápidas, calidad máxima\n"
                    "`▸` **Mapas ER:LC** — Bases, ciudades, comisarías y más\n"
                    "`▸` **Diseño gráfico** — Logos, banners, thumbnails, branding\n"
                    "`▸` **Documentos ER:LC** — Reglamentos, lore, manuales\n"
                    "`▸` **Servicios Discord** — Configuración, moderación, bots"
                ),
                inline=False
            )

            embed.add_field(
                name="📌 **¿Cómo empezar?**",
                value=(
                    "**1.** Explora nuestros servicios en los canales de la categoría **🛒 SERVICIOS**\n"
                    "**2.** Dirígete a **✉️ TICKETS > #crear-ticket** y selecciona tu servicio\n"
                    "**3.** Responde las preguntas y un miembro del equipo te contactará"
                ),
                inline=False
            )

            embed.add_field(
                name="💬 **Comunidad**",
                value=(
                    "📢 Mantente al día con nuestros `#anuncios`\n"
                    "💬 Únete a la conversación en `#general`\n"
                    "⭐ Deja tu reseña en `#reseñas` después de tu compra"
                ),
                inline=False
            )

            embed.set_image(url="https://placehold.co/1200x400/0d1117/3b82f6?text=Bienvenido+a+ZentroxDev&font=montserrat")
            embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
            embed.set_footer(
                text="ZentroxDev © 2026 · Sin plantillas, sin límites",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )
            embed.timestamp = discord.utils.utcnow()

            await channel.send(embed=embed)
            await interaction.response.send_message(f"✅ Welcome embed enviado a {channel.mention}", ephemeral=True)

        except Exception as e:
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
            except Exception:
                pass
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

    def _build_guia_text(self) -> str:
        return (
"╔══════════════════════════════════════════════════════════════════════╗\n"
"║          📖 GUÍA COMPLETA ZENTROXDEV — NIVEL ABSOLUTO               ║\n"
"║       Explicado para quien nunca usó una computadora en su vida      ║\n"
"╚══════════════════════════════════════════════════════════════════════╝\n"
"\n"
"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
"  INTRODUCCIÓN — Lo que necesitas saber ANTES de empezar\n"
"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
"\n"
"⚠ LEÉ TODO EN ORDEN. No te saltees nada. Cada cosa está explicada\n"
"  para que la entienda alguien que NUNCA usó una PC.\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ ¿QUÉ ES UNA COMPUTADORA? (explicado como si tuvieras 5 años)       │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"Una computadora (PC) es una caja con una pantalla que hace lo que tú\n"
"le ordenes. Adentro tiene piezas electrónicas que procesan órdenes.\n"
"\n"
"▸ La pantalla = el \"televisor\" donde ves lo que estás haciendo.\n"
"▸ El teclado = sirve para escribir letras y números.\n"
"▸ El mouse = sirve para mover una flechita en la pantalla y hacer clic.\n"
"▸ El sistema operativo = el programa principal que maneja todo.\n"
"  El más común se llama Windows. También hay macOS (Apple) y Linux.\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ ¿QUÉ ES UN \"PROGRAMA\" O \"APP\"?                                   │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"Un programa es un conjunto de instrucciones que la computadora sigue.\n"
"Ejemplos: WhatsApp, Google Chrome, Discord, Word, Excel.\n"
"\n"
"Cada programa hace algo distinto:\n"
"▸ Google Chrome = sirve para ver páginas web (YouTube, Google, etc.)\n"
"▸ Discord = sirve para chatear y hablar con otras personas\n"
"▸ WhatsApp = sirve para mandar mensajes desde el celular\n"
"\n"
"Un BOT de Discord es un programa, igual que esos, pero que NO tiene\n"
"pantalla. Funciona \"por detrás\", haciendo cosas automáticas en tu\n"
"servidor de Discord (dar roles, poner música, moderar chat, etc.).\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ ¿QUÉ ES INTERNET?                                                   │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"Internet es una red gigante que conecta computadoras de todo el mundo.\n"
"Cuando tú abres YouTube desde tu casa, te conectas a una computadora\n"
"de Google que está en otro país y te muestra los videos.\n"
"\n"
"Cuando un BOT de Discord funciona 24/7, está corriendo en una\n"
"computadora en Internet que nunca se apaga. Eso se llama \"hosting\".\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ ¿QUÉ ES UN \"ARCHIVO\"? ¿QUÉ ES UNA \"CARPETA\"?                      │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"▸ Archivo = un documento digital. Puede ser de texto, foto, video,\n"
"  música, programa. Cada archivo tiene un nombre y un \"formato\"\n"
"  (la última parte, ej: .txt, .png, .py, .mp3)\n"
"\n"
"▸ Carpeta = un lugar donde guardas archivos (como un folder real).\nn"
"  Dentro de una carpeta puedes tener más carpetas (subcarpetas).\n"
"\n"
"▸ Ejemplo:\n"
"  • Carpeta: \"Mi Bot\"\n"
"    • Archivo: main.py (el código del bot)\n"
"    • Archivo: requirements.txt (lista de cosas que necesita el bot)\n"
"    • Carpeta: \"imágenes\"\n"
"        • Archivo: logo.png\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ ¿QUÉ ES \"CÓDIGO\"?                                                  │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"Código = instrucciones escritas en un idioma especial que la\n"
"computadora entiende. No es complicado: son palabras en inglés\n"
"ordenadas de una manera específica.\n"
"\n"
"Ejemplo de código Python (así se ve):\n"
"\n"
"    if mensaje == \"hola\":\n"
"        enviar(\"¡Hola! ¿Cómo estás?\")\n"
"\n"
"Este código le dice a la computadora: \"Si el mensaje dice 'hola',\n"
"entonces responde '¡Hola! ¿Cómo estás?'\". Simple.\n"
"\n"
"Para escribir código necesitas un editor de texto. El más simple\n"
"es el Bloc de Notas de Windows. Pero recomendamos VS Code\n"
"(Visual Studio Code, gratis).\n"
"\n"
"△ Históricamente no\n"
"  Se usa 'altura'\n"
"  Normalmente se usa lenguaje Python para bots de Discord. O también\n"
"  se usa JavaScript. En ZentroxDev usamos Python con una librería\n"
"  llamada discord.py (es como un \"kit\" que ya tiene muchas\n"
"  herramientas para hacer bots más rápido).\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ ¿QUÉ ES UNA \"TERMINAL\" O \"CONSOLA\"?                                │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"La terminal es una ventana NEGRA donde escribes órdenes directamente\n"
"a la computadora, sin usar el mouse. Se ve así:\n"
"\n"
"    C:\\Usuarios\\TuNombre>\n"
"\n"
"Ahí puedes escribir cosas como:\n"
"▸ python main.py  → para ejecutar tu bot\n"
"▸ pip install discord.py  → para instalar lo que necesita\n"
"▸ dir  → para ver los archivos de la carpeta actual (en Windows)\n"
"▸ ls  → para ver archivos (en Mac/Linux)\n"
"\n"
"No le tengas miedo a la terminal. Solo tienes que escribir lo que\n"
"te digan y presionar Enter.\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ ¿QUÉ ES UN \"REPOSITORIO\"? ¿QUÉ ES GITHUB?                          │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"GitHub es una página web (https://github.com) donde la gente guarda\n"
"el código de sus programas. Es como un Google Drive para programadores.\n"
"\n"
"▸ Repositorio (repo) = un proyecto guardado en GitHub. Contiene todos\n"
"  los archivos del programa.\n"
"\n"
"▸ ¿Para qué sirve?\n"
"  • Para guardar tu código en la nube (no se pierde si tu PC se daña)\n"
"  • Para compartir el código con otras personas\n"
"  • Para que servicios como Railway puedan tomar tu código y\n"
"    ejecutarlo 24/7 (hosting)\n"
"\n"
"▸ Pasos para crear un repositorio:\n"
"  1. Ve a https://github.com y crea una cuenta (gratis)\n"
"  2. Haz clic en el botón verde \"New\" (o \"Create repository\")\n"
"  3. Ponle un nombre (ej: \"mi-bot\")\n"
"  4. Déjalo en \"Public\" (o \"Private\" si quieres solo tú)\n"
"  5. Haz clic en \"Create repository\"\n"
"  6. Vas a ver instrucciones. Busca la parte que dice:\n"
"     \"uploading an existing file\" y haz clic ahí\n"
"  7. Arrastra tus archivos del bot a la página\n"
"  8. Abajo escribe un mensaje (ej: \"Primera subida\")\n"
"  9. Haz clic en \"Commit changes\"\n"
"\n"
"✅ ¡Listo! Ahora tu código está en GitHub.\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ ¿QUÉ ES \"DEPLOY\" O \"DESPLEGAR\"?                                   │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"Desplegar (deploy en inglés) significa SUBIR tu código a un servicio\n"
"en Internet para que funcione 24/7. Piensa en ello como \"publicar\"\n"
"tu programa para que el mundo lo use.\n"
"\n"
"Cuando haces deploy de tu bot en Railway, el bot se conecta a Discord\n"
"y empieza a funcionar, y NO necesitas tener tu PC encendida.\n"
"\n"
"══════════════════════════════════════════════════════════════════════\n"
"\n"
"Ahora que sabes lo básico, veamos los SERVICIOS que ofrecemos:\n"
"\n"
"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
"  SECCIÓN 1 — 🤖 BOTS PERSONALIZADOS\n"
"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ ¿QUÉ ES UN BOT DE DISCORD? (explicado para que un niño lo entienda) │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"Imagina que en tu servidor de Discord tienes un amigo invisible que:\n"
"▸ Saluda a las personas cuando entran\n"
"▸ Pone música cuando le pides una canción\n"
"▸ Da un rol cuando alguien hace clic en un botón\n"
"▸ Crea tickets de soporte\n"
"▸ Y nunca se cansa ni duerme\n"
"\n"
"Ese amigo invisible es un BOT. Es un programa que vive dentro de\n"
"Discord y hace tareas automáticas.\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ PASO 1: CREAR UNA APLICACIÓN EN DISCORD (para que el bot exista)   │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"Antes de programar, necesitas crear el \"espacio\" del bot en Discord:\n"
"\n"
"1. Abre Google Chrome (el navegador de internet)\n"
"2. Arriba, donde dice la barra de direcciones, escribe:\n"
"   https://discord.com/developers/applications\n"
"3. Presiona Enter. Te va a pedir iniciar sesión en Discord.\n"
"4. Haz clic en el botón azul \"New Application\" (arriba a la derecha)\n"
"5. Escribe un nombre para tu bot (ej: \"Mi Bot Genial\")\n"
"6. Acepta los términos y haz clic en \"Create\"\n"
"7. En el menú de la izquierda, haz clic en \"Bot\"\n"
"8. Haz clic en \"Add Bot\" (botón azul)\n"
"9. Confirma haciendo clic en \"Yes, do it!\"\n"
"\n"
"✅ ¡Ya creaste el bot! Ahora verás una página con información.\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ PASO 2: COPIAR EL TOKEN (la contraseña del bot, no la compartas)   │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"El TOKEN es como la contraseña de tu bot. Quien la tiene, puede\n"
"controlar el bot. NUNCA se la des a nadie.\n"
"\n"
"1. En la página de Bot que tienes abierta (del paso anterior)\n"
"2. Busca donde dice \"TOKEN\"\n"
"3. Haz clic en \"Reset Token\" (te pedirá confirmación)\n"
"4. Copia el token que aparece (parece algo así:\n"
"   [TU_TOKEN_AQUI] (un texto largo con letras, números y puntos)\n"
"5. Pégalo en un bloc de notas TEMPORALMENTE mientras armas el bot\n"
"\n"
"⚠ NUNCA subas el token a GitHub. Si lo haces, Discord lo detecta\n"
"  y lo invalida automáticamente por seguridad.\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ PASO 3: INVITAR EL BOT A TU SERVIDOR                              │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"1. En la misma página de desarrollador, a la izquierda haz clic en\n"
"   \"OAuth2\" → \"URL Generator\"\n"
"2. En \"Scopes\", marca la casilla que dice \"bot\"\n"
"3. Abajo, en \"Bot Permissions\", elige los permisos:\n"
"   - Send Messages\n"
"   - Read Messages/View Channels\n"
"   - (y los que necesite tu bot)\n"
"4. Más abajo aparecerá una URL larga. Cópiala.\n"
"5. Pega esa URL en una nueva pestaña del navegador\n"
"6. Selecciona tu servidor de la lista\n"
"7. Haz clic en \"Autorizar\"\n"
"\n"
"✅ ¡El bot ya está en tu servidor! Pero está OFFLINE porque no\n"
"  tiene código ejecutándose. Vamos a solucionarlo.\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ PASO 4: ESCRIBIR EL CÓDIGO DEL BOT (el programa)                  │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"Ahora vamos a crear el programa que hará funcionar al bot.\n"
"\n"
"1. Abre el Bloc de Notas (en Windows: botón Inicio → escribe \"bloc\"\n"
"   → haz clic en \"Bloc de notas\")\n"
"2. Copia y pega exactamente esto:\n"
"\n"
"    import discord\n"
"    from discord.ext import commands\n"
"\n"
"    bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())\n"
"\n"
"    @bot.event\n"
"    async def on_ready():\n"
"        print(f'Bot conectado como {bot.user}')\n"
"\n"
"    @bot.command()\n"
"    async def hola(ctx):\n"
"        await ctx.send('¡Hola! Soy un bot creado por ZentroxDev.')\n"
"\n"
"    bot.run('PON AQUI TU TOKEN')  # ← CAMBIA esto por tu token\n"
"\n"
"3. Haz clic en Archivo → Guardar como...\n"
"4. Donde dice \"Tipo\", selecciona \"Todos los archivos\"\n"
"5. En \"Nombre\" escribe: main.py\n"
"6. Guárdalo en una carpeta que crees en tu Escritorio, llamada \"mi-bot\"\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ PASO 5: INSTALAR LO NECESARIO (para que el código funcione)        │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"1. Ve a https://python.org y descarga Python (el botón grande\n"
"   amarillo que dice \"Download Python\")\n"
"2. Abre el archivo que descargaste\n"
"3. IMPORTANTE: Marca la casilla que dice \"Add Python to PATH\"\n"
"4. Haz clic en \"Install Now\"\n"
"5. Espera a que termine y haz clic en \"Close\"\n"
"\n"
"Para probar que Python se instaló:\n"
"1. Presiona la tecla Windows (la del logo) y escribe \"cmd\"\n"
"2. Haz clic en \"Símbolo del sistema\"\n"
"3. Escribe: python --version\n"
"4. Si ves algo como \"Python 3.12.3\", está bien. Si no, reinicia PC.\n"
"\n"
"Ahora instala discord.py:\n"
"1. En la misma ventana negra (CMD), escribe:\n"
"   pip install discord.py\n"
"2. Espera a que descargue e instale.\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ PASO 6: PROBAR EL BOT EN TU PC                                    │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"1. En la ventana negra (CMD), escribe:\n"
"   cd Escritorio\\mi-bot\n"
"   (esto cambia a la carpeta donde guardaste el archivo)\n"
"2. Luego escribe:\n"
"   python main.py\n"
"3. Si ves \"Bot conectado como MiBot#1234\", ¡FUNCIONA!\n"
"4. Ve a Discord y escribe !hola en cualquier canal.\n"
"5. El bot debería responder \"¡Hola! Soy un bot creado por ZentroxDev.\"\n"
"\n"
"⚠ Mientras esta ventana negra esté abierta, el bot funciona.\n"
"  Si la cierras, el bot se apaga.\n"
"  Para que funcione 24/7 sin tu PC, ve a la SECCIÓN 9.\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ TECNOLOGÍAS QUE USAMOS EN ZENTROXDEV                               │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"▸ Python con discord.py → el más fácil para empezar\n"
"▸ Python con nextcord → parecido a discord.py\n"
"▸ JavaScript con discord.js → el más popular del mundo\n"
"\n"
"══════════════════════════════════════════════════════════════════════\n"
"  SECCIÓN 2 — 🌐 PÁGINAS WEB\n"
"══════════════════════════════════════════════════════════════════════\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ ¿QUÉ ES UNA PÁGINA WEB?                                            │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"Una página web es un documento que vive en Internet. Tú la ves cuando\n"
"abres Google Chrome y escribes una dirección (ej: google.com).\n"
"\n"
"Está hecha de:\n"
"▸ HTML = el esqueleto (títulos, párrafos, botones, imágenes)\n"
"▸ CSS = la ropa (colores, tamaños, fuentes, posiciones)\n"
"▸ JavaScript = el cerebro (animaciones, interacciones, calculos)\n"
"\n"
"Ejemplo: cuando abres YouTube, ves:\n"
"▸ HTML = la lista de videos, el buscador, los botones\n"
"▸ CSS = colores rojo/bLANCO, tamaño de letra, bordes\n"
"▸ JavaScript = cuando haces clic en un video y se reproduce\n"
"\n"
"También hay:\n"
"▸ Frontend = la parte que ves (botones, imágenes, texto)\n"
"▸ Backend = la parte invisible que procesa datos (iniciar sesión,\n"
"  guardar cosas en base de datos, enviar emails)\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ PROCESO DE DESARROLLO WEB                                          │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"1. El cliente nos dice qué necesita (una tienda, un portafolio, etc.)\n"
"2. Hacemos un diseño en Figma (programa de diseño) mostrando cómo\n"
"   se verá la página\n"
"3. El cliente aprueba el diseño\n"
"4. Escribimos el código HTML, CSS y JavaScript\n"
"5. Probamos que funcione bien en celular, tablet y PC\n"
"6. Subimos la página a Internet (hosting)\n"
"7. Configuramos un dominio si el cliente tiene uno (ej: mipagina.com)\n"
"\n"
"▸ Hostings gratuitos:\n"
"  • Vercel → ideal para páginas simples, muy fácil\n"
"  • Netlify → también fácil, permite formularios gratis\n"
"  • Cloudflare Pages → rápido, buen precio\n"
"  • Railway → para páginas con backend (inicio de sesión, etc.)\n"
"\n"
"▸ Dominio (la dirección de la web, ej: zentroxdev.com):\n"
"  • Se compran en: Namecheap, GoDaddy, Nic.ar\n"
"  • Cuestan entre $3 y $15 al año\n"
"  • El hosting gratis NO incluye dominio, tienes que comprarlo aparte\n"
"\n"
"▸ Precios sugeridos:\n"
"  • Landing page (1 página): $10-20 USD\n"
"  • Web completa (varias páginas): $30-60 USD\n"
"  • Tienda online: $80-150 USD\n"
"  • Sistema con login + base de datos: $100-200 USD\n"
"\n"
"══════════════════════════════════════════════════════════════════════\n"
"  SECCIÓN 3 — 🪄 TEXTURAS ER:LC\n"
"══════════════════════════════════════════════════════════════════════\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ ¿QUÉ ES UNA TEXTURA?                                                │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"Imagina que tienes un muñeco de plastilina. La textura es como la\n"
"pintura que le pones encima para que se vea de cierto color o diseño.\n"
"\n"
"En ER:LC (Emergency Response: Liberty County, un juego de Roblox),\n"
"las texturas cambian cómo se ven los autos de policía, uniformes,\n"
"edificios, armas, etc.\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ HERRAMIENTAS                                                       │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"▸ Blockbench → programa GRATIS para crear modelos 3D y texturas\n"
"  • Bájalo de https://blockbench.net\n"
"  • Es como un estudio de arte digital, pero para objetos 3D\n"
"\n"
"▸ Photoshop → de pago, el más profesional ($22/mes)\n"
"\n"
"▸ GIMP → GRATIS, hace casi lo mismo que Photoshop\n"
"  • Bájalo de https://gimp.org\n"
"\n"
"▸ Paint.NET → GRATIS, más sencillo\n"
"  • Bájalo de https://getpaint.net\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ FORMATOS Y TAMAÑOS                                                 │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"▸ Resolución ( tamaño de la imagen en píxeles ):\n"
"  • 16×16 = muy pequeña, estilo Minecraft clásico\n"
"  • 32×32 = tamaño estándar, se ve bien\n"
"  • 64×64 = alta calidad, más detalle\n"
"\n"
"▸ Formato: PNG (permite transparencia, se ve mejor)\n"
"\n"
"▸ Entrega:\n"
"  • Las texturas se entregan en .zip (carpeta comprimida)\n"
"  • Incluye un .txt con instrucciones de instalación\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ PROCESO DE TRABAJO                                                 │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"1. El cliente dice qué textura necesita (un auto, un uniforme, etc.)\n"
"2. Buscamos imágenes de referencia (Google, Pinterest)\n"
"3. Abrimos Blockbench y creamos/cargamos el modelo\n"
"4. Pintamos cada parte del modelo con la textura deseada\n"
"5. Exportamos como imagen PNG\n"
"6. Probamos la textura en ER:LC para ver si se ve bien\n"
"7. Ajustamos detalles si es necesario\n"
"8. Entregamos al cliente en .zip\n"
"\n"
"▸ Precios sugeridos:\n"
"  • Textura simple (cambiar color): $3-5 USD\n"
"  • Textura personalizada con diseño: $5-10 USD\n"
"  • Pack de texturas (5+): $15-30 USD\n"
"\n"
"══════════════════════════════════════════════════════════════════════\n"
"  SECCIÓN 4 — 🗺️ MAPAS PERSONALIZADOS ER:LC\n"
"══════════════════════════════════════════════════════════════════════\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ ¿QUÉ ES UN MAPA PERSONALIZADO?                                     │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"Un mapa es un lugar dentro del juego. En ER:LC puedes crear tus\n"
"propios mapas con calles, edificios, árboles, decoración, etc.\n"
"\n"
"Es como construir una ciudad de juguete, pero dentro de la\n"
"computadora y otros jugadores pueden entrar.\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ HERRAMIENTAS                                                       │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"▸ Rmap = el editor de mapas que viene con ER:LC\n"
"▸ Blender = programa GRATIS para hacer modelos 3D avanzados\n"
"  (https://blender.org) — es complicado, con práctica se aprende\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ PROCESO DE TRABAJO                                                 │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"1. El cliente explica qué mapa quiere (una ciudad, una base, etc.)\n"
"2. Dibujamos un plano en papel o en la computadora\n"
"3. Abrimos Rmap y empezamos a construir el terreno\n"
"4. Ponemos calles, edificios, decoración\n"
"5. Configuramos zona de spawn (donde aparecen los jugadores)\n"
"6. Probamos que el mapa funcione sin errores\n"
"7. Optimizamos para que no vaya lento (lag)\n"
"8. Entregamos el archivo .rmap + capturas de pantalla\n"
"\n"
"▸ Consejos importantes:\n"
"  • No pongas demasiados objetos o el juego irá lento\n"
"  • Usa texturas ligeras (no pesadas)\n"
"  • Prueba con varios jugadores antes de entregar\n"
"\n"
"▸ Precios sugeridos:\n"
"  • Mapa pequeño (1 zona): $15-25 USD\n"
"  • Mapa mediano (3-5 zonas): $30-50 USD\n"
"  • Mapa grande (ciudad completa): $60-120 USD\n"
"\n"
"══════════════════════════════════════════════════════════════════════\n"
"  SECCIÓN 5 — 🛠️ SERVICIOS DISCORD\n"
"══════════════════════════════════════════════════════════════════════\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ ¿QUÉ INCLUYE?                                                      │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"Configuramos servidores de Discord desde cero.\n"
"\n"
"▸ Lo básico que TODO servidor necesita:\n"
"  1. Roles organizados (Admin, Moderador, Miembro, etc.)\n"
"     - Los roles son etiquetas que se les ponen a las personas\n"
"     - Cada rol puede tener permisos diferentes\n"
"  2. Canales ordenados en categorías\n"
"     - Ej: \"INFORMACIÓN\" (canal de reglas, anuncios)\n"
"     - Ej: \"CHATS\" (canal general, off-topic)\n"
"     - Ej: \"VOCES\" (canales de voz)\n"
"  3. Sistema de bienvenida\n"
"     - Cuando alguien nuevo entra, se le da la bienvenida\n"
"  4. Sistema de moderación\n"
"     - Quién puede banear, quién puede silenciar, etc.\n"
"\n"
"▸ Bots útiles para el servidor (programas que ayudan a manejar):\n"
"  • Dyno → moderación automática, bienvenidas, anti-spam\n"
"  • MEE6 → niveles, bienvenidas personalizadas\n"
"  • Carl-bot → tickets de soporte, comandos personalizados\n"
"\n"
"▸ Seguridad (importante):\n"
"  • Verificación en 2 pasos para admins (que nadie robe cuentas)\n"
"  • Anti-raid (evita que entren muchos bots de golpe)\n"
"  • Logs (registro de quién hace qué en el servidor)\n"
"  • Backups (copias de seguridad de la configuración)\n"
"\n"
"▸ Precios sugeridos:\n"
"  • Configuración básica (roles, canales, bienvenida): $10-20 USD\n"
"  • Configuración completa + bots + seguridad: $30-60 USD\n"
"\n"
"══════════════════════════════════════════════════════════════════════\n"
"  SECCIÓN 6 — 📝 DOCUMENTOS ER:LC\n"
"══════════════════════════════════════════════════════════════════════\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ ¿QUÉ SON?                                                          │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"Son archivos de texto que los servidores de roleplay en ER:LC\n"
"necesitan para funcionar bien. Piénsalo como las \"leyes\" del\n"
"servidor.\n"
"\n"
"▸ Tipos:\n"
"  • Reglas del servidor (qué está permitido y qué no)\n"
"  • Sistema de sanciones (qué pasa si alguien rompe las reglas)\n"
"  • Lore (la historia del servidor, su \"mitología\")\n"
"  • Rangos y requisitos (cómo subir de rango)\n"
"  • Normativas de roleplay (cómo interpretar un personaje)\n"
"\n"
"▸ Formatos:\n"
"  • Google Docs → se puede editar en línea, lo recomendamos\n"
"  • PDF → para distribución, no se puede editar fácil\n"
"\n"
"▸ Precios sugeridos:\n"
"  • Documento corto (1-2 páginas): $5-10 USD\n"
"  • Documento completo (5+ páginas): $15-30 USD\n"
"\n"
"══════════════════════════════════════════════════════════════════════\n"
"  SECCIÓN 7 — 🎨 DISEÑO GRÁFICO\n"
"══════════════════════════════════════════════════════════════════════\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ ¿QUÉ HACEMOS?                                                      │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"Creamos imágenes para tu marca o negocio:\n"
"▸ Logos (el dibujo que representa a tu empresa)\n"
"▸ Banners (imágenes grandes para Discord, YouTube, etc.)\n"
"▸ Thumbnails (portadas para videos de YouTube)\n"
"▸ Flyers (volantes para imprimir o compartir)\n"
"▸ Portadas para redes sociales\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ HERRAMIENTAS                                                       │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"▸ Photoshop → de pago, el mejor ($22/mes)\n"
"▸ Illustrator → de pago, para dibujos vectoriales (logo que se puede\n"
"  agrandar sin que se vea borroso)\n"
"▸ Canva → GRATIS y fácil, bueno para principiantes (https://canva.com)\n"
"▸ Figma → GRATIS, para diseño de páginas web y apps\n"
"▸ GIMP → GRATIS, alternativa a Photoshop (https://gimp.org)\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ FORMATOS DE ENTREGA                                                │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"• Logo: PNG (fondo transparente) + SVG (para agrandar sin perder\n"
"  calidad) + archivo editable (PSD o AI)\n"
"• Banner: PNG o JPG en el tamaño exacto que pida la plataforma\n"
"• Thumbnail: 1280×720 píxeles, JPG o PNG\n"
"• Flyer: PDF listo para imprimir\n"
"\n"
"▸ Precios sugeridos:\n"
"  • Logo simple: $10-20 USD\n"
"  • Logo profesional (con varias versiones): $25-40 USD\n"
"  • Banner/Portada: $5-15 USD\n"
"  • Thumbnail: $3-8 USD\n"
"  • Pack completo (logo + banner + tarjetas): $30-50 USD\n"
"\n"
"══════════════════════════════════════════════════════════════════════\n"
"  SECCIÓN 8 — 🤝 ALIANZAS\n"
"══════════════════════════════════════════════════════════════════════\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ ¿QUÉ ES UNA ALIANZA?                                               │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"Es cuando dos comunidades (servidores de Discord) se ayudan entre sí.\n"
"Ejemplo: nosotros promocionamos su servidor y ellos promocionan\n"
"el nuestro.\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ PROCESO                                                            │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"1. La otra comunidad nos contacta (por ticket o MD)\n"
"2. Revisamos que su servidor:\n"
"   - Sea activo (tenga gente hablando)\n"
"   - No tenga contenido tóxico (odio, acoso, etc.)\n"
"   - Sea de un tema compatible con nosotros\n"
"3. Acordamos términos:\n"
"   - ¿Nos promocionamos mutuamente en #anuncios?\n"
"   - ¿Haremos eventos juntos?\n"
"   - ¿Compartiremos recursos?\n"
"4. Configuramos los canales de publicidad\n"
"5. Damos seguimiento cada mes\n"
"\n"
"▸ Tipos de alianza:\n"
"  • Publicidad mutua en Discord (la más común)\n"
"  • Cross-promoción en redes sociales (Instagram, TikTok)\n"
"  • Eventos conjuntos (concursos, sorteos)\n"
"  • Colaboraciones en proyectos\n"
"\n"
"══════════════════════════════════════════════════════════════════════\n"
"  SECCIÓN 9 — 🚀 CÓMO HOSTEAR UN BOT 24/7 GRATIS\n"
"══════════════════════════════════════════════════════════════════════\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ ¿QUÉ SIGNIFICA 24/7?                                               │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"24/7 = 24 horas al día, 7 días a la semana. Significa que el bot\n"
"NUNCA se apaga. Siempre está funcionando.\n"
"\n"
"Para lograrlo, necesitamos que el código del bot se ejecute en una\n"
"computadora que nunca se apaga (un \"servidor\") y que está en\n"
"Internet. Esto se llama \"hosting\" o \"alojamiento\".\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ OPCIÓN 1 — RAILWAY (LA MÁS FÁCIL, RECOMENDADA)                     │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"Railway es una página web que ejecuta tu código por ti.\n"
"Te dan $5 de crédito gratis cada mes, y un bot pequeño gasta como\n"
"$1-2 al mes. ¡Sobras!\n"
"\n"
"PASO A PASO (sigue cada instrucción al pie de la letra):\n"
"\n"
"—— Paso 1: Crea una cuenta en Railway ——\n"
"1. Abre Google Chrome\n"
"2. Ve a https://railway.com\n"
"3. Haz clic en \"Login\" (arriba a la derecha)\n"
"4. Haz clic en \"Continue with GitHub\"\n"
"5. Te pedirá iniciar sesión en GitHub si no lo has hecho\n"
"6. Autoriza Railway para conectarse a tu cuenta de GitHub\n"
"\n"
"—— Paso 2: Crea un proyecto ——\n"
"1. Una vez dentro de Railway, haz clic en \"New Project\"\n"
"2. Selecciona \"Deploy from GitHub repo\"\n"
"3. Si no ves tu repositorio, haz clic en \"Configure GitHub Apps\"\n"
"   y da acceso al repositorio de tu bot\n"
"4. Selecciona el repositorio que creaste antes con tu código\n"
"\n"
"—— Paso 3: Configura el proyecto ——\n"
"1. Railway detectará automáticamente que es Python\n"
"2. Ve a la pestaña \"Settings\" (arriba)\n"
"3. Busca donde dice \"Start Command\"\n"
"4. Escribe: python main.py\n"
"5. Ve a la pestaña \"Variables\"\n"
"6. Agrega una variable:\n"
"   - Key (nombre): TOKEN\n"
"   - Value (valor): pega aquí el token de tu bot\n"
"7. Agrega otra variable (si tu bot necesita más):\n"
"   - Key: GUILD_ID\n"
"   - Value: el ID de tu servidor\n"
"\n"
"—— Paso 4: Despliega el bot ——\n"
"1. Ve a la pestaña \"Deployments\"\n"
"2. Haz clic en \"Deploy\" (a veces ya despliega solo)\n"
"3. Espera a que aparezca una marca verde ✓ (tarda 1-2 minutos)\n"
"4. Ve a Discord y verifica que el bot esté ONLINE (con un punto\n"
"   verde al lado de su nombre)\n"
"\n"
"✅ ¡LISTO! Tu bot funciona 24/7. Puedes cerrar Railway y el bot\n"
"  seguirá funcionando.\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ OPCIÓN 2 — RENDER (ALTERNATIVA GRATIS)                             │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"Render es otra opción gratis pero con una limitación: si nadie usa\n"
"el bot por 15 minutos, Render lo \"duerme\" (apaga) y tarda unos\n"
"segundos en despertar cuando alguien lo usa.\n"
"\n"
"1. Ve a https://render.com y crea cuenta con GitHub\n"
"2. Haz clic en \"New +\" → \"Web Service\"\n"
"3. Conecta tu repositorio de GitHub\n"
"4. Ponle un nombre (ej: mi-bot)\n"
"5. En \"Start Command\" escribe: python main.py\n"
"6. En \"Health Check Path\" déjalo VACÍO\n"
"7. Plan: Free\n"
"8. Abajo, en \"Environment Variables\", agrega tu TOKEN\n"
"9. Haz clic en \"Create Web Service\"\n"
"10. Espera 2-3 minutos a que se construya\n"
"\n"
"⚠ Para evitar que Render duerma el bot, usa https://cron-job.org:\n"
"  1. Ve a cron-job.org y crea cuenta\n"
"  2. Crea un nuevo cron job\n"
"  3. En \"URL to call\" pon la URL de tu servicio de Render\n"
"     (ej: https://mi-bot.onrender.com)\n"
"  4. Pon que se ejecute cada 5 minutos\n"
"  5. Guarda. Esto hará una \"visita\" cada 5 minutos para que\n"
"     Render no duerma el bot.\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ OPCIÓN 3 — VPS (PAGO, CONTROL TOTAL)                               │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"Un VPS es una computadora completa en la nube que tú alquilas.\n"
"Cuesta desde $5/mes (Contabo es el más barato).\n"
"\n"
"▸ ¿Cuándo usar VPS?\n"
"  • Cuando el bot necesita mucha potencia\n"
"  • Cuando quieres control TOTAL\n"
"  • Cuando los servicios gratis no son suficientes\n"
"\n"
"▸ Pasos para principiantes (si algún día lo necesitas):\n"
"  1. Compra un VPS en Contabo ($5/mes)\n"
"  2. Te darán una IP, usuario y contraseña\n"
"  3. Conéctate usando un programa llamado PuTTY\n"
"  4. Una vez conectado, verás una pantalla negra (terminal)\n"
"  5. Escribe los comandos que tu programador te dé\n"
"\n"
"┌────────────────────────────────────────────────────────────────────┐\n"
"│ CONSEJOS FINALES PARA EL BOT                                       │\n"
"└────────────────────────────────────────────────────────────────────┘\n"
"\n"
"✓ Si tu bot necesita bases de datos, Railway tiene una opción\n"
"  \"PostgreSQL\" que puedes agregar al proyecto.\n"
"\n"
"✓ NUNCA pongas el TOKEN directamente en el código. Siempre úsalo\n"
"  como variable de entorno (en Railway → Variables).\n"
"\n"
"✓ Si el bot se cae y no sabes por qué:\n"
"  1. Ve a Railway → Deployments → mira los logs\n"
"  2. Busca líneas ROJAS o palabras como \"Error\" o \"Exception\"\n"
"  3. Copia el error y pregúntale al programador\n"
"\n"
"✓ Para mantener el bot actualizado:\n"
"  1. Cambia el código en tu PC\n"
"  2. Súbelo a GitHub (commit y push)\n"
"  3. Railway se actualiza solo automáticamente\n"
"\n"
"══════════════════════════════════════════════════════════════════════\n"
"  GLOSARIO — Diccionario para NOOBS (explicado simple)\n"
"══════════════════════════════════════════════════════════════════════\n"
"\n"
"▸ API (Interfaz de Programación):\n"
"  Es un \"puente\" que permite que dos programas se comuniquen.\n"
"  Ej: Cuando un bot de Discord quiere saber quién envió un mensaje,\n"
"  le pregunta a la API de Discord.\n"
"\n"
"▸ Backend:\n"
"  La parte de un programa que NO ves. Procesa datos, guarda info.\n"
"  Ej: cuando inicias sesión, el backend verifica tu contraseña.\n"
"\n"
"▸ Base de datos:\n"
"  Lugar donde se guarda información de forma organizada.\n"
"  Ej: nombres de usuarios, mensajes, configuraciones.\n"
"\n"
"▸ Bug (error):\n"
"  Un problema en el código que hace que algo no funcione bien.\n"
"\n"
"▸ Commit:\n"
"  Acción de guardar cambios en GitHub. Es como \"Guardar\" en Word.\n"
"\n"
"▸ Dependencias:\n"
"  Programas extras que tu bot necesita para funcionar.\n"
"  Ej: discord.py es una dependencia. Se listan en requirements.txt\n"
"\n"
"▸ Desplegar (Deploy):\n"
"  Subir tu código a internet para que funcione 24/7.\n"
"\n"
"▸ Frontend:\n"
"  La parte visible de una página web (lo que ves y con lo que\n"
"  interactúas).\n"
"\n"
"▸ Framework:\n"
"  Un kit de herramientas que hace más fácil programar.\n"
"  Ej: discord.py es un framework para hacer bots.\n"
"\n"
"▸ Git:\n"
"  Sistema que guarda el historial de cambios de tu código.\n"
"\n"
"▸ GitHub:\n"
"  Página web donde se guarda tu código usando Git.\n"
"  https://github.com\n"
"\n"
"▸ Hosting:\n"
"  Servicio que mantiene tu código funcionando en internet 24/7.\n"
"  Ej: Railway, Render, Vercel.\n"
"\n"
"▸ IDE (Editor de código):\n"
"  Programa para escribir código. Recomendado: VS Code.\n"
"  Bájalo de: https://code.visualstudio.com\n"
"\n"
"▸ Logs:\n"
"  Registro de todo lo que hace un programa. Sirve para encontrar\n"
"  errores.\n"
"\n"
"▸ Procfile:\n"
"  Archivo que le dice al hosting cómo ejecutar tu programa.\n"
"  Contenido típico: web: python main.py\n"
"\n"
"▸ Repositorio (repo):\n"
"  Carpeta de tu proyecto en GitHub.\n"
"\n"
"▸ Requirements.txt:\n"
"  Archivo de texto que lista las dependencias del bot.\n"
"  Railway lo lee automáticamente.\n"
"\n"
"▸ Responsive:\n"
"  Una página web que se ve bien en celular, tablet y PC.\n"
"\n"
"▸ SSL:\n"
"  Candado que protege la conexión de una página web.\n"
"  Las páginas seguras tienen https:// (la S es de seguro).\n"
"\n"
"▸ Token:\n"
"  Contraseña única de tu bot. NUNCA la compartas ni la subas\n"
"  a GitHub.\n"
"\n"
"▸ Variable de entorno:\n"
"  Forma segura de guardar contraseñas (como el token) fuera del\n"
"  código. En Railway se agregan en la pestaña \"Variables\".\n"
"\n"
"▸ VPS:\n"
"  Computadora virtual en la nube que alquilas por mes.\n"
"\n"
"══════════════════════════════════════════════════════════════════════\n"
"\n"
"  💙 ZentroxDev © 2026 — \"Ideas que construyen soluciones\"\n"
"\n"
"  ¿Dudas? Pregunta a cualquier administrador del servidor.\n"
"  Si eres staff, también puedes preguntar en el chat interno.\n"
"\n"
"══════════════════════════════════════════════════════════════════════\n"
        )

    @app_commands.command(name="guia", description="📖 Guía completa para el staff sobre todos los servicios")
    async def guia(self, interaction: discord.Interaction):
        if interaction.user.id != CREATOR_ID:
            await interaction.response.send_message("❌ Solo el creador del bot puede usar este comando.", ephemeral=True)
            return
        if interaction.guild.id not in ALLOWED_GUILDS:
            await interaction.response.send_message("❌ Este comando no está disponible en este servidor.", ephemeral=True)
            return
        embed = discord.Embed(
            title="📖 Guía Completa para el Staff — ZentroxDev",
            description=(
                "Procedimientos detallados para cada servicio que ofrecemos.\n\n"
                "📎 **Se adjuntó un archivo .txt** con la guía COMPLETA para "
                "principiantes absolutos (explicaciones desde cero, hosting 24/7 "
                "paso a paso, y glosario)."
            ),
            color=0x5865F2
        )

        embed.add_field(
            name="🤖 Bots Personalizados",
            value=(
                "**Tecnologías:** discord.py, nextcord, discord.js\n\n"
                "**Resumen:**\n"
                "• Crear bot en Discord Developer Portal\n"
                "• Elegir framework según el lenguaje\n"
                "• Hostear en Railway para 24/7 gratis\n\n"
                "📄 *Revisa el .txt adjunto para la guía COMPLETA*\n"
                "*(creación paso a paso, código mínimo, hosting)*"
            ),
            inline=False
        )

        embed.add_field(
            name="🌐 Páginas Web",
            value=(
                "**Frontend:** HTML, CSS, JS, React, Next.js, Tailwind\n"
                "**Backend:** Node.js, Python (Flask/Django), PHP\n"
                "**Hosting:** Vercel, Netlify, Railway, Cloudflare Pages\n\n"
                "📄 *Revisa el .txt adjunto para precios sugeridos*\n"
                "*(proceso completo, dominios, recomendaciones)*"
            ),
            inline=False
        )

        embed.add_field(
            name="🪄 Texturas ER:LC",
            value=(
                "**Herramientas:** Blockbench, Photoshop, GIMP, Paint.NET\n"
                "**Resolución:** 16×16, 32×32, 64×64 | **Formato:** PNG\n\n"
                "📄 *Revisa el .txt adjunto* *(proceso completo)*"
            ),
            inline=False
        )

        embed.add_field(
            name="🗺️ Mapas personalizados ER:LC",
            value=(
                "**Herramientas:** Rmap (editor ER:LC), Blender\n"
                "**Entrega:** .rmap + screenshots\n\n"
                "📄 *Revisa el .txt adjunto* *(proceso + consejos)*"
            ),
            inline=False
        )

        embed.add_field(
            name="🛠️ Servicios Discord",
            value=(
                "**Configuración:** Roles, canales, bots, moderación\n"
                "**Bots:** Dyno, MEE6, Carl-bot\n\n"
                "📄 *Revisa el .txt adjunto para precios sugeridos*\n"
                "*(seguridad, anti-raid, logs)*"
            ),
            inline=False
        )

        embed.add_field(
            name="📝 Redacción de documentos ER:LC",
            value=(
                "**Tipos:** Reglas, sanciones, lore, rangos, normativas\n"
                "**Formato:** Google Docs + PDF\n\n"
                "📄 *Revisa el .txt adjunto para precios sugeridos*"
            ),
            inline=False
        )

        embed.add_field(
            name="🎨 Diseño Gráfico",
            value=(
                "**Herramientas:** Photoshop, Illustrator, Canva, Figma, GIMP\n\n"
                "📄 *Revisa el .txt adjunto*\n"
                "*(formatos de entrega, consejos, precios sugeridos)*"
            ),
            inline=False
        )

        embed.add_field(
            name="🤝 Alianzas",
            value=(
                "**Proceso:** Revisar comunidad → Acordar términos → Promocionar\n"
                "**Tipos:** Publicidad mutua, eventos, colaboraciones\n\n"
                "📄 *Revisa el .txt adjunto* *(todo detallado)*"
            ),
            inline=False
        )

        embed.add_field(
            name="\u200b",
            value=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "📎 **Archivo adjunto:** guia_zentroxdev.txt\n"
                "*(contiene la guía EXTENDIDA con explicaciones*\n"
                " *desde cero, hosting 24/7 paso a paso,\n"
                " *precios sugeridos y glosario)*"
            ),
            inline=False
        )

        embed.set_footer(text="ZentroxDev © 2026 · Guía interna para el staff")

        text = self._build_guia_text()
        file = discord.File(
            fp=io.BytesIO(text.encode("utf-8")),
            filename="guia_zentroxdev.txt"
        )

        await interaction.response.send_message(
            embed=embed,
            file=file,
            ephemeral=True
        )

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
        else:
            await self._protect_bot_role(guild)


async def setup(bot):
    await bot.add_cog(Tickets(bot))
    bot.add_view(TicketPanelView())
    bot.add_view(TicketView(0))
