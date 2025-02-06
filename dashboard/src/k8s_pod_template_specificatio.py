from kubernetes import client, config

def get_replicaset_pod_info(namespace="default"):
    """Retrieves pod template information from ReplicaSets.

    Args:
        namespace (str): The Kubernetes namespace to query (default: "default").

    Returns:
        list: A list of dictionaries, where each dictionary contains pod template
              information about a ReplicaSet. Returns an empty list if no
              ReplicaSets are found or an error occurs. Prints error info to stderr.
    """
    try:
        config.load_kube_config()  # Or config.load_incluster_config() if running in a pod
        apps_v1_api = client.AppsV1Api()
        replicasets = apps_v1_api.list_namespaced_replica_set(namespace=namespace)

        pod_info_list = []

        for rs in replicasets.items:
            pod_info = {
                "Name": rs.metadata.name,
                "Namespace": rs.metadata.namespace,
                "Pod Selector": rs.spec.selector.match_labels if rs.spec.selector and rs.spec.selector.match_labels else {},  # Handle None
                "Containers": [],
            }

            template = rs.spec.template
            if template and template.spec and template.spec.containers: # Handle None
                for container in template.spec.containers:
                    container_info = {
                        "Name": container.name,
                        "Image": container.image,
                        "Ports": [port.container_port for port in container.ports] if container.ports else [],  # Handle None
                        "Resources": {
                            "Limits": container.resources.limits if container.resources and container.resources.limits else {}, # Handle None
                            "Requests": container.resources.requests if container.resources and container.resources.requests else {}, # Handle None
                        },
                    }
                    pod_info["Containers"].append(container_info)
            else:
                pod_info["Containers"] = "No containers defined" # Handle no containers case

            pod_info_list.append(pod_info)

        return pod_info_list

    except client.ApiException as e:
        print(f"Kubernetes API Exception: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        return []

import sys

if __name__ == "__main__":
    namespace_to_check = "default"
    pod_data = get_replicaset_pod_info(namespace=namespace_to_check)

    if pod_data:
        print(f"Pod Template Information in namespace '{namespace_to_check}':")
        for rs_info in pod_data:
            print("-" * 20)
            for key, value in rs_info.items():
                print(f"{key}: {value}")
            print("-" * 20)
    else:
        print(f"No ReplicaSets found in namespace '{namespace_to_check}' or an error occurred.", file=sys.stderr)