from kubernetes import client, config
from datetime import datetime, timezone
from ..utils import calculateAge

def list_storage_classes(path: str, context: str):
    # Load Kubernetes config
    config.load_kube_config(path, context=context)
    
    v1 = client.StorageV1Api()
    storage_classes = v1.list_storage_class().items
    
    storage_data = []
    for sc in storage_classes:
        age = calculateAge(datetime.now(timezone.utc) - sc.metadata.creation_timestamp)
        storage_data.append({
            "name": sc.metadata.name,
            "provisioner": sc.provisioner,
            "reclaimPolicy": sc.reclaim_policy,
            "volumeBindingMode": sc.volume_binding_mode,
            "allowVolumeExpansion": sc.allow_volume_expansion,
            "age": age
        })
    
    return storage_data