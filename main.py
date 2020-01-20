import asyncio
import os
import random
import ujson

import discord
from discord.ext import tasks, commands

from dClient import dClient
import datetime



client = discord.Client()
client.myData = {}
with open('config.json', mode='r') as f:    # Rename 'config_example.json' to 'config.json'
    client.myData = ujson.load(f)
client.myData['nsfw_paths'] = getPaths(client.myData['nsfw_root_dirs'])
client.myData['nsfw_channel'] = client.get_channel(client.myData['nsfw_channel_id'])

@client.event
async def on_ready():
    client.msg_bank = []
    
    client.dClient = dClient()

    nsfw_loop.start()
    print("|||||||||||| THE BOT IS READY ||||||||||||")

@client.event
async def on_message(msg):
    global client
    try:
        try:
            if msg.guild.id == client.myData['active_guild']: client.msg_bank.append(msg.content)
        except: pass
        if msg.channel == client.myData['nsfw_channel'] and client.myData['nsfw_pagekw'] in msg.content:
            try:
                msg.content = msg.content.replace(client.myData['nsfw_pagekw'], '')
                if not msg.content: return
                if msg.content.isdigit:
                    if not await client.dClient.inUsedCheck(): return
                    client.dClient.setPage(msg.content)
                    await msg.channel.send(f"hmm page {msg.content} huh...")
            except IndexError: return
        elif msg.channel == client.myData['nsfw_channel'] and client.myData['nsfw_tagkw'] in msg.content:

            msg.content = msg.content.replace(client.myData['nsfw_tagkw'], '')
            if not msg.content: return
            tag = msg.content.split(' ')

            if not await client.dClient.inUsedCheck(): return
            client.dClient.setTag(tag)
            print(client.dClient.config[client.dClient.config_currentPlaylist]['tag'])
            await msg.channel.send("Okay imma find you some `{}`. If I can't, im just gonna find with `{}`".format('` `'.join(tag), '` `'.join(client.dClient.default_tag)))
        # Sticking reaction
        elif 'uon' in msg.content or 'ươn' in msg.content or 'uown' in msg.content:
            await msg.add_reaction('\U0001f595')
        # elif msg.author.id in (337234105219416067, 214128381762076672, 413423796456914955) or msg.content == 'baa':
        #     # await msg.add_reaction('\U0001f411')
        #     await msg.channel.send(random.choice(client.msg_bank))
        # elif msg.content == 'aknalumos_testing':
        #     resp = await client.dClient.poolFetch()
        #     print(resp)
        #     await client.myData['nsfw_channel'].send(resp)

    except IndexError: return

@tasks.loop(seconds=15)
async def nsfw_loop():
    # await client.myData['nsfw_channel'].send(file=discord.File(random.choice(client.myData['nsfw_paths'])))
    if not await client.dClient.inUsedCheck(): return
    resp = await client.dClient.poolFetch()
    print(f"[{datetime.datetime.now()}]   ---   [{len(client.dClient.pool)}] ", resp['file_url'])
    await client.myData['nsfw_channel'].send(embed=discord.Embed(description="[{}] `{}` ([full tag](https://www.large-type.com/#%5B{}%5D))".format(client.dClient.config[client.dClient.config_currentPlaylist]['page'], '` `'.join(client.dClient.config[client.dClient.config_currentPlaylist]['tag']), resp['tag_string_general'].replace(' ', '%5D%20%5B')), colour=0x36393E).set_image(url=resp['file_url']))






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
