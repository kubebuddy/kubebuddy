from kubernetes import client, config
from datetime import datetime, timezone
import yaml
from ..utils import calculateAge

def getDeploymentsInfo(path, context, namespace="all"):
    config.load_kube_config(path, context)
    v1 = client.AppsV1Api()
    deployments = v1.list_deployment_for_all_namespaces() if namespace == "all" else v1.list_namespaced_deployment(namespace=namespace)
    deployment_info_list = []

    current_time = datetime.now(timezone.utc)
    
    for deployment in deployments.items:
        namespace = deployment.metadata.namespace
        name = deployment.metadata.name
        ready_replicas = deployment.status.ready_replicas if deployment.status.ready_replicas is not None else 0
        replicas = deployment.spec.replicas
        ready = str(ready_replicas) + "/" + str(replicas)
        
        # Remove timezone info from creation timestamp
        creation_timestamp = deployment.metadata.creation_timestamp
        age = calculateAge(current_time - creation_timestamp)
        
        deployment_info_list.append({
            'namespace': namespace,
            'name': name,
            'ready': ready,
            'age': age
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
    

def get_deploy_events(path, context, namespace, deployment_name):
    config.load_kube_config(config_file=path, context=context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    deployment_events = [event for event in events if event.involved_object.name == deployment_name and event.involved_object.kind == "Deployment"]
    return "\n".join([f"{e.reason}: {e.message}" for e in deployment_events])

def get_yaml_deploy(path, context, namespace, deployment_name):
    config.load_kube_config(config_file=path, context=context)
    v1 = client.AppsV1Api()
    deployment = v1.read_namespaced_deployment(name=deployment_name, namespace=namespace)
    return yaml.dump(deployment.to_dict(), default_flow_style=False)