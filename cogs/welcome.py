import discord
import asyncio
import random
import time
from discord.ext import commands

WELCOME_CHANNEL_ID = 1525894271314690129
TICKET_CHANNEL_ID = 1525894274250707058
MEMBER_ROLE_ID = 1525894268651176162


class Welcome(commands.Cog):
    _recent = {}
    _call_count = 0

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        print("[WELCOME] Cog loaded", flush=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        self._call_count += 1
        c = self._call_count
        print(f"[WELCOME] CALL #{c} member={member.id}", flush=True)

        try:
            if member.guild.id != 1525894268651176159:
                return

            now = time.time()
            last = self._recent.get(member.id, 0)
            if now - last < 120:
                print(f"[WELCOME] CALL #{c} -> dedup blocked", flush=True)
                return
            self._recent[member.id] = now

            await asyncio.sleep(random.uniform(0, 3))

            channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
            ticket_ch = member.guild.get_channel(TICKET_CHANNEL_ID)
            role = member.guild.get_role(MEMBER_ROLE_ID)

            if role:
                try:
                    await member.add_roles(role, reason="Autorol")
                except Exception as e:
                    print(f"[WELCOME] CALL #{c} -> role error: {e}", flush=True)

            if not channel:
                return

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
            print(f"[WELCOME] CALL #{c} -> sent {msg.id}", flush=True)

            await asyncio.sleep(2)

            is_winner = True
            async for old in channel.history(limit=15):
                if old.id == msg.id:
                    continue
                if old.author == self.bot.user and str(member.id) in old.content:
                    if old.id < msg.id:
                        is_winner = False
                        print(f"[WELCOME] CALL #{c} -> lost to {old.id}", flush=True)
                    else:
                        print(f"[WELCOME] CALL #{c} -> deleting {old.id}", flush=True)
                        await old.delete()

            if not is_winner:
                await msg.delete()
                print(f"[WELCOME] CALL #{c} -> deleted our msg, another was first", flush=True)
                return

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
                print(f"[WELCOME] CALL #{c} -> DM sent", flush=True)
            except discord.Forbidden:
                print(f"[WELCOME] CALL #{c} -> DM blocked", flush=True)

            print(f"[WELCOME] CALL #{c} -> done", flush=True)
        except Exception as e:
            print(f"[WELCOME] CALL #{c} -> ERROR: {e}", flush=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))
