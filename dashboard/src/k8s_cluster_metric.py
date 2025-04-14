from kubernetes import client, config
from .utils import configure_k8s
def getMetrics(path, context):
    try:
        configure_k8s(path, context)

        api = client.CustomObjectsApi()
        core_api = client.CoreV1Api()

        metrics = api.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "nodes")

        node_list = core_api.list_node()

        total_cpu_usage = 0
        total_memory_usage = 0
        total_cpu_capacity = 0
        total_memory_capacity = 0

        for node in metrics["items"]:
            node_name = node["metadata"]["name"]
            
            # CPU Usage (convert from nanocores to cores)
            usage_cpu = int(node["usage"]["cpu"][:-1]) / 1e9
            total_cpu_usage += usage_cpu

            # Memory Usage (convert from Ki to Gi)
            usage_memory = int(node["usage"]["memory"][:-2]) / (1024 * 1024)
            total_memory_usage += usage_memory

            # Get total capacity of each node
            for n in node_list.items:
                if n.metadata.name == node_name:
                    total_cpu_capacity += int(n.status.capacity["cpu"])  # Cores
                    total_memory_capacity += int(n.status.capacity["memory"][:-2]) / (1024 * 1024)  # Convert Ki to Gi
                    total_memory_capacity = round(total_memory_capacity, 2)
        # Calculate percentage usage
        cpu_percent = (total_cpu_usage / total_cpu_capacity) * 100 if total_cpu_capacity else 0
        memory_percent = (total_memory_usage / total_memory_capacity) * 100 if total_memory_capacity else 0

        cpu_percent = round(cpu_percent,2)
        memory_percent = round(memory_percent, 2)

        return {'cpu_usage': cpu_percent, 'memory_usage': memory_percent, 'cpu_total': total_cpu_capacity, 'memory_total': total_memory_capacity }
    
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch endpoint details: {e.reason}"}