from kubernetes import config, client
from kubernetes.client.rest import ApiException

def get_node_metrics(path=None, context=None):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    metrics_api = client.CustomObjectsApi()

    try:
        nodes = v1.list_node().items
        node_metrics = []
        total_nodes = len(nodes)
        metrics_available = True
        
        # Check if metrics API is available
        try:
            # Try to access metrics API
            metrics_api.get_api_resources(group="metrics.k8s.io", version="v1beta1")
        except ApiException:
            # Metrics API not available
            return {"error": "Metrics API not available"}, 0, False
            
        for node in nodes:
            node_name = node.metadata.name
            try:
                metrics = metrics_api.get_cluster_custom_object(
                    group="metrics.k8s.io",
                    version="v1beta1",
                    name=node_name,
                    plural="nodes",
                )

                cpu_usage_nano = int(metrics['usage']['cpu'].replace('n', ''))
                memory_usage_bytes = int(metrics['usage']['memory'].replace('Ki', '')) * 1024  # convert Ki to bytes

                # Get node capacity for CPU and memory to calculate percentages
                node_capacity = node.status.capacity
                cpu_capacity_cores = int(node_capacity['cpu'])
                memory_capacity_bytes = int(node_capacity['memory'].replace('Ki', '')) * 1024

                cpu_usage_percentage = (cpu_usage_nano / (cpu_capacity_cores * 1e9)) * 100
                memory_usage_percentage = (memory_usage_bytes / memory_capacity_bytes) * 100

                # Convert memory bytes to Mi
                memory_capacity_mi = memory_capacity_bytes / (1024 * 1024)
                node_metrics.append({
                    "name": node_name,
                    "cpu_cores": cpu_capacity_cores,
                    "cpu_usage_percentage": round(cpu_usage_percentage, 2),
                    "memory_mi": round(memory_capacity_mi,2),
                    "memory_usage_percentage": round(memory_usage_percentage, 2)
                })

            except ApiException as e:
                print(f"Error fetching metrics for node {node_name}: {e}")
                node_metrics.append({
                    "name": node_name,
                    "error": f"Failed to fetch metrics: {e.reason}"
                })
                metrics_available = False

        return node_metrics, total_nodes, metrics_available

    except ApiException as e:
        return {"error": f"Failed to fetch node list: {e.reason}"}, 0, False