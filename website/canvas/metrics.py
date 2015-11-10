import datetime

from django.conf import settings

from canvas import util
from canvas.redis_models import RedisSet, RedisKey, redis, ThresholdMetric

from services import Services


class Metric(object):
    def __init__(self, name, alarm_minutes, category, threshold=None, ignore_from_api=False):
        self.name = name
        self.basekey = 'metrics:' + name
        self.alarm_minutes = alarm_minutes
        self.category = category
        self.threshold = threshold
        self.ignore_from_api = ignore_from_api

    def __repr__(self):
        return self.name

    def record(self, request_or_user, **metadata):
        from canvas import fact
        # A unique key per day.

        if hasattr(request_or_user, 'user'):
            request = request_or_user
            user = request.user
        else:
            request = None
            user = request_or_user

        def _record(timestamp_key):
            if request:
                RedisSet(timestamp_key + ":unique_ips").sadd(util.ip_to_int(request.META.get('REMOTE_ADDR')))
            if user:
                RedisSet(timestamp_key + ":uniques").sadd(user.id)
            RedisKey(timestamp_key + ":count").incr(1)

        _record(self.basekey + ":" + Services.time.strftime("%Y.%m.%d"))
        _record(self.basekey + ":" + Services.time.strftime("%Y.%m.%d.%H"))
        self.timestamp_key.set(str(Services.time.time()))

        if self.threshold:
            ThresholdMetric(self.basekey, threshold=self.threshold, minutes=self.alarm_minutes).increment()

        if metadata.get('record_fact', True):
            fact.record('metric', request_or_user, dict(metadata, metric=self.name))

    def daykey(self, day, type):
        return self.basekey + ":" + day.strftime("%Y.%m.%d") + ":" + type

    def uniques(self, day, ip=False):
        return RedisSet(self.daykey(day, 'uniques' if not ip else 'unique_ips'))

    def daily_count(self, day):
        return int(RedisKey(self.daykey(day, 'count')).get() or 0)

    def daily_uniques(self, *args):
        return int(self.uniques(*args).scard() or 0)

    def hourly_count(self, datetime):
        return int(RedisKey(self.basekey + ":" + datetime.strftime("%Y.%m.%d.%H") + ":count").get() or 0)

    def hourly_uniques(self, datetime, ip=False):
        return int(RedisSet(self.basekey + ":"
                            + datetime.strftime("%Y.%m.%d.%H")
                            + (":uniques" if not ip else ":unique_ips")).scard()
                   or 0)

    def uniques_breakdown(self, day):
        return [int(n) for n in self.uniques(day).smembers()]

    def is_on_record(self, day, user):
        return self.uniques(day).sismember(user.id)

    def trailing_uniques(self, days, key=None):
        union_keys = [self.daykey(day, 'uniques') for day in Metric.trailing_days(days)]
        if key:
            redis.sunionstore(key, union_keys)
            return key
        else:
            return redis.sunion(union_keys)

    def branch_count(self, experiment_name, branch_name):
        return int(RedisKey(self.basekey + ":" + "experiment:%s:%s:count" % (experiment_name, branch_name)).get()
                   or 0)

    @staticmethod
    def trailing_days(days):
        for i in reversed(range(days)):
            yield datetime.datetime.today() - datetime.timedelta(i)

    @property
    def timestamp_key(self):
        return RedisKey(self.basekey + ":last_timestamp")

    def get_threshold_count(self):
        if self.threshold:
            metric = ThresholdMetric(self.basekey, threshold=self.threshold, minutes=self.alarm_minutes)
            return metric.amount()
        return None

    def check_threshold(self, doubled=False):
        if self.threshold:
            metric = ThresholdMetric(self.basekey, threshold=self.threshold, minutes=self.alarm_minutes)
            return metric.is_okay(doubled)
        return True


class Metrics(object):
    """
    This is a heuristic of how often certain actions should be triggered on the site.
    We use this to page the team when a certain action does not happen within the allotted minutes.
    This can signal that the site is a broken in a way that was not caught by the tests, such as
    broken JS or HTML.

    The tuples are: metric name, minutes without a metric before we page, optional: required events
    triggered per timespan to succeed.

    You may also have an optional 2nd argument which is whether the /api/metric/record endpoint should ignore
    this call, for when the client duplicates server-side metrics.
    """
    def td(**kwargs):
        """
        make a nice way to specify alarm times, ala:
            td(minute=10)
            td(days=3)
            td(hours=8)
        """
        return int(datetime.timedelta(**kwargs).total_seconds() / 60)

    if settings.PROJECT == 'canvas':
        names = (
            ('views', [
                ('view', td(minutes=12)),
                ('logged_in_infinite_scroll', td(minutes=90)),
                ('logged_out_infinite_scroll', td(minutes=160)),
                ('get_new_replies', td(hours=2)),
                ('logged_out_view', td(minutes=45)),
                ('share_redirect', None),
                ('large_thread_view', None),
                ('scrolled_to_bottom', None),
                ('page_ready', td(minutes=3)),
                ('visit_from_invite', None),
                ('api_call', None),
            ]),
            ('bad', [
                ('exception', td(minutes=10), -30),
                ('file_not_found', None),
                ('sticker_ratelimit', None),
                ('flag_ratelimit', None),
                ('fact_record_fail', None),
                ('image_missing', None),
                ('logged_out_reply_dropped', None),
                ('group_404', None),
                ('signup_form_invalid', None),
                ('facebook_signed_request_error', None),
                ('timeline_sticker_error', None),
                ('timeline_remix_error', None),
                ('timeline_complete_error', td(hours=4), -5),
            ]),
            ('stickering', [
                ('sticker', td(hours=2), 2),
                ('logged_out_sticker', None),
                ('shop_sticker_purchased', None),
                ('shop_sticker_used', None),
                ('seasonal_sticker_used', None),
            ]),
            ('following', [
                ('follow_user', None),
                ('unfollow_user', None),
                ('follow_tag', None),
                ('unfollow_tag', None),
                ('follow_thread', None),
                ('unfollow_thread', None),
            ]),
            ('alarms', [
                ('op', td(hours=12)),
                ('group_post', None),
                ('signup_main', td(days=7)),
                ('signup_prompt', None),
                ('draw_from_scratch', td(hours=12)),
                ('remix_stamp_used', td(hours=16)),
                ('remix_text_used', td(hours=16)),
            ]),
            ('core interactions', [
                ('post', td(hours=24)),
                ('attempted_remix', td(hours=24)),
                ('remix', td(hours=24)),
                ('text_reply', td(hours=16)),
                ('image_reply', td(hours=16)),
                ('remix_tool_used', None),
            ]),
            ('logged out interactions', [
                ('logged_out_post', None),
                ('sticker_attempt', None),
            ]),
            ('interactions', [
                ('delete_post', td(hours=24)),
                ('claim_post', td(hours=36)),
                ('flag', td(hours=36)),
                ('flag_anonymous_post', None),
                ('pin', None),
                ('downvote_action', td(hours=24)),
                ('follow', None),
                ('new_group', None),

                ('unsubscribe_email_address', None),
                ('unsubscribe_action', None),
                ('unsubscribe_all', None),
                ('mute_thread', None),

                ('posted_thread', None),
                ('posted_thread_from_popup', None),
                ('post_thread_page_view', None),
                ('start_remix_from_disk', None),
                ('start_remix_from_draw', td(hours=24)),
                ('start_remix_from_url',  td(hours=24)),

                ('epic_sticker_message', None),

                ('hide_comment', None),
                ('hide_thread', None),
            ]),
            ('uploads', [
                ('upload_attempt', td(hours=12)),
                ('upload_fail', None),
                ('upload_success', td(hours=12)),
                ('publish', td(hours=8)),
                #('upload', td(minutes=30)), # Dead, replaced by 'publish'
            ]),
            ('growth', [
                ('invite', None), # Don't get enough of these to alert on them in any reliable fashion :(
                ('signup', td(hours=16)),
                ('signup_second_try', None),
                ('login_wall', td(hours=12)),

                ('invite_remixer', None),
                ('invite_facebook_friends', None),
                ('invite_facebook_friends_to_remix', None),
            ]),
            ('share', [
                ('share', None),
                ('facebook', td(days=2)),
                ('twitter', td(days=3)),
                ('stumbleupon', None),
                ('tumblr', td(days=3)),
                ('reddit', None),
                ('email', None),
                ('timeline_sticker', None),
                ('timeline_remix', None),
                ('timeline_complete', None),
            ]),
            ('click_tracking', [
                ('email_sent', None),
                ('email_clickthrough', None),
            ]),
            ('dummy_page_testing', [
                ('dummy_page_view', None),
                ('dummy_page_click', None),
                ('dummy_page_scroll', None),
            ]),
            ('public_api', [
                ('api_successful_request', None),
                ('api_failed_request', None),
                ('api_rate_limited', None),
                ('api_items_limited', None),
                ('api_comment', None),
                ('api_user', None),
                ('api_group', None),
                ('api_documentation', None),
            ]),
            ('onboarding', [
                ('onboarding_funnel_start', None),
                ('signup_form_view', None),
                ('onboarding_groups', None),
                ('onboarding_invites', None),
                ('onboarding_welcome_tutorial_view', None),
                ('onboarding_finish', None),
            ]),
            ('monstermash', [
                ('random_monster_complete', None),
                ('skip_monster', None),
                ('no_more_monsters', None),
            ]),
            ('feed', [
                ('feed_infinite_scroll', None),
            ]),
            ('activity_stream', [
                ('activity_stream_infinite_scroll', None),
            ]),
        )
    elif settings.PROJECT == 'drawquest':
        names = (
            ('core interactions', [
                ('post', td(hours=72)),
            ]),
            ('interactions', [
                ('star', True, None),
                ('unstar', True, None),
                ('flag', True, None),
            ]),
            ('growth', [
                ('signup', True, None),
                ('share_redirect', None),

                ('tap_invite', None),
                ('send_invite_email', None),

                ('share_to_facebook', None),
                ('share_to_twitter', None),
            ]),
            ('following', [
                ('follow_user', True, None),
                ('unfollow_user', True, None),
            ]),
            ('misc', [
                ('api_call', None),

                ('view_quest_of_the_day_homepage', None),
                ('view_quest_of_the_day_editor', None),
                ('view_fte_homepage', None),
                ('view_fte_editor', None),
                ('view_fte_publish', None),
                ('view_fte_signup_success', None),
                ('view_editor', None),
                ('view_publish', None),
                ('view_coin_purchase_dialog', None),
                ('view_palette_purchase_dialog', None),
                ('view_own_profile', None),
                ('view_other_user_profile', None),
                ('view_gallery', None),
                ('view_editor', None),
                ('view_settings', None),
                ('view_basement', None),
                ('view_about', None),

                ('publish_comment', None),
                ('publish_quest_of_the_day', None),
                ('receive_quest_of_the_day_reaction', None),
                ('purchase_coins', None),
                ('purchase_palette', None),
                ('signup_with_facebook', None),
                ('associate_facebook', None),
                ('signup_with_email', None),
                ('share_to_timeline', True, None),
                ('signup_from_canvas', None),

                ('facebook_user_deauthorized', None),

                ('push_notification_sent', None),
            ]),
            ('web', [
                ('view', None),
                ('email_clickthrough', None),
            ]),
            ('bad', [
                ('exception', td(minutes=10), -30),
                ('flag_ratelimit', None),
                ('sticker_ratelimit', None),
                ('post_ratelimit', None),
                ('fact_record_fail', None),
                ('file_not_found', None),
                ('image_missing', None),
                ('facebook_signed_request_error', None),
                ('share_to_timeline_error', None),
            ]),
            ('email', [
                ('unsubscribe_email_address', None),
                ('unsubscribe_action', None),
                ('unsubscribe_all', None),
            ]),
            ('legacy', [
                ('sticker', None),
                ('activity_stream_infinite_scroll', None),
                ('large_thread_view', None),
                ('email_sent', None),
                ('logged_out_view', None),
                ('image_reply', None),
                ('remix_stamp_used', None),
                ('logged_out_view', None),
                ('op', None),
                ('publish', None),
            ]),
        )

def create_metrics(namespace, names, klass):
    namespace.all = {}
    for cat, names in names:
        for args in names:
            ignore_from_api = False
            if len(args) >= 2 and isinstance(args[1], bool):
                ignore_from_api = args[1]
                args = list(args)
                args.pop(1)

            if len(args) == 2:
                name, minutes = args
                m = klass(name, minutes, cat)
            elif len(args) == 3:
                name, minutes, threshold = args
                m = klass(name, minutes, cat, threshold=threshold, ignore_from_api=ignore_from_api)

            setattr(namespace, name, m)
            namespace.all[name] = m

create_metrics(Metrics, Metrics.names, Metric)

