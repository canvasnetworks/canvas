import urllib2

from rauth.service import OAuth1Service
import requests

from canvas import bgwork
from canvas.exceptions import ServiceError
from drawquest import economy

def post_photo(user, blog_hostname, comment):
    tumblr = OAuth1Service(
        name='tumblr',
        consumer_key=user_token,
        consumer_secret=user_secret,
        request_token_url='http://www.tumblr.com/oauth/request_token',
        authorize_url='http://www.tumblr.com/oauth/authorize',
        access_token_url='http://www.tumblr.com/oauth/access_token',
    )

    image_data = requests.get(comment.details().content.get_absolute_url_for_image_type('original')).content
    image_data = urllib2.quote(image_data)

    url = comment.get_share_page_url_with_tracking(user, 'tumblr')

    params = {
        'type': 'photo',
        'state': 'published',
        'tags': 'DrawQuest',
        'link': url,
        'source': url,
        'caption': comment.quest.title + ' on DrawQuest',
        'data': [image_data],
    }

    resp = tumblr.post('http://api.tumblr.com/v2/blog/{0}/post'.format(blog_hostname), params,
                       access_token=access_token, access_token_secret=access_token_secret)

    resp.raise_for_status()

    if resp.json['meta']['status'] != 201: # 201: Created. http://www.tumblr.com/docs/en/api/v2#posting
        raise ServiceError("Error posting to Tumblr: " + resp.json['meta']['msg'])

    @bgwork.defer
    def rewards():
        economy.credit_personal_share(user)

