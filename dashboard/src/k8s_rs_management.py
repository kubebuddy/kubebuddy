from kubernetes import client, config
import sys

def get_replicaset_replica_info(namespace="default"):
    """
    Retrieves replica management information about ReplicaSets in a given namespace.

    Args:
        namespace (str): The Kubernetes namespace to query (default: "default").

    Returns:
        list: A list of dictionaries, where each dictionary contains replica
              information about a ReplicaSet. Returns an empty list if no 
              ReplicaSets are found or an error occurs. Prints error info to stderr.
    """
    try:
        config.load_kube_config()  # Or config.load_incluster_config() if running in a pod
        v1_api = client.AppsV1Api()
        replicasets = v1_api.list_namespaced_replica_set(namespace=namespace)

        replica_info_list = []

        for rs in replicasets.items:
            info = {
                "Name": rs.metadata.name,  # Include name for easy identification
                "Namespace": rs.metadata.namespace, # Include namespace
                "Desired Replicas": rs.spec.replicas,
                "Current Replicas": rs.status.replicas if rs.status.replicas is not None else 0, # Handle None
                "Ready Replicas": rs.status.ready_replicas if rs.status.ready_replicas is not None else 0, # Handle None
                "Available Replicas": rs.status.available_replicas if rs.status.available_replicas is not None else 0, # Handle None
            }
            replica_info_list.append(info)

        return replica_info_list

    except client.ApiException as e:
        print(f"Kubernetes API Exception: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        return []


