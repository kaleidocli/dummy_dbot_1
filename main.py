import asyncio
import os
import random
import atexit

import discord
from discord.ext.commands.cooldowns import BucketType
from discord.ext import tasks, commands
import ujson

from dClient import dClient
import datetime





def prepHelpDict(helper_path='helper.json'):
    temp = {}
    with open(helper_path, mode='r') as f:
        temp2 = ujson.load(f)

    for k, v in temp2.items():
        temp[k] = {}
        temp[k]['brief'] = v['brief'].replace('prefix_here', client.myData['prefix'])
        try:
            temp[k]['brief'] = temp[k]['brief'].replace('aliases_here', client.myData['command_aliases'][k][0])
        except KeyError: pass
    return temp






with open('config.json', mode='r') as f:    # Rename 'config_example.json' to 'config.json'
    temp = ujson.load(f)

client = commands.Bot(command_prefix=temp['prefix'])
client.remove_command('help')
client.myData = temp
client.helpDict = prepHelpDict()
client.myData['root_config'] = ['TOKEN', 'IS_BOT', 'owner', 'moderator', 'prefix', 'active_guild', 'nsfw_root_dirs', 'nsfw_channel_id', 'command_aliases', 'time_interval']
client.IS_BOT_READY = False



extensions = [
    'error_handler'
]







@client.event
async def on_ready():
    global client

    client.msg_bank = []
    
    client.dClient = dClient()
    client.myData['nsfw_paths'] = getPaths(client.myData['nsfw_root_dirs'])
    client.myData['nsfw_channel'] = client.get_channel(client.myData['nsfw_channel_id'])
    client.myData['IS_RUNNING'] = True

    nsfw_loop.start()
    client.IS_BOT_READY = True
    print("|||||||||||| THE BOT IS READY ||||||||||||")

@client.event
async def on_message(msg):
    if not client.IS_BOT_READY: return

    # Sticking reaction
    if msg.guild.id == 479636890358906881:
        msg.content = msg.content.lower()
        if 'uon' in msg.content or 'ươn' in msg.content or 'uown' in msg.content or 'cyberlife' in msg.content:
            await msg.add_reaction('\U0001f595')
    # elif msg.author.id in (337234105219416067, 214128381762076672, 413423796456914955) or msg.content == 'baa':
    #     # await msg.add_reaction('\U0001f411')
    #     await msg.channel.send(random.choice(client.msg_bank))
    await client.process_commands(msg)







def check_nsfwChannel():
    def inner(ctx):
        return ctx.message.channel == client.myData['nsfw_channel']
    return commands.check(inner)

def check_mod():
    def inner(ctx):
        return ctx.author.id in client.myData['moderator']
    return commands.check(inner)

def check_owner():
    def inner(ctx):
        return ctx.message.author.id == client.myData['owner']
    return commands.check(inner)

@client.command(aliases=['cuu_tao'])
async def help(ctx, *args):
    await ctx.send('https://imgur.com/a/GjfUh66.png')
    #     await ctx.send(f"""
    #         ```css
    # PREFIX == '{client.myData['prefix']}'
    # ==========================================
    # [{client.myData['nsfw_tagkw']}] [tags]  Change tags. 
    #                                         (e.g. "{client.myData['prefix']}{client.myData['nsfw_tagkw']} yuri tentacle")
    # [{client.myData['nsfw_pagekw']}]        Change page. Also, page is automatically increased after all images of that page is used.
    #                                         (e.g. "{client.myData['prefix']}{client.myData['nsfw_tagkw']} 6")
    #         ```
    #     """)

@client.command(aliases=client.myData['command_aliases']['change_tag'], brief=client.helpDict['change_tag']['brief'])
@commands.cooldown(1, 10, type=BucketType.user)
@check_nsfwChannel()
async def change_tag(ctx, *args):
    if not args: return
    args = list(args)

    client.dClient.setTag(args)
    print(client.dClient.config[client.dClient.config_currentPlaylist]['tag'])
    await ctx.channel.send("Okay Imma bu some cu with `{}`. If I can't, just `{}` will do for me. yea?".format('` `'.join(args), '` `'.join(client.dClient.default_tag)))

@client.command(aliases=client.myData['command_aliases']['change_page'], brief=client.helpDict['change_page']['brief'])
@commands.cooldown(1, 10, type=BucketType.user)
@check_nsfwChannel()
async def change_page(ctx, *args):
    if not args: return
    args = list(args)

    try:
        if args[0].isdigit:
            if not await client.dClient.inUsedCheck(): return
            client.dClient.setPage(args[0])
            await ctx.channel.send(f"hmm page {args[0]} huh...")
    except IndexError: return

@client.command(aliases=client.myData['command_aliases']['change_timeInterval'], brief=client.helpDict['change_timeInterval']['brief'])
@commands.cooldown(1, 10, type=BucketType.user)
@check_nsfwChannel()
async def change_timeInterval(ctx, *args):
    try:
        a = int(args[0])
        b = int(args[1])
        if a < 8 or b < 8:
            client.myData['time_interval'][0] = 8
            client.myData['time_interval'][1] = client.myData['time_interval'][0] + 20
        elif a > 180 or b > 180:
            client.myData['time_interval'][1] = 8
            client.myData['time_interval'][0] = client.myData['time_interval'][1] - 20
        elif a < b:
            client.myData['time_interval'][0] = a
            client.myData['time_interval'][1] = b
        elif a > b:
            client.myData['time_interval'][0] = b
            client.myData['time_interval'][1] = a
        elif a == b:
            if b >= 160:
                client.myData['time_interval'][0] = client.myData['time_interval'][1] - 20
            if a <= 28:
                client.myData['time_interval'][1] = client.myData['time_interval'][0] + 20
    except IndexError: await ctx.send(f":warning: [**`{client.myData['time_interval'][0]} ~ {client.myData['time_interval'][1]}`**] Please type in `min_time` and `max_time` (e.g. `{client.myData['prefix']}{client.myData['command_aliases']['change_timeInterval']} 10 25`) (Min=8, Max=180)"); return

    await ctx.send(f":white_check_mark: Time interval is set as **`{client.myData['time_interval'][0]} ~ {client.myData['time_interval'][1]}`** secs.")

    updateConfig(client.myData)

@client.command(aliases=client.myData['command_aliases']['playback'], brief=client.helpDict['playback']['brief'])
@commands.cooldown(1, 10, type=BucketType.user)
@check_nsfwChannel()
@check_mod()
async def playback(ctx, *args):
    try:
        if args[0] == 'pause': client.myData['IS_RUNNING'] = False
        elif args[0] == 'resume':
            client.myData['IS_RUNNING'] = True
            await client.myData['nsfw_channel'].send(":white_check_mark: Resumed!"); return
    except IndexError: await ctx.send(":warning: Choose `pause` or `resume`!"); return
    await client.myData['nsfw_channel'].send(f":white_check_mark: NSFW Playlist was paused by moderator {ctx.author.mention}.")
    print("""
        ================================================
        ============    CURRENTLY PAUSED    ============
        =================================== by {}|{}
        """.format(ctx.author.id, ctx.author.name))

@client.command(brief=client.helpDict['grant_mod']['brief'])
@check_owner()
async def grant_mod(ctx, *args):
    try:
        if ctx.message.mentions[0].id not in client.myData['moderator']:
            client.myData['moderator'].append(ctx.message.mentions[0].id)
            await ctx.send(":white_check_mark: Granted!")
        else:
            client.myData['moderator'].remove(ctx.message.mentions[0].id)
            await ctx.send(":white_check_mark: Demodded!")
    except IndexError:
        await ctx.send(":warning: Please tag a user."); return
    updateConfig(client.myData)

@client.command(aliases=client.myData['command_aliases']['info'], brief=client.helpDict['info']['brief'])
async def info(ctx, *args):
    await ctx.send("""
        >>> Browsing `{}` for [**`{}`**]. Average posting speed: `{}~{} secs/img`.
        **Alive?** {}
        Sheltering at {}, and you can reach me by `{}`.
    """.format(
        client.dClient.config[client.dClient.config_currentPlaylist]['site'],
        '` `'.join(client.dClient.config[client.dClient.config_currentPlaylist]['tag']),
        client.myData['time_interval'][0],
        client.myData['time_interval'][1],
        client.myData['IS_RUNNING'],
        client.myData['nsfw_channel'].name,
        client.myData['prefix']
    ))






@tasks.loop(seconds=random.choice(range(client.myData['time_interval'][0], client.myData['time_interval'][1])))       # anti-antiSelfbot
async def nsfw_loop():
    global client

    try:
        if not client.myData['nsfw_channel'].is_nsfw():
            print("<!> Designated channel is not NSFW!"); return
        elif not client.myData['IS_RUNNING']: return
    except AttributeError: print("<!> Channel missing!"); return

    # await client.myData['nsfw_channel'].send(file=discord.File(random.choice(client.myData['nsfw_paths'])))
    if not await client.dClient.inUsedCheck(): return
    resp = await client.dClient.poolFetch()
    try:
        url = resp['large_file_url']
    except KeyError:
        try:
            url = resp['file_url']
        except KeyError:
            url = resp['source']
    await client.myData['nsfw_channel'].send(
        ">>> **[**`{}#{}`**][**`{}`**]** {}".format(
            client.dClient.config[client.dClient.config_currentPlaylist]['page'],
            len(client.dClient.pool),
            '` `'.join(client.dClient.config[client.dClient.config_currentPlaylist]['tag']),
            url
            )
        )
    print(f" |  [{datetime.datetime.now()}]   ---   [{client.dClient.config[client.dClient.config_currentPlaylist]['page']}][{len(client.dClient.pool)}] ", url)






def getPaths(dirs):
    paths = []

    def walkthrough(dir_path, paths, prev=''):
        dir_path = os.path.join(prev, dir_path)
        for f in os.listdir(dir_path):
            if '.' not in f and f not in dirs:
                try:
                    paths = walkthrough(f, paths, prev=dir_path)
                except NotADirectoryError: pass
            if f.endswith('.png') or f.endswith('.jpg'):
                paths.append(os.path.join(dir_path, f))
            else:
                continue
        return paths

    for dir_path in dirs:
        paths = walkthrough(dir_path, paths)
    
    return paths

def updateConfig(myData, config_path='config.json'):
    temp_conf = {}
    for o in myData['root_config']:
        temp_conf[o] = myData[o]
    with open(config_path, mode='w') as f:
        ujson.dump(temp_conf, f, indent=4)

def exiting():
    client.dClient.updateConfig(client.dClient.config, client.dClient.fpConfig)
    updateConfig(client.myData)
    print("========================== SAVED and EXIT ==========================")




if __name__ == "__main__":
    for e in extensions:
        client.load_extension(e)

    atexit.register(exiting)
    client.run(client.myData['TOKEN'], bot=client.myData['IS_BOT'], reconnect=True)
    # client.run('NDQ5Mjc4ODExMzY5MTExNTUz.Xcodxg.9TAsDeHjUghAD_D0VH14j6nmCOg', bot=True, reconnect=True)
