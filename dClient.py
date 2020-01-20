import aiohttp
import asyncio
import random

import ujson
import json



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
        if not default_tag: self.default_tag = ['yuri', 'ahegao']
        else: self.default_tag = default_tag
        self.session = aiohttp.ClientSession(json_serialize=ujson.dumps)
        self.fpConfig = fpConfig
        resp = self.getConfig(self.fpConfig)
        if not resp:
            self.config = {
                'aaaaa': 'default',          # current playlist. sorting.
                'default': {
                    'tag': self.default_tag,
                    'page': 1
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
        if tags: tag = '+'.join(tags[0:2])
        else:
            if not self.config[self.config_currentPlaylist]['tag']: self.config[self.config_currentPlaylist]['tag'] = self.default_tag
            tag = '+'.join(self.config[self.config_currentPlaylist]['tag'])

        async with self.session.get('https://danbooru.donmai.us/posts.json?tags={}&limit={}&page={}'.format(tag, limit, page)) as resp:
            content = await resp.json()
            print(f"<*> GET {len(content)} posts! (p={page})")
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
                self.config[self.config_currentPlaylist]['page'] = 1
                self.updateConfig(self.config, self.fpConfig)
                self.RESET_POOL = False
                print(f"<*> Resetting pool... (tag=<{self.config[self.config_currentPlaylist]['tag']}>)")
                return self.pool.pop(random.choice(range(len(self.pool))))            

            try:
                return self.pool.pop(random.choice(range(len(self.pool))))
            except IndexError:
                if self.ACTIVATED or first:
                    self.ACTIVATED = True
                    self.config[self.config_currentPlaylist]['page'] += 1
                    print('<*> Pool is empty. Re-filling with new page...')
                else:
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