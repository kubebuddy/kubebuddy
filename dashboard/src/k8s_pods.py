from kubernetes import client, config

def getpods():
    config.load_kube_config()
    v1 = client.CoreV1Api()
    pods = v1.list_pod_for_all_namespaces()
    pod_names = [pod.metadata.name for pod in pods.items]
    pod_list = []
    for name in pod_names:
        pod_list.append(name)
    return pod_list, len(pod_list)

def getPodsStatus():
    config.load_kube_config()
    v1 = client.CoreV1Api()
    pods = v1.list_pod_for_all_namespaces()

    status_counts = {
    "Pending": 0,
    "Running": 0,
    "Failed": 0,
    "Succeeded": 0
    }
    
    # for pod in pods.items:
    #     print(pod.metadata.name)
    #     print(pod.status)
        # if pod.status.phase == "Running":
        #     print(pod.status.container_statuses)

    # Check each pod's status
    for pod in pods.items:
        if pod.status.phase == "Succeeded":
            status_counts["Succeeded"]+=1
        elif pod.status.phase == "Pending":
            status_counts["Pending"]+=1
        elif pod.status.phase == "Running":
            if pod.status.container_statuses[0].state.running: # CURRENTLY ASSUMING ONLY 1 CONTAINER PER POD !
                status_counts["Running"]+=1
            else:
                status_counts["Failed"]+=1

    return status_counts