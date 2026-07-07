import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import yt_dlp
import config

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

YDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "extractor_args": {"youtube": {"player_client": ["android"]}},
}

class MusicControls(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=600)
        self.cog = cog
        self.guild_id = guild_id

    @discord.ui.button(label="⏸️", style=discord.ButtonStyle.secondary)
    async def pause_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice = interaction.guild.voice_client
        if voice and voice.is_playing():
            voice.pause()
            await interaction.response.send_message("⏸️ Pausado", ephemeral=True)
        else:
            await interaction.response.send_message("No hay nada reproduciendo", ephemeral=True)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def resume_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice = interaction.guild.voice_client
        if voice and voice.is_paused():
            voice.resume()
            await interaction.response.send_message("▶️ Reanudado", ephemeral=True)
        else:
            await interaction.response.send_message("No hay nada pausado", ephemeral=True)

    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.secondary)
    async def skip_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice = interaction.guild.voice_client
        if voice and voice.is_playing():
            voice.stop()
            await interaction.response.send_message("⏭️ Saltado", ephemeral=True)
        else:
            await interaction.response.send_message("No hay nada reproduciendo", ephemeral=True)

    @discord.ui.button(label="⏹️", style=discord.ButtonStyle.danger)
    async def stop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice = interaction.guild.voice_client
        if voice:
            self.cog.queues[interaction.guild.id] = []
            voice.stop()
            await voice.disconnect()
            await interaction.response.send_message("⏹️ Detenido y desconectado", ephemeral=True)
            self.stop()
        else:
            await interaction.response.send_message("No estoy conectado", ephemeral=True)

    @discord.ui.button(label="📋", style=discord.ButtonStyle.secondary)
    async def queue_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        queue = self.cog.queues.get(interaction.guild.id, [])
        if not queue:
            await interaction.response.send_message("La cola está vacía", ephemeral=True)
            return
        lines = [f"{i+1}. {s.get('title', '...')}" for i, s in enumerate(queue[:10])]
        await interaction.response.send_message("**Cola:**\n" + "\n".join(lines), ephemeral=True)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        self.text_channels = {}
        self.now_playing = {}

    def get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]

    async def play_next(self, guild_id):
        queue = self.get_queue(guild_id)
        if not queue:
            self.now_playing[guild_id] = None
            return
        song = queue.pop(0)
        await self._play_url(guild_id, song)

    async def _play_url(self, guild_id, song):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        voice = guild.voice_client
        if not voice:
            return

        channel = self.text_channels.get(guild_id)
        url = song.get("url") or song
        title = song.get("title", "Desconocido")

        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(YDL_OPTIONS).extract_info(url, download=False))
        except Exception as e:
            if channel:
                await channel.send(f"Error al obtener el audio: {e}")
            return await self.play_next(guild_id)

        audio_url = data["url"]
        source = await discord.FFmpegOpusAudio.from_probe(audio_url, **FFMPEG_OPTIONS)
        self.now_playing[guild_id] = title

        voice.play(source, after=lambda e, gid=guild_id: asyncio.run_coroutine_threadsafe(
            self.play_next(gid), self.bot.loop
        ))

        embed = discord.Embed(title="🎵 Reproduciendo", description=f"**{title}**", color=discord.Color.green())
        if channel:
            view = MusicControls(self, guild_id)
            await channel.send(embed=embed, view=view)

    async def _search_youtube(self, query):
        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL({
                **YDL_OPTIONS, "default_search": "ytsearch", "max_results": 1
            }).extract_info(f"ytsearch:{query}", download=False))
            entries = data.get("entries", [])
            if not entries:
                return None
            video = entries[0]
            return {"url": video["webpage_url"], "title": video["title"]}
        except:
            return None

    async def _get_spotify_tracks(self, url):
        try:
            from spotapi import PublicPlaylist
            pl = PublicPlaylist(url)
            info = pl.get_playlist_info()
            items = info.get('data', {}).get('playlistV2', {}).get('content', {}).get('items', [])
            tracks = []
            for item in items:
                track_data = item.get('itemV2', {}).get('data', {})
                name = track_data.get('name', '')
                artists = ' '.join(
                    a.get('profile', {}).get('name', '')
                    for a in track_data.get('artists', {}).get('items', [])
                )
                if name:
                    tracks.append(f"{name} {artists}".strip())
            return tracks
        except Exception as e:
            print(f"Spotify error: {e}")
            return None

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
            song = {"url": query, "title": query}
            self.get_queue(interaction.guild.id).append(song)
            if not interaction.guild.voice_client.is_playing():
                await self.play_next(interaction.guild.id)
            else:
                await interaction.followup.send(f"Añadido a la cola")
        else:
            result = await self._search_youtube(query)
            if not result:
                await interaction.followup.send("No se encontraron resultados")
                return
            self.get_queue(interaction.guild.id).append(result)
            if not interaction.guild.voice_client.is_playing():
                await self.play_next(interaction.guild.id)
            else:
                await interaction.followup.send(f"Añadido a la cola: **{result['title']}**")

    @app_commands.command(name="spotify", description="Reproducir una playlist de Spotify")
    @app_commands.describe(url="URL de la playlist de Spotify")
    async def spotify(self, interaction: discord.Interaction, url: str):
        if not interaction.user.voice:
            await interaction.response.send_message("Debes estar en un canal de voz", ephemeral=True)
            return

        await interaction.response.defer()

        tracks = await self._get_spotify_tracks(url)
        if tracks is None:
            await interaction.followup.send("Error al obtener la playlist. Verifica la URL e inténtalo de nuevo.")
            return
        if not tracks:
            await interaction.followup.send("La playlist está vacía o no se encontraron canciones")
            return

        channel = interaction.user.voice.channel
        if interaction.guild.voice_client:
            if interaction.guild.voice_client.channel != channel:
                await interaction.guild.voice_client.move_to(channel)
        else:
            await channel.connect()

        self.text_channels[interaction.guild.id] = interaction.channel

        added = 0
        started = False
        for query in tracks[:50]:
            result = await self._search_youtube(query)
            if result:
                self.get_queue(interaction.guild.id).append(result)
                added += 1
                if not started:
                    started = True
                    await interaction.followup.send(f"Obteniendo {len(tracks)} canciones...")
                    await self.play_next(interaction.guild.id)

        if added > 0 and not started:
            await self.play_next(interaction.guild.id)
        if added > 0:
            msg = f"Añadidas **{added}** canciones a la cola"
            if not started:
                msg += "\n(no se pudo iniciar la reproducción)"
            await interaction.followup.send(msg)

    @app_commands.command(name="skip", description="Saltar a la siguiente canción")
    async def skip(self, interaction: discord.Interaction):
        voice = interaction.guild.voice_client
        if voice and voice.is_playing():
            voice.stop()
            await interaction.response.send_message("⏭️ Canción saltada")
        else:
            await interaction.response.send_message("No hay nada reproduciéndose")

    @app_commands.command(name="stop", description="Detener la música y desconectar")
    async def stop(self, interaction: discord.Interaction):
        voice = interaction.guild.voice_client
        if voice:
            self.queues[interaction.guild.id] = []
            self.now_playing[interaction.guild.id] = None
            voice.stop()
            await voice.disconnect()
            await interaction.response.send_message("⏹️ Desconectado y cola limpiada")
        else:
            await interaction.response.send_message("No estoy conectado a un canal de voz")

    @app_commands.command(name="queue", description="Ver la cola de reproducción")
    async def queue(self, interaction: discord.Interaction):
        queue = self.queues.get(interaction.guild.id, [])
        now = self.now_playing.get(interaction.guild.id)
        msg = ""
        if now:
            msg += f"**Reproduciendo ahora:** {now}\n\n"
        if not queue:
            msg += "La cola está vacía"
        else:
            msg += "**Cola:**\n" + "\n".join(f"{i+1}. {s.get('title', '...')}" for i, s in enumerate(queue[:10]))
            if len(queue) > 10:
                msg += f"\n... y {len(queue) - 10} más"
        await interaction.response.send_message(msg)

    @app_commands.command(name="pause", description="Pausar la reproducción")
    async def pause(self, interaction: discord.Interaction):
        voice = interaction.guild.voice_client
        if voice and voice.is_playing():
            voice.pause()
            await interaction.response.send_message("⏸️ Reproducción pausada")
        else:
            await interaction.response.send_message("No hay nada reproduciéndose")

    @app_commands.command(name="resume", description="Reanudar la reproducción")
    async def resume(self, interaction: discord.Interaction):
        voice = interaction.guild.voice_client
        if voice and voice.is_paused():
            voice.resume()
            await interaction.response.send_message("▶️ Reproducción reanudada")
        else:
            await interaction.response.send_message("No hay nada pausado")

async def setup(bot):
    await bot.add_cog(Music(bot))
