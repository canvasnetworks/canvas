# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

from apps.canvas_auth.models import User
from canvas.models import Category
from services import Services

class Migration(DataMigration):

    depends_on = (
        ("canvas", "0156_add_profile_group"),
    )

    def forwards(self, orm):
        "Write your forwards methods here."

        for u in User.objects.all():
            t = Services.time.time()
            for cat in Category.objects.filter(followers__user=u).order_by('-name'):
                t += 1
                if not u.redis.followed_tags.zrank(cat.name):
                    print "{} not in {}".format(cat.name, u.username)
                else:
                    print "{} already in {}".format(cat.name, u.username)
                u.redis.followed_tags.zadd(cat.name, t)



    def backwards(self, orm):
        "Write your backwards methods here."


    models = {

    }

    complete_apps = ['tags']
