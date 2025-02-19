from kubernetes import client, config

def get_cluster_role(path, context):
    config.load_kube_config(path, context=context)
    rbac_api = client.RbacAuthorizationV1Api()

    clusterroles = []
    response = rbac_api.list_cluster_role()

    for role in response.items:
        creation_timestamp = role.metadata.creation_timestamp
        if creation_timestamp:
            #Convert to local time and format
            creation_time_str = creation_timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        else:
            creation_time_str = "Unknown"

        clusterroles.append({
            "name": role.metadata.name,
            "created_at": creation_time_str
    })
    return clusterroles, len(clusterroles)