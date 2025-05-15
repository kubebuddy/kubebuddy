from kubernetes import config, client
from kubebuddy.appLogs import logger
from kubernetes.client.rest import ApiException
from ..utils import configure_k8s
from kubernetes.config.config_exception import ConfigException

def get_node_metrics(path=None, context=None):
    configure_k8s(path, context)
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
                logger.error(f"Error fetching metrics for node {node_name}: {e}")
                node_metrics.append({
                    "name": node_name,
                    "error": f"Failed to fetch metrics: {e.reason}"
                })
                metrics_available = False

        return node_metrics, total_nodes, metrics_available

    except ApiException as e:
        return {"error": f"Failed to fetch node list: {e.reason}"}, 0, False


def get_cluster_metrics(config_path, context_name):
    try:
        config.load_kube_config(config_file=config_path, context=context_name)
        api = client.CustomObjectsApi()

        # Fetch metrics from Metrics Server
        node_metrics = api.list_cluster_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            plural="nodes"
        )

        def parse_cpu(cpu_value):
            if cpu_value.endswith('n'):
                return int(cpu_value.strip('n')) / 1_000_000  # nanocores to millicores
            elif cpu_value.endswith('m'):
                return int(cpu_value.strip('m'))  # already in millicores
            else:
                return int(cpu_value) * 1000  # cores to millicores

        def parse_memory(mem_value):
            try:
                if mem_value.endswith('Ki'):
                    return int(mem_value.strip('Ki')) / 1024 / 1024  # Ki to Gi
                elif mem_value.endswith('Mi'):
                    return int(mem_value.strip('Mi')) / 1024  # Mi to Gi
                elif mem_value.endswith('Gi'):
                    return float(mem_value.strip('Gi'))  # already in Gi
                elif mem_value.endswith('Ti'):
                    return float(mem_value.strip('Ti')) * 1024  # Ti to Gi
                else:
                    return int(mem_value) / 1024 / 1024  # fallback: assume Ki
            except Exception:
                return 0

        total_cpu = 0
        total_memory = 0
        cpu_usage = 0
        memory_usage = 0

        for node in node_metrics.get('items', []):
            usage = node['usage']
            cpu = usage['cpu']      # e.g., '146162782n' or '350m'
            mem = usage['memory']   # e.g., '123456Ki'
            cpu_usage += parse_cpu(cpu)
            memory_usage += parse_memory(mem)

        # Now, get actual total allocatable capacity
        v1 = client.CoreV1Api()
        nodes = v1.list_node().items

        for node in nodes:
            alloc_cpu = node.status.allocatable['cpu']
            alloc_mem = node.status.allocatable['memory']
            total_cpu += parse_cpu(alloc_cpu)
            total_memory += parse_memory(alloc_mem)

        cpu_percentage = round((cpu_usage / total_cpu) * 100, 2) if total_cpu else 0
        memory_percentage = round((memory_usage / total_memory) * 100, 2) if total_memory else 0

        return {
            "cpu_usage": cpu_percentage,
            "memory_usage": memory_percentage,
            "cpu_total": round(total_cpu / 1000, 2),  # millicores to cores
            "memory_total": round(total_memory, 2)    # in Gi
        }

    except ConfigException as ce:
        return {"error": str(ce)}
    except Exception as e:
        return {"error": str(e)}

