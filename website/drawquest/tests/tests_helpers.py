from canvas.tests.tests_helpers import *
from canvas.tests import tests_helpers as canvas_tests_helpers
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.quests.models import Quest
from drawquest.apps.playback.models import PlaybackData
from drawquest.apps.quest_comments.models import QuestComment

def create_user(*args, **kwargs):
    return canvas_tests_helpers.create_user(*args, user_cls=User, **kwargs)

def create_staff(*args, **kwargs):
    return canvas_tests_helpers.create_staff(*args, user_cls=User, **kwargs)

def create_quest(title='Quest title'):
    content = create_content()
    cmt = create_comment(reply_content=content, title=title)
    return Quest.objects.get(id=cmt.id)

def create_scheduled_quest(**kwargs):
    quest = create_quest(**kwargs)
    return quest.schedule(0)

def create_current_quest(**kwargs):
    scheduled = create_scheduled_quest(**kwargs)
    scheduled.set_as_current_quest()
    return scheduled.quest

def create_quest_comment(quest=None, author=None, playback_data=None):
    if author is None:
        author = create_user()

    if quest is None:
        quest = create_quest()

    content = create_content()
    cmt = create_comment(parent_comment=quest, reply_content=content, author=author)

    cmt = QuestComment.objects.get(id=cmt.id)

    if playback_data is not None:
        PlaybackData.create_with_json(cmt, playback_data)

    return cmt

