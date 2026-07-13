import discord
import asyncio
import time
from discord.ext import commands

WELCOME_CHANNEL_ID = 1525894271314690129
TICKET_CHANNEL_ID = 1525894274250707058
DEDUP_SECONDS = 30


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._recent_joins = {}
        self._lock = asyncio.Lock()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != 1525894268651176159:
            return

        async with self._lock:
            now = time.time()
            last = self._recent_joins.get(member.id, 0)
            if now - last < DEDUP_SECONDS:
                return
            self._recent_joins[member.id] = now

        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if not channel:
            return

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

        embed.set_thumbnail(url=member.guild.icon.url if member.guild.icon else None)

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
            icon_url=member.guild.icon.url if member.guild.icon else None
        )
        embed.timestamp = discord.utils.utcnow()

        await channel.send(f"¡{member.mention}!", embed=embed)

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
            dm.set_thumbnail(url=member.guild.icon.url if member.guild.icon else None)
            dm.set_footer(text="ZentroxDev © 2026 · Desarrollo profesional desde cero")
            await member.send(embed=dm)
        except discord.Forbidden:
            pass

    async def _cleanup_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await asyncio.sleep(120)
            cutoff = time.time() - DEDUP_SECONDS
            async with self._lock:
                stale = [uid for uid, ts in self._recent_joins.items() if ts < cutoff]
                for uid in stale:
                    del self._recent_joins[uid]

    async def cog_load(self):
        self.bot.loop.create_task(self._cleanup_loop())


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
