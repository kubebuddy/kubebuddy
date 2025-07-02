import subprocess, os

from django.shortcuts import render
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseServerError, HttpResponse, FileResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import redirect

from .src.cluster_management import k8s_namespaces, k8s_nodes, k8s_limit_range, k8s_resource_quota, k8s_pdb
from .src.services import k8s_endpoints, k8s_services
from .src.events import k8s_events
from .src.networking import k8s_np, k8s_ingress
from .src.config_secrets import k8s_configmaps, k8s_secrets
from .src.workloads import k8s_cronjobs, k8s_daemonset, k8s_deployments, k8s_jobs, k8s_pods, k8s_replicaset, k8s_statefulset
from .src.persistent_volume import k8s_pv, k8s_pvc, k8s_storage_class
from .src.rbac import k8s_role, k8s_cluster_role_bindings, k8s_cluster_roles, k8s_rolebindings, k8s_service_accounts
from .src.metrics import k8s_pod_metrics, k8s_node_metrics
from .src import dashData, clusters_DB, k8sgpt
from .src.cluster_hotspot import get_cluster_hotspot

from main.models import Cluster
from kubebuddy.appLogs import logger
from kubernetes import config, client
from .decorators import server_down_handler
from .src.workloads.k8s_pods import get_pod_details
from .src.workloads.k8s_deployments import get_deployment_details
from .src.cluster_management.k8s_nodes import get_node_details
from .src.cluster_management.k8s_namespaces import get_namespace_details
from .src.services.k8s_endpoints import get_endpoint_details
from .src.services.k8s_services import get_service_details
from .src.networking.k8s_ingress import get_ingress_details
from kubernetes.config.config_exception import ConfigException
from django.template.loader import get_template
from .src.generate_pdf import generate_pdf
from .src import kube_bench
from .src.utils import validate_and_patch_resource
###### Utilities ######

def get_utils_data(request):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    
    path = current_cluster.kube_config.path
    registered_clusters = clusters_DB.get_cluster_names()
    namespaces = k8s_namespaces.get_namespace(path, current_cluster.context_name)
    context_name = current_cluster.context_name
    return cluster_id, current_cluster, path, registered_clusters, namespaces, context_name
    
############ DASHBOARD ############

@server_down_handler
@login_required
def dashboard(request, cluster_id):
    namespace = request.GET.get("namespace", "all")
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    config.load_kube_config(config_file=path, context=context_name)
    namespaces_count = len(namespaces)
    warning_message = (
        "Warning: You're using the default username & password. Please change it for security reasons."
        if request.user.username == "admin" and request.user.check_password("admin")
        else None
    )
    context = dashData.fetch_dashboard_data(path, context_name, namespace, current_cluster, namespaces, namespaces_count, cluster_id, registered_clusters, warning_message)
    return render(request, 'dashboard/dashboard.html', context)

############ WORKLOAD SECTION ############

def pods(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    pods, pc = k8s_pods.getpods(path, context_name)
    pod_info_list = k8s_pods.get_pod_info(path, current_cluster.context_name)
    status_count = k8s_pods.getPodsStatus(path, current_cluster.context_name)
    return render(request, 'dashboard/workloads/pods.html', { "pods": pods, "pc": pc,
                                                   "cluster_id": cluster_id,
                                                   "pod_info_list": pod_info_list, "status_count": status_count,
                                                   "registered_clusters": registered_clusters, "namespaces": namespaces, 'current_cluster': current_cluster})


def pod_info(request, cluster_id, namespace, pod_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    pod_info = {
        "describe": k8s_pods.get_pod_description(path, context_name, namespace, pod_name),
        "logs": k8s_pods.get_pod_logs(path, context_name, namespace, pod_name),
        "events": k8s_pods.get_pod_events(path, context_name, namespace, pod_name) or "< None >",
        "yaml": k8s_pods.get_pod_yaml(path, context_name, namespace, pod_name, managed_fields=True),
        "edit": k8s_pods.get_pod_yaml(path, context_name, namespace, pod_name, managed_fields=False),
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, pod_name, namespace, pod_info["yaml"], yaml)

        if ret["success"] == False:
            pod_info["show_modal"] = True
            pod_info["message"] = ret["message"]
        else:
            pod_info["show_modal"] = True
            pod_info["changes"] = ret["changes"]
            pod_info["message"] = ret["message"]
            
        new_yaml = k8s_pods.get_pod_yaml(path, context_name, namespace, pod_name, managed_fields=True)
        new_edit = k8s_pods.get_pod_yaml(path, context_name, namespace, pod_name, managed_fields=False)
        pod_info["yaml"] = new_yaml
        pod_info["edit"] = new_edit

    return render(request, 'dashboard/workloads/pod_info.html', {"pod_info": pod_info, "cluster_id": cluster_id,
                                                        "pod_name": pod_name,
                                                        "registered_clusters": registered_clusters, 'current_cluster': current_cluster})


def replicasets(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    rs_status = k8s_replicaset.getReplicasetStatus(path, context_name)
    replicaset_info_list = k8s_replicaset.getReplicaSetsInfo(path, context_name)
    return render(request, 'dashboard/workloads/replicasets.html', {"cluster_id": cluster_id, "replicaset_info_list": replicaset_info_list,
                                                          "rs_status": rs_status,
                                                          "registered_clusters": registered_clusters, "namespaces": namespaces, 'current_cluster': current_cluster})


def rs_info(request, cluster_id, namespace, rs_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    rs_info = {
        "describe": k8s_replicaset.get_replicaset_description(path, context_name, namespace, rs_name),
        "events": k8s_replicaset.get_replicaset_events(path, context_name, namespace, rs_name),
        "yaml": k8s_replicaset.get_yaml_rs(path, context_name, namespace, rs_name, managed_fields=True),
        "edit": k8s_replicaset.get_yaml_rs(path, context_name, namespace, rs_name, managed_fields=False),
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, rs_name, namespace, rs_info["yaml"], yaml)

        if ret["success"] == False:
            rs_info["show_modal"] = True
            rs_info["message"] = ret["message"]
        else:
            rs_info["show_modal"] = True
            rs_info["changes"] = ret["changes"]
            rs_info["message"] = ret["message"]
            
        new_yaml = k8s_replicaset.get_yaml_rs(path, context_name, namespace, rs_name, managed_fields=True)
        new_edit = k8s_replicaset.get_yaml_rs(path, context_name, namespace, rs_name, managed_fields=False)
        rs_info["yaml"] = new_yaml
        rs_info["edit"] = new_edit

    return render(request, 'dashboard/workloads/rs_info.html', {"rs_info": rs_info, "cluster_id": cluster_id, "rs_name": rs_name, 
                                                                "registered_clusters": registered_clusters, 'current_cluster': current_cluster})


def deployments(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    dep_status = k8s_deployments.getDeploymentsStatus(path, context_name)
    deployment_info_list = k8s_deployments.getDeploymentsInfo(path, context_name)
    return render(request, 'dashboard/workloads/deployment.html', {"cluster_id": cluster_id, "dep_status": dep_status, "deployment_info_list": deployment_info_list,
                                                                "registered_clusters": registered_clusters, "namespaces": namespaces, 'current_cluster': current_cluster})


def deploy_info(request, cluster_id, namespace, deploy_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    deploy_info = {
        "describe": k8s_deployments.get_deployment_description(path, context_name, namespace, deploy_name),
        "events": k8s_deployments.get_deploy_events(path, context_name, namespace, deploy_name),
        "yaml": k8s_deployments.get_yaml_deploy(path, context_name, namespace, deploy_name, managed_fields=True),
        "edit": k8s_deployments.get_yaml_deploy(path, context_name, namespace, deploy_name, managed_fields=False),
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, deploy_name, namespace, deploy_info["yaml"], yaml)

        if ret["success"] == False:
            deploy_info["show_modal"] = True
            deploy_info["message"] = ret["message"]
        else:
            deploy_info["show_modal"] = True
            deploy_info["changes"] = ret["changes"]
            deploy_info["message"] = ret["message"]
            
        new_yaml = k8s_deployments.get_yaml_deploy(path, context_name, namespace, deploy_name, managed_fields=True)
        new_edit = k8s_deployments.get_yaml_deploy(path, context_name, namespace, deploy_name, managed_fields=False)
        deploy_info["yaml"] = new_yaml
        deploy_info["edit"] = new_edit

    return render(request, 'dashboard/workloads/deploy_info.html', {"deploy_info": deploy_info, "cluster_id": cluster_id, "deploy_name": deploy_name, 
                                                                    "registered_clusters": registered_clusters, 'current_cluster': current_cluster})


def statefulsets(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    statefulsets_status = k8s_statefulset.getStatefulsetStatus(path, context_name)
    statefulsets_list = k8s_statefulset.getStatefulsetList(path, context_name)

    return render(request, 'dashboard/workloads/statefulsets.html', {'cluster_id': cluster_id,
                                                                     'statefulsets_list': statefulsets_list, 'statefulsets_status': statefulsets_status,
                                                                     'registered_clusters': registered_clusters,'namespaces': namespaces, 'current_cluster': current_cluster})


def sts_info(request, cluster_id, namespace, sts_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    sts_info = {
        "describe": k8s_statefulset.get_statefulset_description(path, context_name, namespace, sts_name),
        "events": k8s_statefulset.get_sts_events(path, context_name, namespace, sts_name),
        "yaml": k8s_statefulset.get_yaml_sts(path, context_name, namespace, sts_name, managed_fields = True),
        "edit": k8s_statefulset.get_yaml_sts(path, context_name, namespace, sts_name, managed_fields = False)
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, sts_name, namespace, sts_info["yaml"], yaml)

        if ret["success"] == False:
            sts_info["show_modal"] = True
            sts_info["message"] = ret["message"]
        else:
            sts_info["show_modal"] = True
            sts_info["changes"] = ret["changes"]
            sts_info["message"] = ret["message"]
            
        new_yaml = k8s_statefulset.get_yaml_sts(path, context_name, namespace, sts_name, managed_fields=True)
        new_edit = k8s_statefulset.get_yaml_sts(path, context_name, namespace, sts_name, managed_fields=False)
        sts_info["yaml"] = new_yaml
        sts_info["edit"] = new_edit
    
    return render(request, 'dashboard/workloads/sts_info.html', {"sts_info": sts_info,"cluster_id": cluster_id,
                                                                 "sts_name": sts_name, 'registered_clusters': registered_clusters, 'current_cluster': current_cluster})


def daemonset(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    daemonset_status = k8s_daemonset.getDaemonsetStatus(path, context_name)
    daemonset_list = k8s_daemonset.getDaemonsetList(path, context_name)
    
    return render(request, 'dashboard/workloads/daemonset.html',{'cluster_id': cluster_id,
                                                                 'daemonset_status': daemonset_status, 'daemonset_list': daemonset_list,
                                                                 'registered_clusters': registered_clusters, 'namespaces': namespaces, 'current_cluster': current_cluster})


def daemonset_info(request, cluster_id, namespace, daemonset_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    ds_info = {
        "describe": k8s_daemonset.get_daemonset_description(path, context_name, namespace, daemonset_name),
        "events": k8s_daemonset.get_daemonset_events(path, context_name, namespace, daemonset_name),
        "yaml": k8s_daemonset.get_daemonset_yaml(path, context_name, namespace, daemonset_name, managed_fields = True),
        "edit": k8s_daemonset.get_daemonset_yaml(path, context_name, namespace, daemonset_name, managed_fields = False)
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, daemonset_name, namespace, ds_info["yaml"], yaml)

        if ret["success"] == False:
            ds_info["show_modal"] = True
            ds_info["message"] = ret["message"]
        else:
            ds_info["show_modal"] = True
            ds_info["changes"] = ret["changes"]
            ds_info["message"] = ret["message"]
            
        new_yaml = k8s_daemonset.get_daemonset_yaml(path, context_name, namespace, daemonset_name, managed_fields=True)
        new_edit = k8s_daemonset.get_daemonset_yaml(path, context_name, namespace, daemonset_name, managed_fields=False)
        ds_info["yaml"] = new_yaml
        ds_info["edit"] = new_edit

    return render(request, 'dashboard/workloads/daemonset_info.html', {"daemonset_info": ds_info, "cluster_id": cluster_id,
                                                                       "daemonset_name": daemonset_name, 'registered_clusters': registered_clusters, 'current_cluster': current_cluster})


def jobs(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    jobs_status = k8s_jobs.getJobsStatus(path, context_name)
    jobs_list = k8s_jobs.getJobsList(path, context_name)

    return render(request, 'dashboard/workloads/jobs.html',{'cluster_id': cluster_id, 'jobs_status': jobs_status,
                                                            'jobs_list': jobs_list, 'registered_clusters': registered_clusters, 'namespaces': namespaces, 'current_cluster': current_cluster})


def jobs_info(request, cluster_id, namespace, job_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    job_info = {
        "describe": k8s_jobs.get_job_description(path, context_name, namespace, job_name),
        "events": k8s_jobs.get_job_events(path, context_name, namespace, job_name),
        "yaml": k8s_jobs.get_yaml_job(path, context_name, namespace, job_name, managed_fields=True),
        "edit": k8s_jobs.get_yaml_job(path, context_name, namespace, job_name, managed_fields=False)
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, job_name, namespace, job_info["yaml"], yaml)

        if ret["success"] == False:
            job_info["show_modal"] = True
            job_info["message"] = ret["message"]
        else:
            job_info["show_modal"] = True
            job_info["changes"] = ret["changes"]
            job_info["message"] = ret["message"]
            
        new_yaml = k8s_jobs.get_yaml_job(path, context_name, namespace, job_name, managed_fields=True)
        new_edit = k8s_jobs.get_yaml_job(path, context_name, namespace, job_name, managed_fields=False)
        job_info["yaml"] = new_yaml
        job_info["edit"] = new_edit

    return render(request, 'dashboard/workloads/job_info.html', { "job_info": job_info, "cluster_id": cluster_id,
                                                                 "job_name": job_name, 'registered_clusters': registered_clusters, 'current_cluster': current_cluster})


def cronjobs(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    cronjobs_status = k8s_cronjobs.getCronJobsStatus(path, context_name)
    cronjobs_list = k8s_cronjobs.getCronJobsList(path, context_name)

    return render(request, 'dashboard/workloads/cronjobs.html', {'cluster_id': cluster_id,
                                                                 'registered_clusters': registered_clusters, 'cronjobs_status': cronjobs_status,
                                                                 'cronjobs_list': cronjobs_list, 'namespaces': namespaces, 'current_cluster': current_cluster})

def cronjob_info(request, cluster_id, namespace, cronjob_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    cronjob_info = {
        "describe": k8s_cronjobs.get_cronjob_description(path, context_name, namespace, cronjob_name),
        "events": k8s_cronjobs.get_cronjob_events(path, context_name, namespace, cronjob_name),
        "yaml": k8s_cronjobs.get_yaml_cronjob(path, context_name, namespace, cronjob_name, managed_fields=True),
        "edit": k8s_cronjobs.get_yaml_cronjob(path, context_name, namespace, cronjob_name, managed_fields=False)
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, cronjob_name, namespace, cronjob_info["yaml"], yaml)

        if ret["success"] == False:
            cronjob_info["show_modal"] = True
            cronjob_info["message"] = ret["message"]
        else:
            cronjob_info["show_modal"] = True
            cronjob_info["changes"] = ret["changes"]
            cronjob_info["message"] = ret["message"]
            
        new_yaml = k8s_cronjobs.get_yaml_cronjob(path, context_name, namespace, cronjob_name, managed_fields=True)
        new_edit = k8s_cronjobs.get_yaml_cronjob(path, context_name, namespace, cronjob_name, managed_fields=False)
        cronjob_info["yaml"] = new_yaml
        cronjob_info["edit"] = new_edit

    return render(request, 'dashboard/workloads/cronjob_info.html', {"cronjob_info": cronjob_info, "cluster_id": cluster_id,
                                                                     "cronjob_name": cronjob_name, 'registered_clusters': registered_clusters, 'current_cluster': current_cluster})

############ CLUSTER MANAGEMENT SECTION ############

def namespace(request, cluster_id):
    cluster_id = request.GET.get('cluster_id')
    current_cluster = Cluster.objects.get(id = cluster_id)
    path = current_cluster.kube_config.path

    registered_clusters = clusters_DB.get_cluster_names()
    namespaces = k8s_namespaces.namespaces_data(path, current_cluster.context_name)
    namespaces_count = len(namespaces)

    return render(request, 'dashboard/cluster_management/namespace.html',{'cluster_id': cluster_id,
                                                                          'registered_clusters': registered_clusters, 'namespaces': namespaces, 'namespaces_count': namespaces_count, 'current_cluster': current_cluster})


def ns_info(request, cluster_id, namespace):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    ns_info = {
        "describe": k8s_namespaces.get_namespace_description(path, context_name, namespace),
        "yaml": k8s_namespaces.get_namespace_yaml(path, context_name, namespace, managed_fields=True),
        "edit": k8s_namespaces.get_namespace_yaml(path, context_name, namespace, managed_fields=False),
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, name=namespace, old_yaml=ns_info["yaml"], new_yaml=yaml)

        if ret["success"] == False:
            ns_info["show_modal"] = True
            ns_info["message"] = ret["message"]
        else:
            ns_info["show_modal"] = True
            ns_info["changes"] = ret["changes"]
            ns_info["message"] = ret["message"]
            
        new_yaml = k8s_namespaces.get_namespace_yaml(path, context_name, namespace, managed_fields=True)
        new_edit = k8s_namespaces.get_namespace_yaml(path, context_name, namespace, managed_fields=False)
        ns_info["yaml"] = new_yaml
        ns_info["edit"] = new_edit

    return render(request, 'dashboard/cluster_management/ns_info.html', {"ns_info": ns_info, "cluster_id": cluster_id,
                                                                         "namespace": namespace, 'registered_clusters': registered_clusters, 'current_cluster': current_cluster})


def nodes(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    nodes = k8s_nodes.get_nodes_info(path, context_name)
    ready_nodes, not_ready_nodes, total_nodes = k8s_nodes.getNodesStatus(path, context_name)
    
    return render(request, 'dashboard/cluster_management/nodes.html', {'cluster_id': cluster_id, 'registered_clusters': registered_clusters, 'nodes': nodes, 
                                                                       'ready_nodes': ready_nodes, 'not_ready_nodes': not_ready_nodes, 'total_nodes': total_nodes, 'current_cluster': current_cluster})


def node_info(request, cluster_id, node_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    node_info = {
        "describe": k8s_nodes.get_node_description(path, context_name, node_name),
        "yaml": k8s_nodes.get_node_yaml(path, context_name, node_name, managed_fields=True),
        "edit": k8s_nodes.get_node_yaml(path, context_name, node_name, managed_fields=False)
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, node_name, old_yaml=node_info["yaml"], new_yaml=yaml)

        if ret["success"] == False:
            node_info["show_modal"] = True
            node_info["message"] = ret["message"]
        else:
            node_info["show_modal"] = True
            node_info["changes"] = ret["changes"]
            node_info["message"] = ret["message"]
            
        new_yaml = k8s_nodes.get_node_yaml(path, context_name, node_name, managed_fields=True)
        new_edit = k8s_nodes.get_node_yaml(path, context_name, node_name, managed_fields=False)
        node_info["yaml"] = new_yaml
        node_info["edit"] = new_edit

    return render(request, 'dashboard/cluster_management/node_info.html', {"node_info": node_info, "cluster_id": cluster_id, "node_name": node_name, 
                                                                           'registered_clusters': registered_clusters, 'current_cluster': current_cluster})


def limitrange(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    limitranges, total_limitranges = k8s_limit_range.get_limit_ranges(path, context_name)

    return render(request, 'dashboard/cluster_management/limitrange.html', {'cluster_id': cluster_id, 'registered_clusters': registered_clusters, 'limitranges': limitranges, 
                                                                            'total_limitranges': total_limitranges, 'namespaces': namespaces, 'current_cluster': current_cluster})


def limitrange_info(request, cluster_id, namespace, limitrange_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    limitrange_info = {
        "describe": k8s_limit_range.get_limit_range_description(path, context_name, namespace, limitrange_name),
        "events": k8s_limit_range.get_limitrange_events(path, context_name, namespace, limitrange_name),
        "yaml": k8s_limit_range.get_limitrange_yaml(path, context_name, namespace, limitrange_name, managed_fields=True),
        "edit": k8s_limit_range.get_limitrange_yaml(path, context_name, namespace, limitrange_name, managed_fields=False)
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, limitrange_name, namespace, old_yaml=limitrange_info["yaml"], new_yaml=yaml)

        if ret["success"] == False:
            limitrange_info["show_modal"] = True
            limitrange_info["message"] = ret["message"]
        else:
            limitrange_info["show_modal"] = True
            limitrange_info["changes"] = ret["changes"]
            limitrange_info["message"] = ret["message"]
            
        new_yaml = k8s_limit_range.get_limitrange_yaml(path, context_name, namespace, limitrange_name, managed_fields=True)
        new_edit = k8s_limit_range.get_limitrange_yaml(path, context_name, namespace, limitrange_name, managed_fields=False)
        limitrange_info["yaml"] = new_yaml
        limitrange_info["edit"] = new_edit

    return render(request, 'dashboard/cluster_management/limitrange_info.html', {"limitrange_info": limitrange_info, "cluster_id": cluster_id, "limitrange_name": limitrange_name, 
                                                                                 'registered_clusters': registered_clusters, 'current_cluster': current_cluster})


def resourcequotas(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    resourcequotas, total_quotas = k8s_resource_quota.get_resource_quotas(path, context_name)

    return render(request, 'dashboard/cluster_management/resourcequotas.html', {'cluster_id': cluster_id, 'registered_clusters': registered_clusters, 'resourcequotas': resourcequotas, 
                                                                                'total_quotas': total_quotas, 'namespaces': namespaces, 'current_cluster': current_cluster})


def resourcequota_info(request, cluster_id, namespace, resourcequota_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    resourcequota_info = {
        "describe": k8s_resource_quota.get_resourcequota_description(path, context_name, namespace, resourcequota_name),
        "events": k8s_resource_quota.get_resourcequota_events(path, context_name, namespace, resourcequota_name),
        "yaml": k8s_resource_quota.get_resourcequota_yaml(path, context_name, namespace, resourcequota_name, managed_fields=True),
        "edit": k8s_resource_quota.get_resourcequota_yaml(path, context_name, namespace, resourcequota_name, managed_fields=False)
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, resourcequota_name, namespace, old_yaml=resourcequota_info["yaml"], new_yaml=yaml)

        if ret["success"] == False:
            resourcequota_info["show_modal"] = True
            resourcequota_info["message"] = ret["message"]
        else:
            resourcequota_info["show_modal"] = True
            resourcequota_info["changes"] = ret["changes"]
            resourcequota_info["message"] = ret["message"]
            
        new_yaml = k8s_resource_quota.get_resourcequota_yaml(path, context_name, namespace, resourcequota_name, managed_fields=True)
        new_edit = k8s_resource_quota.get_resourcequota_yaml(path, context_name, namespace, resourcequota_name, managed_fields=False)
        resourcequota_info["yaml"] = new_yaml
        resourcequota_info["edit"] = new_edit

    return render(request, 'dashboard/cluster_management/resourcequota_info.html', {"resourcequota_info": resourcequota_info, "cluster_id": cluster_id, "resourcequota_name": resourcequota_name, 
                                                                                    'registered_clusters': registered_clusters, 'current_cluster': current_cluster})


def pdb(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    pdbs, pdbs_count = k8s_pdb.get_pdb(path, context_name)

    return render(request, 'dashboard/cluster_management/pdb.html', {"cluster_id": cluster_id, "registered_clusters": registered_clusters, "pdbs": pdbs, 
                                                                     "namespaces": namespaces, "pdbs_count": pdbs_count, 'current_cluster': current_cluster})


def pdb_info(request, cluster_id, namespace, pdb_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    pdb_info = {
        "describe": k8s_pdb.get_pdb_description(path, context_name, namespace, pdb_name),
        "events": k8s_pdb.get_pdb_events(path, context_name, namespace, pdb_name),
        "yaml": k8s_pdb.get_pdb_yaml(path, context_name, namespace, pdb_name, managed_fields=True),
        "edit": k8s_pdb.get_pdb_yaml(path, context_name, namespace, pdb_name, managed_fields=False),
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, pdb_name, namespace, pdb_info["yaml"], yaml)

        if ret["success"] == False:
            pdb_info["show_modal"] = True
            pdb_info["message"] = ret["message"]
        else:
            pdb_info["show_modal"] = True
            pdb_info["changes"] = ret["changes"]
            pdb_info["message"] = ret["message"]
            
        new_yaml = k8s_pdb.get_pdb_yaml(path, context_name, namespace, pdb_name, managed_fields=True)
        new_edit = k8s_pdb.get_pdb_yaml(path, context_name, namespace, pdb_name, managed_fields=False)
        pdb_info["yaml"] = new_yaml
        pdb_info["edit"] = new_edit

    return render(request, 'dashboard/cluster_management/pdb_info.html', {"pdb_info": pdb_info, "cluster_id": cluster_id, 
                                                                          "registered_clusters": registered_clusters, 'current_cluster': current_cluster})


############ CONFIGMAPS & SECRETS SECTION ############

def configmaps(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    configmaps, total_count = k8s_configmaps.get_configmaps(path, context_name)
    return render(request, 'dashboard/config_secrets/configmaps.html', {"configmaps": configmaps, 'total_count':total_count, "cluster_id": cluster_id, 
                                                                        'registered_clusters': registered_clusters, 'namespaces': namespaces, 'current_cluster': current_cluster})


def configmap_info(request, cluster_id, namespace, configmap_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    configmap_info = {
        "describe": k8s_configmaps.get_configmap_description(path, context_name, namespace, configmap_name),
        "events": k8s_configmaps.get_configmap_events(path, context_name, namespace, configmap_name),
        "yaml": k8s_configmaps.get_configmap_yaml(path, context_name, namespace, configmap_name, managed_fields=True),
        "edit": k8s_configmaps.get_configmap_yaml(path, context_name, namespace, configmap_name, managed_fields=False),
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, configmap_name, namespace, old_yaml=configmap_info["yaml"], new_yaml=yaml)

        if ret["success"] == False:
            configmap_info["show_modal"] = True
            configmap_info["message"] = ret["message"]
        else:
            configmap_info["show_modal"] = True
            configmap_info["changes"] = ret["changes"]
            configmap_info["message"] = ret["message"]
            
        new_yaml = k8s_configmaps.get_configmap_yaml(path, context_name, namespace, configmap_name, managed_fields=True)
        new_edit = k8s_configmaps.get_configmap_yaml(path, context_name, namespace, configmap_name, managed_fields=False)
        configmap_info["yaml"] = new_yaml
        configmap_info["edit"] = new_edit

    return render(request, 'dashboard/config_secrets/configmap_info.html', {"configmap_info": configmap_info, "cluster_id": cluster_id, "configmap_name": configmap_name, 
                                                                            'registered_clusters': registered_clusters, 'current_cluster': current_cluster})


def secrets(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    namespaces = k8s_namespaces.get_namespace(path, context_name)
    secrets, total_secrets = k8s_secrets.list_secrets(path, context_name)
    return render(request, 'dashboard/config_secrets/secrets.html', {"secrets": secrets, "total_secrets": total_secrets, "cluster_id": cluster_id, 
                                                                     'registered_clusters': registered_clusters, 'namespaces': namespaces, 'current_cluster': current_cluster})


def secret_info(request, cluster_id, namespace, secret_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    secret_info = {
        "describe": k8s_secrets.get_secret_description(path, context_name, namespace, secret_name),
        "events": k8s_secrets.get_secret_events(path, context_name, namespace, secret_name),
        "yaml": k8s_secrets.get_secret_yaml(path, context_name, namespace, secret_name, managed_fields=True),
        "edit": k8s_secrets.get_secret_yaml(path, context_name, namespace, secret_name, managed_fields=False),
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, secret_name, namespace, old_yaml=secret_info["yaml"], new_yaml=yaml)

        if ret["success"] == False:
            secret_info["show_modal"] = True
            secret_info["message"] = ret["message"]
        else:
            secret_info["show_modal"] = True
            secret_info["changes"] = ret["changes"]
            secret_info["message"] = ret["message"]
            
        new_yaml = k8s_secrets.get_secret_yaml(path, context_name, namespace, secret_name, managed_fields=True)
        new_edit = k8s_secrets.get_secret_yaml(path, context_name, namespace, secret_name, managed_fields=False)
        secret_info["yaml"] = new_yaml
        secret_info["edit"] = new_edit

    return render(request, 'dashboard/config_secrets/secret_info.html', {"secret_info": secret_info, "cluster_id": cluster_id, "secret_name": secret_name, 
                                                                         'registered_clusters': registered_clusters, 'current_cluster': current_cluster})


############ SERVICES SECTION ############

def services(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    services = k8s_services.list_kubernetes_services(path, context_name)
    total_services = len(services)
    return render(request, 'dashboard/services/services.html', {"services": services,"total_services": total_services, "cluster_id": cluster_id, 
                                                                'registered_clusters': registered_clusters, 'namespaces': namespaces, 'current_cluster': current_cluster})


def service_info(request, cluster_id, namespace, service_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    service_info = {
        "describe": k8s_services.get_service_description(path, context_name, namespace, service_name),
        "events": k8s_services.get_service_events(path, context_name, namespace, service_name),
        "yaml": k8s_services.get_service_yaml(path, context_name, namespace, service_name, managed_fields=True),
        "edit": k8s_services.get_service_yaml(path, context_name, namespace, service_name, managed_fields=False),
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, service_name, namespace, old_yaml=service_info["yaml"], new_yaml=yaml)

        if ret["success"] == False:
            service_info["show_modal"] = True
            service_info["message"] = ret["message"]
        else:
            service_info["show_modal"] = True
            service_info["changes"] = ret["changes"]
            service_info["message"] = ret["message"]
            
        new_yaml = k8s_services.get_service_yaml(path, context_name, namespace, service_name, managed_fields=True)
        new_edit = k8s_services.get_service_yaml(path, context_name, namespace, service_name, managed_fields=False)
        service_info["yaml"] = new_yaml
        service_info["edit"] = new_edit


    return render(request, 'dashboard/services/service_info.html', {"service_info": service_info, "cluster_id": cluster_id, "service_name": service_name, 
                                                                    'registered_clusters': registered_clusters, 'current_cluster': current_cluster})


def endpoints(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    
    endpoints = k8s_endpoints.get_endpoints(path, context_name)
    total_endpoints = len(endpoints)
    return render(request, 'dashboard/services/endpoints.html', {"endpoints": endpoints,"total_endpoints":total_endpoints, "cluster_id": cluster_id, 'registered_clusters': registered_clusters, 'namespaces': namespaces, 'current_cluster': current_cluster}) 


def endpoint_info(request, cluster_id, namespace, endpoint_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    endpoint_info = {
        "describe": k8s_endpoints.get_endpoint_description(path, context_name, namespace, endpoint_name),
        "events": k8s_endpoints.get_endpoint_events(path, context_name, namespace, endpoint_name),
        "yaml": k8s_endpoints.get_endpoint_yaml(path, context_name, namespace, endpoint_name, managed_fields=True),
        "edit": k8s_endpoints.get_endpoint_yaml(path, context_name, namespace, endpoint_name, managed_fields=False)
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, endpoint_name, namespace, old_yaml=endpoint_info["yaml"], new_yaml=yaml)

        if ret["success"] == False:
            endpoint_info["show_modal"] = True
            endpoint_info["message"] = ret["message"]
        else:
            endpoint_info["show_modal"] = True
            endpoint_info["changes"] = ret["changes"]
            endpoint_info["message"] = ret["message"]
            
        new_yaml = k8s_endpoints.get_endpoint_yaml(path, context_name, namespace, endpoint_name, managed_fields=True)
        new_edit = k8s_endpoints.get_endpoint_yaml(path, context_name, namespace, endpoint_name, managed_fields=False)
        endpoint_info["yaml"] = new_yaml
        endpoint_info["edit"] = new_edit

    return render(request, 'dashboard/services/endpoint_info.html', {"endpoint_info": endpoint_info, "cluster_id": cluster_id, "endpoint_name": endpoint_name, 
                                                                     'registered_clusters': registered_clusters, 'current_cluster': current_cluster})


############ PERSISTENT STORAGE SECTION ############

def persistentvolume(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    pvs, total_pvs = k8s_pv.list_persistent_volumes(path, context_name)

    return render(request, 'dashboard/persistent_storage/persistentvolume.html', {'cluster_id': cluster_id, 'registered_clusters': registered_clusters, 
                                                                                  'pvs': pvs, 'total_pvs': total_pvs, 'current_cluster': current_cluster})


def pv_info(request, cluster_id, pv_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    pv_info = {
        "describe": k8s_pv.get_pv_description(path, context_name, pv_name),
        "yaml": k8s_pv.get_pv_yaml(path, context_name, pv_name, managed_fields=True),
        "edit": k8s_pv.get_pv_yaml(path, context_name, pv_name, managed_fields=False),
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, pv_name, old_yaml=pv_info["yaml"], new_yaml=yaml)

        if ret["success"] == False:
            pv_info["show_modal"] = True
            pv_info["message"] = ret["message"]
        else:
            pv_info["show_modal"] = True
            pv_info["changes"] = ret["changes"]
            pv_info["message"] = ret["message"]
            
        new_yaml = k8s_pv.get_pv_yaml(path, context_name, pv_name, managed_fields=True)
        new_edit = k8s_pv.get_pv_yaml(path, context_name, pv_name, managed_fields=False)
        pv_info["yaml"] = new_yaml
        pv_info["edit"] = new_edit

    return render(request, 'dashboard/persistent_storage/pv_info.html', {"pv_info": pv_info, "cluster_id": cluster_id, "pv_name": pv_name, 
                                                                         'registered_clusters': registered_clusters, 'current_cluster': current_cluster})


def persistentvolumeclaim(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    pvc, total_pvc = k8s_pvc.list_pvc(path, context_name)

    return render(request, 'dashboard/persistent_storage/persistentvolumeclaim.html', {'cluster_id': cluster_id, 'registered_clusters': registered_clusters, 'pvc': pvc, 
                                                                                       'total_pvc': total_pvc, 'namespaces': namespaces, 'current_cluster': current_cluster})


def pvc_info(request, cluster_id, namespace, pvc_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    pvc_info = {
        "describe": k8s_pvc.get_pvc_description(path, context_name, namespace, pvc_name),
        "events": k8s_pvc.get_pvc_events(path, context_name, namespace, pvc_name),
        "yaml": k8s_pvc.get_pvc_yaml(path, context_name, namespace, pvc_name, managed_fields=True),
        "edit": k8s_pvc.get_pvc_yaml(path, context_name, namespace, pvc_name, managed_fields=False)
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, pvc_name, namespace, old_yaml=pvc_info["yaml"], new_yaml=yaml)

        if ret["success"] == False:
            pvc_info["show_modal"] = True
            pvc_info["message"] = ret["message"]
        else:
            pvc_info["show_modal"] = True
            pvc_info["changes"] = ret["changes"]
            pvc_info["message"] = ret["message"]
            
        new_yaml = k8s_pvc.get_pvc_yaml(path, context_name, namespace, pvc_name, managed_fields=True)
        new_edit = k8s_pvc.get_pvc_yaml(path, context_name, namespace, pvc_name, managed_fields=False)
        pvc_info["yaml"] = new_yaml
        pvc_info["edit"] = new_edit

    return render(request, 'dashboard/persistent_storage/pvc_info.html', {"pvc_info": pvc_info, "cluster_id": cluster_id, "pvc_name": pvc_name, 
                                                                          'registered_clusters': registered_clusters, 'current_cluster': current_cluster})


def storageclass(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    sc, total_sc = k8s_storage_class.list_storage_classes(path, context_name)

    return render(request, 'dashboard/persistent_storage/storageclass.html', {'cluster_id': cluster_id, 'registered_clusters': registered_clusters, 
                                                                              'sc': sc, 'total_sc': total_sc, 'current_cluster': current_cluster})

def storageclass_info(request, cluster_id, sc_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    sc_info = {
        "describe": k8s_storage_class.get_storage_class_description(path, context_name, sc_name),
        "events": k8s_storage_class.get_storage_class_events(path, context_name, sc_name),
        "yaml": k8s_storage_class.get_sc_yaml(path, context_name, sc_name, managed_fields=True),
        "edit": k8s_storage_class.get_sc_yaml(path, context_name, sc_name, managed_fields=False)
    }    

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, sc_name, old_yaml=sc_info["yaml"], new_yaml=yaml)

        if ret["success"] == False:
            sc_info["show_modal"] = True
            sc_info["message"] = ret["message"]
        else:
            sc_info["show_modal"] = True
            sc_info["changes"] = ret["changes"]
            sc_info["message"] = ret["message"]
            
        new_yaml = k8s_storage_class.get_sc_yaml(path, context_name, sc_name, managed_fields=True)
        new_edit = k8s_storage_class.get_sc_yaml(path, context_name, sc_name, managed_fields=False)
        sc_info["yaml"] = new_yaml
        sc_info["edit"] = new_edit

    return render(request, 'dashboard/persistent_storage/storageclass_info.html', {'cluster_id': cluster_id, 'registered_clusters': registered_clusters, 'sc_info': sc_info, 'current_cluster': current_cluster})

############ NETWORKING SECTION ############

def np(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    nps, nps_count = k8s_np.get_np(path, current_cluster.context_name)

    return render(request, 'dashboard/networking/np.html', {'cluster_id': cluster_id, 'registered_clusters': registered_clusters, 
                                                            'nps': nps, 'nps_count': nps_count, 'namespaces': namespaces, 'current_cluster': current_cluster})


def np_info(request, cluster_id, namespace, np_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    np_info = {
        "describe": k8s_np.get_np_description(path, current_cluster.context_name, namespace, np_name),
        "events": k8s_np.get_np_events(path, current_cluster.context_name, namespace, np_name),
        "yaml": k8s_np.get_np_yaml(path, current_cluster.context_name, namespace, np_name, managed_fields=True),
        "edit": k8s_np.get_np_yaml(path, current_cluster.context_name, namespace, np_name, managed_fields=False)
    }    

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, np_name, namespace, old_yaml=np_info["yaml"], new_yaml=yaml)

        if ret["success"] == False:
            np_info["show_modal"] = True
            np_info["message"] = ret["message"]
        else:
            np_info["show_modal"] = True
            np_info["changes"] = ret["changes"]
            np_info["message"] = ret["message"]
            
        new_yaml = k8s_np.get_np_yaml(path, context_name, namespace, np_name, managed_fields=True)
        new_edit = k8s_np.get_np_yaml(path, context_name, namespace, np_name, managed_fields=False)
        np_info["yaml"] = new_yaml
        np_info["edit"] = new_edit

    return render(request, 'dashboard/networking/np_info.html', {'cluster_id': cluster_id, 
                                                                 'registered_clusters': registered_clusters, 'np_info': np_info, 'current_cluster': current_cluster})


def ingress(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    ingress, ingress_count = k8s_ingress.get_ingress(path, current_cluster.context_name)

    return render(request, 'dashboard/networking/ingress.html', {'cluster_id': cluster_id, 'registered_clusters': registered_clusters, 
                                                                 'ingress': ingress, 'ingress_count': ingress_count, 'namespaces': namespaces, 'current_cluster': current_cluster})

def ingress_info(request, cluster_id, namespace, ingress_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    ingress_info = {
        "describe": k8s_ingress.get_ingress_description(path, current_cluster.context_name, namespace, ingress_name),
        "events": k8s_ingress.get_ingress_events(path, current_cluster.context_name, namespace, ingress_name),
        "yaml": k8s_ingress.get_ingress_yaml(path, current_cluster.context_name, namespace, ingress_name, managed_fields=True),
        "edit": k8s_ingress.get_ingress_yaml(path, current_cluster.context_name, namespace, ingress_name, managed_fields=False)
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, ingress_name, namespace, old_yaml=ingress_info["yaml"], new_yaml=yaml)

        if ret["success"] == False:
            ingress_info["show_modal"] = True
            ingress_info["message"] = ret["message"]
        else:
            ingress_info["show_modal"] = True
            ingress_info["changes"] = ret["changes"]
            ingress_info["message"] = ret["message"]
            
        new_yaml = k8s_ingress.get_ingress_yaml(path, context_name, namespace, ingress_name, managed_fields=True)
        new_edit = k8s_ingress.get_ingress_yaml(path, context_name, namespace, ingress_name, managed_fields=False)
        ingress_info["yaml"] = new_yaml
        ingress_info["edit"] = new_edit

    return render(request, 'dashboard/networking/ingress_info.html', {'cluster_id': cluster_id, 'registered_clusters': registered_clusters, 'ingress_info': ingress_info, 'current_cluster': current_cluster})


############ RBAC SECTION ############

def role(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    role, total_role = k8s_role.list_roles(path, current_cluster.context_name)

    return render(request, 'dashboard/RBAC/role.html', {'cluster_id': cluster_id, 'registered_clusters': registered_clusters, 
                                                        'role': role, 'total_role': total_role, 'namespaces': namespaces, 'current_cluster': current_cluster})


def role_info(request, cluster_id, namespace, role_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    role_info = {
        "describe": k8s_role.get_role_description(path, context_name, namespace, role_name),
        "events": k8s_role.get_role_events(path, context_name, namespace, role_name),
        "yaml": k8s_role.get_role_yaml(path, context_name, namespace, role_name, managed_fields=True),
        "edit": k8s_role.get_role_yaml(path, context_name, namespace, role_name, managed_fields=False)
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, role_name, namespace, old_yaml=role_info["yaml"], new_yaml=yaml)

        if ret["success"] == False:
            role_info["show_modal"] = True
            role_info["message"] = ret["message"]
        else:
            role_info["show_modal"] = True
            role_info["changes"] = ret["changes"]
            role_info["message"] = ret["message"]
            
        new_yaml = k8s_role.get_role_yaml(path, context_name, namespace, role_name, managed_fields=True)
        new_edit = k8s_role.get_role_yaml(path, context_name, namespace, role_name, managed_fields=False)
        role_info["yaml"] = new_yaml
        role_info["edit"] = new_edit

    return render(request, 'dashboard/RBAC/role_info.html', {"role_info": role_info, "cluster_id": cluster_id, 'registered_clusters': registered_clusters, 'current_cluster': current_cluster})


def rolebinding(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    rolebinding, total_rolebinding = k8s_rolebindings.list_rolebindings(path, context_name)

    return render(request, 'dashboard/RBAC/rolebinding.html', {'cluster_id': cluster_id, 'registered_clusters': registered_clusters, 
                                                               'rolebinding': rolebinding, 'total_rolebinding': total_rolebinding, 'namespaces': namespaces, 'current_cluster': current_cluster})


def role_binding_info(request, cluster_id, namespace, role_binding_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    role_binding_info = {
        "describe": k8s_rolebindings.get_role_binding_description(path, context_name, namespace, role_binding_name),
        "events": k8s_rolebindings.get_role_binding_events(path, context_name, namespace, role_binding_name),
        "yaml": k8s_rolebindings.get_role_binding_yaml(path, context_name, namespace, role_binding_name, managed_fields=True),
        "edit": k8s_rolebindings.get_role_binding_yaml(path, context_name, namespace, role_binding_name, managed_fields=False)
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, role_binding_name, namespace, old_yaml=role_binding_info["yaml"], new_yaml=yaml)

        if ret["success"] == False:
            role_binding_info["show_modal"] = True
            role_binding_info["message"] = ret["message"]
        else:
            role_binding_info["show_modal"] = True
            role_binding_info["changes"] = ret["changes"]
            role_binding_info["message"] = ret["message"]
            
        new_yaml = k8s_rolebindings.get_role_binding_yaml(path, context_name, namespace, role_binding_name, managed_fields=True)
        new_edit = k8s_rolebindings.get_role_binding_yaml(path, context_name, namespace, role_binding_name, managed_fields=False)
        role_binding_info["yaml"] = new_yaml
        role_binding_info["edit"] = new_edit

    return render(request, 'dashboard/RBAC/rolebinding_info.html', {"role_binding_info": role_binding_info, "cluster_id": cluster_id, 
                                                                    'registered_clusters': registered_clusters, 'current_cluster': current_cluster})


def clusterrole(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    clusterrole, total_clusterrole = k8s_cluster_roles.get_cluster_role(path, context_name)

    return render(request, 'dashboard/RBAC/clusterrole.html', {'cluster_id': cluster_id, 'registered_clusters': registered_clusters, 
                                                               'clusterrole': clusterrole, 'total_clusterrole': total_clusterrole, 'current_cluster': current_cluster})


def clusterrole_info(request, cluster_id, cluster_role_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    cluster_role_info = {
        "describe": k8s_cluster_roles.get_cluster_role_description(path, context_name, cluster_role_name),
        "events": k8s_cluster_roles.get_cluster_role_events(path, context_name, cluster_role_name),
        "yaml": k8s_cluster_roles.get_cluster_role_yaml(path, context_name, cluster_role_name, managed_fields=True),
        "edit": k8s_cluster_roles.get_cluster_role_yaml(path, context_name, cluster_role_name, managed_fields=False)
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, cluster_role_name, old_yaml=cluster_role_info["yaml"], new_yaml=yaml)

        if ret["success"] == False:
            cluster_role_info["show_modal"] = True
            cluster_role_info["message"] = ret["message"]
        else:
            cluster_role_info["show_modal"] = True
            cluster_role_info["changes"] = ret["changes"]
            cluster_role_info["message"] = ret["message"]
            
        new_yaml = k8s_cluster_roles.get_cluster_role_yaml(path, context_name, cluster_role_name, managed_fields=True)
        new_edit = k8s_cluster_roles.get_cluster_role_yaml(path, context_name, cluster_role_name, managed_fields=False)
        cluster_role_info["yaml"] = new_yaml
        cluster_role_info["edit"] = new_edit

    return render(request, 'dashboard/RBAC/clusterrole_info.html', {"cluster_role_info": cluster_role_info, "cluster_id": cluster_id, 
                                                                    'registered_clusters': registered_clusters, 'current_cluster': current_cluster})


def clusterrolebinding(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    clusterrolebinding, total_clusterrolebinding = k8s_cluster_role_bindings.get_cluster_role_bindings(path, context_name)

    return render(request, 'dashboard/RBAC/clusterrolebinding.html', {'cluster_id': cluster_id, 'registered_clusters': registered_clusters, 'clusterrolebinding': clusterrolebinding, 
                                                                      'total_clusterrolebinding': total_clusterrolebinding, 'current_cluster': current_cluster})


def cluster_role_binding_info(request, cluster_id, cluster_role_binding_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    cluster_role_binding_info = {
        "describe": k8s_cluster_role_bindings.get_cluster_role_binding_description(path, context_name, cluster_role_binding_name),
        "events": k8s_cluster_role_bindings.get_cluster_role_binding_events(path, context_name, cluster_role_binding_name),
        "yaml": k8s_cluster_role_bindings.get_cluster_role_binding_yaml(path, context_name, cluster_role_binding_name, managed_fields=True),
        "edit": k8s_cluster_role_bindings.get_cluster_role_binding_yaml(path, context_name, cluster_role_binding_name, managed_fields=False)
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, cluster_role_binding_name, old_yaml=cluster_role_binding_info["yaml"], new_yaml=yaml)

        if ret["success"] == False:
            cluster_role_binding_info["show_modal"] = True
            cluster_role_binding_info["message"] = ret["message"]
        else:
            cluster_role_binding_info["show_modal"] = True
            cluster_role_binding_info["changes"] = ret["changes"]
            cluster_role_binding_info["message"] = ret["message"]
            
        new_yaml = k8s_cluster_role_bindings.get_cluster_role_binding_yaml(path, context_name, cluster_role_binding_name, managed_fields=True)
        new_edit = k8s_cluster_role_bindings.get_cluster_role_binding_yaml(path, context_name, cluster_role_binding_name, managed_fields=False)
        cluster_role_binding_info["yaml"] = new_yaml
        cluster_role_binding_info["edit"] = new_edit

    return render(request, 'dashboard/RBAC/clusterrolebinding_info.html', {"cluster_role_binding_info": cluster_role_binding_info, 
                                                                           "cluster_id": cluster_id, 'registered_clusters': registered_clusters, 'current_cluster': current_cluster})


def serviceAccount(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    serviceAccount, total_serviceAccount = k8s_service_accounts.get_service_accounts(path, context_name)

    return render(request, 'dashboard/RBAC/serviceAccount.html', {'cluster_id': cluster_id, 'registered_clusters': registered_clusters, 
                                                                  'serviceAccount': serviceAccount, 'total_serviceAccount': total_serviceAccount, 'namespaces': namespaces, 'current_cluster': current_cluster})


def serviceAccountInfo(request, cluster_id, namespace, sa_name):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

    serviceAccountInfo = {
        "describe": k8s_service_accounts.get_sa_description(path, context_name, namespace, sa_name),
        "events": k8s_service_accounts.get_sa_events(path, context_name, namespace, sa_name),
        "yaml": k8s_service_accounts.get_sa_yaml(path, context_name, namespace, sa_name, managed_fields=True),
        "edit": k8s_service_accounts.get_sa_yaml(path, context_name, namespace, sa_name, managed_fields=False)
    }

    if request.method == 'POST':
        yaml = request.POST.get('yaml')
        ret = validate_and_patch_resource(path, context_name, sa_name, namespace, old_yaml=serviceAccountInfo["yaml"], new_yaml=yaml)

        if ret["success"] == False:
            serviceAccountInfo["show_modal"] = True
            serviceAccountInfo["message"] = ret["message"]
        else:
            serviceAccountInfo["show_modal"] = True
            serviceAccountInfo["changes"] = ret["changes"]
            serviceAccountInfo["message"] = ret["message"]
            
        new_yaml = k8s_service_accounts.get_sa_yaml(path, context_name, namespace, sa_name, managed_fields=True)
        new_edit = k8s_service_accounts.get_sa_yaml(path, context_name, namespace, sa_name, managed_fields=False)
        serviceAccountInfo["yaml"] = new_yaml
        serviceAccountInfo["edit"] = new_edit

    return render(request, 'dashboard/RBAC/serviceAccountInfo.html', {'cluster_id': cluster_id, 'registered_clusters': registered_clusters, 
                                                                      'serviceAccountInfo': serviceAccountInfo, 'current_cluster': current_cluster})


############ METRICS SECTION ############

def pod_metrics(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)

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

    return render(request, 'dashboard/metrics/pod_metrics.html', {'all_pod_metrics': all_pod_metrics if metrics_available else [], 'total_pods': total_pods, 
                                                                  'metrics_available': metrics_available, 'error_message': error_message, 'cluster_id': cluster_id, 
                                                                  'registered_clusters': registered_clusters, 'namespaces': namespaces, 'current_cluster': current_cluster})


def node_metrics(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    
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
    
    return render(request, 'dashboard/metrics/node_metrics.html', {'node_metrics': node_metrics if metrics_available else [], 'total_nodes': total_nodes, 'metrics_available': metrics_available, 
                                                                   'error_message': error_message, 'cluster_id': cluster_id, 
                                                                   'registered_clusters': registered_clusters, 'namespaces': namespaces, 'current_cluster': current_cluster})


############ EVENTS SECTION ############


def events(request=None, cluster_id = None):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    
    events = k8s_events.get_events(path, context_name, False)
    if not isinstance(events, list):
        events = []
    # Paginate events
    paginator = Paginator(events, 50)  
    page_number = request.GET.get('page')  
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'dashboard/events.html', {'cluster_id': cluster_id, 'events': page_obj,
                                                     'registered_clusters': registered_clusters,
                                                     'namespaces': namespaces, 'page_obj': page_obj, 'current_cluster': current_cluster})


current_working_directory = os.path.expanduser('~')

@csrf_exempt
def execute_command(request):
    global current_working_directory

    if request.method == 'POST':
        import json
        data = json.loads(request.body)
        command = data.get('command', '')

        try:
            # Handle 'cd' command separately
            if command.strip().startswith('cd'):
                # Extract the directory path from the command
                new_dir = command.strip().split(' ', 1)[1] if len(command.strip().split(' ', 1)) > 1 else ''

                # Handle 'cd' without arguments (go to home directory)
                if not new_dir:
                    new_dir = os.path.expanduser('~')

                # Resolve the full path
                new_dir = os.path.join(current_working_directory, new_dir)
                new_dir = os.path.abspath(os.path.expanduser(new_dir))

                # Check if the directory exists
                if os.path.isdir(new_dir):
                    current_working_directory = new_dir
                    output = f"Changed directory to: {current_working_directory}"
                else:
                    output = f"Error: Directory not found: {new_dir}"
            else:
                # Determine the shell based on the OS
                if os.name == 'nt':  # Windows
                    shell = 'C:\\Windows\\System32\\cmd.exe'
                    if command.strip() == 'ls':
                        command = 'dir'  # Replace 'ls' with 'dir' on Windows
                    elif command.strip() == 'pwd':
                        command = 'cd'  # Replace 'pwd' with 'cd' on Windows
                    elif command.strip().startswith('cat'):
                        command = command.replace('cat', 'type', 1)  # Replace 'cat' with 'type' on Windows
                else:  # Unix-like systems (Linux, macOS)
                    shell = '/bin/bash'

                # Execute the command
                result = subprocess.run(
                    command,
                    shell=True,
                    executable=shell,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=current_working_directory,  # Use the current working directory
                    env=os.environ  # Pass the current environment variables
                )

                if result.returncode == 0:
                    output = result.stdout
                else:
                    output = result.stderr
        except Exception as e:
            output = f"Error: {str(e)}"

        return JsonResponse({'output': output})
    
################### Download report Function #############################    

def get_cluster_name():
    try:
        contexts, current_context = config.list_kube_config_contexts()
        if current_context:
            return current_context['context']['cluster']
    except ConfigException:
        return "in-cluster"
    return "unknown"

def generate_reports(request):
    try:
        # Load kube config
        try:
            config.load_incluster_config()
        except ConfigException:
            config.load_kube_config()

        # Fetch all resources
        pods = get_pod_details()
        pod_counts = len(pods)
        nodes = get_node_details()
        node_counts = len(nodes)
        namespaces = get_namespace_details()
        namespace_count = len(namespaces)
        deployments = get_deployment_details()
        deployment_counts = len(deployments)
        services = get_service_details()
        endpoints = get_endpoint_details()
        ingresses = get_ingress_details()
        cluster_name = get_cluster_name()

        # Cluster Overview
        v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()

        total_nodes = len(nodes)
        ready_nodes = sum(1 for node in nodes if node['status'] == 'Ready')

        running_pods = sum(1 for p in pods if p['status'] == "Running")
        pending_pods = sum(1 for p in pods if p['status'] == "Pending")
        failed_pods = sum(1 for p in pods if p['status'] == "Failed")
        pod_namespaces = list(set(p['namespace'] for p in pods))

        available_deployments = sum(1 for d in deployments if d.get('available_replicas', 0) > 0)
        deployment_namespaces = list(set(d['namespace'] for d in deployments))

        cluster_ip_services = sum(1 for s in services if s['type'] == "ClusterIP")
        load_balancer_services = sum(1 for s in services if s['type'] == "LoadBalancer")
        node_port_services = sum(1 for s in services if s['type'] == "NodePort")
        service_namespaces = list(set(s['namespace'] for s in services))

        cluster_overview = {
            'nodes': {
                'total': total_nodes,
                'ready': ready_nodes,
                'namespaces': pod_namespaces
            },
            'pods': {
                'total': pod_counts,
                'running': running_pods,
                'pending': pending_pods,
                'failed': failed_pods,
                'namespaces': pod_namespaces
            },
            'deployments': {
                'total': deployment_counts,
                'available': available_deployments,
                'namespaces': deployment_namespaces
            },
            'services': {
                'total': len(services),
                'cluster_ip': cluster_ip_services,
                'load_balancer': load_balancer_services,
                'node_port': node_port_services,
                'namespaces': service_namespaces
            }
        }

        context = {
            'title': 'KubeBuddy Report',
            'pods': pods,
            'pod_counts': pod_counts,
            'nodes': nodes,
            'node_count': node_counts,
            'namespaces': namespaces,
            'namespace_count': namespace_count,
            'deployments': deployments,
            'deployment_counts': deployment_counts,
            'services': services,
            'endpoints': endpoints,
            'ingresses': ingresses,
            'cluster_name': cluster_name,
            'cluster_overview': cluster_overview,
        }

        template = get_template('dashboard/generate_reports.html')
        html = template.render(context)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="report.pdf"'

        pdf_status = generate_pdf(html, response)
        if not pdf_status:
            return HttpResponse("Error generating PDF", status=500)

        return response

    except Exception as e:
        return HttpResponse(f"Exception occurred: {e}", status=500)
    
# kube-bench report views

def kube_bench_report(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    try:
        kube_bench.kube_bench_report_generate(path, context_name)

        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        file_path = os.path.join(BASE_DIR, 'static', 'fpdf', 'kube_bench_report.pdf')

        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename='kube_bench_report.pdf')
    except Exception as e:
        print('Caught exception:', e)
        return HttpResponseServerError("Error generating report.")

def cluster_hotspot(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    try:
        empty_namespaces, latest_tag_pods, orphaned_configmaps, orphaned_secrets, container_missing_probes, container_restart_count, priviledged_containers, empty_limit = get_cluster_hotspot(path, context_name)
        
        # grab top 5 container reestart count
        container_restart_count = sorted(container_restart_count, key = lambda x: x['restart_count'], reverse = True)
        container_restart_count = container_restart_count[:5]
        return render(request, 'dashboard/cluster_hotspot.html', {'cluster_id': cluster_id, 'current_cluster': current_cluster, 
                                                                  'registered_clusters': registered_clusters, 
                                                                  'empty_namespaces': empty_namespaces, 'latest_tag_pods': latest_tag_pods, 'orphanded_configmaps': orphaned_configmaps, 'orphaned_secrets': orphaned_secrets, 'container_missing_probes': container_missing_probes,
                                                                  'container_restart_count': container_restart_count, 'priviledged_containers': priviledged_containers, "empty_limit": empty_limit})
            
    except Exception as e:
        print('Caught exception: ', e)

def k8sgpt_view(request, cluster_id):
    cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(request)
    filter_list = ['Pod', 'ConfigMap', 'Service', 'ReplicaSet', 'StatefulSet', 'CronJob', 'PersistentVolumeClaim', 'Node','Deployment', 'Ingress', 'ValidatingWebhookConfiguration', 'MutatingWebhookConfiguration']
    if request.method == 'GET':
        # Handle GET request to display the k8sgpt page
        return render(request, 'dashboard/k8sgpt.html', {'cluster_id': cluster_id, 'registered_clusters': registered_clusters, 
                                                         'namespaces': namespaces, 'current_cluster': current_cluster, 'filter_list': filter_list })
    else:
        output = None
        selected_namespace = request.POST.get('namespace')
        explain = request.POST.get('explain')
        filters = request.POST.getlist('resources')
        if 'All' in filters or not filters: 
            filters_to_pass = None
        else:
            filters_to_pass = filters
        if explain:
            output = k8sgpt.k8sgpt_analyze_explain(selected_namespace, path, context_name, filters=filters_to_pass)
            if output:
                output = output['results']
            else:
                output = "Error"
        else:
            output = k8sgpt.k8sgpt_analyze(selected_namespace, path, context_name,filters=filters_to_pass )
            if output:
                output = output['results']
            else:
                output = "Error"

        return render(request, 'dashboard/k8sgpt.html', {'cluster_id': cluster_id, 'registered_clusters': registered_clusters,
                                                         'namespaces': namespaces, 'current_cluster': current_cluster,'output': output,
                                                         'selected_namespace': selected_namespace, 'explain': explain, 'filter_list': filter_list, 'filters':filters_to_pass })
