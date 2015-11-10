# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

from apps.canvas_auth.models import User
from django.conf import settings

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        try:
            canvas_user_id = User.objects.get(username=settings.CANVAS_ACCOUNT_USERNAME).id
        except User.DoesNotExist:
            canvas_user_id = User.objects.create_user(settings.CANVAS_ACCOUNT_USERNAME,
                                                      'accounts@example.com', 'password123$').id
        for user in User.objects.all().exclude(username=settings.CANVAS_ACCOUNT_USERNAME):
            user.redis.following.sadd(canvas_user_id)


    def backwards(self, orm):
        "Write your backwards methods here."


    models = {
        
    }

    complete_apps = ['canvas_auth']
