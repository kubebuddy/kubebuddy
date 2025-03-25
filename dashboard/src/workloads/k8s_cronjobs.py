from kubernetes import client, config
from ..utils import calculateAge, filter_annotations
from datetime import datetime, timezone
from kubebuddy.appLogs import logger
import yaml

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
        logger(f"Kubernetes API Exception: {e}")  # Print API errors to stderr
        return []
    except Exception as e:  # Catch other potential errors (e.g., config issues)
        logger(f"An error occurred: {e}")  # Print other errors to stderr
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
        logger.error(f"Kubernetes API Exception: {e}")  # Print API errors to stderr
        return []
    except Exception as e:  # Catch other potential errors (e.g., config issues)
        logger.error(f"An error occurred: {e}")  # Print other errors to stderr
        return []

def get_cronjob_description(path=None, context=None, namespace=None, cronjob_name=None):
    config.load_kube_config(path, context)
    v1 = client.BatchV1Api()

    try:
        # Fetch CronJob details
        cronjob = v1.read_namespaced_cron_job(name=cronjob_name, namespace=namespace)
        
        # Prepare CronJob information
        cronjob_info = {
            "name": cronjob.metadata.name,
            "namespace": cronjob.metadata.namespace,
            "schedule": cronjob.spec.schedule,
            "concurrency_policy": cronjob.spec.concurrency_policy,
            "suspend": cronjob.spec.suspend,
            "successful_jobs_history_limit": cronjob.spec.successful_jobs_history_limit,
            "failed_jobs_history_limit": cronjob.spec.failed_jobs_history_limit,
            "starting_deadline_seconds": cronjob.spec.starting_deadline_seconds,
            "selector": cronjob.spec.selector.match_labels if hasattr(cronjob.spec, 'selector') and cronjob.spec.selector else "<unset>",
            "labels": cronjob.metadata.labels if isinstance(cronjob.metadata.labels, dict) else "<none>",
            "annotations": filter_annotations(cronjob.metadata.annotations or {}),
            "pods_status": {
                "active": cronjob.status.active,
                "last_schedule_time": cronjob.status.last_schedule_time
            },
            "pod_template": {
                "labels": cronjob.spec.job_template.spec.template.metadata.labels,
                "containers": [
                    {
                        "name": container.name,
                        "image": container.image,
                        "command": container.command,
                        "env": [env.name for env in (container.env or [])],
                        "mounts": [mount.mount_path for mount in (container.volume_mounts or [])]
                    }
                    for container in cronjob.spec.job_template.spec.template.spec.containers
                ],
                "volumes": [
                    {
                        "name": volume.name,
                        "type": volume.secret or volume.config_map or volume.projected
                    }
                    for volume in (cronjob.spec.job_template.spec.template.spec.volumes or [])
                ],
                "node_selectors": cronjob.spec.job_template.spec.template.spec.node_selector,
                "tolerations": cronjob.spec.job_template.spec.template.spec.tolerations
            },
            "active_jobs": [job.name for job in cronjob.status.active] if cronjob.status.active else []
        }

        return cronjob_info

    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch CronJob details: {e.reason}"}

def get_cronjob_events(path, context, namespace, cronjob_name):
    config.load_kube_config(config_file=path, context=context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    cronjob_events = [event for event in events if event.involved_object.name == cronjob_name and event.involved_object.kind == "CronJob"]
    return "\n".join([f"{e.reason}: {e.message}" for e in cronjob_events])

def get_yaml_cronjob(path, context, namespace, cronjob_name):
    config.load_kube_config(config_file=path, context=context)
    v1 = client.BatchV1Api()
    cronjob = v1.read_namespaced_cron_job(name=cronjob_name, namespace=namespace)
    # Filtering Annotations
    if cronjob.metadata:
        cronjob.metadata.annotations = filter_annotations(cronjob.metadata.annotations or {})
    return yaml.dump(cronjob.to_dict(), default_flow_style=False)