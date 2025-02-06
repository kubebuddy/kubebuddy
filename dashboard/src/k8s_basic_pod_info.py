from kubernetes import client, config
from datetime import datetime

def get_pod_info(namespace="default"):
    """
    Retrieves basic information about pods in a Kubernetes cluster.

    Args:
        namespace (str, optional): The namespace to query. Defaults to "default".
                                     Use "all" to query all namespaces.

    Returns:
        list: A list of dictionaries, where each dictionary represents a pod
              and contains its information.  Returns an empty list if no pods
              are found or if there's an error.  Prints errors to stderr.
    """
    try:
        config.load_kube_config()

        v1 = client.CoreV1Api()

        if namespace == "all":
            ret = v1.list_pod_for_all_namespaces()
        else:
            ret = v1.list_namespaced_pod(namespace=namespace)

        pod_info_list = []
        for i in ret.items:
            pod_info = {
                "Pod Name": i.metadata.name,
                "Namespace": i.metadata.namespace,
                "Labels": i.metadata.labels or {},  # Handle cases where labels are None
                "Annotations": i.metadata.annotations or {}, # Handle cases where annotations are None
                "Creation Time": i.metadata.creation_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if i.metadata.creation_timestamp else "N/A", # Format time or handle missing timestamps
            }
            pod_info_list.append(pod_info)

        return pod_info_list

    except client.exceptions.ApiException as e:
        print(f"Kubernetes API Exception: {e}")  # Print API errors to stderr
        return []
    except Exception as e:  # Catch other potential errors (e.g., config issues)
        print(f"An error occurred: {e}")  # Print other errors to stderr
        return []


if __name__ == "__main__":
    pods = get_pod_info(namespace="default") # Get pods in the 'default' namespace
    # pods = get_pod_info(namespace="all") # Get pods in all namespaces

    if pods:
        for pod in pods:
            print("--- Pod Information ---")
            for key, value in pod.items():
                print(f"{key}: {value}")
            print("-" * 20)  # Separator between pods
    else:
      print("No pods found or an error occurred.")