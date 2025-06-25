from kubernetes import client, config
import yaml
from datetime import datetime, timezone
from kubebuddy.appLogs import logger
from ..utils import calculateAge, filter_annotations, configure_k8s

def get_np(path, context):
    try:
        configure_k8s(path, context)
        v1 = client.NetworkingV1Api()
        nps = v1.list_network_policy_for_all_namespaces()
        np_list = []
        # np.spec.pod_selector.match_labels
        for np in nps.items:
           np_list.append({
              "namespace": np.metadata.namespace,
              "name": np.metadata.name,
              "pod_selector": ", ".join(f"{k}={v}" for k, v in np.spec.pod_selector.match_labels.items()) if np.spec.pod_selector.match_labels else "None",
              "age": calculateAge(datetime.now(timezone.utc) - np.metadata.creation_timestamp)
           })
        
    except Exception as e:
        logger.error(f"Error fetching np: {e}")
    
    return np_list, len(np_list)

def get_np_description(path=None, context=None, namespace=None, np_name=None):
    configure_k8s(path, context)
    v1 = client.NetworkingV1Api()
    try:
        np = v1.read_namespaced_network_policy(name=np_name, namespace=namespace)

        np_info = {
            "name": np.metadata.name,
            "namespace": np.metadata.name,
            "created_on": np.metadata.creation_timestamp,
            "labels": np.metadata.labels,
            "annotations": filter_annotations(np.metadata.annotations or {}),
            "spec":{
                "pod_selector": np.spec.pod_selector.match_labels,
                "ingress": np.spec.ingress,
                "egress": np.spec.egress,
                "policy_types": np.spec.policy_types
            }
        }
        return np_info

    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch np details: {e.reason}"}


def get_np_events(path, context, namespace, np_name):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    pdb_events = [
        event for event in events if event.involved_object.name == np_name and event.involved_object.kind == "NetworkPolicy"
    ]
    return "\n".join([f"{e.reason}: {e.message}" for e in pdb_events])

def get_np_yaml(path, context, namespace, np_name, managed_fields):
    configure_k8s(path, context)
    v1 = client.NetworkingV1Api()
    np = v1.read_namespaced_network_policy(np_name, namespace=namespace)
    # Filtering Annotations
    if np.metadata:
        np.metadata.annotations = filter_annotations(np.metadata.annotations or {})
    
    api_client = client.ApiClient()
    np_dict = api_client.sanitize_for_serialization(np)

    # Clean up metadata
    if "metadata" in np_dict and not managed_fields:
        for meta_field in [
            "selfLink", "managedFields", "generation"
        ]:
            np_dict["metadata"].pop(meta_field, None)

    return yaml.safe_dump(np_dict, sort_keys=False)