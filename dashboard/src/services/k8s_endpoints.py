from kubernetes import client, config
from datetime import datetime, timezone
import yaml
from kubebuddy.appLogs import logger
from ..utils import calculateAge, filter_annotations

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
            logger.error(f"Error fetching namespaces: {e}")
            return []
        
        endpoint_data = []
        
        for ns in namespaces.items:
            namespace = ns.metadata.name
            
            # Get all endpoints in the namespace
            try:
                endpoints = v1.list_namespaced_endpoints(namespace)
            except Exception as e:
                logger.error(f"Error fetching endpoints for namespace '{namespace}': {e}")
                continue  # Skip to the next namespace
            
            for ep in endpoints.items:
                try:
                    # Extract IP addresses with associated ports
                    ip_port_pairs = []
                    for subset in ep.subsets or []:
                        if subset.addresses:
                            for addr in subset.addresses:
                                if subset.ports:
                                    for port in subset.ports:
                                        ip_port_pairs.append(f"{addr.ip}:{port.port}")
                                else:
                                    ip_port_pairs.append(addr.ip)

                    endpoint_info = {
                        'namespace': namespace,
                        'name': ep.metadata.name,
                        'endpoints': ip_port_pairs if ip_port_pairs else ['None'],
                        'age': calculateAge(datetime.now(timezone.utc) - ep.metadata.creation_timestamp) if ep.metadata.creation_timestamp else 'N/A'
                    }
                    endpoint_data.append(endpoint_info)
                except Exception as e:
                    logger.error(f"Error processing endpoint '{ep.metadata.name}' in namespace '{namespace}': {e}")
        
        return endpoint_data
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return []


def get_endpoint_description(path=None, context=None, namespace=None, endpoint_name=None):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    try:
        target_endpoint = v1.read_namespaced_endpoints(endpoint_name, namespace=namespace)
        endpoint_info = {
            "name": target_endpoint.metadata.name,
            "namespace": target_endpoint.metadata.namespace,
            "labels": target_endpoint.metadata.labels,
            "annotations": filter_annotations(target_endpoint.metadata.annotations or {}),
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
    endpoints = v1.read_namespaced_endpoints(endpoint_name, namespace=namespace)
    # Filtering Annotations
    if endpoints.metadata:
        endpoints.metadata.annotations = filter_annotations(endpoints.metadata.annotations or {})
    return yaml.dump(endpoints.to_dict(), default_flow_style=False)