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
                                pod_metrics, node_metrics, pdb, pdb_info, np, np_info, ingress, \
                                ingress_info, execute_command, generate_reports, kube_bench_report, \
                                cluster_hotspot, k8sgpt_view

from dashboard.decorators import require_permission, session_required

urlpatterns = [

    # ── Always accessible ────────────────────────────────────────────────
    path('<int:cluster_id>/dashboard/',  dashboard,        name='dashboard'),
    path('execute/',                     execute_command,  name='execute_command'),
    path('generate_reports/',            generate_reports, name='generate_reports'),
    path('<int:cluster_id>/kube-bench/', kube_bench_report, name='kube_bench_report'),
    path('<int:cluster_id>/hotspot/',    cluster_hotspot,   name='cluster_hotspot'),
    path('<int:cluster_id>/k8sgpt',      k8sgpt_view,       name='k8sgpt'),

    # ── Events ───────────────────────────────────────────────────────────
    path('<int:cluster_id>/events', require_permission('events')(events), name='events'),
    path('events/',                 require_permission('events')(events), name='events_no_cluster'),

    # ── WORKLOADS ────────────────────────────────────────────────────────
    path('<int:cluster_id>/pods',        require_permission('workloads')(pods),        name='pods'),
    path('<int:cluster_id>/replicasets', require_permission('workloads')(replicasets), name='replicasets'),
    path('<int:cluster_id>/deployments', require_permission('workloads')(deployments), name='deployments'),
    path('<int:cluster_id>/statefulsets',require_permission('workloads')(statefulsets),name='statefulsets'),
    path('<int:cluster_id>/daemonset',   require_permission('workloads')(daemonset),   name='daemonset'),
    path('<int:cluster_id>/jobs',        require_permission('workloads')(jobs),        name='jobs'),
    path('<int:cluster_id>/cronjobs',    require_permission('workloads')(cronjobs),    name='cronjobs'),

    path('<int:cluster_id>/pods/<str:namespace>/<str:pod_name>/',           require_permission('workloads')(pod_info),       name='pod_info'),
    path('<int:cluster_id>/replicasets/<str:namespace>/<str:rs_name>/',     require_permission('workloads')(rs_info),        name='rs_info'),
    path('<int:cluster_id>/deployments/<str:namespace>/<str:deploy_name>/', require_permission('workloads')(deploy_info),    name='deploy_info'),
    path('<int:cluster_id>/statefulsets/<str:namespace>/<str:sts_name>/',   require_permission('workloads')(sts_info),       name='sts_info'),
    path('<int:cluster_id>/daemonset/<str:namespace>/<str:daemonset_name>/',require_permission('workloads')(daemonset_info), name='daemonset_info'),
    path('<int:cluster_id>/jobs/<str:namespace>/<str:job_name>/',           require_permission('workloads')(jobs_info),      name='jobs_info'),
    path('<int:cluster_id>/cronjobs/<str:namespace>/<str:cronjob_name>/',   require_permission('workloads')(cronjob_info),   name='cronjob_info'),

    # ── CONFIGMAPS & SECRETS ─────────────────────────────────────────────
    path('<int:cluster_id>/configmaps',                                       require_permission('configmaps')(configmaps),    name='configmaps'),
    path('<int:cluster_id>/secrets',                                          require_permission('configmaps')(secrets),       name='secrets'),
    path('<int:cluster_id>/configmaps/<str:namespace>/<str:configmap_name>/', require_permission('configmaps')(configmap_info),name='configmap_info'),
    path('<int:cluster_id>/secrets/<str:namespace>/<str:secret_name>/',       require_permission('configmaps')(secret_info),   name='secret_info'),

    # ── SERVICES ─────────────────────────────────────────────────────────
    path('<int:cluster_id>/services',                                         require_permission('services')(services),      name='services'),
    path('<int:cluster_id>/endpoints',                                        require_permission('services')(endpoints),     name='endpoints'),
    path('<int:cluster_id>/services/<str:namespace>/<str:service_name>/',     require_permission('services')(service_info),  name='service_info'),
    path('<int:cluster_id>/endpoints/<str:namespace>/<str:endpoint_name>/',   require_permission('services')(endpoint_info), name='endpoint_info'),

    # ── CLUSTER MANAGEMENT ───────────────────────────────────────────────
    path('<int:cluster_id>/nodes/',                                                   require_permission('cluster_management')(nodes),           name='nodes'),
    path('<int:cluster_id>/namespace',                                                require_permission('cluster_management')(namespace),        name='namespace'),
    path('<int:cluster_id>/limitrange',                                               require_permission('cluster_management')(limitrange),       name='limitrange'),
    path('<int:cluster_id>/resourcequotas',                                           require_permission('cluster_management')(resourcequotas),   name='resourcequotas'),
    path('<int:cluster_id>/pdb',                                                      require_permission('cluster_management')(pdb),              name='pdb'),

    path('<int:cluster_id>/nodes/<str:node_name>/',                                   require_permission('cluster_management')(node_info),         name='node_info'),
    path('<int:cluster_id>/namespace/<str:namespace>/',                               require_permission('cluster_management')(ns_info),           name='ns_info'),
    path('<int:cluster_id>/limitrange/<str:namespace>/<str:limitrange_name>/',        require_permission('cluster_management')(limitrange_info),   name='limitrange_info'),
    path('<int:cluster_id>/resourcequotas/<str:namespace>/<str:resourcequota_name>/', require_permission('cluster_management')(resourcequota_info),name='resourcequota_info'),
    path('<int:cluster_id>/pdb/<str:namespace>/<str:pdb_name>/',                      require_permission('cluster_management')(pdb_info),          name='pdb_info'),

    # ── PERSISTENT STORAGE ───────────────────────────────────────────────
    path('<int:cluster_id>/pv',                                    require_permission('storage')(persistentvolume),     name='persistentvolume'),
    path('<int:cluster_id>/pvc',                                   require_permission('storage')(persistentvolumeclaim),name='persistentvolumeclaim'),
    path('<int:cluster_id>/storageclass',                          require_permission('storage')(storageclass),         name='storageclass'),
    path('<int:cluster_id>/pv/<str:pv_name>/',                     require_permission('storage')(pv_info),              name='pv_info'),
    path('<int:cluster_id>/pvc/<str:namespace>/<str:pvc_name>/',   require_permission('storage')(pvc_info),             name='pvc_info'),
    path('<int:cluster_id>/storageclass/<str:sc_name>/',           require_permission('storage')(storageclass_info),    name='sc_info'),

    # ── NETWORKING / INGRESS ─────────────────────────────────────────────
    path('<int:cluster_id>/np',                                          require_permission('ingress')(np),          name='np'),
    path('<int:cluster_id>/ingress',                                     require_permission('ingress')(ingress),     name='ingress'),
    path('<int:cluster_id>/np/<str:namespace>/<str:np_name>/',           require_permission('ingress')(np_info),     name='np_info'),
    path('<int:cluster_id>/ingress/<str:namespace>/<str:ingress_name>/', require_permission('ingress')(ingress_info),name='ingress_info'),

    # ── RBAC SECTION ─────────────────────────────────────────────────────
    path('<int:cluster_id>/role',               require_permission('rbac')(role),             name='role'),
    path('<int:cluster_id>/rolebinding',        require_permission('rbac')(rolebinding),      name='rolebinding'),
    path('<int:cluster_id>/clusterrole',        require_permission('rbac')(clusterrole),      name='clusterrole'),
    path('<int:cluster_id>/clusterrolebinding', require_permission('rbac')(clusterrolebinding),name='clusterrolebinding'),
    path('<int:cluster_id>/sa',                 require_permission('rbac')(serviceAccount),   name='serviceAccount'),

    path('<int:cluster_id>/role/<str:namespace>/<str:role_name>/',                      require_permission('rbac')(role_info),                name='role_info'),
    path('<int:cluster_id>/clusterrole/<str:cluster_role_name>/',                       require_permission('rbac')(clusterrole_info),         name='clusterrole_info'),
    path('<int:cluster_id>/rolebinding/<str:namespace>/<str:role_binding_name>/',       require_permission('rbac')(role_binding_info),        name='role_binding_info'),
    path('<int:cluster_id>/clusterrolebinding/<str:cluster_role_binding_name>/',        require_permission('rbac')(cluster_role_binding_info),name='cluster_role_binding_info'),
    path('<int:cluster_id>/sa/<str:namespace>/<str:sa_name>/',                          require_permission('rbac')(serviceAccountInfo),       name='serviceAccountInfo'),

    # ── METRICS ──────────────────────────────────────────────────────────
    path('<int:cluster_id>/pod_metrics',  require_permission('metrics')(pod_metrics),  name='pod_metrics'),
    path('<int:cluster_id>/node_metrics', require_permission('metrics')(node_metrics), name='node_metrics'),
]