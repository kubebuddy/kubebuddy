from django.shortcuts import render
from main.models import KubeConfig, Cluster
from .src import k8s_pods, k8s_nodes, k8s_deployments, k8s_daemonset, k8s_replicaset, \
                k8s_statefulset, k8s_jobs, k8s_cronjobs, k8s_namespaces
from django.contrib.auth.decorators import login_required
from kubebuddy.appLogs import logger
from kubernetes import config, client
from .decorators import server_down_handler

@server_down_handler
@login_required
def dashboard(request,cluster_id):
    # cluster_id = 'cluster_id_01' #for reference now, we have to change it to dynamic in future
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    # data = KubeConfig.objects.filter(cluster_id=cluster_id).values().first()
    # path = data['path']
    logger.info(f"kube config file path  : {path}")

    config.load_kube_config(config_file=path, context = current_cluster.cluster_name)  # Load the kube config
        
    v1 = client.CoreV1Api()

    # get cluster name
    current_cluster = current_cluster.cluster_name
    
    namespaces = v1.list_namespace().items
    namespaces_count = len(namespaces)
    logger.info(f"Namespaces  : {len(namespaces)}")

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

    # get statefulset count
    statefulset_count = k8s_statefulset.getStatefulsetCount()

    # get jobs count
    job_count = k8s_jobs.getJobCount()

    # get cronjobs count
    cronjob_count = k8s_cronjobs.getCronJobCount()

    # get namespaces list
    namespaces = k8s_namespaces.get_namespace()

    return render(request, 'dashboard/dashboard.html', {'warning': warning_message, 
                                                        'ready_nodes': ready_nodes, 
                                                        'not_ready_nodes' : not_ready_nodes, 
                                                        'node_count': node_count, 
                                                        'status_count': status_count, 
                                                        'pod_count': pode_count, 
                                                        'current_cluster': current_cluster, 
                                                        'node_list': node_list, 
                                                        'deployments_count':deployments_count, 
                                                        'daemonset_count': daemonset_count, 
                                                        'replicaset_count':replicaset_count, 
                                                        'statefulset_count': statefulset_count, 
                                                        'job_count': job_count, 
                                                        'cronjob_count': cronjob_count,
                                                        'namespaces':namespaces})
    
def pods(request):

    pods, pc = k8s_pods.getpods()
    logger.info(f"pods : {pods}")
    return render(request, 'dashboard/pods.html', { "pods": pods, "pc": pc})

def nodes(request):
    nc, nodes = k8s_nodes.getnodes()
    logger.info(f"nodes : {nodes}")
    return render(request, 'dashboard/nodes.html', { "nodes": nodes, "nc": nc})