from kubernetes import client, config

def get_pod_networking(namespace="default"):
    """
    Retrieves networking information about pods in a Kubernetes cluster.

    Args:
        namespace (str, optional): The namespace to query. Defaults to "default".
                                     Use "all" to query all namespaces.

    Returns:
        list: A list of dictionaries, where each dictionary represents a pod
              and contains its networking information. Returns an empty list if no pods
              are found or if there's an error. Prints errors to stderr.
    """
    try:
        config.load_kube_config()
        v1 = client.CoreV1Api()

        if namespace == "all":
            ret = v1.list_pod_for_all_namespaces()
        else:
            ret = v1.list_namespaced_pod(namespace=namespace)

        pod_networking_list = []
        for i in ret.items:
            pod_networking = {
                "Pod Name": i.metadata.name,
                "Namespace": i.metadata.namespace,
                "Pod IP": i.status.pod_ip,
                "Node Name": i.spec.node_name,
                "Host IP": i.status.host_ip,
                "Service Mappings": [],  # We'll populate this later
                "Ingress & Egress Traffic": "Not implemented in this example",  # Requires more advanced techniques
            }

            # Get Service Mappings (This part requires some work)
            # This is a simplified example and might need adjustments based on how
            # your services are configured.  It's not a perfect solution for all cases.
            try:
                core_v1_api = client.CoreV1Api()
                services = core_v1_api.list_namespaced_service(namespace=i.metadata.namespace).items
                for service in services:
                    if service.spec.selector:  # Check if the service has a selector
                        # Check if the pod's labels match the service's selector
                        pod_labels = i.metadata.labels or {}
                        selector_match = True
                        for key, value in service.spec.selector.items():
                            if pod_labels.get(key) != value:
                                selector_match = False
                                break
                        if selector_match:
                            pod_networking["Service Mappings"].append({
                                "Service Name": service.metadata.name,
                                "Service Namespace": service.metadata.namespace,
                                "Ports": [{"name": port.name, "port": port.port, "target_port": port.target_port} for port in service.spec.ports or []]
                            })
            except client.exceptions.ApiException as e:
                print(f"Error getting service info: {e}") # Report error but continue

            pod_networking_list.append(pod_networking)

        return pod_networking_list

    except client.exceptions.ApiException as e:
        print(f"Kubernetes API Exception: {e}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []



if __name__ == "__main__":
    pod_networkings = get_pod_networking(namespace="default")  # or "all"

    if pod_networkings:
        for pod_networking in pod_networkings:
            print("--- Pod Networking ---")
            for key, value in pod_networking.items():
                print(f"{key}: {value}")
            print("-" * 20)
    else:
      print("No pods found or an error occurred.")