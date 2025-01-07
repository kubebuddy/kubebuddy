from kubernetes import client, config

def getpods():
    config.load_kube_config()
    v1 = client.CoreV1Api()
    pods = v1.list_pod_for_all_namespaces()
    pod_names = [pod.metadata.name for pod in pods.items]
    podlist = []
    for name in pod_names:
        podlist.append(name)
    return podlist, len(podlist)