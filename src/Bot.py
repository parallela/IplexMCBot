import asyncio
import discord
import urllib.request,json
from discord.ext import commands

if not discord.opus.is_loaded():
    discord.opus.load_opus('opus')

class VoiceEntry:
    def __init__(self, message, player):
        self.requester = message.author
        self.channel = message.channel
        self.player = player

    def __str__(self):
        fmt = '*{0.title}* kacheno ot {0.uploader} pusnato ot {1.display_name}'
        duration = self.player.duration
        if duration:
            fmt = fmt + ' [length: {0[0]}m {0[1]}s]'.format(divmod(duration, 60))
        return fmt.format(self.player, self.requester)

class VoiceState:
    def __init__(self, bot):
        self.current = None
        self.voice = None
        self.bot = bot
        self.play_next_song = asyncio.Event()
        self.songs = asyncio.Queue()
        self.skip_votes = set()
        self.audio_player = self.bot.loop.create_task(self.audio_player_task())

    def is_playing(self):
        if self.voice is None or self.current is None:
            return False

        player = self.current.player
        return not player.is_done()

    @property
    def player(self):
        return self.current.player

    def skip(self):
        self.skip_votes.clear()
        if self.is_playing():
            self.player.stop()

    def toggle_next(self):
        self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

    async def audio_player_task(self):
        while True:
            self.play_next_song.clear()
            self.current = await self.songs.get()
            await self.bot.send_message(self.current.channel, 'Sega vurvi ' + str(self.current))
            self.current.player.start()
            await self.play_next_song.wait()
        

class IplexMC:
    def __init__ (self, bot):
        self.bot = bot

    @commands.command(pass_context=True)
    async def vlez(self,ctx):
        embed = discord.Embed(title="Как да вляза?",description="--------------------",color=0x00ff00)
        embed.add_field(name="IP Адрес",value="play.iplexmc.eu")
        embed.add_field(name="Версия",value="1.9-1.12.2")
        embed.add_field(name="Магазин",value="www.iplexmc.eu")
        await self.bot.say(embed=embed)


    @commands.command(pass_context=True)
    async def checkserver(self,ctx):
        req = urllib.request.urlopen("http://lstankov.me/iplex")
    
        data = json.loads(req.read())

        if data['status'] == "online":
            embed = discord.Embed(title="play.iplexmc.eu",description="--------------------",color=0x00ff00)
            embed.add_field(name="Статус",value="Онлайн")
            embed.add_field(name="Играчи",value=data['players'])
            embed.add_field(name="Платформа",value=data['platform'])
            await self.bot.say(embed=embed)
        else:
            embed = discord.Embed(title="play.iplexmc.eu",description="--------------------",color=0xff0000)
            embed.add_field(name="Статус",value="Офлайн")
            await self.bot.say(embed=embed)


class Muzika:
    def __init__(self, bot):
        self.bot = bot
        self.voice_states = {}

    def get_voice_state(self, server):
        state = self.voice_states.get(server.id)
        if state is None:
            state = VoiceState(self.bot)
            self.voice_states[server.id] = state

        return state

    async def create_voice_client(self, channel):
        voice = await self.bot.join_voice_channel(channel)
        state = self.get_voice_state(channel.server)
        state.voice = voice

    def __unload(self):
        for state in self.voice_states.values():
            try:
                state.audio_player.cancel()
                if state.voice:
                    self.bot.loop.create_task(state.voice.disconnect())
            except:
                pass

    @commands.command(pass_context=True, no_pm=True)
    async def join(self, ctx, *, channel : discord.Channel):
        try:
            await self.create_voice_client(channel)
        except discord.ClientException:
            await self.bot.say('Veche sum v kanal...')
        except discord.InvalidArgument:
            await self.bot.say('Tova ne e voice channel...')
        else:
            await self.bot.say('Puskame muzika v ' + channel.name)

    @commands.command(pass_context=True, no_pm=True)
    async def summon(self, ctx):
        summoned_channel = ctx.message.author.voice_channel
        if summoned_channel is None:
            await self.bot.say('Ne si v voice channel.')
            return False

        state = self.get_voice_state(ctx.message.server)
        if state.voice is None:
            state.voice = await self.bot.join_voice_channel(summoned_channel)
        else:
            await state.voice.move_to(summoned_channel)

        return True

    @commands.command(pass_context=True, no_pm=True)
    async def play(self, ctx, *, song : str):
        state = self.get_voice_state(ctx.message.server)
        opts = {
            'default_search': 'auto',
            'quiet': True,
        }

        if state.voice is None:
            success = await ctx.invoke(self.summon)
            if not success:
                return

        try:
            player = await state.voice.create_ytdl_player(song, ytdl_options=opts, after=state.toggle_next)
        except Exception as e:
            fmt = 'Vuznikna greshka: ```py\n{}: {}\n```'
            await self.bot.send_message(ctx.message.channel, fmt.format(type(e).__name__, e))
        else:
            player.volume = 0.6
            entry = VoiceEntry(ctx.message, player)
            await self.bot.say('Puskam ' + str(entry))
            await state.songs.put(entry)

    @commands.command(pass_context=True, no_pm=True)
    async def volume(self, ctx, value : int):
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.volume = value / 100
            await self.bot.say('Naglasi silata na {:.0%}'.format(player.volume))

    @commands.command(pass_context=True, no_pm=True)
    async def pause(self, ctx):
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.pause()

    @commands.command(pass_context=True, no_pm=True)
    async def resume(self, ctx):
        state = self.get_voice_state(ctx.message.server)
        if state.is_playing():
            player = state.player
            player.resume()

    @commands.command(pass_context=True, no_pm=True)
    async def stop(self, ctx):
        server = ctx.message.server
        state = self.get_voice_state(server)

        if state.is_playing():
            player = state.player
            player.stop()

        try:
            state.audio_player.cancel()
            del self.voice_states[server.id]
            await state.voice.disconnect()
        except:
            pass

    @commands.command(pass_context=True, no_pm=True)
    async def skip(self, ctx):

        state = self.get_voice_state(ctx.message.server)
        if not state.is_playing():
            await self.bot.say('V momenta ne vurvi nikakva muzika...')
            return

        voter = ctx.message.author
        if voter == state.current.requester:
            await self.bot.say('Ima request za smenqne...')
            state.skip()
        elif voter.id not in state.skip_votes:
            state.skip_votes.add(voter.id)
            total_votes = len(state.skip_votes)
            if total_votes >= 3:
                await self.bot.say('Skipvane na muzikata...')
                state.skip()
            else:
                await self.bot.say('Skip glas pusnat [{}/3]'.format(total_votes))
        else:
            await self.bot.say('Veche si glasuval.')
                
                
    @commands.command(pass_context=True, no_pm=True)
    async def playing(self, ctx):

        state = self.get_voice_state(ctx.message.server)
        if state.current is None:
            await self.bot.say('Ne sum pusnal nishto?.')
        else:
            skip_count = len(state.skip_votes)
            await self.bot.say('Sega vurvi {} [skips: {}/3]'.format(state.current, skip_count))

bot = commands.Bot(command_prefix=commands.when_mentioned_or('.'), description='')
bot.add_cog(Muzika(bot))
bot.add_cog(IplexMC(bot))

@bot.event
async def on_ready():
    print("Bota e zareden!")
    print("User: {0}".format(bot.user.name))
    print("ID: {0}".format(bot.user.id))

bot.run('im not stupid ;)')
