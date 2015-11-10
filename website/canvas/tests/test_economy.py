from canvas.tests.tests_helpers import CanvasTestCase, NotOkay, FakeRequest, create_content, create_user, create_group, redis,\
    create_rich_user
from canvas.models import Category, Comment, CommentSticker, AnonymousUser, Visibility
from services import Services, with_override_service, FakeTimeProvider

from canvas import economy, stickers
from canvas.economy import InvalidPurchase

class TestEconomy(CanvasTestCase):
    def setUp(self):
        CanvasTestCase.setUp(self)
        self.user = create_user()
        self.request = FakeRequest(self.user)
        
    @with_override_service('time', FakeTimeProvider)
    def test_new_user_gets_free_stickers(self):
        self.assertTrue(economy.eligible_for_daily_free_stickers(self.request.user))
        
    def test_dont_level_up_if_no_points(self):
        reward = economy.level_up(self.request.user)
        total_stickers = int(self.user.kv.stickers.currency.get() or 0)
        self.assertEquals(reward, 0)
        self.assertEquals(total_stickers, 0)

    def test_level_up_if_first_levels_worth_of_points(self):
        points = economy.sticker_schedule(None)
        expected_reward = economy.sticker_schedule(None, reward=True)
        self.user.redis.user_kv.hset('sticker_inbox', points)
        self.request.user_kv = self.user.redis.user_kv.hgetall()
        
        reward = economy.level_up(self.request.user)
        total_stickers = int(self.user.kv.stickers.currency.get() or 0)
        self.assertEquals(total_stickers, expected_reward)
        self.assertEquals(reward, expected_reward)
        
    def test_level_up_twice_together(self):
        points = economy.sticker_schedule(0) + economy.sticker_schedule(1)
        expected_reward = economy.sticker_schedule(0, reward=True) + economy.sticker_schedule(1, reward=True)
        self.user.redis.user_kv.hset('sticker_inbox', points)
        self.request.user_kv = self.user.redis.user_kv.hgetall()
        
        reward = economy.level_up(self.request.user, only_once=False)
        total_stickers = int(self.user.kv.stickers.currency.get() or 0)
        self.assertEquals(total_stickers, expected_reward)
        self.assertEquals(reward, expected_reward)
    
    @with_override_service('time', FakeTimeProvider)
    def test_dont_grant_daily_free_stickers_on_second_hit(self):
        economy.grant_daily_free_stickers(self.request.user)
        self.user.redis.notifications.acknowledge(1)
        
        economy.grant_daily_free_stickers(self.request.user)
        self.assertEqual(self.user.redis.notifications.get(), [])

class TestLimitedAvailabilityStickers(CanvasTestCase):  
    def setUp(self):
        CanvasTestCase.setUp(self)
        self.sticker = stickers.Sticker(11111, "test", cost=10, maximum=100)
        stickers.add_sticker(self.sticker)
    
    def tearDown(self):
        CanvasTestCase.tearDown(self)
        # We remove the sticker because adding it manipulates stickers._stickers, which would break the icons test.
        stickers.remove_sticker(self.sticker)   
         
    def test_purchase_sticker_limited_inventory(self):
        user = create_rich_user()
        user.kv.stickers.add_limited_sticker(self.sticker)
        # Purchase
        economy.purchase_stickers(user, self.sticker.type_id, 1)
        # Should not be able to buy again
        self.assertRaises(InvalidPurchase, lambda: economy.purchase_stickers(user, self.sticker.type_id, 1))

    def test_purchase_sticker_unlimited_inventory(self):
        sticker = stickers.get("banana")
        assert not sticker.is_limited_inventory()
        user = create_rich_user()
        user.kv.stickers.add_limited_sticker(sticker)
        # Purchase
        economy.purchase_stickers(user, sticker.type_id, 1)
        # SHOULD be able to buy again
        for i in range(0, 10):
            economy.purchase_stickers(user, sticker.type_id, 1)
        
                
class TestOldEconomy(CanvasTestCase):
    def setUp(self):
        CanvasTestCase.setUp(self)
        self.user = create_user(is_qa=False)
        self.request = FakeRequest(self.user)

    @with_override_service('time', FakeTimeProvider)
    def test_dont_get_stickers_if_you_just_got_them(self):
        economy.grant_daily_free_stickers(self.request.user)
        self.assertFalse(economy.eligible_for_daily_free_stickers(self.request.user))

