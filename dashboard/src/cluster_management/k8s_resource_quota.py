from kubernetes import client, config
from datetime import datetime, timezone
from kubebuddy.appLogs import logger
import yaml
from ..utils import calculateAge, filter_annotations

def get_resource_quotas(path, context, namespace="all"):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    
    try:
        quotas = v1.list_resource_quota_for_all_namespaces() if namespace == "all" else v1.list_namespaced_resource_quota(namespace=namespace)
        quota_list = []
        
        for quota in quotas.items:
            created_at = quota.metadata.creation_timestamp
            age = calculateAge(datetime.now(timezone.utc) - created_at)
            
            hard_limits = quota.status.hard if quota.status.hard else {}
            used_resources = quota.status.used if quota.status.used else {}
            
            requests = []
            limits = []
            pods = ""
            
            for resource, hard_value in hard_limits.items():
                used_value = used_resources.get(resource, "0")
                if "requests" in resource:
                    requests.append(f"{resource}: {used_value}/{hard_value}")
                elif "limits" in resource:
                    limits.append(f"{resource}: {used_value}/{hard_value}")
                elif resource == "pods":
                    pods = f"pods: {used_value}/{hard_value}"
            
            quota_list.append({
                "namespace": quota.metadata.namespace,
                "name": quota.metadata.name,
                "age": age,
                "requests": ", ".join(requests),
                "limits": ", ".join(limits),
                "pods": pods
            })
        
        return quota_list, len(quota_list)
    
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch ResourceQuotas: {e.reason}"}, 0
    

def get_resourcequota_description(path=None, context=None, namespace=None, resourcequota_name=None):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    try:
        resource_quotas = v1.list_namespaced_resource_quota(namespace=namespace).items

        target_resource_quota = next((rq for rq in resource_quotas if rq.metadata.name == resourcequota_name), None)
        if target_resource_quota is None:
            return {"error": f"ResourceQuota {resourcequota_name} not found in namespace {namespace}"}
        
        hard_limits = target_resource_quota.spec.hard if target_resource_quota.spec.hard else {}
        used_resources = target_resource_quota.status.used if target_resource_quota.status.used else {}

        resourcequota_info = {
            "name": target_resource_quota.metadata.name,
            "namespace": target_resource_quota.metadata.namespace,
            "resources": []
        }

        for resource, value in hard_limits.items():
            resourcequota_info["resources"].append({
                "resource": resource,
                "used": used_resources.get(resource, "0"),
                "hard": value
            })
        return resourcequota_info
    
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch ResourceQuota details: {e.reason}"}

def get_resourcequota_events(path, context, namespace, resourcequota_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    resourcequota_events = [
        event for event in events if event.involved_object.name == resourcequota_name and event.involved_object.kind == "ResourceQuota"
    ]
    return "\n".join([f"{e.reason}: {e.message}" for e in resourcequota_events])

def get_resourcequota_yaml(path, context, namespace, resourcequota_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    resource_quotas = v1.read_namespaced_resource_quota(resourcequota_name, namespace=namespace)
    # Filtering Annotations
    if resource_quotas.metadata:
        resource_quotas.metadata.annotations = filter_annotations(resource_quotas.metadata.annotations or {})
    return yaml.dump(resource_quotas.to_dict(), default_flow_style=False)