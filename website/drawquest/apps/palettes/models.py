from django.db import models

from canvas.models import BaseCanvasModel
from canvas.redis_models import redis, RedisSet


class Color(object):
    def __init__(self, rgb=None, special_name=None, index=None):
        """
        `special_name` is for e.g. rainbow, which has no single RGB value.
        """
        if rgb is None and special_name is None:
            raise ValueError("Must specify either rgb or special_name.")
        
        self.rgb = rgb
        self.special_name = special_name
        self.index = index

    def to_client(self):
        ret = {'rgb': self.rgb}

        for attr in ['special_name', 'index']:
            if getattr(self, attr) is not None:
                ret[attr] = getattr(self, attr)

        return ret


class Palette(object):
    def __init__(self, id_, name, human_readable_name, cost, colors):
        """
        `colors` is a list of Color instances.
        """
        self.id = id_
        self.name = name
        self.human_readable_name = human_readable_name
        self.colors = colors
        self.cost = cost

    def __repr__(self):
        return self.name

    def to_client(self):
        return {
            'name': self.name,
            'human_readable_name': self.human_readable_name,
            'colors': self.colors,
            'cost': self.cost,
        }


class UserPalettes(object):
    def __init__(self, user_id=None):
        self.user_id = user_id

        self._palettes = None

        if user_id:
            self._palettes = RedisSet('user:{}:palettes'.format(user_id))

    def __iter__(self):
        yield DEFAULT_PALETTE

        if self._palettes:
            for palette in self._palettes.smembers():
                yield get_palette_by_id(palette)

    def __contains__(self, palette):
        if palette.id == DEFAULT_PALETTE.id:
            return True

        return self._palettes and palette.id in self._palettes

    def to_client(self):
        return [palette for palette in self]

    def unlock(self, palette):
        if not self.user_id:
            raise TypeError("Cannot unlock a palette for a logged-out user.")

        if isinstance(palette, basestring):
            palette = get_palette_by_name(name)

        if palette.id == DEFAULT_PALETTE.id:
            return

        self._palettes.sadd(palette.id)


def _colors(*rgbs):
    return [Color(rgb, index=idx) for (idx, rgb) in rgbs]

DEFAULT_PALETTE = Palette(0, 'default', 'Default', 0,
                          _colors(
                              (390,   (255,255,255)),
                              (410,   (184,182,181)),
                              (010,   (74,74,74)),
                              (180,   (108,214,116)),
                              (140,   (255,228,92)),
                              (120,   (248,172,85)),
                              (060,   (233,90,92)),
                              (340,   (124,130,255)),
                              (230,   (134,213,255)),
                              (375,   (255,228,177)),
                              (200,   (36,113,247)),
                              (355,   (156,103,95)),
                          ))

PALETTE_COST = 50

purchasable_palettes = [
    Palette(1, 'vintage_rainbow', 'Vintage Rainbow', PALETTE_COST,
            _colors(
                (060,     (163,53,14)),
                (100,     (242,136,0)),
                (150,     (24,200,38)),
                (220,     (44,154,213)),
                (300,     (136,60,237))
            )),
    Palette(2, 'winter_hues', 'Winter Hues', PALETTE_COST,
            _colors(
                (280,     (221,251,253)),
                (400,     (239,239,239)),
                (195,     (206,225,214)),
                (170,     (59,121,77)),
                (050,     (118,0,0)),
            )),
    Palette(3, 'candy', 'Candy', PALETTE_COST,
            _colors(
                ( 80,     (254,67,101)),
                ( 90,     (255,171,187)),
                (190,     (150,255,171)),
                (240,     (18,238,255)),
            )),
    Palette(4, 'humane', 'Humane', PALETTE_COST,
            _colors(
                (380,     (255,233,215)),
                (370,     (255,224,214)),
                (360,     (241,189,171)),
                (350,     (87,37,30)),
            )),
    Palette(5, 'dawn', 'Dawn', PALETTE_COST,
            _colors(
                (320,     (91,35,105)),
                (330,     (161,28,71)),
                (040,     (235,30,37)),
                (110,     (255,161,0)),
                (130,     (255,227,0)),
            )),
    Palette(6, 'sky_shades', 'Sky Shades', PALETTE_COST,
            _colors(
                (210,     (30,66,176)),
                (250,     (139,220,255)),
                (270,     (212,242,255)),
                (260,     (182,216,230)),
            )),
    Palette(7, 'midnight', 'Midnight', PALETTE_COST,
            _colors(
                (420,     (0,0,0)),
                (205,     (2,14,106)),
                (310,     (50,2,85)),
                (160,     (8,51,55)),
                (145,     (255,254,222)),
            )),
]

all_palettes = purchasable_palettes + [DEFAULT_PALETTE]

_palette_names = dict((palette.name, palette) for palette in purchasable_palettes + [DEFAULT_PALETTE])
_palette_ids = dict((palette.id, palette) for palette in purchasable_palettes + [DEFAULT_PALETTE])

def palettes_hash():
    """ Returns the sum of all RGB values in all palettes. """
    return sum([sum(p.rgb) for p in all_palettes()])

def get_palette_by_id(id_):
    if isinstance(id_, basestring):
        id_ = int(id_)

    return _palette_ids[id_]

def get_palette_by_name(name):
    return _palette_names[name]

def user_palettes(user):
    if user.is_authenticated():
        return user.redis.palettes

    return UserPalettes()

