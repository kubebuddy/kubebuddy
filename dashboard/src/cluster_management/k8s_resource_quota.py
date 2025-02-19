from kubernetes import client, config
from datetime import datetime, timezone
import yaml
from ..utils import calculateAge

def get_resource_quotas(path, context, namespace="all"):
    # Load kubeconfig
    config.load_kube_config(path, context)
    
    # Create API client
    v1 = client.CoreV1Api()
    
    # Fetch all ResourceQuotas
    quotas = v1.list_resource_quota_for_all_namespaces() if namespace == "all" else v1.list_namespaced_resource_quota(naemspace=namespace)

    quota_list = []
    
    for quota in quotas.items:
        namespace = quota.metadata.namespace
        name = quota.metadata.name
        created_at = quota.metadata.creation_timestamp
        
        # Calculate Age
        age = calculateAge(datetime.now(timezone.utc) - created_at)
        
        # Get requests and limits
        status = quota.status
        if status.hard:
            if status.hard["requests.cpu"]:
                requests =  status.hard["requests.cpu"]
        
        if status.hard:
            if status.hard["limits.cpu"]:
                limits =  status.hard["limits.cpu"]
        

        # requests = status.get("hard", {}).get("requests.cpu", "N/A")
        # limits = status.get("hard", {}).get("limits.cpu", "N/A")
        
        quota_list.append({
            "namespace": namespace,
            "name": name,
            "requests": requests,
            "limits": limits,
            "age": age
        })
    
    return quota_list, len(quota_list)


def get_resourcequota_description(path=None, context=None, namespace=None, resourcequota_name=None):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    try:
        resource_quotas = v1.list_namespaced_resource_quota(namespace=namespace).items

        target_resource_quota = None
        for rq in resource_quotas:
            if rq.metadata.name == resourcequota_name:
                target_resource_quota = rq
                break

        if target_resource_quota is None:
            return {"error": f"ResourceQuota {resourcequota_name} not found in namespace {namespace}"}


        resourcequota_info = {
            "name": target_resource_quota.metadata.name,
            "namespace": target_resource_quota.metadata.namespace,
            "spec": {
                "hard": {k: v for k, v in target_resource_quota.spec.hard.items()}, # Handle missing hard
                "scopes": target_resource_quota.spec.scopes or [] # Handle missing scopes
            },
            "status": {
                "hard": {k: v for k, v in target_resource_quota.status.hard.items()}, # Handle missing hard
                "used": {k: v for k, v in target_resource_quota.status.used.items()}, # Handle missing used
            },
        }
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
    resource_quotas = v1.list_namespaced_resource_quota(namespace=namespace).items

    target_resource_quota = None
    for rq in resource_quotas:
      if rq.metadata.name == resourcequota_name:
        target_resource_quota = rq
        break

    if target_resource_quota is None:
      return {"error": f"ResourceQuota {resourcequota_name} not found in namespace {namespace}"}
    return yaml.dump(target_resource_quota.to_dict(), default_flow_style=False)