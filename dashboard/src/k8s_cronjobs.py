from kubernetes import client, config

def getCronJobCount():
    config.load_kube_config()
    v1 = client.BatchV1Api()
    cronjobs = v1.list_cron_job_for_all_namespaces().items

    return len(cronjobs)

def getCronJobsStatus(path, context, namespace="all"):
    try:
        config.load_kube_config(path, context)
        v1 = client.BatchV1Api()
        cronjobs = v1.list_cron_job_for_all_namespaces() if namespace == "all" else v1.list_namespaced_cron_job(namespace=namespace)

        cronjobs_status = {
            "Running": 0,
            "Completed": 0,
            "Count": 0
        }


        return cronjobs_status
    
    except client.exceptions.ApiException as e:
        print(f"Kubernetes API Exception: {e}")  # Print API errors to stderr
        return []
    except Exception as e:  # Catch other potential errors (e.g., config issues)
        print(f"An error occurred: {e}")  # Print other errors to stderr
        return []