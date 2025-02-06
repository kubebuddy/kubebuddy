from kubernetes import client, config
config.load_kube_config()
v1 = client.CoreV1Api()
def get_namespace():
    list_ns = []
    namespaces = v1.list_namespace()
    for ns in namespaces.items:
        list_ns.append(ns.metadata.name)
    return list_ns
n = get_namespace()
print(n)