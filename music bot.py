from youtube_search import YoutubeSearch
from discord.ui import Button, View
from discord import app_commands
from collections import deque
import colorama
import discord
import yt_dlp

# ------------------------------

TOKEN: str = ""

# ------------------------------

Red_Text    = colorama.Fore.RED
Green_Text  = colorama.Fore.GREEN
Reset_Color = colorama.Fore.RESET

class MusicPlayer:
    def __init__(self):
        self.queue = deque()
        self.current_song = None
        
    async def add_to_queue(self, song_info):
        self.queue.append(song_info)
    
    def get_queue(self):
        return list(self.queue)
    
    def skip_song(self):
        if self.queue:
            return self.queue.popleft()
        return None

async def create_basic_embed(title, description, color=discord.Color.blurple()):
    return discord.Embed(
        title=title,
        description=description,
        color=color
    )

class PlaybackButtons(View):
    def __init__(self, voice_client, music_player):
        super().__init__(timeout=None)
        self.voice_client = voice_client
        self.music_player = music_player

    @discord.ui.button(label="⏭️ Next", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.voice_client.is_playing():
            self.voice_client.stop()
        embed = await create_basic_embed("Skip", "Skipping to next song...")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="⏸️ Pause", style=discord.ButtonStyle.secondary)
    async def pause_button(self, interaction: discord.Interaction, button: Button):
        if self.voice_client.is_playing() and not self.voice_client.is_paused():
            self.voice_client.pause()
            embed = await create_basic_embed("Pause", "Paused playback")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = await create_basic_embed("Error", "Nothing is playing or already paused!", discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="▶️ Resume", style=discord.ButtonStyle.success)
    async def resume_button(self, interaction: discord.Interaction, button: Button):
        if self.voice_client.is_paused():
            self.voice_client.resume()
            embed = await create_basic_embed("Resume", "Resumed playback")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = await create_basic_embed("Error", "Nothing is paused!", discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.danger)
    async def stop_button(self, interaction: discord.Interaction, button: Button):
        if self.voice_client.is_playing() or self.voice_client.is_paused():
            self.voice_client.stop()
            self.music_player.queue.clear()
            embed = await create_basic_embed("Stop", "Stopped playback and cleared queue")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            embed = await create_basic_embed("Error", "Nothing is playing!", discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)

class ClearQueueButton(View):
    def __init__(self, music_player):
        super().__init__(timeout=None)
        self.music_player = music_player

    @discord.ui.button(label="🗑️ Clear Queue", style=discord.ButtonStyle.danger)
    async def clear_button(self, interaction: discord.Interaction, button: Button):
        self.music_player.queue.clear()
        cleared_embed = await create_basic_embed("Queue Cleared", "Queue has been cleared!")
        await interaction.response.send_message(embed=cleared_embed, ephemeral=True)
        empty_embed = await create_basic_embed(
            title="Queue Empty",
            description="No songs in queue",
            color=discord.Color.blurple()
        )
        await interaction.message.edit(embed=empty_embed)

class aclient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.synced = False
        self.music_player = MusicPlayer()

    async def on_ready(self):
        await self.wait_until_ready()
        if not self.synced:
            await tree.sync() 
            self.synced = True
        print(f"{Green_Text}| --> Logged in as {Reset_Color}{self.user}.")

client = aclient()
tree = app_commands.CommandTree(client)

@tree.command(name="queue", description="Show queue or add song to queue")
async def queue(interaction: discord.Interaction, query: str = None):
    if not query:
        
        queue_list = client.music_player.get_queue()
        embed = discord.Embed(
            title="🎵 Current Queue",
            color=discord.Color.blurple()
        )
        
        if not queue_list:
            embed.description = "Queue is empty"
        else:
            queue_text = ""
            for i, song in enumerate(queue_list, 1):
                queue_text += f"`{i}.` **{song['title']}**\n"
            embed.description = queue_text
            
        embed.set_footer(text=f"Total songs in queue: {len(queue_list)}")
        view = ClearQueueButton(client.music_player)
        await interaction.response.send_message(embed=embed, view=view)
        return

    
    results = YoutubeSearch(query, max_results=1).to_dict()
    if not results:
        error_embed = discord.Embed(
            title="Error",
            description="No results found!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=error_embed)
        return
    
    song_info = {
        'title': results[0]['title'],
        'url': f"https://youtube.com{results[0]['url_suffix']}"
    }
    
    await client.music_player.add_to_queue(song_info)
    
    added_embed = discord.Embed(
        title="Added to Queue",
        description=f"🎵 **{song_info['title']}**",
        color=discord.Color.blurple()
    )
    await interaction.response.send_message(embed=added_embed)

async def create_song_embed(song_title, thumbnail_url=None, status="Now Playing"):
    embed = discord.Embed(
        title=status,
        description=f"🎵 **{song_title}**",
        color=discord.Color.blurple()
    )
    if thumbnail_url:
        embed.set_thumbnail(url=thumbnail_url)
    embed.set_footer(text="Music Player")
    return embed

@tree.command(name="play", description="Play a song from YouTube")
async def play(interaction: discord.Interaction, query: str = None):
    if not interaction.user.voice:
        embed = await create_basic_embed("Error", "You need to be in a voice channel!", discord.Color.red())
        await interaction.response.send_message(embed=embed)
        return

    if not query:
        embed = await create_basic_embed("Error", "Please provide a song to play!", discord.Color.red())
        await interaction.response.send_message(embed=embed)
        return
    
    await interaction.response.defer()  

    voice_channel = interaction.user.voice.channel
    voice_client = interaction.guild.voice_client

    if voice_client is None:
        voice_client = await voice_channel.connect()
    elif voice_client.channel != voice_channel:
        await voice_client.move_to(voice_channel)

    if query:
        results = YoutubeSearch(query, max_results=1).to_dict()
        if results:
            song_info = {
                'title': results[0]['title'],
                'url': f"https://youtube.com{results[0]['url_suffix']}"
            }
            
            
            if voice_client.is_playing():
                voice_client.stop()
                
            
            client.music_player.queue.clear()
            await client.music_player.add_to_queue(song_info)

    async def play_next(voice_client):
        if client.music_player.queue:
            song = client.music_player.skip_song()
            ydl_opts = {
                'format': 'bestaudio',
                'quiet': True,
                'no_warnings': True,
                'default_search': 'auto',
                'noplaylist': True,
                'extract_flat': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            }
            
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(song['url'], download=False)
                    url2 = info['url']
                    thumbnail_url = info.get('thumbnail', None)
                    
                    voice_client.play(
                        discord.FFmpegPCMAudio(
                            url2,
                            executable="ffmpeg.exe",
                            before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                            options='-vn'
                        ),
                        after=lambda e: client.loop.create_task(play_next(voice_client))
                    )
                    
                    embed = await create_song_embed(song['title'], thumbnail_url)
                    view = PlaybackButtons(voice_client, client.music_player)
                    await interaction.followup.send(embed=embed, view=view)
                    
            except Exception as e:
                print(f"Error playing song: {e}")
                error_embed = await create_basic_embed("Error", "Error playing the song!", discord.Color.red())
                await interaction.followup.send(embed=error_embed)
                client.loop.create_task(play_next(voice_client))

    if not query:
        await interaction.followup.send("Please provide a song to play!")
        return

    await play_next(voice_client)

@tree.command(name="help", description="Shows all available commands")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎵 Music Bot Commands",
        description="Here are all the available commands:",
        color=discord.Color.blue()
    )
    
    commands = [
        {
            "name": "/play",
            "description": "Play a song from YouTube",
            "usage": "/play <song name or URL>"
        },
        {
            "name": "/queue",
            "description": "View the current queue or add a song",
            "usage": "/queue [song name]"
        },
        {
            "name": "/help",
            "description": "Shows this help message",
            "usage": "/help"
        },
        {
            "name": "/disconnect",
            "description": "Disconnect the bot from the voice channel",
            "usage": "/disconnect"
        }
    ]
    
    for cmd in commands:
        embed.add_field(
            name=cmd["name"],
            value=f"Description: {cmd['description']}\nUsage: `{cmd['usage']}`",
            inline=False
        )
    
    embed.set_footer(text="[] = optional parameter, <> = required parameter")
    await interaction.response.send_message(embed=embed)

@tree.command(name="disconnect", description="Disconnect the bot from the voice channel")
async def disconnect(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client:
        await voice_client.disconnect()
        embed = await create_basic_embed("Disconnected", "Disconnected from voice channel")
        await interaction.response.send_message(embed=embed)
    else:
        embed = await create_basic_embed("Error", "Not connected to a voice channel!", discord.Color.red())
        await interaction.response.send_message(embed=embed)

client.run(TOKEN)
