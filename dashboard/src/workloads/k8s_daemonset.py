from kubernetes import client, config
from datetime import datetime, timezone

import yaml
from ..utils import calculateAge

def getDaemonsetCount():
    config.load_kube_config()
    v1 = client.AppsV1Api() #Create an API client for the AppsV1Api
    deployments = v1.list_daemon_set_for_all_namespaces().items

    return len(deployments)

def getDaemonsetStatus(path, context, namespace="all"):
    try:
        config.load_kube_config(config_file=path, context=context)
        v1 = client.AppsV1Api()
        daemonsets = v1.list_daemon_set_for_all_namespaces() if namespace == "all" else v1.list_namespaced_daemon_set(namespace=namespace)

        daemonset_status = {
            "Running": 0,
            "Pending": 0,
            "Count": 0
        }

        for daemonset in daemonsets.items:
            if daemonset.status.number_ready == daemonset.status.desired_number_scheduled == daemonset.status.current_number_scheduled != None: 
                daemonset_status["Running"] += 1
            else: 
                daemonset_status["Pending"] += 1 
            
            daemonset_status["Count"] += 1

        return daemonset_status
    
    except client.exceptions.ApiException as e:
        print(f"Kubernetes API Exception: {e}")  # Print API errors to stderr
        return []
    except Exception as e:  # Catch other potential errors (e.g., config issues)
        print(f"An error occurred: {e}")  # Print other errors to stderr
        return []
    
def getDaemonsetList(path, context, namespace="all"):
    try:
        config.load_kube_config(config_file=path, context=context)
        v1 = client.AppsV1Api()
        daemonsets = v1.list_daemon_set_for_all_namespaces() if namespace == "all" else v1.list_namespaced_daemon_set(namespace=namespace)

        daemonset_info_list = []
        for daemonset in daemonsets.items:
            namespace = daemonset.metadata.namespace
            name = daemonset.metadata.name
            desired = daemonset.status.desired_number_scheduled
            current = daemonset.status.current_number_scheduled
            ready = daemonset.status.number_ready
            difference = (datetime.now(timezone.utc) - daemonset.metadata.creation_timestamp)
            age = calculateAge(difference)
            
            daemonset_info_list.append({
                'namespace': namespace,
                'name': name,
                'desired': desired,
                'current': current,
                'ready': ready,
                'age': age
            })
        
        return daemonset_info_list
    
    except client.exceptions.ApiException as e:
        print(f"Kubernetes API Exception: {e}")  # Print API errors to stderr
        return []
    except Exception as e:  # Catch other potential errors (e.g., config issues)
        print(f"An error occurred: {e}")  # Print other errors to stderr
        return []




def get_daemonset_description(path=None, context=None, namespace=None, daemonset_name=None):
    config.load_kube_config(path, context)
    v1 = client.AppsV1Api()  # Use AppsV1Api for DaemonSets
    try:
        daemonset = v1.read_namespaced_daemon_set(name=daemonset_name, namespace=namespace)
        
        daemonset_info = {
            "name": daemonset.metadata.name,
            "namespace": daemonset.metadata.namespace,
            "selector": daemonset.spec.selector.match_labels, # Add selector info
            "template": { # Expanded pod template structure
                "labels": daemonset.spec.template.metadata.labels,
                "service_account": getattr(daemonset.spec.template.spec, "service_account_name", None),
                "containers": [
                    {
                        "name": container.name,
                        "image": container.image,
                        "ports": [port.container_port for port in (container.ports or [])],
                        "resources": getattr(container, "resources", None),
                        "volume_mounts": [
                            {
                                "name": volume_mount.name,
                                "mount_path": volume_mount.mount_path,
                                "read_only": getattr(volume_mount, "read_only", False)
                            } for volume_mount in (container.volume_mounts or [])
                        ]
                    }
                    for container in daemonset.spec.template.spec.containers
                ],
                "volumes": [
                    {
                        "name": volume.name,
                        # Instead of trying to dynamically determine volume type, extract known volume types
                        "config_map": getattr(volume, "config_map", None),
                        "secret": getattr(volume, "secret", None),
                        "empty_dir": getattr(volume, "empty_dir", None),
                        "host_path": getattr(volume, "host_path", None),
                        "persistent_volume_claim": getattr(volume, "persistent_volume_claim", None),
                        "projected": getattr(volume, "projected", None)
                    } for volume in (getattr(daemonset.spec.template.spec, "volumes", []) or [])
                ],
                "priority_class_name": getattr(daemonset.spec.template.spec, "priority_class_name", None),
                "node_selector": getattr(daemonset.spec.template.spec, "node_selector", None),
                "tolerations": [
                    {
                        "key": toleration.key,
                        "operator": toleration.operator,
                        "value": toleration.value,
                        "effect": toleration.effect,
                        "toleration_seconds": toleration.toleration_seconds
                    } for toleration in (getattr(daemonset.spec.template.spec, "tolerations", []) or [])
                ]
            },
            "status": {
                "desired_number_scheduled": daemonset.status.desired_number_scheduled,
                "current_number_scheduled": daemonset.status.current_number_scheduled,
                "number_ready": daemonset.status.number_ready,
                "number_available": daemonset.status.number_available,
                "number_misscheduled": getattr(daemonset.status, "number_misscheduled", "N/A"),
                "number_updated": getattr(daemonset.status, "number_updated", "N/A"),
            },
        }
        return daemonset_info
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch daemonset details: {e.reason}"}


def get_daemonset_events(path, context, namespace, daemonset_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    daemonset_events = [
        event for event in events if event.involved_object.name == daemonset_name and event.involved_object.kind == "DaemonSet" # Filter by kind
    ]
    return "\n".join([f"{e.reason}: {e.message}" for e in daemonset_events])

def get_daemonset_yaml(path, context, namespace, daemonset_name):
    config.load_kube_config(path, context)
    v1 = client.AppsV1Api() # Use AppsV1Api
    daemonset = v1.read_namespaced_daemon_set(name=daemonset_name, namespace=namespace)
    return yaml.dump(daemonset.to_dict(), default_flow_style=False)
