from kubernetes import client, config
from datetime import datetime, timezone
from .utils import calculateAge

def getDaemonsetCount():
    config.load_kube_config()
    v1 = client.AppsV1Api() #Create an API client for the AppsV1Api
    deployments = v1.list_daemon_set_for_all_namespaces().items

    return len(deployments)

def getDaemonsetStatus(path, context, namespace="all"):
    try:
        config.load_kube_config(config_file=path, context=context)
        v1 = client.AppsV1Api()
        daemonsets = v1.list_daemon_set_for_all_namespaces() if namespace == "all" else v1.list_namespaced_daemon_set(namespace=namespace)

        daemonset_status = {
            "Running": 0,
            "Pending": 0,
            "Count": 0
        }

        for daemonset in daemonsets.items:
            if daemonset.status.number_ready == daemonset.status.desired_number_scheduled == daemonset.status.current_number_scheduled != None: 
                daemonset_status["Running"] += 1
            else: 
                daemonset_status["Pending"] += 1 
            
            daemonset_status["Count"] += 1

        return daemonset_status
    
    except client.exceptions.ApiException as e:
        print(f"Kubernetes API Exception: {e}")  # Print API errors to stderr
        return []
    except Exception as e:  # Catch other potential errors (e.g., config issues)
        print(f"An error occurred: {e}")  # Print other errors to stderr
        return []
    
def getDaemonsetList(path, context, namespace="all"):
    try:
        config.load_kube_config(config_file=path, context=context)
        v1 = client.AppsV1Api()
        daemonsets = v1.list_daemon_set_for_all_namespaces() if namespace == "all" else v1.list_namespaced_daemon_set(namespace=namespace)

        daemonset_info_list = []
        for daemonset in daemonsets.items:
            namespace = daemonset.metadata.namespace
            name = daemonset.metadata.name
            desired = daemonset.status.desired_number_scheduled
            current = daemonset.status.current_number_scheduled
            ready = daemonset.status.number_ready
            difference = (datetime.now(timezone.utc) - daemonset.metadata.creation_timestamp)
            age = calculateAge(difference)
            
            daemonset_info_list.append({
                'namespace': namespace,
                'name': name,
                'desired': desired,
                'current': current,
                'ready': ready,
                'age': age
            })
        
        return daemonset_info_list
    
    except client.exceptions.ApiException as e:
        print(f"Kubernetes API Exception: {e}")  # Print API errors to stderr
        return []
    except Exception as e:  # Catch other potential errors (e.g., config issues)
        print(f"An error occurred: {e}")  # Print other errors to stderr
        return []