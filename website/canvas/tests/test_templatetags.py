import datetime

from django.core.urlresolvers import reverse
from django.utils.html import strip_tags

from canvas.tests.tests_helpers import (CanvasTestCase, create_comment, create_content, create_group, create_user,
                                        create_staff, FakeRequest)
from canvas import util, stickers, knobs
from canvas.browse import TileDetails, LastReplyTileDetails
from canvas.models import AnonymousUser, Comment, Visibility
from canvas.templatetags import jinja_tags
from canvas.templatetags.helpers import TemplateComment
from canvas.templatetags.jinja_base import get_jinja_tags_modules
from canvas.templatetags.jinja_tags import _fit_inside, _fit_width, _fit_height
from canvas.util import render_template_tag, _template_tag_cache, strip_template_chars
from canvas.view_helpers import tile_render_options
from services import Services, override_service, FakeTimeProvider


class TemplateTagTestCase(CanvasTestCase):
    def _has(self, html, items):
        for t in items:
            self.assertTrue(t in html, u"The rendered templatetag is missing text: \"{0}\"".format(t))

    def _has_not(self, html, items):
        for t in items:
            self.assertFalse(t in html, u"The rendered templatetag includes text it should not: \"{0}\"".format(t))


class TestJinjaBase(CanvasTestCase):
    def test_module_locator(self):
        modules = get_jinja_tags_modules()
        self.assertTrue('canvas.templatetags.jinja_tags' in modules)
        self.assertFalse('canvas.templatetags.canvas_tags' in modules)


class TestStickerTags(TemplateTagTestCase):
    def test_sticker_image(self):
        banana = stickers.get("banana")
        tag = jinja_tags.sticker_image(banana)
        self.assertNumCssMatches(1, tag, '.banana')

    def test_sticker_image_by_id(self):
        banana = stickers.get("banana")
        tag = jinja_tags.sticker_image(banana.type_id)
        self.assertNumCssMatches(1, tag, '.banana')

    def test_sticker_image_with_size(self):
        banana = stickers.get("banana")
        tag = jinja_tags.sticker_image(banana, image_size="original")
        self.assertNumCssMatches(1, tag, '.banana')
        self.assertNumCssMatches(1, tag, '.original')


class TestThreadTags(TemplateTagTestCase):
    def _render_post(self, post, fullsize=False, for_user=None):
        for_user = for_user or AnonymousUser()
        context = {'request': FakeRequest(for_user)}
        return jinja_tags.jinja_thread_comment(context, post.details(), fullsize)

    def _render_replies(self, replies):
        context = {'request': FakeRequest(create_user())}
        return jinja_tags.jinja_thread_comments(context, [c.details() for c in replies])

    def test_standard_op(self):
        comment = create_comment(reply_content=create_content(), reply_text="hello friends")
        post = self._render_post(comment, fullsize=True)

        self.assertNumCssMatches(1, post, '.has_content')
        self.assertNumCssMatches(1, post, '.op.expanded')
        self.assertNumCssMatches(1, post, 'div.reply_content')

    def test_standard_reply(self):
        comment = create_comment(reply_content=create_content(), reply_text="hello friends")
        post = self._render_post(comment, fullsize=False)

        self.assertNumCssMatches(1, post, '.has_content')
        self.assertNumCssMatches(0, post, '.op.expanded')
        self.assertNumCssMatches(1, post, 'div.reply_content')

    def test_text_reply(self):
        comment = create_comment(reply_content=create_content(), reply_text="hello friends")
        reply = create_comment(reply_text="reply!", parent_comment=comment)
        post = self._render_post(reply, fullsize=False)

        self.assertNumCssMatches(0, post, '.has_content')
        self.assertNumCssMatches(0, post, '.op.expanded')
        self.assertNumCssMatches(0, post, 'div.reply_content')

    def test_replies_have_no_op_class(self):
        comment = create_comment(reply_content=create_content(), reply_text="hello friends")
        reply = create_comment(reply_text="reply!", parent_comment=comment)
        reply2 = create_comment(reply_text="another", parent_comment=comment)
        posts = self._render_replies([reply, reply2])

        self.assertNumCssMatches(0, posts, '.op.expanded')

    def test_slider_absence(self):
        comment = create_comment(reply_content=create_content(), reply_text="hello friends")
        posts = self._render_replies([comment])
        self.assertNumCssMatches(0, posts, '.remix_parent')

# These need to be updated for explore tiles
#
# class TestCommentTags(TemplateTagTestCase):
#     def setUp(self):
#         super(TestCommentTags, self).setUp()
#         self.render_options = {
#             'image_type': 'column',
#             'show_timestamp': True,
#         }

#     def _render_tile(self, comment, nav_category=None, tag_name='image_tile', user=None, show_pins=False,
#                      details_cls=TileDetails):
#         nav_category = nav_category or create_group()
#         request = FakeRequest(user)
#         render_options = self.render_options.copy()
#         render_options['show_pins'] = show_pins
#         return jinja_tags.explore_tile({'request': request},
#                                      details_cls.from_comment_id(comment.id),
#                                      render_options,
#                                      nav_category.details())

#     def _render_tiles(self, comments, nav_category=None, sort='hot', user=None, show_pins=False):
#         render_options = tile_render_options(sort, show_pins)
#         nav_category = nav_category or create_group()
#         request = FakeRequest(user)

#         return jinja_tags.explore_tiles({'request': request},
#                                             TileDetails.from_queryset_with_pins(comments),
#                                             render_options,
#                                             nav_category.details())

#     def test_image_tile(self):
#         text = 'the comment text!'
#         content = create_content()
#         category = create_group(name='foo')
#         current_nav = create_group(name='bar')
#         parent = create_comment()
#         comment = create_comment(reply_text=text,
#                                 reply_content=content,
#                                 category=category,
#                                 parent_comment=parent)

#         tile = self._render_tile(comment, nav_category=current_nav)

#         # Has.
#         self._has(tile, ['image_tile',
#                         'post_{0}'.format(comment.id),
#                         comment.get_absolute_url(),
#                         '<img',
#                         getattr(content.details(), self.render_options['image_type'])['name'],
#                         'class="sticker_float"',
#                         'data-category="{0}"'.format(category.name),
#                         category.get_absolute_url(),
#                         text])

#         # Has not.
#         self._has_not(tile, ['data-category="{0}"'.format(current_nav.name),
#                             'op_wrapper',
#                             'op_image',
#                             'new_activity',
#                             'text_only',])

#         self.assertFalse(self.css_select(tile, 'div.downvoted'))

#         # Check the details JSON.
#         details = util.loads(self.css_select(tile, '.image_tile')[0].attrib['data-details'])
#         self.assertEqual(details['url'], comment.get_absolute_url())

#     def test_image_tile_in_reply_to(self):
#         with override_service('time', FakeTimeProvider):
#             content = create_content()
#             comment = create_comment(reply_content=content)
#             reply = create_comment(parent_comment=comment, timestamp=Services.time.time())

#             tile = self._render_tile(comment, details_cls=LastReplyTileDetails)

#             # Has.
#             self._has(tile, ['post_{0}'.format(reply.id),
#                              '"{0}?nav='.format(reply.get_absolute_url())])

#             # Has not.
#             self._has_not(tile, ['single_post_info',])

#     def test_image_tile_pinned(self):
#         user = create_user()
#         comment = create_comment()
#         tile = self._render_tile(comment, user=user, show_pins=True)
#         self.assertEqual(len(self.css_select(tile, '.pinned')), 0)

#         result = self.api_post('/api/comment/pin', {'comment_id': comment.id}, user=user)
#         tile = self._render_tile(comment, user=user, show_pins=True)
#         self.assertEqual(len(self.css_select(tile, '.pinned')), 1)

#     def test_image_tile_pinned_parent(self):
#         user = create_user()
#         parent = create_comment()
#         comment = create_comment(parent_comment=parent)
#         tile = self._render_tile(comment, user=user, show_pins=True)
#         self.assertEqual(len(self.css_select(tile, '.pinned')), 0)

#         result = self.api_post('/api/comment/pin', {'comment_id': parent.id}, user=user)
#         tile = self._render_tile(comment, user=user, show_pins=True)
#         self.assertEqual(len(self.css_select(tile, '.pinned')), 1)

#     def test_image_tile_sticker_float_with_last_reply(self):
#         """
#         user = create_user()
#         for i, (expected, comment) in enumerate([
#                 (0, create_comment()),
#                 (1, create_comment(reply_content=create_content(), reply_text='foo')),
#                 (0, create_comment(reply_content=create_content(), reply_text='')),
#                 (0, create_comment(reply_content=create_content(), reply_text='', parent_comment=create_comment())),
#                 (1, create_comment(reply_content=create_content(), reply_text='foo',
#                                     parent_comment=create_comment())),
#                 (0, create_comment(reply_content=None, reply_text='', parent_comment=create_comment())),]):
#             tile = self._render_tile(comment.thread.op, user=user, details_cls=LastReplyTileDetails)
#             actual = len(self.css_select(tile, '.sticker_float'))
#             self.assertEqual(actual, expected, "Got %s, expected %s at index %s" % (actual, expected, i))
#         """

#     #TODO
#     #def test_image_tile_with_curated_last_reply(self):
#     #    pass

#     def _assert_class(self, comment, class_name, has_class=True):
#         return getattr(self, 'assert{0}'.format(has_class))(
#                 self.css_select(self._render_tile(comment), 'div.{0}'.format(class_name)))

#     def test_image_tile_visibility_downvoted(self):
#         comment = create_comment()
#         for _ in xrange(Comment.DOWNVOTES_REQUIRED):
#             self._assert_class(comment, 'downvoted', False)
#             comment.downvote(create_user())
#         self._assert_class(comment, 'downvoted', True)

#     def test_image_tile_visibility_inappropriate(self):
#         comment = create_comment()
#         self._assert_class(comment, 'inappropriate', False)

#         comment.add_flag(create_user())
#         comment.moderate_and_save(Visibility.HIDDEN, comment.author)
#         comment = Comment.all_objects.get(pk=comment.pk)
#         self.assertTrue(comment.is_inappropriate())
#         self._assert_class(comment, 'inappropriate', True)

#     def test_image_tile_visibility_offtopic(self):
#         user, group = create_user(), create_group()
#         group.moderators.add(user)
#         comment = create_comment(category=group)
#         self._assert_class(comment, 'offtopic', False)

#         comment.mark_offtopic(user)
#         self._assert_class(comment, 'offtopic', True)

#     def test_image_tile_visibility_disabled(self):
#         comment = create_comment()
#         self._assert_class(comment, 'disabled', False)

#         comment.moderate_and_save(Visibility.DISABLED, create_staff())
#         self._assert_class(comment, 'disabled', True)

#     def test_image_tile_visibility_deleted(self):
#         comment = create_comment()
#         self._assert_class(comment, 'disabled', False)
#         self._assert_class(comment, 'removed', False)

#         comment.moderate_and_save(Visibility.UNPUBLISHED, create_staff())
#         self._assert_class(comment, 'disabled', True)
#         self._assert_class(comment, 'removed', True)



class TestTemplateCommentHelper(CanvasTestCase):
    def after_setUp(self):
        self.user = create_staff()

    def _ctx(self, user, cmt):
        author = cmt.author
        request = FakeRequest(user)
        return {
            'current_user_info': user.userinfo,
            'admin_infos': {
                cmt.id: {
                    'username': author.username,
                },
            },
            'request': request,
        }

    def test_anonymous_user_url_when_staff(self):
        user = self.user
        author = create_user()
        cmt = create_comment(author=author, anonymous=True)
        ctx = self._ctx(user, cmt)
        cmt = TemplateComment(cmt.details(), request_context=ctx)
        url = cmt.get_user_url()
        self.assertEqual(url, reverse('user_link', args=[author.username]))

    def test_timestamp_url(self):
        user = self.user
        cmt = create_comment()
        ctx = self._ctx(user, cmt)
        cmt = TemplateComment(cmt.details(), request_context=ctx)
        self.assertTrue(cmt.timestamp_link_url())

    def test_title_in_metadata(self):
        user = self.user
        title = "here's a title for this comment"
        cmt = create_comment(title=title)
        ctx = self._ctx(user, cmt)
        cmt = TemplateComment(cmt.details(), request_context=ctx)
        self.assertTrue(strip_template_chars(title) in cmt.shareable_metadata()['title'])


class TestTemplateCommentHelperFacebookMetadata(CanvasTestCase):
    def _metadata(self, **cmt_kwargs):
        group = create_group()
        cmt = TemplateComment(self.post_comment(category=group.name, **cmt_kwargs).details())
        return (cmt, cmt.shareable_metadata(),)

    def test_image_post_without_any_text(self):
        content = create_content()
        cmt, data = self._metadata(reply_content=content.id)
        self.assertEqual(data, {
            'title': data['title'],
            'description': knobs.TAGLINE,
            'image': data['image'],
        })

    def test_image_post_with_remix_text(self):
        content = create_content(remix_text='bananars')
        cmt, data = self._metadata(reply_content=content.id)
        self.assertEqual(data, {
            'title': data['title'],
            'description': 'bananars',
            'image': data['image'],
        })

    def test_image_post_with_reply_text(self):
        content = create_content()
        cmt, data = self._metadata(reply_text='huh', reply_content=content.id)
        self.assertEqual(data, {
            'title': data['title'],
            'description': 'huh',
            'image': data['image'],
        })


class TestUgcTextTags(TemplateTagTestCase):
    def test_ugc_text(self):
        text = '''
            this is some text.
            this is a #groupname here too.
            and here is a http://link.com/to/something.
            and a #1 sticker for u~
            <div name="this html">will be gone</div>.
            '''
        ugc_text = jinja_tags.ugc_text(text, 9001)
        self._has(ugc_text, ['this is some text',
                             ' #1 ',
                             'href="http://link.com/to/something"',
                             '_blank',
                             '/x/groupname',])

        self._has_not(ugc_text, ['this html',])

    def test_ugc_text_without_linkification(self):
        text = u'what #groupname http://huh.com'
        ugc_text = jinja_tags.ugc_text(text, 9001, 0, 0)

        self._has_not(ugc_text, ['href', '/x/groupname'])

    def test_group_link(self):
        text = '#i_didnt_hacked_canvas'
        ugc_text = jinja_tags.ugc_text(text, 9001, 1, 1)
        self.assertNotEqual(ugc_text, text)
        self.assertEqual(strip_tags(ugc_text), text)

    def test_url_exploit(self):
        text = '''www.schneier.com/essay-337.html?-#i_hacked_canvas'''
        ugc_text = jinja_tags.ugc_text(text, 9001, 1, 1)
        (link,) = self.css_select(ugc_text, 'a')
        self.assertEqual(strip_tags(ugc_text), text)
        self.assertEqual(link.attrib['href'], 'http://' + text)

    def test_group_link_with_space(self):
        text = 'foo #bar'
        ugc_text = jinja_tags.ugc_text(text, 9001, 1, 1)
        self.assertNotEqual(ugc_text, text)
        self.assertEqual(strip_tags(ugc_text), text)

    def test_ugc_link_with_typo(self):
        text = "thishttp://example.com/p/b8mwj"
        ugc_text = jinja_tags.ugc_text(text, 9001, 1, 1)
        (link,) = self.css_select(ugc_text, 'a')
        self.assertEqual("http://example.com/p/b8mwj", link.attrib['href'])

    def test_caret_escaping(self):
        text = '''
               for(var i = 1;i<iterations;i++){
               fg.save();
               }
               '''

        ugc_text = jinja_tags.ugc_text(text, 9001, 0, 0)
        self.assertEqual(strip_tags(ugc_text), text.replace('<', '&lt;'))

    def test_brace_escaping(self):
        text = '{% foo %}'
        for linkify in [0, 1]:
            ugc_text = jinja_tags.ugc_text(text, 9001, 0, linkify)
            self.assertFalse('{' in ugc_text)
            self.assertFalse('}' in ugc_text)
            self.assertTrue('foo' in ugc_text)
            self.assertTrue('&' in ugc_text)


class TestContentTags(CanvasTestCase):
    def test_fits(self):
        def wh(w, h):
            return {'height': h, 'width': w}

        # Mock content image metadata.
        c = wh(50, 100)

        self.assertEqual(_fit_inside( 50, 100, c), wh( 50, 100))
        self.assertEqual(_fit_inside(100, 200, c), wh( 50, 100)) # They won't become larger.
        self.assertEqual(_fit_inside( 50,  50, c), wh( 25,  50))
        self.assertEqual(_fit_inside( 25,  50, c), wh( 25,  50))

        self.assertEqual(_fit_height( 20, c), wh( 10 , 20))
        self.assertEqual(_fit_height(200, c), wh(100, 200))
        self.assertEqual(_fit_width(  10, c), wh( 10,  20))


class TestRelativeTimestamps(CanvasTestCase):
    def test_time_only(self):
        with override_service('time', FakeTimeProvider):
            for t, s in ((1, 'a moment'),
                         (59, 'a moment'),
                         (60, '1 minute'),
                         (60*5, '5 minutes'),
                         (60*60*24, '1 day'),
                         (60*60*23, '23 hours'),
                         (60*60*23.9, '23 hours'),
                         (60*60*23.999, '23 hours'),
                         (60*60*24*365*1.2, '1 year'),
                         (60*60*24*365*1.9, '1 year'),
                         (60*60*24*365*9001, '9001 years'),):
                then = Services.time.time() - t
                self.assertEqual(jinja_tags._relative_timestamp(then), s + ' ago')

    def test_with_html(self):
        with override_service('time', FakeTimeProvider):
            timestamp = Services.time.time() - 60*60*24*365*9001
            html = jinja_tags.relative_timestamp(timestamp)
            self.assertTrue('9001 years' in html)
            self.assertTrue('rel-timestamp' in html)
            self.assertTrue(str(timestamp) in html)


class TestRenderTemplateTagUtil(CanvasTestCase):
    def test_firstof(self):
        self.assertEqual(render_template_tag('firstof', ['foo']), 'foo')

    def test_non_cached(self):
        """
        It doesn't cache templates if only arg values are given, instead of arg key,value pairs.
        """
        _template_tag_cache.clear()
        for i in xrange(2):
            self.assertEqual(len(_template_tag_cache), 0)
            self.assertEqual(render_template_tag('firstof', ['foo']), 'foo')

    def test_cached(self):
        _template_tag_cache.clear()
        for i in xrange(2):
            self.assertEqual(len(_template_tag_cache), i)
            self.assertEqual(render_template_tag('firstof', [('arg_name', 'foo')]), 'foo')


class TestFilters(CanvasTestCase):
    def test_naturalday(self):
        self.assertEqual(jinja_tags.naturalday(datetime.date(2010, 8, 2)), 'August 2')

