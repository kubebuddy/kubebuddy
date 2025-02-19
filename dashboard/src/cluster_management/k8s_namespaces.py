from kubernetes import client, config
from django.shortcuts import render
from datetime import datetime, timezone
from ..utils import calculateAge
config.load_kube_config()
v1 = client.CoreV1Api()

def get_namespace(request):
    try:
        list_ns = []
        namespaces = v1.list_namespace()
        for ns in namespaces.items:
            list_ns.append(ns.metadata.name)
        return list_ns
    except Exception as e:
        return render(request, "templates/500.html")
    


def namespaces_data(path, context):
    # Load Kubernetes config
    config.load_kube_config(path, context)

    v1 = client.CoreV1Api()
    namespaces = v1.list_namespace().items

    namespace_data = []
    for ns in namespaces:
        name = ns.metadata.name
        status = ns.status.phase
        age = calculateAge(datetime.now(timezone.utc) - ns.metadata.creation_timestamp)

        namespace_data.append({
            "name": name,
            "status": status,
            "age": age
        })

    return namespace_data