from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException
from datetime import datetime, timezone
from kubebuddy.appLogs import logger
import yaml
from ..utils import calculateAge, filter_annotations, configure_k8s

def getpods(path, context, namespace="all"):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    pods = v1.list_pod_for_all_namespaces() if namespace == "all" else v1.list_namespaced_pod(namespace=namespace)
    pod_names = [pod.metadata.name for pod in pods.items]
    pod_list = []
    for name in pod_names:
        pod_list.append(name)
    return pod_list, len(pod_list)

def getPodsStatus(path, context, namespace="all"):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    pods = v1.list_pod_for_all_namespaces() if namespace == "all" else v1.list_namespaced_pod(namespace=namespace)

    status_counts = {
    "Pending": 0,
    "Running": 0,
    "Failed": 0,
    "Succeeded": 0
    }

    # Check each pod's status
    for pod in pods.items:
        if pod.status.phase == "Succeeded":
            status_counts["Succeeded"]+=1
        elif pod.status.phase == "Pending":
            status_counts["Pending"]+=1
        elif pod.status.phase == "Running":
            all_container_running = True
            for status in pod.status.container_statuses:
                if status.state.running:
                    pass
                else:
                    status_counts["Failed"]+=1
                    all_container_running = False
                    break
            if all_container_running:
                status_counts["Running"]+=1
        else:
            status_counts["Failed"]+=1

    return status_counts

def getPodStatus(pod):
    if pod.status.phase == "Succeeded":
            return "Succeeded"
    elif pod.status.phase == "Pending":
            return "Pending"
    elif pod.status.phase == "Running":
        all_container_running = True
        for status in pod.status.container_statuses:
            if status.state.running:
                pass
            else:
                all_container_running = False
                return "Failed"
        if all_container_running:
            return "Running"
    return "Failed"

def get_pod_info(config_path, cluster_name):

    configure_k8s(config_path, cluster_name)
    v1 = client.CoreV1Api()
    pods = v1.list_pod_for_all_namespaces(watch=False)

    pod_info_list = []
    for pod in pods.items:
        status = getPodStatus(pod)
        container_statuses = pod.status.container_statuses or []
        ready_count = sum(1 for status in container_statuses if status.ready)
        total_count = len(container_statuses)
        pod_info_list.append({
            "namespace": pod.metadata.namespace,
            "name": pod.metadata.name,
            "containers": f"{ready_count}/{total_count}",
            "node": pod.spec.node_name,
            "ip": pod.status.pod_ip or "N/A",
            "restarts": sum(container.restart_count for container in pod.status.container_statuses or []),
            "age": calculateAge(datetime.now(timezone.utc) - pod.metadata.creation_timestamp),
            "status": status,
        })

    return pod_info_list

def get_pod_description(path=None, context=None, namespace=None, pod_name=None):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    try:
        # Fetch pod details
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        
        # Extract "Controlled By" from owner references
        controlled_by = None
        if pod.metadata.owner_references:
            owner_reference = pod.metadata.owner_references[0]
            controlled_by = f"{owner_reference.kind}/{owner_reference.name}"
        
        # Prepare pod information
        pod_info = {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "priority": pod.spec.priority,
            "status": getPodStatus(pod),
            "node_name": pod.spec.node_name,
            "pod_ip": pod.status.pod_ip,
            "host_ip": pod.status.host_ip,
            "start_time": pod.status.start_time.strftime('%a, %d %b %Y %H:%M:%S %z') if pod.status.start_time else None,
            "labels": list(pod.metadata.labels.items()) if pod.metadata.labels else [],
            "annotations": filter_annotations(pod.metadata.annotations or {}),
            "qos_class": pod.status.qos_class,
            "node_selectors": pod.spec.node_selector if pod.spec.node_selector else None,
            "tolerations" : pod.spec.tolerations if pod.spec.tolerations else None,
            "service_account": pod.spec.service_account_name,
            "containers": [
                {
                    "name": container.name,
                    "image": container.image,
                    "ports": [port.container_port for port in (container.ports or [])],
                    # Simplify state to just show container state name (running, waiting, terminated) without details
                    "container_status": next(
                        (
                            next((state_name for state_name, state_obj in status.state.to_dict().items() if state_obj is not None), "Unknown")
                            for status in (pod.status.container_statuses or [])
                            if status.name == container.name
                        ), 
                        "Unknown"
                    ),
                    # Add container ID
                    "container_id": next(
                        (status.container_id for status in (pod.status.container_statuses or [])
                         if status.name == container.name), None
                    ),
                    # Add image ID
                    "image_id": next(
                        (status.image_id for status in (pod.status.container_statuses or [])
                         if status.name == container.name), None
                    ),
                    "restart_count": next(
                        (status.restart_count for status in (pod.status.container_statuses or [])
                         if status.name == container.name), 0
                    ),
                    "env": [env.name for env in (container.env or [])],
                    "mounts": [mount.mount_path + " from " + mount.name for mount in (container.volume_mounts or [])]
                }
                for container in pod.spec.containers
            ],
            "volumes": [
                {
                    "name": volume.name,
                    "type": next(
                            (attr for attr, value in volume.to_dict().items() 
                            if attr != "name" and value is not None),
                            None
                        ),
                    # "TokenExpirationSeconds": volume.secret.token_expiration_seconds,
                    # "ConfigMapName": volume.config_map.name,
                    # "ConfigMapOptional": volume.config_map.optional,
                    # "DownwardAPI": volume.downward_api.items,
                }
                for volume in pod.spec.volumes
            ],
            "conditions": [
                {"type": cond.type, "status": cond.status}
                for cond in (pod.status.conditions or [])
            ],
            "controlled_by": controlled_by
        }
        return pod_info
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch pod details: {e.reason}"}

def get_pod_logs(path, context, namespace, pod_name):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    try:
        logs = v1.read_namespaced_pod_log(name=pod_name, namespace=namespace)
    except Exception as e:
        if e.status == 400:
            logs = None
    return logs

def get_pod_events(path, context, namespace, pod_name):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    pod_events = [event for event in events if event.involved_object.name == pod_name]
    
    return "\n".join([f"{e.reason}: {e.message}" for e in pod_events])

def get_pod_yaml(path, context, namespace, pod_name):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
    # Filtering Annotations
    if pod.metadata:
        pod.metadata.annotations = filter_annotations(pod.metadata.annotations or {})
    return yaml.dump(pod.to_dict(), default_flow_style=False)

def get_pod_details(namespace=None):
    try:
        config.load_incluster_config()
    except ConfigException:
        config.load_kube_config()

    v1 = client.CoreV1Api()
    pods = v1.list_namespaced_pod(namespace) if namespace else v1.list_pod_for_all_namespaces()

    def get_age(creation_timestamp):
        delta = datetime.now(timezone.utc) - creation_timestamp
        days = delta.days
        hours = delta.seconds // 3600
        return f"{days}d {hours}h" if days else f"{hours}h"

    pod_details = []
    for pod in pods.items:
        pod_info = {
            'name': pod.metadata.name,
            'namespace': pod.metadata.namespace,
            'status': pod.status.phase,
            'node': pod.spec.node_name if pod.spec.node_name else 'N/A',
            'restarts': sum([cs.restart_count for cs in pod.status.container_statuses or []]),
            'age': get_age(pod.metadata.creation_timestamp)
        }
        pod_details.append(pod_info)

    return pod_details
