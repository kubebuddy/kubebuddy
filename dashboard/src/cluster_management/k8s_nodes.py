from kubernetes import client, config
from datetime import datetime, timezone
from ..utils import calculateAge
import yaml

def getnodes():
    config.load_kube_config()
    v1 = client.CoreV1Api() #Create an API client for the CoreV1Api
    nodes = v1.list_node() #total number of nodes
    node_list = []
    for node in nodes.items:
        node_list.append(node.metadata.name)
    return node_list, len(node_list)

def getNodesStatus(path, context):
    config.load_kube_config(path, context)
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

def get_nodes_info(path: str, context: str):
    # Load the kube config with the specified path and context
    config.load_kube_config(path, context=context)
    
    v1 = client.CoreV1Api()
    nodes = v1.list_node().items
    
    node_data = []
    
    for node in nodes:
        print(node)
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
            roles = node.metadata.labels.get("kubernetes.io/role", "Unknown")
        else:
            roles = "-"

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
            "taints": node.spec.taints
        }
        node_data.append(node_info)
    
    return node_data

def get_node_description(path=None, context=None, node_name=None):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()

    try:
        # Fetch node details
        node = v1.read_node(name=node_name)
        roles = [key.replace("node-role.kubernetes.io/", "") for key in node.metadata.labels if key.startswith("node-role.kubernetes.io/")]
        # Prepare node information
        node_info = {
            "name": node.metadata.name,
            "roles": roles,
            "labels": list(node.metadata.labels.items()) if node.metadata.labels else [],
            "annotations": list(node.metadata.annotations.items()) if node.metadata.annotations else [],
            "creation_timestamp": node.metadata.creation_timestamp,
            "taints": node.spec.taints,
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
            }
        }

        return node_info

    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch node details: {e.reason}"}


def get_node_yaml(path, context, node_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    node = v1.read_node(name=node_name)
    return yaml.dump(node.to_dict(), default_flow_style=False)