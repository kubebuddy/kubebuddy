from django.urls import path
from dashboard.views import dashboard, pods, nodes, replicasets, deployments, pod_info, \
                                events, rs_info, deploy_info, \
                                configmaps, secrets, services, endpoints, \
                                statefulsets, daemonset, jobs, cronjobs, node_info, \
                                namespace, limitrange, resourcequotas, persistentvolume, ns_info,\
                                persistentvolumeclaim, storageclass, sts_info, daemonset_info, \
                                role, rolebinding, clusterrole, clusterrolebinding, service_account, \
                                service_info, endpoint_info, jobs_info, limitrange_info, \
                                resourcequota_info, cronjob_info, configmap_info, pvc_info, \
                                secret_info, role_info, pv_info, storageclass_info, role_binding_info, \
                                clusterrole_info, cluster_role_binding_info, service_accountInfo, \
                                pod_metrics, node_metrics, pdb, pdb_info, np, np_info, ingress, \
                                ingress_info, execute_command, generate_reports
                                


urlpatterns = [
    # Dashboard
    path('<int:cluster_id>/dashboard/', dashboard, name='dashboard'),
    path('execute/', execute_command, name='execute_command'),

    # Download Report
    path('generate_reports/', generate_reports, name='generate_reports'),
    
    # Workloads
    path('<int:cluster_id>/pods', pods, name='pods'),
    path('<int:cluster_id>/replicasets', replicasets, name='replicasets'),
    path('<int:cluster_id>/deployments', deployments, name='deployments'),
    path('<int:cluster_id>/statefulsets', statefulsets, name="statefulsets"),
    path('<int:cluster_id>/daemonset', daemonset, name="daemonset"),
    path('<int:cluster_id>/jobs', jobs, name="jobs"),
    path('<int:cluster_id>/cronjobs', cronjobs, name="cronjobs"),
    
    path('<int:cluster_id>/pods/<str:namespace>/<str:pod_name>/', pod_info, name='pod_info'),
    path('<int:cluster_id>/replicasets/<str:namespace>/<str:rs_name>/', rs_info, name='rs_info'),
    path('<int:cluster_id>/deployments/<str:namespace>/<str:deploy_name>/', deploy_info, name='deploy_info'),
    path('<int:cluster_id>/statefulsets/<str:namespace>/<str:sts_name>/', sts_info, name='sts_info'),
    path('<int:cluster_id>/daemonset/<str:namespace>/<str:daemonset_name>/', daemonset_info, name='daemonset_info'),
    path('<int:cluster_id>/jobs/<str:namespace>/<str:job_name>/', jobs_info, name='jobs_info'),
    path('<int:cluster_id>/cronjobs/<str:namespace>/<str:cronjob_name>/', cronjob_info, name='cronjob_info'),
    
    
    # Events
    path('<int:cluster_id>/events', events, name='events'),
    path('events/', events, name='events'),
    
    # ConfigMap & Secrets
    path('<int:cluster_id>/configmaps', configmaps, name='configmaps'),
    path('<int:cluster_id>/secrets', secrets, name='secrets'),

    path('<int:cluster_id>/configmaps/<str:namespace>/<str:configmap_name>/', configmap_info, name='configmap_info'),
    path('<int:cluster_id>/secrets/<str:namespace>/<str:secret_name>/', secret_info, name='secret_info'),


    # Services
    path('<int:cluster_id>/services', services, name='services'),
    path('<int:cluster_id>/endpoints', endpoints, name='endpoints'),
    
    path('<int:cluster_id>/services/<str:namespace>/<str:service_name>/', service_info, name='service_info'),
    path('<int:cluster_id>/endpoints/<str:namespace>/<str:endpoint_name>/', endpoint_info, name='endpoint_info'),

    
    # Cluster Management
    path('<int:cluster_id>/nodes/', nodes, name='nodes'),
    path('<int:cluster_id>/namespace', namespace, name="namespace"),
    path('<int:cluster_id>/limitrange', limitrange, name="limitrange"),
    path('<int:cluster_id>/resourcequotas', resourcequotas, name="resourcequotas"),
    path('<int:cluster_id>/pdb', pdb, name="pdb"),

    path('<int:cluster_id>/nodes/<str:node_name>/', node_info, name='node_info'),
    path('<int:cluster_id>/namespace/<str:namespace>/', ns_info, name='ns_info'),
    path('<int:cluster_id>/limitrange/<str:namespace>/<str:limitrange_name>/', limitrange_info, name='limitrange_info'),
    path('<int:cluster_id>/resourcequotas/<str:namespace>/<str:resourcequota_name>/', resourcequota_info, name='resourcequota_info'),
    path('<int:cluster_id>/pdb/<str:namespace>/<str:pdb_name>/', pdb_info, name='pdb_info'),

    # Persistent Storage
    path('<int:cluster_id>/pv', persistentvolume, name="persistentvolume"),
    path('<int:cluster_id>/pvc', persistentvolumeclaim, name="persistentvolumeclaim"),
    path('<int:cluster_id>/storageclass', storageclass, name="storageclass"),

    path('<int:cluster_id>/pv/<str:pv_name>/', pv_info, name='pv_info'),
    path('<int:cluster_id>/pvc/<str:namespace>/<str:pvc_name>/', pvc_info, name='pvc_info'),

    path('<int:cluster_id>/storageclass/<str:sc_name>/', storageclass_info, name='sc_info'),
    
    # Networking
    path('<int:cluster_id>/np', np, name="np"),
    path('<int:cluster_id>/ingress', ingress, name="ingress"),
    
    path('<int:cluster_id>/np/<str:namespace>/<str:np_name>/', np_info, name='np_info'),
    path('<int:cluster_id>/ingress/<str:namespace>/<str:ingress_name>/', ingress_info, name='ingress_info'),


    # RBAC
    path('<int:cluster_id>/role', role, name="role"),
    path('<int:cluster_id>/rolebinding', rolebinding, name="rolebinding"),
    path('<int:cluster_id>/clusterrole', clusterrole, name="clusterrole"),
    path('<int:cluster_id>/clusterrolebinding', clusterrolebinding, name="clusterrolebinding"),
    path('<int:cluster_id>/sa', service_account, name="service_account"),
    
    path('<int:cluster_id>/role/<str:namespace>/<str:role_name>/', role_info, name='role_info'),
    path('<int:cluster_id>/clusterrole/<str:cluster_role_name>/', clusterrole_info, name='clusterrole_info'),
    path('<int:cluster_id>/rolebinding/<str:namespace>/<str:role_binding_name>/', role_binding_info, name='role_binding_info'),
    path('<int:cluster_id>/clusterrolebinding/<str:cluster_role_binding_name>/', cluster_role_binding_info, name='cluster_role_binding_info'),
    path('<int:cluster_id>/sa/<str:namespace>/<str:sa_name>/', service_accountInfo, name='service_accountInfo'),

    # Pod Metrics
    path('<int:cluster_id>/pod_metrics', pod_metrics, name="pod_metrics"),
    path('<int:cluster_id>/node_metrics', node_metrics, name="node_metrics"),
    
]
