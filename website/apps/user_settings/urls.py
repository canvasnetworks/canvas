from django.conf.urls.defaults import *

urlpatterns = patterns('apps.user_settings.views',
    (r'^$', 'user_settings'),
    
    (r'^/confirm_email/(\w+)/cancel$', 'cancel_email_confirmation'),
    (r'^/confirm_email/(\w+)$', 'confirm_email'),

    (r'^/delete_account$', 'disable_account'),
)

