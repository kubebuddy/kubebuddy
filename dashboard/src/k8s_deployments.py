from kubernetes import client, config

def getDeploymentsCount():
    config.load_kube_config()
    v1 = client.AppsV1Api() #Create an API client for the AppsV1Api
    deployments = v1.list_deployment_for_all_namespaces().items

    return len(deployments)