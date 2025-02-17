from kubernetes import client, config
from datetime import datetime, timezone
from .utils import calculateAge

def getStatefulsetCount():
    config.load_kube_config()
    v1 = client.AppsV1Api() #Create an API client for the AppsV1Api
    statefulsets = v1.list_stateful_set_for_all_namespaces().items

    return len(statefulsets)

def getStatefulsetStatus(path, context, namespace="all"):
    try:
        config.load_kube_config(config_file=path, context=context)
        v1 = client.AppsV1Api()
        statefulsets = v1.list_stateful_set_for_all_namespaces() if namespace == "all" else v1.list_namespaced_stateful_set(namespace=namespace)

        statefulset_status = {
            "Running": 0,
            "Pending": 0,
            "Count": 0
        }

        for statefulset in statefulsets.items:
            if statefulset.status.replicas == statefulset.status.ready_replicas == statefulset.status.available_replicas != None: 
                statefulset_status["Running"] += 1
            else: 
                statefulset_status["Pending"] += 1 
            
            statefulset_status["Count"] += 1

        return statefulset_status
    
    except client.exceptions.ApiException as e:
        print(f"Kubernetes API Exception: {e}")  # Print API errors to stderr
        return []
    except Exception as e:  # Catch other potential errors (e.g., config issues)
        print(f"An error occurred: {e}")  # Print other errors to stderr
        return []
    
def getStatefulsetList(path, context, namespace="all"):
    try:
        config.load_kube_config(config_file=path, context=context)
        v1 = client.AppsV1Api()
        statefulsets = v1.list_stateful_set_for_all_namespaces() if namespace == "all" else v1.list_namespaced_stateful_set(namespace=namespace)

        statefulset_info_list = []
        for statefulset in statefulsets.items:
            namespace = statefulset.metadata.namespace
            name = statefulset.metadata.name
            available_replicas = statefulset.status.available_replicas
            replicas = statefulset.spec.replicas
            ready = str(available_replicas) + "/" + str(replicas)
            difference = (datetime.now(timezone.utc) - statefulset.metadata.creation_timestamp)
            age = calculateAge(difference)
            
            statefulset_info_list.append({
                'namespace': namespace,
                'name': name,
                'ready': ready,
                'age': age
            })
        
        return statefulset_info_list


    except client.exceptions.ApiException as e:
        print(f"Kubernetes API Exception: {e}")  # Print API errors to stderr
        return []
    except Exception as e:  # Catch other potential errors (e.g., config issues)
        print(f"An error occurred: {e}")  # Print other errors to stderr
        return []