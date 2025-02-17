from django.urls import path
from dashboard.views import dashboard, pods, nodes, replicasets, deployments, pod_info, events, rs_info, deploy_info

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
    
]
