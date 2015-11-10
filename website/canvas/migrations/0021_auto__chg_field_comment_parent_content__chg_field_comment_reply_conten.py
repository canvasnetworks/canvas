# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Renaming column for 'Comment.parent_content' to match new field type.
        db.rename_column('canvas_comment', 'parent_content', 'parent_content_id')
        # Changing field 'Comment.parent_content'
        db.alter_column('canvas_comment', 'parent_content_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['canvas.Content']))

        # Adding index on 'Comment', fields ['parent_content']
        db.create_index('canvas_comment', ['parent_content_id'])

        # Renaming column for 'Comment.reply_content' to match new field type.
        db.rename_column('canvas_comment', 'reply_content', 'reply_content_id')
        # Changing field 'Comment.reply_content'
        db.alter_column('canvas_comment', 'reply_content_id', self.gf('django.db.models.fields.related.ForeignKey')(null=True, to=orm['canvas.Content']))

        # Adding index on 'Comment', fields ['reply_content']
        db.create_index('canvas_comment', ['reply_content_id'])


    def backwards(self, orm):
        
        # Removing index on 'Comment', fields ['reply_content']
        db.delete_index('canvas_comment', ['reply_content_id'])

        # Removing index on 'Comment', fields ['parent_content']
        db.delete_index('canvas_comment', ['parent_content_id'])

        # Renaming column for 'Comment.parent_content' to match new field type.
        db.rename_column('canvas_comment', 'parent_content_id', 'parent_content')
        # Changing field 'Comment.parent_content'
        db.alter_column('canvas_comment', 'parent_content', self.gf('django.db.models.fields.CharField')(max_length=32))

        # Renaming column for 'Comment.reply_content' to match new field type.
        db.rename_column('canvas_comment', 'reply_content_id', 'reply_content')
        # Changing field 'Comment.reply_content'
        db.alter_column('canvas_comment', 'reply_content', self.gf('django.db.models.fields.CharField')(max_length=32))


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'canvas.comment': {
            'Meta': {'object_name': 'Comment'},
            'anonymous': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'default': "'0.0.0.0'", 'max_length': '15'}),
            'parent_content': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'comments'", 'to': "orm['canvas.Content']"}),
            'reply_content': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'used_in_comments'", 'null': 'True', 'to': "orm['canvas.Content']"}),
            'reply_text': ('django.db.models.fields.CharField', [], {'max_length': '2000', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.FloatField', [], {})
        },
        'canvas.content': {
            'Meta': {'object_name': 'Content'},
            'id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'default': "'0.0.0.0'", 'max_length': '15'}),
            'timestamp': ('django.db.models.fields.FloatField', [], {})
        },
        'canvas.contentsticker': {
            'Meta': {'object_name': 'ContentSticker'},
            'content': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'stickers'", 'to': "orm['canvas.Content']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'timestamp': ('django.db.models.fields.FloatField', [], {}),
            'type_id': ('django.db.models.fields.IntegerField', [], {})
        },
        'canvas.hashtag': {
            'Meta': {'object_name': 'Hashtag'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50', 'db_index': 'True'})
        },
        'canvas.post': {
            'Meta': {'object_name': 'Post'},
            'anonymous': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'blacklisted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'content_id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'default': "'0.0.0.0'", 'max_length': '15'}),
            'post_id': ('django.db.models.fields.IntegerField', [], {}),
            'thread': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'posts'", 'to': "orm['canvas.Thread']"}),
            'thumb_down': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'thumb_up': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'timestamp': ('django.db.models.fields.FloatField', [], {})
        },
        'canvas.stashcontent': {
            'Meta': {'object_name': 'StashContent'},
            'content_id': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'thread': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['canvas.Thread']", 'null': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'canvas.thread': {
            'Meta': {'object_name': 'Thread'},
            'hashtags': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'threads'", 'symmetrical': 'False', 'to': "orm['canvas.Hashtag']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'locked': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['canvas']
