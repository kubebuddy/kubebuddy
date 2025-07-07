from django.test import SimpleTestCase, override_settings
from django.template import Context, Template
from django.template.base import Variable
from django.templatetags import static as static_tags
import urllib.parse

class StaticTagExtraTests(SimpleTestCase):
    def test_get_static_prefix_with_custom_setting(self):
        with self.settings(STATIC_URL='/assets/'):
            tpl = Template('{% load static %}{% get_static_prefix %}')
            rendered = tpl.render(Context())
            self.assertEqual(rendered, '/assets/')

    def test_get_media_prefix_with_custom_setting(self):
        with self.settings(MEDIA_URL='/uploads/'):
            tpl = Template('{% load static %}{% get_media_prefix %}')
            rendered = tpl.render(Context())
            self.assertEqual(rendered, '/uploads/')

    def test_static_tag_with_empty_string(self):
        tpl = Template('{% load static %}{% static "" %}')
        rendered = tpl.render(Context())
        self.assertEqual(rendered, '/static/')

    def test_static_tag_with_special_characters(self):
        tpl = Template('{% load static %}{% static "img/lo go@.png" %}')
        rendered = tpl.render(Context())
        self.assertEqual(rendered, '/static/img/lo%20go%40.png')


    def test_static_tag_with_leading_slash(self):
        tpl = Template('{% load static %}{% static "/img/logo.png" %}')
        rendered = tpl.render(Context())
        self.assertEqual(rendered, '/static/img/logo.png')

    def test_static_function_with_leading_slash(self):
        url = static_tags.static('/img/logo.png')
        self.assertEqual(url, '/static/img/logo.png')

    def test_static_tag_with_context_variable_and_leading_slash(self):
        tpl = Template('{% load static %}{% static path %}')
        rendered = tpl.render(Context({'path': '/img/logo.png'}))
        self.assertEqual(rendered, '/static/img/logo.png')

    def test_static_tag_with_unicode_path(self):
        path = 'img/логотип.png'
        tpl = Template(f'{{% load static %}}{{% static "{path}" %}}')
        rendered = tpl.render(Context())
        expected = '/static/' + urllib.parse.quote(path)
        self.assertEqual(rendered, expected)

    def test_static_tag_with_none_variable(self):
        tpl = Template('{% load static %}{% static path %}')
        rendered = tpl.render(Context({'path': None}))
        self.assertEqual(rendered, '/static/')

    def test_static_tag_with_integer_variable(self):
        tpl = Template('{% load static %}{% static path %}')
        rendered = tpl.render(Context({'path': 123}))
        self.assertEqual(rendered, '/static/123')

    def test_static_tag_with_nested_variable(self):
        tpl = Template('{% load static %}{% static obj.path %}')
        rendered = tpl.render(Context({'obj': {'path': 'img/logo.png'}}))
        self.assertEqual(rendered, '/static/img/logo.png')

    def test_static_tag_with_as_var_and_variable(self):
        tpl = Template('{% load static %}{% static path as logo %}{{ logo }}')
        rendered = tpl.render(Context({'path': 'img/logo.png'}))
        self.assertEqual(rendered, '/static/img/logo.png')

    def test_staticnode_repr_with_path_variable(self):
        node = static_tags.StaticNode(varname=None, path=Variable('"img/logo.png"'))
        self.assertTrue("StaticNode" in repr(node))

    def test_prefixnode_repr_with_media_url(self):
        node = static_tags.PrefixNode(varname='foo', name='MEDIA_URL')
        self.assertEqual(repr(node), "<PrefixNode for 'MEDIA_URL'>")

    def test_bootstrap_tooltip_script_rendered(self):
        script = """
        <script>
        (function () {
          'use strict'
          var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
          tooltipTriggerList.forEach(function (tooltipTriggerEl) {
            new bootstrap.Tooltip(tooltipTriggerEl)
          })
        })()
        </script>
        """
        tpl = Template(script)
        rendered = tpl.render(Context())
        self.assertIn('bootstrap.Tooltip', rendered)
        self.assertIn('[data-bs-toggle="tooltip"]', rendered)
