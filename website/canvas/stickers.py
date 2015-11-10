import datetime
import math
import time

from django.utils.tzinfo import FixedOffset

from canvas.redis_models import RedisHash, RedisKey
from canvas import knobs
from django.conf import settings


class Sticker(object):
    """
    A datastructure to hold a Canvas sticker definition.

    Note that the `details` property (and `to_client()`) never gets updated after instantiation.
    """
    def __eq__(self, another_sticker):
        try:
            return self.type_id == another_sticker.type_id
        except AttributeError:
            return False

    def __init__(self, type_id, name="", value=None, preference=None, limited=False, hidden=False, unusable=False,
                 cost=None, title="", shop_filename=None, shop_text="", purchasable=None, achievement=None,
                 admin_only=False, maximum=None, hide_from_inventory=False, seasonal=False):
        """
        admin:
            Whether this sticker is only available for admins.
        shop_filename:
            Defaults to "name.png" if unspecified here.
        purchasable:
            Leave this as `None` and it will be determined from the cost and achievement status.
            Set it to `False` to override this and force it to not be sold in the shop.
        """
        if cost is not None:
            cost = int(cost)

        if value is None:
            if cost is None or cost < 1:
                value = 1
            else:
                value = math.sqrt(cost+1)
        else:
            value = float(value)

        self._purchasable = purchasable
        if purchasable and not cost:
            raise ValueError('A sticker without a cost cannot be purchasable.')

        if shop_filename is None:
            shop_filename = u'{0}.png'.format(name)

        self.type_id = type_id
        self.name = name
        self.value = value
        self.preference = preference if preference is not None else type_id
        self._is_limited = bool(limited or cost or maximum)
        # not placeable anymore, but should still show up on existing posts.
        self._is_unusable = unusable
        # not placeable anymore nor should it show up on already stickered posts.
        self.is_hidden = hidden
        self.cost = cost
        self.title = title
        self.shop_filename = shop_filename
        self.shop_text = shop_text
        self.achievement = achievement
        self.admin_only = admin_only
        self.maximum = maximum
        self.user_remaining = None

        self.inventory_hash = None
        if self.maximum:
            self.inventory_hash = RedisKey("sticker:%s:remaining" % self.name)

        self.seasonal = seasonal
        self.hide_from_inventory = hide_from_inventory

    @property
    def active_seasonal(self):
        return self in get_active_seasonal_stickers()

    @property
    def is_unusable(self):
        if self.seasonal:
            return not self.active_seasonal
        else:
            return self._is_unusable

    @property
    def is_limited(self):
        if self.seasonal:
            return self.active_seasonal
        else:
            return self._is_limited

    def is_epic(self):
        """ Recipients of Epic stickers get an exciting realtime notification. """
        return self.cost >= knobs.EPIC_STICKER_COST_THRESHOLD

    def is_star(self):
        from django.conf import settings
        if not hasattr(settings, 'STAR_STICKER_TYPE_ID'):
            return False
        return self.type_id == settings.STAR_STICKER_TYPE_ID

    def is_usable(self, user):
        """
        Whether this sticker can be used by the user. Takes several factors into account,
        not just `Sticker.is_unusable`.
        """
        return bool(self.cost
                    and not self.is_unusable
                    and not self.is_hidden
                    and (self.achievement is None or user.kv.achievements.by_id(self.achievement).get()))

    def is_limited_inventory(self):
        """ Whether this sticker has a limited number of units available. """
        return self.maximum != None

    def is_purchasable(self, user):
        if self._purchasable is None:
            if self.is_limited_inventory() and self.is_out_of_stock():
                # Then it can be purchased if there are enough.
                # Note that we do not check for whether the user has already bought the
                # sticker here. We also do not check if the user can afford it.
                # This logic is done in api.store_buy
                return False

            return bool(self.cost and (self.achievement is None
                                       or user.kv.achievements.by_id(self.achievement).get()))
        return self._purchasable

    @property
    def remaining(self):
        """ Returns the number of stickers available. """
        if self.inventory_hash:
            # Was the value ever bootstrapped
            if self.inventory_hash.get() == None:
                self.inventory_hash.set(self.maximum)
            return int(self.inventory_hash.get())
        return None

    def is_out_of_stock(self):
        return self.remaining == 0

    def decrement_inventory(self):
        try:
            return int(self.inventory_hash.decr())
        except:
            pass

    def to_client(self):
        keys = [
            'type_id',
            'name',
            'value',
            'preference',
            'is_limited',
            'is_unusable',
            'is_hidden',
            'cost',
            'title',
            'shop_filename',
            'shop_text',
            'achievement',
            'admin_only',
            'maximum',
            'user_remaining',
        ]
        return dict([(key, getattr(self, key)) for key in keys])

    def sort_key(self, count):
        score = count * (self.cost+1 if self.cost else 1)
        return (score, int(self.is_limited), self.preference)

    def __repr__(self):
        return unicode(self.to_client())

_stickers = [
    Sticker(0, 'dummy', value=0, unusable=True, hidden=True),
    # Upvotes.
    Sticker(1, 'smiley', preference=27),
    Sticker(2, 'frowny', preference=22),
    Sticker(3, 'monocle', preference=25),
    Sticker(4, 'lol', preference=26),
    Sticker(5, 'wtf', purchasable=True, cost=1000),
    Sticker(6, 'question', preference=20),
    Sticker(601, 'question2', seasonal=True),
    Sticker(7, 'num1', cost=1, limited=True, purchasable=False, hide_from_inventory=True),
    Sticker(8, 'cookie', preference=21),
    Sticker(9, 'heart', preference=24),
    Sticker(10, 'wow', preference=23),
    Sticker(11, 'empty', unusable=True),
    # Seasonal.
    Sticker(100, "note", seasonal=True),
    Sticker(101, "texas", seasonal=True),
    Sticker(102, "sxsw", seasonal=True),
    Sticker(104, "monocle-sombrero", preference=32),
    Sticker(105, "monocle-maracas", preference=33),
    Sticker(106, "monocle-margarita", preference=34),
    Sticker(901, "win", preference=35),
    Sticker(902, "wookie", preference=36),
    Sticker(107, "monocle-hungover", seasonal=True),
    Sticker(507, "selleck2", cost=10000, purchasable=True),
    Sticker(508, "wow_old", cost=123456789, purchasable=True),
    Sticker(108, "zalgo-black", seasonal=True),
    Sticker(109, "america", seasonal=True),
    Sticker(600, "trololol", seasonal=True),
    Sticker(110, "andrewwk", preference=70),
    Sticker(111, "partyhard", cost=500, purchasable=True),
    Sticker(112, "wow-tired", seasonal=True),
    Sticker(113, "skull", seasonal=True),
    Sticker(114, "cthulhu", seasonal=True),
    Sticker(115, "jack-o-lantern", seasonal=True),
    Sticker(116, "turkey", seasonal=True),
    Sticker(117, "cornucopia", seasonal=True),
    Sticker(118, "pumpkin-pie", seasonal=True),
    Sticker(119, "gift", seasonal=True),
    Sticker(120, "snowflake", seasonal=True),
    Sticker(121, "rudolph", seasonal=True),
    Sticker(122, "twothousandtwelve", seasonal=True),
    Sticker(123, "champagne", seasonal=True),
    Sticker(124, "mayan", preference=31),
    Sticker(125, "sopa", seasonal=True),
    Sticker(126, "lantern", seasonal=True),
    Sticker(127, "cupcake", seasonal=True),
    Sticker(128, "groundhog", seasonal=True),
    Sticker(129, "teddy", seasonal=True),
    Sticker(130, "valentine", seasonal=True),
    Sticker(131, "forever-alone-seasonal", seasonal=True),
    Sticker(132, "clover", seasonal=True),
    Sticker(133, "green-beer", seasonal=True),
    Sticker(134, "pot-o-gold", seasonal=True),
    Sticker(135, "bill-fools1", preference=50),
    Sticker(136, "bill-fools2", preference=51),
    Sticker(137, "bill-fools3", preference=52),
    Sticker(138, "bill-fools4", preference=53),
    Sticker(139, "bill-fools5", preference=54),
    Sticker(140, "bill-fools6", preference=55),
    Sticker(141, "lobster", preference=30),
    Sticker(142, "dave", preference=60),
    Sticker(143, "egg-blue", seasonal=True),
    Sticker(144, "egg-pink", seasonal=True),
    Sticker(145, "egg-chocolate", seasonal=True),
    Sticker(146, "jason", seasonal=True),
    Sticker(147, "weed", seasonal=True),
    Sticker(148, "bloodshot", seasonal=True),
    Sticker(149, "joint", seasonal=True),
    Sticker(150, "donut-strawberry", seasonal=True),
    Sticker(151, "donut-chocolate", seasonal=True),
    Sticker(152, "donut-glazed", seasonal=True),
    Sticker(153, "usa-pin", seasonal=True),
    Sticker(154, "usa-hat", seasonal=True),
    Sticker(155, "usa-eagle", seasonal=True),
    Sticker(156, "medal-gold", seasonal=True),
    Sticker(157, "medal-silver", seasonal=True),
    Sticker(158, "medal-copper", seasonal=True),
    Sticker(159, "hurricane-sandy", seasonal=True),
    Sticker(160, "slowpoke-pumpkin", seasonal=True),
    Sticker(161, "slowpoke-ghost", seasonal=True),
    # Inventory
    Sticker(103, "banana", cost=5, title="Banana",
            shop_text="A sticker you may one day earn. Until then, the sticker shall remain locked in here."),
    Sticker(300, "nyancat", cost=25, title="Nyancat",
            shop_text="nyan nyan nyan nyan <a href='http://www.prguitarman.com'>prguitarman</a> nyan nyan nyan nyan "
                      "nyan nyan nyan nyan nyan nyan nyan nyan nyan nyan nyan"),
    Sticker(301, "number-oneocle", cost=100, title="Number Oneocle",
            shop_filename="number-oneocle.gif",
            shop_text="""For the post so classy it needs to be number one'd as well. "But wait," you say, "how is """
                      """it double sided if it's a sticker?" Shhhhhh... it's best not to question the number """
                      """oneocle."""),
    Sticker(302, "fuckyeah", cost=150, title="Fuck Yeah",
            shop_filename="fuckyeah.gif",
            shop_text="FUCK YEAH!"),
    Sticker(303, "cool", cost=1, title="Cool Guy",
            shop_text="Sometimes someone makes a really cool post and only a pair of Raybans can express how you "
                      "feel."),
    Sticker(304, "kawaii", cost=15, title="Kawaii",
            shop_text="For something so cute that just a heart won't do :3"),
    Sticker(305, "hipster", cost=20, achievement=0, title="Hipster",
            shop_text="You probably haven't heard of this sticker, it's still underground."),
    Sticker(306, "glove", cost=50, title="Glove of Power",
            shop_text="I love the power glove. It's so BAD. But it's still pretty nerdy..."),
    Sticker(307, "tacnayn", cost=666666, title="Tacnayn", purchasable=True,
            shop_text="Tacnayn, destroyer of worlds. Sowing death and destruction wherever he goes. The only thing "
                      "standing between Tacnayn and complete annihilation of the universe is his rainbowed enemy "
                      "Nyancat."),
    Sticker(308, "super-lol", cost=30, title="Super LOL",
            shop_text="For when it's so good that you just can't stop laughing."),
    Sticker(309, "forever-alone", cost=10, title="Forever Alone",
        shop_text="Only for the loneliest of posts."),
    # Downvotes.
    Sticker(500, 'stale', unusable=True, hidden=True),
    Sticker(501, 'stop', unusable=True, hidden=True),
    Sticker(502, 'poop', unusable=True, hidden=True),
    # Note that there are two "downvote" stickers.
    # This one is the sticker that gets applied to the comment (hence the -1)
    # when someone uses the downvote action.
    Sticker(503, 'downvote', value=-1, hidden=True),
    # Sharing.
    Sticker(2001, 'facebook', unusable=True),
    Sticker(2002, 'twitter', unusable=True),
    Sticker(2003, 'stumbleupon', unusable=True),
    Sticker(2004, 'tumblr', unusable=True),
    Sticker(2005, 'reddit', unusable=True),
    Sticker(2006, 'email', unusable=True),
    # Actions.
    Sticker(3001, 'flag', unusable=True),
    # This is a down vote action, not a sticker. Hence the "unusable" flag.
    # When this action is applied to a comment, the comment gets a 503/downvote
    # sticker.
    Sticker(3002, 'downvote_action', unusable=True),
    Sticker(3003, 'pin', unusable=True),
    Sticker(3005, 'offtopic', unusable=True),
    Sticker(3007, 'remix'),
    Sticker(8902, 'curated', unusable=True, admin_only=True),
    Sticker(8903, 'sticky', unusable=True, admin_only=True),
]

#
# DRAWQUEST
#
# Ugly hack.
if settings.PROJECT == 'drawquest':
    from django.conf import settings
    _stickers.append(Sticker(settings.STAR_STICKER_TYPE_ID, 'star'))

# Hashes for stickers by name and by id.
# This was we can look them up both ways.
_name_lookup = {}
_id_lookup = {}

def all_stickers():
    return _id_lookup.values()

def add_sticker(sticker):
    _id_lookup[sticker.type_id] = sticker
    # Also index into stickers by name
    _name_lookup[sticker.name] = sticker

def remove_sticker(sticker):
    # This is used by tests only!!
    del _id_lookup[sticker.type_id]
    del _name_lookup[sticker.name]

map(add_sticker, _stickers)

### Mutually-exclusive lists.
primary_types = [_id_lookup[id] for id in [1, 2, 3, 4, 10, 6, 7, 8, 9]]
sharing_types = [_id_lookup[id] for id in [2001, 2002, 2004, 2003, 2005, 2006]]

downvote = _name_lookup.get("downvote")

# Actions that are available to everyone.
actions_base = [_name_lookup.get(sticker_name) for sticker_name in ["flag", "downvote_action", "pin"]]

actions_group_mod = [_name_lookup.get("offtopic")]
actions_staff = [_name_lookup.get("curated"), _name_lookup.get("sticky")]
# Actions that are predicated on a lab setting. get_actions looks for a sticker the action/sticker name
# (Sticker.details.get("name"))
labs_actions = []


def get(name_or_id):
    if isinstance(name_or_id, Sticker):
        return name_or_id
    try:
        # Assuming the typ_id is an int
        sticker = _id_lookup[int(name_or_id)]
    except (KeyError, TypeError, ValueError,):
        sticker = _name_lookup.get(name_or_id)
    if sticker is None:
        sticker = _id_lookup[0]
        #raise ValueError('No such sticker exists.')
    return sticker

def get_purchasable(user):
    """ Returns a list of `Sticker` instances that can be purchased by @user. """
    return sorted(filter(lambda sticker: sticker.is_purchasable(user), all_stickers()),
                  key=lambda sticker: sticker.cost)

def get_inventory(user):
    #TODO move to canvas_auth.models.User
    sticks = sorted([sticker for sticker in all_stickers()
                     if sticker.is_usable(user) and not sticker.hide_from_inventory and user.kv.stickers[sticker.type_id].get()],
                    key=lambda sticker: sticker.cost)
    # Andrew WK :]
    if user.is_authenticated() and user.id == 56409:
        sticks.append(get("partyhard"))
    return sticks

def get_actions(user):
    """ Returns a list of stickers. """
    actions = actions_base[:]
    if user.is_authenticated():
        if user.is_staff:
            actions += actions_staff
        if user.userinfo.details()['moderatable']:
            actions += actions_group_mod
        # Grab stickers that are lab options
        if labs_actions:
            kv = user.redis.user_kv.hgetall()
            for action in labs_actions:
                if RedisHash.read_bool(kv, "labs:"+action.name):
                    actions.append(action)
    return actions

def get_limited_stickers():
    """
    Stickers that can be purchased.

    Returns an iterator on Stickers.
    """
    return filter(lambda sticker: sticker.is_limited or sticker.is_limited_inventory, all_stickers())

def get_managed_stickers():
    """ Returns an iterator of Sticker(s) that have limited availability. """
    for sticker in _stickers:
        if sticker.is_limited and sticker.maximum:
            yield sticker

def details_for(type_id=None, user=None, sticker=None):
    if not sticker:
        sticker = get(type_id)
    if user and sticker.is_limited:
        sticker.user_remaining = user.kv.stickers[sticker.type_id].get()
    return sticker

def all_details(user=None):
    stickers = all_stickers()
    if user:
        stickers += get_actions(user)
    return dict([(sticker.type_id, details_for(user=user, sticker=sticker)) for sticker in stickers])

def sorted_counts(counts):
    filtered_counts = filter(lambda (s,c): not s.is_hidden, counts.items())

    return sorted(
        filtered_counts,
        key=lambda (stick, count): stick.sort_key(count),
        reverse=True
    )


class SeasonalEvent(object):
    def __init__(self, name, start = 0, duration = 0, stickers = [], count = 0, grace_period = 2*60, enabled_locally=False):
        """
        name:
            The historically and globally unique name given to this season, to ensure sticks are delivered once and only once.
        start:
            a unixtime indicating the start time of the seasonal event, in the UTC timezone.
        duration:
            seconds indicating the duration of the event.
        stickers:
            a list of names or type_ids of stickers to give out
        count:
            the number of stickers to give the user
        grace_period:
            number of minutes the sticker is active after the time officially ends (time spent at blinking 00:00:00)
        enabled_locally:
            Ignores start and duration locally to allow easy testing
        """
        self.name = name
        self.start = start
        self.duration = duration
        self.stickers = [get(stick) for stick in stickers]
        self.count = count
        self.enabled_locally = enabled_locally
        self.grace_period = grace_period

    @property
    def sticker_counts(self):
        try:
            return dict(zip(self.stickers, self.count))
        except TypeError:
            return dict((sticker, self.count) for sticker in self.stickers)

    @property
    def end(self):
        return self.start + self.duration

    @property
    def active(self):
        return self.start <= time.time() <= (self.end + self.grace_period) or (settings.LOCAL_SANDBOX and self.enabled_locally)

    def to_client(self):
        return {
            'end_time': self.end,
        }

_seasonal_events = [
    SeasonalEvent(
        "groundhog_wtf_redux",
        start = 1332342980,
        duration = 5 * 60,
        grace_period = 2 * 60,
        stickers = ["groundhog"],
        count = 1,
    ),
    SeasonalEvent(
        "april_fools_crazy",
        start = 1333246256,
        duration = 12 * 60 * 60,
        grace_period = 2 * 60,
        stickers = ["bill-fools1","bill-fools2","bill-fools3","bill-fools4","bill-fools5","bill-fools6"],
        count = 0,
    ),
    SeasonalEvent(
        "seafood_fools",
        start = 1390347542,
        duration = 48 * 60 * 60,
        grace_period = 2 * 60,
        stickers = ["lobster", "groundhog", "monocle-sombrero", "monocle-maracas", "monocle-margarita", "win", "wookie", "bill-fools1","bill-fools2","bill-fools3","bill-fools4","bill-fools5","bill-fools6", "dave", "andrewwk"],
        count = 4,
    ),
    SeasonalEvent(
        "murray9001",
        start = 1390861872,
        duration = 1 * 60 * 60,
        grace_period = 2 * 60,
        stickers = ['groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog', 'groundhog'],
        count = 9000,
    ),
    SeasonalEvent(
        "hungover3",
        start = 1390629065,
        duration = 24 * 60 * 60,
        grace_period = 2 * 60,
        stickers = ['monocle-hungover', 'wow-tired', 'zalgo-black'],
        count = 3,
    ),
    SeasonalEvent(
        "easter",
        start = 1333890000,
        duration = 24 * 60 * 60,
        stickers = ["egg-pink", "egg-blue", "egg-chocolate"],
        count = 3,
    ),
    SeasonalEvent(
        "friday_13_april_2012",
        start = 1334307600,
        duration = 24 * 60 * 60,
        stickers = ["jason"],
        count = 5,
    ),
    SeasonalEvent(
        "420",
        start = 1334916000,
        duration = 24 * 60 * 60,
        stickers = ["weed", "bloodshot", "joint"],
        count = 3,
    ),
    SeasonalEvent(
        "donut_day",
        start = 1338544800,
        duration = 24 * 60 * 60,
        stickers = ["donut-strawberry", "donut-chocolate", "donut-glazed"],
        count = 3,
    ),
    SeasonalEvent(
        "independence_day",
        start = 1341399600,
        duration = 24 * 60 * 60,
        stickers = ["usa-pin", "usa-hat", "usa-eagle"],
        count = 3,
    ),
    SeasonalEvent(
        "olympics",
        start = 1344574800,
        duration = 3 * 24 * 60 * 60,
        stickers = ["medal-gold", "medal-silver", "medal-copper"],
        count = [1, 3, 5],
    ),
    SeasonalEvent(
        "halloween",
        start = 1351843200,
        duration = 3 * 24 * 60 * 60,
        stickers = ["hurricane-sandy", "slowpoke-pumpkin", "slowpoke-ghost"],
        count = 5,
    ),
    SeasonalEvent(
        "thanksgiving",
        start = 1353495600,
        duration = 3 * 24 * 60 * 60,
        stickers = ["turkey", "cornucopia", "pumpkin-pie"],
        count = 5,
    ),
    SeasonalEvent(
        "dec212012",
        start = 1390347542,
        duration = 1 * 24 * 60 * 60,
        stickers = ["mayan"],
        count = 5,
    ),
    SeasonalEvent(
        "christmas",
        start = 1356325200,
        duration = 3 * 24 * 60 * 60,
        stickers = ["gift", "snowflake", "rudolph"],
        count = 5,
    ),
    # In progress
    SeasonalEvent(
        "groundhog_day",
        start = 1359799200,
        duration = 1 * 24 * 60 * 60,
        stickers = ["groundhog"],
        count = 5,
    ),
    SeasonalEvent(
        "final_countdown6",
        start = 1390853567,
        duration = .5 * 60 * 60,
        stickers = ["trololol", "twothousandtwelve", "usa-eagle", "texas", "skull", "question2"],
        count = 9001,
    ),
    SeasonalEvent(
        "note3332",
        start = 1390867766,
        duration = 4 * 60,
        stickers = ["cupcake"],
        count = 1,
    ),
]

def get_active_event():
    for event in _seasonal_events:
        if event.active:
            return event

def get_active_seasonal_stickers():
    event = get_active_event()
    return event.stickers if event else []
