from kubernetes import client, config

def getStatefulsetCount():
    config.load_kube_config()
    v1 = client.AppsV1Api() #Create an API client for the AppsV1Api
    statefulsets = v1.list_stateful_set_for_all_namespaces().items

    return len(statefulsets)