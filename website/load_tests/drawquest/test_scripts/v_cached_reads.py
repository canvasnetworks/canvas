import time

from utils import *


class Transaction(DrawquestTransaction):
    def run(self):
        api = ApiConsumer()

        t2 = time.time()
        onboarding_quest = api.onboarding_quest()
        self.custom_timers['Onboarding_Quest'] = time.time() - t2

        t3 = time.time()
        #api.quest_comments(onboarding_quest['quest']['id'])
        #self.custom_timers['Onboarding_Quest_Comments'] = time.time() - t3
        api.call('economy/rewards')
        self.custom_timers['Rewards'] = time.time() - t3

        # Taps Quests (Quest Homepage).
        t4 = time.time()
        api.call('quests/current')
        self.custom_timers['Current_Quest'] = time.time() - t4

        t5 = time.time()
        api.call('quests/archive')
        self.custom_timers['Quest_Archive'] = time.time() - t5

if __name__ == '__main__':
    main(Transaction)

