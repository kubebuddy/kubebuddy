from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException
from django.shortcuts import render
from datetime import datetime, timezone
from ..utils import calculateAge, filter_annotations, configure_k8s
import yaml
import logging

logger = logging.getLogger(__name__)

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

def get_namespace_details(cluster_id=None, namespace=None):
    try:
        if cluster_id:
            from main.models import Cluster
            current_cluster = Cluster.objects.get(id=cluster_id)
            path = current_cluster.kube_config.path
            context_name = current_cluster.context_name
            config.load_kube_config(config_file=path, context=context_name)
        else:
            try:
                config.load_incluster_config()
            except ConfigException:
                config.load_kube_config()
    except Exception as e:
        logger.error(f"Error loading kubeconfig: {str(e)}")
        return {}

    v1 = client.CoreV1Api()

    try:
        namespaces = v1.list_namespace().items
    except Exception as e:
        logger.error(f"Error fetching namespaces: {str(e)}")
        return {}

    def get_age_data(creation_timestamp):
        delta = datetime.now(timezone.utc) - creation_timestamp
        days = delta.days
        hours = delta.seconds // 3600
        return {
            "age_str": f"{days}d {hours}h" if days else f"{hours}h",
            "age_seconds": delta.total_seconds()
        }

    all_ns = []
    active_ns = []
    inactive_ns = []

    for ns in namespaces:
        age_data = get_age_data(ns.metadata.creation_timestamp)
        item = {
            'name': ns.metadata.name,
            'status': ns.status.phase,
            'age': age_data["age_str"],
            'age_seconds': age_data["age_seconds"]
        }
        all_ns.append(item)
        if ns.status.phase == "Active":
            active_ns.append(item)
        else:
            inactive_ns.append(item)

    # Find oldest and newest by age_seconds
    if all_ns:
        oldest = max(all_ns, key=lambda x: x["age_seconds"])
        newest = min(all_ns, key=lambda x: x["age_seconds"])
        oldest_age = oldest["age"]
        newest_age = newest["age"]
    else:
        oldest_age = newest_age = "N/A"

    return {
        "all": all_ns,
        "active": active_ns,
        "not_active": inactive_ns,
        "oldest_age": oldest_age,
        "newest_age": newest_age,
        "total_namespaces": len(all_ns),
        "active_count": len(active_ns),
        "not_active_count": len(inactive_ns)
    }