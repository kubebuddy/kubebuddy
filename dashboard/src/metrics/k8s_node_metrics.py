from kubernetes import client, config


def get_node_metrics(path, context):
    # Load kubeconfig using the provided path and context
    config.load_kube_config(path, context=context)
    
    return 