from kubernetes import client, config
from datetime import datetime
def get_endpoints(path, context):
    # Load kube config with specific path and context
    config.load_kube_config(path, context=context)
    
    # Initialize the Kubernetes API client
    v1 = client.CoreV1Api()
    
    # Get all namespaces
    namespaces = v1.list_namespace()
    
    endpoint_data = []
    
    for ns in namespaces.items:
        namespace = ns.metadata.name
        
        # Get all endpoints in the namespace
        endpoints = v1.list_namespaced_endpoints(namespace)
        for ep in endpoints.items:
            endpoint_info = {
                'namespace': namespace,
                'name': ep.metadata.name,
                'endpoints': [subset.addresses[0].ip if subset.addresses else 'N/A' for subset in ep.subsets],
                'age': (datetime.now() - ep.metadata.creation_timestamp.replace(tzinfo=None)).days
            }
            endpoint_data.append(endpoint_info)
    
    return endpoint_data