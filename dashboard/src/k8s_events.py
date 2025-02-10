from kubernetes import client, config

def get_events(config_file, context, namespace = "all"):
    """
    Retrieves events for a particular namesapce.

    Args:
        config_file (str, required): The path of config file to use for cluster selection.

        context (str, required): The context to use for API call.

        namespace (str, optional): The namespace to query. Defaults to "all" to query all namespaces.

    Returns:
        list: A 

    """

    try:
        config.load_kube_config(config_file=config_file, context=context)

        v1 = client.CoreV1Api()

        data = v1.list_event_for_all_namespaces() if namespace == "all" else v1.list_namespaced_event(namespace=namespace, pretty=True)

        # print(data)

    except client.exceptions.ApiException as e:
        print(f"Kubernetes API Exception: {e}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []