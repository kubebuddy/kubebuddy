from kubernetes import client, config
from datetime import datetime, timezone
from ..utils import calculateAge
import yaml


def list_kubernetes_services(path, context):
    # Load the kubeconfig with the specified context
    config.load_kube_config(path, context=context)

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
    config.load_kube_config(path, context)
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

    # Get annotations
    annotations = service.metadata.annotations or {}
    # Remove 'kubectl.kubernetes.io/last-applied-configuration' if it's the only annotation
    filtered_annotations = {k: v for k, v in annotations.items() if k != "kubectl.kubernetes.io/last-applied-configuration"}        
        
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
        "annotations": filtered_annotations if filtered_annotations else None,
        "ip_family_policy": getattr(service.spec, "ip_family_policy", "N/A"),
        "ip_families": getattr(service.spec, "ip_families", []),
        "endpoints": endpoints,
        "session_affinity": getattr(service.spec, "session_affinity", "N/A"),
        "internal_traffic_policy": getattr(service.spec, "internal_traffic_policy", "N/A")
    }
    return service_info

def get_service_events(path, context, namespace, service_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    service_events = [
        event for event in events if event.involved_object.name == service_name and event.involved_object.kind == "Service"
    ]
    return "\n".join([f"{e.reason}: {e.message}" for e in service_events])

def get_service_yaml(path, context, namespace, service_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    service = v1.read_namespaced_service(name=service_name, namespace=namespace)
    return yaml.dump(service.to_dict(), default_flow_style=False)