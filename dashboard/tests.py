from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch
from main.models import Cluster, KubeConfig
from django.http import FileResponse
import os

class ClusterHotspotViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = self._create_test_user()
        self.client.force_login(self.user)

        # Create the required KubeConfig instance
        self.kube_config = KubeConfig.objects.create(
            path='/fake/path/config',
            path_type='manual'
        )

        # Create a valid Cluster instance
        self.cluster = Cluster.objects.create(
            cluster_name='Test Cluster',
            kube_config=self.kube_config,
            context_name='context1'
        )

        # Use the real cluster_id for the URL
        self.url = reverse('cluster_hotspot', kwargs={'cluster_id': self.cluster.id})

    def _create_test_user(self):
        from django.contrib.auth.models import User
        return User.objects.create_user(username='testuser', password='password')

    @patch('dashboard.views.get_utils_data')
    @patch('dashboard.views.get_cluster_hotspot')
    def test_cluster_hotspot_view_renders_correct_template_and_context(self, mock_hotspot, mock_utils):
        # Mock get_utils_data return
        mock_utils.return_value = (
            1, 'Test Cluster', '/fake/path/config', 
            ['cluster1', 'cluster2'], ['ns1', 'ns2'], 'context1'
        )

        # Mock get_cluster_hotspot return
        mock_hotspot.return_value = (
            [{'name': 'ns1', 'status': 'Active', 'age': '5d', 'labels': {}}],
            [{'namespace': 'ns1', 'pod': 'pod1', 'image': 'nginx:latest'}],
            [{'namespace': 'ns1', 'configmap': 'cm1', 'age': '3d'}],
            [{'namespace': 'ns1', 'secret': 'secret1', 'age': '2d'}],
            [{'namespace': 'ns1', 'pod': 'pod1', 'container': 'c1', 'image': 'nginx', 'missing_probes': {'liveness_probe': True, 'readiness_probe': False}}],
            [
                {'namespace': 'ns1', 'pod': 'pod1', 'container': 'c1', 'restart_count': 5},
                {'namespace': 'ns1', 'pod': 'pod2', 'container': 'c2', 'restart_count': 3}
            ],
            [{'namespace': 'ns1', 'pod': 'pod1', 'container': 'c1', 'image': 'nginx'}]
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/cluster_hotspot.html')
        self.assertIn('container_restart_count', response.context)
        self.assertEqual(len(response.context['container_restart_count']), 2)
        self.assertEqual(response.context['current_cluster'], 'Test Cluster')

class KubeBenchReportViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.cluster_id = 1
        self.url = reverse("kube_bench_report", kwargs={"cluster_id": self.cluster_id})

        # Create dummy kube_bench_report.pdf in static/fpdf
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.report_path = os.path.join(base_dir, 'static', 'fpdf', 'kube_bench_report.pdf')
        os.makedirs(os.path.dirname(self.report_path), exist_ok=True)

    def tearDown(self):
        import time
        time.sleep(0.1)  # Optional: avoids file-lock race on Windows

        if os.path.exists(self.report_path):
            try:
                os.remove(self.report_path)
            except PermissionError:
                time.sleep(0.1)
                os.remove(self.report_path)

    @patch("dashboard.views.kube_bench.kube_bench_report_generate")
    @patch("dashboard.views.get_utils_data")
    def test_kube_bench_report_success(self, mock_get_utils_data, mock_generate_report):
        # Mock expected return values
        mock_get_utils_data.return_value = (
            self.cluster_id, "Test Cluster", "/fake/path", [], [], "context-name"
        )
        mock_generate_report.return_value = None  # Doesn't need to return anything

        # Create dummy PDF (simulating that generate function did it)
        with open(self.report_path, 'wb') as f:
            f.write(b"%PDF-1.4 Dummy PDF content")

        with patch("dashboard.views.os.path.join", return_value=self.report_path):
            response = self.client.get(self.url)

            # ✅ Ensure streaming_content is fully consumed (closes file)
            for _ in response.streaming_content:
                pass

        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response, FileResponse)
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="kube_bench_report.pdf"')
        self.assertEqual(response['Content-Type'], 'application/pdf')

    @patch("dashboard.views.kube_bench.kube_bench_report_generate")
    @patch("dashboard.views.get_utils_data")
    def test_kube_bench_report_missing_file(self, mock_get_utils_data, mock_generate_report):
        # Simulate generate_report did not produce the file
        mock_get_utils_data.return_value = (
            self.cluster_id, "Test Cluster", "/fake/path", [], [], "context-name"
        )
        mock_generate_report.return_value = None

        # Ensure file is missing
        if os.path.exists(self.report_path):
            os.remove(self.report_path)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 500)  # Exception caught in view

class K8sGPTViewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.cluster_id = 1
        self.url = reverse('k8sgpt', kwargs={'cluster_id': self.cluster_id})

    @patch('dashboard.views.get_utils_data')
    def test_k8sgpt_get_request(self, mock_get_utils_data):
        # Mock return values
        mock_get_utils_data.return_value = (
            self.cluster_id,
            "test-cluster",
            "/fake/path",
            ["cluster1", "cluster2"],
            ["default", "kube-system"],
            "test-context"
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/k8sgpt.html')
        self.assertIn("cluster_id", response.context)
        self.assertIn("registered_clusters", response.context)
        self.assertIn("namespaces", response.context)

    @patch('dashboard.views.get_utils_data')
    @patch('dashboard.views.k8sgpt.k8sgpt_analyze')
    def test_k8sgpt_post_request_analyze(self, mock_analyze, mock_get_utils_data):
        mock_get_utils_data.return_value = (
            self.cluster_id,
            "test-cluster",
            "/fake/path",
            ["cluster1", "cluster2"],
            ["default", "kube-system"],
            "test-context"
        )
        mock_analyze.return_value = {"results": "Analysis output"}

        response = self.client.post(self.url, data={"namespace": "default"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Kubernetes Analysis', response.content)

    @patch('dashboard.views.get_utils_data')
    @patch('dashboard.views.k8sgpt.k8sgpt_analyze_explain')
    def test_k8sgpt_post_request_explain(self, mock_explain, mock_get_utils_data):
        mock_get_utils_data.return_value = (
            self.cluster_id,
            "test-cluster",
            "/fake/path",
            ["cluster1", "cluster2"],
            ["default", "kube-system"],
            "test-context"
        )
        mock_explain.return_value = {"results": "Explain output"}

        response = self.client.post(self.url, data={"namespace": "default", "explain": "true"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Kubernetes Analysis', response.content)