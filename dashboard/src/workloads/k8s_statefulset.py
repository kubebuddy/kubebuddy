from kubernetes import client, config
from datetime import datetime, timezone
from ..utils import calculateAge, filter_annotations, configure_k8s
from kubebuddy.appLogs import logger
import yaml

def getStatefulsetCount(path, context):
    configure_k8s(path, context)
    v1 = client.AppsV1Api() #Create an API client for the AppsV1Api
    statefulsets = v1.list_stateful_set_for_all_namespaces().items

    return len(statefulsets)

def getStatefulsetStatus(path, context, namespace="all"):
    try:
        configure_k8s(path, context)
        v1 = client.AppsV1Api()
        statefulsets = v1.list_stateful_set_for_all_namespaces() if namespace == "all" else v1.list_namespaced_stateful_set(namespace=namespace)

        statefulset_status = {
            "Running": 0,
            "Pending": 0,
            "Count": 0
        }

        for statefulset in statefulsets.items:
            if statefulset.status.replicas == statefulset.status.ready_replicas == statefulset.status.available_replicas != None: 
                statefulset_status["Running"] += 1
            else: 
                statefulset_status["Pending"] += 1 
            
            statefulset_status["Count"] += 1

        return statefulset_status
    
    except client.exceptions.ApiException as e:
        logger.error(f"Kubernetes API Exception: {e}")  # Print API errors to stderr
        return []
    except Exception as e:  # Catch other potential errors (e.g., config issues)
        logger.error(f"An error occurred: {e}")  # Print other errors to stderr
        return []
    
def getStatefulsetList(path, context, namespace="all"):
    try:
        configure_k8s(path, context)
        v1 = client.AppsV1Api()
        statefulsets = v1.list_stateful_set_for_all_namespaces() if namespace == "all" else v1.list_namespaced_stateful_set(namespace=namespace)

        statefulset_info_list = []
        for statefulset in statefulsets.items:
            namespace = statefulset.metadata.namespace
            name = statefulset.metadata.name
            available_replicas = statefulset.status.available_replicas
            replicas = statefulset.spec.replicas
            ready = str(available_replicas) + "/" + str(replicas)
            difference = (datetime.now(timezone.utc) - statefulset.metadata.creation_timestamp)
            age = calculateAge(difference)
            images = []
            for containers in statefulset.spec.template.spec.containers:
                images.append(containers.image)

            statefulset_info_list.append({
                'namespace': namespace,
                'name': name,
                'ready': ready,
                'age': age,
                'images': images
            })
        
        return statefulset_info_list


    except client.exceptions.ApiException as e:
        logger(f"Kubernetes API Exception: {e}")  # Print API errors to stderr
        return []
    except Exception as e:  # Catch other potential errors (e.g., config issues)
        logger(f"An error occurred: {e}")  # Print other errors to stderr
        return []
    

def get_statefulset_description(path=None, context=None, namespace=None, sts_name=None):
    configure_k8s(path, context)
    v1 = client.AppsV1Api()

    try:
        # Fetch StatefulSet details
        sts = v1.read_namespaced_stateful_set(name=sts_name, namespace=namespace)
        
        sts_info = {
            "name": sts.metadata.name,
            "namespace": sts.metadata.namespace,
            "creation_timestamp": sts.metadata.creation_timestamp,
            "selector": sts.spec.selector.match_labels if sts.spec.selector else {},
            "labels": list(sts.metadata.labels.items()) if sts.metadata.labels else [],
            "annotations": filter_annotations(sts.metadata.annotations or {}),
            "replicas": {
                "desired": sts.status.replicas,  # Desired number of replicas
                "total": sts.status.replicas,  # Total number of replicas (desired)
            },
            "update_strategy": {
                "type": sts.spec.update_strategy.type,  # Update strategy (RollingUpdate)
                "partition": sts.spec.update_strategy.rolling_update.partition if sts.spec.update_strategy.type == "RollingUpdate" else None
            },
            "pods_status": {
                "running": sts.status.ready_replicas if hasattr(sts.status, 'ready_replicas') else 0,
                "waiting": sts.status.replicas - (sts.status.ready_replicas if sts.status.ready_replicas is not None else 0),
                "succeeded": 0,  # StatefulSets don't track succeeded pods directly, so it's set to 0 by default
                "failed": 0,     # Similarly for failed pods
            },
            "pod_template": {
                "labels": list(sts.spec.template.metadata.labels.items()) if sts.spec.template.metadata.labels else [],
                "containers": [
                    {
                        "name": container.name,
                        "image": container.image,
                        "ports": [port.container_port for port in (container.ports or [])],
                        "env": [env.name for env in (container.env or [])],
                        "mounts": [mount.mount_path for mount in (container.volume_mounts or [])]
                    }
                    for container in sts.spec.template.spec.containers
                ],
                "volumes": [
                    {
                        "name": volume.name,
                        "type": volume.secret or volume.config_map or volume.projected
                    }
                    for volume in (sts.spec.template.spec.volumes or [])
                ],
                "node_selectors": sts.spec.template.spec.node_selector.items() if sts.spec.template.spec.node_selector else [],
                "tolerations": sts.spec.template.spec.tolerations
            },
            "volume_claims": [
                {
                    "name": pvc.metadata.name,
                    "storage_class": pvc.spec.storage_class_name,
                    "labels": list(pvc.metadata.labels.items()) if pvc.metadata.labels else [],
                    "annotations": list(pvc.metadata.annotations.items()) if pvc.metadata.annotations else [],
                    "capacity": pvc.spec.resources.requests.get("storage") if pvc.spec.resources.requests else None,
                    "access_modes": pvc.spec.access_modes,
                }
                for pvc in (sts.spec.volume_claim_templates or [])
            ]
        }

        return sts_info
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch StatefulSet details: {e.reason}"}


def get_sts_events(path, context, namespace, statefulset_name):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    statefulset_events = [event for event in events if event.involved_object.name == statefulset_name and event.involved_object.kind == "StatefulSet"]
    return "\n".join([f"{e.reason}: {e.message}" for e in statefulset_events])

def get_yaml_sts(path, context, namespace, statefulset_name):
    configure_k8s(path, context)
    v1 = client.AppsV1Api()
    statefulset = v1.read_namespaced_stateful_set(name=statefulset_name, namespace=namespace)
    # Filtering Annotations
    if statefulset.metadata:
        statefulset.metadata.annotations = filter_annotations(statefulset.metadata.annotations or {})
    return yaml.dump(statefulset.to_dict(), default_flow_style=False)
