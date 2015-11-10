'''
Classes to generate the Example.com sitemap based on django.contrib.sitemaps.
'''
from django.contrib.sitemaps import Sitemap
from django.utils.datetime_safe import datetime
from canvas.models import Category, Visibility, Comment
from django.core import urlresolvers
from django.conf import settings
import urlparse
from canvas import util

class BaseSitemap(Sitemap):
    def get_urls(self, page=1, site=None):
        """ A hack so that we don't have to use django.sites
        """
        urls = super(BaseSitemap, self).get_urls(page, site)
        if site.domain != settings.DOMAIN:
            for url in urls:
                url['location'] = url['location'].replace("http://"+site.domain, "", 1)
        return urls
        
class Categories(BaseSitemap):
    # Crawling category pages is important.
    priority = 1.0
    
    def items(self):
        """ Returns a list of categories that are visibile. 
        """
        return Category.objects.filter(visibility=Visibility.PUBLIC)
    
    def last_mod(self, category):
        """
        The last time this URL has changed. For categories, we use the current time because groups get posted to all 
        the time. 

        @TODO: Figure out a way to get a more precise last_mod time
        """
        return datetime.now()
    
    def location(self, category):
        return util.make_absolute_url(category.get_absolute_url(), "http:")

    
#class Threads(BaseSitemap):
#    priority = 0.7
#    
#    def items(self):
#        threads = Comment.objects.filter(parent_comment=None, visibility=Visibility.PUBLIC).order(score)

class StaticSitemap(BaseSitemap):
    """ 
    Generates a sitemp for the static/direct_to_template pages.
    """
    priority = 0.5

    url_patterns = []
    def __init__(self, url_patterns):
        self.url_patterns = url_patterns
        
    def items(self):
        return self.url_patterns

    def changefreq(self, obj):
        return 'monthly'

    def location(self, regex_url):
        relative_url = regex_url.regex.pattern.replace("^", "/").replace("$", "")
        return util.make_absolute_url(relative_url, "http")

