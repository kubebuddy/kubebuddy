from kubernetes import client, config
from kubernetes.client.rest import ApiException

def get_pod_metrics(path, context):
    metrics_data = []
    total_pods = 0

    try:
        # Load kubeconfig (this assumes you have a kubeconfig file)
        config.load_kube_config(config_file=path, context = context)

        # Access metrics from the Metrics API
        v1_metrics = client.MetricsV1beta1Api()
        pod_metrics = v1_metrics.list_pod_metrics_for_all_namespaces()

        for pod in pod_metrics.items:
            namespace = pod.metadata.namespace
            for container in pod.containers:
                pod_name = pod.metadata.name
                cpu_usage = container.usage.get('cpu', 'N/A')
                memory_usage = container.usage.get('memory', 'N/A')
                
                # Append data to the metrics list
                metrics_data.append({
                    'namespace': namespace,
                    'name': pod_name,
                    'cpu': cpu_usage,
                    'memory': memory_usage
                })

                total_pods += 1  # Increase pod count for each pod/instance

    except ApiException as e:
        print(f"An error occurred: {e}")
    
    print(metrics_data, total_pods)
    
    return metrics_data, total_pods