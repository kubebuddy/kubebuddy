from kubernetes import client, config

def get_nodes_info(path: str, context: str):
    # Load the kube config with the specified path and context
    config.load_kube_config(path, context=context)
    
    v1 = client.CoreV1Api()
    nodes = v1.list_node().items
    
    node_data = []
    
    for node in nodes:
        node_info = {
            "name": node.metadata.name,
            "status": node.status.conditions[-1].type if node.status.conditions else "Unknown",
            "roles": node.metadata.labels.get("kubernetes.io/role", "Unknown"),
            "age": node.metadata.creation_timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            "version": node.status.node_info.kubelet_version,
            "internal_ip": next((addr.address for addr in node.status.addresses if addr.type == "InternalIP"), "N/A"),
            "external_ip": next((addr.address for addr in node.status.addresses if addr.type == "ExternalIP"), "N/A"),
            "os_image": node.status.node_info.os_image,
            "kernel_version": node.status.node_info.kernel_version,
            "container_runtime": node.status.node_info.container_runtime_version,
        }
        node_data.append(node_info)
    
    return node_data