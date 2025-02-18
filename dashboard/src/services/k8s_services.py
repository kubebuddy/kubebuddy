from kubernetes import client, config
from datetime import datetime
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
                                if svc.status.load_balancer.ingress) or "None"
        ports = ", ".join(f"{p.port}/{p.protocol}" for p in svc.spec.ports)
        selector = svc.spec.selector if svc.spec.selector else "None"
        age = (datetime.utcnow() - svc.metadata.creation_timestamp.replace(tzinfo=None)).days

        service_data.append({
            "namespace": namespace,
            "name": name,
            "type": svc_type,
            "cluster_ip": cluster_ip,
            "external_ip": external_ip,
            "ports": ports,
            "selector": selector,
            "age": f"{age}d"
        })

    return service_data