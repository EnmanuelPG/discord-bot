import discord
from discord.ext import commands
import re

PEDIDOS_CHANNEL_ID = 1524947903775375551
DEVELOPER_ROLE_ID = 1525311162499993730
TICKETS_CATEGORY_NAME = "TICKETS"
WEBHOOK_URL = "https://discord.com/api/webhooks/1525275298369769653/Bp1OQijkZmBKyZvGlN6FnrgD89JCJVZ3oVb9KXDVpE2QEBm5dY-kVfpnEj-B2rYvnhuV"

async def create_ticket_channel(guild, ticket_id, embed, discord_username=None):
    category = discord.utils.get(guild.categories, name=TICKETS_CATEGORY_NAME)
    if not category:
        category = await guild.create_category(
            TICKETS_CATEGORY_NAME,
            reason="Categoría para tickets de pedidos"
        )

    channel_name = ticket_id.lower().replace('#', '')
    existing = discord.utils.get(guild.channels, name=channel_name)
    if existing:
        return existing, False

    member = None
    if discord_username:
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
        reason=f"Ticket {ticket_id} creado automáticamente"
    )

    welcome_embed = discord.Embed(
        title=f"🎫 Ticket {ticket_id}",
        description=f"**Nuevo pedido recibido**\n{embed.title if hasattr(embed, 'title') and embed.title else ''}",
        color=0x3b82f6,
    )
    if hasattr(embed, 'fields') and embed.fields:
        for field in embed.fields:
            welcome_embed.add_field(name=field.name, value=field.value, inline=field.inline)
    welcome_embed.set_footer(text="ZentroxDev · Ticket automático")

    member_mention = member.mention if member else "*(usuario no encontrado)*"
    welcome_text = (
        f"{member_mention}\n\n"
        f"**¡Bienvenido a tu ticket!**\n"
        f"Un desarrollador te atenderá pronto. Mientras tanto, puedes ir explicando tu pedido con más detalle."
    )
    await ticket_channel.send(content=welcome_text, embed=welcome_embed)

    return ticket_channel, True


async def update_webhook_embed(bot, message_id, embed, ticket_channel):
    new_embed = embed.copy()
    new_embed.url = ticket_channel.jump_url
    try:
        webhook = discord.Webhook.from_url(WEBHOOK_URL, client=bot)
        await webhook.edit_message(message_id, embed=new_embed)
    except Exception as e:
        print(f"No se pudo editar el mensaje del webhook: {e}")
        try:
            await message.edit(embed=new_embed)
        except:
            pass


async def send_embed_to_pedidos(guild, bot_user, ticket_id, service_name, detalle, metodo, usuario, ticket_channel):
    pedidos_channel = guild.get_channel(PEDIDOS_CHANNEL_ID)
    if not pedidos_channel:
        return None

    service_thumbnails = {
        'bots': 'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f916.png',
        'web': 'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f310.png',
        'texturas': 'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1fa84.png',
        'mapas': 'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f5fa.png',
        'discord': 'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f6e0.png',
        'documentos': 'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f4dd.png',
        'diseno': 'https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f3a8.png',
    }
    service_keys = {
        'Bots Personalizados': 'bots', 'Páginas Web': 'web', 'Texturas de ER:LC': 'texturas',
        'Mapas personalizados ER:LC': 'mapas', 'Servicios de Discord': 'discord',
        'Redacción de documentos ER:LC': 'documentos', 'Diseño gráfico': 'diseno'
    }
    key = service_keys.get(service_name, 'bots')
    thumb = service_thumbnails.get(key, service_thumbnails['bots'])

    embed = discord.Embed(
        color=0x3b82f6,
        title=f'📦 {service_name}',
        url=ticket_channel.jump_url,
        description='🎯 **Bienvenido y gracias por confiar en ZentroxDev.**\nHemos recibido tu solicitud y uno de nuestros administradores la revisará en breve.\n━━━━━━━━━━━━━━━━━━━━━━━━',
    )
    embed.set_thumbnail(url=thumb)
    embed.set_author(name='✨ Nuevo pedido recibido', icon_url='https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/2728.png')
    embed.add_field(
        name='📋 Información del pedido',
        value=f'```\nTicket: {ticket_id}\nServicio: {service_name}\n━━━━━━━━━━━━━━━━━━━\nDetalle: {detalle}\nPago: {metodo}\nDiscord: {usuario}```',
        inline=False
    )
    embed.add_field(
        name='📌 Próximos pasos',
        value=':black_small_square: Un miembro del equipo revisará tu solicitud.\n:black_small_square: Recibirás una respuesta por Discord en máximo **24 horas hábiles**.\n:black_small_square: Es posible que te solicitemos información adicional.\n:black_small_square: No cierres este ticket hasta que tu pedido esté finalizado.',
        inline=False
    )
    embed.add_field(
        name='💙 Gracias por tu preferencia',
        value='> *"Ideas que construyen soluciones"*\nEl equipo de ZentroxDev se pondrá en contacto contigo pronto. Si tienes alguna urgencia, responde a este mensaje.',
        inline=False
    )
    embed.set_footer(text='ZentroxDev © 2026 · Los administradores te contactarán pronto', icon_url='https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f3ab.png')

    sent = await pedidos_channel.send(embed=embed)
    return sent


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

        for field in embed.fields:
            if "Información del pedido" in field.name:
                value = field.value
                ticket_match = re.search(r'Ticket:\s*(\S+)', value)
                if ticket_match:
                    ticket_id = ticket_match.group(1)

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

        ticket_channel, created = await create_ticket_channel(
            message.guild, ticket_id, embed, discord_username
        )

        if not created:
            await message.channel.send(f"ℹ️ El canal {ticket_channel.mention} ya existe para el ticket {ticket_id}.")
            return

        await update_webhook_embed(self.bot, message.id, embed, ticket_channel)

        member_mention = ""
        if discord_username:
            m = message.guild.get_member_named(discord_username)
            if m:
                member_mention = m.mention
        await message.channel.send(
            f"✅ **Ticket {ticket_id}** creado → {ticket_channel.mention}  |  {member_mention if member_mention else discord_username or ''}"
        )

async def setup(bot):
    await bot.add_cog(Tickets(bot))
