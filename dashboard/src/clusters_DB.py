from main.models import Cluster
from kubernetes import config, client
import urllib3

def get_registered_clusters():
    
    # pods to check for control plane and dns status
    control_plane_components = [
    {"key": "component", "value": "kube-apiserver"},
    {"key": "component", "value": "etcd"}
    ]
    core_dns_label = {"key": "k8s-app", "value": "kube-dns"}

    # saved clusters in db
    registered_clusters = Cluster.objects.all()

    for context in registered_clusters:
        cluster_name = context.cluster_name
        failed_control_pods = []
        failed_dns_pods = []
        
        try:
            # Set the current context to the specific context
            config.load_kube_config(context=cluster_name)
            v1 = client.CoreV1Api()

            # Get number of nodes
            nodes = v1.list_node().items
            context.number_of_nodes = len(nodes)

            # Check if all control plane components are running
            context.control_plane_status = "Running"
            context.core_dns_status = "Running"
            for component in control_plane_components:
                label_selector = f"{component['key']}={component['value']}"
                pods = v1.list_namespaced_pod(namespace="kube-system", label_selector=label_selector)
                for pod in pods.items:
                    if pod.status.phase != "Running":
                        context.control_plane_status = "Unhealthy"
                        failed_control_pods.append(pod.metadata.name)

            # Check if all CoreDNS pods are running
            label_selector = f"{core_dns_label['key']}={core_dns_label['value']}"
            core_dns_pods = v1.list_namespaced_pod(namespace="kube-system", label_selector=label_selector)
            for pod in core_dns_pods.items:
                if pod.status.phase != "Running":
                    context.core_dns_status = "Unhealthy"
                    failed_dns_pods.append(pod.metadata.name)
            
            # if failed pods present add them to cluster info
            context.failed_control_pods = failed_control_pods
            context.failed_dns_pods = failed_dns_pods

        except urllib3.exceptions.MaxRetryError as e:
            print(e)
            context.control_plane_status = "Unavailable"
            context.core_dns_status = "Unavailable"
        except Exception as e:
            pass
    
    return registered_clusters