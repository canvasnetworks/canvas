from cachecow.cache import invalidate_namespace
from django.dispatch import Signal

comment_freeze_ts_changed = Signal()

comment_freeze_ts_changed.connect(
    lambda sender, **kwargs: invalidate_namespace('comments'),
    dispatch_uid='freeze_ts_changed', weak=False
)

