import discord
from discord.ext import commands

import asyncio
import youtube_dl

#Web Scrap
import requests
from bs4 import BeautifulSoup

#See if a link is a URL
import validators

#mat
from math import ceil
import random

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = []
        self.loop = False

    @commands.command()
    async def join(self, ctx, *, channel: discord.VoiceChannel):
        """Joins a voice channel"""

        if ctx.voice_client is not None:
            return await ctx.voice_client.move_to(channel)

        await channel.connect()      

    
    @commands.command(pass_context=True, aliases=['Skip'])
    async def skip(ctx):
        '''Skip the current track
        If loop is enabled, song is appended to end
        Otherwise, song is deleted from playlist'''
        global player
        global track
        global qloop
        track.stop()
        if qloop:
            last_played = player[0]
            del player[0]
            player.append(last_played)
        else:
            del player[0]
        server = ctx.message.server
        voice_client = client.voice_client_in(server)
        while len(player) > 0:
            track = await voice_client.create_ytdl_player(player[0][1])
            track.start()
            time = track.duration + 3
            await asyncio.sleep(time)
            if qloop:
                last_played = player[0]
                del player[0]
                player.append(last_played)
            else:
                del player[0]
    

    @commands.command(pass_context=True)
    async def pause(ctx):
        '''Turtle pause the current song'''
        """
        try:
            global track
            track.pause()
            await client.say(":white_check_mark: Pause!")
        except:
            await client.say(":x: Turtle isn't singing!")
        """


    #Resume music
    @commands.command(pass_context=True)
    async def resume(self, ctx):
        '''Turtle resume the current song'''
        """
        try:
            global track
            track.resume()
            await client.say(":white_check_mark: Música retomada!")
        except:
            await client.say(":x: Turtle hasn't started singing yet!")
        """

    #Add songs to queue
    @commands.command(pass_context=True, aliases=['a'])
    async def add(self, ctx, a, b="", c="", d="", e="", f="", g=""):
        '''Add a song to queue
        !add [YOUTUBE_URL] to play [YOUTUBE_URL] music
        !add [SONG_NAME] to play [SONG_NAME] music
        '''
        content = a + " " + b + " " + c + " " + d + " " + e + " " + f + " " + g
        content = content.split()
        try:
            pseudo_url = content[0]
            if validators.url(pseudo_url) and ("youtube" in pseudo_url) and ("radio" in pseudo_url):
                await ctx.send(":x: I can't play Youtube Radio playlists!")

            elif validators.url(pseudo_url) and ("youtube" in pseudo_url) and ("list" in pseudo_url):
                url = content[0]
                playlist_start = url.find('list=')
                url = url[playlist_start:]
                playlist_end = url.find('&')
                if playlist_end == -1:
                    url = url
                else:
                    url = url[:playlist_end]
                youtube = 'https://www.youtube.com'
                url = "https://www.youtube.com/playlist?" + url

                await ctx.send(":white_check_mark: Playlist sucessful added!")
                result = ytdl.extract_info(url, download=False)
                if 'entries' in result:
                    # Can be a playlist or a list of videos
                    video = result['entries']

                    #loops entries to grab each video_url
                    for i, item in enumerate(video):
                        self.queue.append(result['entries'][i]['webpage_url'])

                print(self.queue)
            elif validators.url(pseudo_url) and ("youtube" in pseudo_url) and ("watch" in pseudo_url):
                url = content[0]         
                url_content = requests.get(url)
                url_data = BeautifulSoup(url_content.content, "html.parser")
                self.queue += [url,]
                await ctx.send(":white_check_mark: **{}** adicionou a música **{}**!".format("Turtle", url_data.title.string[:-10]))
            elif validators.url(pseudo_url):
                await ctx.send(":x: This is not a music video!")
            else:
                video = ytdl.extract_info(f"ytsearch:{content}", download=False)['entries'][0]
                self.queue.append(video['url'])

                await ctx.send(":white_check_mark: {} added the song **{}**!".format("Turtle", video['title']))                                
        except:
            await ctx.send(":x: Ocorreu um erro inesperado durante o uso do comando **add** :turtle:")


    #Show the queue
    @commands.command(pass_context=True, aliases=['q'])
    async def queue(self, ctx, page=1):
        '''Show the current songs in queue.
        !queue [page]'''
        string = '```Playing Right Now: {}\n\n'.format(self.queue[0])
        start_in = 1 + 15*(page-1)
        go_to = 16 + 15*(page-1)
        if page > ceil(len(player)/15):
            await client.say("Not too many songs in the queue! Wait! You can add more, and then you can acess page {}".format(page))
        else:
            while start_in < go_to and start_in < len(self.queue):
                if start_in < 10:
                    number = str(start_in)+ ' '
                else:
                    number = start_in
                string += '{} ->\t{} \n'.format(number, self.queue[start_in])
                start_in += 1
            string += '\nPage {}\{}```'.format(page, (ceil(len(self.queue)/15)))
            await ctx.send(string)


    #Enable and disable the queue loop
    @commands.command(pass_context=True, aliases=['qloop'])
    async def loop(self, ctx):
        '''Enable/Disable Queue Loop
        '''
        self.loop = not self.loop
        if self.loop:
            await ctx.send(":white_check_mark: Loop ativado!")
        else:
            await ctx.send(":x: Loop desativado!")


    @commands.command(pass_context=True, aliases=['clean','cleanq'])
    async def clear(self, ctx):
        '''Clean Queue
        '''
        self.queue = []
        await ctx.send(":white_check_mark: Bye, songs! :cry:")


    @commands.command()
    async def play(self, ctx, url):
        """Plays from a url (almost anything youtube_dl supports)"""

        if not self.queue:
            self.queue.append(url)
            print('init queue\n')
            print(self.queue)

            while self.queue:
                async with ctx.typing():
                    player = await YTDLSource.from_url(self.queue[0], loop=self.bot.loop)
                    ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)
                
                embedVar = discord.Embed(title="Start Playing", description='Now playing: {}'.format(player.title), color=0x0099ff)
                await ctx.send(embed=embedVar)

                print(player.duration)

                duration = player.duration + 3
                await asyncio.sleep(duration)

                if self.loop:
                    last_played = self.queue[0]
                    del self.queue[0]
                    player.append(last_played)
                else:
                    del self.queue[0]
        else:
            self.queue.append(url)

            embedVar = discord.Embed(title="Add to Queue", description='Add to Queue: {}'.format(url), color=0x0099ff)
            await ctx.send(embed=embedVar)

    @commands.command()
    async def stream(self, ctx, *, url):
        """Streams from a url (same as yt, but doesn't predownload)"""

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print('Player error: %s' % e) if e else None)

        await ctx.send('Now playing: {}'.format(player.title))


    @commands.command()
    async def volume(self, ctx, volume: int):
        """Changes the player's volume"""

        if ctx.voice_client is None:
            return await ctx.send("Not connected to a voice channel.")

        ctx.voice_client.source.volume = volume / 100
        await ctx.send("Changed volume to {}%".format(volume))

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects the bot from voice"""

        await ctx.voice_client.disconnect()

    @play.before_invoke
    @stream.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError("Author not connected to a voice channel.")