from django.urls import path
from dashboard.views import dashboard, pods, nodes, replicasets, deployment, pod_info, events

urlpatterns = [
    path('<int:cluster_id>/dashboard/', dashboard, name='dashboard'),
    path('<int:cluster_id>/pods', pods, name='pods'),
    path('<int:cluster_id>/pods/<str:namespace>/<str:pod_name>/', pod_info, name='pod_info'),
    path('nodes/', nodes, name='nodes'),
    path('<int:cluster_id>/replicasets', replicasets, name='replicasets'),
    path('<int:cluster_id>/deployment', deployment, name='deployment'),
    path('<int:cluster_id>/events', events, name='events'),

]
