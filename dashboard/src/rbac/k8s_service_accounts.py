from kubernetes import client, config
from datetime import datetime, timezone
from ..utils import calculateAge, filter_annotations
from kubebuddy.appLogs import logger
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
            secrets = len([secret.name for secret in sa.secrets]) if sa.secrets else 0

            age = calculateAge(datetime.now(timezone.utc) - sa.metadata.creation_timestamp)

            all_service_accounts.append({
                "namespace": namespace_name,
                "name": sa.metadata.name,
                "secrets": secrets,
                "age": age 
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
            'annotations': filter_annotations(sa.metadata.annotations or {}),
            'metadata': sa.metadata,
            'api_version': sa.api_version,
            'kind': sa.kind,
            'spec': sa.secrets,
            'status': sa.image_pull_secrets,
            'image_pull_secrets': sa.image_pull_secrets,
            'mountable_secrets': sa.secrets,
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
        # Filtering Annotations
        if sa.metadata:
            sa.metadata.annotations = filter_annotations(sa.metadata.annotations or {})
        return yaml.dump(sa.to_dict(), default_flow_style=False)
    
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch Service Account details: {e.reason}"}