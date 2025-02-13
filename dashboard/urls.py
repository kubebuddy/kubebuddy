from django.urls import path
from dashboard.views import dashboard, pods, nodes, replicasets, deployment

urlpatterns = [
    path('<int:cluster_id>/dashboard/', dashboard, name='dashboard'),
    path('<int:cluster_id>/pods', pods, name='pods'),
    path('nodes/', nodes, name='nodes'),
    path('<int:cluster_id>/replicasets', replicasets, name='replicasets'),
    path('<int:cluster_id>/deployment', deployment, name='deployment'),

]
