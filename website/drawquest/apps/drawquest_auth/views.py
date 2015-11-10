import re
import urlparse

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.models import get_current_site
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.http import urlquote, base36_to_int
from django.utils.translation import ugettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import csrf_protect

from apps.facebook_app.signed_request import parse_signed_request
from canvas.metrics import Metrics
from canvas.models import FacebookUser
from canvas.shortcuts import r2r_jinja
from canvas.view_guards import require_POST

@require_POST
@csrf_exempt
def deauthorize_facebook_user(request):
    signed_request = request.POST.get(u'signed_request', None)

    if not signed_request:
        return HttpResponseForbidden('403 Forbidden')

    data = parse_signed_request(request, signed_request)
    fb_uid = data['user_id']

    fb_user = FacebookUser.objects.get(fb_uid=int(fb_uid))
    fb_user.delete()

    Metrics.facebook_user_deauthorized.record(request)

    return HttpResponse('success')


# Below copied from django.contrib.auth.views

# 4 views for password reset:
# - password_reset sends the mail
# - password_reset_done shows a success message for the above
# - password_reset_confirm checks the link the user clicked and
#   prompts for a new password
# - password_reset_complete shows a success message for the above

@csrf_protect
def password_reset(request, is_admin_site=False, template_name='registration/password_reset_form.html',
        domain_override='example.com',
        email_template_name='registration/password_reset_email.html',
        password_reset_form=PasswordResetForm, token_generator=default_token_generator,
        post_reset_redirect=None):
    if post_reset_redirect is None:
        post_reset_redirect = reverse('drawquest.apps.drawquest_auth.views.password_reset_done')
    if request.method == "POST":
        form = password_reset_form(request.POST)
        if form.is_valid():
            opts = {}
            opts['use_https'] = request.is_secure()
            opts['token_generator'] = token_generator
            opts['email_template_name'] = email_template_name
            opts['request'] = request
            if domain_override:
                opts['domain_override'] = domain_override
            if is_admin_site:
                opts['domain_override'] = request.META['HTTP_HOST']
            form.save(**opts)
            return HttpResponseRedirect(post_reset_redirect)
    else:
        form = password_reset_form()
    return r2r_jinja(template_name, {'form': form}, request)

def password_reset_done(request, template_name='registration/password_reset_done.html'):
    return r2r_jinja(template_name, {}, request)

@never_cache
def password_reset_confirm(request, uidb36=None, token=None, template_name='registration/password_reset_confirm.html',
                           token_generator=default_token_generator, set_password_form=SetPasswordForm,
                           post_reset_redirect=None):
    """
    View that checks the hash in a password reset link and presents a
    form for entering a new password.
    """
    assert uidb36 is not None and token is not None # checked by URLconf
    if post_reset_redirect is None:
        post_reset_redirect = reverse('drawquest.apps.drawquest_auth.views.password_reset_complete')
    try:
        uid_int = base36_to_int(uidb36)
        user = User.objects.get(id=uid_int)
    except (ValueError, User.DoesNotExist):
        user = None

    ctx = {}

    if user is not None and token_generator.check_token(user, token):
        ctx['validlink'] = True
        if request.method == 'POST':
            form = set_password_form(user, request.POST)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(post_reset_redirect)
        else:
            form = set_password_form(None)
    else:
        ctx['validlink'] = False
        form = None
    ctx['form'] = form
    return r2r_jinja(template_name, ctx, request)

def password_reset_complete(request, template_name='registration/password_reset_complete.html'):
    return r2r_jinja(template_name, {'login_url': settings.LOGIN_URL}, request)

