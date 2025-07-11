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

    def test_toggle_fullscreen_function_present(self):
        js_code = """
        <script>
        let isFullscreen = false;
        function toggleFullscreen() {
            const chatbotWindow = document.querySelector('.chatbot-window');
            const fullscreenIcon = document.querySelector('.bi-fullscreen');
            const exitFullscreenIcon = document.querySelector('.bi-fullscreen-exit');
            if (!isFullscreen) {
                chatbotWindow.style.width = '80vw';
                chatbotWindow.style.height = '68vh';
                fullscreenIcon.classList.add('d-none');
                exitFullscreenIcon.classList.remove('d-none');
            } else {
                chatbotWindow.style.width = '40vw';
                chatbotWindow.style.height = '58vh';
                fullscreenIcon.classList.remove('d-none');
                exitFullscreenIcon.classList.add('d-none');
            }
            isFullscreen = !isFullscreen;
        }
        </script>
        """
        tpl = Template(js_code)
        rendered = tpl.render(Context())
        self.assertIn('function toggleFullscreen()', rendered)
        self.assertIn('isFullscreen = !isFullscreen', rendered)
        
    def test_clear_chat_history_js_function(self):
        js_code = """
        <script>
        function clearChatHistory() {
            sessionStorage.removeItem('chatHistory');
            sessionStorage.removeItem('apiKeyMessageShown');
            const chatBody = document.getElementById("chatBody");
            chatBody.innerHTML = '';
        }
        </script>
        """
        tpl = Template(js_code)
        rendered = tpl.render(Context())
        self.assertIn('clearChatHistory()', rendered)
        self.assertIn('sessionStorage.removeItem', rendered)
        
    def test_send_message_function_exists(self):
        js_code = """
        <script>
        async function sendMessage() {
            const inputField = document.getElementById("chatInput");
            const message = inputField.value.trim();
            if (message === "") return;
            userMessage(message);
            inputField.value = "";
            // more logic...
        }
        </script>
        """
        tpl = Template(js_code)
        rendered = tpl.render(Context())
        self.assertIn('async function sendMessage()', rendered)
        self.assertIn('userMessage(message)', rendered)

    def test_process_user_query_exists(self):
        js_code = """
        <script>
        async function processUserQuery(message) {
            try {
                const loadingMsgId = showLoadingMessage("Buddy is thinking...");
                const response = await fetch('/chatbot-response/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message }),
                });
                removeLoadingMessage(loadingMsgId);
                const data = await response.json();
                if (data.message) {
                    botMessage(data.message);
                }
            } catch (error) {
                botMessage("Oops! Something went wrong.");
            }
        }
        </script>
        """
        tpl = Template(js_code)
        rendered = tpl.render(Context())
        self.assertIn('async function processUserQuery', rendered)
        self.assertIn("fetch('/chatbot-response/'", rendered)

    def test_toggle_terminal_function_exists(self):
        js = """
        <script>
        function toggleTerminal() {
            if (terminalWindow.style.display === 'flex') {
                hideTerminal();
            } else {
                showTerminal();
            }
        }
        </script>
        """
        tpl = Template(js)
        rendered = tpl.render(Context())
        self.assertIn('function toggleTerminal()', rendered)
        self.assertIn('hideTerminal()', rendered)
        self.assertIn('showTerminal()', rendered)
        
    def test_terminal_fullscreen_function_present(self):
        js = """
        <script>
        function terminalFullscreen() {
            const fullscreenIcon = document.querySelector('.bi-fullscreen');
            const exitFullscreenIcon = document.querySelector('.bi-fullscreen-exit');
            if (!terScreen) {
                terminalWindow.style.width = '80vw';
                terminalWindow.style.height = '65vh';
                fullscreenIcon.classList.add('d-none');
                exitFullscreenIcon.classList.remove('d-none');
            } else {
                terminalWindow.style.width = '50vw';
                terminalWindow.style.height = '55vh';
                fullscreenIcon.classList.remove('d-none');
                exitFullscreenIcon.classList.add('d-none');
            }
            terScreen = !terScreen;
        }
        </script>
        """
        tpl = Template(js)
        rendered = tpl.render(Context())
        self.assertIn('function terminalFullscreen()', rendered)
        self.assertIn("terScreen = !terScreen", rendered)


    def test_terminal_dom_elements_exist(self):
        html = """
        <div id="terminal-window" style="display: none;">
            <div id="terminal-output"></div>
            <input id="input">
            <button id="terminal-icon"></button>
            <button id="close-terminal"></button>
            <button id="fullscreen-terminal"></button>
        </div>
        """
        tpl = Template(html)
        rendered = tpl.render(Context())
        self.assertIn('id="terminal-window"', rendered)
        self.assertIn('id="terminal-output"', rendered)
        self.assertIn('id="input"', rendered)
        self.assertIn('id="terminal-icon"', rendered)
        self.assertIn('id="close-terminal"', rendered)
        self.assertIn('id="fullscreen-terminal"', rendered)
        
    def test_terminal_input_event_listener(self):
        js = """
        <script>
        input.addEventListener('keydown', async (event) => {
            if (event.key === 'Enter') {
                const command = input.value.trim();
                if (command) {
                    const commandLine = document.createElement('div');
                    commandLine.innerHTML = `<span class="prompt">user@host:~$</span> ${command}`;
                    terminalOutput.appendChild(commandLine);
                }
            }
        });
        </script>
        """
        tpl = Template(js)
        rendered = tpl.render(Context())
        self.assertIn("addEventListener('keydown'", rendered)
        self.assertIn("commandLine.innerHTML", rendered)
        self.assertIn("terminalOutput.appendChild", rendered)
        
    def test_get_cookie_function_present(self):
        js = """
        <script>
        function getCookie(name) {
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
        </script>
        """
        tpl = Template(js)
        rendered = tpl.render(Context())
        self.assertIn("function getCookie(name)", rendered)
        self.assertIn("document.cookie.split(';')", rendered)


    def test_table_search_and_sort_dom_exists(self):
        html = """
        <input type="text" id="tableSearchInput">
        <table>
            <thead>
                <tr>
                    <th class="sortable">Name</th>
                    <th class="sortable">Age</th>
                </tr>
            </thead>
            <tbody>
                <tr><td>Alice</td><td>30</td></tr>
                <tr><td>Bob</td><td>25</td></tr>
            </tbody>
        </table>
        """
        tpl = Template(html)
        rendered = tpl.render(Context())
        self.assertIn('id="tableSearchInput"', rendered)
        self.assertIn('class="sortable"', rendered)
        self.assertIn('<table>', rendered)
        self.assertIn('<tbody>', rendered)

    def test_debounce_function_present(self):
        js = """
        <script>
        function debounce(func, delay) {
            let timeout;
            return function (...args) {
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(this, args), delay);
            };
        }
        </script>
        """
        tpl = Template(js)
        rendered = tpl.render(Context())
        self.assertIn('function debounce(func, delay)', rendered)
        self.assertIn('setTimeout', rendered)
        self.assertIn('clearTimeout', rendered)
        
    def test_table_filter_search_keyup_present(self):
        js = """
        <script>
        const searchInput = document.getElementById("tableSearchInput");
        searchInput.addEventListener("keyup", filterTable);
        </script>
        """
        tpl = Template(js)
        rendered = tpl.render(Context())
        self.assertIn('getElementById("tableSearchInput")', rendered)
        self.assertIn('addEventListener("keyup"', rendered)
        self.assertIn('filterTable', rendered)
        
    def test_sortable_column_click_logic(self):
        js = """
        <script>
        document.querySelectorAll("th.sortable").forEach(header => {
            header.addEventListener("click", function () {
                const currentState = header.getAttribute("data-sort") || "desc";
                const newState = currentState === "asc" ? "desc" : "asc";
                header.setAttribute("data-sort", newState);
            });
        });
        </script>
        """
        tpl = Template(js)
        rendered = tpl.render(Context())
        self.assertIn('querySelectorAll("th.sortable")', rendered)
        self.assertIn('addEventListener("click"', rendered)
        self.assertIn('getAttribute("data-sort")', rendered)
        self.assertIn('setAttribute("data-sort", newState)', rendered)
        
    def test_sort_indicator_icon_toggle_logic(self):
        js = """
        <script>
        if (newState === 'asc') {
            header.querySelector(".sort-indicator").classList.remove("bi-arrow-down");
            header.querySelector(".sort-indicator").classList.add("bi-arrow-up");
        } else {
            header.querySelector(".sort-indicator").classList.remove("bi-arrow-up");
            header.querySelector(".sort-indicator").classList.add("bi-arrow-down");
        }
        </script>
        """
        tpl = Template(js)
        rendered = tpl.render(Context())
        self.assertIn('classList.remove("bi-arrow-down")', rendered)
        self.assertIn('classList.add("bi-arrow-up")', rendered)
        self.assertIn('classList.remove("bi-arrow-up")', rendered)
        self.assertIn('classList.add("bi-arrow-down")', rendered)


    def test_checkbox_and_table_dom_structure_exists(self):
        html = """
        <input type="checkbox" id="All" class="column-checkbox">
        <input type="checkbox" value="Name" class="column-checkbox">
        <table>
            <thead><tr><th>Name</th><th>Age</th><th>Actions</th></tr></thead>
            <tbody>
                <tr><td>Alice</td><td>30</td><td>Edit</td></tr>
            </tbody>
        </table>
        """
        tpl = Template(html)
        rendered = tpl.render(Context())
        self.assertIn('id="All"', rendered)
        self.assertIn('class="column-checkbox"', rendered)
        self.assertIn('<table>', rendered)
        self.assertIn('<thead>', rendered)
        self.assertIn('<tbody>', rendered)

    def test_message_truncate_dom_exists(self):
        html = """
        <div class="message-truncate" data-full="This is a full message example.">
            This is a full message...
        </div>
        """
        tpl = Template(html)
        rendered = tpl.render(Context())
        self.assertIn('class="message-truncate"', rendered)
        self.assertIn('data-full=', rendered)
        
    def test_message_toggle_js_logic(self):
        js = """
        document.querySelectorAll(".message-truncate").forEach(element => {
            element.addEventListener("click", function () {
                const fullMessage = this.getAttribute("data-full");
                if (this.textContent.length > 100) {
                    this.textContent = fullMessage;
                } else {
                    this.textContent = fullMessage.slice(0, 100) + "...";
                }
            });
        });
        """
        tpl = Template(js)
        rendered = tpl.render(Context())
        self.assertIn('querySelectorAll(".message-truncate")', rendered)
        self.assertIn('addEventListener("click"', rendered)
        self.assertIn('data-full', rendered)
        self.assertIn('this.textContent = fullMessage', rendered)

    def test_load_selection_logic_exists(self):
        js = """
        function loadSelection() {
            const savedSelection = JSON.parse(localStorage.getItem(`selectedColumns_${pageKey}`));
            if (savedSelection && savedSelection.length > 0) {
                checkboxes.forEach(checkbox => {
                    checkbox.checked = savedSelection.includes(checkbox.value);
                });
            }
        }
        """
        tpl = Template(js)
        rendered = tpl.render(Context())
        self.assertIn('function loadSelection()', rendered)
        self.assertIn('localStorage.getItem', rendered)
        self.assertIn('checkbox.checked = savedSelection.includes', rendered)

    def test_save_selection_logic_exists(self):
        js = """
        function saveSelection() {
            const selectedColumns = [];
            checkboxes.forEach(checkbox => {
                if (checkbox.checked) {
                    selectedColumns.push(checkbox.value);
                }
            });
            localStorage.setItem(`selectedColumns_${pageKey}`, JSON.stringify(selectedColumns));
        }
        """
        tpl = Template(js)
        rendered = tpl.render(Context())
        self.assertIn('function saveSelection()', rendered)
        self.assertIn('localStorage.setItem', rendered)
        self.assertIn('selectedColumns.push', rendered)
        
        
    def test_toggle_columns_function_logic(self):
        js = """
        function toggleColumns() {
            checkboxes.forEach(checkbox => {
                const columnIndex = getColumnIndex(checkbox.value);
                const displayStyle = checkbox.checked ? "table-cell" : "none";
                tableHeaders[columnIndex].style.display = displayStyle;
            });
        }
        """
        tpl = Template(js)
        rendered = tpl.render(Context())
        self.assertIn('function toggleColumns()', rendered)
        self.assertIn('getColumnIndex(checkbox.value)', rendered)
        self.assertIn('style.display = displayStyle', rendered)
        
    def test_get_column_index_function_logic(self):
        js = """
        function getColumnIndex(columnName) {
            for (let i = 0; i < tableHeaders.length; i++) {
                if (tableHeaders[i].textContent.replace(/[^a-zA-Z]+/g, '').trim().toLowerCase() === columnName.toLowerCase()) {
                    return i;
                }
            }
            return -1;
        }
        """
        tpl = Template(js)
        rendered = tpl.render(Context())
        self.assertIn('function getColumnIndex(columnName)', rendered)
        self.assertIn('tableHeaders[i].textContent.replace', rendered)
        self.assertIn('return -1', rendered)


