from kubernetes import client, config
from datetime import datetime, timezone
from ..utils import calculateAge

def get_configmaps(path, context):
    config.load_kube_config(config_file=path, context=context)
    v1 = client.CoreV1Api()

    # Fetch all ConfigMaps in all namespaces
    configmaps = v1.list_config_map_for_all_namespaces().items

    configmap_list = []
    total_count = len(configmaps)
    for cm in configmaps:
        name = cm.metadata.name
        namespace = cm.metadata.namespace
        creation_time = cm.metadata.creation_timestamp

        # Calculate age in days
        age = calculateAge(datetime.now(timezone.utc) - creation_time)

        # Get data keys only (not full values)
        # data_keys = ", ".join(cm.data.keys()) if cm.data else "No Data"

        configmap_list.append({
        "name": name,
        "namespace": namespace,
        "age": age,
        })

    return configmap_list, total_count