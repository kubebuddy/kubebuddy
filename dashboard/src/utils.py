from kubernetes import client, config
from google.auth import default
from google.cloud.container_v1 import ClusterManagerClient
import tempfile
import base64
import os
import yaml
from kubebuddy.appLogs import logger
from deepdiff import DeepDiff
import json
import boto3
import subprocess

# Age calculation
def calculateAge(timedelta_obj):
    total_seconds = timedelta_obj.total_seconds()

    if total_seconds < 60:
        return str(int(total_seconds)) + "s"
    elif total_seconds < 3600:
        return str(int(total_seconds/60)) + "m"
    elif total_seconds < 86400:
        return str(int(total_seconds/3600)) + "h"
    else:
        return str(timedelta_obj.days) + "d"
    

def filter_annotations(annotations):
    if not annotations:
        return None
    filtered_annotations = {k: v for k, v in annotations.items() if k != "kubectl.kubernetes.io/last-applied-configuration"} 
    return filtered_annotations if filtered_annotations else None

def configure_k8s(path: str, context: str):
    if context.startswith('gke_'):
        # Handle GKE
        SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
        credentials, project = default(scopes=SCOPES)
        cluster_manager_client = ClusterManagerClient(credentials=credentials)

        # Extract GKE details from context_name: gke_{project}_{zone}_{cluster_name}
    
        _, project_id, zone, cluster_id = context.split('_', 3) # Have removed the try block assuming context is always in this format

        gke_cluster = cluster_manager_client.get_cluster(
            project_id=project_id,
            zone=zone,
            cluster_id=cluster_id
        )

        cert = base64.b64decode(gke_cluster.master_auth.cluster_ca_certificate)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".crt") as cert_file:
            cert_file.write(cert)
            cert_path = cert_file.name

        configuration = client.Configuration()
        configuration.host = f"https://{gke_cluster.endpoint}:443"
        configuration.ssl_ca_cert = cert_path
        configuration.verify_ssl = True
        configuration.api_key = {"authorization": "Bearer " + credentials.token}
        client.Configuration.set_default(configuration)

    elif context.startswith('arn:aws:eks:'):
        # currently using context for cluster name and user as well, if need be we can read the file and get the relevant data
        # Get token
        region = context.split(':')[3]
        name = context.split(':')[5].split('/')[1]
        eks = boto3.client('eks', region_name=region)
        cluster_info = eks.describe_cluster(name=name)
        cluster_cert = cluster_info['cluster']['certificateAuthority']['data']
        cluster_endpoint = cluster_info['cluster']['endpoint']

        # Generate token
        token = boto3.client('sts').get_caller_identity()
        auth_token = subprocess.check_output(
            ['aws', 'eks', 'get-token', '--cluster-name', context, '--region', region, '--output', 'json']
        )
        token_data = json.loads(auth_token)
        bearer_token = token_data['status']['token']
        # Build config manually

        config_dict = {
            'apiVersion': 'v1',
            'clusters': [{
                'cluster': {
                    'server': cluster_endpoint,
                    'certificate-authority-data': cluster_cert
                },
                'name': context
            }],
            'contexts': [{
                'context': {
                    'cluster': context,
                    'user': context
                },
                'name': context
            }],
            'current-context': context,
            'kind': 'Config',
            'users': [{
                'name': context,
                'user': {
                    'token': bearer_token
                }
            }]
        }

        config.load_kube_config_from_dict(config_dict)
    else:
        config.load_kube_config(config_file=path, context=context)


# Map resource kinds to API client and patch methods
K8S_RESOURCE_MAP = {
    "Pod": {
        "api": client.CoreV1Api,
        "patch_func": "patch_namespaced_pod",
        "namespaced": True
    },
    "ReplicaSet": {
        "api": client.AppsV1Api,
        "patch_func": "patch_namespaced_replica_set",
        "namespaced": True
    },
    "Deployment": {
        "api": client.AppsV1Api,
        "patch_func": "patch_namespaced_deployment",
        "namespaced": True
    },
    "StatefulSet": {
        "api": client.AppsV1Api,
        "patch_func": "patch_namespaced_stateful_set",
        "namespaced": True
    },
    "DaemonSet": {
        "api": client.AppsV1Api,
        "patch_func": "patch_namespaced_daemon_set",
        "namespaced": True
    },
    "Job": {
        "api": client.BatchV1Api,
        "patch_func": "patch_namespaced_job",
        "namespaced": True
    },
    "CronJob": {
        "api": client.BatchV1Api,
        "patch_func": "patch_namespaced_cron_job",
        "namespaced": True
    },
    "Namespace": {
        "api": client.CoreV1Api,
        "patch_func": "patch_namespace",
        "namespaced": False
    },
    "Node": {
        "api": client.CoreV1Api,
        "patch_func": "patch_node",
        "namespaced": False
    },
    "PodDisruptionBudget": {
        "api": client.PolicyV1Api,
        "patch_func": "patch_namespaced_pod_disruption_budget",
        "namespaced": True
    },
    "LimitRange": {
        "api": client.CoreV1Api,
        "patch_func": "patch_namespaced_limit_range",
        "namespaced": True
    },
    "ResourceQuota": {
        "api": client.CoreV1Api,
        "patch_func": "patch_namespaced_resource_quota",
        "namespaced": True
    },
    "Service": {
        "api": client.CoreV1Api,
        "patch_func": "patch_namespaced_service",
        "namespaced": True
    },
    "Endpoints": {
        "api": client.CoreV1Api,
        "patch_func": "patch_namespaced_endpoints",
        "namespaced": True
    },
    "ConfigMap": {
        "api": client.CoreV1Api,
        "patch_func": "patch_namespaced_config_map",
        "namespaced": True
    },
    "Secret": {
        "api": client.CoreV1Api,
        "patch_func": "patch_namespaced_secret",
        "namespaced": True
    },
    "PersistentVolume": {
        "api": client.CoreV1Api,
        "patch_func": "patch_persistent_volume",
        "namespaced": False
    },
    "PersistentVolumeClaim": {
        "api": client.CoreV1Api,
        "patch_func": "patch_namespaced_persistent_volume_claim",
        "namespaced": True
    },
    "StorageClass": {
        "api": client.StorageV1Api,
        "patch_func": "patch_storage_class",
        "namespaced": False
    },
    "Ingress": {
        "api": client.NetworkingV1Api,
        "patch_func": "patch_namespaced_ingress",
        "namespaced": True
    },
    "NetworkPolicy": {
        "api": client.NetworkingV1Api,
        "patch_func": "patch_namespaced_network_policy",
        "namespaced": True
    },
    "Role": {
        "api": client.RbacAuthorizationV1Api,
        "patch_func": "patch_namespaced_role",
        "namespaced": True
    },
    "RoleBinding": {
        "api": client.RbacAuthorizationV1Api,
        "patch_func": "patch_namespaced_role_binding",
        "namespaced": True
    },
    "ClusterRole": {
        "api": client.RbacAuthorizationV1Api,
        "patch_func": "patch_cluster_role",
        "namespaced": False
    },
    "ClusterRoleBinding": {
        "api": client.RbacAuthorizationV1Api,
        "patch_func": "patch_cluster_role_binding",
        "namespaced": False
    },
    "ServiceAccount": {
        "api": client.CoreV1Api,
        "patch_func": "patch_namespaced_service_account",
        "namespaced": True
    },
}

def validate_and_patch_resource(path, context, name, namespace=None, old_yaml=None, new_yaml=None):
    configure_k8s(path, context)
    k8s_client = client.ApiClient()
    try:
        resource_dict = yaml.safe_load(new_yaml)
        kind = resource_dict.get("kind")

        # remove the resource version from the metadata
        resource_dict['metadata'].pop('resourceVersion', None)
        
        resource_info = K8S_RESOURCE_MAP[kind]

        # # Remove system-managed fields
        metadata = resource_dict.get("metadata", {})
        for field in [
            "creationTimestamp", "resourceVersion", "uid", "generation", 
            "managedFields", "selfLink", "annotations"
        ]:
            metadata.pop(field, None)

        resource_dict.pop("status", None)

        # Get the correct API and method
        api_instance = resource_info["api"](k8s_client)
        patch_method = getattr(api_instance, resource_info["patch_func"])

        if resource_info["namespaced"]:
            patch_method(name=name, namespace=namespace, body=resource_dict, dry_run="All")
            ret = patch_method(name=name, namespace=namespace, body=resource_dict)
        else:
            patch_method(name=name, body=resource_dict, dry_run="All")
            ret = patch_method(name=name, body=resource_dict)

        # converting new obj to yaml
        sanitized = client.ApiClient().sanitize_for_serialization(ret)
    
        # Dump YAML
        edited_yaml = yaml.safe_dump(sanitized, sort_keys=False)
        changes = diff_yaml_dicts(old_yaml, edited_yaml)

        return {
            "success": True,
            "message": f"{kind} patched successfully.",
            "changes": changes
        }
    
    except Exception as ex:
        logger.exception("Unexpected error", exc_info=ex)
        print(ex)
        if hasattr(ex, "body"):
            error_body = json.loads(ex.body)
            error_message = error_body.get("message")
            return {
                "success": False,
                "message": f"Unexpected error: Make sure the YAML is valid and the resource exists.",
            }
        else:
            return {
                "success": False,
                "message": f"Unexpected error: Make sure the YAML is valid and the resource exists."
            }

def diff_yaml_dicts(yaml_a, yaml_b):
    """
    Compare two YAML strings and return human-readable differences.
    """

    try:
        dict_a = yaml.safe_load(yaml_a)
        dict_b = yaml.safe_load(yaml_b)
    except yaml.YAMLError as e:
        logger.warning(f"YAML error: {e}")
    
    # remove metafields
    for d in [dict_a, dict_b]:
            if 'metadata' in d:
                d['metadata'].pop('resourceVersion', None)
                d['metadata'].pop('managedFields', None)
    
    # Perform deep diff
    diff = DeepDiff(dict_a, dict_b, ignore_order=True)
    messages = []

    def extract_field(path):
        # Extract the last key name from path example ->  "root['key1']['key2']"
        parts = path.split("['")
        return parts[-1][:-2] if len(parts) > 1 else path

    # Value changes
    for path, change in diff.get("values_changed", {}).items():
        field = extract_field(path)
        messages.append(f"🔄 Changed '{field}': '{change['old_value']}' → '{change['new_value']}'")

    # Added keys
    for path in diff.get("dictionary_item_added", []):
        field = extract_field(path)
        messages.append(f"🟢 Added field: '{field}'")

    # Removed keys
    for path in diff.get("dictionary_item_removed", []):
        field = extract_field(path)
        messages.append(f"🔴 Removed field: '{field}'")

    if not messages:
        return ["✅ No differences found."]
    return messages
