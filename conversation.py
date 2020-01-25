import asyncio
import datetime
import ujson
import json
import os






class ConversationManager:
    def __init__(self, targetGuildID=None, targetChannelID=None, save_path=None):
        self.config = None
        try:
            self.loadConfig()
        # E: Config not found
        except (OSError, ValueError):
            self.config = {
                'targetGuildID': 0,
                'targetChannelID': 0,
                'currentSaveFile': 'dataConv_1.json',
                'timeInterval': 60,
                'bank_max_conv': 100
            }
            self.updateConfig(self.config)

        if targetGuildID: self.config['targetGuildID'] = targetGuildID
        if targetChannelID: self.config['targetChannelID'] = targetChannelID

        if save_path: self.save_path = save_path
        else: self.save_path = ('data', 'conversations', self.config['currentSaveFile'])

        self.bank_max_conv = self.config['bank_max_conv']
        self.bank = {}          # Structure        {'time_stamp_of_first_line': ConvesationObj}
        self.bankActive = {}

    async def msgListener(self, package):
        """
            Package     (Tuple)         (timestamp, user_ID, user_name, content)

            # Note:
            #      user_ID (int)
            #      timestamp (str)
            #      content (str)
        """
        timestamp, user_ID, user_name, content = package
        print(
            f"""
                A --- {self.bankActive}
                B --- {self.bank}
            """
        )

        # Check if user_id is already in an Acitve Conv
        rightnow = datetime.datetime.now()
        for ts, _ in self.bankActive.items():
            await asyncio.sleep(0)
            print((rightnow - datetime.datetime.strptime(self.bankActive[ts].timeline[-1][0][0], '%Y-%m-%d %H:%M:%S.%f')).total_seconds(), self.config['timeInterval'], (rightnow - datetime.datetime.strptime(self.bankActive[ts].timeline[-1][0][0], '%Y-%m-%d %H:%M:%S.%f')), self.bankActive[ts].timeline[-1][0][0])
            if user_ID in self.bankActive[ts].contributor:
                # Check time_interval
                if (rightnow - datetime.datetime.strptime(self.bankActive[ts].timeline[-1][0][0], '%Y-%m-%d %H:%M:%S.%f')).total_seconds() < self.config['timeInterval']:
                    self.bankActive[ts].record(timestamp, user_ID, user_name, content)
                    return True
                else:
                    # If conv's time_interval is out, lock it. Then, continue the search
                    self.lockConv(ts)
            elif (rightnow - datetime.datetime.strptime(self.bankActive[ts].timeline[-1][0][0], '%Y-%m-%d %H:%M:%S.%f')).total_seconds() > self.config['timeInterval']:
                self.lockConv(ts)
        
        # If user not in any Active Conv, pick one.
        try:
            ts = tuple(self.bankActive.keys())[-1]
            self.bankActive[ts].record(timestamp, user_ID, user_name, content)
            
        # If bankActive is empty, create new Conv.
        except IndexError:
            if len(self.bankActive) < self.bank_max_conv:
                self.bankActive[str(rightnow)] = Conversation(package={
                    'contributor': [user_ID],
                    'timeline': [[[timestamp, user_ID, user_name], [content]]]
                })
                return True
            else:
                return False

    def decode(self):
        with open(self.pathJoiner(self.save_path), mode='r') as f:
            return ujson.load(f)

    def loadData(self):
        raw = self.decode()
        for k, v in raw.items():
            self.bank[k] = Conversation(package=v)
        
    def saveData(self):
        raw = {}
        for k, v in self.bank.items():
            raw[k] = v.encode()
        with open(self.pathJoiner(self.save_path), mode='w', encoding='utf-8-sig') as f:
            json.dump(raw, f, ensure_ascii=False, indent=4)

    def loadConfig(self):
        with open(self.pathJoiner(('data', 'configConversation.json')), mode='r') as f:
            self.config = ujson.load(f)

    def updateConfig(self, obj):
        with open(self.pathJoiner(('data', 'configConversation.json')), mode='w') as f:
            ujson.dump(obj, f, indent=4)

    def pathJoiner(self, paths):
        path = paths[0]
        for p in paths[1:]:
            path = os.path.join(path, p)
        return path
    
    def lockConv(self, conv_ts):
        self.bankActive[conv_ts].fix()
        self.bank[conv_ts] = self.bankActive[conv_ts]
        del self.bankActive[conv_ts]







class Conversation:
    """
        Conversation does not deal anything with timestamp. Leave that to ConversationManager.

        A Conv with 0 max_contributor is an Active Conv. A Conv with a fixed max_contributor is a Locked Conv.
    """

    def __init__(self, package=None, max_contributor=0):
        self.max_contributor = max_contributor      # 0 means infinite.
                                                    # This number will be increased to the length of self.contributor after a while (~30s), by ConversationManager.
        self.contributor = []
        self.timeline = []          # Structure     [[[meta_data], [content]],..]      or      [[[time_stamp, user_ID, user_name], [line_1, line_2,..]],..]

        if package: self.decode(package)

        

    def encode(self):
        """
            Into JSON format.

            {
                "contributor": [],
                "timeline": [[meta_data], [content]]
            }

            # Note: timestamp must be str
        """
        return {
            "contributor": self.contributor,
            "timeline": self.timeline
        }

    def decode(self, package):
        """
            Act as a constructor/Adding data. Prefer JSON format.

            For structure, refer to <ENCODE>
        """
        self.contributor = package['contributor']
        self.timeline = package['timeline']

    def record(self, timestamp, user_id, user_name, content):
        # Contributor check
        if user_id not in self.contributor:
            if not self.max_contributor or (self.max_contributor and len(self.contributor) < self.max_contributor):
                self.contributor.append(user_id)
            else: return False
        
        # Metadata check
        if self.timeline[-1][0][1] == user_id:
            self.timeline[-1][1].append(content)
        else:
            self.timeline.append([[timestamp, user_id, user_name], [content]])

        return True

    def fix(self):
        self.max_contributor = len(self.contributor)
        

