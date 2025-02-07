from django.shortcuts import render

# Create your views here.

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm

from kubebuddy.appLogs import logger
from django.contrib import messages

from django.contrib.auth.models import User
from .models import Cluster
from django.http import JsonResponse

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
                            return redirect('/cluster-select')
                        else:
                            # Redirect to the dashboard if credentials are valid
                            return redirect('/cluster-select')
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
                if not KubeConfig.objects.filter(path=path).exists():
                    config.load_kube_config(config_file=path)  # Load the kube config
                    
                    # Save the data to the database
                    kube_config = KubeConfig.objects.create(path=path, path_type=path_type)
                    kube_config.save()

                    save_clusters(kube_config, changes=False)
                    return redirect('/cluster-select')
                else:
                    kube_config = KubeConfig.objects.get(path=path)
                    save_clusters(kube_config, changes = True)
                    return redirect('/cluster-select') # kubeconfig already exists
                
            except ConfigException as e:
                error_message = f"Error: Invalid kube/config file. Details: {str(e)}"
            except Exception as e:
                error_message = f"Error: Unable to connect to the cluster. Details: {str(e)}"

    return render(request, 'main/integrate.html', {
        'error_message': error_message,
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
    # pods to check for control plane and dns status
    control_plane_components = [
    {"key": "component", "value": "kube-apiserver"},
    {"key": "component", "value": "kube-controller-manager"},
    {"key": "component", "value": "kube-scheduler"},
    {"key": "component", "value": "etcd"}
    ]
    core_dns_label = {"key": "k8s-app", "value": "kube-dns"}

    # saved clusters in db
    registered_clusters = Cluster.objects.all()

    for context in registered_clusters:
        cluster_name = context.cluster_name
        failed_control_pods = []
        failed_dns_pods = []
        
        try:
            # Set the current context to the specific context
            config.load_kube_config(context=cluster_name)
            v1 = client.CoreV1Api()

            # Get number of nodes
            nodes = v1.list_node().items
            context.number_of_nodes = len(nodes)

            # Check if all control plane components are running
            context.control_plane_status = "Running"
            context.core_dns_status = "Running"
            for component in control_plane_components:
                label_selector = f"{component['key']}={component['value']}"
                pods = v1.list_namespaced_pod(namespace="kube-system", label_selector=label_selector)
                for pod in pods.items:
                    print(pod.metadata.name)
                    print(pod.status.phase)
                    print(label_selector)
                    if pod.status.phase != "Running":
                        print("reached ")
                        context.control_plane_status = "Unhealthy"
                        failed_control_pods.append(pod.metadata.name)

            # Check if all CoreDNS pods are running
            label_selector = f"{core_dns_label['key']}={core_dns_label['value']}"
            core_dns_pods = v1.list_namespaced_pod(namespace="kube-system", label_selector=label_selector)
            for pod in core_dns_pods.items:
                if pod.status.phase != "Running":
                    context.core_dns_status = "Unhealthy"
                    failed_dns_pods.append(pod.metadata.name)
            
            # if failed pods present add them to cluster info
            context.failed_control_pods = failed_control_pods
            context.failed_dns_pods = failed_dns_pods

        except Exception as e:
            print(e)
            context.control_plane_status = "Unavailable"
            context.core_dns_status = "Unavailable"



    return render(request, 'main/cluster_select.html', {'registered_clusters' : registered_clusters})

def delete_cluster(request, pk):
    cluster = Cluster.objects.get(pk=pk)
    cluster.delete()
    return JsonResponse({'status': 'deleted'})