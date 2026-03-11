from main.models import UserProfile


def rbac_permissions(request):
    default_denied = {
        'user_role':                'user',
        'perms_workloads':          False,
        'perms_cluster_management': False,
        'perms_services':           False,
        'perms_storage':            False,
        'perms_ingress':            False,
        'perms_configmaps':         False,
        'perms_metrics':            False,
        'perms_events':             False,
        'perms_rbac':               False,
    }

    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return default_denied

    if request.user.is_superuser:
        return {
            'user_role':                'admin',
            'perms_workloads':          True,
            'perms_cluster_management': True,
            'perms_services':           True,
            'perms_storage':            True,
            'perms_ingress':            True,
            'perms_configmaps':         True,
            'perms_metrics':            True,
            'perms_events':             True,
            'perms_rbac':               True,
        }

    try:
        profile = UserProfile.get_or_create_for_user(request.user)

        if profile.role == 'admin':
            return {
                'user_role':                'admin',
                'perms_workloads':          True,
                'perms_cluster_management': True,
                'perms_services':           True,
                'perms_storage':            True,
                'perms_ingress':            True,
                'perms_configmaps':         True,
                'perms_metrics':            True,
                'perms_events':             True,
                'perms_rbac':               True,
            }

        return {
            'user_role':                'user',
            'perms_workloads':          profile.can_workloads,
            'perms_cluster_management': profile.can_cluster_management,
            'perms_services':           profile.can_services,
            'perms_storage':            profile.can_storage,
            'perms_ingress':            profile.can_ingress,
            'perms_configmaps':         profile.can_configmaps,
            'perms_metrics':            profile.can_metrics,
            'perms_events':             profile.can_events,
            'perms_rbac':               profile.can_rbac,
        }

    except Exception:
        return default_denied