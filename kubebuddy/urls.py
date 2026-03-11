from django.contrib import admin
from django.urls import path, include
from main.views import (
    login_view, integrate_with, logout_view, change_pass, cluster_select,
    delete_cluster, cluster_error, check_api_key, set_api_key, chatbot_response,
    validate_api_key, settings, profile, send_otp, verify_otp, signup_view,
    # Google SSO
    google_callback, google_login_api,
    # GitHub SSO
    github_callback, github_login_api,
    # Microsoft Outlook SSO
    outlook_callback, outlook_login_api,
    # SMTP
    smtp_details, test_smtp_connection,
    # SSO config
    sso_details,
    # RBAC
    update_user_permissions,
)
from dashboard.src.clusters_DB import get_cluster_status

urlpatterns = [
    path('admin/', admin.site.urls),

    # APP URLS
    path('', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('update-password/', change_pass, name='update-password'),
    path('integrate/', integrate_with, name='integrate'),
    path('', include('dashboard.urls')),
    path('KubeBuddy', cluster_select, name='cluster-select'),
    path('delete_cluster/<int:pk>/', delete_cluster, name='delete_cluster'),
    path('<int:cluster_id>/cluster_error', cluster_error, name="cluster_error"),
    path('check-api-key/', check_api_key, name='check_api_key'),
    path('set-api-key/', set_api_key, name='set_api_key'),
    path('chatbot-response/', chatbot_response, name='chatbot_response'),
    path('validate-api-key/', validate_api_key, name='validate_api_key'),
    path('settings/', settings, name='settings'),
    path('profile/', profile, name='profile'),
    path('get_cluster_status/', get_cluster_status, name='get_cluster_status'),

    # OTP Authentication
    path('api/send-otp/', send_otp, name='send_otp'),
    path('api/verify-otp/', verify_otp, name='verify_otp'),
    path('signup/', signup_view, name='signup'),

    # Google SSO
    path('google-callback/', google_callback, name='google_callback'),
    path('api/google-login/', google_login_api, name='google_login_api'),

    # GitHub SSO
    path('github-callback/', github_callback, name='github_callback'),
    path('api/github-login/', github_login_api, name='github_login_api'),

    # Microsoft Outlook SSO
    path('outlook-callback/', outlook_callback, name='outlook_callback'),
    path('api/outlook-login/', outlook_login_api, name='outlook_login_api'),

    # SMTP Configuration
    path('smtpdetails/', smtp_details, name='smtp_details'),
    path('test-smtp/', test_smtp_connection, name='test_smtp_connection'),

    # SSO Configuration
    path('ssodetails/', sso_details, name='sso_details'),

    # RBAC
    path('api/update-permissions/', update_user_permissions, name='update_user_permissions'),
]