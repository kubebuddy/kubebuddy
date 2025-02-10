from kubernetes import client, config

def getReplicasetCount():
    config.load_kube_config()
    v1 = client.AppsV1Api() #Create an API client for the AppsV1Api
    replicasets = v1.list_replica_set_for_all_namespaces().items

    return len(replicasets)

def getReplicasetStatus(path, context, namespace="all"):
    try:
        config.load_kube_config(config_file=path, context=context)
        v1 = client.AppsV1Api()
        replicasets = v1.list_replica_set_for_all_namespaces() if namespace == "all" else v1.list_namespaced_replica_set(namespace=namespace)

        replicaset_status = {
            "Running": 0,
            "Pending": 0,
            "Count": 0
        }

        for replicaset in replicasets.items:
            if replicaset.status.replicas == replicaset.status.ready_replicas == replicaset.status.available_replicas != None: 
                replicaset_status["Running"] += 1
                replicaset_status["Count"] += 1
            else: 
                replicaset_status["Pending"] += 1 
                replicaset_status["Count"] += 1

        return replicaset_status
    
    except client.exceptions.ApiException as e:
        print(f"Kubernetes API Exception: {e}")  # Print API errors to stderr
        return []
    except Exception as e:  # Catch other potential errors (e.g., config issues)
        print(f"An error occurred: {e}")  # Print other errors to stderr
        return []