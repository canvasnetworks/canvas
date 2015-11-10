import re

from jinja2 import nodes, contextfunction
from jinja2.ext import Extension


_extends_re = re.compile(r'{% *djextends .*%}')
_extends_end_re = re.compile(r'{% *enddjextends .*%}')

_block_re = re.compile(r'{% *block (.*)%}')
_block_end_re = re.compile(r'{% *endblock *%}')

_super_re = re.compile(r'{{ *super\(\) *}}')

EXTENDS_DJANGO = '__extends_django__'


class ExtendsDjangoExtension(Extension):
    tags = set(['djextends', 'djblock'])

    def preprocess(self, source, name, filename=None):
        """ Adds {% enddjextends %} and converts {% block %} to {% djblock %}, if this tag matches. """
        if not _extends_re.search(source):
            return source

        if not _extends_end_re.search(source):
            source += '\n{% enddjextends %}'

        source = _block_re.sub(r'{% djblock \1 %}', source)
        source = _block_end_re.sub(r'{% enddjblock %}', source)

        source = _super_re.sub("{{ '{{' }} block.super {{ '}}' }}", source)

        return source

    def parse(self, parser):
        tag = parser.stream.next()
        lineno = tag.lineno
        return getattr(self, '_parse_' + str(tag))(parser, lineno)

    def _parse_djextends(self, parser, lineno):
        args = [parser.parse_expression()]

        body = parser.parse_statements(['name:enddjextends'], drop_needle=True)

        return [nodes.Assign(
                    nodes.Name(EXTENDS_DJANGO, 'store'),
                    nodes.Const(True),
                ).set_lineno(lineno),
                nodes.CallBlock(self.call_method('_extend_django', args), [], [], body).set_lineno(lineno)]

    @contextfunction
    def _extend_django(self, ctx, django_template, caller):
        from django.template import Context, RequestContext, Template
        from django.http import HttpRequest

        request = ctx.get('request')
        if isinstance(request, HttpRequest):
            django_ctx = RequestContext(request, dict(ctx))
        else:
            django_ctx = Context(ctx.iteritems())

        template = '{{% extends "{0}" %}}\n'.format(django_template) + unicode(caller())
        template = Template(template)
        return template.render(django_ctx)

    def _parse_djblock(self, parser, lineno):
        node = nodes.Block(lineno=lineno)
        node.name = parser.stream.expect('name').value
        node.scoped = parser.stream.skip_if('name:scoped')

        # common problem people encounter when switching from django
        # to jinja.  we do not support hyphens in block names, so let's
        # raise a nicer error message in that case.
        if parser.stream.current.type == 'sub':
            parser.fail('Block names in Jinja have to be valid Python '
                      'identifiers and may not contain hyphens, use an '
                      'underscore instead.')

        node.body = parser.parse_statements(('name:enddjblock',), drop_needle=True)
        parser.stream.skip_if('name:' + node.name)

        block_name = node.name

        def output(text):
            return nodes.CallBlock(self.call_method('_block', args=[
                nodes.Name(EXTENDS_DJANGO, 'load'),
                nodes.Const(text),
            ]), [], [], []).set_lineno(lineno)

        prefix = output('{{% block {0} %}}'.format(block_name))
        postfix = output('{% endblock %}')

        return [prefix, node, postfix]

    def _block(self, extends_django, tag, caller):
        if extends_django:
            return tag
        return ''

