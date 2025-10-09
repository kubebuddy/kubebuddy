from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from kubebuddy.appLogs import logger
from dashboard.src import clusters_DB
from kubernetes import config, client
from kubernetes.config.config_exception import ConfigException

from .models import Cluster, KubeConfig, AIConfig

import os
import json
import markdown
import bleach

# Third-party AI clients
from google import genai
from google.genai import types
import openai
import ollama

# Optional requests for local Ollama HTTP API
try:
    import requests
except Exception:
    requests = None

# ---------------------- AUTHENTICATION ----------------------

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
                        return redirect('/integrate')
                else:
                    form.add_error(None, 'Only superusers are allowed to log in.')
            else:
                form.add_error(None, 'Invalid credentials.')
    else:
        form = AuthenticationForm()
    messages_storage = messages.get_messages(request)
    return render(request, 'main/login.html', {'form': form, 'messages': messages_storage})

@login_required
def logout_view(request):
    # Clear session on logout
    request.session.flush()
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

        try:
            user = User.objects.get(username=username)
            if not user.is_superuser:
                error_message = "The specified user is not a superuser."
            authenticated_user = authenticate(request, username=username, password=password)
            if authenticated_user is None:
                error_message = "Current password is incorrect. Please try again."
            elif new_password != confirm_new_password:
                error_message = "New passwords do not match. Please try again."
            else:
                user.set_password(new_password)
                user.save()
                messages.success(request, "Password updated successfully.")
                return redirect('/')
        except User.DoesNotExist:
            error_message = "User does not exist."
    return render(request, 'main/settings.html', {'error_message': error_message})

# ---------------------- KUBERNETES INTEGRATION ----------------------

@login_required
def integrate_with(request):
    error_message = None
    os_name = "Unknown"
    path = ""

    try:
        if os.name == 'posix':
            os_name = r"e.g. /Users/user_name/.kube/config or $HOME/.kube/config"
            path = os.path.expanduser("~/.kube/config")
        elif os.name == 'nt':
            profile_name = os.environ.get("USERNAME")
            os_name = r"e.g. \%USERPROFILE%\.kube\config"
            path = os.path.expanduser(f"C:\\Users\\{profile_name}\\.kube\\config")
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
        'error_message': error_message,
        'os_name': os_name,
        'path': path,
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
        clusters_to_delete = [cluster for cluster in existing_clusters if cluster.cluster_name not in cluster_context_mapping]
        for cluster in clusters_to_delete:
            cluster.delete()

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

# ---------------------- AI CHATBOT ----------------------

SYSTEM_PROMPT = """
You are Buddy AI, a technical assistant specializing in Kubernetes, cloud, programming, DevOps, and system architecture. 
Keep responses concise, accurate, and include code examples if relevant.
"""

def render_markdown(response_text):
    html_output = markdown.markdown(response_text, extensions=["fenced_code", "codehilite"])
    allowed_tags = ["p", "strong", "em", "code", "ul", "ol", "li", "a", "br", "pre", "blockquote"]
    safe_html = bleach.clean(html_output, tags=allowed_tags)
    safe_html = safe_html.replace(
        "<pre>", '<pre style="background:#f5f5f5; border:1px solid #ccc; padding:10px; border-radius:5px; margin:10px 0; font-family:monospace;">'
    ).replace("</pre>", "</pre>")
    return safe_html

def gemini_response(api_key, model, user_message):
    try:
        client = genai.Client(api_key=api_key)
        full_message = f"{SYSTEM_PROMPT}\n\nUser: {user_message}"
        response = client.models.generate_content(
            model=model,
            contents=full_message
        )
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

def ollama_response(api_key, model, user_message):
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
def chatbot_response(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_message = data.get("message")
        provider_from_request = data.get("provider")
        
        if provider_from_request:
            try:
                config = AIConfig.objects.get(provider=provider_from_request)
            except AIConfig.DoesNotExist:
                return JsonResponse({"status": "error", "message": f"{provider_from_request} not configured. Please set it up in <a href='/settings/?tab=ai-config'>Settings</a>."})
        else:
            config = AIConfig.objects.first()
        
        if not config:
            message = "No AI provider configured. Please set it up in <a href='/settings/?tab=ai-config'>Settings</a>"
            return JsonResponse({"status": "error", "message": message})
        
        if not config.api_key and config.provider not in ["ollama"]:
            message = f"API key not set for {config.provider}. Please configure it in <a href='/settings/?tab=ai-config'>Settings</a>"
            return JsonResponse({"status": "error", "message": message})

        provider = config.provider
        api_key = config.api_key
        model = config.model

        try:
            if provider == "gemini":
                bot_response = gemini_response(api_key, model, user_message)
            elif provider == "openai":
                bot_response = openai_response(api_key, model, user_message)
            elif provider == "ollama":
                bot_response = ollama_response(api_key, model, user_message)
            else:
                bot_response = "Invalid provider selected."
            return JsonResponse({"status": "success", "message": bot_response})
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Error: {str(e)}"})

    return JsonResponse({"status": "error", "message": "Invalid request method."})

# ---------------------- OLLAMA ENDPOINT (READS FROM SETTINGS) ----------------------
@csrf_exempt
def ollama_chat_response(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            user_message = data.get("message")

            if not user_message:
                return JsonResponse({"status": "error", "message": "Message cannot be empty."})

            config = AIConfig.objects.filter(provider="ollama").first()
            
            if not config or not config.model:
                return JsonResponse({
                    "status": "error", 
                    "message": "Ollama model not configured. Please set it in <a href='/settings/?tab=ai-config'>Settings</a>."
                })
            
            model = config.model

            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            )

            bot_message = response.message.content if hasattr(response, "message") else str(response)
            
            return JsonResponse({
                "status": "success",
                "message": render_markdown(bot_message)
            })

        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Ollama error: {str(e)}"})

    return JsonResponse({"status": "error", "message": "Invalid request method."})

# ---------------------- API KEY MANAGEMENT ----------------------

@csrf_exempt
def set_api_key(request):
    if request.method == "POST":
        data = json.loads(request.body)
        provider = data.get("provider")
        api_key = data.get("api_key")
        if provider not in ["openai", "gemini", "ollama"]:
            return JsonResponse({"status": "error", "message": "Invalid provider."})
        if provider in ["openai", "gemini"] and not api_key:
            return JsonResponse({"status": "error", "message": "API key cannot be empty for this provider."})
        AIConfig.objects.update_or_create(provider=provider, defaults={"provider": provider, "api_key": api_key})
        return JsonResponse({"status": "success", "message": "API key saved."})
    return JsonResponse({"status": "error", "message": "Invalid request method."})

@csrf_exempt
def check_api_key(request):
    config = AIConfig.objects.first()
    if not config:
        return JsonResponse({"status": "missing", "message": "Please set the API key and provider."})
    
    if config.provider == "ollama":
        if config.model:
            return JsonResponse({"status": "success", "provider": config.provider})
        else:
            return JsonResponse({"status": "missing", "message": "Ollama model not configured."})
    
    if config.api_key:
        return JsonResponse({"status": "success", "provider": config.provider})
    else:
        return JsonResponse({"status": "missing", "message": "API key not set."})

@csrf_exempt
def validate_api_key(request):
    try:
        config = AIConfig.objects.first()
        if config and (config.api_key or config.provider == "ollama"):
            return JsonResponse({"status": "success", "message": "API key validated successfully."})
        else:
            return JsonResponse({"status": "error", "message": "API key missing or not set."})
    except Exception as e:
        return JsonResponse({"status": "error", "message": f"Validation error: {str(e)}"})

# ---------------------- SETTINGS ----------------------

def settings(request):
    username = request.user.username
    error_message = None
    success_message = None
    active_tab = request.GET.get('tab', 'general')
    ai_configs = {cfg.provider: {"provider": cfg.provider, "api_key": cfg.api_key, "model": cfg.model, "display_name": cfg.get_provider_display()} for cfg in AIConfig.objects.all()}

    if request.method == "POST":
        if 'save_ai_config' in request.POST:
            provider = request.POST.get("provider")
            api_key = request.POST.get("api_key", "").strip()
            model = request.POST.get("model")
            if provider in ["gemini", "openai"] and not api_key:
                return redirect("/settings?ai_config_failed=true&tab=ai-config")
            AIConfig.objects.update_or_create(provider=provider, defaults={"api_key": api_key, "model": model})
            return redirect("/settings?ai_config_success=true&tab=ai-config")
        
        elif 'delete_api_key' in request.POST:
            provider_to_delete = request.POST.get("delete_api_key")
            try:
                config = AIConfig.objects.get(provider=provider_to_delete)
                config.delete()
                return redirect("/settings?delete_success=true&tab=ai-config")
            except AIConfig.DoesNotExist:
                return redirect("/settings?delete_failed=true&tab=ai-config")

    gemini_models = AIConfig.MODELS_GEMINI
    openai_models = AIConfig.MODELS_OPENAI
    ollama_models = AIConfig.MODELS_OLLAMA

    return render(request, "main/settings.html", {
        "username": username,
        "error_message": error_message,
        "success_message": success_message,
        "ai_configs": ai_configs,
        "gemini_models_json": json.dumps(gemini_models),
        "openai_models_json": json.dumps(openai_models),
        "ollama_models_json": json.dumps(ollama_models),
        "active_tab": active_tab,
    })

def profile(request):
    return render(request, "main/profile.html", {"username": request.user.username})
