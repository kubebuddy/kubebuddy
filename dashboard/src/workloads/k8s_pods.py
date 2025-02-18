from kubernetes import client, config
from datetime import datetime, timezone
import yaml
from ..utils import calculateAge

def getpods():
    config.load_kube_config()
    v1 = client.CoreV1Api()
    pods = v1.list_pod_for_all_namespaces()
    pod_names = [pod.metadata.name for pod in pods.items]
    pod_list = []
    for name in pod_names:
        pod_list.append(name)
    return pod_list, len(pod_list)

def getPodsStatus(path, context):
    config.load_kube_config(config_file=path, context=context)
    v1 = client.CoreV1Api()
    pods = v1.list_pod_for_all_namespaces()

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

    return status_counts


def get_pod_info(config_path, cluster_name):

    config.load_kube_config(config_file=config_path, context=cluster_name)

    v1 = client.CoreV1Api()
    pods = v1.list_pod_for_all_namespaces(watch=False)

    pod_info_list = []
    for pod in pods.items:
        pod_info_list.append({
            "namespace": pod.metadata.namespace,
            "name": pod.metadata.name,
            "containers": f"{len(pod.spec.containers)}/{len(pod.spec.containers)}",
            "node": pod.spec.node_name,
            "ip": pod.status.pod_ip or "N/A",
            "restarts": sum(container.restart_count for container in pod.status.container_statuses or []),
            "age": calculateAge(datetime.now(timezone.utc) - pod.metadata.creation_timestamp),
            "status": pod.status.phase,
        })

    return pod_info_list

def get_pod_description(path=None, context=None, namespace=None, pod_name=None):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    try:
        # Fetch pod details
        pod = v1.read_namespaced_pod(name=pod_name, namespace=namespace)

        pod_info = {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "status": pod.status.phase,
            "node_name": pod.spec.node_name,
            "pod_ip": pod.status.pod_ip,
            "host_ip": pod.status.host_ip,
            "start_time": pod.status.start_time.isoformat() if pod.status.start_time else None,
            "containers": [
                {
                    "name": container.name,
                    "image": container.image,
                    "ports": [port.container_port for port in (container.ports or [])],
                }
                for container in pod.spec.containers
            ],
            "conditions": [
                {"type": cond.type, "status": cond.status, "reason": cond.reason or ""}
                for cond in (pod.status.conditions or [])
            ],
        }

        return pod_info
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch pod details: {e.reason}"}

def get_pod_logs(path, context, namespace, pod_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    return v1.read_namespaced_pod_log(name=pod_name, namespace=namespace)

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
