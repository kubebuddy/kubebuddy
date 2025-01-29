from kubernetes import client, config

def getReplicasetCount():
    config.load_kube_config()
    v1 = client.AppsV1Api() #Create an API client for the AppsV1Api
    replicasets = v1.list_replica_set_for_all_namespaces().items

    return len(replicasets)