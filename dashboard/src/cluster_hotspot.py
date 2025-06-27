from kubernetes import client, config
from .utils import configure_k8s, calculateAge
from datetime import datetime, timezone

def get_cluster_hotspot(path, context):
    try:
        # Load kube config
        configure_k8s(path, context)

        core_v1 = client.CoreV1Api()
        apps_v1 = client.AppsV1Api()
        batch_v1 = client.BatchV1Api()

        empty_namespaces = []
        latest_tag_pods = []
        orphaned_configmaps = []
        orphaned_secrets = []
        container_missing_probes = []
        container_restart_count = []
        priviledged_containers = []
        empty_limit = []

        namespaces = core_v1.list_namespace().items

        for ns in namespaces:
            name = ns.metadata.name

            pods = core_v1.list_namespaced_pod(namespace=name).items
            deployments = apps_v1.list_namespaced_deployment(namespace=name).items
            statefulsets = apps_v1.list_namespaced_stateful_set(namespace=name).items
            daemonsets = apps_v1.list_namespaced_daemon_set(namespace=name).items
            configmaps = core_v1.list_namespaced_config_map(namespace=name).items
            secrets = core_v1.list_namespaced_secret(namespace=name).items

            used_configmaps = set()
            used_secrets = set()

            def collect_refs(pod_spec):
                if pod_spec.volumes:
                    for volume in pod_spec.volumes:
                        if volume.config_map and volume.config_map.name:
                            used_configmaps.add(volume.config_map.name)
                        if volume.secret and volume.secret.secret_name:
                            used_secrets.add(volume.secret.secret_name)

                for container in pod_spec.containers:
                    # pods with priviledged containers
                    sc = container.security_context
                    if sc and (sc.privileged if sc.privileged is not None else False):
                        priviledged_containers.append({
                            "namespace": name,
                            "pod": pod.metadata.name,
                            "container": container.name,
                            "image": container.image
                        })
                    #container with no limit
                    limits = container.resources.limits
                    if not limits:
                        empty_limit.append({
                            "namespace": name,
                            "pod":pod.metadata.name,
                            "container":container.name
                        })
                    
                    if container.env:
                        for env_var in container.env:
                            if env_var.value_from:
                                if env_var.value_from.config_map_key_ref:
                                    used_configmaps.add(env_var.value_from.config_map_key_ref.name)
                                if env_var.value_from.secret_key_ref:
                                    used_secrets.add(env_var.value_from.secret_key_ref.name)

                    if container.env_from:
                        for env_from in container.env_from:
                            if env_from.config_map_ref and env_from.config_map_ref.name:
                                used_configmaps.add(env_from.config_map_ref.name)
                            if env_from.secret_ref and env_from.secret_ref.name:
                                used_secrets.add(env_from.secret_ref.name)
            
            # Identify pods with 'latest' tag and collect ConfigMap/Secret references 
            # and find missing liveness and readiness probes
            for pod in pods:
                collect_refs(pod.spec)

                # get container restart count
                for container_status in pod.status.container_statuses or []:
                    restart_info = {
                        "namespace": name,
                        "pod": pod.metadata.name,
                        "container": container_status.name,
                        "restart_count": container_status.restart_count
                    }
                    container_restart_count.append(restart_info)

                for container in pod.spec.containers:

                    # check for missing liveness and readiness probes
                    if not container.liveness_probe or not container.readiness_probe:
                        container_missing_probes.append({
                            "namespace": name,
                            "pod": pod.metadata.name,
                            "container": container.name,
                            "image": container.image,
                            "missing_probes": {
                                "liveness_probe": not container.liveness_probe,
                                "readiness_probe": not container.readiness_probe
                            }
                        })

                    # check for image with tag 'latest'
                    image = container.image
                    if image.endswith(":latest") or (":" not in image):
                        latest_tag_pods.append({
                            "namespace": name,
                            "pod": pod.metadata.name,
                            "image": image
                        })

            for deploy in deployments:
                collect_refs(deploy.spec.template.spec)
            for sts in statefulsets:
                collect_refs(sts.spec.template.spec)
            for ds in daemonsets:
                collect_refs(ds.spec.template.spec)

            # Identify orphaned ConfigMaps
            for cm in configmaps:
                if cm.metadata.name not in used_configmaps and cm.metadata.name != "kube-root-ca.crt":
                    orphaned_configmaps.append({
                        "namespace": name,
                        "configmap": cm.metadata.name,
                        'age': calculateAge(datetime.now(timezone.utc) - cm.metadata.creation_timestamp)
                    })

            non_system_configmaps = [cm for cm in configmaps if cm.metadata.name != "kube-root-ca.crt"]

            # get orphaned secrets
            for secret in secrets:
                if (secret.metadata.name not in used_secrets and
                    not secret.metadata.name.startswith("default-token-")):
                    orphaned_secrets.append({
                        "namespace": name,
                        "secret": secret.metadata.name,
                        'age': calculateAge(datetime.now(timezone.utc) - secret.metadata.creation_timestamp)
                    })

            has_resources = (
                pods or deployments or statefulsets or daemonsets or
                apps_v1.list_namespaced_replica_set(namespace=name).items or
                batch_v1.list_namespaced_job(namespace=name).items or
                batch_v1.list_namespaced_cron_job(namespace=name).items or
                core_v1.list_namespaced_service(namespace=name).items or
                non_system_configmaps or
                core_v1.list_namespaced_secret(namespace=name).items or
                core_v1.list_namespaced_persistent_volume_claim(namespace=name).items
            )

            if not has_resources and ns.metadata.name not in ['kube-system', 'kube-public', 'kube-node-lease', 'default']:
                empty_namespaces.append({'name': name, 'status': ns.status.phase, 'age': calculateAge(datetime.now(timezone.utc) - ns.metadata.creation_timestamp), 'labels': ns.metadata.labels})

        return empty_namespaces, latest_tag_pods, orphaned_configmaps, orphaned_secrets, container_missing_probes, container_restart_count, priviledged_containers, empty_limit
    
    except Exception as e:
        print(f"Error: {e}")
        return None