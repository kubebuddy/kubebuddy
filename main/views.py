from django.shortcuts import render

# Create your views here.

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm

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
                        # Redirect to dashboard if a valid kubeconfig file exists
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
    
    return render(request, 'main/login.html', {'form': form})


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