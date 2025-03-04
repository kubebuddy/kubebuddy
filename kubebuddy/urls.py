"""
DRJ
URL configuration for kubebuddy project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from main.views import login_view, integrate_with, logout_view, change_pass, cluster_select, delete_cluster, cluster_error, \
                        check_api_key, set_api_key, chatbot_response, validate_api_key

urlpatterns = [
    path('admin/', admin.site.urls),

    # APP URLS
    path('', login_view, name='login'),  # Route for the login page
    path('logout/', logout_view, name='logout'),
    path('update-password/', change_pass, name='update-password'),
    path('integrate/', integrate_with, name='integrate'),
    path('', include('dashboard.urls')),
    path('KubeBuddy', cluster_select, name='cluster-select'),
    path('delete_cluster/<int:pk>/', delete_cluster, name='delete_cluster'),
    path('<str:cluster_name>/cluster_error', cluster_error, name="cluster_error"),
    path('check-api-key/', check_api_key, name='check_api_key'),
    path('set-api-key/', set_api_key, name='set_api_key'),
    path('chatbot-response/', chatbot_response, name='chatbot_response'),
    path('validate-api-key/', validate_api_key, name='validate_api_key'),
]
