from kubernetes import client, config
from datetime import datetime, timezone
from ..utils import calculateAge
import yaml


def getJobCount():
    config.load_kube_config()
    v1 = client.BatchV1Api()
    jobs = v1.list_job_for_all_namespaces().items

    return len(jobs)

def getJobsStatus(path, context, namespace="all"):
    try:
        config.load_kube_config(path, context)
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
        print(f"Kubernetes API Exception: {e}")  # Print API errors to stderr
        return []
    except Exception as e:  # Catch other potential errors (e.g., config issues)
        print(f"An error occurred: {e}")  # Print other errors to stderr
        return []
    
def getJobsList(path, context, namespace="all"):
    try:
        config.load_kube_config(path, context)
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
        print(f"Kubernetes API Exception: {e}")  # Print API errors to stderr
        return []
    except Exception as e:  # Catch other potential errors (e.g., config issues)
        print(f"An error occurred: {e}")  # Print other errors to stderr
        return []
    

def get_job_description(path=None, context=None, namespace=None, job_name=None):
    config.load_kube_config(path, context)
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
            "annotations": job.metadata.annotations if isinstance(job.metadata.annotations, dict) else {},
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
    config.load_kube_config(config_file=path, context=context)
    v1 = client.CoreV1Api()
    events = v1.list_namespaced_event(namespace=namespace).items
    job_events = [event for event in events if event.involved_object.name == job_name and event.involved_object.kind == "Job"]
    return "\n".join([f"{e.reason}: {e.message}" for e in job_events])

def get_yaml_job(path, context, namespace, job_name):
    config.load_kube_config(config_file=path, context=context)
    v1 = client.BatchV1Api()
    job = v1.read_namespaced_job(name=job_name, namespace=namespace)
    return yaml.dump(job.to_dict(), default_flow_style=False)
