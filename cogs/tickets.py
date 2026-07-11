import discord
from discord.ext import commands
import re

PEDIDOS_CHANNEL_ID = 1524947903775375551
DEVELOPER_ROLE_ID = 1525311162499993730
TICKETS_CATEGORY_NAME = "TICKETS"
WEBHOOK_URL = "https://discord.com/api/webhooks/1525275298369769653/Bp1OQijkZmBKyZvGlN6FnrgD89JCJVZ3oVb9KXDVpE2QEBm5dY-kVfpnEj-B2rYvnhuV"


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
    await ticket_channel.send(content=welcome_text, embed=welcome_embed)
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


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
            if "Informacion del pedido" in field.name or "Informacion del pedido" in field.name:
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
