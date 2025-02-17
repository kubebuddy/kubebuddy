from kubernetes import client, config
from datetime import datetime

def getDeploymentsInfo(path, context, namespace="all"):
    config.load_kube_config(path, context)
    v1 = client.AppsV1Api()
    deployments = v1.list_deployment_for_all_namespaces() if namespace == "all" else v1.list_namespaced_deployment(namespace=namespace)
    deployment_info_list = []

    current_time = datetime.now()  # Current local time without timezone info
    
    for deployment in deployments.items:
        namespace = deployment.metadata.namespace
        name = deployment.metadata.name
        ready_replicas = deployment.status.ready_replicas if deployment.status.ready_replicas is not None else 0
        replicas = deployment.status.replicas
        ready = str(ready_replicas) + "/" + str(replicas)
        
        # Remove timezone info from creation timestamp
        creation_timestamp_naive = deployment.metadata.creation_timestamp.replace(tzinfo=None)
        age = current_time - creation_timestamp_naive
        age_in_days = age.days  # Get the number of days
        
        deployment_info_list.append({
            'namespace': namespace,
            'name': name,
            'ready': ready,
            'age': f"{age_in_days}d"
        })

    return deployment_info_list

def getDeploymentsStatus(path, context, namespace="all"):
    try:
        config.load_kube_config(path, context)
        v1 = client.AppsV1Api()
        deployments = v1.list_deployment_for_all_namespaces() if namespace == "all" else v1.list_namespaced_deployment(namespace=namespace)

        deployment_status = {
            "Running": 0,
            "Pending": 0,
            "Count": 0
        }

        for deployment in deployments.items:
            if deployment.status.replicas == deployment.status.ready_replicas == deployment.status.available_replicas != None: 
                deployment_status["Running"] += 1
                deployment_status["Count"] += 1
            else: 
                deployment_status["Pending"] += 1 
                deployment_status["Count"] += 1

        return deployment_status
    
    except client.exceptions.ApiException as e:
        print(f"Kubernetes API Exception: {e}")  # Print API errors to stderr
        return []
    except Exception as e:  # Catch other potential errors (e.g., config issues)
        print(f"An error occurred: {e}")  # Print other errors to stderr
        return []