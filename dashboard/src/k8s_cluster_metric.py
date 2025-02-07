from kubernetes import client, config

def getMetrics(path, context):
    # config.load_kube_config(config_file=path, context = context)
    # metric_api = client.CustomObjectsApi()
    # core_api = client.CoreV1Api()

    # node_metrics = metric_api.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "nodes") # change to pods for pod metrics
    # node_list = core_api.list_node()

    # total_cpu_allocated = 0
    # total_memory_allocated = 0
    # total_cpu_usage = 0
    # total_memory_usage = 0

    # node_allocations = {}

    # # node allocations
    # for node in node_list.items:
    #     node_name = node.metadata.name
    #     cpu_allocated = node.status.capacity["cpu"]
    #     memory_allocated = node.status.capacity["memory"]

    #     # total allocated resource
    #     total_cpu_allocated += cpu_allocated
    #     total_memory_allocated += memory_allocated
    
    # # node usage
    # for node in node_metrics.get("items",[]):
    #     node_name = node["metadata"]["name"]
    #     cpu_usage = node["usage"]["cpu"]
    #     memory_usage = node["usage"]["memory"]

    #     # Update total used resources
    #     total_cpu_usage += cpu_usage
    #     total_memory_usage += memory_usage

    # print(node_metrics)

    return