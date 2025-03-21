from kubernetes import client, config
from datetime import datetime
from dateutil.tz import tzutc
from kubebuddy.appLogs import logger
from dateutil.relativedelta import relativedelta

def get_events(config_file, context, limit, namespace = "all"):
    try:
        config.load_kube_config(config_file, context)

        v1 = client.CoreV1Api()

        if limit:
            data = v1.list_event_for_all_namespaces(limit=30) if namespace == "all" else v1.list_namespaced_event(namespace=namespace, limit = 30)
        else:
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
            
            temp = relativedelta(current_time,event.last_timestamp)
            years = temp.years
            months = temp.months
            days = temp.days
            hours = temp.hours
            minutes = temp.minutes
            seconds = temp.seconds

            if years > 0:
                temp = f"{years}y"
            elif months > 0:
                temp = f"{months}mo"
            elif days > 0:
                temp = f"{days}d"
            elif hours > 0:
                temp = f"{hours}h"
            elif minutes > 0:
                temp = f"{minutes}m"
            else:
                temp = f"{seconds}s"

            event_data["last_seen"] = temp

            event_data["type"] = event.type

            events.append(event_data)

        return events

    except client.exceptions.ApiException as e:
        logger(f"Kubernetes API Exception: {e}")
        return []
    except Exception as e:
        logger(f"An error occurred: {e}")
        return []