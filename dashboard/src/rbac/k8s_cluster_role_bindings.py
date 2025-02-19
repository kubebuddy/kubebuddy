from kubernetes import client, config
from datetime import datetime

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
            age = datetime.timedelta(seconds=(datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc) - creation_timestamp).total_seconds())
            days = age.days
            hours, remainder = divmod(age.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            age_str = f"{days}d {hours}h {minutes}m {seconds}s"
        else:
            age_str = "Unknown"

        bindings_data.append({
            "name": binding.metadata.name,
            "role": role_ref.name,
            "users": users,
            "groups": groups,
            "service_accounts": service_accounts,
            "age": age_str
        })

    return bindings_data