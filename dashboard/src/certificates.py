import base64
import datetime
import json
import os
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from kubernetes import client, config

def get_certificate_details(path=None, context=None):
    """
    Get simplified details about certificates in Kubernetes including:
    - Basic certificate information from TLS secrets
    - Certificate Signing Requests (CSRs)
    
    Args:
        path (str, optional): Path to kubeconfig file. If None, uses default location.
        context (str, optional): The kubeconfig context to use. If None, uses current context.
    
    Returns:
        dict: A dictionary containing only the requested certificate details
    """
    result = {
        "certificates": [],
        "certificate_signing_requests": [],
        "errors": []
    }
    
    try:
        # Load kube config with the specified path and context
        try:
            config.load_incluster_config()
        except config.ConfigException:
            # Use the provided path and context if available
            config.load_kube_config(
                config_file=path if path else None,
                context=context if context else None
            )

        # Initialize API clients
        v1 = client.CoreV1Api()
        certificates_api = client.CertificatesV1Api()
        
        # Get all namespaces
        namespaces = v1.list_namespace()
        
        # Get TLS Secrets
        for ns in namespaces.items:
            namespace = ns.metadata.name
            try:
                secrets = v1.list_namespaced_secret(namespace=namespace)
                tls_secrets = [s for s in secrets.items if s.type == "kubernetes.io/tls"]
                
                if tls_secrets:
                    for secret in tls_secrets:
                        if secret.data and 'tls.crt' in secret.data:
                            cert_data = base64.b64decode(secret.data['tls.crt'])
                            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
                            
                            # Only include the requested certificate details
                            cert_info = {
                                "namespace": namespace,
                                "name": secret.metadata.name,
                                "subject": str(cert.subject),
                                "issuer": str(cert.issuer),
                                "not_valid_before": str(cert.not_valid_before),
                                "not_valid_after": str(cert.not_valid_after),
                                "serial_number": str(cert.serial_number),
                                "days_until_expiry": (cert.not_valid_after - datetime.datetime.now()).days
                            }
                            
                            result["certificates"].append(cert_info)
            except client.exceptions.ApiException as e:
                result["errors"].append({
                    "context": f"accessing secrets in namespace {namespace}",
                    "error": str(e)
                })
        
        # Get Certificate Signing Requests
        try:
            csrs = certificates_api.list_certificate_signing_request()
            for csr in csrs.items:
                csr_data = {
                    "name": csr.metadata.name,
                    "username": csr.spec.username,
                    "uid": csr.spec.uid,
                    "status": csr.status.conditions[0].type if csr.status.conditions else "No conditions",
                    "created": str(csr.metadata.creation_timestamp)
                }
                result["certificate_signing_requests"].append(csr_data)
        except client.exceptions.ApiException as e:
            result["errors"].append({
                "context": "accessing CSRs",
                "error": str(e)
            })
        
    except Exception as e:
        result["errors"].append({
            "context": "general execution",
            "error": str(e)
        })
    
    return result