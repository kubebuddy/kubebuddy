from kubernetes import config, client
from kubernetes.client.rest import ApiException

def get_pod_metrics(path=None, context=None):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    metrics_api = client.CustomObjectsApi()

    try:
        # Check if metrics API is available
        try:
            # Try to access metrics API
            metrics_api.get_api_resources(group="metrics.k8s.io", version="v1beta1")
        except ApiException:
            # Metrics API not available
            return {"error": "Metrics API not available"}, 0, False
        
        all_namespaces = v1.list_namespace().items
        all_pod_metrics = []
        metrics_available = True

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
                            cpu_str = container['usage']['cpu']
                            memory_str = container['usage']['memory']

                            if cpu_str.endswith('n'):
                                total_cpu_usage_nano += int(cpu_str.replace('n', ''))
                            elif cpu_str.endswith('m'):
                                total_cpu_usage_nano += int(cpu_str.replace('m', '')) * 1000000

                            if memory_str.endswith('Ki'):
                                total_memory_usage_bytes += int(memory_str.replace('Ki', '')) * 1024
                            elif memory_str.endswith('Mi'):
                                total_memory_usage_bytes += int(memory_str.replace('Mi', '')) * 1024 * 1024
                            elif memory_str.endswith('Gi'):
                                total_memory_usage_bytes += int(memory_str.replace('Gi','')) * 1024 * 1024 * 1024
                            elif memory_str.endswith('Ti'):
                                total_memory_usage_bytes += int(memory_str.replace('Ti','')) * 1024 * 1024 * 1024 * 1024
                            elif memory_str.endswith('Pi'):
                                total_memory_usage_bytes += int(memory_str.replace('Pi','')) * 1024 * 1024 * 1024 * 1024 * 1024
                            elif memory_str.endswith('Ei'):
                                total_memory_usage_bytes += int(memory_str.replace('Ei','')) * 1024 * 1024 * 1024 * 1024 * 1024 * 1024
                            elif memory_str.endswith('B'):
                                total_memory_usage_bytes += int(memory_str.replace('B',''))

                        cpu_usage_milli = int(total_cpu_usage_nano / 1000000)
                        memory_usage_mi = round(total_memory_usage_bytes / (1024 * 1024), 2)

                        all_pod_metrics.append({
                            "name": pod_name,
                            "namespace": namespace,
                            "cpu_usage_milli": cpu_usage_milli,
                            "memory_usage_mi": memory_usage_mi,
                            'error': '-'
                        })

                    except ApiException as e:
                        print(f"Error fetching metrics for pod {pod_name} in namespace {namespace}: {e}")
                        all_pod_metrics.append({
                            "name": pod_name,
                            "namespace": namespace,
                            "error": f"Failed to fetch metrics: {e.reason}"
                        })
                        metrics_available = False

            except ApiException as e:
                print(f"Error fetching pods in namespace {namespace}: {e}")

        return all_pod_metrics, len(all_pod_metrics), metrics_available

    except ApiException as e:
        return {"error": f"Failed to fetch namespace list: {e.reason}"}, 0, False