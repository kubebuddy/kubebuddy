from kubernetes import client, config
from datetime import datetime
import yaml
from ..utils import filter_annotations

def list_roles(path, context):
    # Load kubeconfig using the provided path and context
    config.load_kube_config(path, context=context)

    # Initialize the Kubernetes API client for roles
    rbac_v1 = client.RbacAuthorizationV1Api()

    # List all namespaces
    namespaces = client.CoreV1Api().list_namespace()

    # Collect roles across all namespaces
    roles_data = []

    for namespace in namespaces.items:
        namespace_name = namespace.metadata.name
        roles = rbac_v1.list_namespaced_role(namespace_name)
        for role in roles.items:
            roles_data.append({
                "namespace": namespace_name,
                "name": role.metadata.name,
                "created_at": role.metadata.creation_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            })

    return roles_data, len(roles_data)

def get_role_description(path=None, context=None, namespace=None, role_name=None):
    config.load_kube_config(path, context)
    v1 = client.RbacAuthorizationV1Api()

    try:
        role = v1.read_namespaced_role(name=role_name, namespace=namespace)
      
        policy_rule = [{
                'resources': r.resources,
                'non_resource_urls': r.non_resource_ur_ls,
                'resource_names': r.resource_names,
                'verbs': r.verbs
            } for r in role.rules]
        
        return {
            'name': role.metadata.name,
            'labels': role.metadata.labels,
            'annotations': filter_annotations(role.metadata.annotations or {}),
            'policy_rule': policy_rule
        }
    
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch Role details: {e.reason}"}
    
def get_role_events(path, context, namespace, role_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    role_events = [
        event for event in events if event.involved_object.name == role_name and event.involved_object.kind == "Role"
    ]

    return "\n".join([f"{e.reason}: {e.message}" for e in role_events])

def get_role_yaml(path, context, namespace, role_name):
    config.load_kube_config(path, context)
    v1 = client.RbacAuthorizationV1Api()
    try:
        role = v1.read_namespaced_role(name=role_name, namespace=namespace)
        # Filtering Annotations
        if role.metadata:
            role.metadata.annotations = filter_annotations(role.metadata.annotations or {})
        return yaml.dump(role.to_dict(), default_flow_style=False)
    
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch Role details: {e.reason}"}