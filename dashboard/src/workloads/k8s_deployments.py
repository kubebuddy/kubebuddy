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
        images = []

        for container in deployment.spec.template.spec.containers:
            images.append(container.image)
        
        # Remove timezone info from creation timestamp
        creation_timestamp = deployment.metadata.creation_timestamp
        age = calculateAge(current_time - creation_timestamp)
        
        deployment_info_list.append({
            'namespace': namespace,
            'name': name,
            'ready': ready,
            'age': age,
            'images': images
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

def get_deployment_description(path=None, context=None, namespace=None, dep_name=None):
    config.load_kube_config(path, context)
    v1 = client.AppsV1Api()
    
    try:
        # Fetch Deployment details
        dep = v1.read_namespaced_deployment(name=dep_name, namespace=namespace)

        # Prepare Deployment information
        dep_info = {
            "name": dep.metadata.name,
            "namespace": dep.metadata.namespace,
            "creation_timestamp": dep.metadata.creation_timestamp,
            "labels": list(dep.metadata.labels.items()) if dep.metadata.labels else [],
            "annotations": list(dep.metadata.annotations.items()) if dep.metadata.annotations else [],
            "replicas": {
                "desired": dep.status.replicas,  # Desired number of replicas
                "updated": dep.status.updated_replicas,  # Number of updated replicas
                "total": dep.status.replicas,  # Total number of replicas (desired)
                "available": dep.status.available_replicas if hasattr(dep.status, 'available_replicas') else 0,
                "unavailable": dep.status.unavailable_replicas if hasattr(dep.status, 'unavailable_replicas') else 0,
            },
            "strategy": {
                "type": dep.spec.strategy.type,  # Deployment strategy (RollingUpdate)
                "rolling_update": {
                    "max_unavailable": dep.spec.strategy.rolling_update.max_unavailable if dep.spec.strategy.type == "RollingUpdate" else None,
                    "max_surge": dep.spec.strategy.rolling_update.max_surge if dep.spec.strategy.type == "RollingUpdate" else None
                },
                "min_ready_seconds": dep.spec.min_ready_seconds
            },
            "pod_template": {
                "labels": list(dep.spec.template.metadata.labels.items()) if dep.spec.template.metadata.labels else [],
                "containers": [
                    {
                        "name": container.name,
                        "image": container.image,
                        "ports": [port.container_port for port in (container.ports or [])],
                        "env": [env.name for env in (container.env or [])],
                        "mounts": [mount.mount_path for mount in (container.volume_mounts or [])]
                    }
                    for container in dep.spec.template.spec.containers
                ],
                "volumes": [
                    {
                        "name": volume.name,
                        "type": volume.secret or volume.config_map or volume.projected
                    }
                    for volume in (dep.spec.template.spec.volumes or [])
                ],
                "node_selectors": dep.spec.template.spec.node_selector.items() if dep.spec.template.spec.node_selector else [],
                "tolerations": dep.spec.template.spec.tolerations
            },
            "conditions": [
                {
                    "type": condition.type,
                    "status": condition.status,
                    "reason": condition.reason
                }
                for condition in (dep.status.conditions or [])
            ],
            "old_replicasets": dep.status.oldReplicaSets if hasattr(dep.status, 'oldReplicaSets') else [],
            "new_replicaset": dep.status.newReplicaSet.name if hasattr(dep.status, 'newReplicaSet') else None
        }

        return dep_info
    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch Deployment details: {e.reason}"}


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