"""
Put Canvas specific configuration here.

Note that this project has three different configuration files:

    /var/canvas/website/settings.py
        That is where we keep all Django specific settings.

    /var/canvas/common/configuration.py
        That is where we keep AWS and infrastructure related settings. Note that this one is outside the /website
        package, which means that you need some pythonpath magic to use it inside canvas

    /var/canvas/website/canvas/knobs.py
        That is where we keep static vars that you can use around Canvas.
"""
from drawquest.knobs import *

# how many times a use gets to sticker before he or she is shown a sticker prompt.
LOGGED_OUT_STICKER_LIMIT = 4

EPIC_STICKER_COST_THRESHOLD = 5

# This allows you to override the default template filename for specific notifications.
OVERRIDE_NOTIFICATION_TEMPLATE = {
    "EmailChannel": {
        "newsletter": {
            "body": "email/newsletter_final.html",
            "subject": "email/newsletter_final_subject.txt"
        }
    }
}

FLAG_RATE_LIMITS = {
    'm': (15, 2*60,),
    'h': (50, 60*60,),
}


# The number of (#1) stickers users get when they visit everyday. This is a retention award.
DAILY_FREE_STICKERS = 3
SIGNUP_FREE_STICKERS = 10

# The number of stickers required to reach each level.
STICKER_SCHEDULE = [5,10,15,20,25,30,40,50,60,70,80,90,100]
# The award (in #1 stickers) a user gets when she achieves a level.
STICKER_REWARDS  = [3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4,  5]

TWENTYFOUR_HOUR_EMAIL_COMMENT_COUNT = 9

TAGLINE = 'Share and play with images!'

FACEBOOK_SHARE_IMAGE_TYPE = ['small_column', 'stream', 'thumbnail']
# The max filesize in KB before we try the next smaller image type, from the list above.
FACEBOOK_SHARE_IMAGE_SIZE_CUTOFF = 60

VIEW_THREAD_PAGE_NUM_TOP = 8

COMMENTS_PER_PAGE = 50

DEFAULT_FOOTER_STICKER = 'smiley'

POST_TEXT_TRUNCATION_LENGTH = 140

FOOTER_UPDATE_ATTEMPTS = 3

POST_TITLE_MAX_LENGTH = 140
STICKER_MESSAGE_MAX_LENGTH = 140

# How many points given for one of your posts being remixed.
REMIX_POINTS = 1

PUBLIC_API_RATE_LIMIT = 1000
PUBLIC_API_MAX_ITEMS = 100
PUBLIC_API_PAGINATION_SIZE = 100

FOLLOWING_MENU_ROWS = 15
FOLLOWING_MENU_COLUMNS = FOLLOWING_MENU_ROWS * 4

REMIX_IMAGES_STAFF_PICKS = [
    # This is the abcde from http://example.com/p/abcde
    '2hdv9',
    '1km2r',
    '2ypcj',
    '1f1a9',
    '25gna',
    '1umn4',
    '222zn',
    '8wfp8',
    '89bkc',
    'qix8v',
    'lakze',
    '4uqym',
    '4luij',
    '42k6w',
    'awg15',
    'ocmpt',
    'pkztj',
    '2f6zm',
    '21ypq',
    '1ese3',
    '221qd',
    '1i8xo',
    '6v79z',
    '78ykf',
    'u2zw9',
    'qydyh',
    'tif0q',
    'rc328',
    'piusb',
]

FEED_PROMOTION_STICKER_COST_THRESHOLD = 5
FEED_ITEMS_PER_PAGE = 50

FOLLOWED_TAGS_SHOWN = 100
FOLLOWED_TAGS_REALTIME_THRESHOLD = 10

ACTIVITY_STREAM_PER_PAGE = 20

SUGGESTED_USERS = [
    'Enin',
    'Tati5001',
    'calhaus',
    'RedmonBray',
    'Jiakko',
    'CyberTaco',
    'Harbltron',
    'lollajames',
    'TmsT',
    'Sunset',
    'Xeno_Mezphy',
    'AngelOsario',
    'ravenunknown',
    'abeeiamnot',
    'Coutoon',
    'nicepunk',
    'GrogMalBlood',
    'ZombieLincolnFP',
    'TrueBlue',
    'mradmack',
    'jerm',
    'the7thcolumn',
    'BrettZki',
    'francesco9001',
    'sanamkan',
    'Grga',
    'nsbarr',
    'dmauro',
    'moobraz',
    'dagfooyo',
    'echapa',
    'bhudapop',
    'ChasM',
    'metaknight',
    'Photocopier',
    'lukebn',
    'Zoucas',
    'AvengerOfBoredom',
    'mikshaw',
    'Anominous',
]

SUGGESTED_TOPICS = [
    'abstract',
    'art',
    'canvas',
    'cats',
    'challenges',
    'cute',
    'drawing',
    'exploitable',
    'funny',
    'games',
    'gif_bin',
    'glitch_art',
    'photography',
    'pop_culture',
    'request',
    'video_games',
]

OFFLINE_SUGGESTED_TOPICS = list(sorted([
    '8bit','90s','bookmarklet','darker_side','dogs','drawfriends','fashion','food','glitch_art','minecraft','movies','music','nerdy','partyhard','politics','premium','random','scripts','technology','trololololo','wallpaper','wtf',
    'abstract',
    'art',
    'canvas',
    'cats',
    'challenges',
    'cute',
    'drawing',
    'exploitable',
    'funny',
    'games',
    'gif_bin',
    'glitch_art',
    'photography',
    'pop_culture',
    'request',
    'video_games',
]))

SUGGESTED_TOPIC_PREVIEWS = {
    "abstract"      : "cd12831f5c633ed00c4f483dc3006eb3c0cca345",
    "art"           : "bd457cc102df633df440c96dc2aaae107de3979a",
    "canvas"        : "41eb1025e73b62b297e48e7736098457da32d16c",
    "cats"          : "5c4279694ef21e9be365d6f9d7f6900e48edaba6",
    "challenges"    : "c28e1df3b622ec88203949620b23b82eeacfa6e5",
    "cute"          : "dd2871c89dec7e589425bdfc8b6de1e4b8eafa75",
    "drawing"       : "eddd46ab6992e867a7f45f3e56aa9e95122ae419",
    "exploitable"   : "853e684737772002f3dc99a628b14a60db133fa6",
    "funny"         : "9823b39e77698f7371071310094567d4542e82d0",
    "games"         : "5be3b62cae5538e5457bc24574849af46c02a009",
    "gif_bin"       : "14aba9e1d8a126a7dd2bfad5c9fbc803e0d314c6",
    "glitch_art"    : "bbf5af5e5580dbfb7db2bc73c5ae1172ad281a19",
    "photography"   : "b28d0a7931c11cc5909f05c1bf5e7368ea1bfb32",
    "pop_culture"   : "0d04b9d7ae641a31ea12e50b98e156912f2ad5ef",
    "request"       : "299071ee0d48065c76bd940caa252680d210183f",
    "video_games"   : "91096f74bc169f67c8c62279103eebf73babad0b",
}

SUGGESTED_USERS_TO_FOLLOW_COUNT = 3

