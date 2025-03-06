from django.shortcuts import render

# Create your views here.
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm

from kubebuddy.appLogs import logger
from django.contrib import messages
from dashboard.src import clusters_DB

from django.contrib.auth.models import User
from .models import Cluster
from django.http import JsonResponse

from kubernetes import config, client
from kubernetes.config.config_exception import ConfigException

from .models import KubeConfig

import os
from django.contrib.auth import update_session_auth_hash
from django.http import JsonResponse

# Chat Bot

from django.views.decorators.csrf import csrf_exempt
from .models import AIConfig
import json
import markdown
import bleach
from google import genai

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_superuser:  # Restrict to superuser only
                    login(request, user)

                    # Check for kubeconfig file in the KubeConfig model
                    kube_config_entry = KubeConfig.objects.first()
                    if kube_config_entry and os.path.isfile(kube_config_entry.path):
                        if username == 'admin' and password == 'admin':
                            # Redirect to the dashboard with a warning message
                            request.session['warning'] = "You're using the default password. Please change it for security reasons."
                            return redirect('/KubeBuddy')
                        else:
                            # Redirect to the dashboard if credentials are valid
                            return redirect('/KubeBuddy')
                    else:
                        # Redirect to integrate page if no valid kubeconfig file exists
                        return redirect('/integrate')
                else:
                    form.add_error(None, 'Only superusers are allowed to log in.')
        else:
            form.add_error(None, 'Invalid credentials.')
    else:
        form = AuthenticationForm()
    messages_storage = messages.get_messages(request)
    return render(request, 'main/login.html', {'form': form, 'messages' : messages_storage})


@login_required
def integrate_with(request):
    error_message = None  # Initialize an error message variable
    try:
        if os.name == 'posix':
            os_name = r"e.g. /Users/user_name/.kube/config or $HOME/.kube/config" # for linux
            path = os.path.expanduser("~/.kube/config") # for linux
        elif os.name == 'nt':
            os_name = r"e.g. C:\Users\user_name\.kube\config" # for windows
            path = os.path.expanduser("C:\\Users\\user_name\\.kube\\config")
        else:
            os_name = "Unknown" # for unknown
    except Exception as e:
        pass



    if request.method == 'POST':
        path = request.POST.get('path')
        path_type = request.POST.get('path_type')

        # Check if the file exists
        if not os.path.isfile(path):
            error_message = f"Error: The file at path '{path}' does not exist."
        else:
            # Check if the file is a valid kube/config
            try:
                if not KubeConfig.objects.filter(path=path).exists():
                    config.load_kube_config(config_file=path)  # Load the kube config
                    
                    # Save the data to the database
                    kube_config = KubeConfig.objects.create(path=path, path_type=path_type)
                    kube_config.save()

                    save_clusters(kube_config, changes=False)
                    return redirect('/KubeBuddy')
                else:
                    kube_config = KubeConfig.objects.get(path=path)
                    save_clusters(kube_config, changes = True)
                    return redirect('/KubeBuddy') # kubeconfig already exists
                
            except ConfigException as e:
                error_message = f"Error: Invalid kube/config file. Details: {str(e)}"
            except Exception as e:
                error_message = f"Error: Unable to connect to the cluster. Details: {str(e)}"

    return render(request, 'main/integrate.html', {
        'error_message': error_message, 'os_name': os_name, 'path': path,
    })

def save_clusters(kube_config, changes):

    contexts, _ = config.list_kube_config_contexts()

    if not contexts:
        return # error handling
    
    # list of names present in file
    cluster_names_in_kubeconfig = [context['context']['cluster'] for context in contexts]
    
    if not changes:
        for context in contexts:
            cluster_name = context['context']['cluster']
            
            try:
                # Set the current context to the specific context
                config.load_kube_config(context=context['name'])

                # this check might not be needed, but am keeping it here for now
                if not Cluster.objects.filter(cluster_name=cluster_name, kube_config=kube_config).exists():
                    cluster = Cluster.objects.create(cluster_name=cluster_name, kube_config=kube_config)
                    cluster.save()
                else:
                    pass

            except Exception as e:
                print("exception caught:",e)
    else:
        # file already exists (updated)
        existing_clusters = Cluster.objects.filter(kube_config=kube_config)
        existing_cluster_names = [cluster.cluster_name for cluster in existing_clusters]

        # create newly added clusters
        for context in contexts:
            cluster_name = context['context']['cluster']
                
            # If this cluster is not already in the database, add it
            if cluster_name not in existing_cluster_names:
                Cluster.objects.create(cluster_name=cluster_name, kube_config=kube_config)
        
        clusters_to_delete = [cluster for cluster in existing_clusters if cluster.cluster_name not in cluster_names_in_kubeconfig]
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

        # Debugging output
        logger.debug(f"username: {username}, old_password: {password}, new_password: {new_password}, confirm_new_password: {confirm_new_password}")

        try:
            user = User.objects.get(username=username)
            # Check if the user is a superuser
            if not user.is_superuser:
                error_message = "The specified user is not a superuser."
                
            # Authenticate the user
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
    return render(request, 'main/change_password.html', {'error_message': error_message})

@login_required
def cluster_select(request):

    registered_clusters = clusters_DB.get_registered_clusters()

    return render(request, 'main/cluster_select.html', {'registered_clusters' : registered_clusters})

def cluster_error(request, cluster_name):
    pass
    return render(request, 'cluster_error.html')

@login_required
def delete_cluster(request, pk):
    cluster = Cluster.objects.get(pk=pk)
    cluster.delete()
    return JsonResponse({'status': 'deleted'})


# System prompt to focus responses on technical topics
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
    """Convert Markdown to safe HTML."""
    html_output = markdown.markdown(response_text)  # Convert Markdown to HTML
    safe_html = bleach.clean(html_output, tags=["p", "strong", "em", "code", "ul", "ol", "li", "a", "br"])  # Sanitize
    return safe_html

# ChatBot Views
def gemini_response(api_key, user_message):
    
    try:
        client = genai.Client(api_key=api_key)
        
        # For Gemini, we need to combine the system prompt and user message 
        # in a specific format depending on the API version
        try:
            # Newer method with system prompt support
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[
                    {"role": "system", "parts": [SYSTEM_PROMPT]},
                    {"role": "user", "parts": [user_message]}
                ]
            )
        except Exception:
            # Fallback method for older API versions or models
            combined_prompt = f"{SYSTEM_PROMPT}\n\nUser: {user_message}\nBuddy AI:"
            response = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=combined_prompt
            )
            
        return render_markdown(response.text)
    except Exception as e:
        return f"Error generating response: {str(e)}"

def openai_response(api_key, user_message):
    """Generate a response using the OpenAI API with system prompt."""
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating response: {str(e)}"

@csrf_exempt
def check_api_key(request):
    """Check if an API key is set; if not, prompt the user to enter one."""
    config = AIConfig.objects.first()
    if config and config.api_key:
        return JsonResponse({"status": "success", "provider": config.provider, "api_key": "********"})
    else:
        return JsonResponse({"status": "missing", "message": "Please set the API key and provider."})

@csrf_exempt
def validate_api_key(request):
    """Validate the API key by making a test API call."""
    if request.method == "POST":
        data = json.loads(request.body)
        provider = data.get("provider")
        api_key = data.get("api_key")

        if provider not in ["openai", "gemini"]:
            return JsonResponse({"status": "error", "message": "Invalid provider selected."})

        # Basic validation
        if not api_key:
            return JsonResponse({"status": "invalid", "message": "API key cannot be empty."})

        try:
            if provider == "gemini":
                # Test the API key with a simple request
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-2.0-flash", 
                    contents="Test"
                )
                # If we get here, the key works
                return JsonResponse({"status": "valid"})
                
            elif provider == "openai":
                # Test OpenAI key
                client = openai.OpenAI(api_key=api_key)
                models = client.models.list()
                return JsonResponse({"status": "valid"})
                
        except Exception as e:
            return JsonResponse({"status": "invalid", "message": f"API key validation failed: {str(e)}"})

    return JsonResponse({"status": "error", "message": "Invalid request method."})

@csrf_exempt
def set_api_key(request):
    """Allow the user to set an API key and provider."""
    if request.method == "POST":
        data = json.loads(request.body)
        provider = data.get("provider")
        api_key = data.get("api_key")

        if provider not in ["openai", "gemini"]:
            return JsonResponse({"status": "error", "message": "Invalid provider selected."})

        if not api_key:
            return JsonResponse({"status": "error", "message": "API key cannot be empty."})

        try:
            # Save API key - update or create a single config entry
            config, created = AIConfig.objects.update_or_create(
                defaults={"provider": provider, "api_key": api_key}
            )
            
            return JsonResponse({"status": "success", "message": "API key saved successfully."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Error saving API key: {str(e)}"})

    return JsonResponse({"status": "error", "message": "Invalid request method."})

@csrf_exempt
def chatbot_response(request):
    """Handles chatbot communication."""
    if request.method == "POST":
        data = json.loads(request.body)
        user_message = data.get("message")

        # Get API key
        config = AIConfig.objects.first()
        if not config or not config.api_key:
            return JsonResponse({"status": "error", "message": "API key not set. Please configure it first."})

        provider = config.provider
        api_key = config.api_key

        try:
            if provider == "gemini":
                bot_response = gemini_response(api_key, user_message)
            elif provider == "openai":
                bot_response = openai_response(api_key, user_message)
            else:
                bot_response = "Sorry, I couldn't process that request. Invalid provider."

            return JsonResponse({"status": "success", "message": bot_response})

        except Exception as e:
            return JsonResponse({"status": "error", "message": f"Error: {str(e)}"})

    return JsonResponse({"status": "error", "message": "Invalid request method."})



def settings(request):
    username = request.user.username
    error_message = None
    success_message = None
    ai_configs = {}
    for config in AIConfig.objects.all():
        ai_configs[config.provider] = {
            'provider': config.provider,
            'api_key': config.api_key,
            'display_name': config.get_provider_display()
        }
    
    # Handle form submission for AI configuration
    if request.method == 'POST' and 'save_ai_config' in request.POST:
        provider = request.POST.get('aiModel')
        api_key = request.POST.get('apiKey')
        
        if provider and api_key:
            # Update or create AI configuration
            obj, created = AIConfig.objects.update_or_create(
                provider=provider,
                defaults={'api_key': api_key}
            )
            return redirect('settings?ai_config_success=true')
            
    # Add this block for handling API key deletion
    if request.method == 'POST' and 'delete_api_key' in request.POST:
        provider = request.POST.get('delete_api_key')
        if provider:
            try:
                AIConfig.objects.filter(provider=provider).delete()
                return redirect('settings?ai_config_deleted=true')
            except Exception as e:
                # Handle exception
                pass
    
    if request.method == 'POST' and 'change_password' in request.POST:
        current_password = request.POST.get('currentPassword')
        new_password = request.POST.get('newPassword')
        confirm_password = request.POST.get('confirmPassword')
        
        # Authenticate the user with current password
        user = authenticate(request, username=username, password=current_password)
        
        if user is None:
            error_message = "Current password is incorrect. Please try again."
        elif new_password != confirm_password:
            error_message = "New passwords do not match. Please try again."
        else:
            # Change the password
            user = request.user
            user.set_password(new_password)
            user.save()
            
            # Update the session to prevent logout
            update_session_auth_hash(request, user)
            
            success_message = "Password updated successfully."
    # Get existing AI configuration if available
    ai_configs = {}
    for config in AIConfig.objects.all():
        ai_configs[config.provider] = {
            'provider': config.provider,
            'api_key': config.api_key,
            'display_name': config.get_provider_display()
        }
    
    # Handle form submission for AI configuration
    if request.method == 'POST' and 'save_ai_config' in request.POST:
        provider = request.POST.get('aiModel')
        api_key = request.POST.get('apiKey')
        
        if provider and api_key:
            # Update or create AI configuration
            obj, created = AIConfig.objects.update_or_create(
                provider=provider,
                defaults={'api_key': api_key}
            )
            return redirect('settings?ai_config_success=true')
    
    return render(request, 'main/settings.html', {
        'username': username,
        'error_message': error_message,
        'success_message': success_message,
        'ai_configs': ai_configs,
    })

def profile(request):
    username = request.user.username
    return render(request, 'main/profile.html', {'username': username})