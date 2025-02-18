from kubernetes import client, config
from ..utils import calculateAge
from datetime import datetime, timezone

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

        for cronjob in cronjobs.items:
            if cronjob.status.active == None:
                cronjobs_status["Completed"] += 1
            else:
                cronjobs_status["Running"] += 1

            cronjobs_status["Count"] += 1

        return cronjobs_status
    
    except client.exceptions.ApiException as e:
        print(f"Kubernetes API Exception: {e}")  # Print API errors to stderr
        return []
    except Exception as e:  # Catch other potential errors (e.g., config issues)
        print(f"An error occurred: {e}")  # Print other errors to stderr
        return []

def getCronJobsList(path, context, namespace="all"):
    try:
        config.load_kube_config(path, context)
        v1 = client.BatchV1Api()
        cronjobs = v1.list_cron_job_for_all_namespaces() if namespace == "all" else v1.list_namespaced_cron_job(namespace=namespace)

        cronjobs_list = []
        for job in cronjobs.items:
            namespace = job.metadata.namespace
            name = job.metadata.name
            schedule = job.spec.schedule
            time_zone = job.spec.time_zone
            suspend = job.spec.suspend
            active = len(job.status.active) if job.status.active else 0
            difference1 = datetime.now(timezone.utc) - job.status.last_schedule_time
            last_schedule = calculateAge(difference1)
            difference2 = datetime.now(timezone.utc) - job.metadata.creation_timestamp
            age = calculateAge(difference2)

            cronjobs_list.append({
                'name': name,
                'namespace': namespace,
                'schedule': schedule,
                'time_zone': time_zone,
                'suspend': suspend,
                'active': active,
                'last_schedule': last_schedule,
                'age': age
            })
        
        return cronjobs_list

    except client.exceptions.ApiException as e:
        print(f"Kubernetes API Exception: {e}")  # Print API errors to stderr
        return []
    except Exception as e:  # Catch other potential errors (e.g., config issues)
        print(f"An error occurred: {e}")  # Print other errors to stderr
        return []