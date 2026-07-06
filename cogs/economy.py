import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
BALANCES_FILE = os.path.join(DATA_DIR, "balances.json")
SHOP_FILE = os.path.join(DATA_DIR, "shop.json")
INVENTORY_FILE = os.path.join(DATA_DIR, "inventory.json")

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_balance(user_id):
    data = load_json(BALANCES_FILE)
    return data.get(str(user_id), 0)

def set_balance(user_id, amount):
    data = load_json(BALANCES_FILE)
    data[str(user_id)] = amount
    save_json(BALANCES_FILE, data)

def add_balance(user_id, amount):
    current = get_balance(user_id)
    set_balance(user_id, current + amount)
    return current + amount

class Economy(commands.Cog):
    group = app_commands.Group(name="economy", description="Comandos de economía")

    def __init__(self, bot):
        self.bot = bot
        os.makedirs(DATA_DIR, exist_ok=True)

    @group.command(name="balance", description="Ver tus monedas o las de otro usuario")
    @app_commands.describe(miembro="Usuario a consultar (opcional)")
    async def balance(self, interaction: discord.Interaction, miembro: discord.Member = None):
        target = miembro or interaction.user
        bal = get_balance(target.id)
        await interaction.response.send_message(f"{target.display_name} tiene **{bal}** monedas")

    @group.command(name="daily", description="Reclama tu recompensa diaria")
    async def daily(self, interaction: discord.Interaction):
        amount = random.randint(50, 150)
        new_bal = add_balance(interaction.user.id, amount)
        await interaction.response.send_message(f"Recibiste **{amount}** monedas! Total: **{new_bal}**")

    @group.command(name="transfer", description="Transfiere monedas a otro usuario")
    @app_commands.describe(miembro="Usuario destinatario", cantidad="Cantidad de monedas")
    async def transfer(self, interaction: discord.Interaction, miembro: discord.Member, cantidad: int):
        if cantidad <= 0:
            await interaction.response.send_message("La cantidad debe ser positiva", ephemeral=True)
            return
        sender_bal = get_balance(interaction.user.id)
        if sender_bal < cantidad:
            await interaction.response.send_message("No tienes suficientes monedas", ephemeral=True)
            return
        add_balance(interaction.user.id, -cantidad)
        add_balance(miembro.id, cantidad)
        await interaction.response.send_message(f"Transferiste **{cantidad}** monedas a {miembro.display_name}")

    @group.command(name="shop", description="Ver la tienda")
    async def shop(self, interaction: discord.Interaction):
        items = load_json(SHOP_FILE)
        if not items:
            await interaction.response.send_message("La tienda está vacía")
            return
        embed = discord.Embed(title="Tienda", color=discord.Color.blue())
        for item_id, item in items.items():
            embed.add_field(name=f"{item['name']} ({item_id})", value=f"Precio: {item['price']} monedas", inline=False)
        await interaction.response.send_message(embed=embed)

    @group.command(name="buy", description="Comprar un artículo de la tienda")
    @app_commands.describe(articulo="ID del artículo a comprar")
    async def buy(self, interaction: discord.Interaction, articulo: str):
        items = load_json(SHOP_FILE)
        item = items.get(articulo)
        if not item:
            await interaction.response.send_message("Ese artículo no existe", ephemeral=True)
            return
        if get_balance(interaction.user.id) < item["price"]:
            await interaction.response.send_message("No tienes suficientes monedas", ephemeral=True)
            return
        add_balance(interaction.user.id, -item["price"])
        inv = load_json(INVENTORY_FILE)
        user_inv = inv.get(str(interaction.user.id), [])
        user_inv.append(articulo)
        inv[str(interaction.user.id)] = user_inv
        save_json(INVENTORY_FILE, inv)
        await interaction.response.send_message(f"Compraste **{item['name']}** por {item['price']} monedas!")

    @group.command(name="inventory", description="Ver tu inventario")
    async def inventory(self, interaction: discord.Interaction):
        inv = load_json(INVENTORY_FILE)
        items = load_json(SHOP_FILE)
        user_inv = inv.get(str(interaction.user.id), [])
        if not user_inv:
            await interaction.response.send_message("No tienes artículos en tu inventario")
            return
        names = [items.get(i, {}).get("name", i) for i in user_inv]
        await interaction.response.send_message(f"Inventario: {', '.join(names)}")

    @group.command(name="gamble", description="Apostar monedas al 50%")
    @app_commands.describe(cantidad="Cantidad a apostar")
    async def gamble(self, interaction: discord.Interaction, cantidad: int):
        if cantidad <= 0:
            await interaction.response.send_message("Cantidad inválida", ephemeral=True)
            return
        if get_balance(interaction.user.id) < cantidad:
            await interaction.response.send_message("No tienes suficientes monedas", ephemeral=True)
            return
        result = random.randint(1, 100)
        if result <= 45:
            add_balance(interaction.user.id, -cantidad)
            await interaction.response.send_message(f"Perdiste **{cantidad}** monedas :(")
        elif result <= 90:
            add_balance(interaction.user.id, cantidad)
            await interaction.response.send_message(f"Ganaste **{cantidad}** monedas!")
        else:
            add_balance(interaction.user.id, cantidad * 2)
            await interaction.response.send_message(f"JACKPOT! Ganaste **{cantidad * 2}** monedas!")

    @group.command(name="leaderboard", description="Top 10 usuarios con más monedas")
    async def leaderboard(self, interaction: discord.Interaction):
        data = load_json(BALANCES_FILE)
        sorted_users = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
        if not sorted_users:
            await interaction.response.send_message("No hay datos en el leaderboard")
            return
        embed = discord.Embed(title="Top 10 - Leaderboard", color=discord.Color.gold())
        for i, (uid, bal) in enumerate(sorted_users, 1):
            user = self.bot.get_user(int(uid))
            name = user.display_name if user else f"Usuario {uid}"
            embed.add_field(name=f"{i}. {name}", value=f"{bal} monedas", inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Economy(bot))
