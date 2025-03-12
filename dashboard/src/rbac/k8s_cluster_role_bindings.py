from kubernetes import client, config
from datetime import datetime, timedelta, timezone
from ..utils import calculateAge
import yaml

def get_cluster_role_bindings(path, context):
    config.load_kube_config(path, context)
    rbac_api = client.RbacAuthorizationV1Api()
    clusterrolebindings = rbac_api.list_cluster_role_binding()

    bindings_data = []
    for binding in clusterrolebindings.items:
        role_ref = binding.role_ref
        subjects = binding.subjects or []  # Handle cases where subjects is None
        users = [s.name for s in subjects if s.kind == "User"]
        groups = [s.name for s in subjects if s.kind == "Group"]
        service_accounts = [
            f"{s.namespace}/{s.name}" for s in subjects if s.kind == "ServiceAccount"
        ]

        # Calculate age
        creation_timestamp = binding.metadata.creation_timestamp
        if creation_timestamp:
            age = calculateAge(datetime.now(timezone.utc) - creation_timestamp)
        else:
            age = "Unknown"

        bindings_data.append({
            "name": binding.metadata.name,
            "role": role_ref.name,
            "users": users,
            "groups": groups,
            "service_accounts": service_accounts,
            "age": age
        })

    return bindings_data, len(bindings_data)

def get_cluster_role_binding_description(path=None, context=None, cluster_role_binding=None):
    config.load_kube_config(path, context)
    v1 = client.RbacAuthorizationV1Api()

    try:
        cluster_role_binding = v1.read_cluster_role_binding(name=cluster_role_binding)
        subjects = [{
                'kind': r.kind,
                'name': r.name,
                'namespace': r.namespace
            } for r in cluster_role_binding.subjects or []]
        
        return {
            'name': cluster_role_binding.metadata.name,
            'labels': cluster_role_binding.metadata.labels,
            'annotations': cluster_role_binding.metadata.annotations,
            'role': {
                'kind': cluster_role_binding.role_ref.kind,
                'name': cluster_role_binding.role_ref.name
            },
            'subjects': subjects
        }
    
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch role_binding details: {e.reason}"}
    
def get_cluster_role_binding_events(path, context, cluster_role_binding):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_event_for_all_namespaces().items
    cluster_role_binding_events = [
        event for event in events if event.involved_object.name == cluster_role_binding and event.involved_object.kind == "ClusterRoleBinding"
    ]

    return "\n".join([f"{e.reason}: {e.message}" for e in cluster_role_binding_events])

def get_cluster_role_binding_yaml(path, context, cluster_role_binding):
    config.load_kube_config(path, context)
    v1 = client.RbacAuthorizationV1Api()
    try:
        cluster_role_binding = v1.read_cluster_role_binding(name=cluster_role_binding)

        return yaml.dump(cluster_role_binding.to_dict(), default_flow_style=False)
    
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch role_binding details: {e.reason}"}