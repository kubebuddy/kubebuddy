from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException
from datetime import datetime, timezone
from kubebuddy.appLogs import logger
from ..utils import calculateAge, filter_annotations, configure_k8s
import yaml


def getJobCount(path, context):
    configure_k8s(path, context)
    v1 = client.BatchV1Api()
    jobs = v1.list_job_for_all_namespaces().items

    return len(jobs)

def getJobsStatus(path, context, namespace="all"):
    try:
        configure_k8s(path, context)
        v1 = client.BatchV1Api()
        jobs = v1.list_job_for_all_namespaces() if namespace == "all" else v1.list_namespaced_job(namespace=namespace)

        jobs_status = {
            "Running": 0,
            "Failed": 0,
            "Completed": 0,
            "Count": 0
        }

        for job in jobs.items:
            if job.status.succeeded and job.status.succeeded >= job.spec.completions:
                jobs_status["Completed"] += 1
            elif (job.status.failed and job.status.failed >= job.spec.backoff_limit) or job.status.failed:
                jobs_status["Failed"] += 1
            else:
                jobs_status["Running"] += 1
            
            jobs_status["Count"]+=1

        return jobs_status
    
    except client.exceptions.ApiException as e:
        logger.error(f"Kubernetes API Exception: {e}")  # Print API errors to stderr
        return []
    except Exception as e:  # Catch other potential errors (e.g., config issues)
        logger.error(f"An error occurred: {e}")  # Print other errors to stderr
        return []
    
def getJobsList(path, context, namespace="all"):
    try:
        configure_k8s(path, context)
        v1 = client.BatchV1Api()
        jobs = v1.list_job_for_all_namespaces() if namespace == "all" else v1.list_namespaced_job(namespace=namespace)
        jobs_list = []

        for job in jobs.items:
            namespace = job.metadata.namespace
            name = job.metadata.name
            if job.status.succeeded and job.status.succeeded >= job.spec.completions:
                status = "Completed"
            elif (job.status.failed and job.status.failed >= job.spec.backoff_limit) or job.status.failed:
                status = "Failed"
            else:
                status = "Running"
            completions = str(job.status.succeeded) + "/" + str(job.spec.completions) if job.status.succeeded is not None else "0/" + str(job.spec.completions)
            difference2 = (datetime.now(timezone.utc) - job.metadata.creation_timestamp)
            age = calculateAge(difference2)
            if job.status.completion_time is not None:
                difference1 = job.status.completion_time - job.status.start_time
                duration = calculateAge(difference1)
            else:
                duration = age

            jobs_list.append({
                'namespace': namespace,
                'name': name,
                'status': status,
                'completions': completions,
                'age': age,
                'duration': duration,
            })
        
        return jobs_list
    
    except client.exceptions.ApiException as e:
        logger(f"Kubernetes API Exception: {e}")  # Print API errors to stderr
        return []
    except Exception as e:  # Catch other potential errors (e.g., config issues)
        logger(f"An error occurred: {e}")  # Print other errors to stderr
        return []
    

def get_job_description(path=None, context=None, namespace=None, job_name=None):
    configure_k8s(path, context)
    batch_v1 = client.BatchV1Api()

    try:
        # Fetch Job details
        job = batch_v1.read_namespaced_job(name=job_name, namespace=namespace)

        # Prepare Job information
        job_info = {
            "name": job.metadata.name,
            "namespace": job.metadata.namespace,
            "selector": list(job.spec.selector.match_labels.items()) if job.spec.selector and job.spec.selector.match_labels else [],
            "labels": job.metadata.labels if isinstance(job.metadata.labels, dict) else {},
            "annotations": filter_annotations(job.metadata.annotations or {}),
            "parallelism": job.spec.parallelism,
            "completions": job.spec.completions,
            "completion_mode": job.spec.completion_mode,
            "suspend": job.spec.suspend,
            "backoff_limit": job.spec.backoff_limit,
            "start_time": job.status.start_time,
            "completion_time": job.status.completion_time,
            "duration": (job.status.completion_time - job.status.start_time).total_seconds() if job.status.completion_time else None,
            "pods_status": {
                "active": job.status.active,
                "succeeded": job.status.succeeded,
                "failed": job.status.failed
            },
            "pod_template": {
                "labels": job.spec.template.metadata.labels,
                "containers": [
                    {
                        "name": container.name,
                        "image": container.image,
                        "command": container.command,
                        "env": [env.name for env in (container.env or [])],
                        "mounts": [mount.mount_path for mount in (container.volume_mounts or [])]
                    }
                    for container in job.spec.template.spec.containers
                ],
                "volumes": [
                    {
                        "name": volume.name,
                        "type": volume.secret or volume.config_map or volume.projected
                    }
                    for volume in (job.spec.template.spec.volumes or [])
                ],
                "node_selectors": job.spec.template.spec.node_selector,
                "tolerations": job.spec.template.spec.tolerations
            }
        }

        return job_info

    except client.exceptions.ApiException as e:
        return {"error": f"Failed to fetch Job details: {e.reason}"}

def get_job_events(path, context, namespace, job_name):
    configure_k8s(path, context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    job_events = [event for event in events if event.involved_object.name == job_name and event.involved_object.kind == "Job"]
    return "\n".join([f"{e.reason}: {e.message}" for e in job_events])

def get_yaml_job(path, context, namespace, job_name):
    configure_k8s(path, context)
    v1 = client.BatchV1Api()
    job = v1.read_namespaced_job(name=job_name, namespace=namespace)
    # Filtering Annotations
    if job.metadata:
        job.metadata.annotations = filter_annotations(job.metadata.annotations or {})
    return yaml.dump(job.to_dict(), default_flow_style=False)

def get_job_details(namespace=None):
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()

    batch_v1 = client.BatchV1Api()
    jobs = batch_v1.list_namespaced_job(namespace) if namespace else batch_v1.list_job_for_all_namespaces()

    def get_age(creation_timestamp):
        delta = datetime.now(timezone.utc) - creation_timestamp
        days = delta.days
        hours = delta.seconds // 3600
        return f"{days}d {hours}h" if days else f"{hours}h"

    def get_duration(start, end):
        if start and end:
            duration = end - start
            minutes = duration.total_seconds() // 60
            return f"{int(minutes)}m"
        return "N/A"

    job_details = []
    for job in jobs.items:
        start_time = job.status.start_time
        completion_time = job.status.completion_time
        duration = get_duration(start_time, completion_time)

        job_info = {
            'name': job.metadata.name,
            'namespace': job.metadata.namespace,
            'completions': job.status.succeeded if job.status.succeeded is not None else 0,
            'duration': duration,
            'age': get_age(job.metadata.creation_timestamp)
        }
        job_details.append(job_info)

    return job_details

