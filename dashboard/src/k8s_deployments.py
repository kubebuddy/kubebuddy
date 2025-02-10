from kubernetes import client, config

def getDeploymentsCount(config_path, context):
    config.load_kube_config(config_path, context)
    v1 = client.AppsV1Api() #Create an API client for the AppsV1Api
    deployments = v1.list_deployment_for_all_namespaces().items

    return len(deployments)

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