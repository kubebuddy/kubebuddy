from django.test import TestCase
from .models import KubeConfig, Cluster
from django.core.exceptions import ValidationError

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
