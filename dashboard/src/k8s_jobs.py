from kubernetes import client, config

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
            if job.status.succeeded == None:
                jobs_status["Failed"] += 1
                jobs_status["Count"] += 1
            elif job.status.succeeded >= job.spec.completions:
                jobs_status["Completed"] += 1
                jobs_status["Count"] += 1
            elif job.status.failed >= job.spec.backoff_limit:
                jobs_status["Failed"] += 1
                jobs_status["Count"] += 1
            else:
                jobs_status["Running"] += 1
                jobs_status["Count"] += 1



        return jobs_status
    
    except client.exceptions.ApiException as e:
        print(f"Kubernetes API Exception: {e}")  # Print API errors to stderr
        return []
    except Exception as e:  # Catch other potential errors (e.g., config issues)
        print(f"An error occurred: {e}")  # Print other errors to stderr
        return []