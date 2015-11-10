from drawquest.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group,
                                           create_comment, create_staff,
                                           create_quest, create_current_quest, create_quest_comment)
from canvas.exceptions import ServiceError, ValidationError
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.stars import models as star_models
from services import Services, override_service
from apps.activity.redis_models import ActivityStream
from drawquest.activities import StarredActivity, FolloweePostedActivity


class TestActivities(CanvasTestCase):
    def after_setUp(self):
        self.user = create_user()
        self.actor = create_user()

    def test_actor_avatar(self):
        avatar = create_content()
        self.api_post('/api/user/change_avatar', {'content_id': avatar.id}, user=self.actor)

        comment = create_quest_comment(author=self.user)
        star_models.star(self.actor, comment)

        sticker = comment.stickers.all()[0]
        stream = ActivityStream(self.user.id, activity_types={StarredActivity.TYPE: StarredActivity})
        activity = StarredActivity.from_sticker(self.actor, sticker)
        stream.push(activity)

        activity, _ = list(self.user.redis.activity_stream)
        self.assertTrue('avatar_url' in activity.to_client()['actor'])

    def test_followee_posted(self):
        self.user.follow(self.actor)
        comment = create_quest_comment(author=self.actor)

        stream = ActivityStream(self.user.id, activity_types={FolloweePostedActivity.TYPE: FolloweePostedActivity})
        activity = FolloweePostedActivity.from_comment(self.actor, comment)
        stream.push(activity)

        activity, _ = list(self.user.redis.activity_stream)
        self.assertEqual(activity.to_client()['comment_id'], comment.id)

    def test_cache_invalidation(self):
        def get_items():
            return self.api_post('/api/activity/activities', user=self.user)['activities']

        original_len = len(get_items())

        self.user.follow(self.actor)
        comment = create_quest_comment(author=self.actor)

        stream = ActivityStream(self.user.id, activity_types={FolloweePostedActivity.TYPE: FolloweePostedActivity})
        activity = FolloweePostedActivity.from_comment(self.actor, comment)
        stream.push(activity)

        self.assertEqual(len(get_items()), original_len + 1)
 
