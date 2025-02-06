from kubernetes import client, config

def get_replicaset_status_info(namespace="default"):
    """Retrieves status information for ReplicaSets.

    Args:
        namespace (str): The Kubernetes namespace to query (default: "default").

    Returns:
        list: A list of dictionaries, where each dictionary contains status
              information about a ReplicaSet. Returns an empty list if no
              ReplicaSets are found or an error occurs. Prints error info
              to stderr.
    """
    try:
        config.load_kube_config()  # Or config.load_incluster_config() if in pod
        apps_v1_api = client.AppsV1Api()
        replicasets = apps_v1_api.list_namespaced_replica_set(namespace=namespace)

        status_info_list = []

        for rs in replicasets.items:
            status_info = {
                "Name": rs.metadata.name,
                "Namespace": rs.metadata.namespace,
                "Observed Generation": rs.status.observed_generation,  # No need to handle None, it can be None
                "Min Ready Seconds": rs.spec.min_ready_seconds if rs.spec.min_ready_seconds is not None else None,
            }
            status_info_list.append(status_info)

        return status_info_list

    except client.ApiException as e:
        print(f"Kubernetes API Exception: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        return []

import sys

if __name__ == "__main__":
    namespace_to_check = "default"
    rs_status_data = get_replicaset_status_info(namespace=namespace_to_check)

    if rs_status_data:
        print(f"ReplicaSet Status Information in namespace '{namespace_to_check}':")
        for rs_info in rs_status_data:
            print("-" * 20)
            for key, value in rs_info.items():
                print(f"{key}: {value}")
            print("-" * 20)
    else:
        print(f"No ReplicaSets found in namespace '{namespace_to_check}' or an error occurred.", file=sys.stderr)