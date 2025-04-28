from kubernetes import client, config
from kubebuddy.appLogs import logger
import yaml
from ..utils import filter_annotations, configure_k8s

def get_limit_ranges(path, context):
    # Load Kubernetes configuration
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    
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
                    "created_at": lr.metadata.creation_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                })
        except Exception as e:
            logger.error(f"Error fetching LimitRange for namespace {ns}: {e}")
    
    return limit_ranges, len(limit_ranges)



def get_limit_range_description(path=None, context=None, namespace=None, limit_range_name=None):
    try:
        configure_k8s(path, context)
        v1 = client.CoreV1Api()
        limit_range = v1.read_namespaced_limit_range(name=limit_range_name, namespace=namespace)
        
        limit_range_info = {
            "name": limit_range.metadata.name,
            "namespace": limit_range.metadata.namespace,
            "limits": []
        }
        
        for limit in limit_range.spec.limits:
            limit_details = {
                "type": limit.type,
                "resources": {}
            }
            
            # Define the resource types
            resource_types = ["memory", "cpu"]
            
            for resource_type in resource_types:
                limit_details["resources"][resource_type] = {
                    "min": getattr(limit, "min", {}).get(resource_type, None),
                    "max": getattr(limit, "max", {}).get(resource_type, None),
                    "default_request": getattr(limit, "default_request", {}).get(resource_type, None),
                    "default_limit": getattr(limit, "default", {}).get(resource_type, None),
                    "max_limit_request_ratio": limit.max_limit_request_ratio
                }
            
            limit_range_info["limits"].append(limit_details)
        return limit_range_info

    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch LimitRange details: {e.reason}"}


def get_limitrange_events(path, context, namespace, limitrange_name):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    limitrange_events = [
        event for event in events if event.involved_object.name == limitrange_name and event.involved_object.kind == "LimitRange"
    ]
    return "\n".join([f"{e.reason}: {e.message}" for e in limitrange_events])

def get_limitrange_yaml(path, context, namespace, limitrange_name):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    limit_ranges = v1.read_namespaced_limit_range(limitrange_name, namespace=namespace)
    # Filtering Annotations
    if limit_ranges.metadata:
        limit_ranges.metadata.annotations = filter_annotations(limit_ranges.metadata.annotations or {})
    return yaml.dump(limit_ranges.to_dict(), default_flow_style=False)