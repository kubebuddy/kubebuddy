from kubernetes import client, config
from datetime import datetime, timezone
from .utils import calculateAge

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