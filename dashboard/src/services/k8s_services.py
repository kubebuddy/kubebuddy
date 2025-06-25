from kubernetes import client, config
from datetime import datetime, timezone
from ..utils import calculateAge, filter_annotations, configure_k8s
from kubebuddy.appLogs import logger
import yaml


def list_kubernetes_services(path, context):
    # Load the kubeconfig with the specified context
    configure_k8s(path, context)

    # Create Kubernetes API client
    v1 = client.CoreV1Api()

    # Fetch all services in all namespaces
    services = v1.list_service_for_all_namespaces(watch=False)

    # Prepare data for Jinja template
    service_data = []
    for svc in services.items:
        name = svc.metadata.name
        namespace = svc.metadata.namespace
        svc_type = svc.spec.type
        cluster_ip = svc.spec.cluster_ip
        external_ip = ", ".join(svc.status.load_balancer.ingress[0].ip 
                                for svc.status.load_balancer.ingress in (svc.status.load_balancer.ingress or []) 
                                if svc.status.load_balancer.ingress) or "-"
        ports = ", ".join(f"{p.port}/{p.protocol}" for p in svc.spec.ports)
        age = calculateAge(datetime.now(timezone.utc) - svc.metadata.creation_timestamp)
        selector = svc.spec.selector

        service_data.append({
            "namespace": namespace,
            "name": name,
            "type": svc_type,
            "cluster_ip": cluster_ip,
            "external_ip": external_ip,
            "ports": ports,
            "age": age,
            "selector": selector
        })

    return service_data


def get_service_description(path=None, context=None, namespace=None, service_name=None):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    service = v1.read_namespaced_service(name=service_name, namespace=namespace)
    
    # Get Endpoints related to this service
    endpoints = None
    try:
        endpoints_obj = v1.read_namespaced_endpoints(name=service_name, namespace=namespace)
        endpoints = []
        if endpoints_obj.subsets:
            for subset in endpoints_obj.subsets:
                addresses = [addr.ip for addr in subset.addresses] if subset.addresses else []
                ports = [{"port": port.port, "protocol": port.protocol, "name": port.name} 
                        for port in subset.ports] if subset.ports else []
                endpoints.append({"addresses": addresses, "ports": ports})
    except client.exceptions.ApiException:
        # Endpoints might not exist for this service
        pass
    
    load_balancer_ip = "N/A"
    external_ips = []  # Initialize to an empty list
    if service.spec.type == "LoadBalancer" and hasattr(service.status, "load_balancer") and service.status.load_balancer and hasattr(service.status.load_balancer, "ingress") and service.status.load_balancer.ingress:
        ingress = service.status.load_balancer.ingress[0]
        load_balancer_ip = getattr(ingress, "ip", "N/A")

        for ingress in service.status.load_balancer.ingress:  # For external_ips
            if hasattr(ingress, "ip") and ingress.ip:
                external_ips.append(ingress.ip)

    service_info = {
        "name": service.metadata.name,
        "namespace": service.metadata.namespace,
        "type": service.spec.type,
        "cluster_ip": service.spec.cluster_ip,
        "ports": [
            {
                "name": port.name,
                "protocol": port.protocol,
                "port": port.port,
                "target_port": port.target_port,
                "node_port": getattr(port, "node_port", "N/A"), # Handle missing node_port
            }
            for port in service.spec.ports
        ],
        "selector": service.spec.selector,
        "load_balancer_ip": load_balancer_ip,
        "external_ips": external_ips,
        
        # Added fields
        "labels": service.metadata.labels if hasattr(service.metadata, "labels") else {},
        "annotations": filter_annotations(service.metadata.annotations or {}),
        "ip_family_policy": getattr(service.spec, "ip_family_policy", "N/A"),
        "ip_families": getattr(service.spec, "ip_families", []),
        "endpoints": endpoints,
        "session_affinity": getattr(service.spec, "session_affinity", "N/A"),
        "internal_traffic_policy": getattr(service.spec, "internal_traffic_policy", "N/A")
    }
    return service_info

def get_service_events(path, context, namespace, service_name):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    service_events = [
        event for event in events if event.involved_object.name == service_name and event.involved_object.kind == "Service"
    ]
    return "\n".join([f"{e.reason}: {e.message}" for e in service_events])

def get_service_yaml(path, context, namespace, service_name, managed_fields):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    service = v1.read_namespaced_service(name=service_name, namespace=namespace)
    # Filtering Annotations
    if service.metadata:
        service.metadata.annotations = filter_annotations(service.metadata.annotations or {})
    
    api_client = client.ApiClient()
    service_dict = api_client.sanitize_for_serialization(service)

    # Clean up metadata
    if "metadata" in service_dict and not managed_fields:
        for meta_field in [
            "selfLink", "managedFields", "generation"
        ]:
            service_dict["metadata"].pop(meta_field, None)

    return yaml.safe_dump(service_dict, sort_keys=False)

def get_service_details(namespace=None):
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()

    v1 = client.CoreV1Api()
    services = v1.list_namespaced_service(namespace) if namespace else v1.list_service_for_all_namespaces()

    def get_age(created_at):
        delta = datetime.now(timezone.utc) - created_at
        days = delta.days
        hours = delta.seconds // 3600
        return f"{days}d {hours}h" if days else f"{hours}h"

    service_details = []
    for svc in services.items:
        ports = ", ".join(
            f"{p.port}/{p.protocol}" + (f" → {p.target_port}" if p.target_port else "")
            for p in svc.spec.ports or []
        )

        external_ips = svc.status.load_balancer.ingress
        external_ip = ", ".join(ip.ip if ip.ip else ip.hostname for ip in external_ips) if external_ips else "None"

        service_details.append({
            'name': svc.metadata.name,
            'namespace': svc.metadata.namespace,
            'type': svc.spec.type,
            'cluster_ip': svc.spec.cluster_ip,
            'external_ip': external_ip,
            'ports': ports,
            'age': get_age(svc.metadata.creation_timestamp)
        })

    return service_details