from kubernetes import client, config
from datetime import datetime, timezone
import yaml
from ..utils import calculateAge

def getReplicaSetsInfo(path, context, namespace="all"):
    config.load_kube_config(path, context)
    v1 = client.AppsV1Api()
    replicaset_info_list = []
    
    if namespace == "all":
        replicasets = v1.list_replica_set_for_all_namespaces().items
    else:
        replicasets = v1.list_namespaced_replica_set(namespace=namespace).items

    now = datetime.now(timezone.utc)
    
    for rs in replicasets:
        # Remove timezone info from creation timestamp
        creation_timestamp = rs.metadata.creation_timestamp
        age = calculateAge(now - creation_timestamp)
        
        # Extracting image names
        image_names = []
        if rs.spec.template.spec.containers:
            for container in rs.spec.template.spec.containers:
                image_names.append(container.image)

        # Extracting selector information
        selector = rs.spec.selector.match_labels if rs.spec.selector else {}

        replicaset_info_list.append({
            'namespace': rs.metadata.namespace,
            'name': rs.metadata.name,
            'desired': rs.spec.replicas,
            'current': rs.status.replicas,
            'ready': rs.status.ready_replicas if rs.status.ready_replicas else 0,
            'age': age,
            'images': image_names,   # List of image names for the ReplicaSet
            'selector': selector     # Labels used as the selector for the ReplicaSet
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

# Add Describe as well

def get_replicaset_events(path, context, namespace, replicaset_name):
    config.load_kube_config(config_file=path, context=context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    rs_events = [event for event in events if event.involved_object.name == replicaset_name and event.involved_object.kind == "ReplicaSet"]
    
    return "\n".join([f"{e.reason}: {e.message}" for e in rs_events])    

def get_yaml_rs(path, context, namespace, rs_name):
    config.load_kube_config(path, context)
    v1 = client.AppsV1Api()
    rs = v1.read_namespaced_replica_set(name=rs_name, namespace=namespace)
    return yaml.dump(rs.to_dict(), default_flow_style=False)
