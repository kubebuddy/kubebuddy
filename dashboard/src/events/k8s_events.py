from kubernetes import client
from datetime import datetime
from dateutil.tz import tzutc
from kubebuddy.appLogs import logger
from dateutil.relativedelta import relativedelta
from ..utils import configure_k8s

def get_events(config_file, context, limit, namespace = "all"):
    try:
        configure_k8s(config_file, context)

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
            kind = event.involved_object.kind or ""
            name = event.involved_object.name or ""
            event_data["object"] = f"{kind}/{name}" if kind or name else ""

            # Handle the 'source' field safely
            component = event.source.component
            host = event.source.host

            if component:
                event_data["source"] = component
                if host:
                    event_data["source"] += f", {host}"
            else:
                reporting_component = event.reporting_component or ""
                reporting_instance = event.reporting_instance or ""
                parts = [p for p in [reporting_component, reporting_instance] if p]
                event_data["source"] = ", ".join(parts) if parts else "unknown"

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
        logger.error(f"Kubernetes API Exception: {e}")
        return []
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return []