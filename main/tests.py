from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.urls import reverse
from unittest.mock import patch, MagicMock
import os
from .models import KubeConfig, Cluster
from main.views import login_view, integrate_with
from django.core.exceptions import ValidationError
import tempfile, shutil


DEFAULT_PATH = '/path/one'
MANUAL_PATH = '/path/two'
DEFAULT_TYPE = 'default'
MANUAL_TYPE = 'manual'

class KubeConfigPositiveTest(TestCase):

    def setUp(self):
        self.kube_config_data = {
            'path': '/fake/path/config',
            'path_type': MANUAL_TYPE
        }

    def test_create_kubeconfig(self):
        kube_config = KubeConfig.objects.create(**self.kube_config_data)
        self.assertEqual(kube_config.path, self.kube_config_data['path'])
        self.assertEqual(kube_config.path_type, self.kube_config_data['path_type'])
        self.assertIsNotNone(kube_config.created_at)

    def test_unique_cluster_id_for_each_instance(self):
        kc1 = KubeConfig.objects.create(path=DEFAULT_PATH, path_type=DEFAULT_TYPE)
        kc2 = KubeConfig.objects.create(path=MANUAL_PATH, path_type=MANUAL_TYPE)
        self.assertNotEqual(kc1.cluster_id, kc2.cluster_id)
        self.assertEqual(kc1.cluster_id, 'cluster_id_01')
        self.assertEqual(kc2.cluster_id, 'cluster_id_02')

    def test_str_returns_cluster_id(self):
        kube_config = KubeConfig.objects.create(path='/Fake/path', path_type=DEFAULT_TYPE)
        self.assertEqual(str(kube_config), kube_config.cluster_id)

class KubeConfigNegativeTest(TestCase):

    def test_invalid_path_type(self):
        kube_config = KubeConfig(path='/invalid/path', path_type='invalid_choice')
        with self.assertRaises(ValidationError):
            kube_config.full_clean()

    def test_missing_path_field(self):
        kube_config = KubeConfig(path_type=DEFAULT_TYPE)
        with self.assertRaises(ValidationError):
            kube_config.full_clean()

    def test_missing_path_type_field(self):
        kube_config = KubeConfig(path='/valid/path')
        with self.assertRaises(ValidationError):
            kube_config.full_clean()

    def test_cluster_id_exceeds_max_length(self):
        kube_config = KubeConfig(path='/some/path', path_type=MANUAL_TYPE)
        kube_config.cluster_id = 'x' * 21
        with self.assertRaises(ValidationError):
            kube_config.full_clean()

class ClusterModelTest(TestCase):

    def setUp(self):
        self.kube_config = KubeConfig.objects.create(path='/cluster/path', path_type=DEFAULT_TYPE)

    def test_create_cluster(self):
        cluster = Cluster.objects.create(
            cluster_name='Test Cluster',
            kube_config=self.kube_config,
            context_name='Test-Context'
        )
        self.assertEqual(cluster.cluster_name, 'Test Cluster')
        self.assertEqual(cluster.kube_config, self.kube_config)
        self.assertEqual(cluster.context_name, 'Test-Context')

    def test_str_returns_cluster_name(self):
        cluster = Cluster.objects.create(
            cluster_name='MyCluster',
            kube_config=self.kube_config,
            context_name='ctx'
        )
        self.assertEqual(str(cluster), 'MyCluster')
        
class KubeConfigPositiveTestTestCase(TestCase):
    def setUp(self):
        self.test_case = KubeConfigPositiveTest()
        self.test_case.setUp()

    def test_create_kubeconfig(self):
        self.test_case.test_create_kubeconfig()

    def test_unique_cluster_id_for_each_instance(self):
        self.test_case.test_unique_cluster_id_for_each_instance()

    def test_str_returns_cluster_id(self):
        self.test_case.test_str_returns_cluster_id()

class LoginViewTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        User.objects.filter(username='admin').delete()
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin")
        self.user = User.objects.create_superuser(username=admin_username, password=admin_password, email='admin@example.com')
        self._tmp_dir = tempfile.mkdtemp(prefix="kubebuddy_test_")
        self._tmp_file = tempfile.NamedTemporaryFile(dir=self._tmp_dir, delete=False)
        self.kube_config = KubeConfig.objects.create(path=self._tmp_file.name, path_type='manual')

    def tearDown(self):
        # Clean up temp files and directory
        try:
            self._tmp_file.close()
            os.unlink(self._tmp_file.name)
            shutil.rmtree(self._tmp_dir)
        except Exception:
            pass

    @patch('os.path.isfile', return_value=True)
    @patch('django.contrib.auth.authenticate')
    def test_login_superuser_with_default_password_and_kubeconfig(self, mock_auth, mock_isfile):
        mock_auth.return_value = self.user
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin")
        request = self.factory.post('/login/', {'username': admin_username, 'password': admin_password})
        request.user = AnonymousUser()
        from django.contrib.sessions.backends.db import SessionStore
        request.session = SessionStore()
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        response = login_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/KubeBuddy', response.url)

    @patch('os.path.isfile', return_value=False)
    @patch('django.contrib.auth.authenticate')
    def test_login_superuser_without_kubeconfig(self, mock_auth, mock_isfile):
        mock_auth.return_value = self.user
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin")
        request = self.factory.post('/login/', {'username': admin_username, 'password': admin_password})
        request.user = AnonymousUser()
        from django.contrib.sessions.backends.db import SessionStore
        request.session = SessionStore()
        messages = FallbackStorage(request) 
        setattr(request, '_messages', messages)
        response = login_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/integrate', response.url)

    @patch('django.contrib.auth.authenticate')
    def test_login_non_superuser(self, mock_auth):
        user_username = os.getenv("USER_USERNAME", "user")
        user_password = os.getenv("USER_PASSWORD", "userpass")
        normal_user = User.objects.create_user(username=user_username, password=user_password)
        mock_auth.return_value = normal_user
        request = self.factory.post('/login/', {'username': user_username, 'password': user_password})
        request.user = AnonymousUser()
        setattr(request, 'session', {})
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        response = login_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Only superusers are allowed to log in.', response.content)

    def test_login_get_request(self):
        request = self.factory.get('/login/')
        request.user = AnonymousUser()
        setattr(request, 'session', {})
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        response = login_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'<form', response.content)

class IntegrateWithTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        try:
            User.objects.get(username=os.getenv("ADMIN_USERNAME", "admin")).delete()
        except User.DoesNotExist:
            pass
        admin_username = os.getenv("ADMIN_USERNAME", "admin")   
        admin_password = os.getenv("ADMIN_PASSWORD", "admin")
        self.user = User.objects.create_superuser(username=admin_username, password=admin_password, email='admin@example.com')

    @patch('os.path.isfile', return_value=False)
    def test_post_invalid_path(self, mock_isfile):
        request = self.factory.post('/integrate/', {'path': '/not/exist', 'path_type': 'manual'})
        request.user = self.user
        setattr(request, 'session', {})
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        response = integrate_with(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"does not exist", response.content)

    @patch('os.path.isfile', return_value=True)
    @patch('main.views.config.load_kube_config')
    @patch('main.views.KubeConfig.objects.create')
    @patch('main.views.save_clusters')
    def test_post_valid_path_creates_kubeconfig(self, mock_save_clusters, mock_create, mock_load_kube_config, mock_isfile):
        mock_create.return_value = MagicMock(spec=KubeConfig)
        request = self.factory.post('/integrate/', {'path': '/valid/path', 'path_type': 'manual'})
        request.user = self.user
        setattr(request, 'session', {})
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        response = integrate_with(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/KubeBuddy', response.url)

    @patch('os.path.isfile', return_value=True)
    @patch('main.views.config.load_kube_config', side_effect=Exception("Some error"))
    def test_post_valid_path_load_kube_config_exception(self, mock_load_kube_config, mock_isfile):
        request = self.factory.post('/integrate/', {'path': '/valid/path', 'path_type': 'manual'})
        request.user = self.user
        setattr(request, 'session', {})
        messages = FallbackStorage(request)
        setattr(request, '_messages', messages)
        response = integrate_with(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Unable to connect to the cluster", response.content)



