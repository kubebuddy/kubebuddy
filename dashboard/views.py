from django.shortcuts import render

from .src.cluster_management import k8s_namespaces, k8s_nodes, k8s_limit_range, k8s_resource_quota, k8s_pdb

from .src.services import k8s_endpoints, k8s_services

from .src.events import k8s_events

from .src.networking import k8s_np, k8s_ingress

from .src.config_secrets import k8s_configmaps, k8s_secrets
from .src.workloads import k8s_cronjobs, k8s_daemonset, k8s_deployments, k8s_jobs, k8s_pods, k8s_replicaset, k8s_statefulset
from .src.persistent_volume import k8s_pv, k8s_pvc, k8s_storage_class
from .src.rbac import k8s_role, k8s_cluster_role_bindings, k8s_cluster_roles, k8s_rolebindings, k8s_service_accounts
from .src.metrics import k8s_pod_metrics, k8s_node_metrics
from main.models import KubeConfig, Cluster
from .src import k8s_cluster_metric, certificates
from django.contrib.auth.decorators import login_required
from kubebuddy.appLogs import logger
from kubernetes import config, client
from dashboard.src import clusters_DB
from .decorators import server_down_handler


def get_utils_data(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()
    # get namespaces
    namespaces = k8s_namespaces.get_namespace(path, current_cluster.context_name)
    
    context_name = current_cluster.context_name

    return cluster_id, current_cluster, path, registered_clusters, namespaces, context_name

@server_down_handler
@login_required
def dashboard(request, cluster_name):
    namespace = request.GET.get("namespace")
    if namespace == None:
        namespace="all"
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    context_name = current_cluster.context_name
    path = current_cluster.kube_config.path
    logger.info(f"kube config file path  : {path}")

    config.load_kube_config(config_file=path, context = context_name)  # Load the kube config

    # get cluster name
    current_cluster = current_cluster.cluster_name
    
    namespaces = k8s_namespaces.get_namespace(path, context_name)
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
    ready_nodes, not_ready_nodes, node_count = k8s_nodes.getNodesStatus(path, context_name)

    # getting list of nodes
    node_list, node_count = k8s_nodes.getnodes(path, context_name)

    # get pods status
    status_count = k8s_pods.getPodsStatus(path,context_name, namespace)

    # get list of pods
    pod_list, pode_count = k8s_pods.getpods(path, context_name, namespace)

    # get deployment count
    deployments_status = k8s_deployments.getDeploymentsStatus(path, context_name, namespace)

    # get daemonset count
    daemonset_status = k8s_daemonset.getDaemonsetStatus(path, context_name, namespace)

    # get replicaset count
    replicaset_status = k8s_replicaset.getReplicasetStatus(path, context_name, namespace)

    # get statefulset count
    statefulset_status = k8s_statefulset.getStatefulsetStatus(path, context_name, namespace)

    # get jobs count
    jobs_status = k8s_jobs.getJobsStatus(path, context_name, namespace)

    # get cronjobs count
    cronjob_status = k8s_cronjobs.getCronJobsStatus(path, context_name, namespace)

    # get cluster metrics 
    metrics = k8s_cluster_metric.getMetrics(path, context_name)

    # get cluster events
    events = k8s_events.get_events(path, context_name, True, namespace)

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
                                                        'selected_namespace': namespace,
                                                        'namespaces_count': namespaces_count,
                                                        'cluster_id': cluster_id,
                                                        'metrics' : metrics,
                                                        'registered_clusters': registered_clusters,
                                                        'events': events,
                                                        'context_name': context_name})
    
def pods(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    context_name = current_cluster.context_name

    logger.info(f"kube config file path  : {path}")
    
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    # get namespaces
    namespaces = k8s_namespaces.get_namespace(path, context_name)
    
    pods, pc = k8s_pods.getpods(path, context_name)
    pod_info_list = k8s_pods.get_pod_info(path, current_cluster.context_name)

    # get pods status
    status_count = k8s_pods.getPodsStatus(path,current_cluster.context_name)

    logger.info(f"pods : {pods}")
    return render(request, 'dashboard/workloads/pods.html', { "pods": pods, 
                                                   "pc": pc, 
                                                   "cluster_id": cluster_id,
                                                   "current_cluster": cluster_name,
                                                   "pod_info_list": pod_info_list,
                                                   "status_count": status_count,
                                                   'registered_clusters': registered_clusters,
                                                   'namespaces': namespaces})


def pod_info(request, cluster_name, namespace, pod_name):

    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    pod_info = {
        "describe": k8s_pods.get_pod_description(path, context_name, namespace, pod_name),
        "logs": k8s_pods.get_pod_logs(path, context_name, namespace, pod_name),
        "events": k8s_pods.get_pod_events(path, context_name, namespace, pod_name) or "< None >",
        "yaml": k8s_pods.get_pod_yaml(path, context_name, namespace, pod_name)
    }

    return render(request, 'dashboard/workloads/pod_info.html', {
        "pod_info": pod_info,
        "cluster_id": cluster_id,
        "pod_name": pod_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters
    })


def replicasets(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    rs_status = k8s_replicaset.getReplicasetStatus(path, context_name)
    replicaset_info_list = k8s_replicaset.getReplicaSetsInfo(path, context_name)
    
    return render(request, 'dashboard/workloads/replicasets.html', {"cluster_id": cluster_id, 
                                                          "replicaset_info_list": replicaset_info_list,
                                                          "rs_status": rs_status,
                                                          'current_cluster': cluster_name,
                                                          'registered_clusters': registered_clusters,
                                                          'namespaces': namespaces})

def rs_info(request, cluster_name, namespace, rs_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)
    
    rs_info = {
        "describe": k8s_replicaset.get_replicaset_description(path, context_name, namespace, rs_name),
        "events": k8s_replicaset.get_replicaset_events(path, context_name, namespace, rs_name),
        "yaml": k8s_replicaset.get_yaml_rs(path, context_name, namespace, rs_name)
    }

    return render(request, 'dashboard/workloads/rs_info.html', {
        "rs_info": rs_info,
        "cluster_id": cluster_id,
        "rs_name": rs_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters
    })

def deployments(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    dep_status = k8s_deployments.getDeploymentsStatus(path, context_name)
    deployment_info_list = k8s_deployments.getDeploymentsInfo(path, context_name)
    return render(request, 'dashboard/workloads/deployment.html', {"cluster_id": cluster_id, 
                                                         "dep_status": dep_status,
                                                         "deployment_info_list": deployment_info_list,
                                                         'current_cluster': cluster_name,
                                                         'registered_clusters': registered_clusters,
                                                         'namespaces': namespaces})

def deploy_info(request, cluster_name, namespace, deploy_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    deploy_info = {
        "describe": k8s_deployments.get_deployment_description(path, context_name, namespace, deploy_name),
        "events": k8s_deployments.get_deploy_events(path, context_name, namespace, deploy_name),
        "yaml": k8s_deployments.get_yaml_deploy(path, context_name, namespace, deploy_name)
    }

    return render(request, 'dashboard/workloads/deploy_info.html', {
        "deploy_info": deploy_info,
        "cluster_id": cluster_id,
        "deploy_name": deploy_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters
    })

def events(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    events = k8s_events.get_events(path, context_name, False)
    return render(request, 'dashboard/events.html', {"cluster_id": cluster_id, 
                                                     'events': events,
                                                     'current_cluster': cluster_name,
                                                     'registered_clusters': registered_clusters,
                                                     'namespaces': namespaces})


def statefulsets(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    statefulsets_status = k8s_statefulset.getStatefulsetStatus(path, context_name)
    statefulsets_list = k8s_statefulset.getStatefulsetList(path, context_name)


    return render(request, 'dashboard/workloads/statefulsets.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'statefulsets_list': statefulsets_list,
        'statefulsets_status': statefulsets_status,
        'registered_clusters': registered_clusters,
        'namespaces': namespaces
    })

def sts_info(request, cluster_name, namespace, sts_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    sts_info = {
        "describe": k8s_statefulset.get_statefulset_description(path, context_name, namespace, sts_name),
        "events": k8s_statefulset.get_sts_events(path, context_name, namespace, sts_name),
        "yaml": k8s_statefulset.get_yaml_sts(path, context_name, namespace, sts_name)
    }

    return render(request, 'dashboard/workloads/sts_info.html', {
        "sts_info": sts_info,
        "cluster_id": cluster_id,
        "sts_name": sts_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters
    })

def daemonset(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    daemonset_status = k8s_daemonset.getDaemonsetStatus(path, context_name)
    daemonset_list = k8s_daemonset.getDaemonsetList(path, context_name)

    return render(request, 'dashboard/workloads/daemonset.html',{
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'daemonset_status': daemonset_status,
        'daemonset_list': daemonset_list,
        'registered_clusters': registered_clusters,
        'namespaces': namespaces
    })

def daemonset_info(request, cluster_name, namespace, daemonset_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    daemonset_info = {
        "describe": k8s_daemonset.get_daemonset_description(path, context_name, namespace, daemonset_name),
        "events": k8s_daemonset.get_daemonset_events(path, context_name, namespace, daemonset_name),
        "yaml": k8s_daemonset.get_daemonset_yaml(path, context_name, namespace, daemonset_name),
    }

    return render(request, 'dashboard/workloads/daemonset_info.html', {
        "daemonset_info": daemonset_info,
        "cluster_id": cluster_id,
        "daemonset_name": daemonset_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters
    })


def jobs(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    jobs_status = k8s_jobs.getJobsStatus(path, context_name)
    jobs_list = k8s_jobs.getJobsList(path, context_name)

    return render(request, 'dashboard/workloads/jobs.html',{
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'jobs_status': jobs_status,
        'jobs_list': jobs_list,
        'registered_clusters': registered_clusters,
        'namespaces': namespaces
    })

def jobs_info(request, cluster_name, namespace, job_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    job_info = {
        "describe": k8s_jobs.get_job_description(path, context_name, namespace, job_name),
        "events": k8s_jobs.get_job_events(path, context_name, namespace, job_name),
        "yaml": k8s_jobs.get_yaml_job(path, context_name, namespace, job_name)
    }
    return render(request, 'dashboard/workloads/job_info.html', {
        "job_info": job_info,
        "cluster_id": cluster_id,
        "job_name": job_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters
    })



def cronjobs(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    cronjobs_status = k8s_cronjobs.getCronJobsStatus(path, context_name)
    cronjobs_list = k8s_cronjobs.getCronJobsList(path, context_name)

    return render(request, 'dashboard/workloads/cronjobs.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'cronjobs_status': cronjobs_status,
        'cronjobs_list': cronjobs_list,
        'namespaces': namespaces
    })

def cronjob_info(request, cluster_name, namespace, cronjob_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    cronjob_info = {
        "describe": k8s_cronjobs.get_cronjob_description(path, context_name, namespace, cronjob_name),
        "events": k8s_cronjobs.get_cronjob_events(path, context_name, namespace, cronjob_name),
        "yaml": k8s_cronjobs.get_yaml_cronjob(path, context_name, namespace, cronjob_name)
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
    namespaces = k8s_namespaces.namespaces_data(path, current_cluster.context_name)
    namespaces_count = len(namespaces)

    return render(request, 'dashboard/cluster_management/namespace.html',{
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'namespaces': namespaces,
        'namespaces_count': namespaces_count
    })

def ns_info(request, cluster_name, namespace):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    ns_info = {
        "describe": k8s_namespaces.get_namespace_description(path, context_name, namespace),
        "yaml": k8s_namespaces.get_namespace_yaml(path, context_name, namespace),
    }

    return render(request, 'dashboard/cluster_management/ns_info.html', {
        "ns_info": ns_info,
        "cluster_id": cluster_id,
        "namespace": namespace,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })

def configmaps(request,cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    configmaps, total_count = k8s_configmaps.get_configmaps(path, context_name)
    return render(request, 'dashboard/config_secrets/configmaps.html', {"configmaps": configmaps, 'total_count':total_count, "cluster_id": cluster_id, 'current_cluster': cluster_name, 'registered_clusters': registered_clusters, 'namespaces': namespaces})

def configmap_info(request, cluster_name, namespace, configmap_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    configmap_info = {
        "describe": k8s_configmaps.get_configmap_description(path, context_name, namespace, configmap_name),
        "events": k8s_configmaps.get_configmap_events(path, context_name, namespace, configmap_name),
        "yaml": k8s_configmaps.get_configmap_yaml(path, context_name, namespace, configmap_name),
    }

    return render(request, 'dashboard/config_secrets/configmap_info.html', {
        "configmap_info": configmap_info,
        "cluster_id": cluster_id,
        "configmap_name": configmap_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })


def secrets(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    namespaces = k8s_namespaces.get_namespace(path, context_name)
    secrets, total_secrets = k8s_secrets.list_secrets(path, context_name)
    return render(request, 'dashboard/config_secrets/secrets.html', {"secrets": secrets, "total_secrets": total_secrets, "cluster_id": cluster_id, 'current_cluster': cluster_name, 'registered_clusters': registered_clusters, 'namespaces': namespaces})


def secret_info(request, cluster_name, namespace, secret_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    secret_info = {
        "describe": k8s_secrets.get_secret_description(path, context_name, namespace, secret_name),
        "events": k8s_secrets.get_secret_events(path, context_name, namespace, secret_name),
        "yaml": k8s_secrets.get_secret_yaml(path, context_name, namespace, secret_name),
    }

    return render(request, 'dashboard/config_secrets/secret_info.html', {
        "secret_info": secret_info,
        "cluster_id": cluster_id,
        "secret_name": secret_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })


def services(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    services = k8s_services.list_kubernetes_services(path, context_name)
    total_services = len(services)
    return render(request, 'dashboard/services/services.html', {"services": services,"total_services": total_services, "cluster_id": cluster_id, 'current_cluster': cluster_name, 'registered_clusters': registered_clusters, 'namespaces': namespaces})

def service_info(request, cluster_name, namespace, service_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    service_info = {
        "describe": k8s_services.get_service_description(path, context_name, namespace, service_name),
        "events": k8s_services.get_service_events(path, context_name, namespace, service_name),
        "yaml": k8s_services.get_service_yaml(path, context_name, namespace, service_name),
    }

    return render(request, 'dashboard/services/service_info.html', {
        "service_info": service_info,
        "cluster_id": cluster_id,
        "service_name": service_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })


def endpoints(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)
    
    endpoints = k8s_endpoints.get_endpoints(path, context_name)
    total_endpoints = len(endpoints)
    return render(request, 'dashboard/services/endpoints.html', {"endpoints": endpoints,"total_endpoints":total_endpoints, "cluster_id": cluster_id, 'current_cluster': cluster_name, 'registered_clusters': registered_clusters, 'namespaces': namespaces}) 

def endpoint_info(request, cluster_name, namespace, endpoint_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    endpoint_info = {
        "describe": k8s_endpoints.get_endpoint_description(path, context_name, namespace, endpoint_name),
        "events": k8s_endpoints.get_endpoint_events(path, context_name, namespace, endpoint_name),
        "yaml": k8s_endpoints.get_endpoint_yaml(path, context_name, namespace, endpoint_name),
    }

    return render(request, 'dashboard/services/endpoint_info.html', {
        "endpoint_info": endpoint_info,
        "cluster_id": cluster_id,
        "endpoint_name": endpoint_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })



def nodes(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    nodes = k8s_nodes.get_nodes_info(path, context_name)
    ready_nodes, not_ready_nodes, total_nodes = k8s_nodes.getNodesStatus(path, context_name)
    
    return render(request, 'dashboard/cluster_management/nodes.html', { 
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'nodes': nodes,
        'ready_nodes': ready_nodes,
        'not_ready_nodes': not_ready_nodes,
        'total_nodes': total_nodes
    })

def node_info(request, cluster_name, node_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    node_info = {
        "describe": k8s_nodes.get_node_description(path, context_name, node_name),
        "yaml": k8s_nodes.get_node_yaml(path, context_name, node_name),
    }
    return render(request, 'dashboard/cluster_management/node_info.html', {
        "node_info": node_info,
        "cluster_id": cluster_id,
        "node_name": node_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })

def limitrange(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    limitranges, total_limitranges = k8s_limit_range.get_limit_ranges(path, context_name)

    return render(request, 'dashboard/cluster_management/limitrange.html',{
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'limitranges': limitranges,
        'total_limitranges': total_limitranges,
        'namespaces': namespaces
    })


def limitrange_info(request, cluster_name, namespace, limitrange_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    limitrange_info = {
        "describe": k8s_limit_range.get_limitrange_description(path, context_name, namespace, limitrange_name),
        "events": k8s_limit_range.get_limitrange_events(path, context_name, namespace, limitrange_name),
        "yaml": k8s_limit_range.get_limitrange_yaml(path, context_name, namespace, limitrange_name),
    }

    return render(request, 'dashboard/cluster_management/limitrange_info.html', { 
        "limitrange_info": limitrange_info,
        "cluster_id": cluster_id,
        "limitrange_name": limitrange_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })

def resourcequotas(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    resourcequotas, total_quotas = k8s_resource_quota.get_resource_quotas(path, context_name)

    return render(request, 'dashboard/cluster_management/resourcequotas.html',{
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'resourcequotas': resourcequotas,
        'total_quotas': total_quotas,
        'namespaces': namespaces
    })


def resourcequota_info(request, cluster_name, namespace, resourcequota_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    resourcequota_info = {
        "describe": k8s_resource_quota.get_resourcequota_description(path, context_name, namespace, resourcequota_name),
        "events": k8s_resource_quota.get_resourcequota_events(path, context_name, namespace, resourcequota_name),
        "yaml": k8s_resource_quota.get_resourcequota_yaml(path, context_name, namespace, resourcequota_name),
    }

    return render(request, 'dashboard/cluster_management/resourcequota_info.html', {
        "resourcequota_info": resourcequota_info,
        "cluster_id": cluster_id,
        "resourcequota_name": resourcequota_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })

def pdb(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    pdbs, pdbs_count = k8s_pdb.get_pdb(path, context_name)

    return render(request, 'dashboard/cluster_management/pdb.html', {
        "cluster_id": cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'pdbs': pdbs,
        "namespaces": namespaces,
        "pdbs_count": pdbs_count
    })

def pdb_info(request, cluster_name, namespace, pdb_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    pdb_info = {
        "describe": k8s_pdb.get_pdb_description(path, context_name, namespace, pdb_name),
        "events": k8s_pdb.get_pdb_events(path, context_name, namespace, pdb_name),
        "yaml": k8s_pdb.get_pdb_yaml(path, context_name, namespace, pdb_name),
    }

    return render(request, 'dashboard/cluster_management/pdb_info.html', {
        "pdb_info": pdb_info,
        "cluster_id": cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })

def persistentvolume(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    pvs, total_pvs = k8s_pv.list_persistent_volumes(path, context_name)

    return render(request, 'dashboard/persistent_storage/persistentvolume.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'pvs': pvs,
        'total_pvs': total_pvs
    })

def pv_info(request, cluster_name, pv_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    pv_info = {
        "describe": k8s_pv.get_pv_description(path, context_name, pv_name),
        "yaml": k8s_pv.get_pv_yaml(path, context_name, pv_name),
    }

    return render(request, 'dashboard/persistent_storage/pv_info.html', {
        "pv_info": pv_info,
        "cluster_id": cluster_id,
        "pv_name": pv_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })


def persistentvolumeclaim(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    pvc, total_pvc = k8s_pvc.list_pvc(path, context_name)

    return render(request, 'dashboard/persistent_storage/persistentvolumeclaim.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'pvc': pvc,
        'total_pvc': total_pvc,
        'namespaces': namespaces
    })

def pvc_info(request, cluster_name, namespace, pvc_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    pvc_info = {
        "describe": k8s_pvc.get_pvc_description(path, context_name, namespace, pvc_name),
        "events": k8s_pvc.get_pvc_events(path, context_name, namespace, pvc_name),
        "yaml": k8s_pvc.get_pvc_yaml(path, context_name, namespace, pvc_name),
    }

    return render(request, 'dashboard/persistent_storage/pvc_info.html', {
        "pvc_info": pvc_info,
        "cluster_id": cluster_id,
        "pvc_name": pvc_name,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })


def storageclass(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    sc, total_sc = k8s_storage_class.list_storage_classes(path, context_name)

    return render(request, 'dashboard/persistent_storage/storageclass.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'sc': sc,
        'total_sc': total_sc
    })

def storageclass_info(request, cluster_name, sc_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    sc_info = {
        "describe": k8s_storage_class.get_storage_class_description(path, context_name, sc_name),
        "events": k8s_storage_class.get_storage_class_events(path, context_name, sc_name),
        "yaml": k8s_storage_class.get_sc_yaml(path, context_name, sc_name)
    }    

    return render(request, 'dashboard/persistent_storage/storageclass_info.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'sc_info': sc_info,
    })

# Networking

def np(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()
    # get namespaces
    namespaces = k8s_namespaces.get_namespace(path, current_cluster.context_name)
    
    nps, nps_count = k8s_np.get_np(path, current_cluster.context_name)

    return render(request, 'dashboard/networking/np.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'nps': nps,
        'nps_count': nps_count,
        'namespaces': namespaces
    })


def np_info(request, cluster_name, namespace, np_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    np_info = {
        "describe": k8s_np.get_np_description(path, current_cluster.context_name, namespace, np_name),
        "events": k8s_np.get_np_events(path, current_cluster.context_name, namespace, np_name),
        "yaml": k8s_np.get_np_yaml(path, current_cluster.context_name, namespace, np_name)
    }    

    return render(request, 'dashboard/networking/np_info.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'np_info': np_info,
    })

def ingress(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()    
    # get namespaces
    namespaces = k8s_namespaces.get_namespace(path, current_cluster.context_name)
    
    ingress, ingress_count = k8s_ingress.get_ingress(path, current_cluster.context_name)

    return render(request, 'dashboard/networking/ingress.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'ingress': ingress,
        'ingress_count': ingress_count,
        'namespaces': namespaces
    })

def ingress_info(request, cluster_name, namespace, ingress_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()

    ingress_info = {
        "describe": k8s_ingress.get_ingress_description(path, current_cluster.context_name, namespace, ingress_name),
        "events": k8s_ingress.get_ingress_events(path, current_cluster.context_name, namespace, ingress_name),
        "yaml": k8s_ingress.get_ingress_yaml(path, current_cluster.context_name, namespace, ingress_name)
    }    

    return render(request, 'dashboard/networking/ingress_info.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'ingress_info': ingress_info,
    })

def role(request, cluster_name):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path
    # get clusters in DB
    registered_clusters = clusters_DB.get_registered_clusters()
    # get namespaces
    namespaces = k8s_namespaces.get_namespace(path, current_cluster.context_name)

    role, total_role = k8s_role.list_roles(path, current_cluster.context_name)

    return render(request, 'dashboard/RBAC/role.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'role': role,
        'total_role': total_role,
        'namespaces': namespaces
    })

def role_info(request, cluster_name, namespace, role_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    role_info = {
        "describe": k8s_role.get_role_description(path, context_name, namespace, role_name),
        "events": k8s_role.get_role_events(path, context_name, namespace, role_name),
        "yaml": k8s_role.get_role_yaml(path, context_name, namespace, role_name)
    }

    return render(request, 'dashboard/RBAC/role_info.html', {
        "role_info": role_info,
        "cluster_id": cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })

def rolebinding(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    rolebinding, total_rolebinding = k8s_rolebindings.list_rolebindings(path, context_name)

    return render(request, 'dashboard/RBAC/rolebinding.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'rolebinding': rolebinding,
        'total_rolebinding': total_rolebinding,
        'namespaces': namespaces
    })

def role_binding_info(request, cluster_name, namespace, role_binding_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    role_binding_info = {
        "describe": k8s_rolebindings.get_role_binding_description(path, context_name, namespace, role_binding_name),
        "events": k8s_rolebindings.get_role_binding_events(path, context_name, namespace, role_binding_name),
        "yaml": k8s_rolebindings.get_role_binding_yaml(path, context_name, namespace, role_binding_name),
    }

    return render(request, 'dashboard/RBAC/rolebinding_info.html', {
        "role_binding_info": role_binding_info,
        "cluster_id": cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })

def clusterrole(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    clusterrole, total_clusterrole = k8s_cluster_roles.get_cluster_role(path, context_name)

    return render(request, 'dashboard/RBAC/clusterrole.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'clusterrole': clusterrole,
        'total_clusterrole': total_clusterrole
    })

def clusterrole_info(request, cluster_name, cluster_role_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    cluster_role_info = {
        "describe": k8s_cluster_roles.get_cluster_role_description(path, context_name, cluster_role_name),
        "events": k8s_cluster_roles.get_cluster_role_events(path, context_name, cluster_role_name),
        "yaml": k8s_cluster_roles.get_cluster_role_yaml(path, context_name, cluster_role_name)
    }

    return render(request, 'dashboard/RBAC/clusterrole_info.html', {
        "cluster_role_info": cluster_role_info,
        "cluster_id": cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })

def clusterrolebinding(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    clusterrolebinding, total_clusterrolebinding = k8s_cluster_role_bindings.get_cluster_role_bindings(path, context_name)

    return render(request, 'dashboard/RBAC/clusterrolebinding.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'clusterrolebinding': clusterrolebinding,
        'total_clusterrolebinding': total_clusterrolebinding
    })

def cluster_role_binding_info(request, cluster_name, cluster_role_binding_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    cluster_role_binding_info = {
        "describe": k8s_cluster_role_bindings.get_cluster_role_binding_description(path, context_name, cluster_role_binding_name),
        "events": k8s_cluster_role_bindings.get_cluster_role_binding_events(path, context_name, cluster_role_binding_name),
        "yaml": k8s_cluster_role_bindings.get_cluster_role_binding_yaml(path, context_name, cluster_role_binding_name),
    }

    return render(request, 'dashboard/RBAC/clusterrolebinding_info.html', {
        "cluster_role_binding_info": cluster_role_binding_info,
        "cluster_id": cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
    })

def serviceAccount(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    serviceAccount, total_serviceAccount = k8s_service_accounts.get_service_accounts(path, context_name)

    return render(request, 'dashboard/RBAC/serviceAccount.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'serviceAccount': serviceAccount,
        'total_serviceAccount': total_serviceAccount,
        'namespaces': namespaces
    })

def serviceAccountInfo(request, cluster_name, namespace, sa_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    serviceAccountInfo = {
        "describe": k8s_service_accounts.get_sa_description(path, context_name, namespace, sa_name),
        "events": k8s_service_accounts.get_sa_events(path, context_name, namespace, sa_name),
        "yaml": k8s_service_accounts.get_sa_yaml(path, context_name, namespace, sa_name),
    }

    return render(request, 'dashboard/RBAC/serviceAccountInfo.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'serviceAccountInfo': serviceAccountInfo,
    })


def pod_metrics(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    result = k8s_pod_metrics.get_pod_metrics(path, context_name)
    
    # Check if result is a tuple with 3 elements (indicating new format)
    if isinstance(result, tuple) and len(result) == 3:
        all_pod_metrics, total_pods, metrics_available = result
    else:
        # Fallback for older format or error case
        all_pod_metrics, total_pods = result
        metrics_available = not isinstance(all_pod_metrics, dict) or 'error' not in all_pod_metrics
    
    error_message = None
    if isinstance(all_pod_metrics, dict) and 'error' in all_pod_metrics:
        error_message = all_pod_metrics['error']
        metrics_available = False

    return render(request, 'dashboard/metrics/pod_metrics.html', {
        'all_pod_metrics': all_pod_metrics if metrics_available else [],
        'total_pods': total_pods,
        'metrics_available': metrics_available,
        'error_message': error_message,
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'namespaces': namespaces,
    })


def node_metrics(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)
    
    result = k8s_node_metrics.get_node_metrics(path, context_name)
    
    # Check if result is a tuple with 3 elements (indicating new format)
    if isinstance(result, tuple) and len(result) == 3:
        node_metrics, total_nodes, metrics_available = result
    else:
        # Fallback for older format or error case
        node_metrics, total_nodes = result
        metrics_available = not isinstance(node_metrics, dict) or 'error' not in node_metrics
    
    error_message = None
    if isinstance(node_metrics, dict) and 'error' in node_metrics:
        error_message = node_metrics['error']
        metrics_available = False
    
    return render(request, 'dashboard/metrics/node_metrics.html', {
        'node_metrics': node_metrics if metrics_available else [],
        'total_nodes': total_nodes,
        'metrics_available': metrics_available,
        'error_message': error_message,
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'namespaces': namespaces,
    })


def k8sCertificates(request, cluster_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request, cluster_name)

    k8s_certificates = certificates.get_certificate_details(path, context_name)

    return render(request, 'dashboard/certificates.html', {
        'cluster_id': cluster_id,
        'current_cluster': cluster_name,
        'registered_clusters': registered_clusters,
        'certificate': k8s_certificates,
        'namespaces': namespaces
    })