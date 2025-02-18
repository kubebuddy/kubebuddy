from kubernetes import client, config
from datetime import datetime, timezone

def get_resource_quotas(path, context):
    # Load kubeconfig
    config.load_kube_config(path, context)
    
    # Create API client
    v1 = client.CoreV1Api()
    v1_quota = client.CustomObjectsApi()
    
    # Fetch all ResourceQuotas
    quotas = v1_quota.list_cluster_custom_object("v1", "resourcequotas")["items"]

    quota_list = []
    
    for quota in quotas:
        namespace = quota["metadata"]["namespace"]
        name = quota["metadata"]["name"]
        created_at = quota["metadata"]["creationTimestamp"]
        
        # Calculate Age
        created_time = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - created_time).days
        
        # Get requests and limits
        status = quota.get("status", {})
        requests = status.get("hard", {}).get("requests.cpu", "N/A")
        limits = status.get("hard", {}).get("limits.cpu", "N/A")
        
        quota_list.append({
            "namespace": namespace,
            "name": name,
            "requests": requests,
            "limits": limits,
            "age": f"{age} days"
        })
    
    return quota_list