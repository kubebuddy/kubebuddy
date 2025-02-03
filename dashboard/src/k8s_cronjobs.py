from kubernetes import client, config

def getCronJobCount():
    config.load_kube_config()
    v1 = client.BatchV1Api()
    cronjobs = v1.list_cron_job_for_all_namespaces().items

    return len(cronjobs)