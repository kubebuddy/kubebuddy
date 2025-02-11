from django.urls import path
from dashboard.views import dashboard, pods, nodes

urlpatterns = [
    path('<int:cluster_id>/dashboard/', dashboard, name='dashboard'),
    path('<int:cluster_id>/pods', pods, name='pods'),
    path('nodes/', nodes, name='nodes'),
]
