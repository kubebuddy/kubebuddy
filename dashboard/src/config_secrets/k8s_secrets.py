from kubernetes import client, config
from datetime import datetime, timezone
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