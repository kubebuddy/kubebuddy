from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException
import yaml
from kubebuddy.appLogs import logger
from datetime import datetime, timezone
from ..utils import calculateAge, filter_annotations, configure_k8s

def get_ingress(path, context):
    try:
        configure_k8s(path, context)
        v1 = client.NetworkingV1Api()
        ingresses = v1.list_ingress_for_all_namespaces()
        ingress_list = []
        for ingress in ingresses.items:
            namespace = ingress.metadata.namespace
            name = ingress.metadata.name
            ingress_class = ingress.spec.ingress_class_name
            
            # Extract hosts if present
            hosts = []
            if ingress.spec.rules and isinstance(ingress.spec.rules, list):
                for rule in ingress.spec.rules:
                    if hasattr(rule, 'host') and rule.host:
                        hosts.append(rule.host)
            
            ingress_list.append({
                "namespace": namespace, "name": name, 
                "class": ingress_class,"hosts": hosts
            })
        
    except Exception as e:
        logger.error(f"Error fetching np: {e}")
    
    return ingress_list, len(ingress_list)

def get_ingress_description(path=None, context=None, namespace=None, ingress_name=None):
    configure_k8s(path, context)
    v1 = client.NetworkingV1Api()

    try:
        ingress = v1.read_namespaced_ingress(name=ingress_name, namespace=namespace)

        rules = []
        for rule in ingress.spec.rules or []:
            host = rule.host or "<none>"
            paths = rule.http.paths if rule.http else []
            for path in paths:
                backend_service = path.backend.service.name
                backend_port = path.backend.service.port.name or path.backend.service.port.number

                try:
                    v1_svc = client.CoreV1Api().read_namespaced_service(name=backend_service, namespace=namespace)
                    backend_status = f"{backend_service}:{backend_port}"
                except client.exceptions.ApiException:
                    backend_status = f"{backend_service}:{backend_port} (<error: service '{backend_service}' not found>)"
                
                rules.append({
                    "host": host,
                    "path": path.path or "/",
                    "backend": backend_status
                })

        # Prepare the response
        ingress_info = {
            "name": ingress.metadata.name,
            "labels": ingress.metadata.labels or {},
            "namespace": ingress.metadata.namespace,
            "address": ingress.status.load_balancer.ingress[0].ip if ingress.status.load_balancer.ingress else "<none>",
            "ingress_class": ingress.spec.ingress_class_name if ingress.spec.ingress_class_name else "<none>",
            "rules": rules,
            "annotations": filter_annotations(ingress.metadata.annotations or {})
        }

        return ingress_info

    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch ingress details: {e.reason}"}


def get_ingress_events(path, context, namespace, ingress_name):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    ingress_events = [
        event for event in events 
        if event.involved_object.name == ingress_name and event.involved_object.kind == "Ingress"
    ]
    return "\n".join([f"{e.reason}: {e.message}" for e in ingress_events])

def get_ingress_yaml(path, context, namespace, ingress_name):
    configure_k8s(path, context)
    v1 = client.NetworkingV1Api()
    ingress = v1.read_namespaced_ingress(name=ingress_name, namespace=namespace)
    # Filtering Annotations
    if ingress.metadata:
        ingress.metadata.annotations = filter_annotations(ingress.metadata.annotations or {})
    return yaml.dump(ingress.to_dict(), default_flow_style=False)

def get_ingress_details():
    try:
        config.load_incluster_config()
    except ConfigException:
        config.load_kube_config()

    networking_v1 = client.NetworkingV1Api()
    ingresses = networking_v1.list_ingress_for_all_namespaces()

    def get_age(creation_timestamp):
        delta = datetime.now(timezone.utc) - creation_timestamp
        days = delta.days
        hours = delta.seconds // 3600
        return f"{days}d {hours}h" if days else f"{hours}h"

    ingress_details = []
    for ingress in ingresses.items:
        rules = ingress.spec.rules or []
        paths = []
        hosts = []
        for rule in rules:
            host = rule.host or "N/A"
            hosts.append(host)
            for path in rule.http.paths:
                paths.append(path.path if path.path else "/")
        tls_enabled = "Yes" if ingress.spec.tls else "No"
        ingress_info = {
            "name": ingress.metadata.name,
            "namespace": ingress.metadata.namespace,
            "hosts": ", ".join(hosts),
            "paths": ", ".join(paths),
            "service": ", ".join([
                path.backend.service.name for rule in rules for path in rule.http.paths if path.backend.service
            ]) if rules else "N/A",
            "tls": tls_enabled,
            "age": get_age(ingress.metadata.creation_timestamp)
        }
        ingress_details.append(ingress_info)

    return ingress_details