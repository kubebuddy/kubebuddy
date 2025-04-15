from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException
from django.shortcuts import render
from datetime import datetime, timezone
from ..utils import calculateAge, filter_annotations, configure_k8s
import yaml

def get_namespace(path, context):
    try:
        configure_k8s(path, context)
        v1 = client.CoreV1Api()
        list_ns = []
        namespaces = v1.list_namespace()
        for ns in namespaces.items:
            list_ns.append(ns.metadata.name)
        return list_ns
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch ResourceQuota details: {e.reason}"}


def namespaces_data(path, context):
    # Load Kubernetes config
    configure_k8s(path, context)

    v1 = client.CoreV1Api()
    namespaces = v1.list_namespace().items

    namespace_data = []
    for ns in namespaces:
        name = ns.metadata.name
        status = ns.status.phase
        age = calculateAge(datetime.now(timezone.utc) - ns.metadata.creation_timestamp)
        labels = ns.metadata.labels

        namespace_data.append({
            "name": name,
            "status": status,
            "age": age,
            "labels": labels
        })

    return namespace_data

def get_namespace_description(path=None, context=None, namespace=None):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()

    try:
        # Fetch namespace details
        namespace = v1.read_namespace(name=namespace)

        namespace_info = {
            "name": namespace.metadata.name,
            "status": namespace.status.phase if namespace.status else "Unknown",
            "labels": list(namespace.metadata.labels.items()) if namespace.metadata.labels else [],
            "annotations": filter_annotations(namespace.metadata.annotations or {}),
            "resource_quota": namespace.status.resource_quota if hasattr(namespace.status, 'resource_quota') else None,
            "limit_range": namespace.status.limit_range if hasattr(namespace.status, 'limit_range') else "None",
        }

        return namespace_info

    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch namespace details: {e.reason}"}
    
def get_namespace_yaml(path, context, namespace_name):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    namespace = v1.read_namespace(name=namespace_name)
    # Filtering Annotations
    if namespace.metadata:
        namespace.metadata.annotations = filter_annotations(namespace.metadata.annotations or {})
    return yaml.dump(namespace.to_dict(), default_flow_style=False)

def get_namespace_details():
    try:
        config.load_incluster_config()
    except ConfigException:
        config.load_kube_config()

    v1 = client.CoreV1Api()
    namespaces = v1.list_namespace()

    def get_age(creation_timestamp):
        delta = datetime.now(timezone.utc) - creation_timestamp
        days = delta.days
        hours = delta.seconds // 3600
        return f"{days}d {hours}h" if days else f"{hours}h"

    namespace_details = []

    for namespace in namespaces.items:
        # Fetch pods for the current namespace
        pods = v1.list_namespaced_pod(namespace.metadata.name)
        
        for pod in pods.items:
            # Determine the pod's status
            status = pod.status.phase
            # Get container status
            container_statuses = pod.status.container_statuses or []
            ready_count = sum(1 for cs in container_statuses if cs.ready)
            total_count = len(container_statuses)
            
            # Create the details for the namespace row
            pod_info = {
                'namespace': namespace.metadata.name,
                'name': pod.metadata.name,
                'containers': f"{ready_count}/{total_count}",
                'node': pod.spec.node_name if pod.spec.node_name else 'N/A',
                'ip_address': pod.status.pod_ip or 'N/A',
                'restarts': sum([cs.restart_count for cs in container_statuses]),
                'age': get_age(pod.metadata.creation_timestamp),
                'status': status
            }

            namespace_details.append(pod_info)

    return namespace_details