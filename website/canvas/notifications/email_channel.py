import logging
import os
import string
import time
from urllib import urlencode
import uuid

from django.conf import settings
from django.core.mail.message import EmailMultiAlternatives
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
import yaml

from canvas import knobs, util, experiments
from canvas.notifications.base_channel import CommunicationsChannel
from canvas.notifications.beautiful_premailer import beautiful_premailer as premailer
from services import Services


class EmailMessage(object):
    def __init__(self, from_email, to_email, subject, body_html, body_text, recipient, guid, unsubscribe_links):
        self.to_email = to_email
        self.from_email = from_email
        self.subject = subject
        self.body_text = body_text or ""
        self.raw_body_html = body_html
        self.inline_the_styles()
        self.unsubscribe_links = unsubscribe_links

        self._recipient = recipient
        self._guid = guid

    def record_sent(self, action):
        Services.metrics.email_sent.record(self._recipient, guid=self._guid, action=action)

    def inline_the_styles(self):
        self.body_html = premailer.transform(self.raw_body_html, base_url="http://" + settings.DOMAIN + "/")

    def __repr__(self):
        # Printing thie email message in Yaml makes it easy to read on the debug console.
        return yaml.dump(dict(to_email=self.to_email, subject=self.subject, body=self.body_html),
                         default_flow_style=False)


class EmailChannel(CommunicationsChannel):
    recipient_actions = settings.EMAIL_CHANNEL_ACTIONS['recipient']
    actor_actions = settings.EMAIL_CHANNEL_ACTIONS['actor']

    def get_overriden_template_file(self, action, template_type):
        try:
            return knobs.OVERRIDE_NOTIFICATION_TEMPLATE.get(self.__class__.__name__).get(action).get(template_type)
        except (KeyError, AttributeError,):
            pass

    @classmethod
    def enabled_for_recipient_action(cls, action, recipient, pending_notification=None, *args, **kwargs):
        flag = super(EmailChannel, cls).enabled_for_recipient_action(action, recipient, *args, **kwargs)

        # The user must have an email address.
        flag = flag and bool(recipient.email)

        # and be an active user
        flag = flag and recipient.is_active

        if (flag
                and pending_notification
                and hasattr(pending_notification, 'comment')
                and hasattr(pending_notification.comment, 'thread')):
            # Did the user mute this thread? The email channel is the only channel
            # that can mute specific threads.
            return not pending_notification.comment.thread.op.id in recipient.redis.muted_threads
        return flag

    @classmethod
    def enabled_for_actor_action(cls, action, actor, *args, **kwargs):
        return (super(EmailChannel, cls).enabled_for_actor_action(action, actor, *args, **kwargs)
                and actor.email)

    def _digest_extra_context(self, notification):
        recipient = notification.recipient

        from canvas.models import Comment, Category
        from canvas.browse import get_front_comments, Navigation
        now = Services.time.today()
        nav = Navigation(
            category=Category.ALL,
            sort='top',
            offset=0,
            month=now.month,
            year=now.year,
        )
        featured_comments = get_front_comments(recipient, nav)[:knobs.TWENTYFOUR_HOUR_EMAIL_COMMENT_COUNT]
        featured_comments = [cmt.details() for cmt in featured_comments]

        return {
            'recipient': recipient,
            'featured_comments': featured_comments,
        }

    def make_message(self, notification, force=False):
        # This is a hack to get around circular imports.
        from canvas.templatetags.jinja_base import render_jinja_to_string

        action = notification.action

        guid = str(uuid.uuid1())

        action_unsubscribe_link = self.make_action_unsubscribe_link(action, notification.recipient)
        # In the future, use "*_url" for URLs as a standard convention, not "_link".
        unsubscribe_links = {'action_unsubscribe_link': action_unsubscribe_link}

        comment = getattr(notification, 'comment', None)
        if comment:
            thread_unsubscribe_link = self.make_thread_unsubscribe_link(comment, notification.recipient)
            unsubscribe_links['thread_unsubscribe_link'] = thread_unsubscribe_link

        tracking_query = urlencode({
            'ct': 'email',
            'ct_action': action,
            'ct_guid': guid,
            'ct_user_id': notification.recipient.id,
        })

        # Get Comment or None for the post being replied/remixed
        recipient_comment = {
            'remixed': lambda: comment.reply_content.remix_of.first_caption,
            'replied': lambda: comment.replied_comment,
            'thread_replied': lambda: comment.parent_comment,
        }.get(notification.action, lambda: None)()
        if recipient_comment:
            recipient_comment = recipient_comment.details()

        context = {
            'notification': notification,
            'tracking_query': tracking_query,
            'recipient_comment': recipient_comment,
            'timestamp': time.time(),
            'comments_exist': notification.recipient.comments.exists(),
        }
        context.update(unsubscribe_links)

        context.update(getattr(self, '_{0}_extra_context'.format(action), lambda _: {})(notification))

        # Grab the template
        text_template = (self.get_overriden_template_file(action, "text")
                         or "email/%s.txt" % action)

        html_template = (self.get_overriden_template_file(action, "body")
                         or "email/%s.html" % action)

        subject_template = (self.get_overriden_template_file(action, "subject")
                            or "email/%s_subject.txt" % action)

        # Render it.
        subject = render_to_string(subject_template, context).strip()
        try:
            text = render_to_string(text_template, context)
        except TemplateDoesNotExist:
            text = ""
        html = render_jinja_to_string(html_template, context)

        # Separate Gmail threads based on post_id by altering the subject line
        if recipient_comment:
            thread_id = recipient_comment.id
            if thread_id:
                subject = u''.join([subject, ' (post #', str(thread_id), ')'])

        return EmailMessage(from_email=settings.UPDATES_EMAIL,
                            to_email=notification.recipient.email,
                            subject=subject,
                            body_html=html,
                            body_text=text,
                            recipient=notification.recipient,
                            guid=guid,
                            unsubscribe_links=unsubscribe_links)

    def make_email_backend_message(self, email_message):
        """
        Given an instance of EmailMessage, returns a Django/Email backend email message. This allows us to test the
        unsubscription logic.
        """
        headers = {'List-Unsubscribe': email_message.unsubscribe_links.get("action_unsubscribe_link")}
        mail = EmailMultiAlternatives(email_message.subject, email_message.body_text,
                                      email_message.from_email, [email_message.to_email],
                                      headers=headers)
        mail.attach_alternative(email_message.body_html, "text/html")
        return mail

    def deliver_message(self, email_message):
        # Note that the unsubscribe header link will unsubcribe from the "action"
        # Ie, if you hit "usubscribe" in Gmail on a remix notification, you will never
        # receive email notificiations anymore.
        mail = self.make_email_backend_message(email_message)

        if settings.DEBUG:
            email_path = "/var/canvas/website/run/email"
            if not os.path.exists(email_path):
                os.mkdir(email_path)

            file(os.path.join(email_path, repr(time.time()) + ".html"), 'w').write(email_message.body_html)

        try:
            mail.send()
        except Exception, e:
            #TODO change this catch-all except to use specific exception types, and add an exception type for
            # address blacklisting.
            if hasattr(e, 'error_message') and e.error_message == "Address blacklisted.":
                # This email address has issued a bounce in the last 14 days, but they may work again later.
                return
            else:
                # Resend once for transient network issues
                mail.send()

    def deliver(self, notification_entry):
        """
        `generic_queue_entry`:
            An instance of NotificationQueueEntry
        """
        message = self.make_message(notification_entry)
        if message:
            self.deliver_message(message)
            message.record_sent(action=notification_entry.action)

    def make_action_unsubscribe_link(self, action, recipient):
        if settings.PROJECT == 'drawquest':
            #TODO individual action unsubscriptions: action instead of 'ALL'
            return '{}/unsubscribe?action={}&token={}&email={}'.format("http://" + settings.DOMAIN, 'ALL', util.token(recipient.email), recipient.email)
        else:
            return string.Template("$absolute_path/unsubscribe?action=$action&token=$token&user_id=$user_id").substitute(
                dict(absolute_path="http://" + settings.DOMAIN,
                     action=action,
                     user_id=recipient.id,
                     token=util.token(recipient.id)),
            )

    def make_thread_unsubscribe_link(self, comment, recipient):
        return string.Template("$absolute_path/unsubscribe?post=$post&token=$token&user_id=$user_id").substitute(
            dict(absolute_path="http://" + settings.DOMAIN,
                 post=comment.thread.op.id,
                 user_id=recipient.id,
                 token=util.token(recipient.id)),
        )

