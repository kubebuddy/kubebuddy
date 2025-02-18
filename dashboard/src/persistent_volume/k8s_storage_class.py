from kubernetes import client, config
from datetime import datetime, timezone

def list_storage_classes(path: str, context: str):
    # Load Kubernetes config
    config.load_kube_config(path, context=context)
    
    v1 = client.StorageV1Api()
    storage_classes = v1.list_storage_class().items
    
    storage_data = []
    for sc in storage_classes:
        age = datetime.now(timezone.utc) - sc.metadata.creation_timestamp.replace(tzinfo=timezone.utc)
        storage_data.append({
            "name": sc.metadata.name,
            "provisioner": sc.provisioner,
            "reclaimPolicy": sc.reclaim_policy,
            "volumeBindingMode": sc.volume_binding_mode,
            "allowVolumeExpansion": sc.allow_volume_expansion,
            "age": f"{age.days}d {age.seconds // 3600}h"
        })
    
    return storage_data