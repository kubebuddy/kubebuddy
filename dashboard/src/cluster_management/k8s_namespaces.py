from kubernetes import client, config
from django.shortcuts import render
from datetime import datetime, timezone
from ..utils import calculateAge, filter_annotations
import yaml

def get_namespace(path, context):
    try:
        config.load_kube_config(path, context)
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
    config.load_kube_config(path, context)

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
    config.load_kube_config(path, context)
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
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    namespace = v1.read_namespace(name=namespace_name)
    # Filtering Annotations
    if namespace.metadata:
        namespace.metadata.annotations = filter_annotations(namespace.metadata.annotations or {})
    return yaml.dump(namespace.to_dict(), default_flow_style=False)