from kubernetes import client, config
from datetime import datetime, timezone
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