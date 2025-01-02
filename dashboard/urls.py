from django.urls import path
from dashboard.views import dashboard

urlpatterns = [
    path('dashboard/', dashboard, name='dashboard'),
]
