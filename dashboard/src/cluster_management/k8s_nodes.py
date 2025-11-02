from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException
from datetime import datetime, timezone
from ..utils import calculateAge
from ..utils import configure_k8s
import yaml

def getnodes(path, cluster_name):
    configure_k8s(path, cluster_name)
    v1 = client.CoreV1Api() #Create an API client for the CoreV1Api
    nodes = v1.list_node() #total number of nodes
    node_list = []
    for node in nodes.items:
        node_list.append(node.metadata.name)
    return node_list, len(node_list)

def get_nodes_status(path, context):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    node_list = v1.list_node().items
    ready_nodes = 0
    not_ready_nodes = 0
    for node in node_list:
        if node.status.conditions:
            # Check if any condition type is "Ready" and its status is "True"
            is_ready = any(condition.type == "Ready" and condition.status == "True" for condition in node.status.conditions)

            if is_ready:
                ready_nodes += 1
            else:
                not_ready_nodes += 1
        else:
            # If there are no conditions at all, mark it as not ready
            not_ready_nodes += 1

    return ready_nodes, not_ready_nodes, ready_nodes + not_ready_nodes

NODE_ROLE_PREFIX = "node-role.kubernetes.io/"

def get_nodes_info(path: str, context: str):
    # Load the kube config with the specified path and context
    configure_k8s(path, context)
    
    v1 = client.CoreV1Api()
    nodes = v1.list_node().items
    
    node_data = []
    
    for node in nodes:
        if node.status.conditions:
            # Check if any condition type is "Ready" and its status is "True"
            is_ready = any(condition.type == "Ready" and condition.status == "True" for condition in node.status.conditions)

            if is_ready:
                status = "Ready"
            else:
                status = "Not Ready"
        else:
            # If there are no conditions at all, mark it as not ready
            status = "Not Ready"

        if node.status.addresses:
            internal_ip = next((addr.address for addr in node.status.addresses if addr.type == "InternalIP"), "None")
        if node.status.addresses:
            external_ip = next((addr.address for addr in node.status.addresses if addr.type == "ExternalIP"), "None")
        

        if node.metadata.labels:
            roles = [label.replace(NODE_ROLE_PREFIX, "") for label in node.metadata.labels if label.startswith(NODE_ROLE_PREFIX)]
        else:
            roles = "-"

        if node.spec.taints:
            taints = [taint.key + "=" + (taint.value if taint.value else "") + ":" + taint.effect for taint in node.spec.taints]
        else:
            taints = ""

        node_info = {
            "name": node.metadata.name,
            "status": status,
            "age": calculateAge(datetime.now(timezone.utc) - node.metadata.creation_timestamp),
            "roles": roles,
            "version": node.status.node_info.kubelet_version if node.status.node_info.kubelet_version else "-",
            "internal_ip": internal_ip,
            "external_ip": external_ip,
            "os_image": node.status.node_info.os_image if node.status.node_info.os_image else "-",
            "kernel_version": node.status.node_info.kernel_version if node.status.node_info.kernel_version else "-",
            "container_runtime": node.status.node_info.container_runtime_version if node.status.node_info.container_runtime_version else "-",
            "taints": "" if taints == "none" else taints
        }
        node_data.append(node_info)
    
    return node_data

def get_node_description(path=None, context=None, node_name=None):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    coordination_v1 = client.CoordinationV1Api()

    try:
        # Fetch node details
        node = v1.read_node(name=node_name)
        roles = [key.replace(NODE_ROLE_PREFIX, "") for key in node.metadata.labels if key.startswith(NODE_ROLE_PREFIX)]
        
        # Prepare node information
        if node.spec.taints:
            taints = [taint.key + "=" + (taint.value if taint.value else "") + ":" + taint.effect for taint in node.spec.taints]
        else:
            taints = "none"
        
        # Get lease information
        try:
            lease = coordination_v1.read_namespaced_lease(name=node_name, namespace="kube-node-lease")
            lease_info = {
                "holder_identity": lease.spec.holder_identity,
                "acquire_time": lease.spec.acquire_time,
                "renew_time": lease.spec.renew_time,
                "lease_duration_seconds": lease.spec.lease_duration_seconds,
            }
        except client.exceptions.ApiException:
            lease_info = {"error": "Lease information not available"}
        
        # Get non-terminated pods on the node
        pods = v1.list_pod_for_all_namespaces(field_selector=f"spec.nodeName={node_name},status.phase!=Failed,status.phase!=Succeeded")
        non_terminated_pods = []
        for pod in pods.items:
            non_terminated_pods.append({
                "name": pod.metadata.name,
                "namespace": pod.metadata.namespace,
                "status": pod.status.phase,
                "cpu_requests": pod.spec.containers[0].resources.requests.get("cpu", "N/A") if pod.spec.containers[0].resources and pod.spec.containers[0].resources.requests else "N/A",
                "memory_requests": pod.spec.containers[0].resources.requests.get("memory", "N/A") if pod.spec.containers[0].resources and pod.spec.containers[0].resources.requests else "N/A",
            })
            
        node_info = {
            "name": node.metadata.name,
            "roles": roles,
            "labels": list(node.metadata.labels.items()) if node.metadata.labels else [],
            "annotations": list(node.metadata.annotations.items()) if node.metadata.annotations else [],
            "creation_timestamp": node.metadata.creation_timestamp,
            "taints": taints,
            "unschedulable": node.spec.unschedulable,
            "addresses": {address.type: address.address for address in node.status.addresses} if node.status.addresses else {},
            "capacity": {key: str(value) for key, value in node.status.capacity.items()} if node.status.capacity else {},
            "allocatable": {key: str(value) for key, value in node.status.allocatable.items()} if node.status.allocatable else {},
            "system_info": {
                "machine_id": node.status.node_info.machine_id,
                "system_uuid": node.status.node_info.system_uuid,
                "boot_id": node.status.node_info.boot_id,
                "kernel_version": node.status.node_info.kernel_version,
                "os_image": node.status.node_info.os_image,
                "operating_system": node.status.node_info.operating_system,
                "architecture": node.status.node_info.architecture,
                "container_runtime_version": node.status.node_info.container_runtime_version,
                "kubelet_version": node.status.node_info.kubelet_version,
                "kube_proxy_version": node.status.node_info.kube_proxy_version,
            },
            "allocated_resources": {
                "cpu_requests": node.status.allocatable.get("cpu", "0"),
                "memory_requests": node.status.allocatable.get("memory", "0"),
                "ephemeral_storage_requests": node.status.allocatable.get("ephemeral-storage", "0"),
                "cpu_limits": node.status.capacity.get("cpu", "0"),
                "memory_limits": node.status.capacity.get("memory", "0"),
                "ephemeral_storage_limits": node.status.capacity.get("ephemeral-storage", "0"),
            },
            "lease": lease_info,
            "conditions": [
                {
                    "type": condition.type,
                    "status": condition.status,
                    "last_heartbeat_time": condition.last_heartbeat_time,
                    "last_transition_time": condition.last_transition_time,
                    "reason": condition.reason,
                    "message": condition.message
                } 
                for condition in node.status.conditions
            ] if node.status.conditions else [],
            "pod_cidr": node.spec.pod_cidr if hasattr(node.spec, "pod_cidr") else None,
            "pod_cidrs": node.spec.pod_cidrs if hasattr(node.spec, "pod_cidrs") else None,
            "provider_id": node.spec.provider_id if hasattr(node.spec, "provider_id") else None,
            "non_terminated_pods": non_terminated_pods
        }

        return node_info

    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch node details: {e.reason}"}


def get_node_yaml(path, context, node_name):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    node = v1.read_node(name=node_name)
    return yaml.dump(node.to_dict(), default_flow_style=False)

def get_node_details():
    try:
        config.load_incluster_config()
    except ConfigException:
        config.load_kube_config()

    v1 = client.CoreV1Api()
    nodes = v1.list_node()

    def get_age(creation_timestamp):
        delta = datetime.now(timezone.utc) - creation_timestamp
        days = delta.days
        hours = delta.seconds // 3600
        return f"{days}d {hours}h" if days else f"{hours}h"

    node_details = []
    for node in nodes.items:
        status = "NotReady"
        for condition in node.status.conditions or []:
            if condition.type == "Ready" and condition.status == "True":
                status = "Ready"
                break

        node_info = {
            'name': node.metadata.name,
            'status': status,
            'labels': node.metadata.labels,
            'cpu': node.status.capacity.get('cpu'),
            'memory': node.status.capacity.get('memory'),
            'age': get_age(node.metadata.creation_timestamp)
        }
        node_details.append(node_info)

    return node_details