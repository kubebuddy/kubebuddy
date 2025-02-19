from kubernetes import client, config
from datetime import datetime
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
                "created_at": role.metadata.creation_timestamp
            })

    return roles_data, len(roles_data)