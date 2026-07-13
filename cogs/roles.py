import discord
from discord.ext import commands

ROLE_CHANNEL_ID = 1526340362153627819

CATEGORIES = [
    {
        "id": "rp",
        "placeholder": "Pronombres",
        "max": 1,
        "options": [
            {"label": "Él / He",       "val": "1526346969855950922", "emoji": "\u2642\ufe0f"},
            {"label": "Ella / She",     "val": "1526346971210579978", "emoji": "\u2640\ufe0f"},
            {"label": "Elle / They",    "val": "1526346979402186865", "emoji": "\u26a7"},
        ]
    },
    {
        "id": "re",
        "placeholder": "Especialidad",
        "max": 1,
        "options": [
            {"label": "Developer",         "val": "1526346982048923801", "emoji": "\ud83d\udcbb"},
            {"label": "Disenador",         "val": "1526346984095486134", "emoji": "\ud83c\udfa8"},
            {"label": "Community Manager", "val": "1526346987350523987", "emoji": "\ud83d\udde3\ufe0f"},
            {"label": "Gamer",             "val": "1526346989036376117", "emoji": "\ud83c\udfae"},
        ]
    },
    {
        "id": "rr",
        "placeholder": "Region",
        "max": 1,
        "options": [
            {"label": "Latinoamerica",  "val": "1526346990827475094", "emoji": "\ud83c\uddf2\ud83c\uddfd"},
            {"label": "Norteamerica",   "val": "1526346992601661480", "emoji": "\ud83c\uddfa\ud83c\uddf8"},
            {"label": "Europa",         "val": "1526346993876729927", "emoji": "\ud83c\uddea\ud83c\uddfa"},
            {"label": "Asia-Pacifico",  "val": "1526346995281952970", "emoji": "\ud83c\uddef\ud83c\uddf5"},
        ]
    },
    {
        "id": "rn",
        "placeholder": "Notificaciones (max 2)",
        "max": 2,
        "options": [
            {"label": "Notifs . Anuncios", "val": "1526346996674334780", "emoji": "\ud83d\udce2"},
            {"label": "Notifs . Eventos",  "val": "1526346998960357467", "emoji": "\ud83d\udcc5"},
        ]
    },
]


class RoleSelect(discord.ui.Select):
    def __init__(self, cat: dict):
        self.cat = cat
        opts = [
            discord.SelectOption(
                label=o["label"],
                value=o["val"],
                emoji=o.get("emoji"),
            )
            for o in cat["options"]
        ]
        super().__init__(
            custom_id=cat["id"],
            placeholder=cat["placeholder"],
            min_values=0,
            max_values=cat["max"],
            options=opts,
        )

    async def callback(self, interaction: discord.Interaction):
        member = interaction.user
        guild = interaction.guild

        chosen = set(self.values)
        all_in_cat = {o["val"] for o in self.cat["options"]}

        to_remove = []
        for rid in all_in_cat:
            role = guild.get_role(int(rid))
            if role and role in member.roles and rid not in chosen:
                to_remove.append(role)

        to_add = []
        for rid in chosen:
            role = guild.get_role(int(rid))
            if role and role not in member.roles:
                to_add.append(role)

        if to_remove:
            await member.remove_roles(*to_remove, reason="Role self-service")
        if to_add:
            await member.add_roles(*to_add, reason="Role self-service")

        names = []
        for rid in chosen:
            if rid in ROLE_LABELS:
                names.append(ROLE_LABELS[rid])

        await interaction.response.send_message(
            f"Roles actualizados: {', '.join(names) if names else 'ninguna seleccion'}",
            ephemeral=True,
        )


ROLE_LABELS = {}
for cat in CATEGORIES:
    for o in cat["options"]:
        ROLE_LABELS[o["val"]] = o["label"]


class RoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        for cat in CATEGORIES:
            self.add_item(RoleSelect(cat))


class Roles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.view = RoleView()

    @commands.command(name="setup_roles")
    @commands.has_permissions(administrator=True)
    async def setup_roles(self, ctx: commands.Context):
        channel = ctx.guild.get_channel(ROLE_CHANNEL_ID)
        if not channel:
            await ctx.send("Canal de roles no encontrado.")
            return

        embed = discord.Embed(
            title="Seleccion de Roles",
            description=(
                "Personaliza tu presencia en el servidor eligiendo los roles que mejor te representen.\n"
                "Puedes modificar tu seleccion en cualquier momento.\n\n"
                "Categorias disponibles:\n"
                "\u2022 **Pronombres** \u2014 1 seleccion\n"
                "\u2022 **Especialidad** \u2014 1 seleccion\n"
                "\u2022 **Region** \u2014 1 seleccion\n"
                "\u2022 **Notificaciones** \u2014 hasta 2 selecciones\n\n"
                "Selecciona una opcion en cada menu desplegable."
            ),
            color=0x2c3e50,
        )
        embed.set_footer(text="ZentroxDev \u00a9 2026")

        await channel.send(embed=embed, view=self.view)
        await ctx.send(f"Mensaje de roles enviado a {channel.mention}.")

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(self.view)


async def setup(bot: commands.Bot):
    cog = Roles(bot)
    await bot.add_cog(cog)
    bot.add_view(cog.view)
