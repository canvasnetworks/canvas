from django.core.urlresolvers import reverse
from jinja2 import Markup

from canvas import knobs
from canvas.details_models import CommentDetails
from canvas.metrics import Metrics
from canvas.models import Visibility
from canvas.util import strip_template_chars
from django.conf import settings


class TemplateComment(CommentDetails):
    """
    Wrap comment details in this and then add helper methods here to use in the template, instead of having lots of
    logic in the tag.

    This allows for organized re-use of logic, and makes it much easier to test.
    """
    def __init__(self, comment_details, request_context=None, is_op=False, request=None, title=None):
        """
        `request_context`:
            An instance of RequestContext.
        """
        super(TemplateComment, self).__init__(comment_details.to_backend())
        self.context = request_context
        self.request = self.context.get('request') if self.context else request
        self._is_op = is_op
        self.thread_title = title

    def is_op(self):
        return self._is_op

    def get_mod_classes(self):
        mod_classes = set()
        for name in ["downvoted", "inappropriate", "offtopic", "disabled", "removed", "collapsed"]:
            if getattr(self, "is_%s" % name):
                mod_classes.add(name)
        # Removed posts also get the disabled class.
        if "removed" in mod_classes:
            mod_classes.add("disabled")
        return " ".join(mod_classes)

    def get_collapsed_text(self):
        lookup = {
            'removed': 'This post was deleted by its author.',
            'disabled': 'This post has been disabled.',
            'inappropriate': 'This post has been flagged as inappropriate. Click to show.',
            'offtopic': 'This post was marked off-topic by a group referee. Click to show.',
            'downvoted': 'This post is hidden due to downvotes. Click to show.',
        }
        # Note that removed takes precedence.
        for name in ["removed", "downvoted", "inappropriate", "offtopic", "disabled", "collapsed"]:
            if getattr(self, "is_%s" % name):
                return lookup[name]
        return ''

    def is_viewable(self):
        return self.visibility not in [Visibility.DISABLED, Visibility.UNPUBLISHED]

    @property
    def autoplay(self):
        goto_reply = self.context.get('gotoreply')

        if goto_reply is None:
            return self.is_op()

        return int(goto_reply) == int(self.id)

    def timestamp_link_url(self):
        return self.share_page_url

    def is_animated(self):
        return bool(self.reply_content['original'].get('animated'))

    def get_img_tag(self, fullsize=None, image_type=None):
        if image_type is None:
            image_type = "giant" if fullsize else "column"
            # Note that the "original", "giant", and "columns" parts of Content details was set by
            # thumbnailer.create_content.

        display_image_type = image_type
        if fullsize and self.is_animated() and self.autoplay:
            display_image_type = 'ugc_original'

        try:
            requested = self.reply_content[image_type]
            src = self.reply_content[display_image_type]['name']
            height, width = requested['height'], requested['width']
        except KeyError:
            if self.context:
                Metrics.image_missing.record(self.context['request'], content_details=self.reply_content)
            src, height, width = '', '', ''

        img = '<img id="{0}" class="comment-image" src="{1}" height="{2}" width="{3}">'
        img = img.format(self.reply_content_id, src, height, width)
        return Markup(img)

    @property
    def show_delete_option(self):
        """ Can this tile be deleted by the current user? """
        return self.context.get("show_delete_option", False) and self.is_viewable()

    @property
    def show_claim_option(self):
        """ Can this tile be claimed by the current user? """
        return self.context.get("show_delete_option", False) and self.is_anonymous

    def get_user_url(self):
        """
        Gets the url of the comment author. It handles whether the current user is allowed to reveal the identify
        of an anonymous poster. Only Canvas team members can see profile links to anonymous post authors.

        Returns `None` if the viewer is not staff and the comment is anonymous.
        """
        # Is the current_user staff?
        viewer_is_staff = self.request.user.is_staff

        # Is this an anonymous post?
        if not self.is_anonymous:
            return reverse('user_link', args=[self.author_name])
        elif viewer_is_staff:
            # Then the context has user_infos since this is an admin.
            if self.context.get('admin_infos'):
                admin_infos = self.context.get('admin_infos').get(self.id)
                author_name = admin_infos.get('username')
                return reverse('user_link', args=[author_name])

    def get_remix_link(self):
        if self.is_animated() or self['external_content']:
            return Markup("javascript:action.audio_remix('%s', '%s'); if (thread && thread.pw) { thread.pw.remix_started(); }" % (self['id'], self.reply_content['id']))
        else:
            return Markup("javascript:action.remix('%s'); if (thread && thread.pw) { thread.pw.remix_started(); }" % (self.reply_content['id']))

    def get_new_remix_link(self):
        if self.is_animated() or self['external_content']:
            return Markup("javascript:action.audio_remix('%s', '%s'); if (thread_new && thread_new.pw) { thread_new.pw.remix_started(); }" % (self['id'], self.reply_content['id']))
        else:
            return Markup("javascript:action.remix('%s'); if (thread_new && thread_new.pw) { thread_new.pw.remix_started(); }" % (self.reply_content['id']))

    def get_replied_text(self):
        replied_text = "@%s" % self.replied_comment['author_name']
        if self.reply_text:
            replied_text += ":"
        return replied_text

    @property
    def remix_text(self):
        return self.reply_content_id and self.reply_content['remix_text'] or None

    def shareable_metadata(self):
        title = 'Canvas'

        if self.thread_title:
            title = strip_template_chars(self.thread_title)
        elif self.title:
            title = strip_template_chars(self.title)
        elif self.category:
            title += ' | Posted in #' + self.category

        description = self.reply_text or self.remix_text or knobs.TAGLINE

        # Suppress flagged comments. Ie, comments that are not public.
        if self.is_inappropriate or self.is_disabled or self.is_removed:
            description = ''

        image = None
        if self.reply_content_id:
            # Get the largest thumbnail we can, from the list of candidates.
            image_data = {}
            for image_type in knobs.FACEBOOK_SHARE_IMAGE_TYPE:
                try:
                    image_data = self.reply_content[image_type]
                except IndexError:
                    continue
                if not image_data:
                    continue
                if image_data['kb'] < knobs.FACEBOOK_SHARE_IMAGE_SIZE_CUTOFF:
                    break
            image = image_data.get('name')

        return {
            'title': title,
            'description': strip_template_chars(description.strip()),
            'image': image,
        }

