from django.contrib.auth import logout
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.decorators.http import require_http_methods

from canvas import views
from canvas.models import Category, EmailUnsubscribe
from canvas.shortcuts import r2r
from canvas.view_guards import require_POST, require_user
from forms import (EmailChangeForm, PasswordChangeForm, SubscriptionForm,
                   SecureOnlyForm, BrowsingSettingsForm, ConnectionsForm)
from models import EmailConfirmation


@require_user
def user_settings(request, post_change_redirect=None):
    user = request.user

    if post_change_redirect is None:
        post_change_redirect = reverse('apps.user_settings.views.user_settings')

    if request.method == 'POST':
        resp = HttpResponseRedirect(post_change_redirect)

        pw_form = PasswordChangeForm(user, data=request.POST)
        email_form = EmailChangeForm(user=user, data=request.POST)
        subscription_form = SubscriptionForm(user=user, data=request.POST)
        https_form = SecureOnlyForm(request.user, request.COOKIES, http_response=resp, data=request.POST)
        browsing_form = BrowsingSettingsForm(user, data=request.POST)
        connections_form = ConnectionsForm(user, data=request.POST)
        all_forms = [pw_form, email_form, subscription_form, https_form, browsing_form, connections_form]
        views.handle_unsubscribe_post(user, request.REQUEST, request)

        if all(form.is_valid() for form in all_forms):
            for form in all_forms:
                form.save()

            if pw_form.password_changed():
                request.session['password_updated'] = True
            return resp

    else:
        pw_form = PasswordChangeForm(user)
        email_form = EmailChangeForm(user=user)
        subscription_form = SubscriptionForm(user=user, initial={
            'newsletter': not EmailUnsubscribe.objects.get_or_none(email=user.email),
        })
        https_form = SecureOnlyForm(user, request.COOKIES)
        browsing_form = BrowsingSettingsForm(user)
        connections_form = ConnectionsForm(user)
        all_forms = [pw_form, email_form, subscription_form, https_form, browsing_form, connections_form]

    context = {
        'pw_form': pw_form,
        'email_form': email_form,
        'subscription_form': subscription_form,
        'https_form': https_form,
        'browsing_form': browsing_form,
        'all_forms': all_forms,
        'connections_form': connections_form,
        'is_staff': request.user.is_staff,
        'email_confirmation': EmailConfirmation.objects.get_or_none(user=user),
        'unsubscribed_settings': views.get_unsubscriptions(user),
    }

    def handle_updated_field(name):
        if request.session.get(name, False):
            context[name] = True
            del request.session[name]

    map(handle_updated_field, ['email_updated', 'password_updated'])

    return render_to_response('user/settings.django.html', context,
                              context_instance=RequestContext(request))

def confirm_email(request, confirmation_key):
    '''
    Confirms the new email address for a user.
    '''
    confirmation_key = confirmation_key.lower()
    confirmation = EmailConfirmation.objects.confirm_email(
        confirmation_key)

    if confirmation is None:
        return render_to_response('user_settings/invalid_confirmation_key.django.html', context_instance=RequestContext(request))

    request.session['email_updated'] = True

    return HttpResponseRedirect(reverse('apps.user_settings.views.user_settings'))

@require_user
def cancel_email_confirmation(request, confirmation_key):
    confirmation_key = confirmation_key.lower()
    confirmation = get_object_or_404(EmailConfirmation,
                                     confirmation_key=confirmation_key,
                                     user=request.user)
    confirmation.delete()
    return HttpResponseRedirect(reverse('apps.user_settings.views.user_settings'))

@require_user
@require_POST
def disable_account(request):
    user = request.user
    logout(request)
    user.is_active = False
    user.save()
    return HttpResponseRedirect('/')

