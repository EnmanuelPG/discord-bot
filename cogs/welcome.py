import discord
import asyncio
import random
import uuid
from discord.ext import commands

WELCOME_CHANNEL_ID = 1525894271314690129
TICKET_CHANNEL_ID = 1525894274250707058
MEMBER_ROLE_ID = 1525894268651176162

INSTANCE_ID = uuid.uuid4().hex[:8]


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._lock = asyncio.Lock()
        print(f"[WELCOME] Cog loaded (instance={INSTANCE_ID})")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            if member.guild.id != 1525894268651176159:
                return

            print(f"[WELCOME] on_member_join: member={member.id} name={member.display_name} instance={INSTANCE_ID}")

            channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
            ticket_ch = member.guild.get_channel(TICKET_CHANNEL_ID)
            role = member.guild.get_role(MEMBER_ROLE_ID)

            if role:
                try:
                    await member.add_roles(role, reason="Autorol de bienvenida")
                    print(f"[WELCOME] Assigned role {role.name} to {member.id}")
                except Exception as e:
                    print(f"[WELCOME] Failed to assign role: {e}")

            if not channel:
                print("[WELCOME] Welcome channel not found")
                return

            async with self._lock:
                await asyncio.sleep(random.uniform(0.5, 1.2))
                try:
                    async for msg in channel.history(limit=5):
                        if msg.author == self.bot.user and str(member.id) in msg.content:
                            print(f"[WELCOME] Duplicate blocked (pre-send history check) for {member.id}")
                            return
                except Exception as e:
                    print(f"[WELCOME] Pre-send history check error: {e}")

            guild_icon = member.guild.icon.url if member.guild.icon else ""

            embed = discord.Embed(
                title=f"🚀 ¡Bienvenido a ZentroxDev, {member.display_name}!",
                description=(
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "Somos un estudio de desarrollo con experiencia en proyectos\n"
                    "para servidores, comunidades y creadores de contenido.\n"
                    "Cada trabajo lo tratamos con seriedad, desde el primer\n"
                    "boceto hasta la entrega final.\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                ),
                color=0x3b82f6
            )

            embed.set_thumbnail(url=guild_icon)
            if member.guild.banner:
                embed.set_image(url=member.guild.banner.url)
            else:
                embed.set_image(url="https://placehold.co/1200x400/0d1117/3b82f6?text=Bienvenido+a+ZentroxDev&font=montserrat")

            embed.add_field(
                name="🤖 **¿Qué hacemos?**",
                value=(
                    "`▸` **Bots** para Discord, Telegram y más\n"
                    "`▸` **Páginas web** modernas y responsivas\n"
                    "`▸` **Texturas y mapas** para ER:LC\n"
                    "`▸` **Diseño gráfico** — logos, banners, branding\n"
                    "`▸` **Documentos** — reglamentos, normativas\n"
                    "`▸` **Servicios Discord** — moderación, configuración"
                ),
                inline=False
            )

            embed.add_field(
                name="📌 **¿Cómo contratar?**",
                value=(
                    f"Dirígete a {ticket_ch.mention if ticket_ch else '**TICKETS**'}, "
                    "elige el servicio que necesitas\n"
                    "y responde el cuestionario. Te atenderemos a la brevedad."
                ),
                inline=False
            )

            embed.set_footer(
                text="ZentroxDev © 2026 · Sin plantillas, sin límites",
                icon_url=guild_icon
            )
            embed.timestamp = discord.utils.utcnow()

            msg = await channel.send(f"¡{member.mention}!", embed=embed)
            print(f"[WELCOME] Sent channel message {msg.id} for {member.id} (instance={INSTANCE_ID})")

            await asyncio.sleep(2)

            try:
                async for old in channel.history(limit=10):
                    if old.id == msg.id:
                        continue
                    if old.author == self.bot.user and str(member.id) in old.content:
                        print(f"[WELCOME] Deleting duplicate {old.id} (keeping {msg.id}) for {member.id}")
                        await old.delete()
                        break
            except Exception as e:
                print(f"[WELCOME] Post-send cleanup error: {e}")

            try:
                dm = discord.Embed(
                    title="👋 ¡Gracias por unirte a ZentroxDev!",
                    description=(
                        "Somos un equipo que desarrolla soluciones digitales\n"
                        "**desde cero**, sin plantillas ni atajos.\n\n"
                        "**🛒 ¿Necesitas algo?**\n"
                        f"Ve a {ticket_ch.mention if ticket_ch else 'TICKETS'} y abre un ticket\n\n"
                        "**💬 ¿Dudas?**\n"
                        "Pregunta en **#general** o **#chats**\n\n"
                        "¡Esperamos trabajar contigo! 🚀"
                    ),
                    color=0x3b82f6
                )
                dm.set_thumbnail(url=guild_icon)
                dm.set_footer(text="ZentroxDev © 2026 · Desarrollo profesional desde cero")
                await member.send(embed=dm)
                print(f"[WELCOME] Sent DM to {member.id}")
            except discord.Forbidden:
                print(f"[WELCOME] DM blocked for {member.id}")

            print(f"[WELCOME] Done processing {member.id} (instance={INSTANCE_ID})")
        except Exception as e:
            print(f"[WELCOME] UNHANDLED ERROR for {member.id}: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
