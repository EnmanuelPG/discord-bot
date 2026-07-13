import discord
from discord.ext import commands

WELCOME_CHANNEL_ID = 1525894271314690129


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild.id != 1525894268651176159:
            return

        channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
        if not channel:
            return

        embed = discord.Embed(
            title=f"🚀 ¡Bienvenido a ZentroxDev, {member.display_name}!",
            description=(
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Nos alegra tenerte aquí. **ZentroxDev** es un estudio de desarrollo\n"
                "digital especializado en crear soluciones **a tu medida**.\n"
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
                "Dirígete a **✉️ TICKETS > #crear-ticket**, elige tu servicio\n"
                "y responde el cuestionario. Te responderemos lo antes posible."
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
                    "Somos un equipo de desarrollo apasionado por crear\n"
                    "soluciones digitales **desde cero**, sin plantillas.\n\n"
                    "**🛒 ¿Necesitas algo?**\n"
                    "Ve a nuestro servidor y abre un ticket en **#crear-ticket**\n\n"
                    "**💬 ¿Dudas?**\n"
                    "Pregunta en **#general** o **#chats**\n\n"
                    "¡Esperamos trabajar contigo! 🚀"
                ),
                color=0x3b82f6
            )
            dm.set_thumbnail(url=member.guild.icon.url if member.guild.icon else None)
            dm.set_footer(text="ZentroxDev © 2026")
            await member.send(embed=dm)
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
