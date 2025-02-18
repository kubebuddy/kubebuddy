from kubernetes import client, config
from kubernetes.client.rest import ApiException
from datetime import datetime

def list_rolebindings(path, context):
    # Load kube config with the provided path and context
    config.load_kube_config(path, context=context)
    
    v1 = client.RbacAuthorizationV1Api()

    rolebindings_data = []

    try:
        # List rolebindings across all namespaces
        rolebindings = v1.list_role_binding_for_all_namespaces()

        for rb in rolebindings.items:
            namespace = rb.metadata.namespace
            name = rb.metadata.name
            role_ref = rb.role_ref.name
            users = []
            groups = []
            service_accounts = []

            # Extract subjects (users, groups, service accounts) from rolebinding
            for subject in rb.subjects:
                if subject.kind == 'User':
                    users.append(subject.name)
                elif subject.kind == 'Group':
                    groups.append(subject.name)
                elif subject.kind == 'ServiceAccount':
                    service_accounts.append(subject.name)

            # Calculate the age of the rolebinding
            creation_time = rb.metadata.creation_timestamp
            age = str(datetime.now() - creation_time.replace(tzinfo=None))

            rolebindings_data.append({
                'namespace': namespace,
                'name': name,
                'role': role_ref,
                'users': ', '.join(users),
                'groups': ', '.join(groups),
                'service_accounts': ', '.join(service_accounts),
                'age': age
            })

    except ApiException as e:
        print(f"Error listing role bindings: {e}")
    
    return rolebindings_data