# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from redis.exceptions import ResponseError

from apps.tags.models import all_tags
from canvas.models import Comment

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        for comment in Comment.all_objects.all():
            print comment.tags.smembers()
            tags = comment.tags.smembers()
            if len(tags) > 0:
                try:
                    all_tags.sadd(*tags)
                except ResponseError:
                    pass


    def backwards(self, orm):
        "Write your backwards methods here."


    models = {

    }

    complete_apps = ['tags']
