from kubernetes import client, config
from kubernetes.client.models import V2ObjectMetricStatus

def getMetrics(path, context):
    config.load_kube_config(config_file=path, context = context)

    # Create an instance of the Metrics API
    metrics_api = client.CustomObjectsApi()

    # Define the namespace and metrics API endpoint
    namespace = "kube-system"
    group = "metrics.k8s.io"
    version = "v1beta1"
    plural = "pods"

    # Fetch pod metrics
    pod_metrics = metrics_api.list_namespaced_custom_object(group, version, namespace, plural)

    # Print CPU and memory usage for each pod
    for pod in pod_metrics["items"]:
        pod_name = pod["metadata"]["name"]
        print(f"Pod: {pod_name}")
        for container in pod["containers"]:
            container_name = container["name"]
            cpu_usage = container["usage"]["cpu"]
            memory_usage = container["usage"]["memory"]
            print(f"  Container: {container_name}")
            print(f"    CPU Usage: {cpu_usage}")
            print(f"    Memory Usage: {memory_usage}")


    return pod_metrics