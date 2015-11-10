import time

from utils import *


class Transaction(DrawquestTransaction):
    def run(self):
        api = ApiConsumer()

        t1 = time.time()

        # Onboarding flow.
        api.heavy_state_sync()
        onboarding_quest = api.onboarding_quest()
        api.call('quest_comments/rewards_for_posting', {'quest_id': onboarding_quest['quest']['id']})
        api.signup()
        api.heavy_state_sync()
        api.quest_comments(onboarding_quest['quest']['id'])
        #TODO upload
        api.call('quest_comments/post', {
            'quest_id': QUEST_ID,
            'content_id': '66c7f508180e0dab0b573792a56b0fc7beefbd2b',
        }) #TODO use uploaded one.
        #TODO api.call('playback/set_playback_data')
        api.heavy_state_sync()

        # Taps basement icon.
        api.call('activity/activities')

        # Taps Quests (Quest Homepage).
        api.call('quests/current')
        api.call('quests/archive')

        latency = time.time() - t1
        self.custom_timers['Onboarding_Timer'] = latency

if __name__ == '__main__':
    main()

