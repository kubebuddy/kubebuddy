from kubernetes import client, config

def getnodes():
    con = config.load_kube_config()
    v1 = client.CoreV1Api() #Create an API client for the CoreV1Api
    nodes = v1.list_node() #total number of nodes
    node_list = []
    for node in nodes.items:
        node_list.append(node.metadata.name)
        # print(f"Node Name: {node.metadata.name}")
        # print(f"Labels: {node.metadata.labels}")
        # for condition in node.status.conditions:
        #     print(f"{condition.type}: {condition.status}")

    node_count = len(nodes.items)
    # print(node_list)
    return node_count, node_list
