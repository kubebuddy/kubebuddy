from kubernetes import client, config
from datetime import datetime

def get_endpoints(path, context):
    try:
        # Load kube config with specific path and context
        config.load_kube_config(path, context=context)
        
        # Initialize the Kubernetes API client
        v1 = client.CoreV1Api()
        
        # Get all namespaces
        try:
            namespaces = v1.list_namespace()
        except Exception as e:
            print(f"Error fetching namespaces: {e}")
            return []
        
        endpoint_data = []
        
        for ns in namespaces.items:
            namespace = ns.metadata.name
            
            # Get all endpoints in the namespace
            try:
                endpoints = v1.list_namespaced_endpoints(namespace)
            except Exception as e:
                print(f"Error fetching endpoints for namespace '{namespace}': {e}")
                continue  # Skip to the next namespace
            
            for ep in endpoints.items:
                try:
                    endpoint_info = {
                        'namespace': namespace,
                        'name': ep.metadata.name,
                        'endpoints': [subset.addresses[0].ip if subset.addresses else 'N/A' for subset in ep.subsets],
                        'age': (datetime.now() - ep.metadata.creation_timestamp.replace(tzinfo=None)).days if ep.metadata.creation_timestamp else 'N/A'
                    }
                    endpoint_data.append(endpoint_info)
                except Exception as e:
                    print(f"Error processing endpoint '{ep.metadata.name}' in namespace '{namespace}': {e}")
        
        return endpoint_data
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []
