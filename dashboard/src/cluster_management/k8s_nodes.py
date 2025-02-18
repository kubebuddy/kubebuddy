from kubernetes import client, config
from datetime import datetime, timezone
from ..utils import calculateAge

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
            internal_ip = next((addr.address for addr in node.status.addresses if addr.type == "InternalIP"), "N/A")
            external_ip = next((addr.address for addr in node.status.addresses if addr.type == "ExternalIP"), "N/A")
        else:
            internal_ip = "None"
            external_ip = "None"

        if node.metadata.labels:
            roles = node.metadata.labels.get("kubernetes.io/role", "Unknown")
        else:
            roles = "None"

        node_info = {
            "name": node.metadata.name,
            "status": status,
            "age": calculateAge(datetime.now(timezone.utc) - node.metadata.creation_timestamp),
            "roles": roles,
            "version": node.status.node_info.kubelet_version,
            "internal_ip": internal_ip,
            "external_ip": external_ip,
            "os_image": node.status.node_info.os_image,
            "kernel_version": node.status.node_info.kernel_version,
            "container_runtime": node.status.node_info.container_runtime_version,
        }
        node_data.append(node_info)
    
    return node_data