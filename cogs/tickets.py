import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import string
import re

PEDIDOS_CHANNEL_ID = 1524947903775375551
DEVELOPER_ROLE_ID = 1525311162499993730
TICKETS_CATEGORY_NAME = "TICKETS"
TICKET_PANEL_CHANNEL_ID = 1525888262470897734
WEBHOOK_URL = "https://discord.com/api/webhooks/1525275298369769653/Bp1OQijkZmBKyZvGlN6FnrgD89JCJVZ3oVb9KXDVpE2QEBm5dY-kVfpnEj-B2rYvnhuV"


class TicketCloseView(discord.ui.View):
    def __init__(self, creator_id: int):
        super().__init__(timeout=None)
        self.creator_id = creator_id

    @discord.ui.button(label="🔒 Cerrar ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        has_role = any(role.id == DEVELOPER_ROLE_ID for role in member.roles)
        is_creator = member.id == self.creator_id
        if not has_role and not is_creator:
            await interaction.response.send_message(
                "❌ Solo el creador del ticket o un administrador puede cerrarlo.", ephemeral=True
            )
            return
        await interaction.response.send_message(f"🔒 Cerrando ticket... Solicitado por {member.mention}")
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket cerrado por {member.name} ({member.id})")
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


async def create_ticket_channel(guild, ticket_id, embed, username):
    member = await find_member_in_guild(guild, username)
    category = discord.utils.get(guild.categories, name=TICKETS_CATEGORY_NAME)
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
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, manage_messages=True),
    }
    if developer_role:
        overwrites[developer_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
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
    view = TicketCloseView(creator_id=member.id if member else 0)
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
    title="Servicios 𝐓𝐢𝐜𝐤𝐞𝐭𝐬 [𝒁𝒆𝒏𝒕𝒓𝒐𝒙𝑫𝒆𝒗]",
    description=(
        "👋 ¡Bienvenido al sistema de tickets de **ZentroxDev**!\n\n"
        "Selecciona una categoría abajo según el servicio que necesites.\n"
        "Al hacer clic se creará un canal privado donde solo tú y nuestro "
        "equipo podrán ver y responder.\n\n"
        "📝 **Dentro del ticket** te pediremos los detalles de tu proyecto "
        "para poder ayudarte mejor."
    ),
    color=0x3b82f6
)
PANEL_EMBED.set_footer(text="ZentroxDev © 2026 · Sistema de Tickets")


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🤖 Bot de Discord", style=discord.ButtonStyle.primary, custom_id="panel_bot_discord", row=0)
    async def btn_bot_discord(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "Bot de Discord")

    @discord.ui.button(label="🌐 Página Web", style=discord.ButtonStyle.primary, custom_id="panel_web", row=0)
    async def btn_web(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "Página Web")

    @discord.ui.button(label="🎨 Diseño Gráfico", style=discord.ButtonStyle.success, custom_id="panel_diseno", row=1)
    async def btn_diseno(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "Diseño Gráfico")

    @discord.ui.button(label="⛏️ Bot de Minecraft", style=discord.ButtonStyle.success, custom_id="panel_bot_mc", row=1)
    async def btn_bot_mc(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "Bot de Minecraft")

    @discord.ui.button(label="📜 Scripts", style=discord.ButtonStyle.secondary, custom_id="panel_scripts", row=2)
    async def btn_scripts(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "Scripts")

    @discord.ui.button(label="⚙️ Configuración", style=discord.ButtonStyle.secondary, custom_id="panel_config", row=2)
    async def btn_config(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "Configuración")

    @discord.ui.button(label="💬 Soporte", style=discord.ButtonStyle.danger, custom_id="panel_soporte", row=3)
    async def btn_soporte(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._create_ticket(interaction, "Soporte")

    async def _create_ticket(self, interaction: discord.Interaction, service_name: str):
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("❌ Esto solo funciona en un servidor.", ephemeral=True)
            return
        ticket_id = f"ZTX-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
        dummy_embed = discord.Embed(title=f"📦 {service_name}")
        ticket_channel, created = await create_ticket_channel(guild, ticket_id, dummy_embed, interaction.user.name)
        if not created:
            await interaction.response.send_message(f"⚠️ Ya existe un ticket: {ticket_channel.mention}", ephemeral=True)
            return
        await ticket_channel.send(
            f"📝 **Cuéntanos más sobre tu solicitud de {service_name}**\n\n"
            f"▸ ¿Qué funcionalidades debe tener?\n"
            f"▸ ¿Tienes algún plazo límite?\n"
            f"▸ ¿Cuál es tu método de pago preferido?\n\n"
            f"Un miembro del equipo te atenderá en breve. 💙"
        )
        await interaction.response.send_message(
            f"✅ **Ticket {ticket_id}** creado → {ticket_channel.mention}",
            ephemeral=True
        )


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
        ticket_id = f"ZTX-{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"
        username = interaction.user.name
        guild = interaction.guild
        if not guild:
            await interaction.response.send_message("❌ Este comando solo funciona en un servidor.", ephemeral=True)
            return
        detalle_completo = self.detalle.value
        if self.plazo.value:
            detalle_completo += f"\n\n**Plazo:** {self.plazo.value}"
        dummy_embed = discord.Embed(title=f"📦 {self.servicio.value}")
        ticket_channel, created = await create_ticket_channel(guild, ticket_id, dummy_embed, username)
        if created:
            await send_embed_to_pedidos(guild, self.bot.user, ticket_id, self.servicio.value, detalle_completo, self.pago.value, username, ticket_channel)
        await interaction.response.send_message(
            f"✅ **Ticket {ticket_id} creado** → {ticket_channel.mention}",
            ephemeral=True
        )


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="panel", description="Envía el panel de tickets al canal configurado")
    @app_commands.default_permissions(administrator=True)
    async def panel(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(TICKET_PANEL_CHANNEL_ID) if interaction.guild else None
        if not channel:
            await interaction.response.send_message("❌ Canal de panel no encontrado.", ephemeral=True)
            return
        await channel.send(embed=PANEL_EMBED, view=TicketPanelView())
        await interaction.response.send_message(f"✅ Panel enviado a {channel.mention}", ephemeral=True)

    @app_commands.command(name="pedido", description="Solicita un servicio y crea un ticket")
    async def pedido(self, interaction: discord.Interaction):
        await interaction.response.send_modal(PedidoModal(self.bot))

    @app_commands.command(name="close", description="Cierra el ticket actual (solo admins o creador)")
    async def close(self, interaction: discord.Interaction):
        has_role = any(role.id == DEVELOPER_ROLE_ID for role in interaction.user.roles)
        creator_id = 0
        if interaction.channel.topic and interaction.channel.topic.startswith("creator:"):
            try:
                creator_id = int(interaction.channel.topic.split(":", 1)[1])
            except ValueError:
                pass
        if not has_role and interaction.user.id != creator_id:
            await interaction.response.send_message("❌ No tienes permiso para cerrar este ticket.", ephemeral=True)
            return
        await interaction.response.send_message(f"🔒 Cerrando ticket... Solicitado por {interaction.user.mention}")
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket cerrado por {interaction.user.name} ({interaction.user.id})")
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

        ticket_channel, created = await create_ticket_channel(guild, ticket_id, embed, discord_username)

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


async def setup(bot):
    await bot.add_cog(Tickets(bot))
    bot.add_view(TicketPanelView())
