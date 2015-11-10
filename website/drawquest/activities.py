from website.apps.activity.base_activity import BaseActivity


class WelcomeActivity(BaseActivity):
    TYPE = 'welcome'


class StarredActivity(BaseActivity):
    TYPE = 'starred'
    FORCE_ANONYMOUS = False

    @classmethod
    def from_sticker(cls, actor, comment_sticker):
        comment = comment_sticker.comment
        comment_details = comment_sticker.comment.details()
        data = {
            'thumbnail_url': comment_details.reply_content.get_absolute_url_for_image_type('activity'),
            'comment_id': comment_details.id,
            'quest_id': comment.parent_comment_id,
        }
        return cls(data, actor=actor)


class PlaybackActivity(BaseActivity):
    TYPE = 'playback'
    FORCE_ANONYMOUS = False

    @classmethod
    def from_comment(cls, actor, comment):
        comment_details = comment.details()
        data = {
            'thumbnail_url': comment_details.reply_content.get_absolute_url_for_image_type('activity'),
            'comment_id': comment_details.id,
            'quest_id': comment.parent_comment_id,
        }
        return cls(data, actor=actor)


class FolloweePostedActivity(BaseActivity):
    TYPE = 'followee_posted'
    FORCE_ANONYMOUS = False

    @classmethod
    def from_comment(cls, actor, comment):
        from website.apps.activity.models import Activity

        comment_details = comment.details()

        data = {
            'thumbnail_url': comment_details.reply_content.get_absolute_url_for_image_type('activity'),
            'comment_id': comment_details.id,
            'quest_id': comment.parent_comment_id,
        }

        # Prime the Activity DB instance, to be shared across recipients.
        key = comment_details.id
        try:
            db_activity = Activity.objects.get(activity_type=cls.TYPE, key=key)
            data['id'] = db_activity.id
        except Activity.DoesNotExist:
            pass

        return cls(data, actor=actor)

