# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

from apps.canvas_auth.models import User
from canvas.knobs import SUGGESTED_USERS
from canvas.models import UserInfo
from django.conf import settings

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        if not settings.PRODUCTION:
            for un in SUGGESTED_USERS:
                try:
                    User.objects.get(username=un)
                except:
                    u = User(username=un)
                    u.save()
                    u.userinfo = UserInfo()
                    u.userinfo.save()


    def backwards(self, orm):
        "Write your backwards methods here."

    depends_on = (
        ("canvas", "0157_add_facebook_id"),
        ('canvas', '0160_add_enable_timeline'),
        ('canvas', '0161_add_timeline_posts'),
    )

    models = {

    }

    complete_apps = ['suggest']
