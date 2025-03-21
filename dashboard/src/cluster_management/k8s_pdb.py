from kubernetes import client, config
import yaml
from datetime import datetime, timezone
from kubebuddy.appLogs import logger
from ..utils import calculateAge

def get_pdb(path, context):
    # Load Kubernetes configuration
    try:
        config.load_kube_config(path, context)
        v1 = client.PolicyV1Api()
        pdbs = v1.list_pod_disruption_budget_for_all_namespaces()
        pdb_list = []
        for pdb in pdbs.items:
           pdb_list.append({
              "namespace": pdb.metadata.namespace,
              "name": pdb.metadata.name,
              "min": pdb.spec.min_available or "N/A",
              "max": pdb.spec.max_unavailable or "N/A",
              "disruptions": pdb.status.disruptions_allowed,
              "age": calculateAge(datetime.now(timezone.utc) - pdb.metadata.creation_timestamp)
           })
        
    except Exception as e:
        logger.error(f"Error fetching PDB: {e}")
    
    return pdb_list, len(pdb_list)
        

def get_pdb_description(path=None, context=None, namespace=None, pdb_name=None):
    config.load_kube_config(path, context)
    v1 = client.PolicyV1Api()
    try:
        pdb = v1.read_namespaced_pod_disruption_budget(name=pdb_name, namespace=namespace)
        pdb_info = {
            "name": pdb.metadata.name,
            "namespace": pdb.metadata.namespace,
            "min": pdb.spec.min_available,
            "max": pdb.spec.max_unavailable,
            "selector": pdb.spec.selector.match_labels,
            "status": {
               "Allowed Disruptions": pdb.status.disruptions_allowed,
               "Current": pdb.status.current_healthy,
               "Desired": pdb.status.desired_healthy,
               "Total": pdb.status.expected_pods,
            }
        }

        return pdb_info

    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch pdb details: {e.reason}"}


def get_pdb_events(path, context, namespace, pdb_name):
    config.load_kube_config(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    pdb_events = [
        event for event in events if event.involved_object.name == pdb_name and event.involved_object.kind == "PodDisruptionBudget"
    ]
    return "\n".join([f"{e.reason}: {e.message}" for e in pdb_events])

def get_pdb_yaml(path, context, namespace, pdb_name):
    config.load_kube_config(path, context)
    v1 = client.PolicyV1Api()
    pdb = v1.list_namespaced_pod_disruption_budget(namespace=namespace)
    return yaml.dump(pdb.to_dict(), default_flow_style=False)