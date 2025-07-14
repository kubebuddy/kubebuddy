# dashboard.py
from concurrent.futures import ThreadPoolExecutor
from . import k8s_cluster_metric
from .workloads import k8s_cronjobs, k8s_daemonset, k8s_deployments, k8s_jobs, k8s_pods, k8s_replicaset, k8s_statefulset
from .cluster_management import k8s_nodes
from .events import k8s_events

def fetch_nodes_status(path, context_name):
    return k8s_nodes.get_nodes_status(path, context_name)

def fetch_nodes(path, context_name):
    return k8s_nodes.getnodes(path, context_name)

def fetch_pods_status(path, context_name, namespace):
    return k8s_pods.getPodsStatus(path, context_name, namespace)

def fetch_pods(path, context_name, namespace):
    return k8s_pods.getpods(path, context_name, namespace)

def fetch_deployments(path, context_name, namespace):
    return k8s_deployments.getDeploymentsStatus(path, context_name, namespace)

def fetch_daemonsets(path, context_name, namespace):
    return k8s_daemonset.getDaemonsetStatus(path, context_name, namespace)

def fetch_replicasets(path, context_name, namespace):
    return k8s_replicaset.getReplicasetStatus(path, context_name, namespace)

def fetch_statefulsets(path, context_name, namespace):
    return k8s_statefulset.getStatefulsetStatus(path, context_name, namespace)

def fetch_jobs(path, context_name, namespace):
    return k8s_jobs.getJobsStatus(path, context_name, namespace)

def fetch_cronjobs(path, context_name, namespace):
    return k8s_cronjobs.getCronJobsStatus(path, context_name, namespace)

def fetch_metrics(path, context_name):
    return k8s_cluster_metric.getMetrics(path, context_name)

def fetch_events(path, context_name, namespace):
    return k8s_events.get_events(path, context_name, True, namespace)

def fetch_dashboard_data(path, context_name, namespace, current_cluster, namespaces, namespaces_count, cluster_id, registered_clusters, warning_message):
    with ThreadPoolExecutor() as executor:
        futures = {
            "nodes_status": executor.submit(fetch_nodes_status, path, context_name),
            "nodes": executor.submit(fetch_nodes, path, context_name),
            "pods_status": executor.submit(fetch_pods_status, path, context_name, namespace),
            "pods": executor.submit(fetch_pods, path, context_name, namespace),
            "deployments_status": executor.submit(fetch_deployments, path, context_name, namespace),
            "daemonsets_status": executor.submit(fetch_daemonsets, path, context_name, namespace),
            "replicasets_status": executor.submit(fetch_replicasets, path, context_name, namespace),
            "statefulsets_status": executor.submit(fetch_statefulsets, path, context_name, namespace),
            "jobs_status": executor.submit(fetch_jobs, path, context_name, namespace),
            "cronjobs_status": executor.submit(fetch_cronjobs, path, context_name, namespace),
            "metrics": executor.submit(fetch_metrics, path, context_name),
            "events": executor.submit(fetch_events, path, context_name, namespace),
        }

        results = {key: future.result() for key, future in futures.items()}
    
    # Prepare the context for the template
    context = {
        'warning': warning_message,
        'ready_nodes': results["nodes_status"][0],
        'not_ready_nodes': results["nodes_status"][1],
        'node_count': results["nodes_status"][2],
        'status_count': results["pods_status"],
        'pod_count': results["pods"][1],
        'current_cluster': current_cluster,
        'node_list': results["nodes"],
        'deployments_status': results["deployments_status"],
        'daemonset_status': results["daemonsets_status"],
        'replicaset_status': results["replicasets_status"],
        'statefulset_status': results["statefulsets_status"],
        'jobs_status': results["jobs_status"],
        'cronjob_status': results["cronjobs_status"],
        'namespaces': namespaces,
        'selected_namespace': namespace,
        'namespaces_count': namespaces_count,
        'cluster_id': cluster_id,
        'metrics': results["metrics"],
        'registered_clusters': registered_clusters,
        'events': results["events"],
        'context_name': context_name
    }
    
    return context
