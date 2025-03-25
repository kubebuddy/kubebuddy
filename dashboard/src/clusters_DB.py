from main.models import Cluster
from kubernetes import config, client
from kubebuddy.appLogs import logger
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def get_cluster_status(request):

    cluster = json.loads(request.body)
    control_plane_components = [
        {"key": "component", "value": "kube-apiserver"},
        {"key": "component", "value": "etcd"}
    ]

    core_dns_label = {"key": "k8s-app", "value": "kube-dns"}
    failed_control_pods = []
    failed_dns_pods = []

    try:
        config.load_kube_config(config_file=cluster['kube_config__path'], context=cluster['context_name'])
    except Exception as e:
<<<<<<< Updated upstream
        logger.info(f"Error loading kubeconfig for {cluster['cluster_name']}: {e}")
=======
        logger.error(f"Error loading kubeconfig for {cluster['cluster_name']}: {e}")
>>>>>>> Stashed changes
        cluster.control_plane_status = "Unavailable"
        cluster.core_dns_status = "Unavailable"
        cluster.number_of_nodes = 'N/A'
        cluster.failed_control_pods = []
        cluster.failed_dns_pods = []
        return JsonResponse({"message": "Cluster status retrieved", "received_data": cluster})
    
    try:
        v1 = client.CoreV1Api()
        nodes = v1.list_node().items
        cluster['number_of_nodes'] = len(nodes)
        cluster['control_plane_status'] = "Running"
        cluster['core_dns_status'] = "Running"

        # Check Control Plane components
        for component in control_plane_components:
            label_selector = f"{component['key']}={component['value']}"
            pods = v1.list_namespaced_pod(namespace="kube-system", label_selector=label_selector)
            for pod in pods.items:
                if pod.status.phase != "Running":
                    cluster['control_plane_status'] = "Unhealthy"
                    failed_control_pods.append(pod.metadata.name)

        # Check CoreDNS
        label_selector = f"{core_dns_label['key']}={core_dns_label['value']}"
        core_dns_pods = v1.list_namespaced_pod(namespace="kube-system", label_selector=label_selector)
        for pod in core_dns_pods.items:
            if pod.status.phase != "Running":
                cluster['core_dns_status'] = "Unhealthy"
                failed_dns_pods.append(pod.metadata.name)

        cluster['failed_control_pods'] = failed_control_pods
        cluster['failed_dns_pods'] = failed_dns_pods
        return JsonResponse({"message": "Cluster status retrieved", "received_data": cluster})

    except Exception as e:
<<<<<<< Updated upstream
        logger.info(f"Cluster {cluster['cluster_name']} is unreachable: {e}")
=======
        logger.error(f"Cluster {cluster['cluster_name']} is unreachable: {e}")
>>>>>>> Stashed changes
        cluster['control_plane_status'] = "Unavailable"
        cluster['core_dns_status'] = "Unavailable"
        cluster['number_of_nodes'] = 'N/A'
        cluster['failed_control_pods'] = []
        cluster['failed_dns_pods'] = []
        return JsonResponse({"message": "Cluster status retrieved", "received_data": cluster})

def get_registered_clusters():
    clusters = Cluster.objects.all().values("id", "cluster_name", "context_name", "kube_config__path")
    return list(clusters)

def get_cluster_names():
    clusters = Cluster.objects.all()
    return [{"cluster_name": cluster.cluster_name, "id": cluster.id} for cluster in clusters]