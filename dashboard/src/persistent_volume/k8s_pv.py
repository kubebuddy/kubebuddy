from kubernetes import client, config
from datetime import datetime, timezone
from ..utils import calculateAge, filter_annotations, configure_k8s
import yaml

def list_persistent_volumes(path: str, context: str):
    # Load Kubernetes configuration
    configure_k8s(path, context)
    
    v1 = client.CoreV1Api()
    pv_list = v1.list_persistent_volume().items
    
    # Collect PV details
    pv_details = []
    for pv in pv_list:
        pv_details.append({
            "name": pv.metadata.name,
            "capacity": pv.spec.capacity["storage"],
            "access_modes": ", ".join(
                "RWO" if mode == "ReadWriteOnce" else
                "ROX" if mode == "ReadOnlyMany" else
                "RWX" if mode == "ReadWriteMany" else
                "RWOP" if mode == "ReadWriteOncePod" else
                "Unknown"
                for mode in pv.spec.access_modes
            ),
            "reclaim_policy": pv.spec.persistent_volume_reclaim_policy,
            "status": pv.status.phase,
            "claim": f"{pv.spec.claim_ref.namespace}/{pv.spec.claim_ref.name}" if pv.spec.claim_ref else "-",
            "storage_class": pv.spec.storage_class_name if pv.spec.storage_class_name != None else "-",
            "volume_mode":getattr(pv.spec, 'volume_mode', '-'),
            "age": calculateAge(datetime.now(timezone.utc) -  pv.metadata.creation_timestamp),
            "namespace": pv.spec.claim_ref.namespace if pv.spec.claim_ref else "",
            "claim_name": pv.spec.claim_ref.name if pv.spec.claim_ref else ""
        })
    

    return pv_details, len(pv_details)

def get_pv_description(path=None, context=None, pv_name=None):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    pv = v1.read_persistent_volume(name=pv_name)

    pv_info = {
        "Name": pv.metadata.name,
        "Labels": pv.metadata.labels,
        "Annotations": filter_annotations(pv.metadata.annotations or {}),
        "Finalizers": pv.metadata.finalizers,
        "StorageClass": pv.spec.storage_class_name,
        "Status": pv.status.phase,
        "Claim": f"{pv.spec.claim_ref.namespace}/{pv.spec.claim_ref.name}" if pv.spec.claim_ref else "N/A",
        "reclaim_policy": pv.spec.persistent_volume_reclaim_policy,
        "Access_Modes": pv.spec.access_modes,
        "VolumeMode": pv.spec.volume_mode,
        "Capacity": pv.spec.capacity.get("storage"),  # Get storage capacity
        "Node_Affinity": pv.spec.node_affinity,  # Add Node Affinity
        "Message": pv.status.message,  # Add Message
        "Source": {},  # Initialize Source dictionary
    }

    # Extract source information (handle different source types)
    if pv.spec.host_path:
        pv_info["Source"]["Type"] = "HostPath (bare host directory volume)"
        pv_info["Source"]["Path"] = pv.spec.host_path.path
        pv_info["Source"]["HostPathType"] = pv.spec.host_path.type # Add HostPathType

    elif pv.spec.gce_persistent_disk: # Example: GCE Persistent Disk
        pv_info["Source"]["Type"] = "GCEPersistentDisk"
        pv_info["Source"]["PDName"] = pv.spec.gce_persistent_disk.pd_name
        
    return pv_info


def get_pv_yaml(path, context, pv_name):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    pv = v1.read_persistent_volume(name=pv_name)
    # Filtering Annotations
    if pv.metadata:
        pv.metadata.annotations = filter_annotations(pv.metadata.annotations or {})
    return yaml.dump(pv.to_dict(), default_flow_style=False)