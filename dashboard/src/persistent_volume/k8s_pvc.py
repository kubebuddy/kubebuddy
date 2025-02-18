from kubernetes import client, config

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
            "age": pvc.metadata.creation_timestamp.strftime('%Y-%m-%d %H:%M:%S') if pvc.metadata.creation_timestamp else "N/A"
        }
        pvc_list.append(pvc_info)
    
    return pvc_list