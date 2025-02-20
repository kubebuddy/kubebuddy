from kubernetes import client, config
from datetime import datetime, timezone
from ..utils import calculateAge
import yaml

def list_pvc(path: str, context: str):
    # Load Kubernetes configuration
    config.load_kube_config(path, context=context)
    
    v1 = client.CoreV1Api()
    pvcs = v1.list_persistent_volume_claim_for_all_namespaces().items
    
    pvc_list = []
    for pvc in pvcs:
        pvc_info = {
            "namespace": pvc.metadata.namespace,
            "name": pvc.metadata.name,
            "status": pvc.status.phase,
            "volume": pvc.spec.volume_name if pvc.spec.volume_name else "N/A",
            "capacity": pvc.status.capacity["storage"] if pvc.status.capacity else "N/A",
            "access_mode": ", ".join([mode for mode in pvc.spec.access_modes]) if pvc.spec.access_modes else "N/A",
            "storage_class": pvc.spec.storage_class_name if pvc.spec.storage_class_name else "N/A",
            "volume_attribute_class": pvc.spec.data_source.name if pvc.spec.data_source else "N/A",
            "volume_mode": pvc.spec.volume_mode if pvc.spec.volume_mode else "N/A",
            "age": calculateAge(datetime.now(timezone.utc) - pvc.metadata.creation_timestamp) if pvc.metadata.creation_timestamp else "N/A"
        }
        pvc_list.append(pvc_info)
    
    return pvc_list, len(pvc_list)

def get_pvc_description(path=None, context=None, namespace=None, pvc_name=None):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    pvc = v1.read_namespaced_persistent_volume_claim(name=pvc_name, namespace=namespace)

    pvc_info = {
        "Name": pvc.metadata.name,
        "Namespace": pvc.metadata.namespace,
        "StorageClass": pvc.spec.storage_class_name,
        "Status": pvc.status.phase,
        "Volume": pvc.spec.volume_name,
        "Labels": pvc.metadata.labels,
        "Annotations": pvc.metadata.annotations,
        "Finalizers": pvc.metadata.finalizers,
        "Capacity": pvc.spec.resources.requests.get("storage"),  # Get storage capacity
        "Access Modes": pvc.spec.access_modes,
        "VolumeMode": pvc.spec.volume_mode,
        "Used By": [],  # Initialize Used By list
    }

    # Find Pods using this PVC (Used By) -  This requires iterating through pods
    pods = v1.list_namespaced_pod(namespace=namespace).items
    for pod in pods:
        for volume in pod.spec.volumes:
            if volume.persistent_volume_claim and volume.persistent_volume_claim.claim_name == pvc_name:
                pvc_info["Used By"].append(pod.metadata.name)
    pvc_info["Used By"] = ", ".join(pvc_info["Used By"]) if pvc_info["Used By"] else "N/A" # Format Used By

    return pvc_info

def get_pvc_events(path, context, namespace, pvc_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    pvc_events = [
        event for event in events if event.involved_object.name == pvc_name and event.involved_object.kind == "PersistentVolumeClaim"
    ]
    return "\n".join([f"{e.reason}: {e.message}" for e in pvc_events])

def get_pvc_yaml(path, context, namespace, pvc_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    pvc = v1.read_namespaced_persistent_volume_claim(name=pvc_name, namespace=namespace)
    return yaml.dump(pvc.to_dict(), default_flow_style=False)