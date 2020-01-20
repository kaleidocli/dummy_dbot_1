import asyncio
import os
import random
import ujson

import discord
from discord.ext import tasks, commands

from dClient import dClient
import datetime


with open('config.json', mode='r') as f:    # Rename 'config_example.json' to 'config.json'
    temp = ujson.load(f)
client = commands.Bot(command_prefix=temp['prefix'])
client.remove_command('help')
client.myData = temp
client.IS_BOT_READY = False




@client.event
async def on_ready():
    global client

    client.msg_bank = []
    
    client.dClient = dClient()
    client.myData['nsfw_paths'] = getPaths(client.myData['nsfw_root_dirs'])
    client.myData['nsfw_channel'] = client.get_channel(client.myData['nsfw_channel_id'])

    nsfw_loop.start()
    client.IS_BOT_READY = True
    print("|||||||||||| THE BOT IS READY ||||||||||||")

@client.event
async def on_message(msg):
    if not client.IS_BOT_READY: return
    # try:
    #     if msg.guild.id == client.myData['active_guild']: client.msg_bank.append(msg.content)
    # except: pass
    # if msg.channel == client.myData['nsfw_channel'] and client.myData['nsfw_pagekw'] in msg.content:
    #     try:
    #         msg.content = msg.content.replace(client.myData['nsfw_pagekw'], '')
    #         if not msg.content: return
    #         if msg.content.isdigit:
    #             if not await client.dClient.inUsedCheck(): return
    #             client.dClient.setPage(msg.content)
    #             await msg.channel.send(f"hmm page {msg.content} huh...")
    #     except IndexError: return
    # elif msg.channel == client.myData['nsfw_channel'] and client.myData['nsfw_tagkw'] in msg.content:

    #     msg.content = msg.content.replace(client.myData['nsfw_tagkw'], '')
    #     if not msg.content: return
    #     tag = msg.content.split(' ')

    #     if not await client.dClient.inUsedCheck(): return
    #     client.dClient.setTag(tag)
    #     print(client.dClient.config[client.dClient.config_currentPlaylist]['tag'])
    #     await msg.channel.send("Okay imma find you some `{}`. If I can't, im just gonna find with `{}`".format('` `'.join(tag), '` `'.join(client.dClient.default_tag)))
    # Sticking reaction
    if 'uon' in msg.content or 'ươn' in msg.content or 'uown' in msg.content:
        await msg.add_reaction('\U0001f595')
    # elif msg.author.id in (337234105219416067, 214128381762076672, 413423796456914955) or msg.content == 'baa':
    #     # await msg.add_reaction('\U0001f411')
    #     await msg.channel.send(random.choice(client.msg_bank))
    # elif msg.content == 'aknalumos_testing':
    #     resp = await client.dClient.poolFetch()
    #     print(resp)
    #     await client.myData['nsfw_channel'].send(resp)
    await client.process_commands(msg)




def check_nsfwChannel():
    def inner(ctx):
        return ctx.message.channel == client.myData['nsfw_channel']
    return commands.check(inner)

@client.command(aliases=['cuu_tao'])
async def help(ctx, *args):
    await ctx.send('https://imgur.com/a/zrB9B1G.png')
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

@client.command(aliases=[client.myData['nsfw_tagkw']])
@check_nsfwChannel()
async def change_tag(ctx, *args):
    if not args: return
    args = list(args)

    client.dClient.setTag(args)
    print(client.dClient.config[client.dClient.config_currentPlaylist]['tag'])
    await ctx.channel.send("Okay Imma bu some cu with `{}`. If I can't, just `{}` will do for me. yea?".format('` `'.join(args), '` `'.join(client.dClient.default_tag)))

@client.command(aliases=[client.myData['nsfw_pagekw']])
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






@tasks.loop(seconds=random.choice(range(10, 25)))
async def nsfw_loop():
    global client

    # await client.myData['nsfw_channel'].send(file=discord.File(random.choice(client.myData['nsfw_paths'])))
    if not await client.dClient.inUsedCheck(): return
    await asyncio.sleep(random.choice(range(15)))       # anti-antiSelfbot
    resp = await client.dClient.poolFetch()
    try:
        url = resp['large_file_url']
    except KeyError:
        try:
            url = resp['file_url']
        except KeyError:
            url = resp['source']
    await client.myData['nsfw_channel'].send(
        ">>> **[**`{}`**][**`{}`**]** {}".format(
            client.dClient.config[client.dClient.config_currentPlaylist]['page'],
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




if __name__ == "__main__":


    client.run(client.myData['TOKEN'], bot=client.myData['IS_BOT'], reconnect=True)
    # client.run('NDQ5Mjc4ODExMzY5MTExNTUz.Xcodxg.9TAsDeHjUghAD_D0VH14j6nmCOg', bot=True, reconnect=True)
