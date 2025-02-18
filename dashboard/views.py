from django.shortcuts import render
from .src.cluster_management import k8s_namespaces
from main.models import KubeConfig, Cluster
from .src import k8s_pods, k8s_nodes, k8s_deployments, k8s_daemonset, k8s_replicaset, \
                k8s_statefulset, k8s_jobs, k8s_cronjobs, k8s_cluster_metric, k8s_events, \
                k8s_deployments, k8s_configmaps, k8s_secrets, k8s_services, k8s_endpoints
from django.contrib.auth.decorators import login_required
from kubebuddy.appLogs import logger
from kubernetes import config, client
from dashboard.src import clusters_DB
from .decorators import server_down_handler

@server_down_handler
@login_required
def dashboard(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
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
    # metrics = k8s_cluster_metric.getMetrics(path, current_cluster)

    # get cluster events
    events = k8s_events.get_events(path, current_cluster, True)

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
                                                        # 'metrics' : metrics,
                                                        'registered_clusters': registered_clusters,
                                                        'events': events,})
    
def pods(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path

    logger.info(f"kube config file path  : {path}")
    
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()
    
    pods, pc = k8s_pods.getpods()
    pod_info_list = k8s_pods.get_pod_info(path, current_cluster.cluster_name)

    # get pods status
    status_count = k8s_pods.getPodsStatus(path,current_cluster.cluster_name)

    logger.info(f"pods : {pods}")
    return render(request, 'dashboard/pods.html', { "pods": pods, 
                                                   "pc": pc, 
                                                   "cluster_id": cluster_id,
                                                   "current_cluster": cluster_name,
                                                   "pod_info_list": pod_info_list,
                                                   "status_count": status_count,
                                                   'registered_clusters': registered_clusters})


def pod_info(request, cluster_name, namespace, pod_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id=cluster_id)
    path = current_cluster.kube_config.path

    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    pod_info = {
        "describe": k8s_pods.get_pod_description(path, current_cluster.cluster_name, namespace, pod_name),
        "logs": k8s_pods.get_pod_logs(path, current_cluster.cluster_name, namespace, pod_name),
        "events": k8s_pods.get_pod_events(path, current_cluster.cluster_name, namespace, pod_name),
        "yaml": k8s_pods.get_pod_yaml(path, current_cluster.cluster_name, namespace, pod_name)
    }

    return render(request, 'dashboard/pod_info.html', {
        "pod_info": pod_info,
        "cluster_id": cluster_id,
        "pod_name": pod_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters
    })


def replicasets(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()
    
    rs_status = k8s_replicaset.getReplicasetStatus(path, cluster_name)
    replicaset_info_list = k8s_replicaset.getReplicaSetsInfo(path, cluster_name)
    
    return render(request, 'dashboard/replicasets.html', {"cluster_id": cluster_id, 
                                                          "replicaset_info_list": replicaset_info_list,
                                                          "rs_status": rs_status,
                                                          'current_cluster': cluster_name,
                                                          'registered_clusters': registered_clusters})

def rs_info(request, cluster_name, namespace, rs_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id=cluster_id)
    path = current_cluster.kube_config.path

    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    rs_info = {
        # "describe": k8s_pods.get_replicaset_description(path, current_cluster.cluster_name, namespace, rs_name),
        "events": k8s_replicaset.get_replicaset_events(path, current_cluster.cluster_name, namespace, rs_name),
        "yaml": k8s_replicaset.get_yaml_rs(path, current_cluster.cluster_name, namespace, rs_name)
    }

    return render(request, 'dashboard/rs_info.html', {
        "rs_info": rs_info,
        "cluster_id": cluster_id,
        "rs_name": rs_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters
    })

def deployments(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    dep_status = k8s_deployments.getDeploymentsStatus(path, cluster_name)
    deployment_info_list = k8s_deployments.getDeploymentsInfo(path, cluster_name)
    return render(request, 'dashboard/deployment.html', {"cluster_id": cluster_id, 
                                                         "dep_status": dep_status,
                                                         "deployment_info_list": deployment_info_list,
                                                         'current_cluster': cluster_name,
                                                         'registered_clusters': registered_clusters})

def deploy_info(request, cluster_name, namespace, deploy_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id=cluster_id)
    path = current_cluster.kube_config.path

    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    deploy_info = {
        # "describe": k8s_deployments.get_deploy_description(path, current_cluster.cluster_name, namespace, rs_name),
        "events": k8s_deployments.get_deploy_events(path, current_cluster.cluster_name, namespace, deploy_name),
        "yaml": k8s_deployments.get_yaml_deploy(path, current_cluster.cluster_name, namespace, deploy_name)
    }

    return render(request, 'dashboard/deploy_info.html', {
        "deploy_info": deploy_info,
        "cluster_id": cluster_id,
        "deploy_name": deploy_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters
    })

def events(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path

    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    events = k8s_events.get_events(path, cluster_name, False)
    return render(request, 'dashboard/events.html', {"cluster_id": cluster_id, 
                                                     'events': events,
                                                     'current_cluster': cluster_name,
                                                     'registered_clusters': registered_clusters})


def statefulsets(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path

    statefulsets_status = k8s_statefulset.getStatefulsetStatus(path, cluster_name)
    statefulsets_list = k8s_statefulset.getStatefulsetList(path, cluster_name)

    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    return render(request, 'dashboard/statefulsets.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'statefulsets_list': statefulsets_list,
        'statefulsets_status': statefulsets_status,
        'registered_clusters': registered_clusters
    })

def daemonset(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path

    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    daemonset_status = k8s_daemonset.getDaemonsetStatus(path, cluster_name)
    daemonset_list = k8s_daemonset.getDaemonsetList(path, cluster_name)

    return render(request, 'dashboard/daemonset.html',{
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'daemonset_status': daemonset_status,
        'daemonset_list': daemonset_list,
        'registered_clusters': registered_clusters
    })

def jobs(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path

    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    jobs_status = k8s_jobs.getJobsStatus(path, cluster_name)
    jobs_list = k8s_jobs.getJobsList(path, cluster_name)

    return render(request, 'dashboard/jobs.html',{
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'jobs_status': jobs_status,
        'jobs_list': jobs_list,
        'registered_clusters': registered_clusters
    })

def configmaps(request,cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    configmaps, total_count = k8s_configmaps.get_configmaps(path, cluster_name)
    return render(request, 'dashboard/configmaps.html', {"configmaps": configmaps, 'total_count':total_count, "cluster_id": cluster_id, 'current_cluster': cluster_name})


def secrets(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    secrets = k8s_secrets.list_secrets(path, cluster_name)
    return render(request, 'dashboard/secrets.html', {"secrets": secrets, "cluster_id": cluster_id, 'current_cluster': cluster_name})


def services(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    services = k8s_services.list_kubernetes_services(path, cluster_name)
    total_services = len(services)
    return render(request, 'dashboard/services.html', {"services": services,"total_services": total_services, "cluster_id": cluster_id, 'current_cluster': cluster_name})

def endpoints(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    endpoints = k8s_endpoints.get_endpoints(path, cluster_name)
    total_endpoints = len(endpoints)
    return render(request, 'dashboard/endpoints.html', {"endpoints": endpoints,"total_endpoints":total_endpoints, "cluster_id": cluster_id, 'current_cluster': cluster_name}) 

def nodes(request):
    nc, nodes = k8s_nodes.getnodes()
    logger.info(f"nodes : {nodes}")
    return render(request, 'dashboard/nodes.html', { "nodes": nodes, "nc": nc})