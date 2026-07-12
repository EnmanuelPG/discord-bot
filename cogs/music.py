import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import yt_dlp
import config
from ytmusicapi import YTMusic

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn -b:a 192k -ar 48000",
}

YDL_DOWNLOAD = {
    "format": "bestaudio[abr>=64]/bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "extractor_args": {"youtube": {"player_client": ["android"]}},
}

YDL_PLAY = {
    "format": "bestaudio[abr>=64]/bestaudio/best",
    "noplaylist": True,
    "quiet": True,
}

ytmusic = YTMusic()
INACTIVITY_TIMEOUT = 300

COVER_COLOR = discord.Color.from_str("#5865F2")
FOOTER_TEXT = "Made with ❤️"


class QueueSelect(discord.ui.Select):
    def __init__(self, queue):
        self.queue_ref = queue
        options = []
        if not queue:
            options.append(discord.SelectOption(label="No tracks", default=True))
        else:
            for i, s in enumerate(queue[:25]):
                title = s.get("title", "Unknown")[:80]
                options.append(discord.SelectOption(label=f"{i+1}. {title}", value=str(i)))
        super().__init__(placeholder="Queue", options=options, min_values=0, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        if self.values and self.queue_ref:
            idx = int(self.values[0])
            song = self.queue_ref[idx]
            title = song.get("title", "Unknown")
            await interaction.response.send_message(f"**{title}**", ephemeral=True)
        else:
            await interaction.response.send_message("Queue is empty", ephemeral=True)


class FeaturesSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Shuffle", description="Shuffle the queue", emoji="🔀"),
            discord.SelectOption(label="Clear Queue", description="Clear all queued songs", emoji="🗑️"),
        ]
        super().__init__(placeholder="More Features", options=options, min_values=0, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Music")
        if not self.values:
            return
        choice = self.values[0]
        guild_id = interaction.guild.id

        if choice == "Shuffle":
            queue = cog.queues.get(guild_id, [])
            if len(queue) > 1:
                import random
                random.shuffle(queue)
                cog.queues[guild_id] = queue
                await interaction.response.send_message("🔀 Queue shuffled!", ephemeral=True)
            else:
                await interaction.response.send_message("Not enough songs to shuffle", ephemeral=True)
        elif choice == "Clear Queue":
            cog.queues[guild_id] = []
            await interaction.response.send_message("🗑️ Queue cleared!", ephemeral=True)


class NowPlayingView(discord.ui.View):
    def __init__(self, cog, guild_id):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        self.text_channels = {}
        self.now_playing = {}
        self.previous_tracks = {}
        self.now_playing_views = {}
        self.last_activity = {}
        self.inactivity_tasks = {}

    def get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]

    async def build_view(self, guild_id, queue):
        view = NowPlayingView(self, guild_id)

        view.add_item(discord.ui.Button(label="Latest Update", style=discord.ButtonStyle.link,
                       url="https://github.com/EnmanuelPG/discord-bot", row=0))
        view.add_item(discord.ui.Button(label="Support", style=discord.ButtonStyle.link,
                       url="https://github.com/EnmanuelPG/discord-bot/issues", row=0))
        view.add_item(discord.ui.Button(label="Premium", style=discord.ButtonStyle.link,
                       url="https://github.com/EnmanuelPG/discord-bot", row=0))
        view.add_item(discord.ui.Button(label="Send a review", style=discord.ButtonStyle.link,
                       url="https://github.com/EnmanuelPG/discord-bot/issues", row=0))

        prev_btn = discord.ui.Button(emoji="⏮️", style=discord.ButtonStyle.secondary, row=1)
        async def prev_cb(i): await self._prev_callback(i, guild_id)
        prev_btn.callback = prev_cb
        view.add_item(prev_btn)

        pause_btn = discord.ui.Button(emoji="⏸️", style=discord.ButtonStyle.primary, row=1)
        async def pause_cb(i): await self._pause_callback(i, pause_btn)
        pause_btn.callback = pause_cb
        view.add_item(pause_btn)

        skip_btn = discord.ui.Button(emoji="⏭️", style=discord.ButtonStyle.secondary, row=1)
        async def skip_cb(i): await self._skip_callback(i, guild_id)
        skip_btn.callback = skip_cb
        view.add_item(skip_btn)

        like_btn = discord.ui.Button(emoji="❤️", style=discord.ButtonStyle.secondary, row=1)
        async def like_cb(i): await self._like_callback(i, like_btn)
        like_btn.callback = like_cb
        view.add_item(like_btn)

        view.add_item(QueueSelect(queue))
        view.add_item(FeaturesSelect())
        return view

    async def send_now_playing(self, guild_id):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        channel = self.text_channels.get(guild_id)
        if not channel:
            return

        np_data = self.now_playing.get(guild_id)
        queue = self.get_queue(guild_id)

        embed = discord.Embed(color=COVER_COLOR)
        embed.set_footer(text=FOOTER_TEXT)

        if np_data:
            embed.title = "🎵 Now Playing"
            embed.description = f"**[{np_data.get('title', 'Unknown')}]({np_data.get('url', '')})**"
            if np_data.get("channel"):
                embed.add_field(name="Channel", value=np_data["channel"], inline=True)
            if np_data.get("duration"):
                embed.add_field(name="Duration", value=np_data["duration"], inline=True)
            if np_data.get("thumbnail"):
                embed.set_thumbnail(url=np_data["thumbnail"])
        else:
            embed.title = "No music playing"
            embed.description = "Use `/play` to start listening"

        if queue:
            lines = "\n".join(f"`{i+1}.` {s.get('title','?')[:50]}" for i, s in enumerate(queue[:8]))
            embed.add_field(name=f"Queue ({len(queue)} tracks)", value=lines, inline=False)

        view = await self.build_view(guild_id, queue)

        msg = self.now_playing_views.get(guild_id)
        if msg:
            try:
                await msg.edit(embed=embed, view=view)
                return
            except:
                pass

        msg = await channel.send(embed=embed, view=view)
        self.now_playing_views[guild_id] = msg

    async def _prev_callback(self, interaction, guild_id):
        prev = self.previous_tracks.get(guild_id, [])
        if prev:
            song = prev.pop()
            self.queues.setdefault(guild_id, []).insert(0, song)
            vc = interaction.guild.voice_client
            if vc and vc.is_playing():
                vc.stop()
            else:
                await self.play_next(guild_id)
            await interaction.response.send_message("⏮️", ephemeral=True)
        else:
            await interaction.response.send_message("⏮️ No previous track", ephemeral=True)

    async def _pause_callback(self, interaction, btn):
        vc = interaction.guild.voice_client
        if not vc:
            await interaction.response.send_message("Nothing playing", ephemeral=True)
            return
        await interaction.response.defer()
        if vc.is_playing():
            vc.pause()
            btn.emoji = "▶️"
        elif vc.is_paused():
            vc.resume()
            self.last_activity[interaction.guild.id] = asyncio.get_event_loop().time()
            btn.emoji = "⏸️"
        else:
            await interaction.followup.send("Nothing playing", ephemeral=True)
            return
        try:
            await interaction.edit_original_response(view=btn.view)
        except Exception:
            pass

    async def _skip_callback(self, interaction, guild_id):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            np_data = self.now_playing.get(guild_id, {})
            if np_data:
                self.previous_tracks.setdefault(guild_id, []).append(np_data)
            vc.stop()
            await interaction.response.send_message("⏭️", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing playing", ephemeral=True)

    async def _like_callback(self, interaction, btn):
        await interaction.response.defer()
        liked = getattr(btn, "_liked", False)
        btn._liked = not liked
        btn.style = discord.ButtonStyle.danger if btn._liked else discord.ButtonStyle.secondary
        try:
            await interaction.edit_original_response(view=btn.view)
        except Exception:
            pass

    async def play_next(self, guild_id):
        queue = self.get_queue(guild_id)
        if not queue:
            self.now_playing[guild_id] = None
            self.last_activity[guild_id] = asyncio.get_event_loop().time()
            await self.send_now_playing(guild_id)
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
            data = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(YDL_DOWNLOAD).extract_info(url, download=False))
        except Exception as e:
            if channel:
                await channel.send(f"Error: {e}")
            return await self.play_next(guild_id)

        audio_url = data.get("url") or data.get("webpage_url", "")
        actual_title = data.get("title", title)
        channel_name = data.get("channel", "Unknown")
        duration = data.get("duration", 0)
        thumb = data.get("thumbnail", None)

        dur_str = f"{duration // 60}:{duration % 60:02d}" if duration else "?"

        np_data = {
            "title": actual_title,
            "url": url,
            "channel": channel_name,
            "duration": dur_str,
            "thumbnail": thumb,
        }
        self.now_playing[guild_id] = np_data
        self.last_activity[guild_id] = asyncio.get_event_loop().time()

        source = await discord.FFmpegOpusAudio.from_probe(audio_url, **FFMPEG_OPTIONS)
        voice.play(source, after=lambda e, gid=guild_id: asyncio.run_coroutine_threadsafe(
            self.play_next(gid), self.bot.loop
        ))

        await self.send_now_playing(guild_id)

    async def _search_youtube(self, query):
        try:
            results = ytmusic.search(query, filter="songs", limit=1)
            if not results:
                return None
            r = results[0]
            video_id = r.get("videoId")
            if not video_id:
                return None
            url = f"https://www.youtube.com/watch?v={video_id}"
            artists = " & ".join(a["name"] for a in r.get("artists", []))
            return {
                "url": url,
                "title": r.get("title", "Unknown"),
                "channel": artists,
                "duration": r.get("duration", ""),
                "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            }
        except Exception as e:
            print(f"Search error: {e}")
            return None

    async def _get_spotify_tracks(self, url):
        try:
            from spotapi import PublicPlaylist
            pl = PublicPlaylist(url)
            info = pl.get_playlist_info()
            items = info.get("data", {}).get("playlistV2", {}).get("content", {}).get("items", [])
            tracks = []
            for item in items:
                td = item.get("itemV2", {}).get("data", {})
                name = td.get("name", "")
                artists = " ".join(
                    a.get("profile", {}).get("name", "")
                    for a in td.get("artists", {}).get("items", [])
                )
                if name:
                    tracks.append(f"{name} {artists}".strip())
            return tracks
        except Exception as e:
            print(f"Spotify error: {e}")
            return None

    async def _start_inactivity_timer(self, guild_id):
        if guild_id in self.inactivity_tasks:
            self.inactivity_tasks[guild_id].cancel()

        async def timer():
            try:
                while True:
                    await asyncio.sleep(60)
                    last = self.last_activity.get(guild_id, 0)
                    if last and (asyncio.get_event_loop().time() - last) >= INACTIVITY_TIMEOUT:
                        guild = self.bot.get_guild(guild_id)
                        if guild and guild.voice_client:
                            vc = guild.voice_client
                            if not vc.is_playing() and not vc.is_paused():
                                self.queues[guild_id] = []
                                await vc.disconnect()
                                if guild_id in self.now_playing_views:
                                    try:
                                        await self.now_playing_views[guild_id].delete()
                                    except:
                                        pass
                                    del self.now_playing_views[guild_id]
                        break
            except asyncio.CancelledError:
                pass

        self.inactivity_tasks[guild_id] = asyncio.create_task(timer())

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        guild = member.guild
        if not guild.voice_client:
            return
        if guild.voice_client.channel is None:
            return

        bot_channel = guild.voice_client.channel
        members = [m for m in bot_channel.members if not m.bot]

        if len(members) == 0:
            self.queues[guild.id] = []
            self.now_playing[guild.id] = None
            await guild.voice_client.disconnect()
            if guild.id in self.now_playing_views:
                try:
                    await self.now_playing_views[guild.id].delete()
                except:
                    pass
                del self.now_playing_views[guild.id]

    @app_commands.command(name="play", description="Reproducir una canción desde YouTube")
    @app_commands.describe(query="Nombre de la canción o URL de YouTube")
    async def play(self, interaction: discord.Interaction, query: str):
        if not interaction.user.voice:
            await interaction.response.send_message("Debes estar en un canal de voz", ephemeral=True)
            return

        await interaction.response.defer()
        channel = interaction.user.voice.channel
        if interaction.guild.voice_client:
            if interaction.guild.voice_client.channel != channel:
                await interaction.guild.voice_client.move_to(channel)
        else:
            await channel.connect()

        self.text_channels[interaction.guild.id] = interaction.channel

        is_url = query.startswith("http://") or query.startswith("https://")

        if is_url:
            song = {"url": query, "title": query}
            self.get_queue(interaction.guild.id).append(song)
            if not interaction.guild.voice_client.is_playing():
                await self.play_next(interaction.guild.id)
            else:
                await interaction.followup.send("Added to queue")
        else:
            result = await self._search_youtube(query)
            if not result:
                await interaction.followup.send("No se encontraron resultados")
                return
            self.get_queue(interaction.guild.id).append(result)
            if not interaction.guild.voice_client.is_playing():
                await self.play_next(interaction.guild.id)
            else:
                await interaction.followup.send(f"Added: **{result['title']}**")

    @app_commands.command(name="spotify", description="Reproducir una playlist de Spotify")
    @app_commands.describe(url="URL de la playlist de Spotify")
    async def spotify(self, interaction: discord.Interaction, url: str):
        if not interaction.user.voice:
            await interaction.response.send_message("Debes estar en un canal de voz", ephemeral=True)
            return

        await interaction.response.defer()

        tracks = await self._get_spotify_tracks(url)
        if tracks is None:
            await interaction.followup.send("Error al obtener la playlist")
            return
        if not tracks:
            await interaction.followup.send("La playlist está vacía")
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
            np_data = self.now_playing.get(interaction.guild.id, {})
            if np_data:
                self.previous_tracks.setdefault(interaction.guild.id, []).append(np_data)
            voice.stop()
            await interaction.response.send_message("⏭️ Skipped")
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
            if interaction.guild.id in self.now_playing_views:
                try:
                    await self.now_playing_views[interaction.guild.id].delete()
                except:
                    pass
                del self.now_playing_views[interaction.guild.id]
            await interaction.response.send_message("⏹️ Desconectado y cola limpiada")
        else:
            await interaction.response.send_message("No estoy conectado a un canal de voz")

    @app_commands.command(name="queue", description="Ver la cola de reproducción")
    async def queue(self, interaction: discord.Interaction):
        queue = self.queues.get(interaction.guild.id, [])
        now = self.now_playing.get(interaction.guild.id)
        msg = ""
        if now:
            msg += f"**Reproduciendo ahora:** {now.get('title', '?')}\n\n"
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
            await interaction.response.send_message("⏸️ Pausado")
        else:
            await interaction.response.send_message("No hay nada reproduciéndose")

    @app_commands.command(name="resume", description="Reanudar la reproducción")
    async def resume(self, interaction: discord.Interaction):
        voice = interaction.guild.voice_client
        if voice and voice.is_paused():
            voice.resume()
            self.last_activity[interaction.guild.id] = asyncio.get_event_loop().time()
            await interaction.response.send_message("▶️ Reanudado")
        else:
            await interaction.response.send_message("No hay nada pausado")


async def setup(bot):
    await bot.add_cog(Music(bot))
