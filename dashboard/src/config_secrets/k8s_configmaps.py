from kubernetes import client, config
from datetime import datetime, timezone
import yaml
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



def get_configmap_description(path=None, context=None, namespace=None, configmap_name=None):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    try:
        configmaps = v1.list_namespaced_config_map(namespace=namespace).items

        target_configmap = None
        for cm in configmaps:
            if cm.metadata.name == configmap_name:
                target_configmap = cm
                break

        if target_configmap is None:
            return {"error": f"ConfigMap {configmap_name} not found in namespace {namespace}"}

        configmap_info = {
            "name": target_configmap.metadata.name,
            "namespace": target_configmap.metadata.namespace,
            "data": {k: v for k, v in target_configmap.data.items()} if target_configmap.data else {}, # Handle missing data
        }
        return configmap_info

    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch ConfigMap details: {e.reason}"}

def get_configmap_events(path, context, namespace, configmap_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    configmap_events = [
        event for event in events if event.involved_object.name == configmap_name and event.involved_object.kind == "ConfigMap"
    ]
    return "\n".join([f"{e.reason}: {e.message}" for e in configmap_events])


def get_configmap_yaml(path, context, namespace, configmap_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    configmaps = v1.list_namespaced_config_map(namespace=namespace).items

    target_configmap = None
    for cm in configmaps:
        if cm.metadata.name == configmap_name:
            target_configmap = cm
            break

    if target_configmap is None:
        return {"error": f"ConfigMap {configmap_name} not found in namespace {namespace}"}

    return yaml.dump(target_configmap.to_dict(), default_style='|', width=float("inf"))