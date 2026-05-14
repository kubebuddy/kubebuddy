from functools import wraps
from django.shortcuts import render, redirect
from django.http import HttpResponseServerError
from urllib3.exceptions import MaxRetryError
from kubebuddy.appLogs import logger


def server_down_handler(view_func):
    @wraps(view_func)
    def _wrapped_view_func(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        except MaxRetryError as e:
            logger.error(e)
            return HttpResponseServerError(render(request, 'cluster_error.html'))
    return _wrapped_view_func


def session_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped


def require_permission(permission):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            try:
                from main.models import UserProfile
                profile = UserProfile.get_or_create_for_user(request.user)
                if profile.role == 'admin':
                    return view_func(request, *args, **kwargs)
                if getattr(profile, f'can_{permission}', False):
                    return view_func(request, *args, **kwargs)
                cluster_id = kwargs.get('cluster_id', 1)
                return redirect(f'/{cluster_id}/dashboard?cluster_id={cluster_id}')
            except Exception as e:
                logger.error(f"RBAC decorator error: {e}")
                cluster_id = kwargs.get('cluster_id', 1)
                return redirect(f'/{cluster_id}/dashboard?cluster_id={cluster_id}')
        return _wrapped
    return decorator