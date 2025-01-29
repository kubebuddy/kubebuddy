from kubernetes import client, config

def getDaemonsetCount():
    config.load_kube_config()
    v1 = client.AppsV1Api() #Create an API client for the AppsV1Api
    deployments = v1.list_daemon_set_for_all_namespaces().items

    return len(deployments)