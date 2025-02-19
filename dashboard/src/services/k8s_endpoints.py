from kubernetes import client, config
from datetime import datetime, timezone
import yaml
from ..utils import calculateAge

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
                        'endpoints': [subset.addresses[0].ip if subset.addresses else 'None' for subset in ep.subsets or []],
                        'age': calculateAge(datetime.now(timezone.utc) - ep.metadata.creation_timestamp) if ep.metadata.creation_timestamp else 'N/A'
                    }
                    endpoint_data.append(endpoint_info)
                except Exception as e:
                    print(f"Error processing endpoint '{ep.metadata.name}' in namespace '{namespace}': {e}")
        
        return endpoint_data
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []


def get_endpoint_description(path=None, context=None, namespace=None, endpoint_name=None):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    try:
        endpoints = v1.list_namespaced_endpoints(namespace=namespace).items  # THE CORRECT API CALL
        target_endpoint = None
        for endpoint in endpoints:
            if endpoint.metadata.name == endpoint_name:
                target_endpoint = endpoint
                break
        if target_endpoint is None:
            return {"error": f"Endpoint {endpoint_name} not found in namespace {namespace}"}
        endpoint_info = {
            "name": target_endpoint.metadata.name,
            "namespace": target_endpoint.metadata.namespace,
            "subsets": [
                {
                    "addresses": [
                        {"ip": address.ip, "hostname": getattr(address, "hostname", "N/A"), "target_ref": getattr(address, "target_ref", "N/A")}
                        for address in subset.addresses or []
                    ],
                    "ports": [
                        {"name": port.name, "port": port.port, "protocol": port.protocol}
                        for port in subset.ports or []
                    ],
                    "not_ready_addresses": [
                        {"ip": address.ip, "hostname": getattr(address, "hostname", "N/A"), "target_ref": getattr(address, "target_ref", "N/A")}
                        for address in subset.not_ready_addresses or []
                    ]
                }
                for subset in (target_endpoint.subsets if target_endpoint.subsets else [])
            ],
        }
        return endpoint_info
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch endpoint details: {e.reason}"}

def get_endpoint_events(path, context, namespace, endpoint_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    endpoint_events = [
        event for event in events if event.involved_object.name == endpoint_name and event.involved_object.kind == "Endpoints"
    ]
    return "\n".join([f"{e.reason}: {e.message}" for e in endpoint_events])


def get_endpoint_yaml(path, context, namespace, endpoint_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    try:
        endpoints = v1.list_namespaced_endpoints(namespace=namespace).items # Correct API call

        target_endpoint = None
        for endpoint in endpoints:
            if endpoint.metadata.name == endpoint_name:
                target_endpoint = endpoint
                break

        if target_endpoint is None:
            return {"error": f"Endpoint {endpoint_name} not found in namespace {namespace}"}

        return yaml.dump(target_endpoint.to_dict(), default_flow_style=False) # Use target_endpoint

    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch endpoint details: {e.reason}"}