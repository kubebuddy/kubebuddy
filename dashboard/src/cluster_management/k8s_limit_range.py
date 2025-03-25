from kubernetes import client, config
from kubebuddy.appLogs import logger
import yaml
from ..utils import filter_annotations

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
                    "created_at": lr.metadata.creation_timestamp.strftime("%Y-%m-%d %H:%M:%S")
                })
        except Exception as e:
            logger.error(f"Error fetching LimitRange for namespace {ns}: {e}")
    
    return limit_ranges, len(limit_ranges)



def get_limitrange_description(path=None, context=None, namespace=None, limitrange_name=None):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    try:
        limit_ranges = v1.list_namespaced_limit_range(namespace=namespace).items

        target_limit_range = None
        for lr in limit_ranges:
          if lr.metadata.name == limitrange_name:
            target_limit_range = lr
            break

        if target_limit_range is None:
          return {"error": f"LimitRange {limitrange_name} not found in namespace {namespace}"}

        limit_range_info = {
            "name": target_limit_range.metadata.name,
            "namespace": target_limit_range.metadata.namespace,
            "limits": [
                {
                    "type": limit.type,
                    "default": {k: v for k, v in limit.default.items()} if limit.default else {}, # Handle missing default
                    "default_request": {k: v for k, v in limit.default_request.items()} if limit.default_request else {}, # Handle missing default_request
                    "max": {k: v for k, v in limit.max.items()} if limit.max else {}, # Handle missing max
                    "min": {k: v for k, v in limit.min.items()} if limit.min else {}, # Handle missing min
                }
                for limit in target_limit_range.spec.limits
            ],
        }
        return limit_range_info

    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch LimitRange details: {e.reason}"}


def get_limitrange_events(path, context, namespace, limitrange_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    limitrange_events = [
        event for event in events if event.involved_object.name == limitrange_name and event.involved_object.kind == "LimitRange"
    ]
    return "\n".join([f"{e.reason}: {e.message}" for e in limitrange_events])

def get_limitrange_yaml(path, context, namespace, limitrange_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    limit_ranges = v1.read_namespaced_limit_range(limitrange_name, namespace=namespace)
    # Filtering Annotations
    if limit_ranges.metadata:
        limit_ranges.metadata.annotations = filter_annotations(limit_ranges.metadata.annotations or {})
    return yaml.dump(limit_ranges.to_dict(), default_flow_style=False)