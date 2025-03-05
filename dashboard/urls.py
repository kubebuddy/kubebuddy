from django.urls import path
from dashboard.views import dashboard, pods, nodes, replicasets, deployments, pod_info, \
                                events, rs_info, deploy_info, \
                                configmaps, secrets, services, endpoints, \
                                statefulsets, daemonset, jobs, cronjobs, node_info, \
                                namespace, limitrange, resourcequotas, persistentvolume, ns_info,\
                                persistentvolumeclaim, storageclass, sts_info, daemonset_info, \
                                role, rolebinding, clusterrole, clusterrolebinding, serviceAccount, \
                                service_info, endpoint_info, jobs_info, limitrange_info, \
                                resourcequota_info, cronjob_info, configmap_info, pvc_info, \
                                secret_info, role_info, pv_info, storageclass_info, role_binding_info, \
                                clusterrole_info, cluster_role_binding_info, serviceAccountInfo, \
                                pod_metrics, node_metrics, pdb, pdb_info, np, np_info, ingress
                                


urlpatterns = [
    # Dashboard
    path('<str:cluster_name>/dashboard/', dashboard, name='dashboard'),

    # Workloads
    path('<str:cluster_name>/pods', pods, name='pods'),
    path('<str:cluster_name>/replicasets', replicasets, name='replicasets'),
    path('<str:cluster_name>/deployments', deployments, name='deployments'),
    path('<str:cluster_name>/statefulsets', statefulsets, name="statefulsets"),
    path('<str:cluster_name>/daemonset', daemonset, name="daemonset"),
    path('<str:cluster_name>/jobs', jobs, name="jobs"),
    path('<str:cluster_name>/cronjobs', cronjobs, name="cronjobs"),
    
    path('<str:cluster_name>/pods/<str:namespace>/<str:pod_name>/', pod_info, name='pod_info'),
    path('<str:cluster_name>/replicasets/<str:namespace>/<str:rs_name>/', rs_info, name='rs_info'),
    path('<str:cluster_name>/deployments/<str:namespace>/<str:deploy_name>/', deploy_info, name='deploy_info'),
    path('<str:cluster_name>/statefulsets/<str:namespace>/<str:sts_name>/', sts_info, name='sts_info'),
    path('<str:cluster_name>/daemonset/<str:namespace>/<str:daemonset_name>/', daemonset_info, name='daemonset_info'),
    path('<str:cluster_name>/jobs/<str:namespace>/<str:job_name>/', jobs_info, name='jobs_info'),
    path('<str:cluster_name>/cronjobs/<str:namespace>/<str:cronjob_name>/', cronjob_info, name='cronjob_info'),
    
    
    # Events
    path('<str:cluster_name>/events', events, name='events'),
    
    # ConfigMap & Secrets
    path('<str:cluster_name>/configmaps', configmaps, name='configmaps'),
    path('<str:cluster_name>/secrets', secrets, name='secrets'),

    path('<str:cluster_name>/configmaps/<str:namespace>/<str:configmap_name>/', configmap_info, name='configmap_info'),
    path('<str:cluster_name>/secrets/<str:namespace>/<str:secret_name>/', secret_info, name='secret_info'),


    # Services
    path('<str:cluster_name>/services', services, name='services'),
    path('<str:cluster_name>/endpoints', endpoints, name='endpoints'),
    
    path('<str:cluster_name>/services/<str:namespace>/<str:service_name>/', service_info, name='service_info'),
    path('<str:cluster_name>/endpoints/<str:namespace>/<str:endpoint_name>/', endpoint_info, name='endpoint_info'),

    
    # Cluster Management
    path('<str:cluster_name>/nodes/', nodes, name='nodes'),
    path('<str:cluster_name>/namespace', namespace, name="namespace"),
    path('<str:cluster_name>/limitrange', limitrange, name="limitrange"),
    path('<str:cluster_name>/resourcequotas', resourcequotas, name="resourcequotas"),
    path('<str:cluster_name>/pdb', pdb, name="pdb"),

    path('<str:cluster_name>/nodes/<str:node_name>/', node_info, name='node_info'),
    path('<str:cluster_name>/namespace/<str:namespace>/', ns_info, name='ns_info'),
    path('<str:cluster_name>/limitrange/<str:namespace>/<str:limitrange_name>/', limitrange_info, name='limitrange_info'),
    path('<str:cluster_name>/resourcequotas/<str:namespace>/<str:resourcequota_name>/', resourcequota_info, name='resourcequota_info'),
    path('<str:cluster_name>/pdb/<str:namespace>/<str:pdb_name>/', pdb_info, name='pdb_info'),

    # Persistent Storage
    path('<str:cluster_name>/pv', persistentvolume, name="persistentvolume"),
    path('<str:cluster_name>/pvc', persistentvolumeclaim, name="persistentvolumeclaim"),
    path('<str:cluster_name>/storageclass', storageclass, name="storageclass"),

    path('<str:cluster_name>/pv/<str:pv_name>/', pv_info, name='pv_info'),
    path('<str:cluster_name>/pvc/<str:namespace>/<str:pvc_name>/', pvc_info, name='pvc_info'),

    path('<str:cluster_name>/sc/<str:sc_name>/', storageclass_info, name='sc_info'),
    
    # Networking
    path('<str:cluster_name>/np', np, name="np"),
    path('<str:cluster_name>/ingress', ingress, name="ingress"),
    
    path('<str:cluster_name>/np/<str:namespace>/<str:np_name>/', np_info, name='np_info'),


    # RBAC
    path('<str:cluster_name>/role', role, name="role"),
    path('<str:cluster_name>/rolebinding', rolebinding, name="rolebinding"),
    path('<str:cluster_name>/clusterrole', clusterrole, name="clusterrole"),
    path('<str:cluster_name>/clusterrolebinding', clusterrolebinding, name="clusterrolebinding"),
    path('<str:cluster_name>/serviceAccount', serviceAccount, name="serviceAccount"),
    
    path('<str:cluster_name>/role/<str:namespace>/<str:role_name>/', role_info, name='role_info'),
    path('<str:cluster_name>/clusterrole/<str:cluster_role_name>/', clusterrole_info, name='clusterrole_info'),
    path('<str:cluster_name>/rolebinding/<str:namespace>/<str:role_binding_name>/', role_binding_info, name='role_binding_info'),
    path('<str:cluster_name>/clusterrolebinding/<str:cluster_role_binding_name>/', cluster_role_binding_info, name='cluster_role_binding_info'),
    path('<str:cluster_name>/sa/<str:namespace>/<str:sa_name>/', serviceAccountInfo, name='serviceAccountInfo'),

    # Pod Metrics
    path('<str:cluster_name>/pod_metrics', pod_metrics, name="pod_metrics"),
    path('<str:cluster_name>/node_metrics', node_metrics, name="node_metrics"),
    

]
