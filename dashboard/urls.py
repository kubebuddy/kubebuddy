from django.urls import path
from dashboard.views import dashboard, pods, nodes

urlpatterns = [
    path('dashboard/<int:cluster_id>/', dashboard, name='dashboard'),
    path('pods/', pods, name='pods'),
    path('nodes/', nodes, name='nodes'),
]
