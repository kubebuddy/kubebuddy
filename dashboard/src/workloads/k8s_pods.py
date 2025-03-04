from kubernetes import client, config
from datetime import datetime, timezone
import yaml
from ..utils import calculateAge

def getpods(path, context, namespace="all"):
    config.load_kube_config(config_file=path, context=context)
    v1 = client.CoreV1Api()
    pods = v1.list_pod_for_all_namespaces() if namespace == "all" else v1.list_namespaced_pod(namespace=namespace)
    pod_names = [pod.metadata.name for pod in pods.items]
    pod_list = []
    for name in pod_names:
        pod_list.append(name)
    return pod_list, len(pod_list)

def getPodsStatus(path, context, namespace="all"):
    config.load_kube_config(config_file=path, context=context)
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

    config.load_kube_config(config_file=config_path, context=cluster_name)

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
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    try:
        # Fetch pod details
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        # Get annotations
        annotations =pod.metadata.annotations or {}
        # Remove 'kubectl.kubernetes.io/last-applied-configuration' if it's the only annotation
        filtered_annotations = {k: v for k, v in annotations.items() if k != "kubectl.kubernetes.io/last-applied-configuration"}
        # Prepare pod information
        pod_info = {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "priority": pod.spec.priority,
            "status": pod.status.phase,
            "node_name": pod.spec.node_name,
            "pod_ip": pod.status.pod_ip,
            "host_ip": pod.status.host_ip,
            "start_time": pod.status.start_time.strftime('%a, %d %b %Y %H:%M:%S %z') if pod.status.start_time else None,
            "labels": list(pod.metadata.labels.items()),  # Convert to list of tuples
            "annotations": filtered_annotations if filtered_annotations else None,
            "service_account": pod.spec.service_account_name,
            "containers": [
                {
                    "name": container.name,
                    "image": container.image,
                    "ports": [port.container_port for port in (container.ports or [])],
                    "state": next(
                        (status.state for status in (pod.status.container_statuses or [])
                         if status.name == container.name), "Unknown"
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
                        )
                }
                for volume in pod.spec.volumes
            ],
            "conditions": [
                {"type": cond.type, "status": cond.status}
                for cond in (pod.status.conditions or [])
            ],
        }

        return pod_info
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch pod details: {e.reason}"}



def get_pod_logs(path, context, namespace, pod_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    try:
        logs = v1.read_namespaced_pod_log(name=pod_name, namespace=namespace)
    except Exception as e:
        if e.status == 400:
            logs = None
    return logs

def get_pod_events(path, context, namespace, pod_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    pod_events = [event for event in events if event.involved_object.name == pod_name]
    
    return "\n".join([f"{e.reason}: {e.message}" for e in pod_events])

def get_pod_yaml(path, context, namespace, pod_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)
    return yaml.dump(pod.to_dict(), default_flow_style=False)
