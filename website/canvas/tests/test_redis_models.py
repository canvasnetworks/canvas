from random import random
from time import sleep

from canvas.redis_models import (redis, RedisLastBumpedBuffer, RedisHash, HashSlot, RedisCachedHash, RateLimit,
                                 KeyedSet, hint, hstr, hfloat, hbool, ThresholdMetric)
from canvas.tests.tests_helpers import create_user, FakeRequest, CanvasTestCase, AnonymousUser
from services import Services, override_service, FakeTimeProvider


class TestRedisLastBumpedBuffer(CanvasTestCase):
    def after_setUp(self):
        redis.delete('rblf_key')
        self.lbf = RedisLastBumpedBuffer('rblf_key', 3)

    def set_common_data(self):
        self.lbf.bump(1, 0.1)
        self.lbf.bump(2, 0.9)
        self.lbf.bump(3, 0.4)
        self.lbf.bump(4, 1.0)

    def test_bump_and_get_back_bumped_id(self):
        self.lbf.bump(10, 1.23)
        self.assertEquals([10], self.lbf[:])

    def test_bump_thrice_and_get_ids_in_decreasing_value_order(self):
        self.lbf.bump(10, 1.0)
        self.lbf.bump(11, 1.1)
        self.lbf.bump(9, 1.2)
        self.assertEquals([9, 11, 10], self.lbf[:])

    def test_bumped_four_times_and_get_top_3_ids(self):
        self.set_common_data()
        self.assertEquals([4, 2, 3], self.lbf[:])

    def test_get_the_top_2_via_slicing(self):
        self.set_common_data()
        self.assertEquals([4, 2], self.lbf[:2])
        self.assertEquals([4, 2], self.lbf[0:2])

    def test_get_the_the_back_2_via_slicing(self):
        self.set_common_data()
        self.assertEquals([2, 3], self.lbf[1:3])

    def test_ten_bumps_still_three_items(self):
        for x in range(10):
            self.lbf.bump(x, x)
        self.assertEquals([9,8,7], self.lbf[:])


class TestRedisHash(CanvasTestCase):
    def after_setUp(self):
        redis.delete('rh_key')
        self.rh = RedisHash('rh_key')

    def test_hincrby_ifsufficient_none(self):
        result = self.rh.hincrby_ifsufficient('balance', -5)
        self.assertEqual(result['success'], False)
        self.assertEqual(result['remaining'], 0)

    def test_hincrby_ifsufficient_enough(self):
        self.rh.hset('balance', 8)
        result = self.rh.hincrby_ifsufficient('balance', -5)
        self.assertEqual(result['success'], True)
        self.assertEqual(result['remaining'], 3)

    def test_hincrby_ifsufficient_justenough(self):
        self.rh.hset('balance', 5)
        result = self.rh.hincrby_ifsufficient('balance', -5)
        self.assertEqual(result['success'], True)
        self.assertEqual(result['remaining'], 0)

    def test_hincrby_ifsufficient_notquiteenough(self):
        self.rh.hset('balance', 4)
        result = self.rh.hincrby_ifsufficient('balance', -5)
        self.assertEqual(result['success'], False)
        self.assertEqual(result['remaining'], 4)


class TestRedisCachedHash(CanvasTestCase):
    def after_setUp(self):
        redis.delete('redis_object_key')
        self.hash = self.create_hash()

    def create_hash(self):
        return RedisCachedHash('redis_object_key', {
            'ifoo': hint(100),
            'sbar': hstr("default"),
            'bbaz': hbool(),
            'fqux': hfloat(),
        })

    def test_set_and_get(self):
        self.hash.sbar.set("testing")
        self.assertEquals(self.hash.sbar.get(), "testing")

    def test_setnx(self):
        self.assertFalse(self.hash.fqux.get())
        changed = self.hash.fqux.setnx(4)
        self.assertTrue(changed)
        self.assertEqual(self.hash.fqux.get(), 4)
        changed = self.hash.fqux.setnx(5)
        self.assertFalse(changed)
        self.assertEqual(self.hash.fqux.get(), 4)

    def test_delete(self):
        self.hash.sbar.set("testing")
        self.hash.sbar.delete()
        self.assertEquals(self.hash.sbar.get(), "default")

    def test_get_default(self):
        self.assertEquals(self.hash.ifoo.get(), 100)
        self.assertEquals(self.hash.sbar.get(), "default")

    def test_changes_persist(self):
        self.hash.sbar.set("baz")
        del self.hash
        self.hash = self.create_hash()
        self.assertEquals(self.hash.sbar.get(), "baz")

    def test_hint_coerces_to_and_from_int(self):
        self.hash.ifoo.set(50)
        del self.hash
        self.hash = self.create_hash()
        self.assertEquals(self.hash.ifoo.get(), 50)

    def test_hfloat_coerces_to_and_from_float(self):
        self.hash.fqux.set(0.125)
        del self.hash
        self.hash = self.create_hash()
        self.assertEquals(self.hash.fqux.get(), 0.125)

    def test_hbool_coerces_to_and_from_bool(self):
        self.hash.bbaz.set(False)
        self.assertFalse(self.hash.bbaz.get())

        self.hash.bbaz.set(True)
        self.assertTrue(self.hash.bbaz.get())

    def test_increment(self):
        self.hash.ifoo.set(50)
        self.hash.ifoo.increment(100)
        self.assertEquals(self.hash.ifoo.get(), 150)

    def test_increment_persists(self):
        self.hash.ifoo.set(50)
        self.hash.ifoo.increment(100)
        del self.hash
        self.hash = self.create_hash()
        self.assertEquals(self.hash.ifoo.get(), 150)

    def test_dictionary_access(self):
        self.hash['ifoo'].set(50)
        self.assertEquals(self.hash['ifoo'].get(), 50)
        self.assertEquals(self.hash.ifoo.get(), 50)

    def test_increment_ifsufficient(self):
        self.hash.ifoo.set(50)
        result = self.hash.ifoo.increment_ifsufficient(-100)

        self.assertEquals(result['success'], False)
        self.assertEquals(result['remaining'], 50)
        self.assertEquals(self.hash.ifoo.get(), 50)


class TestKeyedSet(CanvasTestCase):
    def after_setUp(self):
        self.prefix = "test_notification:"
        for key in redis.keys(self.prefix + "*"):
            redis.delete(key)

        self.q = KeyedSet(self.prefix)

    def test_add_to_queue(self):
        key = self.q.add('foo_bar')
        self.assertEqual(self.q.get(), {key: 'foo_bar'})

    def test_add_multiple_items_to_queue(self):
        expected = {}
        for value in ["one", "two", "three"]:
            key = self.q.add(value)
            expected[key] = value

        self.assertEqual(self.q.get(), expected)

    def test_remove_from_queue(self):
        key = self.q.add('frooba')
        self.q.remove(key)
        self.assertEqual(self.q.get(), {})


    def test_add_multiple_items_and_remove_one_from_queue(self):
        expected = {}

        remove_key = self.q.add("flux")

        for value in ["one", "two", "three"]:
            key = self.q.add(value)
            expected[key] = value

        self.q.remove(remove_key)

        self.assertEqual(self.q.get(), expected)

    def test_delete_twice_from_queue(self):
        key = self.q.add("foo")

        self.assertEqual(self.q.remove(key), True)
        self.assertEqual(self.q.remove(key), False)


class TestUserNotificationQueue(CanvasTestCase):
    def after_setUp(self):
        self.user = create_user()
        self.n = self.user.redis.notifications

    def test_send_notification(self):
        self.n.send({"foo": "bar"})
        self.assertEqual(self.n.get(), [{"foo": "bar", "nkey": 1}])

    def test_send_two_notifications(self):
        self.n.send({"foo": "bar"})
        self.n.send({"foo": "qux"})
        self.assertEqual(self.n.get(), [{"foo": "bar", "nkey": 1}, {"foo": "qux", "nkey": 2}])

    def test_send_three_notifications_and_acknowledge_middle_one(self):
        self.n.send({"step": "one"})
        ack_key = self.n.send({"step": "two"})
        self.n.send({"step": "three"})
        self.n.acknowledge(ack_key)
        self.assertEqual(self.n.get(), [{"step": "one", "nkey": 1}, {"step": "three", "nkey": 3}])

    def test_sending_notification_sends_message_over_channel(self):
        self.n.send({"what": "what"})
        self.assertEqual(self.user.redis.channel.get().values(),
                         [{"what": "what", "msg_type": "notification", "nkey": 1}])

    def test_acknowledge_returns_success(self):
        key = self.n.send({"you_got": "fuckyeah"})
        self.assertEqual(self.n.acknowledge(key), True)
        self.assertEqual(self.n.acknowledge(key), False)

    def test_acknowledge_sends_message_over_channel(self):
        key = self.n.send({})
        self.n.acknowledge(key)
        self.assertEqual(self.user.redis.channel.get().values()[-1], {"msg_type": "notification_ack", "nkey": key})


class TestRateLimiting(CanvasTestCase):
    def after_setUp(self):
        self.rl = RateLimit('test', 2, 100)

    def test_rate_limit_allows_one(self):
        self.assertTrue(self.rl.allowed())

    def test_rate_limit_allows_two(self):
        self.assertTrue(self.rl.allowed())
        self.assertTrue(self.rl.allowed())

    def test_rate_disallows_the_third(self):
        self.assertTrue(self.rl.allowed())
        self.assertTrue(self.rl.allowed())
        self.assertFalse(self.rl.allowed())

    def test_rate_limit_restarts_after_time(self):
        with override_service('time', FakeTimeProvider):
            self.assertTrue(self.rl.allowed())
            self.assertTrue(self.rl.allowed())

            Services.time.step(100)

            self.assertTrue(self.rl.allowed())
            self.assertTrue(self.rl.allowed())
            self.assertFalse(self.rl.allowed())

class TestThresholdMetric(CanvasTestCase):
    def test_threshold_initial_failure(self):
        mt = ThresholdMetric(str(random()), 5, 1)
        with override_service('time', FakeTimeProvider):
            self.assertFalse(mt.is_okay())

    def test_threshold_returns_to_success(self):
        mt = ThresholdMetric(str(random()), 5, 1)
        with override_service('time', FakeTimeProvider):
            self.assertFalse(mt.is_okay())
            mt.increment()
            Services.time.step(30)
            mt.increment()
            mt.increment()
            mt.increment()
            mt.increment()
            self.assertTrue(mt.is_okay())
            Services.time.step(50)
            self.assertFalse(mt.is_okay())
            mt.increment()
            self.assertTrue(mt.is_okay())

    def test_negative_threshold_returns_to_success(self):
        mt = ThresholdMetric(str(random()), -5, 1)
        with override_service('time', FakeTimeProvider):
            self.assertTrue(mt.is_okay())
            mt.increment()
            Services.time.step(30)
            mt.increment()
            mt.increment()
            mt.increment()
            mt.increment()
            self.assertFalse(mt.is_okay())
            Services.time.step(50)
            self.assertTrue(mt.is_okay())
            mt.increment()
            self.assertFalse(mt.is_okay())

    def test_threshold_doubles_appropriately(self):
        mt = ThresholdMetric(str(random()), 5, 1)
        with override_service('time', FakeTimeProvider):
            self.assertFalse(mt.is_okay())
            mt.increment()
            mt.increment()
            Services.time.step(30)
            mt.increment()
            mt.increment()
            Services.time.step(50)
            mt.increment()
            mt.increment()
            self.assertFalse(mt.is_okay())
            self.assertTrue(mt.is_okay(True))

    def test_negative_threshold_doubles_appropriately(self):
        mt = ThresholdMetric(str(random()), -5, 1)
        with override_service('time', FakeTimeProvider):
            self.assertTrue(mt.is_okay())
            mt.increment()
            mt.increment()
            self.assertTrue(mt.is_okay())
            Services.time.step(30)
            mt.increment()
            mt.increment()
            self.assertTrue(mt.is_okay())
            Services.time.step(50)
            mt.increment()
            mt.increment()
            self.assertTrue(mt.is_okay())
            self.assertFalse(mt.is_okay(True))

