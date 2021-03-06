import asyncio
import os
import random
import atexit
import traceback
from time import sleep
import datetime
from io import BytesIO

import discord
from discord.ext.commands.cooldowns import BucketType
from discord.ext import tasks, commands
import ujson

from dClient import dClient
from conversation import Conversation, ConversationManager
from utils import ImageCensoring, ImageDescribing
from PIL import Image





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




# Some func ===================
globalVar = {
    'config_path': 'config.json'
}

def createProfile(globalVar):
    model = {
        "TOKEN":"",
        "owner": 1111111111111111111,
        "moderator": [1111111111111111111, 1111111111111111111],
        "IS_BOT":False,
        "prefix":"",
        "active_guild":1111111111111111111,
        "nsfw_root_dirs":[],
        "nsfw_channel_id":1111111111111111111,
        "command_aliases":{
            "change_tag":[
                "bucu"
            ],
            "change_page":[
                "gay"
            ],
            "change_timeInterval":[
                "dit"
            ],
            "playback":[
                "ditme"
            ],
            "info":[
                "sua"
            ]
        },
        "time_interval":[
            15,
            30
        ]
    }

    # INFO
    print("====== CREATE A PROFILE ======")
    while True:
        pName = input("| Input profile name. (No space allowed)\n| > ")
        try: pName = pName.split(' ')[0]
        except IndexError: continue
        break
    pToken = input("| Input poster's token.\n| > ")
    while True:
        try: 
            pOwnerId = int(input("| Input owner's ID.\n| > "))
            break
        except ValueError:
            print("<!> Invalid owner's ID.")
    while True:
        pIsBot = input("| Is the poster a BOT account, or a USER account? (y/n)\n| > ")
        pIsBot = pIsBot.lower()
        if pIsBot == 'y':
            pIsBot = True
        elif pIsBot == 'n':
            pIsBot = False
        else:
            print("<!> Invalid response!")
            continue
        break
    pPrefix = input("! Input poster's prefix.\n| > ")
    while True:
        try: 
            pGuildId = int(input("| Input server's ID. (The server to post images)\n| > "))
            break
        except ValueError:
            print("<!> Invalid server's ID.")
    while True:
        try: 
            pChannelId = int(input("| Input channel's ID. (The channel to post images, and must be NSFW)\n| > "))
            break
        except ValueError:
            print("<!> Invalid channel's ID.")
    print("====== PLEASE WAIT... ======")
    sleep(1) # Purely for dramatic purpose
    model['TOKEN'] = pToken
    model['owner'] = pOwnerId
    model['moderator'].append(pOwnerId)
    model['IS_BOT'] = pIsBot
    model['prefix'] = pPrefix
    model['active_guild'] = pGuildId
    model['nsfw_channel_id'] = pChannelId
    print("====== EXTRACTING at UID 5000... ======")
    sleep(2) # Also for dramatic purpose
    print("====== PROFILE SET UP! ======")

    return pName, model
        
def deleteProfile(globalVar, configAll, targetProfile):
    try:
        del configAll[targetProfile]
    except KeyError:
        return 0
    if not configAll: return 2
    return configAll

def rewriteConfig(globalVar, configAll):
    with open(globalVar['config_path'], mode='w+') as f:
        ujson.dump(configAll, f, indent=4)

def loadConfig(globalVar):
    try:
        with open(globalVar['config_path'], mode='r') as f:    # Rename 'config_example.json' to 'config.json'
            configAll = ujson.load(f)
        if not configAll:
            raise FileNotFoundError
    except FileNotFoundError:
        print("<!> No profile found! Creating new one...")
        configAll = {}
        name, model = createProfile(globalVar)
        configAll[name] = model

        rewriteConfig(globalVar, configAll)
        
    return configAll

def console(globalVar, userInput):

    if userInput == 'new':
        createProfile(globalVar)
    elif userInput == 'del':
        targetProfile = input("| Type the profile's name to delete:\n| > ") 
        resp = deleteProfile(globalVar, configAll, targetProfile)
        if resp or resp == 2:
            rewriteConfig(globalVar, configAll)
            print("<*> Profile deleted!")
        else:
            print("<!> Profile name not found!")
    else:
        return False
    return True



# BOOT ==================
configAll = loadConfig(globalVar)

while True:
    try:
        profileName = input("| [new]   ---   Create a new profile\n| [del]   ---   Delete a profile\n| Choose a profile:\n+ [{}]\n> ".format(']\n+ ['.join(configAll.keys())))

        if console(globalVar, profileName):
            continue

        temp = configAll[profileName]
        break
    except KeyError:
        print("\n<!> Invalid profile.")



# INIT ==================
client = commands.Bot(command_prefix=temp['prefix'])
# client.remove_command('help')
client.myData = temp
client.myData['configAll'] = configAll
client.myData['profileName'] = profileName
client.helpDict = prepHelpDict()
client.myData['root_config'] = ['TOKEN', 'IS_BOT', 'owner', 'moderator', 'prefix', 'active_guild', 'nsfw_root_dirs', 'nsfw_channel_id', 'command_aliases', 'time_interval']
client.IS_BOT_READY = False
client.POSTING = False



extensions = [
    'cog.error_handler',
    'cog.misc'
]







@client.event
async def on_ready():
    global client

    client.msg_bank = []
    
    client.dClient = dClient()
    client.myData['nsfw_paths'] = getPaths(client.myData['nsfw_root_dirs'])
    client.myData['nsfw_channel'] = client.get_channel(client.myData['nsfw_channel_id'])
    client.myData['IS_RUNNING'] = False
    client.myData['IS_RECORDING'] = False
    client.myData['blocklist'] = []
    client.myData['sites'] = {
        'danbooru': 'https://danbooru.donmai.us',
        'nhentai': 'nhentai',
        'reddit': 'https://www.reddit.com',
        'yandere': 'https://yande.re'
    }
    client.myData['site_codes'] = {
        'https://danbooru.donmai.us': 0,
        'nhentai': 1,
        'https://www.reddit.com': 2,
        'https://yande.re': 3
    }
    client.myData['site_code'] = client.myData['site_codes'][client.dClient.config[client.dClient.config_currentPlaylist]['site']]

    client.CM = ConversationManager(targetChannelID=660081356860030989)

    nsfw_loop.start()
    client.IS_BOT_READY = True
    print("|||||||||||| THE BOT IS READY ||||||||||||")

@client.event
async def on_message(msg):
    if not client.IS_BOT_READY: return
    if msg.author.id in client.myData['blocklist']: return

    # Sticking reaction
    # try:
    #     if msg.guild.id == 479636890358906881:
    #         # # CONVERSATIONN ANALYSIS
    #         # if client.myData['IS_RECORDING'] and msg.channel.id == client.CM.config['targetChannelID']:
    #         #     content = filteringConv(msg)
    #         #     if content:
    #         #         try: await client.CM.msgListener((str(datetime.datetime.now()), msg.author.id, msg.author.name, content))
    #         #         except RuntimeError:
    #         #             await asyncio.sleep(0.01)
    #         #             await client.CM.msgListener((str(datetime.datetime.now()), msg.author.id, msg.author.name, content))

    #         content = msg.content.lower()
    #         if 'uon' in content or 'ươn' in content or 'uown' in content: 
    #             await msg.add_reaction('\U0001f595')
    # except AttributeError: pass
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

# @client.command(aliases=['cuu_tao'])
# async def help(ctx, *args):
#     await ctx.send('https://imgur.com/a/GjfUh66.png')
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

@client.command(aliases=client.myData['command_aliases']['change_tag'], brief=client.helpDict['tag']['brief'])
@commands.cooldown(1, 10, type=BucketType.user)
@check_nsfwChannel()
async def tag(ctx, *args):
    if not args: return
    common = set(args).intersection(client.dClient.config[client.dClient.config_currentPlaylist]['blacklist'])
    if common:
        await ctx.send(":warning: Tags `{}` blacklisted!".format('` `'.join(common))); return

    client.dClient.setTag(list(args))
    print(client.dClient.config[client.dClient.config_currentPlaylist]['tag'])
    await ctx.channel.send("Okay Imma bu some cu with `{}`. If I can't, just `{}` will do for me. yea?".format('` `'.join(args), '` `'.join(client.dClient.default_tag[client.dClient.config[client.dClient.config_currentPlaylist]['site']])))

@client.command(aliases=client.myData['command_aliases']['change_page'], brief=client.helpDict['page']['brief'])
@commands.cooldown(1, 10, type=BucketType.user)
@check_nsfwChannel()
async def page(ctx, *args):
    if not args: return
    args = list(args)

    try:
        if args[0].isdigit:
            if not await client.dClient.inUsedCheck(): return
            client.dClient.setPage(args[0])
            await ctx.channel.send(f"hmm page {args[0]} huh...")
    except IndexError: return

@client.command(aliases=client.myData['command_aliases']['change_timeInterval'], brief=client.helpDict['time']['brief'])
@commands.cooldown(1, 10, type=BucketType.user)
@check_nsfwChannel()
async def time(ctx, *args):
    try:
        a = int(args[0])
        b = int(args[1])
        if a < 8 or b < 8:
            client.myData['time_interval'][0] = 8
            client.myData['time_interval'][1] = client.myData['time_interval'][0] + 20
        elif a > 300 or b > 300:
            client.myData['time_interval'][1] = 8
            client.myData['time_interval'][0] = client.myData['time_interval'][1] - 20
        elif a < b:
            client.myData['time_interval'][0] = a
            client.myData['time_interval'][1] = b
        elif a > b:
            client.myData['time_interval'][0] = b
            client.myData['time_interval'][1] = a
        elif a == b:
            if b >= 280:
                client.myData['time_interval'][0] = client.myData['time_interval'][1] - 20
            if a <= 28:
                client.myData['time_interval'][1] = client.myData['time_interval'][0] + 20
    except (IndexError, ValueError): await ctx.send(f":warning: [**`{client.myData['time_interval'][0]} ~ {client.myData['time_interval'][1]}`**] Please type in `min_time` and `max_time` (e.g. `{client.myData['prefix']}{client.myData['command_aliases']['change_timeInterval']} 10 25`) (Min=8, Max=300)"); return

    await ctx.send(f":white_check_mark: Time interval is set as **`{client.myData['time_interval'][0]} ~ {client.myData['time_interval'][1]}`** secs.")

    updateConfig(client.myData)

@client.command(aliases=client.myData['command_aliases']['playback'], brief=client.helpDict['playback']['brief'])
@commands.cooldown(1, 10, type=BucketType.user)
@check_nsfwChannel()
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

@client.command(brief=client.helpDict['site']['brief'])
@commands.cooldown(1, 30, type=BucketType.guild)
@check_nsfwChannel()
async def site(ctx, *args):
    try:
        client.myData['sites'][args[0]]
        while True:
            if not await client.dClient.inUsedCheck():
                await asyncio.sleep(0.5)
            else: break
        client.dClient.setSite(client.myData['sites'][args[0]])
        client.myData['site_code'] = client.myData['site_codes'][client.dClient.config[client.dClient.config_currentPlaylist]['site']]
    except IndexError: await ctx.send(":warning: Missing site names (`{}`)".format('` `'.join(tuple(client.myData['sites'].keys())))); return
    except KeyError: await ctx.send(":warning: Invalid options! (`{}`)".format('` `'.join(tuple(client.myData['sites'].keys())))); return

    await ctx.send(f"switching to **`{client.myData['sites'][args[0]]}`**... please wait a while...")

@client.command(brief=client.helpDict['skip']['brief'])
@commands.cooldown(1, 10, type=BucketType.guild)
@check_nsfwChannel()
async def skip(ctx, *args):
    if client.myData['site_code'] != 1:
        await ctx.send(":warning: Manga-streaming mode only!"); return

    while client.POSTING:
        await asyncio.sleep(0)
    
    client.POSTING = True

    await ctx.send("Please wait...")
    await client.dClient.mangaSkip()

    await ctx.send("Skipped~ <3")
    client.POSTING = False

@client.command(brief=client.helpDict['tags']['brief'])
@commands.cooldown(1, 10, type=BucketType.guild)
@check_nsfwChannel()
async def tags(ctx, *args):

    # DANBOORU
    if client.myData['site_code'] == 0:
        # Prep
        category = 'any'
        order = 'count'
        limit = 30
        for i in args:
            # tag
            if i == args[0]: tag = args[0]
            # category
            elif i in tuple(client.dClient.CATEGORY_INDEX.keys()): category = i
            elif i in ('name', 'date', 'count'): order = i
            elif i.isdigit(): limit = (int(i) if int(i) <= limit else limit)

        try: resp = await client.dClient.searchTag(tag, source=client.myData['site_code'], category=category, order=order, limit=limit)
        except UnboundLocalError: await ctx.send(":warning: Syntax: `change_site [tag] (any | general | artist | copyright | character) (name | date | count) (result_limit)` (`()` are optional)"); return

        line = ''
        for r in resp:
            await asyncio.sleep(0)
            line += "**`{}`**||+{}|| ".format(r['name'], r['post_count'])

    # YANDERE
    elif client.myData['site_code'] == 3:
        # Prep
        category = 'any'
        order = 'count'
        limit = 30
        for i in args:
            # tag
            if i == args[0]: tag = args[0]
            # category
            elif i in tuple(client.dClient.CATEGORY_INDEX.keys()): category = i
            elif i in ('name', 'date', 'count'): order = i
            elif i.isdigit(): limit = (int(i) if i <= limit else limit)

        try: resp = await client.dClient.searchTag(tag, source=client.myData['site_code'], category=category, order=order, limit=limit)
        except UnboundLocalError: await ctx.send(":warning: Syntax: `change_site [tag] (any | general | artist | copyright | character) (name | date | count)` (`()` are optional)"); return

        line = ''
        for r in resp:
            await asyncio.sleep(0)
            line += "**`{}`**||+{}|| ".format(r['name'], r['count'])

    # site_not_supported
    else:
        await ctx.send(":warning: Current site is not supported with this functionality."); return
    

    await ctx.send(line)



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
        Sheltering at **{}**, and listening to `{}`.
        Blacklist: [`{}`]
        MOD: [`{}`]
    """.format(
        client.dClient.config[client.dClient.config_currentPlaylist]['site'],
        '` `'.join(client.dClient.config[client.dClient.config_currentPlaylist]['tag']),
        client.myData['time_interval'][0],
        client.myData['time_interval'][1],
        client.myData['IS_RUNNING'],
        client.myData['nsfw_channel'].name,
        client.myData['prefix'],
        '` `'.join(client.dClient.config[client.dClient.config_currentPlaylist]['blacklist']),
        '` `'.join([client.get_user(uid).mention for uid in client.myData['moderator'] if client.get_user(uid)])
    ))

@client.command(hidden=True)
@check_owner()
async def record(ctx, *args):
    try:
        if args[0] == 'save':
            client.CM.saveData()
        elif args[0] == 'lock':
            try: client.CM.lockConv(' '.join(args[1:]))
            except KeyError: return
        await ctx.send(":white_check_mark:")
        return
    except IndexError: pass

    if client.myData['IS_RECORDING']:
        client.myData['IS_RECORDING'] = False
        await ctx.send("Paused")
    else:
        client.myData['IS_RECORDING'] = True
        await ctx.send("Resumed")

@client.command(hidden=True)
@check_owner()
async def simuta(ctx, *args):
    ranc = random.choice(tuple(client.CM.bank.values()))
    await ctx.send(f"Here's a conversation with {len(ranc.contributor)} contributors.")
    for p in ranc.timeline:
        for line in p[1]:
            await asyncio.sleep(random.choice(range(1, 3)))
            await ctx.send(f"`[{p[0][2]}]` {line}")

@client.command(hidden=True)
@check_owner()
async def block(ctx, *args):
    try:
        try: target = ctx.message.mentions[0]
        except IndexError: pass
        if not args[0].isdigit(): raise IndexError
        else: target = int(args)
    except IndexError: await ctx.send(":warning: Missing target's mention/ID"); return

    if target in client.myData['moderator'] or target == client.myData['owner']:
        await ctx.send(":warning: Invalid target's mention/ID"); return
    
    if target in client.myData['blocklist']:
        client.myData['blocklist'].remove(target)
        await ctx.send(":white_check_mark: Unblocked!"); return
    else:
        await ctx.send(":white_check_mark: BLOCKED!"); return

@client.command()
@commands.cooldown(1, 10, type=BucketType.user)
@check_nsfwChannel()
async def censor_this(ctx, *args):
    CENSORING_MODE = "RECTANGLE"
    try:
        if args[0].upper() not in  ["RECTANGLE", "BLUR", "PIXELATE"]:
            await ctx.send(f":x: Unknown option! (`RECTANGLE` | `BLUR` | `PIXELATE`)")
            return
        CENSORING_MODE = args[0].upper()
    except IndexError: pass

    # Saving image
    if not ctx.message.attachments:
        return
    await ctx.message.attachments[0].save('imageBIO_in.png', use_cached=True)

    # Make an Image obj out of the buffer
    imageImage = Image.open('imageBIO_in.png')

    # Describing
    tDescription = ImageDescribing('imageBIO_in.png')

    # Censoring
    imageImage = ImageCensoring(imageImage, tDescription, CENSORING_MODE)

    # Saving output
    imageBIO_out = BytesIO()
    imageImage.save(imageBIO_out, "png")
    imageBIO_out.seek(0)

    await ctx.send("`{}`".format("` `".join([f"{i['label']}: {i['score']}" for i in tDescription])), file=discord.File(fp=imageBIO_out, filename='stuff.png'))
    imageBIO_out.close()
    imageImage.close()


@tasks.loop(seconds=3)       # anti-antiSelfbot       (Enabled in on_ready()    ||      On hold)
async def nsfw_loop():
    global client

    if not client.POSTING: client.POSTING = True
    else: return

    await asyncio.sleep(random.choice(range(client.myData['time_interval'][0], client.myData['time_interval'][1])))             # anti-antiSelfbot

    try:
        if not client.myData['nsfw_channel'].is_nsfw():
            print("<!> Designated channel is not NSFW!"); return
        elif not client.myData['IS_RUNNING']:
            client.POSTING = False        
            return
    except AttributeError: print("<!> Channel missing!"); return

    try:
        # await client.myData['nsfw_channel'].send(file=discord.File(random.choice(client.myData['nsfw_paths'])))
        if not await client.dClient.inUsedCheck(): return
        # DANBOORU
        if client.myData['site_code'] == 0:
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

            print(f" |  [{datetime.datetime.now()}]   ---   <D> [{client.dClient.config[client.dClient.config_currentPlaylist]['page']}][{len(client.dClient.pool)}] ", url)

        # NHENTAI
        elif client.myData['site_code'] == 1:
            # Search by ID / Search by tag
            if client.dClient.config[client.dClient.config_currentPlaylist]['tag'][0].isdigit():
                resp = await client.dClient.poolFetch(order=1, source=1, id=client.dClient.config[client.dClient.config_currentPlaylist]['tag'][0])
            else:
                resp = await client.dClient.poolFetch(order=1, source=1)

            await client.myData['nsfw_channel'].send(
                ">>> **[**`{}#{}#{}`**]** {} **[**`{}`**]**".format(
                    client.dClient.config[client.dClient.config_currentPlaylist]['page'],
                    resp['doujinshiiOrder'],
                    resp['page'],
                    resp['url'],
                    '` `'.join(client.dClient.config[client.dClient.config_currentPlaylist]['tag'])
                    )
                )

            print(f" |  [{datetime.datetime.now()}]   ---   <N> [{client.dClient.config[client.dClient.config_currentPlaylist]['page']}.{resp['doujinshiiOrder']}.{resp['page']}][{len(client.dClient.pool)}] ", resp['url'])

        # REDDIT
        elif client.myData['site_code'] == 2:
            resp = await client.dClient.poolFetch(source=2)

            await client.myData['nsfw_channel'].send(
                """>>> **[**`{}#{}`**]**[**`r/{}`**| **"{}"**] {}""".format(
                    client.dClient.config[client.dClient.config_currentPlaylist]['page'],
                    len(client.dClient.pool),
                    resp['subreddit'],
                    resp['title'],
                    resp['url']
                    )
                )

            print(f" |  [{datetime.datetime.now()}]   ---   <R> [{client.dClient.config[client.dClient.config_currentPlaylist]['page']}][{len(client.dClient.pool)}] ", resp['url'])

        # YANDERE
        else:
            resp = await client.dClient.poolFetch(source=3)

            try:
                url = resp['jpeg_url']
            except KeyError:
                try:
                    url = resp['large_file_url']
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

            print(f" |  [{datetime.datetime.now()}]   ---   <Y> [{client.dClient.config[client.dClient.config_currentPlaylist]['page']}][{len(client.dClient.pool)}] ", url)

    except:
        print(traceback.format_exc())
    finally:
        client.POSTING = False








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
        try: paths = walkthrough(dir_path, paths)
        except FileNotFoundError: print(f"<!> FileNotFound error ({dir_path})")
    
    return paths

def updateConfig(myData, config_path='config.json'):
    temp_conf = {}
    for o in myData['root_config']:
        temp_conf[o] = myData[o]
    client.myData['configAll'][client.myData['profileName']] = temp_conf
    with open(config_path, mode='w') as f:
        ujson.dump(client.myData['configAll'], f, indent=4)

def filteringConv(msg):
    """
        Return content of a message object
    """

    if msg.author.bot or msg.author == client.user: return ''
    if msg.role_mentions: return ''
    try:
        msg.content += msg.attachments[0].url
    except IndexError: pass
    return msg.content

def exiting():
    client.dClient.updateConfig(client.dClient.config, client.dClient.fpConfig)
    updateConfig(client.myData)
    print("========================== SAVED and EXIT ==========================")

async def starting():
    await client.login(client.myData['TOKEN'], bot=client.myData['IS_BOT'])
    # await client.login('NDQ2MzU2Mjg3MTIzNDg4NzY5.XiWEyg._jdIrF2tuYxoIL65ZpUfy1_iRt0', bot=False)
    print("LOGGED IN")
    await client.connect(reconnect=True)

# ====== CONFIG


    




if __name__ == "__main__":
    # for e in extensions:
    #     client.load_extension(e)
    
    # atexit.register(exiting)
    # client.run(client.myData['TOKEN'], bot=client.myData['IS_BOT'], reconnect=True)
    # client.run('NDQ2MzU2Mjg3MTIzNDg4NzY5.XiWEyg._jdIrF2tuYxoIL65ZpUfy1_iRt0', bot=False, reconnect=True)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(starting())
