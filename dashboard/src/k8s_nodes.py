from kubernetes import client, config

def getnodes():
    config.load_kube_config()
    v1 = client.CoreV1Api() #Create an API client for the CoreV1Api
    nodes = v1.list_node() #total number of nodes
    node_list = []
    for node in nodes.items:
        node_info = {
        "name": node.metadata.name,
        "status": node.status.conditions[-1].type  # Grab the status of the node
        }
        node_list.append(node.metadata.name)
        # print(f"Node Name: {node.metadata.name}")
        # print(f"Labels: {node.metadata.labels}")
        # for condition in node.status.conditions:
        #     print(f"{condition.type}: {condition.status}")

    # print(node_list)
    return node_list, len(node_list)

def getNodesStatus():
    config.load_kube_config()
    v1 = client.CoreV1Api()
    node_list = v1.list_node().items

    ready_nodes = 0
    not_ready_nodes = 0

    for node in node_list:
        for condition in node.status.conditions:
            if condition.type == 'Ready':
                if condition.status == 'True':
                    ready_nodes += 1
                else:
                    not_ready_nodes += 1

    return ready_nodes, not_ready_nodes
