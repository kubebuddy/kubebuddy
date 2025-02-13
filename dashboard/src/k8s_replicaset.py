from kubernetes import client, config
from datetime import datetime

def getReplicaSetsInfo(path, context, namespace="all"):
    config.load_kube_config(path, context)
    v1 = client.AppsV1Api()
    replicaset_info_list = []
    
    if namespace == "all":
        replicasets = v1.list_replica_set_for_all_namespaces().items
    else:
        replicasets = v1.list_namespaced_replica_set(namespace=namespace).items

    now = datetime.now()
    
    for rs in replicasets:
        # Remove timezone info from creation timestamp
        creation_timestamp_naive = rs.metadata.creation_timestamp.replace(tzinfo=None)
        age = now - creation_timestamp_naive
        age_str = str(age).split('.')[0]  # Remove microseconds for a cleaner format
        
        replicaset_info_list.append({
            'namespace': rs.metadata.namespace,
            'name': rs.metadata.name,
            'desired': rs.spec.replicas,
            'current': rs.status.replicas,
            'ready': rs.status.ready_replicas if rs.status.ready_replicas else 0,
            'age': age_str
        })
    
    return replicaset_info_list

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