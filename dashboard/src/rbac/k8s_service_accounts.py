from kubernetes import client, config
from datetime import datetime, timezone

def get_service_accounts(path, context):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    namespaces = v1.list_namespace()
    all_service_accounts = []

    for namespace in namespaces.items:
        namespace_name = namespace.metadata.name
        service_accounts = v1.list_namespaced_service_account(namespace=namespace_name)
        for sa in service_accounts.items:
            secrets = [secret.name for secret in sa.secrets] if sa.secrets else []
            creation_timestamp = sa.metadata.creation_timestamp

            if creation_timestamp:
                now = datetime.now(timezone.utc)
                age = now - creation_timestamp
                days = age.days
                hours, remainder = divmod(age.seconds, 3600)
                minutes, seconds = divmod(remainder, 60)

                age_str = ""
                if days > 0:
                    age_str += f"{days}d "
                if hours > 0:
                    age_str += f"{hours}h "
                if minutes > 0:
                    age_str += f"{minutes}m "
                age_str += f"{seconds}s"
            else:
                age_str = "Unknown"

            all_service_accounts.append({
                "namespace": namespace_name,
                "name": sa.metadata.name,
                "secrets": secrets,
                "age": age_str  # Store the calculated age string
            })

    return all_service_accounts