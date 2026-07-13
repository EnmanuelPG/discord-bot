import discord
import asyncio
import time
import os
import pathlib
from discord.ext import commands

WELCOME_CHANNEL_ID = 1525894271314690129
TICKET_CHANNEL_ID = 1525894274250707058
DEDUP_DIR = pathlib.Path("/tmp/welcome_dedup")


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            if member.guild.id != 1525894268651176159:
                return

            if not self._claim(member.id):
                return

            channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
            if not channel:
                return

            guild_icon = member.guild.icon.url if member.guild.icon else ""
            ticket_ch = member.guild.get_channel(TICKET_CHANNEL_ID)

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

            await asyncio.sleep(0.5)

            try:
                async for old in channel.history(limit=10):
                    if old.id == msg.id:
                        continue
                    if old.author == self.bot.user and str(member.id) in old.content:
                        await old.delete()
                        break
            except Exception:
                pass

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
            except discord.Forbidden:
                pass
        except Exception as e:
            print(f"[WELCOME] Error: {e}")

    def _claim(self, member_id: int) -> bool:
        DEDUP_DIR.mkdir(parents=True, exist_ok=True)
        flag = DEDUP_DIR / str(member_id)
        try:
            fd = os.open(str(flag), os.O_CREAT | os.O_EXCL)
            os.close(fd)
            return True
        except FileExistsError:
            return False

    async def _cleanup_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(60)
            cutoff = time.time() - 60
            for f in DEDUP_DIR.iterdir():
                try:
                    if f.stat().st_mtime < cutoff:
                        f.unlink(missing_ok=True)
                except Exception:
                    pass

    async def cog_load(self):
        asyncio.create_task(self._cleanup_loop())


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
