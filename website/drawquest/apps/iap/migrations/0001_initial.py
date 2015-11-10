# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'IapReceipt'
        db.create_table('iap_iapreceipt', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('purchaser', self.gf('django.db.models.fields.related.ForeignKey')(related_name='iap_receipts', to=orm['auth.User'])),
            ('receipt_data', self.gf('django.db.models.fields.TextField')()),
            ('timestamp', self.gf('canvas.util.UnixTimestampField')()),
            ('product_id', self.gf('django.db.models.fields.CharField')(max_length=256, blank=True)),
            ('version_external_identifier', self.gf('django.db.models.fields.CharField')(max_length=256, blank=True)),
            ('bvrs', self.gf('django.db.models.fields.CharField')(max_length=256, blank=True)),
            ('bid', self.gf('django.db.models.fields.CharField')(max_length=256, blank=True)),
            ('verified', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('iap', ['IapReceipt'])


    def backwards(self, orm):
        
        # Deleting model 'IapReceipt'
        db.delete_table('iap_iapreceipt')


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
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '254', 'blank': 'True'}),
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
        'canvas_auth.user': {
            'Meta': {'object_name': 'User', 'db_table': "'auth_user'", '_ormbases': ['auth.User'], 'proxy': 'True'}
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'drawquest_auth.user': {
            'Meta': {'object_name': 'User', 'db_table': "'auth_user'", '_ormbases': ['canvas_auth.User'], 'proxy': 'True'}
        },
        'iap.iapreceipt': {
            'Meta': {'object_name': 'IapReceipt'},
            'bid': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'}),
            'bvrs': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'product_id': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'}),
            'purchaser': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'iap_receipts'", 'to': "orm['auth.User']"}),
            'receipt_data': ('django.db.models.fields.TextField', [], {}),
            'timestamp': ('canvas.util.UnixTimestampField', [], {}),
            'verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'version_external_identifier': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'})
        }
    }

    complete_apps = ['iap']