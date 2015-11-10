from django.conf.urls.defaults import *

urlpatterns = patterns('drawquest.apps.drawquest_auth.views',
    url(r'^$', 'password_reset', kwargs={'template_name': 'password_reset/request.html', 'email_template_name': 'password_reset_email.django.html', 'domain_override': 'example.com'}), # use 'from_email': 'passwordreset@example.com' when it lands in stable.
    url(r'^email_sent$', 'password_reset_done', kwargs={'template_name': 'password_reset/email_sent.html'}),
    url(r'^reset(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', 'password_reset_confirm', kwargs={'template_name': 'password_reset/reset.html'}),
    url(r'^success$', 'password_reset_complete', kwargs={'template_name': 'password_reset/success.html'}),
)

