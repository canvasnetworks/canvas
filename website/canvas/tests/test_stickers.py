from itertools import ifilter
import os

from canvas import stickers
from canvas.api import store_buy
from canvas.models import UserKV
from canvas.tests.tests_helpers import CanvasTestCase, create_user, create_rich_user, create_group, FakeRequest

"""
We're leaving this test disabled until we have a good way to generate the sticker
background-image CSS from the sticker objects.

class TestStickerImages(CanvasTestCase):
    def test_existence(self):
        for sticker in ifilter(lambda sticker: not sticker.is_hidden,
                               stickers.all_details().itervalues()):
            # Check the inventory/comment image.
            #
            # This is a hack to make it work for the "downvote" sticker and the corresponding "downvote_action" 
            # stickers.
            #
            # So the convention for paired sticker/action is to add a _prefix.    
            sticker_name = sticker.name.split("_")[0]
            self.assertTrue(os.path.exists('/var/canvas/website/static/img/stickers/{0}.png'.format(sticker_name)))
"""
            

class TestStickers(CanvasTestCase):
    def test_get_actions(self):
        user = create_user()
        group = create_group(name="foobar")
        # Make that user a moderator
        group.moderators.add(user)
        actions = stickers.get_actions(user)
        for sticker in stickers.actions_group_mod:
            assert sticker in actions

    def test_get_nonexistent_sticker(self):
        for key in -666, "bogus_thing":
            sticker = stickers.get(key)
            self.assertEqual(0.0, sticker.value)
            self.assertEqual(0, sticker.type_id)
            self.assertEqual('dummy', sticker.name)


class TestStickerInventory(CanvasTestCase):
    def setUp(self):
        CanvasTestCase.setUp(self)
        self.sticker = stickers.Sticker(11111, "test", cost=10, maximum=100)
        stickers.add_sticker(self.sticker)
    
    def tearDown(self):
        CanvasTestCase.tearDown(self)
        # We remove the sticker because adding it manipulates stickers._stickers, which would break the icons test.
        #stickers.remove_sticker(self.sticker)
        
    def test_remaining(self):
        sticker = self.sticker
        self.assertTrue(sticker.remaining)
        self.assertEqual(sticker.remaining, sticker.maximum)
    
    def test_purchase(self):
        sticker = self.sticker

        remaining = sticker.remaining
        sticker.decrement_inventory()
        new_remaining = sticker.remaining
        
        self.assertEqual(new_remaining, remaining - 1)
    
    def test_is_purchasable(self):
        user = create_rich_user()
        # Grab a purchasable sticker
        banana = stickers.get("banana")
        user.kv.stickers.add_limited_sticker(self.sticker)
        self.assertTrue(banana.cost)
        # Purchase it twice
        # @TODO: we should rafactor the api calls to be able to take 
        # arguments that are not wrapped in the request payload.
        request = FakeRequest(user)
        request.POST = dict(item_type="sticker", item_id=banana.type_id)
        request.method = "POST"
        request.raw_post_data = {}
        for _ in range(0, 2):
            # Buy
            store_buy(request)
            self.assertTrue(banana.is_purchasable(user))

    def test_is_purchasable_limited_availability(self):
        user = create_rich_user()

        # Grab a limited availability sticker
        sticker = self.sticker
        user.kv.stickers.add_limited_sticker(sticker)
        
        self.assertTrue(sticker.is_purchasable(user))
        
        # Buy it
        request = FakeRequest(user)
        request.POST = dict(item_type="sticker", item_id=sticker)
        request.method = "POST"
        request.raw_post_data = {}
        assert store_buy(request)
        
        # is_purchasable should still return True. The logic that checks for 
        # whether you bought this sticker twice happens in the api.
        self.assertTrue(sticker.is_purchasable(user))

    def test_overridden_unpurchasable(self):
        sticker = stickers.Sticker(31337, 'test', cost=1, purchasable=False)
        self.assertFalse(sticker.is_purchasable(create_user()))
    
