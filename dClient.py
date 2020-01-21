import aiohttp
import asyncio
import random
import time
import datetime
import json

import ujson



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
                    'tag': self.default_tag,
                    'page': 1,
                    'rating': 'explicit'
                }
            }
            self.updateConfig(self.config, self.fpConfig)
            print('<*> Config not found, so one is created!')
        else: self.config = resp
        self.config_currentPlaylist = self.config['aaaaa']

        self.pool = {}          # Each dClient has ONLY ONE pool, and ONLY stored in cache. Switching playlist means pool got deleted as well.

    # def __del__(self):
    #     await self.session.close()



    async def getPost(self, tags=None, page=None, limit='1000'):
        """
            (Str)    limit        Max=1000
            (List)   Tag          Max=2
            (Int)    Page
        """
        if int(limit) > 1000: limit = '1000'
        elif int(limit) < 0: limit = '1'
        if page == None: page = str(self.config[self.config_currentPlaylist]['page'])
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
            return content

    async def poolFetch(self, first=False):
        """
            Randomly fetch a response DICT from pool.
            If pool is empty, create one, using current playlist's config
        """
        
        self.IN_USED = True
        try:
            if self.RESET_POOL:
                self.pool = await self.getPost()
                if not self.pool:
                    self.setTag(self.default_tag)
                    self.pool = await self.getPost()
                    print('<*> Query is exhausted. Set back to default tag.')
                self.updateConfig(self.config, self.fpConfig)
                self.RESET_POOL = False
                print(f"<*> Resetting pool... (tag={self.config[self.config_currentPlaylist]['tag']})")
                return self.pool.pop(random.choice(range(len(self.pool))))

            try:
                return self.pool.pop(random.choice(range(len(self.pool))))
            except IndexError:
                if self.ACTIVATED or first:
                    self.config[self.config_currentPlaylist]['page'] += 1
                    print('<*> Pool is empty. Re-filling with new page...')
                else:
                    self.ACTIVATED = True
                    print('<*> Pool is empty. Re-filling...')
                self.pool = await self.getPost()
                if not self.pool:
                    self.setTag(self.default_tag)
                    self.config[self.config_currentPlaylist]['page'] = 1
                    self.pool = await self.getPost()
                    print('<*> Query is exhausted. Set back to default tag.')
                self.updateConfig(self.config, self.fpConfig)
                return self.pool.pop(random.choice(range(len(self.pool))))
            finally:
                self.IN_USED = False
        finally:
            self.IN_USED = False



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
