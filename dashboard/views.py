from django.shortcuts import render

from .src.cluster_management import k8s_namespaces, k8s_nodes, k8s_limit_range, k8s_resource_quota

from .src.services import k8s_endpoints, k8s_services

from .src.events import k8s_events

from .src.config_secrets import k8s_configmaps, k8s_secrets
from .src.workloads import k8s_cronjobs, k8s_daemonset, k8s_deployments, k8s_jobs, k8s_pods, k8s_replicaset, k8s_statefulset
from .src.persistent_volume import k8s_pv, k8s_pvc, k8s_storage_class
from .src.rbac import k8s_role, k8s_cluster_role_bindings, k8s_cluster_roles, k8s_rolebindings, k8s_service_accounts
from main.models import KubeConfig, Cluster
from .src import k8s_cluster_metric
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
    ready_nodes, not_ready_nodes, node_count = k8s_nodes.getNodesStatus(path, current_cluster)

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
    namespaces = k8s_namespaces.get_namespace(request)

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
    return render(request, 'dashboard/workloads/pods.html', { "pods": pods, 
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

    return render(request, 'dashboard/workloads/pod_info.html', {
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
    
    return render(request, 'dashboard/workloads/replicasets.html', {"cluster_id": cluster_id, 
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
        "describe": k8s_replicaset.get_replicaset_description(path, current_cluster.cluster_name, namespace, rs_name),
        "events": k8s_replicaset.get_replicaset_events(path, current_cluster.cluster_name, namespace, rs_name),
        "yaml": k8s_replicaset.get_yaml_rs(path, current_cluster.cluster_name, namespace, rs_name)
    }

    return render(request, 'dashboard/workloads/rs_info.html', {
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
    return render(request, 'dashboard/workloads/deployment.html', {"cluster_id": cluster_id, 
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
        "describe": k8s_deployments.get_deployment_description(path, current_cluster.cluster_name, namespace, deploy_name),
        "events": k8s_deployments.get_deploy_events(path, current_cluster.cluster_name, namespace, deploy_name),
        "yaml": k8s_deployments.get_yaml_deploy(path, current_cluster.cluster_name, namespace, deploy_name)
    }

    return render(request, 'dashboard/workloads/deploy_info.html', {
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

    return render(request, 'dashboard/workloads/statefulsets.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'statefulsets_list': statefulsets_list,
        'statefulsets_status': statefulsets_status,
        'registered_clusters': registered_clusters
    })

def sts_info(request, cluster_name, namespace, sts_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id=cluster_id)
    path = current_cluster.kube_config.path
    registered_clusters = clusters_DB.get_registered_clusters()

    sts_info = {
        "describe": k8s_statefulset.get_statefulset_description(path, current_cluster.cluster_name, namespace, sts_name),
        "events": k8s_statefulset.get_sts_events(path, current_cluster.cluster_name, namespace, sts_name),
        "yaml": k8s_statefulset.get_yaml_sts(path, current_cluster.cluster_name, namespace, sts_name)
    }

    return render(request, 'dashboard/workloads/sts_info.html', {
        "sts_info": sts_info,
        "cluster_id": cluster_id,
        "sts_name": sts_name,
        'current_cluster': cluster_name,
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

    return render(request, 'dashboard/workloads/daemonset.html',{
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'daemonset_status': daemonset_status,
        'daemonset_list': daemonset_list,
        'registered_clusters': registered_clusters
    })

def daemonset_info(request, cluster_name, namespace, daemonset_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id=cluster_id)
    path = current_cluster.kube_config.path

    registered_clusters = clusters_DB.get_registered_clusters()

    daemonset_info = {
        "describe": k8s_daemonset.get_daemonset_description(path, current_cluster.cluster_name, namespace, daemonset_name),
        "events": k8s_daemonset.get_daemonset_events(path, current_cluster.cluster_name, namespace, daemonset_name),
        "yaml": k8s_daemonset.get_daemonset_yaml(path, current_cluster.cluster_name, namespace, daemonset_name),
    }

    return render(request, 'dashboard/workloads/daemonset_info.html', {
        "daemonset_info": daemonset_info,
        "cluster_id": cluster_id,
        "daemonset_name": daemonset_name,
        'current_cluster': cluster_name,
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

    return render(request, 'dashboard/workloads/jobs.html',{
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'jobs_status': jobs_status,
        'jobs_list': jobs_list,
        'registered_clusters': registered_clusters
    })

def jobs_info(request, cluster_name, namespace, job_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id=cluster_id)
    path = current_cluster.kube_config.path
    registered_clusters = clusters_DB.get_registered_clusters()

    job_info = {
        "describe": k8s_jobs.get_job_description(path, current_cluster.cluster_name, namespace, job_name),
        "events": k8s_jobs.get_job_events(path, current_cluster.cluster_name, namespace, job_name),
        "yaml": k8s_jobs.get_yaml_job(path, current_cluster.cluster_name, namespace, job_name)
    }
    return render(request, 'dashboard/workloads/job_info.html', {
        "job_info": job_info,
        "cluster_id": cluster_id,
        "job_name": job_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters
    })



def cronjobs(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path

    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()
    cronjobs_status = k8s_cronjobs.getCronJobsStatus(path, cluster_name)
    cronjobs_list = k8s_cronjobs.getCronJobsList(path, cluster_name)

    return render(request, 'dashboard/workloads/cronjobs.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'cronjobs_status': cronjobs_status,
        'cronjobs_list': cronjobs_list,
    })

def cronjob_info(request, cluster_name, namespace, cronjob_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id=cluster_id)
    path = current_cluster.kube_config.path
    registered_clusters = clusters_DB.get_registered_clusters()

    cronjob_info = {
        "describe": k8s_cronjobs.get_cronjob_description(path, current_cluster.cluster_name, namespace, cronjob_name),
        "events": k8s_cronjobs.get_cronjob_events(path, current_cluster.cluster_name, namespace, cronjob_name),
        "yaml": k8s_cronjobs.get_yaml_cronjob(path, current_cluster.cluster_name, namespace, cronjob_name)
    }
    return render(request, 'dashboard/workloads/cronjob_info.html', {
        "cronjob_info": cronjob_info,
        "cluster_id": cluster_id,
        "cronjob_name": cronjob_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters
    })

def namespace(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path

    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()
    namespaces = k8s_namespaces.namespaces_data(path, cluster_name)
    namespaces_count = len(namespaces)

    return render(request, 'dashboard/cluster_management/namespace.html',{
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'namespaces': namespaces,
        'namespaces_count': namespaces_count
    })

def configmaps(request,cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()
    configmaps, total_count = k8s_configmaps.get_configmaps(path, cluster_name)
    return render(request, 'dashboard/config_secrets/configmaps.html', {"configmaps": configmaps, 'total_count':total_count, "cluster_id": cluster_id, 'current_cluster': cluster_name, 'registered_clusters': registered_clusters})

def configmap_info(request, cluster_name, namespace, configmap_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id=cluster_id)
    path = current_cluster.kube_config.path

    registered_clusters = clusters_DB.get_registered_clusters()

    configmap_info = {
        "describe": k8s_configmaps.get_configmap_description(path, current_cluster.cluster_name, namespace, configmap_name),
        "events": k8s_configmaps.get_configmap_events(path, current_cluster.cluster_name, namespace, configmap_name),
        "yaml": k8s_configmaps.get_configmap_yaml(path, current_cluster.cluster_name, namespace, configmap_name),
    }

    return render(request, 'dashboard/config_secrets/configmap_info.html', {
        "configmap_info": configmap_info,
        "cluster_id": cluster_id,
        "configmap_name": configmap_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })


def secrets(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()
    secrets, total_secrets = k8s_secrets.list_secrets(path, cluster_name)
    return render(request, 'dashboard/config_secrets/secrets.html', {"secrets": secrets, "total_secrets": total_secrets, "cluster_id": cluster_id, 'current_cluster': cluster_name, 'registered_clusters': registered_clusters})


def secret_info(request, cluster_name, namespace, secret_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id=cluster_id)
    path = current_cluster.kube_config.path

    registered_clusters = clusters_DB.get_registered_clusters()

    secret_info = {
        "describe": k8s_secrets.get_secret_description(path, current_cluster.cluster_name, namespace, secret_name),
        "events": k8s_secrets.get_secret_events(path, current_cluster.cluster_name, namespace, secret_name),
        "yaml": k8s_secrets.get_secret_yaml(path, current_cluster.cluster_name, namespace, secret_name),
    }

    return render(request, 'dashboard/config_secrets/secret_info.html', {
        "secret_info": secret_info,
        "cluster_id": cluster_id,
        "secret_name": secret_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })


def services(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()
    services = k8s_services.list_kubernetes_services(path, cluster_name)
    total_services = len(services)
    return render(request, 'dashboard/services/services.html', {"services": services,"total_services": total_services, "cluster_id": cluster_id, 'current_cluster': cluster_name, 'registered_clusters': registered_clusters})

def service_info(request, cluster_name, namespace, service_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id=cluster_id)
    path = current_cluster.kube_config.path

    registered_clusters = clusters_DB.get_registered_clusters()

    service_info = {
        "describe": k8s_services.get_service_description(path, current_cluster.cluster_name, namespace, service_name),
        "events": k8s_services.get_service_events(path, current_cluster.cluster_name, namespace, service_name),
        "yaml": k8s_services.get_service_yaml(path, current_cluster.cluster_name, namespace, service_name),
    }

    return render(request, 'dashboard/services/service_info.html', {
        "service_info": service_info,
        "cluster_id": cluster_id,
        "service_name": service_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })


def endpoints(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()
    endpoints = k8s_endpoints.get_endpoints(path, cluster_name)
    total_endpoints = len(endpoints)
    return render(request, 'dashboard/services/endpoints.html', {"endpoints": endpoints,"total_endpoints":total_endpoints, "cluster_id": cluster_id, 'current_cluster': cluster_name, 'registered_clusters': registered_clusters}) 

def endpoint_info(request, cluster_name, namespace, endpoint_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id=cluster_id)
    path = current_cluster.kube_config.path

    registered_clusters = clusters_DB.get_registered_clusters()

    endpoint_info = {
        "describe": k8s_endpoints.get_endpoint_description(path, current_cluster.cluster_name, namespace, endpoint_name),
        "events": k8s_endpoints.get_endpoint_events(path, current_cluster.cluster_name, namespace, endpoint_name),
        "yaml": k8s_endpoints.get_endpoint_yaml(path, current_cluster.cluster_name, namespace, endpoint_name),
    }

    return render(request, 'dashboard/services/endpoint_info.html', {
        "endpoint_info": endpoint_info,
        "cluster_id": cluster_id,
        "endpoint_name": endpoint_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })



def nodes(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    nodes = k8s_nodes.get_nodes_info(path, cluster_name)
    ready_nodes, not_ready_nodes, total_nodes = k8s_nodes.getNodesStatus(path, cluster_name)
    
    return render(request, 'dashboard/cluster_management/nodes.html', { 
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'nodes': nodes,
        'ready_nodes': ready_nodes,
        'not_ready_nodes': not_ready_nodes,
        'total_nodes': total_nodes
    })

def limitrange(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    limitranges, total_limitranges = k8s_limit_range.get_limit_ranges(path, cluster_name)

    return render(request, 'dashboard/cluster_management/limitrange.html',{
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'limitranges': limitranges,
        'total_limitranges': total_limitranges
    })


def limitrange_info(request, cluster_name, namespace, limitrange_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id=cluster_id)
    path = current_cluster.kube_config.path

    registered_clusters = clusters_DB.get_registered_clusters()

    limitrange_info = {
        "describe": k8s_limit_range.get_limitrange_description(path, current_cluster.cluster_name, namespace, limitrange_name),
        "events": k8s_limit_range.get_limitrange_events(path, current_cluster.cluster_name, namespace, limitrange_name),
        "yaml": k8s_limit_range.get_limitrange_yaml(path, current_cluster.cluster_name, namespace, limitrange_name),
    }

    return render(request, 'dashboard/cluster_management/limitrange_info.html', { 
        "limitrange_info": limitrange_info,
        "cluster_id": cluster_id,
        "limitrange_name": limitrange_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })

def resourcequotas(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    resourcequotas, total_quotas = k8s_resource_quota.get_resource_quotas(path, cluster_name)

    return render(request, 'dashboard/cluster_management/resourcequotas.html',{
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'resourcequotas': resourcequotas,
        'total_quotas': total_quotas
    })


def resourcequota_info(request, cluster_name, namespace, resourcequota_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id=cluster_id)
    path = current_cluster.kube_config.path

    registered_clusters = clusters_DB.get_registered_clusters()

    resourcequota_info = {
        "describe": k8s_resource_quota.get_resourcequota_description(path, current_cluster.cluster_name, namespace, resourcequota_name),
        "events": k8s_resource_quota.get_resourcequota_events(path, current_cluster.cluster_name, namespace, resourcequota_name),
        "yaml": k8s_resource_quota.get_resourcequota_yaml(path, current_cluster.cluster_name, namespace, resourcequota_name),
    }

    return render(request, 'dashboard/cluster_management/resourcequota_info.html', {
        "resourcequota_info": resourcequota_info,
        "cluster_id": cluster_id,
        "resourcequota_name": resourcequota_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })


def persistentvolume(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    pvs, total_pvs = k8s_pv.list_persistent_volumes(path, cluster_name)

    return render(request, 'dashboard/persistent_storage/persistentvolume.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'pvs': pvs,
        'total_pvs': total_pvs
    })

def persistentvolumeclaim(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    pvc, total_pvc = k8s_pvc.list_pvc(path, cluster_name)

    return render(request, 'dashboard/persistent_storage/persistentvolumeclaim.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'pvc': pvc,
        'total_pvc': total_pvc
    })

def pvc_info(request, cluster_name, namespace, pvc_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id=cluster_id)
    path = current_cluster.kube_config.path

    registered_clusters = clusters_DB.get_registered_clusters()

    pvc_info = {
        "describe": k8s_pvc.get_pvc_description(path, current_cluster.cluster_name, namespace, pvc_name),
        "events": k8s_pvc.get_pvc_events(path, current_cluster.cluster_name, namespace, pvc_name),
        "yaml": k8s_pvc.get_pvc_yaml(path, current_cluster.cluster_name, namespace, pvc_name),
    }

    return render(request, 'dashboard/persistent_storage/pvc_info.html', {
        "pvc_info": pvc_info,
        "cluster_id": cluster_id,
        "pvc_name": pvc_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })


def storageclass(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    sc, total_sc = k8s_storage_class.list_storage_classes(path, cluster_name)

    return render(request, 'dashboard/persistent_storage/storageclass.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'sc': sc,
        'total_sc': total_sc
    })

def role(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    role, total_role = k8s_role.list_roles(path, cluster_name)

    return render(request, 'dashboard/RBAC/role.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'role': role,
        'total_role': total_role
    })

def rolebinding(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    rolebinding, total_rolebinding = k8s_rolebindings.list_rolebindings(path, cluster_name)

    return render(request, 'dashboard/RBAC/rolebinding.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'rolebinding': rolebinding,
        'total_rolebinding': total_rolebinding
    })

def clusterrole(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    clusterrole, total_clusterrole = k8s_cluster_roles.get_cluster_role(path, cluster_name)

    return render(request, 'dashboard/RBAC/clusterrole.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'clusterrole': clusterrole,
        'total_clusterrole': total_clusterrole
    })

def clusterrolebinding(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    clusterrolebinding, total_clusterrolebinding = k8s_cluster_role_bindings.get_cluster_role_bindings(path, cluster_name)

    return render(request, 'dashboard/RBAC/clusterrolebinding.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'clusterrolebinding': clusterrolebinding,
        'total_clusterrolebinding': total_clusterrolebinding
    })

def serviceAccount(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    serviceAccount, total_serviceAccount = k8s_service_accounts.get_service_accounts(path, cluster_name)

    return render(request, 'dashboard/RBAC/serviceAccount.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'serviceAccount': serviceAccount,
        'total_serviceAccount': total_serviceAccount
    })