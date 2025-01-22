from django.shortcuts import render
from main.models import KubeConfig
from .src import k8s_pods, k8s_nodes
from django.contrib.auth.decorators import login_required

from kubernetes import config, client



# Create your views here.
@login_required
def dashboard(request):
    cluster_id = 'cluster_id_01' #for reference now, we have to change it to dynamic in future 
    data = KubeConfig.objects.filter(cluster_id=cluster_id).values().first()
    path = data['path']
    print(path)

    # try:
    config.load_kube_config(config_file=path)  # Load the kube config
    v1 = client.CoreV1Api()
    namespaces = v1.list_namespace()
    return render(request, 'dashboard/dashboard.html')
    # cluster_id = 'cluster_id_01' #for reference now, we have to change it to dynamic in future 
    # data = KubeConfig.objects.filter(cluster_id=cluster_id).values().first()
    # path = data['path']


    # try:
    #     config.load_kube_config(config_file=path)  # Load the kube config
    #     v1 = client.CoreV1Api()
    #     namespaces = v1.list_namespace()
    #     return render(request, 'dashboard/dashboard.html')
    
    # except Exception as e:
    #     error_message = f"Error: Unable to connect to the cluster. \n Details: {str(e)}"
    #     return render(request, 'dashboard/error.html', {"error": error_message})

def pods(request):



    pods, pc = k8s_pods.getpods()
    return render(request, 'dashboard/pods.html', { "pods": pods, "pc": pc})

def nodes(request):
    nc, nodes = k8s_nodes.getnodes()
    return render(request, 'dashboard/nodes.html', { "nodes": nodes, "nc": nc})