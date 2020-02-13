import aiohttp
import asyncio
import random
import time
import datetime
import json

import ujson
import nhentai



class dClient:
    """
        To use, simply use <POOLFETCH>
        To re-fill pool, use <GETPOST>
        To set tag, please use setter setTag()
    """

    def __init__(self, fpConfig='dClient_config.json', default_tag=None):
        """
            (List)      default_tag
        """

        self.ACTIVATED = False
        self.RESET_POOL = False
        self.IN_USED = False
        if not default_tag: self.default_tag = ['random']
        else: self.default_tag = default_tag
        self.session = aiohttp.ClientSession(json_serialize=ujson.dumps)
        self.fpConfig = fpConfig
        resp = self.getConfig(self.fpConfig)
        if not resp:
            self.config = {
                'aaaaa': 'default',          # current playlist. sorting.
                'default': {
                    'site': 'https://danbooru.donmai.us',
                    'rating': 'explicit',
                    'tag': self.default_tag,
                    'page': 1,
                    "blacklist":[
                        "guro",
                        "scat"
                    ]
                },
                'default_prototype': {
                    'site': 'https://danbooru.donmai.us',
                    'rating': 'explicit',
                    'tag': self.default_tag,
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

    # def __del__(self):
    #     await self.session.close()



    async def getPost(self, tags=None, page=None, limit='1000', source=0):
        """
            (Str)    limit        Max=1000
            (List)   Tag          Max=2
            (Int)    Page
            (int)    source       0==danbooru    1==nhentai
        """
        print("into getPost")
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
                    if not self.config[self.config_currentPlaylist]['tag']: self.config[self.config_currentPlaylist]['tag'] = self.default_tag
                    # QUERY: Random
                    if self.config[self.config_currentPlaylist]['tag'] == ['random']:
                        tag = '?random=true'
                    else:
                        tag = 'tags={}'.format('+'.join(self.config[self.config_currentPlaylist]['tag']))
                query = 'posts.json?{}&limit={}&page={}&rating={}'.format(tag, limit, page, self.config[self.config_currentPlaylist]['rating'])

            async with self.session.get('{}/{}'.format(self.config[self.config_currentPlaylist]['site'], query)) as resp:
                content = await resp.json()
                print(f"""<*> GET {len(content)} posts! (p={page}) (q="{resp.url}")""")
                return content          # content is list

        # NHENTAI
        else:
            print("getPost 1")
            if not tags: tags = self.config[self.config_currentPlaylist]['tag']
            print("getPost 2")
            a = nhentai.search(' '.join(tags), page=page)
            print(a)
            return await self.doujinshiisToPool(a)

    async def poolFetch(self, first=False, order=0, source=0):
        """
            Randomly fetch a response DICT from pool.
            If pool is empty, create one, using current playlist's config

            (int) order            0==random   1==chronical
            (int) source           0==danbooru    1==nhentai
        """
        
        self.IN_USED = True
        print("into fetch")
        try:
            if self.RESET_POOL:
                print("reseting pool 1")
                self.pool = await self.getPost(source=source)
                print("reseting pool 2")
                if not self.pool:
                    print("reseting pool 3")
                    self.setTag(self.default_tag)
                    self.pool = await self.getPost(source=source)
                    print('<*> Query is exhausted. Set back to default tag.')
                print("reseting pool 4")
                self.updateConfig(self.config, self.fpConfig)
                print("reseting pool 5")
                self.RESET_POOL = False
                print(f"<*> Resetting pool... (tag={self.config[self.config_currentPlaylist]['tag']})")
                if order: return self.pool.pop(0)
                else: return self.pool.pop(random.choice(range(len(self.pool))))

            try:
                print(self.pool)
                print("fetch index 1")
                if order:
                    print("fetch in order")
                    return self.pool.pop(0)
                else:
                    print("fetch in random")
                    return self.pool.pop(random.choice(range(len(self.pool))))
                print("fetch index 2")
            except IndexError:
                print("fetch index 3")
                if self.ACTIVATED or first:
                    print("fetch index 4")
                    self.config[self.config_currentPlaylist]['page'] += 1
                    print('<*> Pool is empty. Re-filling with new page...')
                else:
                    print("fetch index 5")
                    self.ACTIVATED = True
                    print('<*> Pool is empty. Re-filling...')
                print("fetch index 6")
                self.pool = await self.getPost(source=source)
                print("fetch index 7")
                if not self.pool:
                    print("fetch index 8")
                    self.setTag(self.default_tag)
                    print("fetch index 9")
                    self.config[self.config_currentPlaylist]['page'] = 1
                    self.pool = await self.getPost(source=source)
                    print('<*> Query is exhausted. Set back to default tag.')
                print("fetch index 10")
                self.updateConfig(self.config, self.fpConfig)
                print("fetch index 11")
                if order: return self.pool.pop(0)
                else: return self.pool.pop(random.choice(range(len(self.pool))))
        finally:
            print("finishing fetch")
            self.IN_USED = False



    async def doujinshiisToPool(self, doujins):
        """
            DICT {url, page, doujinshiiOrder}
        """

        temp = []
        dOrder = 0
        print(doujins)
        for d in doujins:
            print(d.magic, d.name, d.pages, dOrder, d.tags)
            temp.append(self.doujinshiiDictFormatter(f"""<n> **[**`{d.magic}`**]** "{d.name}" ({d.pages} pages)""", -1, dOrder, d.tags))
            page = 0
            await asyncio.sleep(0)
            print("before pack")
            while True:
                await asyncio.sleep(0)
                try:
                    print(d)
                    print(page)
                    print(d[page])
                    print(d.pages)
                    print(page)
                    print(dOrder)
                    print(d.tags)
                    print(self.doujinshiiDictFormatter(d[page], d.pages - page, dOrder, d.tags))
                    temp.append(self.doujinshiiDictFormatter(d[page], d.pages - page, dOrder, d.tags))
                except IndexError:
                    print("breaking...")
                    break
                page += 1
            print("after pack")
            dOrder += 1
        print('EXTRACTING PACK -------')
        print(len(temp))
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
            self.config[self.config_currentPlaylist]['tag'] = tag[0:2]
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
            self.RESET_POOL = True
        finally:
            self.IN_USED = False

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


    def random_date(self, start, end, prop):
        return self.str_time_prop(start, end, '%Y-%m-%d', prop)
