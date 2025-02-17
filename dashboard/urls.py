from django.urls import path
from dashboard.views import dashboard, pods, nodes, replicasets, deployment, pod_info, events, statefulsets, daemonset, jobs

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
    path('<str:cluster_name>/statefulsets', statefulsets, name="statefulsets"),
    path('<str:cluster_name>/daemonset', daemonset, name="daemonset"),
    path('<str:cluster_name>/jobs', jobs, name="jobs")
]
