import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import yt_dlp

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

YDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
}

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        self.text_channels = {}

    def get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]

    async def play_next(self, guild_id):
        queue = self.get_queue(guild_id)
        if not queue:
            return
        url = queue.pop(0)
        await self._play_url(guild_id, url)

    async def _play_url(self, guild_id, url):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        voice = guild.voice_client
        if not voice:
            return

        channel = self.text_channels.get(guild_id)

        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(YDL_OPTIONS).extract_info(url, download=False))
        except Exception as e:
            if channel:
                await channel.send(f"Error al obtener el audio: {e}")
            return

        audio_url = data["url"]
        title = data.get("title", "Desconocido")

        source = await discord.FFmpegOpusAudio.from_probe(audio_url, **FFMPEG_OPTIONS)
        voice.play(source, after=lambda e, gid=guild_id: asyncio.run_coroutine_threadsafe(
            self.play_next(gid), self.bot.loop
        ))
        if channel:
            await channel.send(f"Reproduciendo: **{title}**")

    @app_commands.command(name="play", description="Reproducir una canción desde YouTube")
    @app_commands.describe(query="Nombre de la canción o URL de YouTube")
    async def play(self, interaction: discord.Interaction, query: str):
        if not interaction.user.voice:
            await interaction.response.send_message("Debes estar en un canal de voz", ephemeral=True)
            return

        channel = interaction.user.voice.channel
        if interaction.guild.voice_client:
            if interaction.guild.voice_client.channel != channel:
                await interaction.guild.voice_client.move_to(channel)
        else:
            await channel.connect()

        self.text_channels[interaction.guild.id] = interaction.channel
        await interaction.response.defer()

        is_url = query.startswith("http://") or query.startswith("https://")

        if is_url:
            self.get_queue(interaction.guild.id).append(query)
            if not interaction.guild.voice_client.is_playing():
                await self.play_next(interaction.guild.id)
            else:
                await interaction.followup.send("Añadido a la cola")
        else:
            loop = asyncio.get_event_loop()
            try:
                data = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL({
                    **YDL_OPTIONS, "default_search": "ytsearch", "max_results": 1
                }).extract_info(f"ytsearch:{query}", download=False))
            except Exception as e:
                await interaction.followup.send(f"Error al buscar: {e}")
                return

            entries = data.get("entries", [])
            if not entries:
                await interaction.followup.send("No se encontraron resultados")
                return
            video = entries[0]
            url = video["webpage_url"]
            self.get_queue(interaction.guild.id).append(url)
            if not interaction.guild.voice_client.is_playing():
                await self.play_next(interaction.guild.id)
            else:
                await interaction.followup.send(f"Añadido a la cola: **{video['title']}**")

    @app_commands.command(name="skip", description="Saltar a la siguiente canción")
    async def skip(self, interaction: discord.Interaction):
        voice = interaction.guild.voice_client
        if voice and voice.is_playing():
            voice.stop()
            await interaction.response.send_message("Canción saltada")
        else:
            await interaction.response.send_message("No hay nada reproduciéndose")

    @app_commands.command(name="stop", description="Detener la música y desconectar el bot")
    async def stop(self, interaction: discord.Interaction):
        voice = interaction.guild.voice_client
        if voice:
            self.queues[interaction.guild.id] = []
            voice.stop()
            await voice.disconnect()
            await interaction.response.send_message("Desconectado y cola limpiada")
        else:
            await interaction.response.send_message("No estoy conectado a un canal de voz")

    @app_commands.command(name="queue", description="Ver la cola de reproducción")
    async def queue(self, interaction: discord.Interaction):
        queue = self.get_queue(interaction.guild.id)
        if not queue:
            await interaction.response.send_message("La cola está vacía")
            return
        await interaction.response.send_message(f"Cola ({len(queue)} canciones):\n" + "\n".join(queue[:10]))

    @app_commands.command(name="pause", description="Pausar la reproducción")
    async def pause(self, interaction: discord.Interaction):
        voice = interaction.guild.voice_client
        if voice and voice.is_playing():
            voice.pause()
            await interaction.response.send_message("Reproducción pausada")
        else:
            await interaction.response.send_message("No hay nada reproduciéndose")

    @app_commands.command(name="resume", description="Reanudar la reproducción")
    async def resume(self, interaction: discord.Interaction):
        voice = interaction.guild.voice_client
        if voice and voice.is_paused():
            voice.resume()
            await interaction.response.send_message("Reproducción reanudada")
        else:
            await interaction.response.send_message("No hay nada pausado")

async def setup(bot):
    await bot.add_cog(Music(bot))
