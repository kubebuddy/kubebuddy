from main.models import Cluster
from kubernetes import config, client
from kubebuddy.appLogs import logger
import urllib3

def get_registered_clusters():
    control_plane_components = [
        {"key": "component", "value": "kube-apiserver"},
        {"key": "component", "value": "etcd"}
    ]
    core_dns_label = {"key": "k8s-app", "value": "kube-dns"}

    registered_clusters = Cluster.objects.all()

    for context in registered_clusters:
        cluster_name = context.cluster_name
        path = context.kube_config.path
        failed_control_pods = []
        failed_dns_pods = []
        
        try:
            config.load_kube_config(config_file=path, context=context.context_name)
        except Exception as e:
            print(f"Error loading kubeconfig for {cluster_name}: {e}")
            context.control_plane_status = "Unavailable"
            context.core_dns_status = "Unavailable"
            context.number_of_nodes = 0
            context.failed_control_pods = []
            context.failed_dns_pods = []
            continue  # Skip further checks for this cluster
        
        try:
            v1 = client.CoreV1Api()
            nodes = v1.list_node().items
            context.number_of_nodes = len(nodes)
            context.control_plane_status = "Running"
            context.core_dns_status = "Running"

            # Check Control Plane components
            for component in control_plane_components:
                label_selector = f"{component['key']}={component['value']}"
                pods = v1.list_namespaced_pod(namespace="kube-system", label_selector=label_selector)
                for pod in pods.items:
                    if pod.status.phase != "Running":
                        context.control_plane_status = "Unhealthy"
                        failed_control_pods.append(pod.metadata.name)

            # Check CoreDNS
            label_selector = f"{core_dns_label['key']}={core_dns_label['value']}"
            core_dns_pods = v1.list_namespaced_pod(namespace="kube-system", label_selector=label_selector)
            for pod in core_dns_pods.items:
                if pod.status.phase != "Running":
                    context.core_dns_status = "Unhealthy"
                    failed_dns_pods.append(pod.metadata.name)

            context.failed_control_pods = failed_control_pods
            context.failed_dns_pods = failed_dns_pods

        except urllib3.exceptions.MaxRetryError as e:
            print(f"Cluster {cluster_name} is unreachable: {e}")
            context.control_plane_status = "Unavailable"
            context.core_dns_status = "Unavailable"
            context.number_of_nodes = 0
            context.failed_control_pods = []
            context.failed_dns_pods = []
        except Exception as e:
            print(f"Unexpected error for {cluster_name}: {e}")

    return registered_clusters

def get_cluster_names():
    clusters = Cluster.objects.all()
    return [{"cluster_name": cluster.cluster_name} for cluster in clusters]