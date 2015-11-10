import urllib

from django.contrib import auth
from django.db import IntegrityError
from django.http import HttpResponseRedirect, HttpResponseServerError, Http404, HttpResponse
from django.views.decorators.csrf import csrf_exempt

from apps.canvas_auth.models import User
from apps.ip_blocking.view_guards import require_unblocked_ip
from canvas import bgwork, util, economy, experiments, after_signup, knobs
from canvas.exceptions import ServiceError, NotLoggedIntoFacebookError
from canvas.forms import validate_and_clean_comment
from canvas.metrics import Metrics
from canvas.models import Comment, FacebookInvite, InviteCode, UserInfo, Category, FollowCategory
from canvas.shortcuts import r2r_jinja, r2r
from canvas.util import base36encode
from canvas.view_guards import require_user, require_staff, require_secure
from canvas.view_helpers import check_rate_limit
from configuration import Config
from django.conf import settings


@csrf_exempt
@require_unblocked_ip
@require_secure
def signup(request, skip_invite_code=None, template="signup/signup.html", success_redirect="/onboarding/start"):
    cookies_to_delete = []
    cookies_to_set = {}

    error_context = get_signup_context(request, skip_invite_code, template,
                                       cookies_to_set, cookies_to_delete)

    Metrics.signup_form_view.record(request)

    def process_response(response):
        for key in cookies_to_delete:
            response.delete_cookie(key)
        for key, val in cookies_to_set.items():
            response.set_cookie(key, val)
        return response

    if not error_context:
        # error_context is only None if this is a POST (and with no errors).
        # DEPRECATED: next and next_params. we use cookies for these now - see get_signup_context
        if request.POST.get('next'):
            next_params = request.POST.get('next_params', '')
            if next_params:
                next_params = '?' + next_params
            success_redirect = request.POST['next']
            return process_response(HttpResponseRedirect(success_redirect + next_params))
        return process_response(HttpResponseRedirect(success_redirect))
    else:
        request.session['failed_signup'] = True

    if template == "signup_prompt.django.html":
        return process_response(r2r(template, error_context))
    return process_response(r2r_jinja(template, error_context, request))

def post_comment(request, user, post_data, persist_url=True):
    reply_text = post_data.get('reply_text', '')

    try:
        replied_comment, parent_comment, reply_content, external_content, category, title = (
            validate_and_clean_comment(
                user,
                reply_text=reply_text,
                parent_comment=post_data.get('parent_comment'),
                replied_comment=post_data.get('replied_comment'),
                reply_content=post_data.get('reply_content'),
                category=post_data.get('category'),
                external_content=post_data.get('external_content'),
                title=post_data.get('title'),
            )
        )

        post_anon = True
        if category and category == MONSTER_GROUP:
            post_anon = False

        comment = Comment.create_and_post(
            request,
            user,
            post_anon, # Anonymous.
            category,
            reply_content,
            parent_comment=parent_comment,
            reply_text=reply_text,
            replied_comment=replied_comment,
            external_content=external_content,
            title=title,
        )

        post_pending_url = comment.details().url

        if persist_url:
            if category and category.name == MONSTER_GROUP:
                post_pending_url = '/monster/{0}'.format(base36encode(comment.thread.op.id))
            user.kv.post_pending_signup_url.set(post_pending_url)

        return comment

    except ServiceError, e:
        # Silently drop the post if an error occurs.
        # We tried validating it prior to posting, but something went wrong between then and now
        # and it no longer validates. Should be rare.
        Metrics.logged_out_reply_dropped.record(request, extra_info=extra_info, service_error=e)

def get_signup_context(request, skip_invite_code=None, template="user/signup.django.html",
                       cookies_to_set={}, cookies_to_delete=[]):
    """
    Returns an error context (or dict) if the signup is not successful.

    Returns `None` for successful signups.

    `cookies_to_set` and `cookies_to_delete` should be passed empty so that this functin may append to them.
    `cookies_to_set` is for session cookies, to tie into after_signup.py / after_signup.js.
    """
    skip_invite_code = skip_invite_code or request.GET.get('skip_invite_code', '').lower()
    bypass_copy = settings.SHORT_CODE_COPY.get(skip_invite_code)
    skippable_codes = (['dicksoup', 'angelgate', 'friends_and_family', 'herpderp', 'fffffat', 'buzzfeedbrews']
                       + settings.SHORT_CODES)

    login_url = '/login'
    if request.REQUEST.get('next'):
        next = request.REQUEST['next']
        params = [urllib.urlencode({'next': next})]
        if request.method == 'POST':
            next_params = request.POST.get('next_params', '')
        else:
            next_params = request.GET.copy()
            del next_params['next']
            next_params = urllib.urlencode(next_params)
        if next_params:
            params.append(next_params)
        login_url = login_url + '?' + u'&'.join(params)

    try:
        fb_user, fb_api = util.get_fb_api(request)
    except NotLoggedIntoFacebookError:
        fb_user, fb_api = None, None

    fb_uid = fb_user.get('uid') if fb_user else None
    fb_invite = None
    if request.COOKIES.get('fb_message_id'):
        fb_invite = FacebookInvite.objects.get_or_none(fb_message_id=request.COOKIES.get('fb_message_id'))
        cookies_to_delete.append('fb_message_id')

    if not fb_invite and fb_uid:
        fb_invite = FacebookInvite.get_invite(fb_user.get('uid'))

    if request.method == 'GET':
        return locals()

    username = request.POST.get('username', '')
    password = request.POST.get('password', '')
    email = request.POST.get('email', '')
    if not fb_uid:
        fb_uid = request.POST.get('facebook_id', None)

    code = InviteCode.objects.get_or_none(code=request.POST.get('code'))

    def error(message, context=locals()):
        context['message'] = message
        Metrics.signup_form_invalid.record(request)
        return context

    if check_rate_limit(request, username):
        return error("Too many failed signup attempts. Wait a minute and try again.")

    if not password:
        return error("Password required.")
    if not User.validate_password(password):
        return error("Sorry, your password is too short. Please use 5 or more characters.")

    error_msg = User.validate_username(username)
    if error_msg:
        return error(error_msg)

    if not User.validate_email(email):
        return error("Please enter a valid email address.")

    if not User.email_is_unused(email):
        return error("This email address is already in use. Try <a href='/login'>signing in</a> "
                    "or <a href='/password_reset'>resetting</a> your password if you've forgotten it.")

    if fb_uid and not UserInfo.facebook_is_unused(fb_uid):
        return error("This Facebook account is already in use. Try <a href='/login'>signing in</a> "
                    "or <a href='/password_reset'>resetting</a> your password if you've forgotten it.")

    try:
        user = User.objects.create_user(username, email, password)
    except IntegrityError:
        return error("Username taken.")

    if not fb_uid:
        fb_uid = None

    UserInfo(user=user, invite_bypass=skip_invite_code,
             facebook_id=fb_uid, enable_timeline=True).save()

    if code:
        code.invitee = user
        code.save()

    if fb_invite:
        fb_invite.invitee = user
        fb_invite.save()

    user = auth.authenticate(username=username, password=password)

    # Handle following featured groups and optionally one defined by their short code.
    if skip_invite_code:
        autofollow = settings.SHORT_CODE_AUTOFOLLOW.get(skip_invite_code)
        if autofollow:
            to_follow.append(autofollow)

    economy.grant_daily_free_stickers(request.user, force=True, count=knobs.SIGNUP_FREE_STICKERS)

    # Follow the Canvas account.
    try:
        user.redis.following.sadd(User.objects.get(username=settings.CANVAS_ACCOUNT_USERNAME).id)
    except User.DoesNotExist:
        pass

    # Logged-out remix?
    cookie_key, post_data = after_signup.get_posted_comment(request)
    if post_data:
        post_comment(request, user, post_data)
        cookies_to_delete.append(cookie_key)

    inviter_id = request.session.get('inviter')
    if inviter_id:
        user.kv.inviter = inviter_id
        del request.session['inviter']

        inviter = User.objects.get(pk=inviter_id)
        user.follow(inviter)
        inviter.follow(user)

    # DEPRECATED. Use after_signup.py / after_signup.js now instead.
    extra_info = request.POST.get("info")
    if extra_info:
        extra_info = util.loads(extra_info)

        if extra_info.get('in_flow') == 'yes':
            fact.record('flow_signup', request, {})

        # A user may have come to signup by remixing/replying, and we've got their post data to submit and send them
        # to.
        if not post_data:
            post_data = extra_info.get('post')
            if post_data:
                post_comment(request, user, post_data)

    old_session_key = request.session.session_key

    def _after_signup():
        if fb_api:
            app_requests = fb_api.get_object('/me/apprequests/').get('data', [])
            for app_request in app_requests:
                if id in app_request:
                    fb.delete_object(app_request['id'])

        Metrics.signup.record(request, old_session_key=old_session_key, username=username, email=email)

        if 'failed_signup' in request.session:
            del request.session['failed_signup']
            Metrics.signup_second_try.record(request)

        if template == 'signup/_signup_prompt.html':
            Metrics.signup_prompt.record(request)
        else:
            Metrics.signup_main.record(request)

    bgwork.defer(_after_signup)

    # auth.login starts a new session and copies the session data from the old one to the new one
    auth.login(request, user)

    experiments.migrate_from_request_to_user(request, user)
