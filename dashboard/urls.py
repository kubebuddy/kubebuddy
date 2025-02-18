from django.urls import path
from dashboard.views import dashboard, pods, nodes, replicasets, deployments, pod_info, \
                                events, rs_info, deploy_info, \
                                configmaps, secrets, services, endpoints, \
                                statefulsets, daemonset, jobs, cronjobs


urlpatterns = [
    path('<str:cluster_name>/dashboard/', dashboard, name='dashboard'),
    path('<str:cluster_name>/pods', pods, name='pods'),
    path('<str:cluster_name>/pods/<str:namespace>/<str:pod_name>/', pod_info, name='pod_info'),
    path('nodes/', nodes, name='nodes'),
    path('<str:cluster_name>/replicasets', replicasets, name='replicasets'),
    path('<str:cluster_name>/replicasets/<str:namespace>/<str:rs_name>/', rs_info, name='rs_info'),
    path('<str:cluster_name>/deployments', deployments, name='deployments'),
    path('<str:cluster_name>/deployments/<str:namespace>/<str:deploy_name>/', deploy_info, name='deploy_info'),
    path('<str:cluster_name>/events', events, name='events'),
    path('<str:cluster_name>/configmaps', configmaps, name='configmaps'),
    path('<str:cluster_name>/secrets', secrets, name='secrets'),
    path('<str:cluster_name>/services', services, name='services'),
    path('<str:cluster_name>/endpoints', endpoints, name='endpoints'),
    path('<str:cluster_name>/statefulsets', statefulsets, name="statefulsets"),
    path('<str:cluster_name>/daemonset', daemonset, name="daemonset"),
    path('<str:cluster_name>/jobs', jobs, name="jobs"),
    path('<str:cluster_name>/cronjobs', cronjobs, name="cronjobs")
]
