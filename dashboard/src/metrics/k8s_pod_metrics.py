from kubernetes import config, client
from kubernetes.client.rest import ApiException

def get_pod_metrics(path=None, context=None):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    metrics_api = client.CustomObjectsApi()

    try:
        all_namespaces = v1.list_namespace().items
        all_pod_metrics = []

        for namespace_obj in all_namespaces:
            namespace = namespace_obj.metadata.name
            try:
                pods = v1.list_namespaced_pod(namespace=namespace).items
                for pod in pods:
                    pod_name = pod.metadata.name
                    try:
                        metrics = metrics_api.get_namespaced_custom_object(
                            group="metrics.k8s.io",
                            version="v1beta1",
                            name=pod_name,
                            plural="pods",
                            namespace=namespace,
                        )

                        total_cpu_usage_nano = 0
                        total_memory_usage_bytes = 0

                        for container in metrics['containers']:
                            total_cpu_usage_nano += int(container['usage']['cpu'].replace('n', ''))
                            total_memory_usage_bytes += int(container['usage']['memory'].replace('Ki', '')) * 1024

                        all_pod_metrics.append({
                            "name": pod_name,
                            "namespace": namespace,
                            "cpu_usage_nano": total_cpu_usage_nano,
                            "memory_usage_bytes": total_memory_usage_bytes,
                            'total_pods': len(pod_name),
                            'error': 'N/A'
                        })

                    except ApiException as e:
                        print(f"Error fetching metrics for pod {pod_name} in namespace {namespace}: {e}")
                        all_pod_metrics.append({
                            "name": pod_name,
                            "namespace": namespace,
                            "error": f"Failed to fetch metrics: {e.reason}"
                        })

            except ApiException as e:
                print(f"Error fetching pods in namespace {namespace}: {e}")

        return all_pod_metrics

    except ApiException as e:
        return {"error": f"Failed to fetch namespace list: {e.reason}"}