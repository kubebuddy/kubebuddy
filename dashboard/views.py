from django.shortcuts import render
from main.models import KubeConfig, Cluster
from .src import k8s_pods, k8s_nodes, k8s_deployments, k8s_daemonset, k8s_replicaset, \
                k8s_statefulset, k8s_jobs, k8s_cronjobs, k8s_namespaces, k8s_cluster_metric, k8s_events
from django.contrib.auth.decorators import login_required
from kubebuddy.appLogs import logger
from kubernetes import config, client
from dashboard.src import clusters_DB
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

    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    # get nodes information
    ready_nodes, not_ready_nodes = k8s_nodes.getNodesStatus()

    # getting list of nodes
    node_list, node_count = k8s_nodes.getnodes()

    # get pods status
    status_count = k8s_pods.getPodsStatus(path,current_cluster)

    # get list of pods
    pod_list, pode_count = k8s_pods.getpods()

    # get deployment count
    deployments_status = k8s_deployments.getDeploymentsStatus(path, current_cluster)

    # get daemonset count
    daemonset_status = k8s_daemonset.getDaemonsetStatus(path, current_cluster)

    # get replicaset count
    replicaset_status = k8s_replicaset.getReplicasetStatus(path, current_cluster)

    # get statefulset count
    statefulset_status = k8s_statefulset.getStatefulsetStatus(path, current_cluster)

    # get jobs count
    jobs_status = k8s_jobs.getJobsStatus(path, current_cluster)

    # get cronjobs count
    cronjob_status = k8s_cronjobs.getCronJobsStatus(path, current_cluster)

    # get namespaces list
    namespaces = k8s_namespaces.get_namespace()

    # get cluster metrics
    metrics = k8s_cluster_metric.getMetrics(path, current_cluster)

    # get cluster events
    events = k8s_events.get_events(path, current_cluster)

    return render(request, 'dashboard/dashboard.html', {'warning': warning_message, 
                                                        'ready_nodes': ready_nodes, 
                                                        'not_ready_nodes' : not_ready_nodes, 
                                                        'node_count': node_count, 
                                                        'status_count': status_count, 
                                                        'pod_count': pode_count, 
                                                        'current_cluster': current_cluster, 
                                                        'node_list': node_list, 
                                                        'deployments_status':deployments_status,
                                                        'daemonset_status': daemonset_status, 
                                                        'replicaset_status':replicaset_status, 
                                                        'statefulset_status': statefulset_status, 
                                                        'jobs_status': jobs_status, 
                                                        'cronjob_status': cronjob_status,
                                                        'namespaces':namespaces,
                                                        'namespaces_count': namespaces_count,
                                                        'cluster_id': cluster_id,
                                                        'registered_clusters': registered_clusters})
    
def pods(request):

    pods, pc = k8s_pods.get_pod_info()
    logger.info(f"pods : {pods}")
    return render(request, 'dashboard/pods.html', { "pods": pods, "pc": pc})

def nodes(request):
    nc, nodes = k8s_nodes.getnodes()
    logger.info(f"nodes : {nodes}")
    return render(request, 'dashboard/nodes.html', { "nodes": nodes, "nc": nc})