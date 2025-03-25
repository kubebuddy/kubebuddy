from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubebuddy.appLogs import logger
from datetime import datetime, timezone
from ..utils import calculateAge, filter_annotations
import yaml

def list_rolebindings(path, context):
    # Load kube config with the provided path and context
    config.load_kube_config(path, context=context)
    
    v1 = client.RbacAuthorizationV1Api()

    rolebindings_data = []

    try:
        # List rolebindings across all namespaces
        rolebindings = v1.list_role_binding_for_all_namespaces()

        for rb in rolebindings.items:
            namespace = rb.metadata.namespace
            name = rb.metadata.name
            role_ref = rb.role_ref.name
            users = []
            groups = []
            service_accounts = []

            # Extract subjects (users, groups, service accounts) from rolebinding
            for subject in rb.subjects:
                if subject.kind == 'User':
                    users.append(subject.name)
                elif subject.kind == 'Group':
                    groups.append(subject.name)
                elif subject.kind == 'ServiceAccount':
                    service_accounts.append(subject.name)

            # Calculate the age of the rolebinding
            creation_time = rb.metadata.creation_timestamp
            age = calculateAge(datetime.now(timezone.utc) - creation_time)

            rolebindings_data.append({
                'namespace': namespace,
                'name': name,
                'role': role_ref,
                'users': ', '.join(users),
                'groups': ', '.join(groups),
                'service_accounts': ', '.join(service_accounts),
                'age': age
            })

    except ApiException as e:
        logger.error(f"Error listing role bindings: {e}")
    
    return rolebindings_data, len(rolebindings_data)

def get_role_binding_description(path=None, context=None, namespace=None, role_binding_name=None):
    config.load_kube_config(path, context)
    v1 = client.RbacAuthorizationV1Api()

    try:
        role_binding = v1.read_namespaced_role_binding(name=role_binding_name, namespace=namespace)
        
        subjects = [{
                'kind': r.kind,
                'name': r.name,
                'namespace': r.namespace
            } for r in role_binding.subjects]
        
        return {
            'name': role_binding.metadata.name,
            'labels': role_binding.metadata.labels,
            'annotations': filter_annotations(role_binding.metadata.annotations or {}),
            'role': {
                'kind': role_binding.role_ref.kind,
                'name': role_binding.role_ref.name
            },
            'subjects': subjects
        }
    
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch role_binding details: {e.reason}"}
    
def get_role_binding_events(path, context, namespace, role_binding_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    role_binding_events = [
        event for event in events if event.involved_object.name == role_binding_name and event.involved_object.kind == "RoleBinding"
    ]

    return "\n".join([f"{e.reason}: {e.message}" for e in role_binding_events])

def get_role_binding_yaml(path, context, namespace, role_binding_name):
    config.load_kube_config(path, context)
    v1 = client.RbacAuthorizationV1Api()
    try:
        role_binding = v1.read_namespaced_role_binding(name=role_binding_name, namespace=namespace)
        # Filtering Annotations
        if role_binding.metadata:
            role_binding.metadata.annotations = filter_annotations(role_binding.metadata.annotations or {})
        return yaml.dump(role_binding.to_dict(), default_flow_style=False)
    
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch role_binding details: {e.reason}"}