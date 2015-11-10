import json
import uuid

import requests

PASSWORD = 'testpassword'
QUEST_ID = 658

PLAYBACK_DATA = ''

TEST_USERNAME = 'test_account__'
TEST_PASSWORD = 'testaccount'


class ApiError(Exception):
    pass


class HttpError(Exception):
    pass


class ApiConsumer(object):
    def __init__(self):
        self.session_id = None

    def call(self, endpoint, params={}):
        payload = json.dumps(params)
        headers = {
            'content-type': 'application/json',
        }

        if self.session_id:
            headers['X-SESSIONID'] = self.session_id

        ret = requests.post('https://api.example.com/' + endpoint, data=payload, headers=headers)

        if ret.status_code != 200:
            raise HttpError(ret.status_code)

        if not ret.json.get('success'):
            raise ApiError(ret.json)

        return ret.json

    def signup(self, username=None):
        if not username:
            username = '_TEST_' + str(uuid.uuid4())[-10:].replace('-', '_')

        ret = self.call('auth/signup', {
            'username': username,
            'email': '{}@example.example'.format(username),
            'password': PASSWORD,
        })

        self.session_id = ret['sessionid']

    def heavy_state_sync(self):
        return self.call('heavy_state_sync')

    def onboarding_quest(self):
        return self.call('quests/onboarding')

    def quest_comments(self, quest_id):
        return self.call('quests/comments', {'quest_id': quest_id})


class DrawquestTransaction(object):
    def __init__(self):
        self.custom_timers = {}


def main(trans_cls):
    trans = trans_cls()
    trans.run()
    print trans.custom_timers

