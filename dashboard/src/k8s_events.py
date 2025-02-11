from kubernetes import client, config
from datetime import datetime
from dateutil.tz import tzutc
from dateutil.relativedelta import relativedelta

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
        config.load_kube_config(config_file, context)

        v1 = client.CoreV1Api()

        data = v1.list_event_for_all_namespaces() if namespace == "all" else v1.list_namespaced_event(namespace=namespace)
        events = []

        for event in data.items:
            event_data = {}
            event_data["namespace"] = event.metadata.namespace
            event_data["message"] = event.message
            event_data["object"] = event.involved_object.kind + "/" + event.involved_object.name

            if event.source.component:
                event_data["source"] = event.source.component
                if event.source.host:
                    event_data["source"] = event_data["source"] + ", " + event.source.host
            else:
                event_data["source"] =  event.reporting_component + ", " + event.reporting_instance

            event_data["count"] = event.count
            current_time = datetime.now(tzutc())
            # event_data["last_seen"] = current_time - event.last_timestamp
            event_data["last_seen"] = relativedelta(current_time,event.last_timestamp)
            event_data["type"] = event.type

            events.append(event_data)

        return events

    except client.exceptions.ApiException as e:
        print(f"Kubernetes API Exception: {e}")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []