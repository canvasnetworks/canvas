from cachecow.cache import invalidate_namespace
from django.dispatch import Signal


current_quest_changed = Signal(providing_args=['instance'])

current_quest_changed.connect(lambda sender, instance, **kwargs: invalidate_namespace('quests'),
                                      dispatch_uid='current_quest_changed_invalidate_namespace', weak=False)

