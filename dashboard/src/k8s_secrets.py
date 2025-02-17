from kubernetes import client, config
from datetime import datetime, timezone

def list_secrets(path, context):
    # Load the kubeconfig file with the specified path and context
    config.load_kube_config(config_file=path, context=context)
    
    v1 = client.CoreV1Api()
    secrets = v1.list_secret_for_all_namespaces(watch=False)
    print(f"Secrets: {secrets}")

    secret_list = []
    for secret in secrets.items:
        # Calculate age of the secret
        now = datetime.now(timezone.utc)
        age = now - secret.metadata.creation_timestamp

        # Prepare secret data
        secret_data = {
            "name": secret.metadata.name,
            "namespace": secret.metadata.namespace,
            "type": secret.type,
            "data": {key: 'REDACTED' for key in secret.data.keys()},
            "age": str(age)
        }
        secret_list.append(secret_data)
    
    return secret_list