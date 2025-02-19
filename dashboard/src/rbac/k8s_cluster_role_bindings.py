from kubernetes import client, config
from datetime import datetime, timedelta, timezone
from ..utils import calculateAge

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