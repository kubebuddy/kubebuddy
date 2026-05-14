"""
KubeBuddy — SSO & RBAC Unit Tests
Run with:
    python manage.py test main.rbac_tests --verbosity=2
"""

import json
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, Client, RequestFactory

from main.models import SsoConfig, UserProfile


# ═══════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════

def make_user(username, is_superuser=False, password='testpass123'):
    user = User.objects.create_user(
        username=username, password=password, email=f'{username}@test.com'
    )
    if is_superuser:
        user.is_superuser = True
        user.is_staff = True
        user.save()
    return user


def make_sso(user, provider='google', client_id='cid123',
             client_secret='csec456', redirect_uri='https://app.test/cb', is_active=True):
    return SsoConfig.objects.create(
        user=user, provider=provider, client_id=client_id,
        client_secret=client_secret, redirect_uri=redirect_uri, is_active=is_active
    )


# ═══════════════════════════════════════════════════
# SSO MODEL TESTS
# ═══════════════════════════════════════════════════

class SsoConfigModelTest(TestCase):

    def setUp(self):
        self.user = make_user('ssouser')

    def test_create_google_sso(self):
        sso = make_sso(self.user, provider='google')
        self.assertEqual(sso.provider, 'google')
        self.assertTrue(sso.is_active)

    def test_create_github_sso(self):
        sso = make_sso(self.user, provider='github')
        self.assertEqual(sso.provider, 'github')

    def test_create_outlook_sso(self):
        sso = make_sso(self.user, provider='outlook')
        self.assertEqual(sso.provider, 'outlook')

    def test_str_representation(self):
        sso = make_sso(self.user, provider='google')
        self.assertIn('Google', str(sso))
        self.assertIn(self.user.username, str(sso))

    def test_masked_secret_long(self):
        sso = make_sso(self.user, client_secret='abcd1234efgh5678')
        masked = sso.get_masked_client_secret()
        self.assertTrue(masked.startswith('abcd'))
        self.assertTrue(masked.endswith('5678'))
        self.assertIn('...', masked)

    def test_masked_secret_short(self):
        sso = make_sso(self.user, client_secret='short')
        self.assertEqual(sso.get_masked_client_secret(), '********')

    def test_unique_together_user_provider(self):
        make_sso(self.user, provider='google')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            SsoConfig.objects.create(
                user=self.user, provider='google',
                client_id='other', client_secret='other'
            )

    def test_same_user_different_providers_allowed(self):
        make_sso(self.user, provider='google')
        sso2 = make_sso(self.user, provider='github', client_id='gh_cid')
        self.assertIsNotNone(sso2.pk)

    def test_redirect_uri_optional(self):
        sso = SsoConfig.objects.create(
            user=self.user, provider='google',
            client_id='cid', client_secret='csec'
        )
        self.assertIsNone(sso.redirect_uri)

    def test_inactive_sso(self):
        sso = make_sso(self.user, is_active=False)
        self.assertFalse(sso.is_active)


# ═══════════════════════════════════════════════════
# SSO VIEW TESTS
# ═══════════════════════════════════════════════════

class SsoDetailsViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_user('admin_sso', is_superuser=True)
        self.client.login(username='admin_sso', password='testpass123')

    def _post(self, data):
        return self.client.post('/ssodetails/', data)

    def test_save_google_sso(self):
        resp = self._post({'provider': 'google', 'client_id': 'cid', 'client_secret': 'csec', 'redirect_uri': ''})
        self.assertIn('sso_config_success', resp.url)
        self.assertTrue(SsoConfig.objects.filter(user=self.admin, provider='google').exists())

    def test_save_github_sso(self):
        self._post({'provider': 'github', 'client_id': 'gh_cid', 'client_secret': 'gh_sec', 'redirect_uri': ''})
        self.assertTrue(SsoConfig.objects.filter(user=self.admin, provider='github').exists())

    def test_save_outlook_sso(self):
        self._post({'provider': 'outlook', 'client_id': 'ol_cid', 'client_secret': 'ol_sec', 'redirect_uri': ''})
        self.assertTrue(SsoConfig.objects.filter(user=self.admin, provider='outlook').exists())

    def test_invalid_provider_fails(self):
        resp = self._post({'provider': 'facebook', 'client_id': 'cid', 'client_secret': 'csec'})
        self.assertIn('sso_config_failed', resp.url)

    def test_missing_client_id_fails(self):
        resp = self._post({'provider': 'google', 'client_id': '', 'client_secret': 'csec'})
        self.assertIn('sso_config_failed', resp.url)

    def test_missing_client_secret_fails(self):
        resp = self._post({'provider': 'google', 'client_id': 'cid', 'client_secret': ''})
        self.assertIn('sso_config_failed', resp.url)

    def test_update_existing_sso(self):
        make_sso(self.admin, provider='google', client_id='old_cid', client_secret='old_sec')
        self._post({'provider': 'google', 'client_id': 'new_cid', 'client_secret': 'new_sec', 'redirect_uri': ''})
        sso = SsoConfig.objects.get(user=self.admin, provider='google')
        self.assertEqual(sso.client_id, 'new_cid')

    def test_delete_sso(self):
        make_sso(self.admin, provider='google')
        resp = self._post({'delete_sso_config': 'google'})
        self.assertFalse(SsoConfig.objects.filter(user=self.admin, provider='google').exists())
        self.assertIn('sso_config_success', resp.url)

    def test_unauthenticated_redirected(self):
        """
        FIX: The app redirects to /?next=/ssodetails/ (root login, not /login/).
        We verify it's a 302 redirect — the destination URL confirms auth enforcement.
        """
        self.client.logout()
        resp = self._post({'provider': 'google', 'client_id': 'cid', 'client_secret': 'csec'})
        self.assertEqual(resp.status_code, 302)
        # App redirects to root with next param — assert redirect happened (auth enforced)
        self.assertIn('/ssodetails/', resp.url)

    def test_get_redirects_to_settings(self):
        resp = self.client.get('/ssodetails/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('settings', resp.url)


# ═══════════════════════════════════════════════════
# GOOGLE SSO TESTS
# ═══════════════════════════════════════════════════

class GoogleSSOTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_user('gadmin', is_superuser=True)
        self.client.login(username='gadmin', password='testpass123')

    def _make_sso(self):
        return make_sso(self.admin, provider='google',
                        client_id='gcid', client_secret='gsec')

    def test_callback_no_code(self):
        """App renders login page (200) with error when no code provided."""
        resp = self.client.get('/google-callback/?error=access_denied')
        self.assertEqual(resp.status_code, 200)

    def test_callback_no_sso_configured(self):
        """App renders login page (200) when SSO is not configured."""
        resp = self.client.get('/google-callback/?code=abc123')
        self.assertEqual(resp.status_code, 200)

    @patch('main.views.http_requests.post')
    @patch('main.views.http_requests.get')
    def test_callback_success(self, mock_get, mock_post):
        self._make_sso()
        mock_post.return_value.json.return_value = {'access_token': 'tok123'}
        mock_get.return_value.json.return_value = {
            'email': 'newuser@google.com', 'given_name': 'New', 'family_name': 'User'
        }
        resp = self.client.get('/google-callback/?code=valid_code')
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(email='newuser@google.com').exists())

    @patch('main.views.http_requests.post')
    def test_callback_no_access_token(self, mock_post):
        """App renders login page (200) when access token is missing."""
        self._make_sso()
        mock_post.return_value.json.return_value = {}
        resp = self.client.get('/google-callback/?code=bad_code')
        self.assertEqual(resp.status_code, 200)

    @patch('main.views.http_requests.post')
    @patch('main.views.http_requests.get')
    def test_callback_no_email(self, mock_get, mock_post):
        """App renders login page (200) when email is missing from user info."""
        self._make_sso()
        mock_post.return_value.json.return_value = {'access_token': 'tok123'}
        mock_get.return_value.json.return_value = {}
        resp = self.client.get('/google-callback/?code=valid_code')
        self.assertEqual(resp.status_code, 200)

    def test_api_no_code(self):
        resp = self.client.post('/api/google-login/',
                                data=json.dumps({}), content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_api_no_sso_configured(self):
        resp = self.client.post('/api/google-login/',
                                data=json.dumps({'code': 'abc'}), content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    @patch('main.views.http_requests.post')
    @patch('main.views.http_requests.get')
    def test_api_success(self, mock_get, mock_post):
        self._make_sso()
        mock_post.return_value.json.return_value = {'access_token': 'tok123'}
        mock_get.return_value.json.return_value = {
            'email': 'apiuser@google.com', 'given_name': 'API', 'family_name': 'User'
        }
        resp = self.client.post('/api/google-login/',
                                data=json.dumps({'code': 'valid'}), content_type='application/json')
        self.assertTrue(resp.json().get('success'))


# ═══════════════════════════════════════════════════
# GITHUB SSO TESTS
# ═══════════════════════════════════════════════════

class GitHubSSOTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_user('ghadmin', is_superuser=True)
        self.client.login(username='ghadmin', password='testpass123')

    def _make_sso(self):
        return make_sso(self.admin, provider='github', client_id='gh_cid', client_secret='gh_sec')

    def test_callback_no_code(self):
        """App renders login page (200) with error when no code provided."""
        resp = self.client.get('/github-callback/?error=access_denied')
        self.assertEqual(resp.status_code, 200)

    def test_callback_no_sso(self):
        """App renders login page (200) when SSO is not configured."""
        resp = self.client.get('/github-callback/?code=abc')
        self.assertEqual(resp.status_code, 200)

    @patch('main.views.http_requests.post')
    @patch('main.views.http_requests.get')
    def test_callback_success(self, mock_get, mock_post):
        self._make_sso()
        mock_post.return_value.json.return_value = {'access_token': 'gh_tok'}
        mock_get.return_value.json.return_value = {
            'email': 'ghuser@github.com', 'login': 'ghuser', 'name': 'GH User'
        }
        resp = self.client.get('/github-callback/?code=valid')
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(email='ghuser@github.com').exists())

    @patch('main.views.http_requests.post')
    @patch('main.views.http_requests.get')
    def test_callback_fetches_email_fallback(self, mock_get, mock_post):
        self._make_sso()
        mock_post.return_value.json.return_value = {'access_token': 'gh_tok'}
        mock_get.side_effect = [
            MagicMock(json=lambda: {'login': 'ghuser', 'name': 'GH User', 'email': None}),
            MagicMock(json=lambda: [{'email': 'private@gh.com', 'primary': True, 'verified': True}]),
        ]
        resp = self.client.get('/github-callback/?code=valid')
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(email='private@gh.com').exists())

    def test_api_no_code(self):
        resp = self.client.post('/api/github-login/',
                                data=json.dumps({}), content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    @patch('main.views.http_requests.post')
    @patch('main.views.http_requests.get')
    def test_api_success(self, mock_get, mock_post):
        self._make_sso()
        mock_post.return_value.json.return_value = {'access_token': 'gh_tok'}
        mock_get.return_value.json.return_value = {
            'email': 'api_gh@github.com', 'login': 'apiuser', 'name': 'API User'
        }
        resp = self.client.post('/api/github-login/',
                                data=json.dumps({'code': 'valid'}), content_type='application/json')
        self.assertTrue(resp.json().get('success'))


# ═══════════════════════════════════════════════════
# OUTLOOK SSO TESTS
# ═══════════════════════════════════════════════════

class OutlookSSOTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = make_user('oladmin', is_superuser=True)
        self.client.login(username='oladmin', password='testpass123')

    def _make_sso(self):
        return make_sso(self.admin, provider='outlook', client_id='ol_cid', client_secret='ol_sec')

    def test_callback_no_code(self):
        """App renders login page (200) with error when no code provided."""
        resp = self.client.get('/outlook-callback/?error=access_denied')
        self.assertEqual(resp.status_code, 200)

    def test_callback_no_sso(self):
        """App renders login page (200) when SSO is not configured."""
        resp = self.client.get('/outlook-callback/?code=abc')
        self.assertEqual(resp.status_code, 200)

    @patch('main.views.http_requests.post')
    @patch('main.views.http_requests.get')
    def test_callback_success(self, mock_get, mock_post):
        self._make_sso()
        mock_post.return_value.json.return_value = {'access_token': 'ms_tok'}
        mock_get.return_value.json.return_value = {
            'mail': 'msuser@outlook.com', 'displayName': 'MS User',
            'givenName': 'MS', 'surname': 'User'
        }
        resp = self.client.get('/outlook-callback/?code=valid')
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(User.objects.filter(email='msuser@outlook.com').exists())

    @patch('main.views.http_requests.post')
    @patch('main.views.http_requests.get')
    def test_callback_uses_principal_name_fallback(self, mock_get, mock_post):
        self._make_sso()
        mock_post.return_value.json.return_value = {'access_token': 'ms_tok'}
        mock_get.return_value.json.return_value = {
            'userPrincipalName': 'fallback@outlook.com', 'displayName': 'Fallback'
        }
        resp = self.client.get('/outlook-callback/?code=valid')
        self.assertEqual(resp.status_code, 302)

    def test_api_no_code(self):
        resp = self.client.post('/api/outlook-login/',
                                data=json.dumps({}), content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    @patch('main.views.http_requests.post')
    @patch('main.views.http_requests.get')
    def test_api_success(self, mock_get, mock_post):
        self._make_sso()
        mock_post.return_value.json.return_value = {'access_token': 'ms_tok'}
        mock_get.return_value.json.return_value = {
            'mail': 'api_ms@outlook.com', 'displayName': 'API MS',
            'givenName': 'API', 'surname': 'MS'
        }
        resp = self.client.post('/api/outlook-login/',
                                data=json.dumps({'code': 'valid'}), content_type='application/json')
        self.assertTrue(resp.json().get('success'))


# ═══════════════════════════════════════════════════
# RBAC — UserProfile MODEL TESTS
# ═══════════════════════════════════════════════════

class UserProfileModelTest(TestCase):

    def setUp(self):
        self.regular = make_user('regular')
        self.superuser = make_user('superadmin', is_superuser=True)

    def test_creates_profile_for_regular_user(self):
        profile = UserProfile.get_or_create_for_user(self.regular)
        self.assertEqual(profile.role, 'user')

    def test_creates_profile_for_superuser(self):
        profile = UserProfile.get_or_create_for_user(self.superuser)
        self.assertEqual(profile.role, 'admin')
        self.assertTrue(profile.can_rbac)

    def test_get_or_create_idempotent(self):
        p1 = UserProfile.get_or_create_for_user(self.regular)
        p2 = UserProfile.get_or_create_for_user(self.regular)
        self.assertEqual(p1.pk, p2.pk)

    def test_regular_user_default_permissions(self):
        profile = UserProfile.get_or_create_for_user(self.regular)
        self.assertTrue(profile.can_workloads)
        self.assertFalse(profile.can_cluster_management)
        self.assertFalse(profile.can_services)
        self.assertFalse(profile.can_storage)
        self.assertFalse(profile.can_ingress)
        self.assertFalse(profile.can_configmaps)
        self.assertFalse(profile.can_metrics)
        self.assertFalse(profile.can_events)
        self.assertFalse(profile.can_rbac)

    def test_superuser_has_all_permissions(self):
        profile = UserProfile.get_or_create_for_user(self.superuser)
        for perm in ['can_workloads', 'can_cluster_management', 'can_services',
                     'can_storage', 'can_ingress', 'can_configmaps',
                     'can_metrics', 'can_events', 'can_rbac']:
            self.assertTrue(getattr(profile, perm))

    def test_is_admin_role_superuser(self):
        profile = UserProfile.get_or_create_for_user(self.superuser)
        self.assertTrue(profile.is_admin_role())

    def test_is_admin_role_admin_role_user(self):
        profile = UserProfile.get_or_create_for_user(self.regular)
        profile.role = 'admin'
        profile.save()
        self.assertTrue(profile.is_admin_role())

    def test_is_not_admin_role_regular(self):
        profile = UserProfile.get_or_create_for_user(self.regular)
        self.assertFalse(profile.is_admin_role())

    def test_get_permissions_list_admin(self):
        profile = UserProfile.get_or_create_for_user(self.superuser)
        self.assertEqual(len(profile.get_permissions_list()), 9)

    def test_get_permissions_list_partial(self):
        profile = UserProfile.get_or_create_for_user(self.regular)
        profile.can_services = True
        profile.save()
        perms = profile.get_permissions_list()
        self.assertIn('Services', perms)
        self.assertNotIn('RBAC', perms)

    def test_get_permissions_display_no_perms(self):
        profile = UserProfile.get_or_create_for_user(self.regular)
        profile.can_workloads = False
        profile.save()
        self.assertEqual(profile.get_permissions_display(), 'No permissions')

    def test_str_representation(self):
        profile = UserProfile.get_or_create_for_user(self.regular)
        self.assertIn(self.regular.username, str(profile))


# ═══════════════════════════════════════════════════
# RBAC — has_permission HELPER
# ═══════════════════════════════════════════════════

class HasPermissionTest(TestCase):

    def setUp(self):
        from main.views import has_permission
        self.has_permission = has_permission
        self.superuser = make_user('superperm', is_superuser=True)
        self.regular = make_user('regularperm')
        # Ensure profile exists before tests run
        UserProfile.get_or_create_for_user(self.regular)

    def test_superuser_has_all_permissions(self):
        for perm in ['workloads', 'cluster_management', 'services', 'storage',
                     'ingress', 'configmaps', 'metrics', 'events', 'rbac']:
            self.assertTrue(self.has_permission(self.superuser, perm))

    def test_regular_user_has_workloads_by_default(self):
        self.assertTrue(self.has_permission(self.regular, 'workloads'))

    def test_regular_user_denied_rbac(self):
        self.assertFalse(self.has_permission(self.regular, 'rbac'))

    def test_granted_permission_returns_true(self):
        """
        FIX: Refresh profile from DB after update to ensure has_permission
        reads the latest persisted value.
        """
        profile = UserProfile.objects.get(user=self.regular)
        profile.can_metrics = True
        profile.save()
        # Refresh user object to bust any caching
        self.regular.refresh_from_db()
        self.assertTrue(self.has_permission(self.regular, 'metrics'))

    def test_admin_role_has_all(self):
        """
        FIX: Set role to 'admin' and save, then refresh user before checking.
        has_permission uses is_admin_role() which checks the profile role field.
        """
        profile = UserProfile.objects.get(user=self.regular)
        profile.role = 'admin'
        profile.save()
        self.regular.refresh_from_db()
        self.assertTrue(self.has_permission(self.regular, 'rbac'))

    def test_unknown_permission_returns_false(self):
        self.assertFalse(self.has_permission(self.regular, 'nonexistent'))


# ═══════════════════════════════════════════════════
# RBAC — require_permission DECORATOR
# ═══════════════════════════════════════════════════

class RequirePermissionDecoratorTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.superuser = make_user('dec_super', is_superuser=True)
        self.regular = make_user('dec_regular')
        UserProfile.get_or_create_for_user(self.regular)

    def _make_view(self, permission):
        from dashboard.decorators import require_permission
        from django.http import HttpResponse
        @require_permission(permission)
        def dummy_view(request, cluster_id=1):
            return HttpResponse('ok')
        return dummy_view

    def _request(self, user):
        request = self.factory.get('/1/pods')
        request.user = user
        return request

    def test_superuser_always_allowed(self):
        view = self._make_view('rbac')
        resp = view(self._request(self.superuser), cluster_id=1)
        self.assertEqual(resp.status_code, 200)

    def test_user_with_permission_allowed(self):
        profile = UserProfile.objects.get(user=self.regular)
        profile.can_services = True
        profile.save()
        resp = self._make_view('services')(self._request(self.regular), cluster_id=1)
        self.assertEqual(resp.status_code, 200)

    def test_user_without_permission_redirected(self):
        resp = self._make_view('rbac')(self._request(self.regular), cluster_id=5)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('5/dashboard', resp.url)

    def test_unauthenticated_redirected_to_login(self):
        """
        FIX: The decorator redirects AnonymousUser to '/' (the root/login page),
        not to '/login/'. We verify it's a 302 redirect to the root path.
        """
        from django.contrib.auth.models import AnonymousUser
        request = self.factory.get('/1/pods')
        request.user = AnonymousUser()
        resp = self._make_view('workloads')(request, cluster_id=1)
        self.assertEqual(resp.status_code, 302)
        # App uses '/' as the login entry point
        self.assertEqual(resp.url, '/')

    def test_admin_role_allowed(self):
        profile = UserProfile.objects.get(user=self.regular)
        profile.role = 'admin'
        profile.save()
        resp = self._make_view('rbac')(self._request(self.regular), cluster_id=1)
        self.assertEqual(resp.status_code, 200)

    def test_all_nine_permission_flags(self):
        from dashboard.decorators import require_permission
        from django.http import HttpResponse
        perms = ['workloads', 'cluster_management', 'services', 'storage',
                 'ingress', 'configmaps', 'metrics', 'events', 'rbac']
        for perm in perms:
            user = make_user(f'flag_{perm}')
            profile = UserProfile.get_or_create_for_user(user)
            for p in perms:
                setattr(profile, f'can_{p}', False)
            setattr(profile, f'can_{perm}', True)
            profile.save()

            @require_permission(perm)
            def dummy(request, cluster_id=1):
                return HttpResponse('ok')

            request = self.factory.get('/1/test')
            request.user = user
            resp = dummy(request, cluster_id=1)
            self.assertEqual(resp.status_code, 200, f'Failed for permission: {perm}')


# ═══════════════════════════════════════════════════
# RBAC — context processor
# ═══════════════════════════════════════════════════

class RbacContextProcessorTest(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def _run(self, user):
        from main.context_processors import rbac_permissions
        request = self.factory.get('/')
        request.user = user
        return rbac_permissions(request)

    def test_superuser_all_true(self):
        user = make_user('cp_super', is_superuser=True)
        ctx = self._run(user)
        for key in ['perms_workloads', 'perms_cluster_management', 'perms_services',
                    'perms_storage', 'perms_ingress', 'perms_configmaps',
                    'perms_metrics', 'perms_events', 'perms_rbac']:
            self.assertTrue(ctx[key])
        self.assertEqual(ctx['user_role'], 'admin')

    def test_unauthenticated_all_false(self):
        from django.contrib.auth.models import AnonymousUser
        from main.context_processors import rbac_permissions
        request = self.factory.get('/')
        request.user = AnonymousUser()
        ctx = rbac_permissions(request)
        self.assertFalse(ctx['perms_workloads'])
        self.assertFalse(ctx['perms_rbac'])

    def test_regular_user_partial(self):
        user = make_user('cp_regular')
        profile = UserProfile.get_or_create_for_user(user)
        profile.can_services = True
        profile.save()
        ctx = self._run(user)
        self.assertTrue(ctx['perms_workloads'])
        self.assertTrue(ctx['perms_services'])
        self.assertFalse(ctx['perms_rbac'])

    def test_admin_role_all_true(self):
        user = make_user('cp_admin_role')
        profile = UserProfile.get_or_create_for_user(user)
        profile.role = 'admin'
        profile.save()
        ctx = self._run(user)
        self.assertTrue(ctx['perms_rbac'])
        self.assertEqual(ctx['user_role'], 'admin')


# ═══════════════════════════════════════════════════
# RBAC — update_user_permissions VIEW
# ═══════════════════════════════════════════════════

class UpdateUserPermissionsViewTest(TestCase):

    def setUp(self):
        self.client = Client()
        self.superuser = make_user('perm_super', is_superuser=True)
        self.regular = make_user('perm_regular')
        UserProfile.get_or_create_for_user(self.regular)
        self.client.login(username='perm_super', password='testpass123')
        self.url = '/api/update-permissions/'

    def _post(self, data):
        return self.client.post(self.url, data=json.dumps(data),
                                content_type='application/json')

    def test_grant_multiple_permissions(self):
        resp = self._post({'user_id': self.regular.id,
                           'permissions': ['services', 'storage', 'metrics']})
        self.assertEqual(resp.json()['status'], 'success')
        profile = UserProfile.objects.get(user=self.regular)
        self.assertTrue(profile.can_services)
        self.assertTrue(profile.can_storage)
        self.assertTrue(profile.can_metrics)

    def test_revoke_all_permissions(self):
        self._post({'user_id': self.regular.id, 'permissions': []})
        profile = UserProfile.objects.get(user=self.regular)
        self.assertFalse(profile.can_workloads)
        self.assertFalse(profile.can_services)

    def test_grant_all_nine(self):
        all_perms = ['workloads', 'cluster_management', 'services', 'storage',
                     'ingress', 'configmaps', 'metrics', 'events', 'rbac']
        self._post({'user_id': self.regular.id, 'permissions': all_perms})
        profile = UserProfile.objects.get(user=self.regular)
        for perm in all_perms:
            self.assertTrue(getattr(profile, f'can_{perm}'))

    def test_cannot_restrict_superuser(self):
        another_super = make_user('another_super', is_superuser=True)
        resp = self._post({'user_id': another_super.id, 'permissions': []})
        self.assertEqual(resp.status_code, 400)

    def test_nonexistent_user_returns_404(self):
        resp = self._post({'user_id': 99999, 'permissions': []})
        self.assertEqual(resp.status_code, 404)

    def test_non_superuser_forbidden(self):
        self.client.logout()
        self.client.login(username='perm_regular', password='testpass123')
        resp = self._post({'user_id': self.regular.id, 'permissions': ['rbac']})
        self.assertEqual(resp.status_code, 403)

    def test_get_method_rejected(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 400)

    def test_response_contains_username(self):
        resp = self._post({'user_id': self.regular.id, 'permissions': ['workloads']})
        self.assertIn(self.regular.username, resp.json()['message'])

    def test_unauthenticated_redirected(self):
        self.client.logout()
        resp = self._post({'user_id': self.regular.id, 'permissions': []})
        self.assertEqual(resp.status_code, 302)