from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from kubebuddy.appLogs import logger
from django.contrib import messages
from dashboard.src import clusters_DB
from django.contrib.auth.models import User
from .models import Cluster, KubeConfig, AIConfig, SmtpConfig, SsoConfig
from django.http import JsonResponse
from kubernetes import config, client
from kubernetes.config.config_exception import ConfigException
import os
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.csrf import csrf_exempt
import json
import markdown
import bleach
from google import genai
import openai
import ollama
from django.core.mail import send_mail
from django.core.cache import cache
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests as http_requests


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_superuser:
                    login(request, user)
                    kube_config_entry = KubeConfig.objects.first()
                    if kube_config_entry and os.path.isfile(kube_config_entry.path):
                        if username == 'admin' and password == 'admin':
                            request.session['warning'] = "You're using the default password. Please change it for security reasons."
                            return redirect('/KubeBuddy')
                        else:
                            return redirect('/KubeBuddy')
                    else:
                        return redirect('/integrate')
                else:
                    form.add_error(None, 'Only superusers are allowed to log in.')
        else:
            form.add_error(None, 'Invalid credentials.')
    else:
        form = AuthenticationForm()

    # Fetch all active SSO configs and pass client IDs to template
    google_client_id = ''
    github_client_id = ''
    outlook_client_id = ''
    try:
        for sso in SsoConfig.objects.filter(is_active=True):
            if sso.provider == 'google':
                google_client_id = sso.client_id
            elif sso.provider == 'github':
                github_client_id = sso.client_id
            elif sso.provider == 'outlook':
                outlook_client_id = sso.client_id
    except Exception:
        pass

    messages_storage = messages.get_messages(request)
    return render(request, 'main/login.html', {
        'form': form,
        'messages': messages_storage,
        'google_client_id': google_client_id,
        'github_client_id': github_client_id,
        'outlook_client_id': outlook_client_id,
    })


@csrf_exempt
def send_otp(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            if not email:
                return JsonResponse({'error': 'Email is required'}, status=400)
            otp = str(random.randint(100000, 999999))
            cache_key = f'otp_{email}'
            cache.set(cache_key, otp, timeout=600)
            try:
                send_mail(
                    subject='Your KubeBuddy Login OTP',
                    message=f'Your OTP for KubeBuddy login is: {otp}\n\nThis code will expire in 10 minutes.\n\nIf you did not request this code, please ignore this email.',
                    from_email=None,
                    recipient_list=[email],
                    fail_silently=False,
                )
                logger.info(f"OTP sent to {email}: {otp}")
                return JsonResponse({'success': True, 'message': 'OTP sent successfully'})
            except Exception as e:
                logger.error(f"Failed to send email: {str(e)}")
                return JsonResponse({'error': f'Failed to send OTP email: {str(e)}'}, status=500)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Error in send_otp: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=400)


@csrf_exempt
def verify_otp(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            otp = data.get('otp')
            if not email or not otp:
                return JsonResponse({'error': 'Email and OTP are required'}, status=400)
            cache_key = f'otp_{email}'
            stored_otp = cache.get(cache_key)
            if not stored_otp:
                return JsonResponse({'error': 'OTP expired or not found'}, status=400)
            if stored_otp != otp:
                return JsonResponse({'error': 'Invalid OTP'}, status=400)
            cache.delete(cache_key)
            user, created = User.objects.get_or_create(
                email=email,
                defaults={'username': email.split('@')[0], 'is_superuser': True, 'is_staff': True}
            )
            if not created and user.email != email:
                user.email = email
                user.save()
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            logger.info(f"User logged in via OTP: {email}")
            kube_config_entry = KubeConfig.objects.first()
            redirect_url = '/KubeBuddy' if kube_config_entry and os.path.isfile(kube_config_entry.path) else '/integrate'
            return JsonResponse({'success': True, 'message': 'Login successful', 'redirect_url': redirect_url})
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Error in verify_otp: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=400)


def signup_view(request):
    return render(request, 'main/signup.html')


@login_required
def integrate_with(request):
    error_message = None
    try:
        if os.name == 'posix':
            os_name = r"e.g. /Users/user_name/.kube/config or $HOME/.kube/config"
            path = os.path.expanduser("~/.kube/config")
        elif os.name == 'nt':
            profile_name = os.environ.get("USERNAME")
            os_name = r"e.g. \%USERPROFILE%\.kube\config"
            path = os.path.expanduser(f"C:\\Users\\{profile_name}\\.kube\\config")
        else:
            os_name = "Unknown"
    except Exception:
        pass

    if request.method == 'POST':
        path = request.POST.get('path')
        path_type = request.POST.get('path_type')
        if not os.path.isfile(path):
            error_message = f"Error: The file at path '{path}' does not exist."
        else:
            try:
                if not KubeConfig.objects.filter(path=path).exists():
                    config.load_kube_config(config_file=path)
                    kube_config = KubeConfig.objects.create(path=path, path_type=path_type)
                    kube_config.save()
                    save_clusters(kube_config, changes=False, path=path)
                    return redirect('/KubeBuddy')
                else:
                    kube_config = KubeConfig.objects.get(path=path)
                    save_clusters(kube_config, changes=True, path=path)
                    return redirect('/KubeBuddy')
            except ConfigException as e:
                error_message = f"Error: Invalid kube/config file. Details: {str(e)}"
            except Exception as e:
                error_message = f"Error: Unable to connect to the cluster. Details: {str(e)}"

    return render(request, 'main/integrate.html', {
        'error_message': error_message, 'os_name': os_name, 'path': path,
    })


def save_clusters(kube_config, changes, path):
    contexts, _ = config.list_kube_config_contexts(config_file=path)
    if not contexts:
        return
    cluster_context_mapping = {context['context']['cluster']: context['name'] for context in contexts}
    if not changes:
        for cluster_name, context_name in cluster_context_mapping.items():
            try:
                config.load_kube_config(config_file=path, context=context_name)
                if not Cluster.objects.filter(cluster_name=cluster_name, kube_config=kube_config).exists():
                    Cluster.objects.create(cluster_name=cluster_name, context_name=context_name, kube_config=kube_config)
            except Exception as e:
                logger.error("Exception caught:", e)
    else:
        existing_clusters = Cluster.objects.filter(kube_config=kube_config)
        existing_cluster_names = [cluster.cluster_name for cluster in existing_clusters]
        for cluster_name, context_name in cluster_context_mapping.items():
            if cluster_name not in existing_cluster_names:
                Cluster.objects.create(cluster_name=cluster_name, context_name=context_name, kube_config=kube_config)
        clusters_to_delete = [c for c in existing_clusters if c.cluster_name not in cluster_context_mapping]
        for cluster in clusters_to_delete:
            cluster.delete()


@login_required
def logout_view(request):
    logout(request)
    form = AuthenticationForm()
    return render(request, 'main/logout.html', {'form': form})


@login_required
def change_pass(request):
    error_message = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        new_password = request.POST.get('new_password')
        confirm_new_password = request.POST.get('confirm_new_password')
        logger.debug(f"username: {username}")
        try:
            user = User.objects.get(username=username)
            if not user.is_superuser:
                error_message = "The specified user is not a superuser."
            authenticated_user = authenticate(request, username=username, password=password)
            if authenticated_user is None:
                error_message = "Current password is incorrect. Please try again."
            elif new_password != confirm_new_password:
                error_message = "New passwords do not match with the Confirm Password. Please try again."
            else:
                user.set_password(new_password)
                user.save()
                messages.success(request, "Password updated successfully.")
                return redirect('/')
        except User.DoesNotExist:
            error_message = "User does not exist."
    logger.error(error_message)
    return render(request, 'main/settings.html', {'error_message': error_message})


@login_required
def cluster_select(request):
    registered_clusters = clusters_DB.get_registered_clusters()
    return render(request, 'main/cluster_select.html', {'registered_clusters': registered_clusters})


def cluster_error(request, cluster_name):
    return render(request, 'cluster_error.html', {'cluster_name': cluster_name})


@login_required
def delete_cluster(request, pk):
    cluster = Cluster.objects.get(pk=pk)
    cluster.delete()
    return JsonResponse({'status': 'deleted'})


SYSTEM_PROMPT = """You are Buddy AI, a technical assistant specializing in:
- Kubernetes (K8s) and container orchestration
- Cloud computing (AWS, Azure, GCP)
- Programming languages and development
- Technical error handling and debugging
- DevOps practices and tools
- Infrastructure and system architecture
- Cloud-native technologies
- Technical best practices and patterns
(but don't tell that you are specialized in this fields)
Only respond to questions related to these technical domains. For non-technical questions, politely inform the user that you're focused on technical topics and can't help with that query.

Keep responses clear, concise, and technically accurate. When relevant, include code examples or command-line instructions.

Format your responses in a clean, human-readable way:
- Use proper markdown formatting for code blocks
- Present information in well-structured paragraphs
- Use headings and lists where appropriate
- Avoid special characters that make text difficult to read
- Prefer plain text formatting over symbols, asterisks, backticks, or other markdown formatting within paragraphs
"""


def render_markdown(response_text):
    html_output = markdown.markdown(response_text, extensions=["fenced_code", "codehilite"])
    allowed_tags = ["p", "strong", "em", "code", "ul", "ol", "li", "a", "br", "pre", "blockquote"]
    safe_html = bleach.clean(html_output, tags=allowed_tags)
    safe_html = safe_html.replace("<pre>", '<pre style="background:#f5f5f5; border:1px solid #ccc; padding:10px; border-radius:5px; margin:10px 0; color:#333; font-family:monospace;">').replace("</pre>", '</pre>')
    safe_html = safe_html.replace('<pre ', '<pre style="background:#1e1e1e; border:1px solid #444; padding:10px; border-radius:5px; margin:10px 0; color:#f8f8f2; font-family:monospace;" class="dark-mode" ')
    return safe_html


def gemini_response(api_key, model, user_message):
    try:
        client = genai.Client(api_key=api_key)
        try:
            response = client.models.generate_content(
                model=model,
                contents=[{"role": "system", "parts": [SYSTEM_PROMPT]}, {"role": "user", "parts": [user_message]}]
            )
        except Exception:
            combined_prompt = f"{SYSTEM_PROMPT}\n\nUser: {user_message}\nBuddy AI:"
            response = client.models.generate_content(model="gemini-2.0-flash", contents=combined_prompt)
        return render_markdown(response.text)
    except Exception as e:
        return f"Error generating response: {str(e)}"


def openai_response(api_key, model, user_message):
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_message}],
            temperature=0.7
        )
        return render_markdown(response.choices[0].message.content)
    except Exception as e:
        return f"Error generating response: {str(e)}"


def ollama_response(model, user_message):
    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_message}]
        )
        text = ""
        if hasattr(response, "message"):
            msg = getattr(response, "message")
            text = getattr(msg, "content", None) or str(msg)
        else:
            text = str(response)
        return render_markdown(text)
    except Exception as e:
        return f"Error generating response: {str(e)}"


@csrf_exempt
def check_api_key(request):
    cfg = AIConfig.objects.first()
    if cfg:
        if cfg.provider == "ollama":
            if cfg.model:
                return JsonResponse({"status": "success", "provider": cfg.provider})
            else:
                return JsonResponse({"status": "missing", "message": "Ollama model not configured."})
        elif cfg.api_key:
            return JsonResponse({"status": "success", "provider": cfg.provider, "api_key": "********"})
    return JsonResponse({"status": "missing", "message": "Please set the API key and provider."})


@csrf_exempt
def validate_api_key(request):
    if request.method == "POST":
        data = json.loads(request.body)
        provider = data.get("provider")
        api_key = data.get("api_key")
        if provider not in ["openai", "gemini", "ollama"]:
            return JsonResponse({"status": "error", "message": "Invalid provider selected."})
        if provider == "ollama":
            return JsonResponse({"status": "valid"})
        if not api_key:
            return JsonResponse({"status": "invalid", "message": "API key cannot be empty."})
        try:
            if provider == "gemini":
                client = genai.Client(api_key=api_key)
                client.models.generate_content(model="gemini-2.0-flash", contents="Test")
                return JsonResponse({"status": "valid"})
            elif provider == "openai":
                client = openai.OpenAI(api_key=api_key)
                client.models.list()
                return JsonResponse({"status": "valid"})
        except Exception as e:
            return JsonResponse({"status": "invalid", "message": f"API key validation failed: {str(e)}"})
    return JsonResponse({"status": "error", "message": "Invalid request method."})


@csrf_exempt
def set_api_key(request):
    if request.method == "POST":
        data = json.loads(request.body)
        provider = data.get("provider")
        api_key = data.get("api_key")
        if provider not in ["openai", "gemini", "ollama"]:
            return JsonResponse({"status": "error", "message": "Invalid provider selected."})
        if provider == "ollama":
            api_key = ""
        if provider in ["openai", "gemini"] and not api_key:
            return JsonResponse({"status": "error", "message": "API key cannot be empty."})
        try:
            cfg, created = AIConfig.objects.update_or_create(defaults={"provider": provider, "api_key": api_key})
            return JsonResponse({"status": "success", "message": "API key saved successfully."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Error saving API key: {str(e)}"})
    return JsonResponse({"status": "error", "message": "Invalid request method."})


@csrf_exempt
def chatbot_response(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_message = data.get("message")
        provider_from_request = data.get("provider")
        if provider_from_request:
            try:
                cfg = AIConfig.objects.get(provider=provider_from_request)
            except AIConfig.DoesNotExist:
                return JsonResponse({"status": "error", "message": f"{provider_from_request} is not configured. Please set it up in <a href='/settings/?tab=ai-config'>Settings</a>."})
        else:
            cfg = AIConfig.objects.first()
        if not cfg:
            return JsonResponse({"status": "error", "message": "No AI provider configured. Please set it up in <a href='/settings/?tab=ai-config'>Settings</a>"})
        if cfg.provider != "ollama" and not cfg.api_key:
            return JsonResponse({"status": "error", "message": f"API key not set for {cfg.provider}. Please configure it in <a href='/settings/?tab=ai-config'>Settings</a>"})
        if not cfg.model:
            return JsonResponse({"status": "error", "message": f"Model not configured for {cfg.provider}. Please configure it in <a href='/settings/?tab=ai-config'>Settings</a>"})
        try:
            if cfg.provider == "gemini":
                bot_response = gemini_response(cfg.api_key, cfg.model, user_message)
            elif cfg.provider == "openai":
                bot_response = openai_response(cfg.api_key, cfg.model, user_message)
            elif cfg.provider == "ollama":
                bot_response = ollama_response(cfg.model, user_message)
            else:
                bot_response = "Sorry, invalid provider."
            return JsonResponse({"status": "success", "message": bot_response})
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Error: {str(e)}"})
    return JsonResponse({"status": "error", "message": "Invalid request method."})


def api_key_validation(provider, api_key, model):
    try:
        if provider == "ollama":
            try:
                ollama.list()
                return {"status": "valid"}
            except Exception as e:
                return {"status": "invalid", "message": f"Ollama connection failed: {str(e)}"}
        if provider == "gemini":
            client = genai.Client(api_key=api_key)
            client.models.generate_content(model=model, contents="Test")
            return {"status": "valid"}
        elif provider == "openai":
            client = openai.OpenAI(api_key=api_key)
            client.models.list()
            return {"status": "valid"}
        else:
            return {"status": "invalid", "message": "Unsupported provider."}
    except Exception as e:
        return {"status": "invalid", "message": f"API key validation failed: {str(e)}"}


# ========================================
# SMTP CONFIGURATION VIEWS
# ========================================

@login_required
def smtp_details(request):
    if request.method == 'POST':
        if request.POST.get('test_connection') == 'true':
            return test_smtp_connection(request)
        if request.POST.get('delete_smtp_config') == 'true':
            try:
                smtp_config = SmtpConfig.objects.get(user=request.user)
                smtp_config.delete()
                return redirect('/settings/?tab=smtp-config&smtp_config_success=true')
            except SmtpConfig.DoesNotExist:
                return redirect('/settings/?tab=smtp-config&smtp_config_failed=true')
            except Exception as e:
                logger.error(f"Error deleting SMTP config: {str(e)}")
                return redirect('/settings/?tab=smtp-config&smtp_config_failed=true')
        try:
            smtp_server = request.POST.get('smtp_server')
            smtp_port = request.POST.get('smtp_port')
            smtp_from_email = request.POST.get('smtp_from_email')
            smtp_username = request.POST.get('smtp_username')
            smtp_password = request.POST.get('smtp_password')
            smtp_use_tls = request.POST.get('smtp_use_tls') == 'true'
            if not all([smtp_server, smtp_port, smtp_from_email, smtp_username, smtp_password]):
                return redirect('/settings/?tab=smtp-config&smtp_config_failed=true')
            try:
                int(smtp_port)
            except ValueError:
                return redirect('/settings/?tab=smtp-config&smtp_config_failed=true')
            smtp_config, created = SmtpConfig.objects.update_or_create(
                user=request.user,
                defaults={'smtp_server': smtp_server, 'smtp_port': smtp_port, 'smtp_from_email': smtp_from_email,
                          'smtp_username': smtp_username, 'smtp_password': smtp_password, 'smtp_use_tls': smtp_use_tls}
            )
            logger.info(f"SMTP config {'created' if created else 'updated'} for user {request.user.username}")
            return redirect('/settings/?tab=smtp-config&smtp_config_success=true')
        except Exception as e:
            logger.error(f"Error saving SMTP configuration: {str(e)}")
            return redirect('/settings/?tab=smtp-config&smtp_config_failed=true')
    return redirect('/settings/?tab=smtp-config')


@login_required
def test_smtp_connection(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    try:
        smtp_server = request.POST.get('smtp_server')
        smtp_port = request.POST.get('smtp_port')
        smtp_username = request.POST.get('smtp_username')
        smtp_password = request.POST.get('smtp_password')
        smtp_from_email = request.POST.get('smtp_from_email')
        smtp_use_tls = request.POST.get('smtp_use_tls') == 'true'
        if not all([smtp_server, smtp_port, smtp_username, smtp_password]):
            return JsonResponse({'success': False, 'message': 'All fields are required for testing connection'})
        try:
            smtp_port = int(smtp_port)
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Invalid port number'})
        try:
            if smtp_use_tls:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
                server.ehlo()
                server.starttls()
                server.ehlo()
            else:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
            server.login(smtp_username, smtp_password)
            if smtp_from_email:
                try:
                    msg = MIMEMultipart()
                    msg['From'] = smtp_from_email
                    msg['To'] = smtp_username
                    msg['Subject'] = 'KubeBuddy SMTP Test'
                    msg.attach(MIMEText('This is a test email from KubeBuddy. Your SMTP configuration is working correctly!', 'plain'))
                    server.send_message(msg)
                except Exception as email_error:
                    logger.warning(f"SMTP login successful but test email failed: {str(email_error)}")
            server.quit()
            return JsonResponse({'success': True, 'message': '✓ SMTP connection successful! Your settings are correct.'})
        except smtplib.SMTPAuthenticationError:
            return JsonResponse({'success': False, 'message': '✗ Authentication failed. Please check your username and password.'})
        except smtplib.SMTPException as e:
            return JsonResponse({'success': False, 'message': f'✗ SMTP error: {str(e)}'})
        except ConnectionRefusedError:
            return JsonResponse({'success': False, 'message': '✗ Connection refused. Please check your server and port settings.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'✗ Connection failed: {str(e)}'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'✗ Error testing connection: {str(e)}'})


# ========================================
# SSO CONFIGURATION VIEWS
# ========================================

@login_required
def sso_details(request):
    if request.method == 'POST':
        if request.POST.get('delete_sso_config'):
            try:
                provider = request.POST.get('delete_sso_config')
                SsoConfig.objects.filter(user=request.user, provider=provider).delete()
                logger.info(f"SSO config deleted for user {request.user.username}, provider: {provider}")
                return redirect('/settings/?tab=login-settings&sso_config_success=true')
            except Exception as e:
                logger.error(f"Error deleting SSO config: {str(e)}")
                return redirect('/settings/?tab=login-settings&sso_config_failed=true')
        try:
            provider = request.POST.get('provider', '').strip()
            client_id = request.POST.get('client_id', '').strip()
            client_secret = request.POST.get('client_secret', '').strip()
            redirect_uri = request.POST.get('redirect_uri', '').strip()
            if provider not in ['google', 'outlook', 'github']:
                return redirect('/settings/?tab=login-settings&sso_config_failed=true')
            if not client_id or not client_secret:
                return redirect('/settings/?tab=login-settings&sso_config_failed=true')
            existing = SsoConfig.objects.filter(user=request.user, provider=provider).first()
            if existing:
                existing.client_id = client_id
                existing.client_secret = client_secret
                existing.redirect_uri = redirect_uri
                existing.is_active = True
                existing.save()
            else:
                SsoConfig.objects.create(
                    user=request.user, provider=provider, client_id=client_id,
                    client_secret=client_secret, redirect_uri=redirect_uri, is_active=True
                )
            return redirect('/settings/?tab=login-settings&sso_config_success=true')
        except Exception as e:
            logger.error(f"Error saving SSO configuration: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return redirect('/settings/?tab=login-settings&sso_config_failed=true')
    return redirect('/settings/?tab=login-settings')


# ========================================
# SETTINGS VIEW
# ========================================

def settings(request):
    username = request.user.username
    error_message = None
    success_message = None
    active_tab = request.GET.get('tab', 'general')

    ai_configs = {}
    for cfg in AIConfig.objects.all():
        ai_configs[cfg.provider] = {
            'provider': cfg.provider,
            'api_key': cfg.api_key,
            'model': cfg.model,
            'display_name': cfg.get_provider_display()
        }

    smtp_config = None
    try:
        smtp_config = SmtpConfig.objects.get(user=request.user)
    except SmtpConfig.DoesNotExist:
        smtp_config = None

    sso_configs = {}
    try:
        for sso in SsoConfig.objects.filter(user=request.user):
            sso_configs[sso.provider] = {
                'provider': sso.provider,
                'client_id': sso.client_id,
                'client_secret': sso.get_masked_client_secret(),
                'redirect_uri': sso.redirect_uri,
                'is_active': sso.is_active,
                'display_name': sso.get_provider_display()
            }
    except Exception:
        sso_configs = {}

    if request.method == 'POST' and 'save_ai_config' in request.POST:
        provider = request.POST.get('provider')
        api_key = request.POST.get('api_key', '').strip()
        model = request.POST.get('model')
        if provider == "ollama":
            api_key = ""
        if provider in ["gemini", "openai"] and not api_key:
            return redirect('/settings?ai_config_failed=true&tab=ai-config')
        if provider in ["gemini", "openai"]:
            validation_result = api_key_validation(provider, api_key, model)
            if validation_result["status"] == "invalid":
                return redirect('/settings?ai_config_failed=true&tab=ai-config')
        AIConfig.objects.update_or_create(provider=provider, defaults={'api_key': api_key, 'model': model})
        return redirect('/settings?ai_config_success=true&tab=ai-config')

    if request.method == 'POST' and 'delete_api_key' in request.POST:
        provider = request.POST.get('delete_api_key')
        if provider:
            try:
                AIConfig.objects.filter(provider=provider).delete()
                return redirect('/settings?ai_config_deleted=true&tab=ai-config')
            except Exception:
                pass

    if request.method == 'POST' and 'change_password' in request.POST:
        current_password = request.POST.get('currentPassword')
        new_password = request.POST.get('newPassword')
        confirm_password = request.POST.get('confirmPassword')
        user = authenticate(request, username=username, password=current_password)
        if user is None:
            error_message = "Current password is incorrect. Please try again."
        elif new_password != confirm_password:
            error_message = "New passwords do not match. Please try again."
        else:
            user = request.user
            user.set_password(new_password)
            user.save()
            update_session_auth_hash(request, user)
            success_message = "Password updated successfully."

    gemini_models = AIConfig.MODELS_GEMINI
    openai_models = AIConfig.MODELS_OPENAI
    ollama_models = AIConfig.MODELS_OLLAMA

    return render(request, 'main/settings.html', {
        'username': username,
        'error_message': error_message,
        'success_message': success_message,
        'ai_configs': ai_configs,
        'smtp_config': smtp_config,
        'sso_configs': sso_configs,
        'gemini_models_json': json.dumps(gemini_models),
        'openai_models_json': json.dumps(openai_models),
        'ollama_models_json': json.dumps(ollama_models),
        'active_tab': active_tab,
    })


def profile(request):
    username = request.user.username
    return render(request, 'main/profile.html', {'username': username})


# ========================================
# GOOGLE SSO (Standard OAuth with client secret)
# ========================================

def google_callback(request):
    """Handle Google OAuth callback - exchange code for token and log user in"""
    code = request.GET.get('code')
    error = request.GET.get('error')
    
    if error or not code:
        return render(request, 'main/login.html', {'error_message': f'Google login failed: {error or "No code received"}'})
    
    try:
        # Get stored Google SSO config
        sso = SsoConfig.objects.filter(provider='google', is_active=True).first()
        if not sso:
            return render(request, 'main/login.html', {'error_message': 'Google SSO is not configured'})

        redirect_uri = sso.redirect_uri or (request.build_absolute_uri('/').rstrip('/') + '/google-callback/')

        # Exchange code for access token
        token_response = http_requests.post(
            'https://oauth2.googleapis.com/token',
            data={
                'client_id': sso.client_id,
                'client_secret': sso.client_secret,
                'code': code,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code',
            },
            timeout=10
        )
        token_data = token_response.json()
        access_token = token_data.get('access_token')

        if not access_token:
            logger.error(f"Google token exchange failed: {token_data}")
            return render(request, 'main/login.html', {'error_message': 'Failed to get access token from Google'})

        # Get user info from Google
        user_response = http_requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=10
        )
        user_data = user_response.json()

        email = user_data.get('email')
        name = user_data.get('name', '')
        given_name = user_data.get('given_name', '')
        family_name = user_data.get('family_name', '')

        if not email:
            return render(request, 'main/login.html', {'error_message': 'Could not retrieve email from Google'})

        # Get or create user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0],
                'first_name': given_name or (name.split()[0] if name else ''),
                'last_name': family_name or (' '.join(name.split()[1:]) if name and len(name.split()) > 1 else ''),
                'is_superuser': True,
                'is_staff': True,
            }
        )
        if not created:
            user.first_name = given_name or user.first_name
            user.last_name = family_name or user.last_name
            user.save()

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        logger.info(f"User logged in via Google OAuth: {email}")

        kube_config_entry = KubeConfig.objects.first()
        redirect_url = '/KubeBuddy' if kube_config_entry and os.path.isfile(kube_config_entry.path) else '/integrate'
        
        return redirect(redirect_url)

    except Exception as e:
        logger.error(f"Error in google_callback: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return render(request, 'main/login.html', {'error_message': f'Login error: {str(e)}'})


@csrf_exempt
def google_login_api(request):
    """Exchange Google code for access token, get user info, log them in (standard OAuth)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code')
            if not code:
                return JsonResponse({'error': 'No code provided'}, status=400)

            # Get stored Google SSO config
            sso = SsoConfig.objects.filter(provider='google', is_active=True).first()
            if not sso:
                return JsonResponse({'error': 'Google SSO is not configured'}, status=400)

            redirect_uri = sso.redirect_uri or (request.build_absolute_uri('/').rstrip('/') + '/google-callback/')

            # Exchange code for access token
            token_response = http_requests.post(
                'https://oauth2.googleapis.com/token',
                data={
                    'client_id': sso.client_id,
                    'client_secret': sso.client_secret,
                    'code': code,
                    'redirect_uri': redirect_uri,
                    'grant_type': 'authorization_code',
                },
                timeout=10
            )
            token_data = token_response.json()
            access_token = token_data.get('access_token')

            if not access_token:
                logger.error(f"Google token exchange failed: {token_data}")
                return JsonResponse({'error': 'Failed to get access token from Google'}, status=400)

            # Get user info from Google
            user_response = http_requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=10
            )
            user_data = user_response.json()

            email = user_data.get('email')
            name = user_data.get('name', '')
            given_name = user_data.get('given_name', '')
            family_name = user_data.get('family_name', '')

            if not email:
                return JsonResponse({'error': 'Could not retrieve email from Google account'}, status=400)

            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0],
                    'first_name': given_name or (name.split()[0] if name else ''),
                    'last_name': family_name or (' '.join(name.split()[1:]) if name and len(name.split()) > 1 else ''),
                    'is_superuser': True,
                    'is_staff': True,
                }
            )
            if not created:
                user.first_name = given_name or user.first_name
                user.last_name = family_name or user.last_name
                user.save()

            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            
            # CRITICAL FIX: Force session save
            request.session.save()
            request.session.modified = True
            
            logger.info(f"User logged in via Google OAuth: {email}")

            kube_config_entry = KubeConfig.objects.first()
            redirect_url = '/KubeBuddy' if kube_config_entry and os.path.isfile(kube_config_entry.path) else '/integrate'
            
            # Return session key in response so JS can verify
            response = JsonResponse({'success': True, 'redirect_url': redirect_url})
            
            # CRITICAL FIX: Ensure session cookie is set on response
            if request.session.session_key:
                response.set_cookie(
                    'sessionid',
                    request.session.session_key,
                    max_age=1209600,  # 2 weeks
                    httponly=True,
                    samesite='Lax'
                )
            
            return response

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Error in google_login_api: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=400)


# ===== OLD PKCE VERSION (COMMENTED OUT — keeping for reference) =====
# @csrf_exempt
# def google_login_api(request):
#     """Create Django session after PKCE Google login"""
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             email = data.get('email')
#             name = data.get('name')
#             if not email:
#                 return JsonResponse({'error': 'Email is required'}, status=400)
#             user, created = User.objects.get_or_create(
#                 email=email,
#                 defaults={
#                     'username': email.split('@')[0],
#                     'first_name': name.split()[0] if name else '',
#                     'last_name': ' '.join(name.split()[1:]) if name and len(name.split()) > 1 else '',
#                     'is_superuser': True,
#                     'is_staff': True,
#                 }
#             )
#             if not created and name:
#                 user.first_name = name.split()[0]
#                 user.last_name = ' '.join(name.split()[1:]) if len(name.split()) > 1 else ''
#                 user.save()
#             user.backend = 'django.contrib.auth.backends.ModelBackend'
#             login(request, user)
#             logger.info(f"User logged in via Google PKCE: {email}")
#             kube_config_entry = KubeConfig.objects.first()
#             redirect_url = '/KubeBuddy' if kube_config_entry and os.path.isfile(kube_config_entry.path) else '/integrate'
#             return JsonResponse({'success': True, 'redirect_url': redirect_url})
#         except json.JSONDecodeError:
#             return JsonResponse({'error': 'Invalid JSON'}, status=400)
#         except Exception as e:
#             logger.error(f"Error in google_login_api: {str(e)}")
#             return JsonResponse({'error': str(e)}, status=500)
#     return JsonResponse({'error': 'Invalid request method'}, status=400)
# ===== END OLD PKCE VERSION =====


# ========================================
# GITHUB SSO
# ========================================

def github_callback(request):
    return render(request, 'main/github_callback.html')


@csrf_exempt
def github_login_api(request):
    """Exchange GitHub code for access token, get user info, log them in."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code')
            if not code:
                return JsonResponse({'error': 'No code provided'}, status=400)

            # Get stored GitHub SSO config (not tied to a specific user for login page)
            sso = SsoConfig.objects.filter(provider='github', is_active=True).first()
            if not sso:
                return JsonResponse({'error': 'GitHub SSO is not configured'}, status=400)

            redirect_uri = sso.redirect_uri or (request.build_absolute_uri('/').rstrip('/') + '/github-callback/')

            # Exchange code for access token
            token_response = http_requests.post(
                'https://github.com/login/oauth/access_token',
                headers={'Accept': 'application/json'},
                data={
                    'client_id': sso.client_id,
                    'client_secret': sso.client_secret,
                    'code': code,
                    'redirect_uri': redirect_uri,
                },
                timeout=10
            )
            token_data = token_response.json()
            access_token = token_data.get('access_token')

            if not access_token:
                logger.error(f"GitHub token exchange failed: {token_data}")
                return JsonResponse({'error': 'Failed to get access token from GitHub'}, status=400)

            # Get user info from GitHub
            user_response = http_requests.get(
                'https://api.github.com/user',
                headers={'Authorization': f'token {access_token}', 'Accept': 'application/json'},
                timeout=10
            )
            user_data = user_response.json()

            # Get user email (may be private, need separate endpoint)
            email = user_data.get('email')
            if not email:
                email_response = http_requests.get(
                    'https://api.github.com/user/emails',
                    headers={'Authorization': f'token {access_token}', 'Accept': 'application/json'},
                    timeout=10
                )
                emails = email_response.json()
                primary = next((e['email'] for e in emails if e.get('primary') and e.get('verified')), None)
                email = primary or next((e['email'] for e in emails), None)

            if not email:
                return JsonResponse({'error': 'Could not retrieve email from GitHub. Make sure your email is not private, or grant email access.'}, status=400)

            name = user_data.get('name') or user_data.get('login', '')

            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': user_data.get('login', email.split('@')[0]),
                    'first_name': name.split()[0] if name else '',
                    'last_name': ' '.join(name.split()[1:]) if name and len(name.split()) > 1 else '',
                    'is_superuser': True,
                    'is_staff': True,
                }
            )
            if not created and name:
                user.first_name = name.split()[0]
                user.last_name = ' '.join(name.split()[1:]) if len(name.split()) > 1 else ''
                user.save()

            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            logger.info(f"User logged in via GitHub: {email}")

            kube_config_entry = KubeConfig.objects.first()
            redirect_url = '/KubeBuddy' if kube_config_entry and os.path.isfile(kube_config_entry.path) else '/integrate'
            return JsonResponse({'success': True, 'redirect_url': redirect_url})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Error in github_login_api: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=400)


# ========================================
# MICROSOFT OUTLOOK SSO
# ========================================

def outlook_callback(request):
    return render(request, 'main/outlook_callback.html')


@csrf_exempt
def outlook_login_api(request):
    """Exchange Microsoft code for access token, get user info, log them in."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code')
            if not code:
                return JsonResponse({'error': 'No code provided'}, status=400)

            sso = SsoConfig.objects.filter(provider='outlook', is_active=True).first()
            if not sso:
                return JsonResponse({'error': 'Microsoft SSO is not configured'}, status=400)

            redirect_uri = sso.redirect_uri or (request.build_absolute_uri('/').rstrip('/') + '/outlook-callback/')

            # Exchange code for access token
            token_response = http_requests.post(
                'https://login.microsoftonline.com/common/oauth2/v2.0/token',
                data={
                    'client_id': sso.client_id,
                    'client_secret': sso.client_secret,
                    'code': code,
                    'redirect_uri': redirect_uri,
                    'grant_type': 'authorization_code',
                    'scope': 'openid email profile User.Read',
                },
                timeout=10
            )
            token_data = token_response.json()
            access_token = token_data.get('access_token')

            if not access_token:
                logger.error(f"Microsoft token exchange failed: {token_data}")
                return JsonResponse({'error': 'Failed to get access token from Microsoft'}, status=400)

            # Get user info from Microsoft Graph
            user_response = http_requests.get(
                'https://graph.microsoft.com/v1.0/me',
                headers={'Authorization': f'Bearer {access_token}', 'Accept': 'application/json'},
                timeout=10
            )
            user_data = user_response.json()

            email = user_data.get('mail') or user_data.get('userPrincipalName', '')
            name = user_data.get('displayName', '')
            first_name = user_data.get('givenName', '')
            last_name = user_data.get('surname', '')

            if not email:
                return JsonResponse({'error': 'Could not retrieve email from Microsoft account'}, status=400)

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0],
                    'first_name': first_name or (name.split()[0] if name else ''),
                    'last_name': last_name or (' '.join(name.split()[1:]) if name and len(name.split()) > 1 else ''),
                    'is_superuser': True,
                    'is_staff': True,
                }
            )
            if not created:
                user.first_name = first_name or user.first_name
                user.last_name = last_name or user.last_name
                user.save()

            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            logger.info(f"User logged in via Microsoft: {email}")

            kube_config_entry = KubeConfig.objects.first()
            redirect_url = '/KubeBuddy' if kube_config_entry and os.path.isfile(kube_config_entry.path) else '/integrate'
            return JsonResponse({'success': True, 'redirect_url': redirect_url})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            logger.error(f"Error in outlook_login_api: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request method'}, status=400)