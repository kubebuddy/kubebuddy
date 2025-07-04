from django.test import TestCase
from unittest.mock import patch, MagicMock
from dashboard.src.metrics import k8s_pod_metrics
from dashboard.src.cluster_management import k8s_limit_range, k8s_namespaces, k8s_nodes, k8s_pdb, k8s_resource_quota
from dashboard.src.config_secrets import k8s_configmaps, k8s_secrets
from dashboard.src.events import k8s_events
from dashboard.src.networking import k8s_ingress, k8s_np
from dashboard.src.persistent_volume import k8s_pv, k8s_pvc, k8s_storage_class
from dashboard.src.rbac import k8s_cluster_role_bindings, k8s_cluster_roles, k8s_role, k8s_rolebindings, k8s_service_accounts
from dashboard.src.services import k8s_endpoints, k8s_services
from kubernetes.client.rest import ApiException
from kubernetes.config.config_exception import ConfigException
import yaml
import base64
from datetime import datetime, timezone, timedelta
from dateutil.tz import tzutc
import os
# This file is convering test cases for files present in dashboard.src

# test cases for pod metrics
class GetPodMetricsTests(TestCase):
    def setUp(self):
        self.mock_configure_k8s = patch('dashboard.src.metrics.k8s_pod_metrics.configure_k8s').start()
        self.mock_core_v1 = patch('dashboard.src.metrics.k8s_pod_metrics.client.CoreV1Api').start()
        self.mock_custom_api = patch('dashboard.src.metrics.k8s_pod_metrics.client.CustomObjectsApi').start()
        self.addCleanup(patch.stopall)

        self.mock_v1_instance = self.mock_core_v1.return_value
        self.mock_metrics_api = self.mock_custom_api.return_value

    def test_successful_metrics_collection(self):
        # Mock namespace list
        mock_namespace = MagicMock()
        mock_namespace.metadata.name = "default"
        self.mock_v1_instance.list_namespace.return_value.items = [mock_namespace]

        # Mock pod list
        mock_pod = MagicMock()
        mock_pod.metadata.name = "test-pod"
        self.mock_v1_instance.list_namespaced_pod.return_value.items = [mock_pod]

        # Mock metrics API availability
        self.mock_metrics_api.get_api_resources.return_value = True

        # Mock metrics return
        self.mock_metrics_api.get_namespaced_custom_object.return_value = {
            "containers": [
                {"usage": {"cpu": "100000000n", "memory": "128Mi"}}
            ]
        }

        result, count, available = k8s_pod_metrics.get_pod_metrics("dummy/path", "dummy-context")

        self.assertEqual(count, 1)
        self.assertTrue(available)
        self.assertEqual(result[0]['name'], 'test-pod')
        self.assertEqual(result[0]['cpu_usage_milli'], 100)
        self.assertEqual(result[0]['memory_usage_mi'], 128.0)
        self.assertEqual(result[0]['error'], '-')


    def test_metrics_api_not_available(self):
        self.mock_metrics_api.get_api_resources.side_effect = ApiException(status=404)

        result, count, available = k8s_pod_metrics.get_pod_metrics("dummy/path", "dummy-context")

        self.assertEqual(count, 0)
        self.assertFalse(available)
        self.assertIn("error", result)
        self.assertEqual(result["error"], "Metrics API not available")

    def test_namespace_listing_failure(self):
        self.mock_metrics_api.get_api_resources.return_value = True
        self.mock_v1_instance.list_namespace.side_effect = ApiException(reason="Forbidden")

        result, count, available = k8s_pod_metrics.get_pod_metrics("dummy/path", "dummy-context")

        self.assertEqual(count, 0)
        self.assertFalse(available)
        self.assertIn("error", result)
        self.assertIn("Forbidden", result["error"])

    def test_pod_metrics_failure_for_single_pod(self):
        mock_namespace = MagicMock()
        mock_namespace.metadata.name = "default"
        self.mock_v1_instance.list_namespace.return_value.items = [mock_namespace]

        mock_pod = MagicMock()
        mock_pod.metadata.name = "failing-pod"
        self.mock_v1_instance.list_namespaced_pod.return_value.items = [mock_pod]

        self.mock_metrics_api.get_api_resources.return_value = True
        self.mock_metrics_api.get_namespaced_custom_object.side_effect = ApiException(reason="NotFound")

        result, count, available = k8s_pod_metrics.get_pod_metrics("dummy/path", "dummy-context")

        self.assertEqual(count, 1)
        self.assertTrue(available)
        self.assertEqual(result[0]["name"], "failing-pod")
        self.assertIn("error", result[0])
        self.assertIn("Failed to fetch metrics", result[0]["error"])

    def test_list_pods_failure_in_namespace(self):
        mock_namespace = MagicMock()
        mock_namespace.metadata.name = "broken-ns"
        self.mock_v1_instance.list_namespace.return_value.items = [mock_namespace]

        self.mock_metrics_api.get_api_resources.return_value = True
        self.mock_v1_instance.list_namespaced_pod.side_effect = ApiException(reason="Unauthorized")

        result, count, available = k8s_pod_metrics.get_pod_metrics("dummy/path", "dummy-context")

        self.assertEqual(count, 0)
        self.assertTrue(available)  # metrics API was available
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

# Test cases for limit ranges
class LimitRangeFunctionTests(TestCase):
    def setUp(self):
        self.mock_configure_k8s = patch('dashboard.src.cluster_management.k8s_limit_range.configure_k8s').start()
        self.mock_core_v1 = patch('dashboard.src.cluster_management.k8s_limit_range.client.CoreV1Api').start()
        self.mock_logger = patch('dashboard.src.cluster_management.k8s_limit_range.logger').start()
        self.addCleanup(patch.stopall)

    def test_get_limit_ranges_success(self):
        mock_v1 = self.mock_core_v1.return_value
        mock_ns = MagicMock()
        mock_ns.metadata.name = "default"
        mock_v1.list_namespace.return_value.items = [mock_ns]

        mock_lr = MagicMock()
        mock_lr.metadata.name = "mylr"
        mock_lr.metadata.creation_timestamp.strftime.return_value = "2024-01-01 12:00:00"
        mock_v1.list_namespaced_limit_range.return_value.items = [mock_lr]

        result, count = k8s_limit_range.get_limit_ranges("/dummy/path", "dummy-context")
        self.assertEqual(count, 1)
        self.assertEqual(result[0]["name"], "mylr")
        self.assertEqual(result[0]["namespace"], "default")

    def test_get_limit_ranges_error_logging(self):
        mock_v1 = self.mock_core_v1.return_value
        mock_ns = MagicMock()
        mock_ns.metadata.name = "default"
        mock_v1.list_namespace.return_value.items = [mock_ns]
        mock_v1.list_namespaced_limit_range.side_effect = Exception("API Failure")

        result, count = k8s_limit_range.get_limit_ranges("/dummy/path", "dummy-context")
        self.assertEqual(count, 0)
        self.assertTrue(self.mock_logger.error.called)

    def test_get_limit_range_description_success(self):
        mock_v1 = self.mock_core_v1.return_value
        mock_limit = MagicMock()
        mock_limit.metadata.name = "lr1"
        mock_limit.metadata.namespace = "default"
        limit_obj = MagicMock()
        limit_obj.type = "Container"
        limit_obj.min = {"cpu": "100m"}
        limit_obj.max = {"cpu": "500m"}
        limit_obj.default_request = {"cpu": "200m"}
        limit_obj.default = {"cpu": "300m"}
        limit_obj.max_limit_request_ratio = {"cpu": "2"}
        mock_limit.spec.limits = [limit_obj]

        mock_v1.read_namespaced_limit_range.return_value = mock_limit

        result = k8s_limit_range.get_limit_range_description("/dummy/path", "ctx", "default", "lr1")
        self.assertEqual(result["name"], "lr1")
        self.assertEqual(result["namespace"], "default")
        self.assertEqual(result["limits"][0]["resources"]["cpu"]["min"], "100m")

    def test_get_limit_range_description_failure(self):
        mock_v1 = self.mock_core_v1.return_value
        mock_v1.read_namespaced_limit_range.side_effect = k8s_limit_range.client.exceptions.ApiException(reason="Not Found")

        result = k8s_limit_range.get_limit_range_description("/dummy", "ctx", "ns", "lr1")
        self.assertIn("error", result)

    def test_get_limitrange_events_filters_correctly(self):
        mock_v1 = self.mock_core_v1.return_value
        mock_event = MagicMock()
        mock_event.involved_object.name = "lr1"
        mock_event.involved_object.kind = "LimitRange"
        mock_event.reason = "Created"
        mock_event.message = "LimitRange created"

        mock_v1.list_namespaced_event.return_value.items = [mock_event]

        result = k8s_limit_range.get_limitrange_events("/dummy", "ctx", "default", "lr1")
        self.assertIn("Created: LimitRange created", result)

    def test_get_limitrange_yaml_success(self):
        mock_v1 = self.mock_core_v1.return_value
        mock_lr = MagicMock()
        mock_lr.metadata.annotations = {"foo": "bar"}
        mock_lr.to_dict.return_value = {"metadata": {"annotations": {"foo": "bar"}}, "kind": "LimitRange"}

        mock_v1.read_namespaced_limit_range.return_value = mock_lr

        with patch('dashboard.src.cluster_management.k8s_limit_range.filter_annotations', return_value={"foo": "bar"}) as mock_filter, \
             patch('dashboard.src.cluster_management.k8s_limit_range.yaml.dump', return_value="mock-yaml") as mock_yaml:

            yaml_result = k8s_limit_range.get_limitrange_yaml("/dummy", "ctx", "default", "lr1")
            mock_filter.assert_called_once()
            mock_yaml.assert_called_once()
            self.assertEqual(yaml_result, "mock-yaml")

# Test cases for namepsaces
class NamespaceFunctionsTests(TestCase):
    def setUp(self):
        patcher_core_v1 = patch('dashboard.src.cluster_management.k8s_namespaces.client.CoreV1Api')
        self.mock_core_v1 = patcher_core_v1.start()
        self.addCleanup(patcher_core_v1.stop)

        patcher_configure = patch('dashboard.src.cluster_management.k8s_namespaces.configure_k8s')
        self.mock_configure = patcher_configure.start()
        self.addCleanup(patcher_configure.stop)

        patcher_filter = patch('dashboard.src.cluster_management.k8s_namespaces.filter_annotations', side_effect=lambda x: x)
        self.mock_filter_annotations = patcher_filter.start()
        self.addCleanup(patcher_filter.stop)

        patcher_calc_age = patch('dashboard.src.cluster_management.k8s_namespaces.calculateAge', return_value="5d")
        self.mock_calculate_age = patcher_calc_age.start()
        self.addCleanup(patcher_calc_age.stop)

        self.mock_v1 = self.mock_core_v1.return_value

    def test_get_namespace_success(self):
        ns1 = MagicMock()
        ns1.metadata.name = "ns1"
        ns2 = MagicMock()
        ns2.metadata.name = "ns2"
        self.mock_v1.list_namespace.return_value.items = [ns1, ns2]

        result = k8s_namespaces.get_namespace("/dummy", "ctx")
        self.assertEqual(result, ["ns1", "ns2"])
        self.mock_configure.assert_called_once()

    def test_get_namespace_failure(self):
        self.mock_v1.list_namespace.side_effect = ApiException(reason="Forbidden")

        result = k8s_namespaces.get_namespace("/dummy", "ctx")
        self.assertIn("error", result)
        self.assertIn("Forbidden", result["error"])

    def test_namespaces_data(self):
        mock_ns = MagicMock()
        mock_ns.metadata.name = "ns1"
        mock_ns.status.phase = "Active"
        mock_ns.metadata.creation_timestamp = MagicMock()
        mock_ns.metadata.labels = {"env": "dev"}

        self.mock_v1.list_namespace.return_value.items = [mock_ns]

        result = k8s_namespaces.namespaces_data("/dummy", "ctx")
        self.assertEqual(result[0]["name"], "ns1")
        self.assertEqual(result[0]["status"], "Active")
        self.assertEqual(result[0]["labels"], {"env": "dev"})
        self.assertEqual(result[0]["age"], "5d")

    def test_get_namespace_description(self):
        mock_ns = MagicMock()
        mock_ns.metadata.name = "test-ns"
        mock_ns.metadata.labels = {"team": "dev"}
        mock_ns.metadata.annotations = {"key": "val"}
        mock_ns.status.phase = "Active"

        self.mock_v1.read_namespace.return_value = mock_ns

        result = k8s_namespaces.get_namespace_description("/dummy", "ctx", "test-ns")
        self.assertEqual(result["name"], "test-ns")
        self.assertEqual(result["labels"], [("team", "dev")])
        self.assertEqual(result["annotations"], {"key": "val"})

    def test_get_namespace_yaml(self):
        mock_ns = MagicMock()
        mock_ns.to_dict.return_value = {"metadata": {"name": "test-ns"}}
        mock_ns.metadata.annotations = {"foo": "bar"}

        self.mock_v1.read_namespace.return_value = mock_ns

        yaml_str = k8s_namespaces.get_namespace_yaml("/dummy", "ctx", "test-ns")
        self.assertIn("metadata", yaml.safe_load(yaml_str))
        self.assertIn("name", yaml.safe_load(yaml_str)["metadata"])

# Test cases for Nodes
class NodesTests(TestCase):
    def setUp(self):
        patcher = patch('dashboard.src.cluster_management.k8s_nodes.client.CoreV1Api')
        self.mock_core_v1_api = patcher.start()
        self.addCleanup(patcher.stop)

        self.mock_configure = patch('dashboard.src.cluster_management.k8s_nodes.configure_k8s')
        self.mock_configure.start()
        self.addCleanup(self.mock_configure.stop)

    def test_getnodes(self):
        mock_api = self.mock_core_v1_api.return_value

        mock_node1 = MagicMock()
        mock_node1.metadata.name = "node1"

        mock_node2 = MagicMock()
        mock_node2.metadata.name = "node2"

        mock_api.list_node.return_value.items = [mock_node1, mock_node2]

        result, count = k8s_nodes.getnodes("dummy", "ctx")

        self.assertEqual(count, 2)
        self.assertIn("node1", result)
        self.assertIn("node2", result)

    def test_getNodesStatus(self):
        mock_api = self.mock_core_v1_api.return_value
        node_ready = MagicMock(status=MagicMock(conditions=[MagicMock(type="Ready", status="True")]))
        node_not_ready = MagicMock(status=MagicMock(conditions=[MagicMock(type="Ready", status="False")]))
        mock_api.list_node.return_value.items = [node_ready, node_not_ready]

        ready, not_ready, total = k8s_nodes.getNodesStatus("dummy", "ctx")
        self.assertEqual(ready, 1)
        self.assertEqual(not_ready, 1)
        self.assertEqual(total, 2)

    def test_get_nodes_info(self):
        mock_api = self.mock_core_v1_api.return_value
        mock_node = MagicMock()
        mock_node.metadata.name = "node1"
        mock_node.metadata.creation_timestamp = datetime.now(timezone.utc)
        mock_node.status.conditions = [MagicMock(type="Ready", status="True")]
        mock_node.status.addresses = [
            MagicMock(type="InternalIP", address= os.getenv('INTERNAL_IP')),
            MagicMock(type="ExternalIP", address= os.getenv('EXTERNAL_IP')),
        ]
        mock_node.status.node_info.kubelet_version = "v1.29.0"
        mock_node.status.node_info.os_image = "Ubuntu"
        mock_node.status.node_info.kernel_version = "5.15"
        mock_node.status.node_info.container_runtime_version = "docker://20.10"
        mock_node.metadata.labels = {
            "node-role.kubernetes.io/master": ""
        }
        mock_node.spec.taints = []
        mock_api.list_node.return_value.items = [mock_node]

        result = k8s_nodes.get_nodes_info("dummy", "ctx")
        self.assertEqual(result[0]["name"], "node1")
        self.assertEqual(result[0]["status"], "Ready")

    @patch('dashboard.src.cluster_management.k8s_nodes.client.CoordinationV1Api')
    def test_get_node_description(self, mock_coordination_api):
        mock_v1 = self.mock_core_v1_api.return_value
        mock_node = MagicMock()
        mock_node.metadata.name = "node1"
        mock_node.metadata.labels = {"node-role.kubernetes.io/control-plane": ""}
        mock_node.metadata.annotations = {"test": "value"}
        mock_node.metadata.creation_timestamp = datetime.now(timezone.utc)
        mock_node.spec.taints = []
        mock_node.status.conditions = []
        mock_node.status.addresses = [MagicMock(type="InternalIP", address= os.getenv('INTERNAL_IP'))]
        mock_node.status.capacity = {"cpu": "2", "memory": "4Gi"}
        mock_node.status.allocatable = {"cpu": "1", "memory": "3Gi"}
        mock_node.status.node_info = MagicMock(
            machine_id="mid", system_uuid="uuid", boot_id="bid",
            kernel_version="5.15", os_image="Ubuntu", operating_system="linux",
            architecture="amd64", container_runtime_version="docker://20.10",
            kubelet_version="v1.29", kube_proxy_version="v1.29"
        )
        mock_v1.read_node.return_value = mock_node
        mock_v1.list_pod_for_all_namespaces.return_value.items = []

        mock_lease = MagicMock()
        mock_lease.spec.holder_identity = "node1"
        mock_lease.spec.acquire_time = datetime.now(timezone.utc)
        mock_lease.spec.renew_time = datetime.now(timezone.utc)
        mock_lease.spec.lease_duration_seconds = 40
        mock_coordination_api.return_value.read_namespaced_lease.return_value = mock_lease

        node_info = k8s_nodes.get_node_description("dummy", "ctx", "node1")
        self.assertEqual(node_info["name"], "node1")
        self.assertIn("lease", node_info)
        self.assertEqual(node_info["lease"]["holder_identity"], "node1")

    def test_get_node_yaml(self):
        mock_api = self.mock_core_v1_api.return_value
        mock_node = MagicMock()
        mock_node.to_dict.return_value = {"metadata": {"name": "node1"}}
        mock_api.read_node.return_value = mock_node

        yaml_output = k8s_nodes.get_node_yaml("dummy", "ctx", "node1")
        self.assertIn("name: node1", yaml_output)

    @patch("dashboard.src.cluster_management.k8s_nodes.config.load_incluster_config", side_effect=ConfigException)
    @patch("dashboard.src.cluster_management.k8s_nodes.config.load_kube_config")
    def test_get_node_details(self, mock_kube_config, mock_incluster):
        mock_api = self.mock_core_v1_api.return_value
        mock_node = MagicMock()
        mock_node.metadata.name = "node1"
        mock_node.metadata.labels = {"env": "test"}
        mock_node.metadata.creation_timestamp = datetime.now(timezone.utc)
        mock_node.status.conditions = [MagicMock(type="Ready", status="True")]
        mock_node.status.capacity = {"cpu": "2", "memory": "4Gi"}
        mock_api.list_node.return_value.items = [mock_node]

        result = k8s_nodes.get_node_details()
        self.assertEqual(result[0]["name"], "node1")
        self.assertEqual(result[0]["status"], "Ready")

# test cases for Pod Disruption Budget
class PDBTests(TestCase):
    def setUp(self):
        patcher = patch("dashboard.src.cluster_management.k8s_pdb.client.PolicyV1Api")
        self.mock_policy_api = patcher.start()
        self.addCleanup(patcher.stop)

        patcher_core = patch("dashboard.src.cluster_management.k8s_pdb.client.CoreV1Api")
        self.mock_core_api = patcher_core.start()
        self.addCleanup(patcher_core.stop)

        patcher_config = patch("dashboard.src.cluster_management.k8s_pdb.configure_k8s")
        self.mock_configure = patcher_config.start()
        self.addCleanup(patcher_config.stop)

    def test_get_pdb(self):
        mock_pdb = MagicMock()
        mock_pdb.metadata.namespace = "default"
        mock_pdb.metadata.name = "test-pdb"
        mock_pdb.spec.min_available = "1"
        mock_pdb.spec.max_unavailable = None
        mock_pdb.status.disruptions_allowed = 2
        mock_pdb.metadata.creation_timestamp = datetime.now(timezone.utc)

        self.mock_policy_api.return_value.list_pod_disruption_budget_for_all_namespaces.return_value.items = [mock_pdb]

        result, count = k8s_pdb.get_pdb("dummy", "ctx")

        self.assertEqual(count, 1)
        self.assertEqual(result[0]["name"], "test-pdb")
        self.assertEqual(result[0]["min"], "1")
        self.assertEqual(result[0]["max"], "N/A")
        self.assertEqual(result[0]["disruptions"], 2)

    def test_get_pdb_description_success(self):
        mock_pdb = MagicMock()
        mock_pdb.metadata.name = "test-pdb"
        mock_pdb.metadata.namespace = "default"
        mock_pdb.spec.min_available = "1"
        mock_pdb.spec.max_unavailable = "0"
        mock_pdb.spec.selector.match_labels = {"app": "nginx"}
        mock_pdb.status.disruptions_allowed = 1
        mock_pdb.status.current_healthy = 3
        mock_pdb.status.desired_healthy = 2
        mock_pdb.status.expected_pods = 3

        self.mock_policy_api.return_value.read_namespaced_pod_disruption_budget.return_value = mock_pdb

        result = k8s_pdb.get_pdb_description("dummy", "ctx", "default", "test-pdb")

        self.assertEqual(result["name"], "test-pdb")
        self.assertEqual(result["selector"], {"app": "nginx"})
        self.assertEqual(result["status"]["Allowed Disruptions"], 1)

    def test_get_pdb_events(self):
        mock_event1 = MagicMock()
        mock_event1.involved_object.name = "test-pdb"
        mock_event1.involved_object.kind = "PodDisruptionBudget"
        mock_event1.reason = "Eviction"
        mock_event1.message = "Pod eviction allowed"

        mock_event2 = MagicMock()
        mock_event2.involved_object.name = "other-pdb"
        mock_event2.involved_object.kind = "PodDisruptionBudget"
        mock_event2.reason = "Eviction"
        mock_event2.message = "Ignored"

        self.mock_core_api.return_value.list_namespaced_event.return_value.items = [mock_event1, mock_event2]

        result = k8s_pdb.get_pdb_events("dummy", "ctx", "default", "test-pdb")

        self.assertIn("Eviction: Pod eviction allowed", result)
        self.assertNotIn("other-pdb", result)

    def test_get_pdb_yaml(self):
        mock_pdb = MagicMock()
        mock_pdb.to_dict.return_value = {"kind": "PodDisruptionBudget", "metadata": {"name": "test-pdb"}}
        mock_pdb.metadata.annotations = {"kubectl.kubernetes.io/last-applied-configuration": "something"}

        self.mock_policy_api.return_value.read_namespaced_pod_disruption_budget.return_value = mock_pdb

        yaml_str = k8s_pdb.get_pdb_yaml("dummy", "ctx", "default", "test-pdb")

        self.assertIn("PodDisruptionBudget", yaml_str)
        self.assertIn("name: test-pdb", yaml_str)

# Test cases for resource quotas
class ResourceQuotaTests(TestCase):
    def setUp(self):
        patcher_core = patch("dashboard.src.cluster_management.k8s_resource_quota.client.CoreV1Api")
        self.mock_core_api = patcher_core.start()
        self.addCleanup(patcher_core.stop)

        patcher_cfg = patch("dashboard.src.cluster_management.k8s_resource_quota.configure_k8s")
        self.mock_configure = patcher_cfg.start()
        self.addCleanup(patcher_cfg.stop)

    def test_get_resource_quotas_all(self):
        mock_quota = MagicMock()
        mock_quota.metadata.namespace = "default"
        mock_quota.metadata.name = "rq1"
        mock_quota.metadata.creation_timestamp = datetime.now(timezone.utc)
        mock_quota.status.hard = {"pods": "10", "requests.cpu": "1"}
        mock_quota.status.used = {"pods": "2", "requests.cpu": "0.5"}

        self.mock_core_api.return_value.list_resource_quota_for_all_namespaces.return_value.items = [mock_quota]

        result, count = k8s_resource_quota.get_resource_quotas("dummy", "ctx", namespace="all")

        self.assertEqual(count, 1)
        self.assertEqual(result[0]["name"], "rq1")
        self.assertIn("requests.cpu: 0.5/1", result[0]["requests"])
        self.assertIn("pods: 2/10", result[0]["pods"])

    def test_get_resourcequota_description(self):
        rq = MagicMock()
        rq.metadata.name = "rq1"
        rq.metadata.namespace = "default"
        rq.spec.hard = {"cpu": "2"}
        rq.status.used = {"cpu": "1"}

        self.mock_core_api.return_value.list_namespaced_resource_quota.return_value.items = [rq]

        result = k8s_resource_quota.get_resourcequota_description("dummy", "ctx", "default", "rq1")

        self.assertEqual(result["name"], "rq1")
        self.assertEqual(result["resources"][0]["resource"], "cpu")
        self.assertEqual(result["resources"][0]["used"], "1")

    def test_get_resourcequota_description_not_found(self):
        self.mock_core_api.return_value.list_namespaced_resource_quota.return_value.items = []

        result = k8s_resource_quota.get_resourcequota_description("dummy", "ctx", "default", "missing-rq")
        self.assertIn("error", result)

    def test_get_resourcequota_events(self):
        event = MagicMock()
        event.involved_object.name = "rq1"
        event.involved_object.kind = "ResourceQuota"
        event.reason = "Exceeded"
        event.message = "CPU usage exceeded"

        self.mock_core_api.return_value.list_namespaced_event.return_value.items = [event]

        result = k8s_resource_quota.get_resourcequota_events("dummy", "ctx", "default", "rq1")
        self.assertIn("Exceeded: CPU usage exceeded", result)

    def test_get_resourcequota_yaml(self):
        rq = MagicMock()
        rq.to_dict.return_value = {"metadata": {"name": "rq1"}, "spec": {}}
        rq.metadata.annotations = {"kubectl.kubernetes.io/last-applied-configuration": "something"}

        self.mock_core_api.return_value.read_namespaced_resource_quota.return_value = rq

        result = k8s_resource_quota.get_resourcequota_yaml("dummy", "ctx", "default", "rq1")
        self.assertIn("name: rq1", result)

# Test cases for config maps
class ConfigMapTests(TestCase):
    def setUp(self):
        patcher_api = patch("dashboard.src.config_secrets.k8s_configmaps.client.CoreV1Api")
        self.mock_core_api = patcher_api.start()
        self.addCleanup(patcher_api.stop)

        patcher_cfg = patch("dashboard.src.config_secrets.k8s_configmaps.configure_k8s")
        self.mock_configure = patcher_cfg.start()
        self.addCleanup(patcher_cfg.stop)

    def test_get_configmaps(self):
        now = datetime.now(timezone.utc)
        cm1 = MagicMock()
        cm1.metadata.name = "cm1"
        cm1.metadata.namespace = "default"
        cm1.metadata.creation_timestamp = now
        cm1.data = {"key1": "val1", "key2": "val2"}

        cm2 = MagicMock()
        cm2.metadata.name = "cm2"
        cm2.metadata.namespace = "kube-system"
        cm2.metadata.creation_timestamp = now
        cm2.data = {}

        self.mock_core_api.return_value.list_config_map_for_all_namespaces.return_value.items = [cm1, cm2]

        result, count = k8s_configmaps.get_configmaps("dummy", "ctx")
        self.assertEqual(count, 2)
        self.assertEqual(result[0]["name"], "cm1")
        self.assertEqual(result[0]["data"], 2)
        self.assertEqual(result[1]["name"], "cm2")
        self.assertEqual(result[1]["data"], 0)

    def test_get_configmap_description_success(self):
        cm = MagicMock()
        cm.metadata.name = "test-cm"
        cm.metadata.namespace = "default"
        cm.data = {"env": "production"}

        self.mock_core_api.return_value.list_namespaced_config_map.return_value.items = [cm]

        result = k8s_configmaps.get_configmap_description("dummy", "ctx", "default", "test-cm")
        self.assertEqual(result["name"], "test-cm")
        self.assertEqual(result["data"]["env"], "production")

    def test_get_configmap_description_not_found(self):
        self.mock_core_api.return_value.list_namespaced_config_map.return_value.items = []

        result = k8s_configmaps.get_configmap_description("dummy", "ctx", "default", "missing-cm")
        self.assertIn("error", result)

    def test_get_configmap_events(self):
        event = MagicMock()
        event.involved_object.name = "my-cm"
        event.involved_object.kind = "ConfigMap"
        event.reason = "Created"
        event.message = "ConfigMap created successfully"

        self.mock_core_api.return_value.list_namespaced_event.return_value.items = [event]

        result = k8s_configmaps.get_configmap_events("dummy", "ctx", "default", "my-cm")
        self.assertIn("Created: ConfigMap created successfully", result)

    def test_get_configmap_yaml(self):
        cm = MagicMock()
        cm.to_dict.return_value = {"metadata": {"name": "cm1"}, "data": {"env": "prod"}}
        cm.metadata.annotations = {"kubectl.kubernetes.io/last-applied-configuration": "something"}

        self.mock_core_api.return_value.read_namespaced_config_map.return_value = cm

        result = k8s_configmaps.get_configmap_yaml("dummy", "ctx", "default", "cm1")
        self.assertIn("name: cm1", result)

# test cases for secrets
class SecretsTests(TestCase):
    def setUp(self):
        patcher_api = patch("dashboard.src.config_secrets.k8s_secrets.client.CoreV1Api")
        self.mock_core_api = patcher_api.start()
        self.addCleanup(patcher_api.stop)

        patcher_cfg = patch("dashboard.src.config_secrets.k8s_secrets.configure_k8s")
        self.mock_configure = patcher_cfg.start()
        self.addCleanup(patcher_cfg.stop)

    def test_list_secrets(self):
        mock_secret1 = MagicMock()
        mock_secret1.metadata.name = "secret1"
        mock_secret1.metadata.namespace = "default"
        mock_secret1.type = "Opaque"
        mock_secret1.metadata.creation_timestamp = datetime.now(timezone.utc)
        mock_secret1.data = {"key1": "dmFsdWUx"}  # "value1"

        mock_secret2 = MagicMock()
        mock_secret2.metadata.name = "secret2"
        mock_secret2.metadata.namespace = "kube-system"
        mock_secret2.type = "kubernetes.io/service-account-token"
        mock_secret2.metadata.creation_timestamp = datetime.now(timezone.utc)
        mock_secret2.data = {}

        self.mock_core_api.return_value.list_secret_for_all_namespaces.return_value.items = [mock_secret1, mock_secret2]

        result, count = k8s_secrets.list_secrets("dummy", "ctx")

        self.assertEqual(count, 2)
        self.assertEqual(result[0]["name"], "secret1")
        self.assertEqual(result[0]["data"], 1)
        self.assertEqual(result[1]["name"], "secret2")
        self.assertEqual(result[1]["data"], 0)

    def test_get_secret_description_success(self):
        encoded_value = base64.b64encode(b"my-secret-data").decode()

        mock_secret = MagicMock()
        mock_secret.metadata.name = "my-secret"
        mock_secret.metadata.namespace = "default"
        mock_secret.type = "Opaque"
        mock_secret.data = {"api-key": encoded_value}

        self.mock_core_api.return_value.list_namespaced_secret.return_value.items = [mock_secret]

        result = k8s_secrets.get_secret_description("dummy", "ctx", "default", "my-secret")
        self.assertEqual(result["name"], "my-secret")
        self.assertEqual(result["data"]["api-key"], "14 bytes")

    def test_get_secret_description_not_found(self):
        self.mock_core_api.return_value.list_namespaced_secret.return_value.items = []

        result = k8s_secrets.get_secret_description("dummy", "ctx", "default", "missing-secret")
        self.assertIn("error", result)

    def test_get_secret_events(self):
        mock_event = MagicMock()
        mock_event.involved_object.name = "secret1"
        mock_event.involved_object.kind = "Secret"
        mock_event.reason = "Created"
        mock_event.message = "Secret created successfully"

        self.mock_core_api.return_value.list_namespaced_event.return_value.items = [mock_event]

        result = k8s_secrets.get_secret_events("dummy", "ctx", "default", "secret1")
        self.assertIn("Created: Secret created successfully", result)

    def test_get_secret_yaml(self):
        mock_secret = MagicMock()
        mock_secret.to_dict.return_value = {"metadata": {"name": "secret1"}, "type": "Opaque"}
        mock_secret.metadata.annotations = {"kubectl.kubernetes.io/last-applied-configuration": "something"}

        self.mock_core_api.return_value.read_namespaced_secret.return_value = mock_secret

        result = k8s_secrets.get_secret_yaml("dummy", "ctx", "default", "secret1")
        self.assertIn("name: secret1", result)
        self.assertIn("Opaque", result)

# Test cases for events
class EventsTests(TestCase):
    def setUp(self):
        patcher_cfg = patch("dashboard.src.events.k8s_events.configure_k8s")
        self.mock_configure = patcher_cfg.start()
        self.addCleanup(patcher_cfg.stop)

        patcher_api = patch("dashboard.src.events.k8s_events.client.CoreV1Api")
        self.mock_core_api = patcher_api.start()
        self.addCleanup(patcher_api.stop)

    def mock_event(self, name="mypod", kind="Pod", namespace="default", count=3,
                   last_timestamp=None, component="kubelet", host="node1", message="Started container", etype="Normal"):
        event = MagicMock()
        event.metadata.namespace = namespace
        event.message = message
        event.involved_object.kind = kind
        event.involved_object.name = name
        event.source.component = component
        event.source.host = host
        event.count = count
        event.last_timestamp = last_timestamp or (datetime.now(tzutc()) - timedelta(minutes=10))
        event.type = etype
        event.reporting_component = "reporter"
        event.reporting_instance = "instance1"
        return event

    def test_get_events_all_namespace_with_limit(self):
        mock_event_obj = self.mock_event()
        self.mock_core_api.return_value.list_event_for_all_namespaces.return_value.items = [mock_event_obj]

        events = k8s_events.get_events("dummy", "ctx", limit=True, namespace="all")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["namespace"], "default")
        self.assertIn("10m", events[0]["last_seen"])

    def test_get_events_specific_namespace_without_limit(self):
        mock_event_obj = self.mock_event(kind="Deployment", name="nginx-deploy", namespace="dev")
        self.mock_core_api.return_value.list_namespaced_event.return_value.items = [mock_event_obj]

        events = k8s_events.get_events("dummy", "ctx", limit=False, namespace="dev")
        self.assertEqual(events[0]["object"], "Deployment/nginx-deploy")
        self.assertEqual(events[0]["source"], "kubelet, node1")

    def test_get_events_no_source_component(self):
        event = self.mock_event()
        event.source.component = None
        self.mock_core_api.return_value.list_event_for_all_namespaces.return_value.items = [event]

        events = k8s_events.get_events("dummy", "ctx", limit=True)
        self.assertEqual(events[0]["source"], "reporter, instance1")

    def test_get_events_exception(self):
        self.mock_core_api.return_value.list_event_for_all_namespaces.side_effect = Exception("Boom")
        events = k8s_events.get_events("dummy", "ctx", limit=True)
        self.assertEqual(events, [])

# Test cases for Ingress
class IngressTests(TestCase):
    def setUp(self):
        patcher_k8s = patch("dashboard.src.networking.k8s_ingress.configure_k8s")
        self.mock_configure = patcher_k8s.start()
        self.addCleanup(patcher_k8s.stop)

        patcher_api = patch("dashboard.src.networking.k8s_ingress.client.NetworkingV1Api")
        self.mock_networking_api = patcher_api.start()
        self.addCleanup(patcher_api.stop)

        patcher_core = patch("dashboard.src.networking.k8s_ingress.client.CoreV1Api")
        self.mock_core_api = patcher_core.start()
        self.addCleanup(patcher_core.stop)

    def test_get_ingress(self):
        mock_ingress = MagicMock()
        mock_ingress.metadata.namespace = "default"
        mock_ingress.metadata.name = "ing1"
        mock_ingress.spec.ingress_class_name = "nginx"
        rule = MagicMock()
        rule.host = "example.com"
        mock_ingress.spec.rules = [rule]

        self.mock_networking_api.return_value.list_ingress_for_all_namespaces.return_value.items = [mock_ingress]

        result, count = k8s_ingress.get_ingress("dummy", "ctx")
        self.assertEqual(count, 1)
        self.assertEqual(result[0]["name"], "ing1")
        self.assertIn("example.com", result[0]["hosts"])

    def test_get_ingress_description_success(self):
        rule = MagicMock()
        rule.host = "myhost"
        path = MagicMock()
        path.path = "/app"
        path.backend.service.name = "myservice"
        path.backend.service.port.name = "http"
        rule.http.paths = [path]
        ingress = MagicMock()
        ingress.metadata.name = "ingress1"
        ingress.metadata.namespace = "default"
        ingress.metadata.labels = {"app": "web"}
        ingress.metadata.annotations = {"foo": "bar"}
        ingress.spec.rules = [rule]
        ingress.spec.ingress_class_name = "nginx"
        ingress.status.load_balancer.ingress = [MagicMock(ip="10.1.1.1")]

        self.mock_networking_api.return_value.read_namespaced_ingress.return_value = ingress
        self.mock_core_api.return_value.read_namespaced_service.return_value = MagicMock()

        result = k8s_ingress.get_ingress_description("p", "ctx", "default", "ingress1")
        self.assertEqual(result["name"], "ingress1")
        self.assertIn("myhost", [r["host"] for r in result["rules"]])
        self.assertEqual(result["address"], "10.1.1.1")

    def test_get_ingress_events(self):
        event1 = MagicMock()
        event1.involved_object.name = "ingress1"
        event1.involved_object.kind = "Ingress"
        event1.reason = "Created"
        event1.message = "Ingress created"
        self.mock_core_api.return_value.list_namespaced_event.return_value.items = [event1]

        result = k8s_ingress.get_ingress_events("p", "ctx", "default", "ingress1")
        self.assertIn("Created: Ingress created", result)

    def test_get_ingress_yaml(self):
        ingress = MagicMock()
        ingress.to_dict.return_value = {"metadata": {"name": "ing1"}}
        ingress.metadata.annotations = {"foo": "bar"}
        self.mock_networking_api.return_value.read_namespaced_ingress.return_value = ingress

        yaml_output = k8s_ingress.get_ingress_yaml("p", "ctx", "default", "ing1")
        self.assertIn("metadata:", yaml_output)

    def test_get_ingress_details(self):
        patcher_cfg = patch("dashboard.src.networking.k8s_ingress.config.load_incluster_config")
        patcher_fallback = patch("dashboard.src.networking.k8s_ingress.config.load_kube_config")
        patcher_cfg.start()
        patcher_fallback.start()
        self.addCleanup(patcher_cfg.stop)
        self.addCleanup(patcher_fallback.stop)

        rule = MagicMock()
        rule.host = "host.local"
        path = MagicMock()
        path.path = "/x"
        path.backend.service.name = "svc"
        rule.http.paths = [path]
        ingress = MagicMock()
        ingress.metadata.name = "ingx"
        ingress.metadata.namespace = "dev"
        ingress.metadata.creation_timestamp = datetime.now(timezone.utc) - timedelta(days=1)
        ingress.spec.rules = [rule]
        ingress.spec.tls = ["tls"]
        self.mock_networking_api.return_value.list_ingress_for_all_namespaces.return_value.items = [ingress]

        result = k8s_ingress.get_ingress_details()
        self.assertEqual(result[0]["name"], "ingx")
        self.assertEqual(result[0]["tls"], "Yes")

# Test cases for Network Policy
class NetworkPolicyTests(TestCase):
    def setUp(self):
        patcher_cfg = patch("dashboard.src.networking.k8s_np.configure_k8s")
        self.mock_configure = patcher_cfg.start()
        self.addCleanup(patcher_cfg.stop)

        patcher_net = patch("dashboard.src.networking.k8s_np.client.NetworkingV1Api")
        self.mock_net_api = patcher_net.start()
        self.addCleanup(patcher_net.stop)

        patcher_core = patch("dashboard.src.networking.k8s_np.client.CoreV1Api")
        self.mock_core_api = patcher_core.start()
        self.addCleanup(patcher_core.stop)

    def test_get_np(self):
        mock_np = MagicMock()
        mock_np.metadata.namespace = "default"
        mock_np.metadata.name = "allow-app"
        mock_np.metadata.creation_timestamp = datetime.now(timezone.utc) - timedelta(days=1)
        mock_np.spec.pod_selector.match_labels = {"app": "nginx"}

        self.mock_net_api.return_value.list_network_policy_for_all_namespaces.return_value.items = [mock_np]

        result, count = k8s_np.get_np("dummy", "ctx")
        self.assertEqual(count, 1)
        self.assertEqual(result[0]["name"], "allow-app")
        self.assertIn("app=nginx", result[0]["pod_selector"])

    def test_get_np_description(self):
        np = MagicMock()
        np.metadata.name = "allow-db"
        np.metadata.namespace = "default"
        np.metadata.creation_timestamp = datetime.now(timezone.utc)
        np.metadata.labels = {"env": "prod"}
        np.metadata.annotations = {"foo": "bar"}
        np.spec.pod_selector.match_labels = {"tier": "db"}
        np.spec.ingress = ["ingress-rule"]
        np.spec.egress = ["egress-rule"]
        np.spec.policy_types = ["Ingress", "Egress"]

        self.mock_net_api.return_value.read_namespaced_network_policy.return_value = np

        result = k8s_np.get_np_description("dummy", "ctx", "default", "allow-db")
        self.assertEqual(result["name"], "allow-db")
        self.assertEqual(result["spec"]["policy_types"], ["Ingress", "Egress"])
        self.assertEqual(result["spec"]["pod_selector"]["tier"], "db")

    def test_get_np_events(self):
        event = MagicMock()
        event.involved_object.name = "np-1"
        event.involved_object.kind = "NetworkPolicy"
        event.reason = "Applied"
        event.message = "NP applied successfully"

        self.mock_core_api.return_value.list_namespaced_event.return_value.items = [event]

        result = k8s_np.get_np_events("dummy", "ctx", "default", "np-1")
        self.assertIn("Applied: NP applied successfully", result)

    def test_get_np_yaml(self):
        np = MagicMock()
        np.to_dict.return_value = {"metadata": {"name": "np-1"}}
        np.metadata.annotations = {"foo": "bar"}

        self.mock_net_api.return_value.read_namespaced_network_policy.return_value = np

        result = k8s_np.get_np_yaml("dummy", "ctx", "default", "np-1")
        self.assertIn("metadata:", result)
        self.assertIn("name: np-1", result)

class PersistentVolumesTests(TestCase):
    def setUp(self):
        patcher_cfg = patch("dashboard.src.persistent_volume.k8s_pv.configure_k8s")
        self.mock_configure_k8s = patcher_cfg.start()
        self.addCleanup(patcher_cfg.stop)

        patcher_core = patch("dashboard.src.persistent_volume.k8s_pv.client.CoreV1Api")
        self.mock_core_api = patcher_core.start()
        self.addCleanup(patcher_core.stop)

    def test_list_persistent_volumes(self):
        mock_pv = MagicMock()
        mock_pv.metadata.name = "pv1"
        mock_pv.metadata.creation_timestamp = datetime.now(timezone.utc) - timedelta(days=2)
        mock_pv.spec.capacity = {"storage": "10Gi"}
        mock_pv.spec.access_modes = ["ReadWriteOnce", "ReadOnlyMany"]
        mock_pv.spec.persistent_volume_reclaim_policy = "Retain"
        mock_pv.spec.claim_ref.namespace = "default"
        mock_pv.spec.claim_ref.name = "my-claim"
        mock_pv.spec.storage_class_name = "standard"
        mock_pv.spec.volume_mode = "Filesystem"
        mock_pv.status.phase = "Bound"

        self.mock_core_api.return_value.list_persistent_volume.return_value.items = [mock_pv]

        result, count = k8s_pv.list_persistent_volumes("dummy", "ctx")
        self.assertEqual(count, 1)
        self.assertEqual(result[0]["name"], "pv1")
        self.assertIn("RWO", result[0]["access_modes"])
        self.assertIn("ROX", result[0]["access_modes"])
        self.assertEqual(result[0]["claim"], "default/my-claim")

    def test_get_pv_description(self):
        pv = MagicMock()
        pv.metadata.name = "pv1"
        pv.metadata.labels = {"app": "test"}
        pv.metadata.annotations = {"foo": "bar"}
        pv.metadata.finalizers = ["kubernetes.io/pv-protection"]
        pv.spec.storage_class_name = "standard"
        pv.status.phase = "Available"
        pv.status.message = "Provisioned"
        pv.spec.claim_ref.namespace = "default"
        pv.spec.claim_ref.name = "claim1"
        pv.spec.persistent_volume_reclaim_policy = "Delete"
        pv.spec.access_modes = ["ReadWriteMany"]
        pv.spec.volume_mode = "Filesystem"
        pv.spec.capacity = {"storage": "20Gi"}
        pv.spec.node_affinity = {"required": "some-affinity"}
        pv.spec.host_path = MagicMock(path="/data", type="Directory")

        self.mock_core_api.return_value.read_persistent_volume.return_value = pv

        result = k8s_pv.get_pv_description("dummy", "ctx", "pv1")
        self.assertEqual(result["Name"], "pv1")
        self.assertEqual(result["StorageClass"], "standard")
        self.assertEqual(result["Claim"], "default/claim1")
        self.assertEqual(result["Source"]["Type"], "HostPath (bare host directory volume)")
        self.assertEqual(result["Source"]["Path"], "/data")

    def test_get_pv_yaml(self):
        pv = MagicMock()
        pv.to_dict.return_value = {"metadata": {"name": "pv1"}}
        pv.metadata.annotations = {"foo": "bar"}

        self.mock_core_api.return_value.read_persistent_volume.return_value = pv

        result = k8s_pv.get_pv_yaml("dummy", "ctx", "pv1")
        self.assertIn("metadata:", result)
        self.assertIn("name: pv1", result)

class PVCTests(TestCase):
    def setUp(self):
        patcher_cfg = patch("dashboard.src.persistent_volume.k8s_pvc.configure_k8s")
        self.mock_configure_k8s = patcher_cfg.start()
        self.addCleanup(patcher_cfg.stop)

        patcher_core = patch("dashboard.src.persistent_volume.k8s_pvc.client.CoreV1Api")
        self.mock_core_api = patcher_core.start()
        self.addCleanup(patcher_core.stop)

    def test_list_pvc(self):
        mock_pvc = MagicMock()
        mock_pvc.metadata.name = "pvc1"
        mock_pvc.metadata.namespace = "default"
        mock_pvc.metadata.creation_timestamp = datetime.now(timezone.utc) - timedelta(days=3)
        mock_pvc.status.phase = "Bound"
        mock_pvc.status.capacity = {"storage": "5Gi"}
        mock_pvc.spec.volume_name = "pv1"
        mock_pvc.spec.access_modes = ["ReadWriteOnce"]
        mock_pvc.spec.storage_class_name = "standard"
        mock_pvc.spec.volume_mode = "Filesystem"

        mock_pod = MagicMock()
        mock_pod.metadata.name = "mypod"
        mock_vol = MagicMock()
        mock_vol.persistent_volume_claim.claim_name = "pvc1"
        mock_pod.spec.volumes = [mock_vol]

        core_v1 = self.mock_core_api.return_value
        core_v1.list_persistent_volume_claim_for_all_namespaces.return_value.items = [mock_pvc]
        core_v1.list_namespaced_pod.return_value.items = [mock_pod]

        result, count = k8s_pvc.list_pvc("dummy", "ctx")
        self.assertEqual(count, 1)
        self.assertEqual(result[0]["name"], "pvc1")
        self.assertIn("mypod", result[0]["used_by"])

    def test_get_pvc_description(self):
        pvc = MagicMock()
        pvc.metadata.name = "pvc1"
        pvc.metadata.namespace = "default"
        pvc.metadata.labels = {"app": "test"}
        pvc.metadata.annotations = {"foo": "bar"}
        pvc.metadata.finalizers = ["kubernetes.io/pvc-protection"]
        pvc.spec.storage_class_name = "standard"
        pvc.status.phase = "Pending"
        pvc.spec.volume_name = "pv1"
        pvc.spec.resources.requests = {"storage": "1Gi"}
        pvc.spec.access_modes = ["ReadWriteOnce"]
        pvc.spec.volume_mode = "Filesystem"

        pod = MagicMock()
        pod.metadata.name = "pod-using-pvc"
        vol = MagicMock()
        vol.persistent_volume_claim.claim_name = "pvc1"
        pod.spec.volumes = [vol]

        core_v1 = self.mock_core_api.return_value
        core_v1.read_namespaced_persistent_volume_claim.return_value = pvc
        core_v1.list_namespaced_pod.return_value.items = [pod]

        result = k8s_pvc.get_pvc_description("dummy", "ctx", "default", "pvc1")
        self.assertEqual(result["Name"], "pvc1")
        self.assertEqual(result["Used_By"], "pod-using-pvc")

    def test_get_pvc_yaml(self):
        pvc = MagicMock()
        pvc.to_dict.return_value = {"metadata": {"name": "pvc1"}}
        pvc.metadata.annotations = {"foo": "bar"}

        self.mock_core_api.return_value.read_namespaced_persistent_volume_claim.return_value = pvc

        result = k8s_pvc.get_pvc_yaml("dummy", "ctx", "default", "pvc1")
        self.assertIn("metadata:", result)
        self.assertIn("name: pvc1", result)

class StorageClassTests(TestCase):
    def setUp(self):
        patcher_cfg = patch("dashboard.src.persistent_volume.k8s_storage_class.configure_k8s")
        self.mock_configure_k8s = patcher_cfg.start()
        self.addCleanup(patcher_cfg.stop)

        patcher_api = patch("dashboard.src.persistent_volume.k8s_storage_class.client.StorageV1Api")
        self.mock_storage_api = patcher_api.start()
        self.addCleanup(patcher_api.stop)

    def test_list_storage_classes(self):
        mock_sc = MagicMock()
        mock_sc.metadata.name = "standard"
        mock_sc.metadata.creation_timestamp = datetime.now(timezone.utc) - timedelta(days=2)
        mock_sc.metadata.annotations = {"storageclass.kubernetes.io/is-default-class": "true"}
        mock_sc.provisioner = "kubernetes.io/aws-ebs"
        mock_sc.reclaim_policy = "Delete"
        mock_sc.volume_binding_mode = "Immediate"
        mock_sc.allow_volume_expansion = True

        api = self.mock_storage_api.return_value
        api.list_storage_class.return_value.items = [mock_sc]

        result, count = k8s_storage_class.list_storage_classes("dummy", "ctx")
        self.assertEqual(count, 1)
        self.assertEqual(result[0]["name"], "standard")
        self.assertEqual(result[0]["isDefault"], "Yes")

    def test_get_storage_class_description(self):
        mock_sc = MagicMock()
        mock_sc.metadata.name = "gp2"
        mock_sc.metadata.annotations = {"storageclass.kubernetes.io/is-default-class": "false"}
        mock_sc.provisioner = "ebs.csi.aws.com"
        mock_sc.parameters = {"type": "gp2"}
        mock_sc.allow_volume_expansion = False
        mock_sc.mount_options = ["noatime"]
        mock_sc.reclaim_policy = "Delete"
        mock_sc.volume_binding_mode = "WaitForFirstConsumer"

        api = self.mock_storage_api.return_value
        api.read_storage_class.return_value = mock_sc

        result = k8s_storage_class.get_storage_class_description("dummy", "ctx", "gp2")
        self.assertEqual(result["name"], "gp2")
        self.assertEqual(result["is_default_class"], "No")
        self.assertEqual(result["provisioner"], "ebs.csi.aws.com")

    def test_get_sc_yaml(self):
        mock_sc = MagicMock()
        mock_sc.to_dict.return_value = {"metadata": {"name": "sc1"}}
        mock_sc.metadata.annotations = {"foo": "bar"}

        api = self.mock_storage_api.return_value
        api.read_storage_class.return_value = mock_sc

        result = k8s_storage_class.get_sc_yaml("dummy", "ctx", "sc1")
        self.assertIn("metadata:", result)
        self.assertIn("name: sc1", result)

class ClusterRoleBindingsTests(TestCase):
    def setUp(self):
        patcher_cfg = patch("dashboard.src.rbac.k8s_cluster_role_bindings.configure_k8s")
        self.mock_configure_k8s = patcher_cfg.start()
        self.addCleanup(patcher_cfg.stop)

        patcher_api = patch("dashboard.src.rbac.k8s_cluster_role_bindings.client.RbacAuthorizationV1Api")
        self.mock_rbac_api = patcher_api.start()
        self.addCleanup(patcher_api.stop)

    def test_get_cluster_role_bindings(self):
        mock_binding = MagicMock()
        mock_binding.metadata.name = "admin-binding"
        mock_binding.metadata.creation_timestamp = datetime.now(timezone.utc) - timedelta(days=1)
        mock_binding.role_ref.name = "cluster-admin"

        # Define user subject
        user_subject = MagicMock()
        user_subject.kind = "User"
        user_subject.name = "alice"

        # Define group subject
        group_subject = MagicMock()
        group_subject.kind = "Group"
        group_subject.name = "devs"

        # Define service account subject
        sa_subject = MagicMock()
        sa_subject.kind = "ServiceAccount"
        sa_subject.name = "default"
        sa_subject.namespace = "kube-system"

        mock_binding.subjects = [user_subject, group_subject, sa_subject]

        api = self.mock_rbac_api.return_value
        api.list_cluster_role_binding.return_value.items = [mock_binding]

        result, count = k8s_cluster_role_bindings.get_cluster_role_bindings("dummy", "ctx")
        self.assertEqual(count, 1)
        self.assertEqual(result[0]["name"], "admin-binding")
        self.assertIn("alice", result[0]["users"])
        self.assertIn("devs", result[0]["groups"])
        self.assertIn("kube-system/default", result[0]["service_accounts"])

    def test_get_cluster_role_binding_description(self):
        mock_binding = MagicMock()
        mock_binding.metadata.name = "admin-binding"
        mock_binding.metadata.labels = {"env": "prod"}
        mock_binding.metadata.annotations = {"some/annotation": "value"}
        mock_binding.role_ref.kind = "ClusterRole"
        mock_binding.role_ref.name = "admin"
        mock_binding.subjects = [
            MagicMock(kind="User", name="bob", namespace=None),
            MagicMock(kind="ServiceAccount", name="default", namespace="default")
        ]

        api = self.mock_rbac_api.return_value
        api.read_cluster_role_binding.return_value = mock_binding

        result = k8s_cluster_role_bindings.get_cluster_role_binding_description("dummy", "ctx", "admin-binding")
        self.assertEqual(result["name"], "admin-binding")
        self.assertEqual(result["role"]["name"], "admin")
        self.assertEqual(len(result["subjects"]), 2)

    def test_get_cluster_role_binding_yaml(self):
        mock_binding = MagicMock()
        mock_binding.to_dict.return_value = {"metadata": {"name": "binding"}}
        mock_binding.metadata.annotations = {"foo": "bar"}

        api = self.mock_rbac_api.return_value
        api.read_cluster_role_binding.return_value = mock_binding

        yaml_data = k8s_cluster_role_bindings.get_cluster_role_binding_yaml("dummy", "ctx", "binding")
        self.assertIn("metadata:", yaml_data)
        self.assertIn("name: binding", yaml_data)

# test cases for cluster roles
class ClusterRoleTests(TestCase):
    def setUp(self):
        patcher_cfg = patch("dashboard.src.rbac.k8s_cluster_roles.configure_k8s")
        self.mock_configure_k8s = patcher_cfg.start()
        self.addCleanup(patcher_cfg.stop)

        patcher_api = patch("dashboard.src.rbac.k8s_cluster_roles.client.RbacAuthorizationV1Api")
        self.mock_rbac_api = patcher_api.start()
        self.addCleanup(patcher_api.stop)

        patcher_core = patch("dashboard.src.rbac.k8s_cluster_roles.client.CoreV1Api")
        self.mock_core_api = patcher_core.start()
        self.addCleanup(patcher_core.stop)

    def test_get_cluster_role(self):
        mock_role = MagicMock()
        mock_role.metadata.name = "test-cluster-role"
        mock_role.metadata.creation_timestamp = None

        api = self.mock_rbac_api.return_value
        api.list_cluster_role.return_value.items = [mock_role]

        result, count = k8s_cluster_roles.get_cluster_role("dummy", "ctx")
        self.assertEqual(count, 1)
        self.assertEqual(result[0]["name"], "test-cluster-role")
        self.assertEqual(result[0]["created_at"], "Unknown")

    def test_get_cluster_role_description(self):
        mock_rule = MagicMock()
        mock_rule.resources = ["pods"]
        mock_rule.resource_names = ["*"]
        mock_rule.non_resource_ur_ls = ["/metrics"]
        mock_rule.verbs = ["get", "list"]

        mock_meta = MagicMock()
        mock_meta.name = "test-role"
        mock_meta.labels = {"env": "dev"}
        mock_meta.annotations = {"some": "annotation"}

        mock_role = MagicMock()
        mock_role.metadata = mock_meta
        mock_role.rules = [mock_rule]

        api = self.mock_rbac_api.return_value
        api.read_cluster_role.return_value = mock_role

        with patch("dashboard.src.rbac.k8s_cluster_roles.filter_annotations", return_value={}):
            result = k8s_cluster_roles.get_cluster_role_description("dummy", "ctx", "test-role")

        self.assertEqual(result["name"], "test-role")
        self.assertEqual(result["labels"], {"env": "dev"})
        self.assertEqual(len(result["policy_rule"]), 1)

    def test_get_cluster_role_description_error(self):
        api = self.mock_rbac_api.return_value
        api.read_cluster_role.side_effect = k8s_cluster_roles.client.exceptions.ApiException(reason="NotFound")

        result = k8s_cluster_roles.get_cluster_role_description("dummy", "ctx", "invalid-role")
        self.assertIn("error", result)
        self.assertIn("NotFound", result["error"])

    def test_get_cluster_role_events(self):
        mock_event = MagicMock()
        mock_event.involved_object.name = "test-role"
        mock_event.involved_object.kind = "ClusterRole"
        mock_event.reason = "Created"
        mock_event.message = "ClusterRole created"

        core_api = self.mock_core_api.return_value
        core_api.list_event_for_all_namespaces.return_value.items = [mock_event]

        result = k8s_cluster_roles.get_cluster_role_events("dummy", "ctx", "test-role")
        self.assertIn("Created: ClusterRole created", result)

    def test_get_cluster_role_yaml(self):
        mock_meta = MagicMock()
        mock_meta.annotations = {"foo": "bar"}

        mock_role = MagicMock()
        mock_role.metadata = mock_meta
        mock_role.to_dict.return_value = {"metadata": {"name": "test-cluster-role"}}

        api = self.mock_rbac_api.return_value
        api.read_cluster_role.return_value = mock_role

        with patch("dashboard.src.rbac.k8s_cluster_roles.filter_annotations", return_value={}):
            yaml_str = k8s_cluster_roles.get_cluster_role_yaml("dummy", "ctx", "test-cluster-role")

        self.assertIn("metadata:", yaml_str)
        self.assertIn("name: test-cluster-role", yaml_str)

    def test_get_cluster_role_yaml_error(self):
        api = self.mock_rbac_api.return_value
        api.read_cluster_role.side_effect = k8s_cluster_roles.client.exceptions.ApiException(reason="Forbidden")

        result = k8s_cluster_roles.get_cluster_role_yaml("dummy", "ctx", "invalid")
        self.assertIn("error", result)
        self.assertIn("Forbidden", result["error"])

class RoleTests(TestCase):
    def setUp(self):
        patcher_cfg = patch("dashboard.src.rbac.k8s_role.configure_k8s")
        self.mock_configure_k8s = patcher_cfg.start()
        self.addCleanup(patcher_cfg.stop)

        patcher_rbac = patch("dashboard.src.rbac.k8s_role.client.RbacAuthorizationV1Api")
        self.mock_rbac_api = patcher_rbac.start()
        self.addCleanup(patcher_rbac.stop)

        patcher_core = patch("dashboard.src.rbac.k8s_role.client.CoreV1Api")
        self.mock_core_api = patcher_core.start()
        self.addCleanup(patcher_core.stop)

    def test_list_roles(self):
        mock_namespace = MagicMock()
        mock_namespace.metadata.name = "dev"

        mock_role = MagicMock()
        mock_role.metadata.name = "reader"
        mock_role.metadata.creation_timestamp = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        self.mock_core_api.return_value.list_namespace.return_value.items = [mock_namespace]
        self.mock_rbac_api.return_value.list_namespaced_role.return_value.items = [mock_role]

        result, count = k8s_role.list_roles("dummy", "ctx")
        self.assertEqual(count, 1)
        self.assertEqual(result[0]["namespace"], "dev")
        self.assertEqual(result[0]["name"], "reader")
        self.assertIn("2024-01-01", result[0]["created_at"])

    def test_get_role_description_success(self):
        mock_rule = MagicMock()
        mock_rule.resources = ["pods"]
        mock_rule.resource_names = ["*"]
        mock_rule.non_resource_ur_ls = ["/metrics"]
        mock_rule.verbs = ["get", "list"]

        mock_meta = MagicMock()
        mock_meta.name = "reader"
        mock_meta.labels = {"team": "dev"}
        mock_meta.annotations = {"key": "value"}

        mock_role = MagicMock()
        mock_role.metadata = mock_meta
        mock_role.rules = [mock_rule]

        self.mock_rbac_api.return_value.read_namespaced_role.return_value = mock_role

        with patch("dashboard.src.rbac.k8s_role.filter_annotations", return_value={}):
            result = k8s_role.get_role_description("dummy", "ctx", "dev", "reader")

        self.assertEqual(result["name"], "reader")
        self.assertEqual(result["labels"], {"team": "dev"})
        self.assertEqual(len(result["policy_rule"]), 1)

    def test_get_role_description_error(self):
        self.mock_rbac_api.return_value.read_namespaced_role.side_effect = k8s_role.client.exceptions.ApiException(reason="NotFound")

        result = k8s_role.get_role_description("dummy", "ctx", "dev", "nonexistent")
        self.assertIn("error", result)
        self.assertIn("NotFound", result["error"])

    def test_get_role_events(self):
        mock_event = MagicMock()
        mock_event.involved_object.name = "reader"
        mock_event.involved_object.kind = "Role"
        mock_event.reason = "Modified"
        mock_event.message = "Role was updated"

        self.mock_core_api.return_value.list_namespaced_event.return_value.items = [mock_event]

        result = k8s_role.get_role_events("dummy", "ctx", "dev", "reader")
        self.assertIn("Modified: Role was updated", result)

    def test_get_role_yaml_success(self):
        mock_meta = MagicMock()
        mock_meta.annotations = {"key": "value"}

        mock_role = MagicMock()
        mock_role.metadata = mock_meta
        mock_role.to_dict.return_value = {"metadata": {"name": "reader"}}

        self.mock_rbac_api.return_value.read_namespaced_role.return_value = mock_role

        with patch("dashboard.src.rbac.k8s_role.filter_annotations", return_value={}):
            yaml_output = k8s_role.get_role_yaml("dummy", "ctx", "dev", "reader")

        self.assertIn("metadata:", yaml_output)
        self.assertIn("name: reader", yaml_output)

    def test_get_role_yaml_error(self):
        self.mock_rbac_api.return_value.read_namespaced_role.side_effect = k8s_role.client.exceptions.ApiException(reason="Forbidden")

        result = k8s_role.get_role_yaml("dummy", "ctx", "dev", "bad-role")
        self.assertIn("error", result)
        self.assertIn("Forbidden", result["error"])

class RoleBindingTests(TestCase):
    def setUp(self):
        patcher_cfg = patch("dashboard.src.rbac.k8s_rolebindings.configure_k8s")
        self.mock_configure_k8s = patcher_cfg.start()
        self.addCleanup(patcher_cfg.stop)

        patcher_rbac = patch("dashboard.src.rbac.k8s_rolebindings.client.RbacAuthorizationV1Api")
        self.mock_rbac_api = patcher_rbac.start()
        self.addCleanup(patcher_rbac.stop)

        patcher_core = patch("dashboard.src.rbac.k8s_rolebindings.client.CoreV1Api")
        self.mock_core_api = patcher_core.start()
        self.addCleanup(patcher_core.stop)

        patcher_age = patch("dashboard.src.rbac.k8s_rolebindings.calculateAge", return_value="1d")
        self.mock_calculate_age = patcher_age.start()
        self.addCleanup(patcher_age.stop)

    def test_list_rolebindings(self):
        mock_subject_user = MagicMock()
        mock_subject_user.kind = "User"
        mock_subject_user.name = "alice"

        mock_subject_group = MagicMock()
        mock_subject_group.kind = "Group"
        mock_subject_group.name = "devs"

        mock_subject_sa = MagicMock()
        mock_subject_sa.kind = "ServiceAccount"
        mock_subject_sa.name = "default"

        mock_binding = MagicMock()
        mock_binding.metadata.name = "rb-test"
        mock_binding.metadata.namespace = "dev"
        mock_binding.metadata.creation_timestamp = datetime.now(timezone.utc) - timedelta(days=1)
        mock_binding.role_ref.name = "read-only"
        mock_binding.subjects = [mock_subject_user, mock_subject_group, mock_subject_sa]

        self.mock_rbac_api.return_value.list_role_binding_for_all_namespaces.return_value.items = [mock_binding]

        result, count = k8s_rolebindings.list_rolebindings("dummy", "ctx")

        self.assertEqual(count, 1)
        self.assertEqual(result[0]["name"], "rb-test")
        self.assertIn("alice", result[0]["users"])
        self.assertIn("devs", result[0]["groups"])
        self.assertIn("default", result[0]["service_accounts"])
        self.assertEqual(result[0]["age"], "1d")

    def test_get_role_binding_description_success(self):
        mock_subject = MagicMock()
        mock_subject.kind = "User"
        mock_subject.name = "bob"
        mock_subject.namespace = None

        mock_meta = MagicMock()
        mock_meta.name = "rb"
        mock_meta.labels = {"env": "test"}
        mock_meta.annotations = {"key": "val"}

        mock_binding = MagicMock()
        mock_binding.metadata = mock_meta
        mock_binding.role_ref.kind = "Role"
        mock_binding.role_ref.name = "reader"
        mock_binding.subjects = [mock_subject]

        self.mock_rbac_api.return_value.read_namespaced_role_binding.return_value = mock_binding

        with patch("dashboard.src.rbac.k8s_rolebindings.filter_annotations", return_value={}):
            result = k8s_rolebindings.get_role_binding_description("dummy", "ctx", "dev", "rb")

        self.assertEqual(result["name"], "rb")
        self.assertEqual(result["role"]["name"], "reader")
        self.assertEqual(len(result["subjects"]), 1)

    def test_get_role_binding_description_error(self):
        self.mock_rbac_api.return_value.read_namespaced_role_binding.side_effect = k8s_rolebindings.client.exceptions.ApiException(reason="NotFound")

        result = k8s_rolebindings.get_role_binding_description("dummy", "ctx", "dev", "invalid")
        self.assertIn("error", result)
        self.assertIn("NotFound", result["error"])

    def test_get_role_binding_events(self):
        mock_event = MagicMock()
        mock_event.involved_object.name = "rb"
        mock_event.involved_object.kind = "RoleBinding"
        mock_event.reason = "Updated"
        mock_event.message = "RoleBinding was updated"

        self.mock_core_api.return_value.list_namespaced_event.return_value.items = [mock_event]

        result = k8s_rolebindings.get_role_binding_events("dummy", "ctx", "dev", "rb")
        self.assertIn("Updated: RoleBinding was updated", result)

    def test_get_role_binding_yaml_success(self):
        mock_meta = MagicMock()
        mock_meta.annotations = {"foo": "bar"}

        mock_binding = MagicMock()
        mock_binding.metadata = mock_meta
        mock_binding.to_dict.return_value = {"metadata": {"name": "rb"}}

        self.mock_rbac_api.return_value.read_namespaced_role_binding.return_value = mock_binding

        with patch("dashboard.src.rbac.k8s_rolebindings.filter_annotations", return_value={}):
            yaml_str = k8s_rolebindings.get_role_binding_yaml("dummy", "ctx", "dev", "rb")

        self.assertIn("metadata:", yaml_str)
        self.assertIn("name: rb", yaml_str)

    def test_get_role_binding_yaml_error(self):
        self.mock_rbac_api.return_value.read_namespaced_role_binding.side_effect = k8s_rolebindings.client.exceptions.ApiException(reason="Forbidden")

        result = k8s_rolebindings.get_role_binding_yaml("dummy", "ctx", "dev", "bad-rb")
        self.assertIn("error", result)
        self.assertIn("Forbidden", result["error"])

class ServiceAccountTests(TestCase):
    def setUp(self):
        patcher_cfg = patch("dashboard.src.rbac.k8s_service_accounts.configure_k8s")
        self.mock_configure_k8s = patcher_cfg.start()
        self.addCleanup(patcher_cfg.stop)

        patcher_core = patch("dashboard.src.rbac.k8s_service_accounts.client.CoreV1Api")
        self.mock_core_api = patcher_core.start()
        self.addCleanup(patcher_core.stop)

        patcher_age = patch("dashboard.src.rbac.k8s_service_accounts.calculateAge", return_value="2d")
        self.mock_calculate_age = patcher_age.start()
        self.addCleanup(patcher_age.stop)

    def test_get_service_accounts(self):
        mock_namespace = MagicMock()
        mock_namespace.metadata.name = "dev"

        mock_sa = MagicMock()
        mock_sa.metadata.name = "default"
        mock_sa.metadata.creation_timestamp = datetime.now(timezone.utc) - timedelta(days=2)
        mock_sa.secrets = [MagicMock(name="s1"), MagicMock(name="s2")]

        self.mock_core_api.return_value.list_namespace.return_value.items = [mock_namespace]
        self.mock_core_api.return_value.list_namespaced_service_account.return_value.items = [mock_sa]

        result, count = k8s_service_accounts.get_service_accounts("dummy", "ctx")

        self.assertEqual(count, 1)
        self.assertEqual(result[0]["namespace"], "dev")
        self.assertEqual(result[0]["name"], "default")
        self.assertEqual(result[0]["secrets"], 2)
        self.assertEqual(result[0]["age"], "2d")

    def test_get_sa_description_success(self):
        mock_meta = MagicMock()
        mock_meta.name = "default"
        mock_meta.namespace = "dev"
        mock_meta.labels = {"app": "test"}
        mock_meta.annotations = {"foo": "bar"}

        mock_sa = MagicMock()
        mock_sa.metadata = mock_meta
        mock_sa.api_version = "v1"
        mock_sa.kind = "ServiceAccount"
        mock_sa.secrets = [MagicMock(name="s1")]
        mock_sa.image_pull_secrets = [MagicMock(name="img-secret")]

        self.mock_core_api.return_value.read_namespaced_service_account.return_value = mock_sa

        with patch("dashboard.src.rbac.k8s_service_accounts.filter_annotations", return_value={}):
            result = k8s_service_accounts.get_sa_description("dummy", "ctx", "dev", "default")

        self.assertEqual(result["name"], "default")
        self.assertEqual(result["namespace"], "dev")
        self.assertEqual(result["labels"], {"app": "test"})
        self.assertIsInstance(result["mountable_secrets"], list)
        self.assertIsInstance(result["image_pull_secrets"], list)

    def test_get_sa_description_error(self):
        self.mock_core_api.return_value.read_namespaced_service_account.side_effect = k8s_service_accounts.client.exceptions.ApiException(reason="NotFound")

        result = k8s_service_accounts.get_sa_description("dummy", "ctx", "dev", "bad-sa")
        self.assertIn("error", result)
        self.assertIn("NotFound", result["error"])

    def test_get_sa_events(self):
        mock_event = MagicMock()
        mock_event.involved_object.name = "default"
        mock_event.involved_object.kind = "ServiceAccount"
        mock_event.reason = "Created"
        mock_event.message = "SA created"

        self.mock_core_api.return_value.list_namespaced_event.return_value.items = [mock_event]

        result = k8s_service_accounts.get_sa_events("dummy", "ctx", "dev", "default")
        self.assertIn("Created: SA created", result)

    def test_get_sa_yaml_success(self):
        mock_meta = MagicMock()
        mock_meta.annotations = {"foo": "bar"}

        mock_sa = MagicMock()
        mock_sa.metadata = mock_meta
        mock_sa.to_dict.return_value = {"metadata": {"name": "default"}}

        self.mock_core_api.return_value.read_namespaced_service_account.return_value = mock_sa

        with patch("dashboard.src.rbac.k8s_service_accounts.filter_annotations", return_value={}):
            yaml_str = k8s_service_accounts.get_sa_yaml("dummy", "ctx", "dev", "default")

        self.assertIn("metadata:", yaml_str)
        self.assertIn("name: default", yaml_str)

    def test_get_sa_yaml_error(self):
        self.mock_core_api.return_value.read_namespaced_service_account.side_effect = k8s_service_accounts.client.exceptions.ApiException(reason="Forbidden")

        result = k8s_service_accounts.get_sa_yaml("dummy", "ctx", "dev", "restricted-sa")
        self.assertIn("error", result)
        self.assertIn("Forbidden", result["error"])

class EndpointTests(TestCase):
    def setUp(self):
        patcher_cfg = patch("dashboard.src.services.k8s_endpoints.configure_k8s")
        self.mock_configure_k8s = patcher_cfg.start()
        self.addCleanup(patcher_cfg.stop)

        patcher_core = patch("dashboard.src.services.k8s_endpoints.client.CoreV1Api")
        self.mock_core_api = patcher_core.start()
        self.addCleanup(patcher_core.stop)

        patcher_age = patch("dashboard.src.services.k8s_endpoints.calculateAge", return_value="3d")
        self.mock_calculate_age = patcher_age.start()
        self.addCleanup(patcher_age.stop)

    def test_get_endpoints(self):
        mock_namespace = MagicMock()
        mock_namespace.metadata.name = "default"

        mock_ep = MagicMock()
        mock_ep.metadata.name = "my-service"
        mock_ep.metadata.creation_timestamp = datetime.now(timezone.utc) - timedelta(days=3)

        mock_addr = MagicMock()
        mock_addr.ip = "10.0.0.1"

        mock_port = MagicMock()
        mock_port.port = 80

        mock_subset = MagicMock()
        mock_subset.addresses = [mock_addr]
        mock_subset.ports = [mock_port]

        mock_ep.subsets = [mock_subset]

        self.mock_core_api.return_value.list_namespace.return_value.items = [mock_namespace]
        self.mock_core_api.return_value.list_namespaced_endpoints.return_value.items = [mock_ep]

        result = k8s_endpoints.get_endpoints("dummy", "ctx")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["namespace"], "default")
        self.assertEqual(result[0]["name"], "my-service")
        self.assertIn("10.0.0.1:80", result[0]["endpoints"])
        self.assertEqual(result[0]["age"], "3d")

    def test_get_endpoint_description_success(self):
        mock_meta = MagicMock()
        mock_meta.name = "my-ep"
        mock_meta.namespace = "default"
        mock_meta.labels = {"app": "web"}
        mock_meta.annotations = {"foo": "bar"}

        mock_addr = MagicMock()
        mock_addr.ip = "10.0.0.2"
        mock_addr.hostname = "host"
        mock_addr.target_ref = {"kind": "Pod", "name": "pod-1"}

        mock_port = MagicMock()
        mock_port.name = "http"
        mock_port.port = 8080
        mock_port.protocol = "TCP"

        mock_subset = MagicMock()
        mock_subset.addresses = [mock_addr]
        mock_subset.not_ready_addresses = []
        mock_subset.ports = [mock_port]

        mock_ep = MagicMock()
        mock_ep.metadata = mock_meta
        mock_ep.subsets = [mock_subset]

        self.mock_core_api.return_value.read_namespaced_endpoints.return_value = mock_ep

        with patch("dashboard.src.services.k8s_endpoints.filter_annotations", return_value={}):
            result = k8s_endpoints.get_endpoint_description("dummy", "ctx", "default", "my-ep")

        self.assertEqual(result["name"], "my-ep")
        self.assertEqual(result["namespace"], "default")
        self.assertIn("addresses", result["subsets"][0])
        self.assertIn("ports", result["subsets"][0])

    def test_get_endpoint_description_error(self):
        self.mock_core_api.return_value.read_namespaced_endpoints.side_effect = k8s_endpoints.client.exceptions.ApiException(reason="NotFound")
        result = k8s_endpoints.get_endpoint_description("dummy", "ctx", "default", "bad-ep")
        self.assertIn("error", result)
        self.assertIn("NotFound", result["error"])

    def test_get_endpoint_events(self):
        mock_event = MagicMock()
        mock_event.involved_object.name = "my-ep"
        mock_event.involved_object.kind = "Endpoints"
        mock_event.reason = "Updated"
        mock_event.message = "Endpoint updated"

        self.mock_core_api.return_value.list_namespaced_event.return_value.items = [mock_event]

        result = k8s_endpoints.get_endpoint_events("dummy", "ctx", "default", "my-ep")
        self.assertIn("Updated: Endpoint updated", result)

    def test_get_endpoint_yaml_success(self):
        mock_meta = MagicMock()
        mock_meta.annotations = {"foo": "bar"}

        mock_ep = MagicMock()
        mock_ep.metadata = mock_meta
        mock_ep.to_dict.return_value = {"metadata": {"name": "ep"}}

        self.mock_core_api.return_value.read_namespaced_endpoints.return_value = mock_ep

        with patch("dashboard.src.services.k8s_endpoints.filter_annotations", return_value={}):
            yaml_data = k8s_endpoints.get_endpoint_yaml("dummy", "ctx", "default", "ep")

        self.assertIn("metadata:", yaml_data)
        self.assertIn("name: ep", yaml_data)

class ServiceTests(TestCase):
    def setUp(self):
        patcher_cfg = patch("dashboard.src.services.k8s_services.configure_k8s")
        self.mock_configure_k8s = patcher_cfg.start()
        self.addCleanup(patcher_cfg.stop)

        patcher_core = patch("dashboard.src.services.k8s_services.client.CoreV1Api")
        self.mock_core_api = patcher_core.start()
        self.addCleanup(patcher_core.stop)

        patcher_age = patch("dashboard.src.services.k8s_services.calculateAge", return_value="3d")
        self.mock_calculate_age = patcher_age.start()
        self.addCleanup(patcher_age.stop)

    def test_list_kubernetes_services(self):
        mock_service = MagicMock()
        mock_service.metadata.name = "web"
        mock_service.metadata.namespace = "default"
        mock_service.metadata.creation_timestamp = datetime.now(timezone.utc) - timedelta(days=3)
        mock_service.spec.type = "ClusterIP"
        mock_service.spec.cluster_ip = "10.0.0.1"
        mock_service.spec.ports = [MagicMock(port=80, protocol="TCP")]
        mock_service.spec.selector = {"app": "web"}
        mock_service.status.load_balancer.ingress = None

        self.mock_core_api.return_value.list_service_for_all_namespaces.return_value.items = [mock_service]

        result = k8s_services.list_kubernetes_services("dummy", "ctx")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "web")
        self.assertEqual(result[0]["cluster_ip"], "10.0.0.1")
        self.assertEqual(result[0]["external_ip"], "-")
        self.assertEqual(result[0]["age"], "3d")

    def test_get_service_description(self):
        mock_service = MagicMock()
        mock_service.metadata.name = "svc"
        mock_service.metadata.namespace = "default"
        mock_service.metadata.labels = {"env": "dev"}
        mock_service.metadata.annotations = {"foo": "bar"}
        mock_service.spec.type = "ClusterIP"
        mock_service.spec.cluster_ip = "10.0.0.1"
        mock_service.spec.ports = [MagicMock(
            name="http", port=80, protocol="TCP", target_port=8080, node_port=30080
        )]
        mock_service.spec.selector = {"app": "web"}
        mock_service.spec.ip_family_policy = "SingleStack"
        mock_service.spec.ip_families = ["IPv4"]
        mock_service.spec.session_affinity = "None"
        mock_service.spec.internal_traffic_policy = "Cluster"

        mock_service.status.load_balancer.ingress = []

        mock_endpoints = MagicMock()
        mock_endpoints.subsets = []

        self.mock_core_api.return_value.read_namespaced_service.return_value = mock_service
        self.mock_core_api.return_value.read_namespaced_endpoints.return_value = mock_endpoints

        with patch("dashboard.src.services.k8s_services.filter_annotations", return_value={}):
            result = k8s_services.get_service_description("dummy", "ctx", "default", "svc")

        self.assertEqual(result["name"], "svc")
        self.assertEqual(result["namespace"], "default")
        self.assertEqual(result["load_balancer_ip"], "N/A")
        self.assertEqual(result["external_ips"], [])
        self.assertEqual(result["ip_family_policy"], "SingleStack")
        self.assertIn("ports", result)

    def test_get_service_description_no_endpoints(self):
        mock_service = MagicMock()
        mock_service.metadata.name = "svc"
        mock_service.metadata.namespace = "default"
        mock_service.metadata.annotations = {}
        mock_service.spec.ports = []
        mock_service.status.load_balancer.ingress = None

        self.mock_core_api.return_value.read_namespaced_service.return_value = mock_service
        self.mock_core_api.return_value.read_namespaced_endpoints.side_effect = k8s_services.client.exceptions.ApiException()

        with patch("dashboard.src.services.k8s_services.filter_annotations", return_value={}):
            result = k8s_services.get_service_description("dummy", "ctx", "default", "svc")

        self.assertEqual(result["endpoints"], None)
        self.assertEqual(result["load_balancer_ip"], "N/A")

    def test_get_service_events(self):
        mock_event = MagicMock()
        mock_event.involved_object.name = "svc"
        mock_event.involved_object.kind = "Service"
        mock_event.reason = "Updated"
        mock_event.message = "Service modified"

        self.mock_core_api.return_value.list_namespaced_event.return_value.items = [mock_event]

        result = k8s_services.get_service_events("dummy", "ctx", "default", "svc")
        self.assertIn("Updated: Service modified", result)

    def test_get_service_yaml(self):
        mock_service = MagicMock()
        mock_service.metadata.annotations = {"foo": "bar"}
        mock_service.to_dict.return_value = {"metadata": {"name": "svc"}}

        self.mock_core_api.return_value.read_namespaced_service.return_value = mock_service

        with patch("dashboard.src.services.k8s_services.filter_annotations", return_value={}):
            result = k8s_services.get_service_yaml("dummy", "ctx", "default", "svc")

        self.assertIn("metadata:", result)
        self.assertIn("name: svc", result)