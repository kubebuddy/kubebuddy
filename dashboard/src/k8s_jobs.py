from kubernetes import client, config

def getJobCount():
    config.load_kube_config()
    v1 = client.BatchV1Api()
    jobs = v1.list_job_for_all_namespaces().items

    return len(jobs)