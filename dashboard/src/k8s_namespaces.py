from kubernetes import client, config
from django.shortcuts import render
config.load_kube_config()
v1 = client.CoreV1Api()

def get_namespace():
    try:
        list_ns = []
        namespaces = v1.list_namespace()
        for ns in namespaces.items:
            list_ns.append(ns.metadata.name)
        return list_ns
    except Exception as e:
        return render("templates/500.html")