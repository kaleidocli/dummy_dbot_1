import aiohttp
import asyncio
import random
import time
import datetime
import json

import ujson
import nhentai
import traceback



class dClient:
    """
        To use, simply use <POOLFETCH>
        To re-fill pool, use <GETPOST>
        To set tag, please use setter setTag()
    """

    def __init__(self, fpConfig='dClient_config.json', default_tag=None):
        """
            (List)      default_tag

            To update new site, consider:
                + self.TAGS_PER_PAGE
                + self.getPost()
                + self.getTag()
            also in <main.py>, consider:
                + nsfw_loop()
                + search_tag()
                + client.myData['sites']
                + client.myData['site_code']
            All should adhere to general.
        """

        self.ACTIVATED = False
        self.RESET_POOL = False
        self.IN_USED = False
        if not default_tag:
            self.default_tag = {
                'nhentai': ['random'],
                'https://danbooru.donmai.us': ['popular'],
                'https://www.reddit.com': ['cosplaybabes'],
                'https://yande.re': ['popular']
            }
        else: self.default_tag = default_tag
        self.infiniteTag = [
            'nhentai',
            'https://yande.re'
        ]
        self.session = aiohttp.ClientSession(json_serialize=ujson.dumps)
        self.fpConfig = fpConfig
        resp = self.getConfig(self.fpConfig)
        if not resp:
            self.config = {
                'aaaaa': 'default',          # current playlist. sorting.
                'default': {
                    'site': 'https://danbooru.donmai.us',
                    'rating': 'explicit',
                    'tag': self.default_tag['https://danbooru.donmai.us'],
                    'page': 1,
                    "blacklist":[
                        "guro",
                        "scat"
                    ]
                },
                'default_prototype': {
                    'site': 'https://danbooru.donmai.us',
                    'rating': 'explicit',
                    'tag': self.default_tag['https://danbooru.donmai.us'],
                    'page': 1,
                    "blacklist":[
                        "guro",
                        "scat"
                    ]
                }
            }
            self.updateConfig(self.config, self.fpConfig)
            print('<*> Config not found, so one is created!')
        else: self.config = resp
        self.config_currentPlaylist = self.config['aaaaa']

        self.pool = []          # Each dClient has ONLY ONE pool, and ONLY stored in cache. Switching playlist means pool got deleted as well.

        self.CATEGORY_INDEX = {
            'any': '',
            'general': '0',
            'artist': '1',
            'copyright': '3',
            'character': '4'
        }
        self.TAGS_PER_PAGE = {     # Site_code : Number of tags received per page (1 means unknown)
            0: 20,
            1: 1,
            2: 1,
            3: 52
        }




    async def getPost(self, tags=None, page=None, limit='1000', source=0, id=None):
        """
            (Str)    limit        Max=1000
            (List)   Tag          Max=2
            (Int)    Page
            (int)    source       0==danbooru    1==nhentai     2==reddit
        """
        # print("into getPost")
        # DANBOORU
        if not source:
            if int(limit) > 1000: limit = '1000'
            elif int(limit) < 0: limit = '1'
            if page == None:
                page = str(self.config[self.config_currentPlaylist]['page'])
            else: page = str(page)

            # QUERY: Popular over time
            if self.config[self.config_currentPlaylist]['tag'] == ['popular']:
                query = "explore/posts/popular.json?date={}".format(self.random_date('2010-1-1', datetime.datetime.today().strftime('%Y-%m-%d'), random.random()))
            # QUERY: Tag
            else:
                if tags:
                    tag = '+'.join(tags[0:2])
                else:
                    if not self.config[self.config_currentPlaylist]['tag']: self.config[self.config_currentPlaylist]['tag'] = self.default_tag[self.config[self.config_currentPlaylist]['site']]
                    # QUERY: Random
                    if self.config[self.config_currentPlaylist]['tag'] == ['random']:
                        tag = '?random=true'
                    else:
                        tag = 'tags={}'.format('+'.join(self.config[self.config_currentPlaylist]['tag'][0:2]))
                query = 'posts.json?{}&limit={}&page={}&rating={}'.format(tag, limit, page, self.config[self.config_currentPlaylist]['rating'])

            async with self.session.get('{}/{}'.format(self.config[self.config_currentPlaylist]['site'], query)) as resp:
                content = await resp.json()
                print(f"""<*> GET {len(content)} posts! (p={page}) (q="{resp.url}")""")
                return content          # content is list

        # NHENTAI
        elif source == 1:
            # print("getPost 1")
            if not tags: tags = self.config[self.config_currentPlaylist]['tag']
            # print("getPost 2")
            if id:
                try:
                    # print("getPost 3")
                    return await self.doujinshiisToPool([nhentai.Doujinshi(int(id))])
                except nhentai.errors.DoujinshiNotFound:
                    # print("getPost 4")
                    return []
            else:
                # print("getPost 5")
                return await self.doujinshiisToPool([i for i in nhentai.search(' '.join(tags), page=page)])

        # REDDIT
        elif source == 2:
            # Preparing
            # print("getPost 6")
            if int(limit) > 100: limit = '100'
            elif int(limit) < 0: limit = '1'
            if not page:
                page = int(self.config[self.config_currentPlaylist]['page'])

            # QUERY
            query = f"r/{self.config[self.config_currentPlaylist]['tag'][0]}/hot.json?limit={limit}"
            # print("getPost 7")
            content = await self.redditRequest(query, page=page)
            # print("getPost 8")
            print(f"""<*> GET {len(content)} posts! (p={page}) (base_q="{query}")""")
            return await self.redditToPool(content)

        # YANDE.RE
        else:
            if int(limit) > 1000: limit = '1000'
            elif int(limit) < 0: limit = '1'
            if page == None:
                page = str(self.config[self.config_currentPlaylist]['page'])
            else: page = str(page)

            # QUERY: Popular over time
            if self.config[self.config_currentPlaylist]['tag'] == ['popular']:
                query = "/post/popular_by_week.json?date={}".format(self.random_date('day=1&month=1&year=2010', datetime.datetime.today().strftime('day=%d&month=%m&year=%Y'), random.random(), format='day=%d&month=%m&year=%Y'))
            # QUERY: Tag
            else:
                if tags:
                    tag = '+'.join(tags)
                else:
                    if not self.config[self.config_currentPlaylist]['tag']: self.config[self.config_currentPlaylist]['tag'] = self.default_tag[self.config[self.config_currentPlaylist]['site']]
                    # QUERY: Random
                    if self.config[self.config_currentPlaylist]['tag'] == ['random']:
                        tag = '?random=true'
                    else:
                        tag = 'tags={}'.format('+'.join(self.config[self.config_currentPlaylist]['tag']))
                query = 'post.json?{}&limit={}&page={}&rating={}'.format(tag, limit, page, self.config[self.config_currentPlaylist]['rating'])

            async with self.session.get('{}/{}'.format(self.config[self.config_currentPlaylist]['site'], query)) as resp:
                content = await resp.json()
                print(f"""<*> GET {len(content)} posts! (p={page}) (q="{resp.url}")""")
                return content          # content is list



    async def poolFetch(self, first=False, order=0, source=0, id=None):
        """
            Randomly fetch a response DICT from pool.
            If pool is empty, create one, using current playlist's config

            (int) order            0==random   1==chronical
            (int) source           0==danbooru    1==nhentai    2==reddit
        """
        
        self.IN_USED = True
        # print("into fetch")
        try:
            if self.RESET_POOL:
                # print("reseting pool 1")
                if id: self.pool = await self.getPost(source=source, id=id) 
                else: self.pool = await self.getPost(source=source)
                # print("reseting pool 2")
                if not self.pool:
                    # print("reseting pool 3")
                    self.setTag(self.default_tag[self.config[self.config_currentPlaylist]['site']])
                    if id: self.pool = await self.getPost(source=source, id=id) 
                    else: self.pool = await self.getPost(source=source)
                    print('<*> Query is exhausted. Set back to default tag.')
                # print("reseting pool 4")
                self.updateConfig(self.config, self.fpConfig)
                # print("reseting pool 5")
                self.RESET_POOL = False
                print(f"<*> Resetting pool... (tag={self.config[self.config_currentPlaylist]['tag']})")
                if order: return self.pool.pop(0)
                else: return self.pool.pop(random.choice(range(len(self.pool))))

            try:
                # print("fetch index 1")
                if order:
                    # print("fetch in order")
                    return self.pool.pop(0)
                else:
                    # print("fetch in random")
                    return self.pool.pop(random.choice(range(len(self.pool))))
                # print("fetch index 2")
            except IndexError:
                # print("fetch index 3")
                if self.ACTIVATED or first:
                    # print("fetch index 4")
                    self.config[self.config_currentPlaylist]['page'] += 1
                    print('<*> Pool is empty. Re-filling with new page...')
                else:
                    # print("fetch index 5")
                    self.ACTIVATED = True
                    print('<*> Pool is empty. Re-filling...')
                # print("fetch index 6")
                if id: self.pool = await self.getPost(source=source, id=id) 
                else: self.pool = await self.getPost(source=source)
                # print("fetch index 7")
                if not self.pool:
                    # print("fetch index 8")
                    self.setTag(self.default_tag[self.config[self.config_currentPlaylist]['site']])
                    # print("fetch index 9")
                    self.config[self.config_currentPlaylist]['page'] = 1
                    if id: self.pool = await self.getPost(source=source, id=id) 
                    else: self.pool = await self.getPost(source=source)
                    print('<*> Query is exhausted. Set back to default tag.')
                # print("fetch index 10")
                self.updateConfig(self.config, self.fpConfig)
                # print("fetch index 11")
                if order: return self.pool.pop(0)
                else: return self.pool.pop(random.choice(range(len(self.pool))))
        finally:
            self.IN_USED = False



    async def searchTag(self, tag, source=0, category='any', order='count', limit=30):
        """
            tag         (String)
            source      (Int)       Adhere to general format
            category    (String)    general, artist, copyright, character
            order       (String)    Either: 'name', 'date', 'count'
            limit       (Int)       Estimating each tag containing 20 chars. In total would be 1000 chars for 30 tags.

            Returning a list (no result/OK result), or False (site_not_supported)
        """

        # DANBOORU
        if source == 0:
            content = []

            # Prep
            if '*' not in tag: tag = '*{}*'.format(tag)
            try: category = self.CATEGORY_INDEX[category]
            except KeyError: category = 0
            query = """tags.json?search[name_or_alias_matches]={}&search[category]={}&search[order]={}&search[hide_empty]=yes""".format(tag, category, order)

            for page in range(limit//self.TAGS_PER_PAGE[source] + (1 if limit%self.TAGS_PER_PAGE[source] else 0)):
                await asyncio.sleep(0)

                async with self.session.get('{}/{}'.format(self.config[self.config_currentPlaylist]['site'], query)) as resp:
                    content = content + await resp.json()
                    print(f"""<*> RECEIVED {len(content)} tags! (p={page}) (q="{resp.url}")""")
                    return content          # content is list

        # YANDERE
        elif source == 3:
            content = []

            # Prep
            if '*' not in tag: tag = '*{}*'.format(tag)
            try: category = self.CATEGORY_INDEX[category]
            except KeyError: category = 0
            query = """tag.json?name={}&type={}&order={}&limit={}""".format(tag, category, order, limit)

            for page in range(limit//self.TAGS_PER_PAGE[source] + (1 if limit%self.TAGS_PER_PAGE[source] else 0)):
                await asyncio.sleep(0)

                async with self.session.get('{}/{}'.format(self.config[self.config_currentPlaylist]['site'], query)) as resp:
                    content = content + await resp.json()
                    print(f"""<*> RECEIVED {len(content)} tags! (p={page}) (q="{resp.url}")""")
                    return content          # content is list

        # Site_not_supported
        else:
            return False

        

    async def redditRequest(self, base_query, page=1):
        count = 1
        lastPost = ''

        while True:
            # print("redQuest 0")
            async with self.session.get('{}/{}{}'.format(self.config[self.config_currentPlaylist]['site'], base_query, (f"&after={lastPost}" if lastPost else ''))) as resp:
                # print("redQuest 1")
                content = await resp.json()
                # print("redQuest 2")
                if (page - count):
                    lastPost = content['data']['children'][-1]['data']['name']
                else:
                    return content['data']['children']      # List of posts
                # print("redQuest 3")
            await asyncio.sleep(0)

            count += 1

    async def redditToPool(self, content):
        """
            DICT {url, title, subreddit_name_prefixed}
        """

        temp = []
        for p in content:
            # print(p)
            # if not p['data']['is_reddit_media_domain']: continue
            temp.append({
                "url": p['data']['url'],
                "title": p['data']['title'],
                "subreddit": p['data']['subreddit']
            })
        return temp

    async def doujinshiisToPool(self, doujins):
        """
            DICT {url, page, doujinshiiOrder, tags}
        """

        temp = []
        dOrder = 0
        random.shuffle(doujins)
        for d in doujins:
            if set(self.config[self.config_currentPlaylist]['blacklist']).intersection(d.tags): continue
            temp.append(self.doujinshiiDictFormatter(f"""<n> **[ID:**`{d.magic}`**]** ({d.pages} pages) ```css
{d.name}
⠀```""", -1, len(doujins) - dOrder, d.tags))
            page = 0
            await asyncio.sleep(0)
            try:
                while True:
                    await asyncio.sleep(0)
                    try: temp.append(self.doujinshiiDictFormatter(d[page], d.pages - page, len(doujins) - dOrder, d.tags))
                    except IndexError: break
                    page += 1
            except: print(traceback.format_exc())
            dOrder += 1
        return temp
    
    def doujinshiiDictFormatter(self, url, page, doujinshiiOrder, tags):
        return {
            "url": url,
            "page": page,
            "doujinshiiOrder": doujinshiiOrder,
            "tags": tags
        }

    def getConfig(self, fpConfig):
        try:
            with open(fpConfig) as f:
                return json.load(f)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            print('<!> File not found! (path="{}")'.format(fpConfig))
            return False

    def updateConfig(self, obj, fpConfig):
        # try:
        with open(fpConfig, mode='w') as f:
            ujson.dump(obj, f, indent=4)
        # except
        print("<*> UPDATED config!")

    def setTag(self, tag):
        """
            Set the tag of current playlist

            (List)      Tag
        """
        try:
            self.IN_USED = True
            if self.config[self.config_currentPlaylist]['site'] in self.infiniteTag: self.config[self.config_currentPlaylist]['tag'] = tag
            else: self.config[self.config_currentPlaylist]['tag'] = tag[0:2]
            self.config[self.config_currentPlaylist]['page'] = 1
            self.RESET_POOL = True
        finally:
            self.IN_USED = False

    def setPage(self, page_number):
        """
            Set the tag of current playlist

            (List)      Tag
        """
        try:
            self.IN_USED = True
            self.config[self.config_currentPlaylist]['page'] = int(page_number)
            self.RESET_POOL = True
        finally:
            self.IN_USED = False

    def setSite(self, site):
        try:
            self.IN_USED = True
            self.config[self.config_currentPlaylist]['site'] = site
            self.setTag(self.default_tag[self.config[self.config_currentPlaylist]['site']])
            self.RESET_POOL = True
        finally:
            self.IN_USED = False

    async def mangaSkip(self, manga=1):
        """
            for skipping manga in nhentai
        """

        for _ in range(manga):
            while True:
                await asyncio.sleep(0)
                if self.pool[0]['page'] != -1:
                    self.pool.pop(0)
                else: break

    async def inUsedCheck(self):
        loop_count = 0          # loop_safe=4
        while self.IN_USED:
            await asyncio.sleep(1)
            loop_count += 1
            if loop_count == 4: return False
        return True

    def str_time_prop(self, start, end, format, prop):
        """
        SOURCE: @Tom_Alsberg (https://stackoverflow.com/questions/553303/generate-a-random-date-between-two-other-dates)

        Get a time at a proportion of a range of two formatted times.

        start and end should be strings specifying times formated in the
        given format (strftime-style), giving an interval [start, end].
        prop specifies how a proportion of the interval to be taken after
        start.  The returned time will be in the specified format.
        """

        stime = time.mktime(time.strptime(start, format))
        etime = time.mktime(time.strptime(end, format))

        ptime = stime + prop * (etime - stime)

        return time.strftime(format, time.localtime(ptime))


    def random_date(self, start, end, prop, format='%Y-%m-%d'):
        return self.str_time_prop(start, end, format, prop)
