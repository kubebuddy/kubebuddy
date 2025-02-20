from kubernetes import client, config
import yaml 

def get_cluster_role(path, context):
    config.load_kube_config(path, context=context)
    rbac_api = client.RbacAuthorizationV1Api()

    clusterroles = []
    response = rbac_api.list_cluster_role()

    for role in response.items:
        creation_timestamp = role.metadata.creation_timestamp
        if creation_timestamp:
            #Convert to local time and format
            creation_time_str = creation_timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        else:
            creation_time_str = "Unknown"

        clusterroles.append({
            "name": role.metadata.name,
            "created_at": creation_time_str
    })
    return clusterroles, len(clusterroles)

def get_cluster_role_description(path=None, context=None, cluster_role_name=None):
    config.load_kube_config(path, context)
    v1 = client.RbacAuthorizationV1Api()

    try:
        cluster_role = v1.read_cluster_role(name=cluster_role_name)
        policy_rule = [{
                'resources': r.resources,
                'non_resource_urls': r.non_resource_ur_ls,
                'resource_names': r.resource_names,
                'verbs': r.verbs
            } for r in cluster_role.rules]
        
        return {
            'name': cluster_role.metadata.name,
            'labels': cluster_role.metadata.labels,
            'annotations': cluster_role.metadata.annotations,
            'policy_rule': policy_rule
        }
    
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch Role details: {e.reason}"}
    
def get_cluster_role_events(path, context, cluster_role_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_event_for_all_namespaces().items
    cluster_role_events = [
        event for event in events if event.involved_object.name == cluster_role_name and event.involved_object.kind == "ClusterRole"
    ]

    return "\n".join([f"{e.reason}: {e.message}" for e in cluster_role_events])

def get_cluster_role_yaml(path, context, cluster_role_name):
    config.load_kube_config(path, context)
    v1 = client.RbacAuthorizationV1Api()
    try:
        cluster_role = v1.read_cluster_role(name=cluster_role_name)

        return yaml.dump(cluster_role.to_dict(), default_flow_style=False)
    
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch cluster_role details: {e.reason}"}