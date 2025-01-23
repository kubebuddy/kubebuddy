from django.shortcuts import render

# Create your views here.

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm

from kubebuddy.appLogs import logger
from django.contrib import messages

from django.contrib.auth.models import User

from kubernetes import config, client
from kubernetes.config.config_exception import ConfigException

from .models import KubeConfig

import os

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
                            return redirect('/dashboard')
                        else:
                            # Redirect to the dashboard if credentials are valid
                            return redirect('/dashboard')
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

    if request.method == 'POST':
        path = request.POST.get('path')
        path_type = request.POST.get('path_type')

        # Check if the file exists
        if not os.path.isfile(path):
            error_message = f"Error: The file at path '{path}' does not exist."
        else:
            # Check if the file is a valid kube/config
            try:
                config.load_kube_config(config_file=path)  # Load the kube config
                v1 = client.CoreV1Api()
                namespaces = v1.list_namespace()
                
                # Save the data to the database
                kube_config = KubeConfig.objects.create(path=path, path_type=path_type)
                kube_config.save()

                return redirect('/dashboard')
            except ConfigException as e:
                error_message = f"Error: Invalid kube/config file. Details: {str(e)}"
            except Exception as e:
                error_message = f"Error: Unable to connect to the cluster. Details: {str(e)}"

    return render(request, 'main/integrate.html', {
        'error_message': error_message,
    })

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