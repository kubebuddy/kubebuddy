from kubernetes import client, config
from kubernetes.client.models import V2ObjectMetricStatus

def getMetrics(node_list, path, context, namespace="all"):
    config.load_kube_config(config_file=path, context = context)

    # Create an instance of the Metrics API
    metrics_api = client.CustomObjectsApi()
    client_api = client.CoreV1Api()
    # Define the namespace and metrics API endpoint
    group = "metrics.k8s.io"
    version = "v1beta1"
    plural = "pods"

    # Fetch pod metrics
    node_status = client_api.list_node()
    pod_metrics = metrics_api.list_custom_object_for_all_namespaces(group, version, plural) if namespace == "all" else metrics_api.list_namespaced_custom_object(group, version, plural)

    # cpu and memory usage
    total_cpu_usage = 0
    total_memory_usage = 0
    # Print CPU and memory usage for each pod
    for pod in pod_metrics["items"]:
        for container in pod["containers"]:
            cpu_usage = container["usage"]["cpu"]
            memory_usage = container["usage"]["memory"]
            cpu_value = 0
            
            if cpu_usage.endswith('n'):
                cpu_value = int(cpu_usage[:-1])
            elif cpu_usage.endswith('m'):
                cpu_value = int(cpu_usage[:-1]) * 1_000_000
            
            total_cpu_usage += cpu_value

            if memory_usage.endswith("Ki"):
                memory_value = int(memory_usage[:-2]) 
            elif memory_usage.endswith("Mi"):
                memory_value = int(memory_usage[:-2]) * 1024
            elif memory_usage.endswith("Gi"):
                memory_value = int(memory_usage[:-2]) * 1024 * 1024

            total_memory_usage += memory_value

    total_cpu_millicore = total_cpu_usage / 1_000_000
    total_memory_gb = total_memory_usage / (1024 * 1024)

    total_cpu_capacity = 0
    total_memory_capacity = 0

    for node in node_status.items:
        total_cpu_capacity += int(node.status.capacity["cpu"])
        total_memory_capacity += int(node.status.capacity["memory"][:-2])

    # millicores and megabytes
    total_cpu_capacity_millicore = total_cpu_capacity * 1_000_000
    total_cpu_capacity_millicore = round(total_cpu_capacity_millicore, 2)
    total_memory_capacity_gb = total_memory_capacity / (1024 * 1024)
    total_memory_capacity_gb = round(total_memory_capacity_gb, 2)

    cpu_percent = (total_cpu_millicore / total_cpu_capacity_millicore) * 100
    cpu_percent = round(cpu_percent, 2)

    memory_percent = (total_memory_gb / total_memory_capacity_gb) * 100
    memory_percent = round(memory_percent, 2)

    metrics = {'cpu_usage': cpu_percent, 'memory_usage': memory_percent, 'cpu_total': total_cpu_capacity, 'memory_total': total_memory_capacity_gb}

    return metrics