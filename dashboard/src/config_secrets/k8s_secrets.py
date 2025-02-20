from kubernetes import client, config
from datetime import datetime, timezone
import yaml
import base64
from ..utils import calculateAge

def list_secrets(path, context):
    # Load the kubeconfig file with the specified path and context
    config.load_kube_config(config_file=path, context=context)
    
    v1 = client.CoreV1Api()
    secrets = v1.list_secret_for_all_namespaces()

    secret_list = []
    for secret in secrets.items:
        # Calculate age of the secret
        now = datetime.now(timezone.utc)
        age = now - secret.metadata.creation_timestamp
        data = len(secret.data)
        # Prepare secret data
        secret_data = {
            "name": secret.metadata.name,
            "namespace": secret.metadata.namespace,
            "type": secret.type,
            "data": data,
            "age": calculateAge(age)
        }
        secret_list.append(secret_data)
    
    return secret_list, len(secret_list)




def get_secret_description(path=None, context=None, namespace=None, secret_name=None):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    try:
        secrets = v1.list_namespaced_secret(namespace=namespace).items

        target_secret = None
        for secret in secrets:
            if secret.metadata.name == secret_name:
                target_secret = secret
                break

        if target_secret is None:
            return {"error": f"Secret {secret_name} not found in namespace {namespace}"}

        secret_info = {
            "name": target_secret.metadata.name,
            "namespace": target_secret.metadata.namespace,
            "type": target_secret.type, # Include type
            "data": {k: base64.b64decode(v).decode('utf-8') for k, v in target_secret.data.items()} if target_secret.data else {}, # Decode base64 and handle missing data
        }
        return secret_info

    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch Secret details: {e.reason}"}

def get_secret_events(path, context, namespace, secret_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    secret_events = [
        event for event in events if event.involved_object.name == secret_name and event.involved_object.kind == "Secret"
    ]
    return "\n".join([f"{e.reason}: {e.message}" for e in secret_events])

def get_secret_yaml(path, context, namespace, secret_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    secrets = v1.list_namespaced_secret(namespace=namespace).items

    target_secret = None
    for secret in secrets:
        if secret.metadata.name == secret_name:
            target_secret = secret
            break

    if target_secret is None:
        return {"error": f"Secret {secret_name} not found in namespace {namespace}"}
    return yaml.dump(target_secret.to_dict(), default_flow_style=False)