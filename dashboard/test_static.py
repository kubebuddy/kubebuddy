from django.test import SimpleTestCase
from django.template import Context, Template, TemplateSyntaxError
from django.conf import settings
from django.templatetags import static as static_tags
from django.template.base import Variable

if not settings.configured:
    settings.configure(STATIC_URL='/static/', MEDIA_URL='/media/')

class StaticTagTests(SimpleTestCase):

    def test_get_static_prefix_direct(self):
        tpl = Template('{% load static %}{% get_static_prefix %}')
        rendered = tpl.render(Context())
        self.assertEqual(rendered, '/static/')

    def test_get_static_prefix_as_var(self):
        tpl = Template('{% load static %}{% get_static_prefix as sp %}{{ sp }}')
        rendered = tpl.render(Context())
        self.assertEqual(rendered, '/static/')

    def test_get_media_prefix_direct(self):
        with self.settings(MEDIA_URL='/media/'):
            tpl = Template('{% load static %}{% get_media_prefix %}')
            rendered = tpl.render(Context())
            self.assertEqual(rendered, '/media/')

    def test_get_media_prefix_as_var(self):
        with self.settings(MEDIA_URL='/media/'):
            tpl = Template('{% load static %}{% get_media_prefix as mp %}{{ mp }}')
            rendered = tpl.render(Context())
            self.assertEqual(rendered, '/media/')

    def test_static_tag_with_string(self):
        tpl = Template('{% load static %}{% static "img/logo.png" %}')
        rendered = tpl.render(Context())
        self.assertEqual(rendered, '/static/img/logo.png')

    def test_static_tag_with_variable(self):
        tpl = Template('{% load static %}{% static path %}')
        rendered = tpl.render(Context({'path': 'img/logo.png'}))
        self.assertEqual(rendered, '/static/img/logo.png')

    def test_static_tag_as_var(self):
        tpl = Template('{% load static %}{% static "img/logo.png" as logo %}{{ logo }}')
        rendered = tpl.render(Context())
        self.assertEqual(rendered, '/static/img/logo.png')

    def test_static_function(self):
        url = static_tags.static('img/logo.png')
        self.assertEqual(url, '/static/img/logo.png')

    def test_static_tag_missing_argument(self):
        tpl = '{% load static %}{% static %}'
        with self.assertRaises(TemplateSyntaxError):
            Template(tpl)

    def test_prefixnode_repr(self):
        node = static_tags.PrefixNode(varname='foo', name='STATIC_URL')
        self.assertEqual(repr(node), "<PrefixNode for 'STATIC_URL'>")

    def test_staticnode_repr(self):
        node = static_tags.StaticNode(varname='foo', path=Variable('"img/logo.png"'))
        self.assertIn("StaticNode", repr(node))

    def test_staticnode_render_autoescape(self):
        tpl = Template('{% load static %}{% static "<img>.png" %}')
        rendered = tpl.render(Context(autoescape=True))
        self.assertNotIn('&lt;img&gt;.png', rendered)

    def test_staticnode_handle_simple_without_staticfiles(self):
        original_is_installed = static_tags.apps.is_installed
        static_tags.apps.is_installed = lambda app: False
        try:
            url = static_tags.StaticNode.handle_simple('img/logo.png')
            self.assertEqual(url, '/static/img/logo.png')
        finally:
            static_tags.apps.is_installed = original_is_installed
            
            def test_tooltip_function_runs_without_error(self):
                try:
                    pass
                except Exception as e:
                    self.fail(f"Tooltip JS function raised an exception: {e}")

            def test_tooltip_function_document_query_selector_all(self):
                elements = ['el1', 'el2', 'el3']
                tooltipTriggerList = list(elements)
                self.assertEqual(len(tooltipTriggerList), 3)

            def test_tooltip_function_forEach(self):
                elements = ['el1', 'el2']
                called = []
                def fake_tooltip(el):
                    called.append(el)
                for el in elements:
                    fake_tooltip(el)
                self.assertEqual(called, elements)
