from kubernetes import client, config
import sys

def get_replicaset_info(namespace="default"):
    """
    Retrieves information about ReplicaSets in a given Kubernetes namespace.

    Args:
        namespace (str): The Kubernetes namespace to query (default: "default").

    Returns:
        list: A list of dictionaries, where each dictionary contains information
              about a ReplicaSet.  Returns an empty list if no ReplicaSets are found
              or if there's an error.  Prints error information to stderr.
    """
    try:
        # Load Kubernetes configuration.  This will look for a kubeconfig file
        # in the default location (~/.kube/config) or environment variables.  You
        # can also specify a path: config.load_kube_config("/path/to/kubeconfig")
        config.load_kube_config()  # Or config.load_incluster_config() if running inside a pod

        v1_api = client.AppsV1Api()
        replicasets = v1_api.list_namespaced_replica_set(namespace=namespace)

        replicaset_info_list = []

        for rs in replicasets.items:
            info = {
                "Name": rs.metadata.name,
                "Namespace": rs.metadata.namespace,
                "UID": rs.metadata.uid,
                "Labels": rs.metadata.labels if rs.metadata.labels else {},  # Handle potential None
                "Annotations": rs.metadata.annotations if rs.metadata.annotations else {}, # Handle potential None
            }
            replicaset_info_list.append(info)

        return replicaset_info_list

    except client.ApiException as e:
        print(f"Kubernetes API Exception: {e}", file=sys.stderr)  # Print to stderr for errors
        return []  # Return empty list to indicate failure
    except Exception as e:  # Catch other exceptions like file not found, etc.
        print(f"An error occurred: {e}", file=sys.stderr)
        return []