from kubernetes import client, config

def list_persistent_volumes(path: str, context: str):
    # Load Kubernetes configuration
    config.load_kube_config(path, context)
    
    v1 = client.CoreV1Api()
    pv_list = v1.list_persistent_volume().items
    
    # Collect PV details
    pv_details = []
    for pv in pv_list:
        pv_details.append({
            "name": pv.metadata.name,
            "capacity": pv.spec.capacity["storage"],
            "access_modes": ", ".join(pv.spec.access_modes),
            "reclaim_policy": pv.spec.persistent_volume_reclaim_policy,
            "status": pv.status.phase,
            "claim": f"{pv.spec.claim_ref.namespace}/{pv.spec.claim_ref.name}" if pv.spec.claim_ref else "-",
            "storage_class": pv.spec.storage_class_name,
            "volume_attribute_class": getattr(pv.spec, 'volume_mode', '-'),
            "volume_system": getattr(pv.spec, 'csi', {}).get('volume_handle', '-'),
            "age": pv.metadata.creation_timestamp,
        })
    
    return pv_details