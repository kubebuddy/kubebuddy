from kubernetes import client, config
from datetime import datetime

def get_pod_status(namespace="default"):
    """
    Retrieves status information about pods in a Kubernetes cluster.

    Args:
        namespace (str, optional): The namespace to query. Defaults to "default".
                                     Use "all" to query all namespaces.

    Returns:
        list: A list of dictionaries, where each dictionary represents a pod
              and contains its status information. Returns an empty list if no pods
              are found or if there's an error. Prints errors to stderr.
    """
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()

        if namespace == "all":
            ret = v1.list_pod_for_all_namespaces()
        else:
            ret = v1.list_namespaced_pod(namespace=namespace)

        pod_status_list = []
        for i in ret.items:
            conditions = []
            if i.status.conditions:
                for condition in i.status.conditions:
                    conditions.append({
                        "type": condition.type,
                        "status": condition.status,
                        "reason": condition.reason,  # Add reason for condition if available
                        "message": condition.message # Add message for condition if available
                    })

            pod_status = {
                "Pod Name": i.metadata.name, # Include pod name for context
                "Namespace": i.metadata.namespace,
                "Phase": i.status.phase,
                "Conditions": conditions,
                "QoS Class": i.status.qos_class,
                "Restart Count": sum([container.restart_count for container in i.status.container_statuses or []]) if i.status.container_statuses else 0,  # Correct restart count calculation
            }
            pod_status_list.append(pod_status)

        return pod_status_list

    except client.exceptions.ApiException as e:
        print(f"Kubernetes API Exception: {e}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []



if __name__ == "__main__":
    pod_statuses = get_pod_status(namespace="default") # or "all" for all namespaces

    if pod_statuses:
        for pod_status in pod_statuses:
            print("--- Pod Status ---")
            for key, value in pod_status.items():
                print(f"{key}: {value}")
            print("-" * 20)
    else:
      print("No pods found or an error occurred.")