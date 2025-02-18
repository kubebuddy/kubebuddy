from kubernetes import client, config

def get_limit_ranges(path, context):
    # Load Kubernetes configuration
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    api = client.ApiextensionsV1Api()
    
    # Get all namespaces
    namespaces = [ns.metadata.name for ns in v1.list_namespace().items]
    
    limit_ranges = []
    
    # Iterate over all namespaces and get limit ranges
    for ns in namespaces:
        try:
            lr_list = client.CoreV1Api().list_namespaced_limit_range(ns).items
            for lr in lr_list:
                limit_ranges.append({
                    "namespace": ns,
                    "name": lr.metadata.name,
                    "created_at": lr.metadata.creation_timestamp
                })
        except Exception as e:
            print(f"Error fetching LimitRange for namespace {ns}: {e}")
    
    return limit_ranges, len(limit_ranges)