from kubernetes import client, config
from datetime import datetime, timezone
import yaml

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

    return all_service_accounts, len(all_service_accounts)

def get_sa_description(path=None, context=None, namespace=None, sa_name=None):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()

    try:
        sa = v1.read_namespaced_service_account(name=sa_name, namespace=namespace)
        
        return {
            'name': sa.metadata.name,
            'namespace': sa.metadata.namespace,
            'labels': sa.metadata.labels,
            'annotations': sa.metadata.annotations,
            'image_pull_secrets': sa.image_pull_secrets,
            'mountable_secrets': sa.secrets,
            'tokens': "coudlnt find in api"
        }
    
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch Service Account details: {e.reason}"}
    
def get_sa_events(path, context, namespace, sa_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    sa_events = [
        event for event in events if event.involved_object.name == sa_name and event.involved_object.kind == "ServiceAccount"
    ]

    return "\n".join([f"{e.reason}: {e.message}" for e in sa_events])

def get_sa_yaml(path, context, namespace, sa_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    try:
        sa = v1.read_namespaced_service_account(name=sa_name, namespace=namespace)

        return yaml.dump(sa.to_dict(), default_flow_style=False)
    
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch Service Account details: {e.reason}"}