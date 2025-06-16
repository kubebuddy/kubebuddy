from kubernetes import client, config
from google.auth import default
from google.cloud.container_v1 import ClusterManagerClient
import tempfile
import base64
import os

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
    if context.startswith("gke_"):
        try:
            _, project_id, zone, cluster_id = context.split("_", 3)
        except ValueError:
            raise ValueError("Invalid GKE context format")

        SCOPES = ['https://www.googleapis.com/auth/cloud-platform']
        credentials, _ = default(scopes=SCOPES)

        cluster_manager_client = ClusterManagerClient(credentials=credentials)
        cluster = cluster_manager_client.get_cluster(
            project_id=project_id,
            zone=zone,
            cluster_id=cluster_id
        )

        cert = base64.b64decode(cluster.master_auth.cluster_ca_certificate)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".crt") as cert_file:
            cert_file.write(cert)
            cert_path = cert_file.name

        configuration = client.Configuration()
        configuration.host = f"https://{cluster.endpoint}:443"
        configuration.ssl_ca_cert = cert_path
        configuration.verify_ssl = True
        configuration.api_key = {"authorization": "Bearer " + credentials.token}
        client.Configuration.set_default(configuration)

    else:
        config.load_kube_config(config_file=path, context=context)

        aws_token = os.getenv("AWS_EKS_TOKEN")
        if aws_token and context.startswith("arn:aws:eks"):
            configuration = client.Configuration.get_default_copy()
            configuration.api_key = {"authorization": f"Bearer {aws_token}"}
            client.Configuration.set_default(configuration)