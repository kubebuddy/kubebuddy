from main.models import Cluster
from kubernetes import config, client
from kubebuddy.appLogs import logger
from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
import os
from dotenv import load_dotenv
from google.auth import default
from google.cloud.container_v1 import ClusterManagerClient
import base64
import tempfile
import boto3
import subprocess

@csrf_exempt
def get_cluster_status(request):
    load_dotenv()
    cluster = json.loads(request.body)
    control_plane_components = [
        {"key": "component", "value": "kube-apiserver"},
        {"key": "component", "value": "etcd"}
    ]
    core_dns_label = {"key": "k8s-app", "value": "kube-dns"}
    failed_control_pods = []
    failed_dns_pods = []

    try:
        if cluster.get('context_name', '').startswith('gke_'):
            # Handle GKE
            SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
            credentials, project = default(scopes=SCOPES)
            cluster_manager_client = ClusterManagerClient(credentials=credentials)

            # Extract GKE details from context_name: gke_{project}_{zone}_{cluster_name}
        
            _, project_id, zone, cluster_id = cluster['context_name'].split('_', 3) # Have removed the try block assuming context is always in this format
    
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

        elif cluster.get('context_name', '').startswith('arn:aws:eks:'):
            # currently using context for cluster name and user as well, if need be we can read the file and get the relevant data
            # Get token
            region = cluster['context_name'].split(':')[3]
            name = cluster['context_name'].split(':')[5].split('/')[1]
            eks = boto3.client('eks', region_name=region)
            cluster_info = eks.describe_cluster(name=name)
            cluster_cert = cluster_info['cluster']['certificateAuthority']['data']
            cluster_endpoint = cluster_info['cluster']['endpoint']

            # Generate token
            token = boto3.client('sts').get_caller_identity()
            auth_token = subprocess.check_output(
                ['aws', 'eks', 'get-token', '--cluster-name', cluster['cluster_name'], '--region', region, '--output', 'json']
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
                    'name': cluster['cluster_name']
                }],
                'contexts': [{
                    'context': {
                        'cluster': cluster['cluster_name'],
                        'user': cluster['context_name']
                    },
                    'name': cluster['context_name']
                }],
                'current-context': cluster['context_name'],
                'kind': 'Config',
                'users': [{
                    'name': cluster['context_name'],
                    'user': {
                        'token': bearer_token
                    }
                }]
            }

            config.load_kube_config_from_dict(config_dict)
        else:
            config.load_kube_config(config_file=cluster["kube_config__path"], context=cluster["context_name"])

        v1 = client.CoreV1Api()
        nodes = v1.list_node().items
        cluster['number_of_nodes'] = len(nodes)
        cluster['control_plane_status'] = "Running"
        cluster['core_dns_status'] = "Running"

        for component in control_plane_components:
            label_selector = f"{component['key']}={component['value']}"
            pods = v1.list_namespaced_pod(namespace="kube-system", label_selector=label_selector)
            for pod in pods.items:
                if pod.status.phase != "Running":
                    cluster['control_plane_status'] = "Unhealthy"
                    failed_control_pods.append(pod.metadata.name)

        label_selector = f"{core_dns_label['key']}={core_dns_label['value']}"
        core_dns_pods = v1.list_namespaced_pod(namespace="kube-system", label_selector=label_selector)
        for pod in core_dns_pods.items:
            if pod.status.phase != "Running":
                cluster['core_dns_status'] = "Unhealthy"
                failed_dns_pods.append(pod.metadata.name)

        cluster['failed_control_pods'] = failed_control_pods
        cluster['failed_dns_pods'] = failed_dns_pods
        return JsonResponse({"message": "Cluster status retrieved", "received_data": cluster})

    except Exception as e:
        logger.error(f"Error retrieving cluster status for {cluster['cluster_name']}: {e}")
        cluster['control_plane_status'] = "Unavailable"
        cluster['core_dns_status'] = "Unavailable"
        cluster['number_of_nodes'] = 'N/A'
        cluster['failed_control_pods'] = []
        cluster['failed_dns_pods'] = []
        return JsonResponse({"message": "Cluster status retrieved", "received_data": cluster})


def get_registered_clusters():
    clusters = Cluster.objects.all().values("id", "cluster_name", "context_name", "kube_config__path")
    return list(clusters)

def get_cluster_names():
    clusters = Cluster.objects.all()
    return [{"cluster_name": cluster.cluster_name, "id": cluster.id} for cluster in clusters]