from django.shortcuts import render
from main.models import KubeConfig
from .src import k8s_pods, k8s_nodes, k8s_deployments, k8s_daemonset, k8s_replicaset, k8s_statefulset
from django.contrib.auth.decorators import login_required
from kubebuddy.appLogs import logger
from kubernetes import config, client


@login_required
def dashboard(request):
    cluster_id = 'cluster_id_01' #for reference now, we have to change it to dynamic in future 
    data = KubeConfig.objects.filter(cluster_id=cluster_id).values().first()
    path = data['path']
    logger.info(f"kube config file path  : {path}")

    config.load_kube_config(config_file=path)  # Load the kube config
        
    v1 = client.CoreV1Api()

    # get cluster name
    current_cluster = config.list_kube_config_contexts()[1]['context']['cluster']
    
    namespaces = v1.list_namespace()
    logger.info(f"Namespaces  : {len(namespaces.items)}")

    # check if the user is using default username and password
    if request.user.username == "admin" and request.user.check_password("admin"):
        warning_message = "Warning: You're using the default username & password. Please change it for security reasons."
    else:
        warning_message = None

    # get nodes information
    ready_nodes, not_ready_nodes = k8s_nodes.getNodesStatus()

    # getting list of nodes
    node_list, node_count = k8s_nodes.getnodes()

    # get pods status
    status_count = k8s_pods.getPodsStatus()

    # get list of pods
    pod_list, pode_count = k8s_pods.getpods()

    # get deployment count
    deployments_count = k8s_deployments.getDeploymentsCount()

    # get daemonset count
    daemonset_count = k8s_daemonset.getDaemonsetCount()

    # get replicaset count
    replicaset_count = k8s_replicaset.getReplicasetCount()

    #get statefulset count
    statefulset_count = k8s_statefulset.getStatefulsetCount()

    return render(request, 'dashboard/dashboard.html', {'warning': warning_message, 'ready_nodes': ready_nodes, 'not_ready_nodes' : not_ready_nodes, 'node_count': node_count, 'status_count': status_count, 'pod_count': pode_count, 'current_cluster': current_cluster, 'node_list': node_list, 'deployments_count':deployments_count, 'daemonset_count': daemonset_count, 'replicaset_count':replicaset_count, 'statefulset_count': statefulset_count})
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
    logger.info(f"pods : {pods}")
    return render(request, 'dashboard/pods.html', { "pods": pods, "pc": pc})

def nodes(request):
    nc, nodes = k8s_nodes.getnodes()
    logger.info(f"nodes : {nodes}")
    return render(request, 'dashboard/nodes.html', { "nodes": nodes, "nc": nc})