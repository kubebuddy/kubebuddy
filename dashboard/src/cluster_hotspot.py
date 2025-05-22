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
        rbac = client.RbacAuthorizationV1Api()

        empty_namespaces = []
        latest_tag_pods = []
        orphaned_configmaps = []
        orphaned_secrets = []
        container_missing_probes = []
        container_restart_count = []
        priviledged_containers = []

        namespaces = core_v1.list_namespace().items

        # Find Roles, ClusterRoles, RoleBindings, and ClusterRoleBindings with "*" verbs/resources
        roles_with_wildcard = []
        clusterroles_with_wildcard = []
        rolebindings_with_wildcard = []
        clusterrolebindings_with_wildcard = []

        # Check Roles
        for role in rbac.list_role_for_all_namespaces().items:
            for rule in role.rules or []:
                if ("*" in (rule.verbs or [])) and ("*" in (rule.resources or [])):
                    roles_with_wildcard.append({
                        "namespace": role.metadata.namespace,
                        "name": role.metadata.name,
                        "verbs": rule.verbs,
                        "resources": rule.resources
                    })

        # Check ClusterRoles
        for cr in rbac.list_cluster_role().items:
            for rule in cr.rules or []:
                if ("*" in (rule.verbs or [])) and ("*" in (rule.resources or [])):
                    clusterroles_with_wildcard.append({
                        "name": cr.metadata.name,
                        "verbs": rule.verbs,
                        "resources": rule.resources
                    })

        # Check RoleBindings
        for rb in rbac.list_role_binding_for_all_namespaces().items:
            if rb.role_ref.kind == "Role":
                roles = [r for r in roles_with_wildcard if r["namespace"] == rb.metadata.namespace and r["name"] == rb.role_ref.name]
                if roles:
                    rolebindings_with_wildcard.append({
                        "namespace": rb.metadata.namespace,
                        "name": rb.metadata.name,
                        "role_ref": rb.role_ref.name
                    })
            elif rb.role_ref.kind == "ClusterRole":
                crs = [cr for cr in clusterroles_with_wildcard if cr["name"] == rb.role_ref.name]
                if crs:
                    rolebindings_with_wildcard.append({
                        "namespace": rb.metadata.namespace,
                        "name": rb.metadata.name,
                        "role_ref": rb.role_ref.name
                    })

        # Check ClusterRoleBindings
        for crb in rbac.list_cluster_role_binding().items:
            crs = [cr for cr in clusterroles_with_wildcard if cr["name"] == crb.role_ref.name]
            if crs:
                clusterrolebindings_with_wildcard.append({
                    "name": crb.metadata.name,
                    "role_ref": crb.role_ref.name
                })

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
                    # pods with privelidged containers
                    sc = container.security_context
                    if sc and (sc.run_as_user == 0 or (sc.privileged if sc.privileged is not None else False)):
                        priviledged_containers.append({
                            "namespace": name,
                            "pod": pod.metadata.name,
                            "container": container.name,
                            "image": container.image
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

            if not has_resources:
                empty_namespaces.append({'name': name, 'status': ns.status.phase, 'age': calculateAge(datetime.now(timezone.utc) - ns.metadata.creation_timestamp), 'labels': ns.metadata.labels})

        return empty_namespaces, latest_tag_pods, orphaned_configmaps, orphaned_secrets, container_missing_probes, container_restart_count, priviledged_containers, roles_with_wildcard, clusterroles_with_wildcard, rolebindings_with_wildcard, clusterrolebindings_with_wildcard
    
    except Exception as e:
        print(f"Error: {e}")
        return None