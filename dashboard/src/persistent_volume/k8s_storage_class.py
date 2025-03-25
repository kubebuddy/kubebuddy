from kubernetes import client, config
from datetime import datetime, timezone
from ..utils import calculateAge, filter_annotations
import yaml

def list_storage_classes(path: str, context: str):
    # Load Kubernetes config
    config.load_kube_config(path, context=context)
    
    v1 = client.StorageV1Api()
    storage_classes = v1.list_storage_class().items
    
    storage_data = []
    for sc in storage_classes:
        age = calculateAge(datetime.now(timezone.utc) - sc.metadata.creation_timestamp)
        if sc.metadata.annotations.get("storageclass.kubernetes.io/is-default-class") and sc.metadata.annotations.get("storageclass.kubernetes.io/is-default-class") == "true":
            is_default = "Yes"
        else:
            is_default = "-"
        storage_data.append({
            "name": sc.metadata.name,
            "provisioner": sc.provisioner,
            "reclaimPolicy": sc.reclaim_policy,
            "volumeBindingMode": sc.volume_binding_mode,
            "allowVolumeExpansion": sc.allow_volume_expansion,
            "age": age,
            "isDefault": is_default
        })
    
    return storage_data, len(storage_data)

def get_storage_class_description(path=None, context=None, sc_name=None):
    config.load_kube_config(path, context)
    v1 = client.StorageV1Api()

    try:
        sc = v1.read_storage_class(name=sc_name)
        
        if sc.metadata.annotations.get("storageclass.kubernetes.io/is-default-class") and sc.metadata.annotations.get("storageclass.kubernetes.io/is-default-class") == "true":
            is_default = "Yes"
        else:
            is_default = "No"

        return {
            'name': sc.metadata.name,
            'is_default_class': is_default,
            'annotations': filter_annotations(sc.metadata.annotations or {}),
            'provisioner': sc.provisioner,
            'parameters': sc.parameters,
            'allow_volume_expansion': sc.allow_volume_expansion,
            'mount_options': sc.mount_options,
            'reclaim_policy': sc.reclaim_policy,
            'volume_binding_mode': sc.volume_binding_mode,
        }
    
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch Storage Class details: {e.reason}"}
    
def get_storage_class_events(path, context, sc_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_event_for_all_namespaces().items
    sc_events = [
        event for event in events if event.involved_object.name == sc_name and event.involved_object.kind == "StorageClass"
    ]

    return "\n".join([f"{e.reason}: {e.message}" for e in sc_events])

def get_sc_yaml(path, context, sc_name):
    config.load_kube_config(path, context)
    v1 = client.StorageV1Api()
    try:
        sc = v1.read_storage_class(name=sc_name)
        # Filtering Annotations
        if sc.metadata:
            sc.metadata.annotations = filter_annotations(sc.metadata.annotations or {})
        return yaml.dump(sc.to_dict(), default_flow_style=False)
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch Storage Class details: {e.reason}"}