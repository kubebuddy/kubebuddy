from kubernetes import client, config
from datetime import datetime, timezone
from ..utils import calculateAge, filter_annotations
import yaml

def list_pvc(path: str, context: str):
    # Load Kubernetes configuration
    config.load_kube_config(path, context=context)
    
    v1 = client.CoreV1Api()
    pvcs = v1.list_persistent_volume_claim_for_all_namespaces().items
    
    pvc_list = []
    for pvc in pvcs:
        used_by = [] # list of pods using this pvc
        pods = v1.list_namespaced_pod(namespace=pvc.metadata.namespace)
        for pod in pods.items:
            for volume in pod.spec.volumes or []:
                if volume.persistent_volume_claim and volume.persistent_volume_claim.claim_name == pvc.metadata.name:
                    used_by.append(pod.metadata.name) # list of pods
        pvc_info = {
            "namespace": pvc.metadata.namespace,
            "name": pvc.metadata.name,
            "status": pvc.status.phase,
            "volume": pvc.spec.volume_name if pvc.spec.volume_name else "-",
            "capacity": pvc.status.capacity["storage"] if pvc.status.capacity else "-",
            "access_modes": ", ".join(
                "RWO" if mode == "ReadWriteOnce" else
                "ROX" if mode == "ReadOnlyMany" else
                "RWX" if mode == "ReadWriteMany" else
                "RWOP" if mode == "ReadWriteOncePod" else
                "Unknown"
                for mode in (pvc.spec.access_modes if pvc.spec.access_modes else "-")
            ),
            "storage_class": pvc.spec.storage_class_name if pvc.spec.storage_class_name else "-",
            "volume_mode": pvc.spec.volume_mode if pvc.spec.volume_mode else "-",
            "used_by": used_by,
            "age": calculateAge(datetime.now(timezone.utc) - pvc.metadata.creation_timestamp) if pvc.metadata.creation_timestamp else "-"
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
        "Annotations": filter_annotations(pvc.metadata.annotations or {}),
        "Finalizers": pvc.metadata.finalizers,
        "Capacity": pvc.spec.resources.requests.get("storage"),  # Get storage capacity
        "Access_Modes": pvc.spec.access_modes,
        "VolumeMode": pvc.spec.volume_mode,
        "Used_By": [],  # Initialize Used By list
    }

    # Find Pods using this PVC (Used By) -  This requires iterating through pods
    pods = v1.list_namespaced_pod(namespace=namespace).items
    for pod in pods:
        for volume in pod.spec.volumes:
            if volume.persistent_volume_claim and volume.persistent_volume_claim.claim_name == pvc_name:
                pvc_info["Used_By"].append(pod.metadata.name)
    pvc_info["Used_By"] = ", ".join(pvc_info["Used_By"]) if pvc_info["Used_By"] else "N/A" # Format Used By

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
    # Filtering Annotations
    if pvc.metadata:
        pvc.metadata.annotations = filter_annotations(pvc.metadata.annotations or {})
    return yaml.dump(pvc.to_dict(), default_flow_style=False)