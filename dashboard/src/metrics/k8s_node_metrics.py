from kubernetes import config, client
from kubernetes.client.rest import ApiException
import requests
import json

def get_node_metrics(path=None, context=None):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    metrics_api = client.CustomObjectsApi()

    try:
        nodes = v1.list_node().items
        node_metrics = []
        total_nodes = len(nodes)
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
                memory_usage_bytes = int(metrics['usage']['memory'].replace('Ki', '')) * 1024 # convert Ki to bytes

                # Get node capacity for CPU and memory to calculate percentages
                node_capacity = node.status.capacity
                cpu_capacity_cores = int(node_capacity['cpu'])
                memory_capacity_bytes = int(node_capacity['memory'].replace('Ki', '')) * 1024

                cpu_usage_percentage = (cpu_usage_nano / (cpu_capacity_cores * 1e9)) * 100
                memory_usage_percentage = (memory_usage_bytes / memory_capacity_bytes) * 100

                node_metrics.append({
                    "name": node_name,
                    "cpu_cores": cpu_capacity_cores,
                    "cpu_usage_percentage": round(cpu_usage_percentage, 2),
                    "memory_bytes": memory_capacity_bytes,
                    "memory_usage_percentage": round(memory_usage_percentage, 2)
                })

            except ApiException as e:
                print(f"Error fetching metrics for node {node_name}: {e}")
                node_metrics.append({
                    "name": node_name,
                    "error": f"Failed to fetch metrics: {e.reason}"
                })

        return node_metrics, total_nodes

    except ApiException as e:
        return {"error": f"Failed to fetch node list: {e.reason}"}