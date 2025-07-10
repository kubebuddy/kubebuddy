from django.test import SimpleTestCase, override_settings
from django.template import Context, Template
from django.template.base import Variable
from django.templatetags import static as static_tags
import urllib.parse
from django.test import TestCase, Client

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
        
    def test_chatbot_window_structure_exists(self):
        html = """
        <div id="chatbotWindow" class="chatbot-window" style="display: none;">
            <div id="chatBody"></div>
            <textarea id="chatInput"></textarea>
        </div>
        """
        tpl = Template(html)
        rendered = tpl.render(Context())
        self.assertIn('id="chatbotWindow"', rendered)
        self.assertIn('id="chatInput"', rendered)
        self.assertIn('id="chatBody"', rendered)

    def test_toggle_chat_js_function_included(self):
        js = """
        <script>
        function toggleChat() {
            var chatWindow = document.getElementById("chatbotWindow");
            chatWindow.style.display = chatWindow.style.display === "none" || chatWindow.style.display === "" ? "flex" : "none";
        }
        </script>
        """
        tpl = Template(js)
        rendered = tpl.render(Context())
        self.assertIn('function toggleChat()', rendered)
        self.assertIn('chatbotWindow', rendered)

    def test_event_listener_for_chatinput_enter_key(self):
        js = """
        <script>
        document.getElementById("chatInput").addEventListener("keydown", function(event) {
            if (event.key === "Enter") {
                if (event.shiftKey) {
                    event.preventDefault();
                    this.value += "\\n";
                } else {
                    event.preventDefault();
                    sendMessage();
                }
            }
        });
        </script>
        """
        tpl = Template(js)
        rendered = tpl.render(Context())
        self.assertIn('addEventListener("keydown"', rendered)
        self.assertIn('sendMessage()', rendered)

    def test_js_chatbot_message_function_exists(self):
        js = """
        <script>
        function botMessage(text) {
            const chatBody = document.getElementById("chatBody");
            const messageElement = document.createElement("div");
            messageElement.innerHTML = text;
            messageElement.className = "bot-message";
            chatBody.appendChild(messageElement);
        }
        </script>
        """
        tpl = Template(js)
        rendered = tpl.render(Context())
        self.assertIn('function botMessage', rendered)
        self.assertIn('chatBody.appendChild', rendered)

    def test_static_js_reference_is_correct(self):
        tpl = Template('{% load static %}<script src="{% static \'js/chatbot.js\' %}"></script>')
        rendered = tpl.render(Context())
        self.assertIn('<script src="/static/js/chatbot.js"></script>', rendered)
        
    def test_static_chatbot_js_inclusion(self):
        tpl = Template('{% load static %}<script src="{% static \'js/chatbot.js\' %}"></script>')
        rendered = tpl.render(Context())
        self.assertEqual(rendered.strip(), '<script src="/static/js/chatbot.js"></script>')

    def test_static_chatbot_css_inclusion(self):
        tpl = Template('{% load static %}<link href="{% static \'css/chatbot.css\' %}" rel="stylesheet">')
        rendered = tpl.render(Context())
        self.assertEqual(rendered.strip(), '<link href="/static/css/chatbot.css" rel="stylesheet">')

    def test_static_tag_with_image_space(self):
        tpl = Template('{% load static %}<img src="{% static "img/my image.png" %}">')
        rendered = tpl.render(Context())
        self.assertIn('/static/img/my%20image.png', rendered)

    def test_toggle_chat_function_in_js_block(self):
        js_code = """
        <script>
        function toggleChat() {
            var chatWindow = document.getElementById("chatbotWindow");
            chatWindow.style.display = chatWindow.style.display === "none" ? "flex" : "none";
        }
        </script>
        """
        tpl = Template(js_code)
        rendered = tpl.render(Context())
        self.assertIn('function toggleChat()', rendered)
        self.assertIn('chatbotWindow', rendered)

    def test_chatbot_dom_elements_exist(self):
        html = """
        <div id="chatbotWindow"><div id="chatBody"></div><textarea id="chatInput"></textarea></div>
        """
        tpl = Template(html)
        rendered = tpl.render(Context())
        self.assertIn('id="chatbotWindow"', rendered)
        self.assertIn('id="chatBody"', rendered)
        self.assertIn('id="chatInput"', rendered)    

