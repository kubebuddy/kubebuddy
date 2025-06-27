from django.test import TestCase, RequestFactory
from unittest.mock import patch, MagicMock
from main.models import KubeConfig, Cluster 
from dashboard.views import get_utils_data, pods, pod_info, replicasets, rs_info, deployments, deploy_info, statefulsets, sts_info, daemonset, daemonset_info, jobs, jobs_info, cronjob_info, cronjobs, namespace, ns_info, nodes, node_info

class GetUtilsDataFunctionTests(TestCase):
    def setUp(self):
        self.kube_config_entry = KubeConfig.objects.create(
            path='/test/kube/config/path',
            path_type='file'
        )
        self.cluster = Cluster.objects.create(
            cluster_name='my-test-cluster',
            context_name='my-test-context',
            kube_config=self.kube_config_entry,
            id=101
        )
        self.another_kube_config_entry = KubeConfig.objects.create(
            path='/another/kube/config/path',
            path_type='file'
        )
        self.another_cluster = Cluster.objects.create(
            cluster_name='another-cluster',
            context_name='another-context',
            kube_config=self.another_kube_config_entry,
            id=102
        )


        self.patcher_get_cluster_names = patch('dashboard.views.clusters_DB.get_cluster_names')
        self.patcher_get_namespace = patch('dashboard.views.k8s_namespaces.get_namespace')

        self.mock_get_cluster_names = self.patcher_get_cluster_names.start()
        self.mock_get_namespace = self.patcher_get_namespace.start()

    def tearDown(self):
        self.patcher_get_cluster_names.stop()
        self.patcher_get_namespace.stop()

    def test_get_utils_data_successful_retrieval(self):
        mock_registered_cluster_names = ['cluster-A', 'cluster-B', 'my-test-cluster', 'another-cluster']
        mock_namespaces_data = ['default', 'kube-system', 'my-app-namespace']

        self.mock_get_cluster_names.return_value = mock_registered_cluster_names
        self.mock_get_namespace.return_value = mock_namespaces_data

        mock_request = MagicMock()
        mock_request.GET = {'cluster_id': str(self.cluster.id)}  

        cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(mock_request)

        self.assertEqual(str(cluster_id), str(self.cluster.id)) 
        self.assertEqual(current_cluster, self.cluster)
        self.assertEqual(path, self.kube_config_entry.path)
        self.assertEqual(registered_clusters, mock_registered_cluster_names)
        self.assertEqual(namespaces, mock_namespaces_data)
        self.assertEqual(context_name, self.cluster.context_name)

        self.mock_get_cluster_names.assert_called_once()
        self.mock_get_namespace.assert_called_once_with(self.kube_config_entry.path, self.cluster.context_name)

    def test_get_utils_data_cluster_does_not_exist(self):
        mock_request = MagicMock()
        mock_request.GET = {'cluster_id': self.cluster.id + 999} 

        with self.assertRaises(Cluster.DoesNotExist):
            get_utils_data(mock_request)

        self.mock_get_cluster_names.assert_not_called()
        self.mock_get_namespace.assert_not_called()

    def test_get_utils_data_missing_cluster_id_in_request(self):
        mock_request = MagicMock()
        mock_request.GET = {} 

        with self.assertRaises(Cluster.DoesNotExist):
            get_utils_data(mock_request)

        self.mock_get_cluster_names.assert_not_called()
        self.mock_get_namespace.assert_not_called()

    def test_get_utils_data_namespace_empty(self):
        mock_registered_cluster_names = ['my-test-cluster']
        self.mock_get_cluster_names.return_value = mock_registered_cluster_names
        self.mock_get_namespace.return_value = [] 
        mock_request = MagicMock()
        mock_request.GET = {'cluster_id': self.cluster.id}

        cluster_id, _, _, _, namespaces, _ = get_utils_data(mock_request)

        self.assertEqual(str(cluster_id), str(self.cluster.id))
        self.assertEqual(namespaces, [])  
        self.mock_get_namespace.assert_called_once_with(self.kube_config_entry.path, self.cluster.context_name)

    def test_get_utils_data_get_cluster_names_empty(self):
        self.mock_get_cluster_names.return_value = [] 
        mock_namespaces_data = ['default']
        self.mock_get_namespace.return_value = mock_namespaces_data

        mock_request = MagicMock()
        mock_request.GET = {'cluster_id': self.cluster.id}

        cluster_id, _, _, registered_clusters, _, _ = get_utils_data(mock_request)

        self.assertEqual(str(cluster_id), str(self.cluster.id))
        self.assertEqual(registered_clusters, []) 
        self.mock_get_cluster_names.assert_called_once()
        self.mock_get_namespace.assert_called_once_with(self.kube_config_entry.path, self.cluster.context_name)

    def test_get_utils_data_kube_config_path_is_none(self):
        kube_config_none_path = KubeConfig.objects.create(
            path='',
            path_type='file'
        )
        cluster_none_path = Cluster.objects.create(
            cluster_name='cluster-none-path',
            context_name='context-none-path',
            kube_config=kube_config_none_path,
            id=103
        )

        mock_registered_cluster_names = ['cluster-none-path']
        self.mock_get_cluster_names.return_value = mock_registered_cluster_names
        self.mock_get_namespace.return_value = [] 

        mock_request = MagicMock()
        mock_request.GET = {'cluster_id': cluster_none_path.id}

        _, _, path, _, _, _ = get_utils_data(mock_request)

        self.assertEqual(path, '') 
        self.mock_get_namespace.assert_called_once_with('', cluster_none_path.context_name) 

    def test_get_utils_data_get_namespace_raises_exception(self):
        mock_registered_cluster_names = ['my-test-cluster']
        self.mock_get_cluster_names.return_value = mock_registered_cluster_names
        self.mock_get_namespace.side_effect = Exception("K8s API error: Could not get namespaces")

        mock_request = MagicMock()
        mock_request.GET = {'cluster_id': self.cluster.id}

        with self.assertRaises(Exception) as context:
            get_utils_data(mock_request)

        self.assertIn("K8s API error: Could not get namespaces", str(context.exception))
        self.mock_get_namespace.assert_called_once_with(self.kube_config_entry.path, self.cluster.context_name)

    def test_get_utils_data_get_cluster_names_raises_exception(self):
        self.mock_get_cluster_names.side_effect = Exception("DB error: Could not get cluster names")
        mock_namespaces_data = ['default']
        self.mock_get_namespace.return_value = mock_namespaces_data

        mock_request = MagicMock()
        mock_request.GET = {'cluster_id': self.cluster.id}

        with self.assertRaises(Exception) as context:
            get_utils_data(mock_request)

        self.assertIn("DB error: Could not get cluster names", str(context.exception))
        self.mock_get_cluster_names.assert_called_once()
        self.mock_get_namespace.assert_not_called()

    def test_get_utils_data_with_string_cluster_id(self):
        mock_registered_cluster_names = ['my-test-cluster']
        mock_namespaces_data = ['default']
        self.mock_get_cluster_names.return_value = mock_registered_cluster_names
        self.mock_get_namespace.return_value = mock_namespaces_data

        mock_request = MagicMock()
        mock_request.GET = {'cluster_id': str(self.cluster.id)} 

        cluster_id, current_cluster, path, registered_clusters, namespaces, context_name = get_utils_data(mock_request)

        self.assertEqual(cluster_id, str(self.cluster.id))
        self.assertEqual(current_cluster, self.cluster)
        self.mock_get_cluster_names.assert_called_once()
        self.mock_get_namespace.assert_called_once_with(self.kube_config_entry.path, self.cluster.context_name)

def server_down_handler(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

def login_required(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

class PodsViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        self.kube_config_entry = KubeConfig.objects.create(
            path='/test/kube/config/path',
            path_type='file'
        )
        self.cluster = Cluster.objects.create(
            cluster_name='my-test-cluster',
            context_name='my-test-context',
            kube_config=self.kube_config_entry,
            id=101
        )

        self.patcher_k8s_pods = patch('dashboard.views.k8s_pods')
        self.mock_k8s_pods = self.patcher_k8s_pods.start()

        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()

        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_pods.stop()
        self.patcher_get_utils_data.stop()
        self.patcher_render.stop()

    def _setup_successful_mocks(self):
        mock_current_cluster = MagicMock()
        mock_current_cluster.context_name = self.cluster.context_name
        self.mock_get_utils_data.return_value = (
            str(self.cluster.id),  
            mock_current_cluster,  
            self.kube_config_entry.path,  
            ['cluster-A', 'my-test-cluster'], 
            ['default', 'kube-system'], 
            self.cluster.context_name 
        )

        self.mock_k8s_pods.getpods.return_value = (
            [
                {"name": "pod-1", "status": "Running", "namespace": "default"},
                {"name": "pod-2", "status": "Pending", "namespace": "kube-system"}
            ],
            2  
        )
        self.mock_k8s_pods.get_pod_info.return_value = [
            {"name": "pod-1", "containers": 1, "images": ["nginx"], "restarts": 0},
            {"name": "pod-2", "containers": 1, "images": ["busybox"], "restarts": 1},
        ]
        self.mock_k8s_pods.getPodsStatus.return_value = {
            "Running": 1, "Pending": 1, "Failed": 0, "Succeeded": 0, "Unknown": 0
        }

    def test_pods_view_successful_rendering(self):
        self._setup_successful_mocks()
        request = self.factory.get(f'/dashboard/pods/{self.cluster.id}/')

        response = pods(request, self.cluster.id)

        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/workloads/pods.html')

        context = args[2] 
        self.assertIn("pods", context)
        self.assertIn("pc", context)
        self.assertIn("cluster_id", context)
        self.assertIn("pod_info_list", context)
        self.assertIn("status_count", context)
        self.assertIn("registered_clusters", context)
        self.assertIn("namespaces", context)
        self.assertIn("current_cluster", context)

        self.assertEqual(context["pods"], self.mock_k8s_pods.getpods.return_value[0])
        self.assertEqual(context["pc"], self.mock_k8s_pods.getpods.return_value[1])
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["pod_info_list"], self.mock_k8s_pods.get_pod_info.return_value)
        self.assertEqual(context["status_count"], self.mock_k8s_pods.getPodsStatus.return_value)
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])

        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_pods.getpods.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )
        self.mock_k8s_pods.get_pod_info.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )
        self.mock_k8s_pods.getPodsStatus.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_pods_view_no_pods_found(self):
        self._setup_successful_mocks() 
        self.mock_k8s_pods.getpods.return_value = ([], 0)
        self.mock_k8s_pods.get_pod_info.return_value = []
        self.mock_k8s_pods.getPodsStatus.return_value = {"Running": 0, "Pending": 0, "Failed": 0, "Succeeded": 0, "Unknown": 0}

        request = self.factory.get(f'/dashboard/pods/{self.cluster.id}/')
        response = pods(request, self.cluster.id)

        self.mock_render.assert_called_once()
        context = self.mock_render.call_args[0][2]
        self.assertEqual(context["pods"], [])
        self.assertEqual(context["pc"], 0)
        self.assertEqual(context["pod_info_list"], [])
        self.assertEqual(context["status_count"], {"Running": 0, "Pending": 0, "Failed": 0, "Succeeded": 0, "Unknown": 0})

    def test_pods_view_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/pods/{self.cluster.id}/')

        with self.assertRaises(Cluster.DoesNotExist):
            pods(request, self.cluster.id)

        self.mock_k8s_pods.getpods.assert_not_called()
        self.mock_k8s_pods.get_pod_info.assert_not_called()
        self.mock_k8s_pods.getPodsStatus.assert_not_called()
        self.mock_render.assert_not_called()

    def test_pods_view_k8s_api_failure(self):
        self._setup_successful_mocks() 
        self.mock_k8s_pods.getpods.side_effect = Exception("K8s connection error")
        self.mock_k8s_pods.get_pod_info.reset_mock()
        self.mock_k8s_pods.getPodsStatus.reset_mock()

        request = self.factory.get(f'/dashboard/pods/{self.cluster.id}/')
        with self.assertRaises(Exception):
            pods(request, self.cluster.id)

        self.mock_render.assert_not_called()
        self.mock_k8s_pods.getpods.assert_called_once()
        self.mock_k8s_pods.get_pod_info.assert_not_called()
        self.mock_k8s_pods.getPodsStatus.assert_not_called()

    def test_pods_view_partial_k8s_data(self):
        self._setup_successful_mocks()
        self.mock_k8s_pods.get_pod_info.return_value = [
            {"name": "pod-1", "containers": 1, "images": ["image-x"]}
        ]

        request = self.factory.get(f'/dashboard/pods/{self.cluster.id}/')
        response = pods(request, self.cluster.id)

        self.mock_render.assert_called_once()
        context = self.mock_render.call_args[0][2]

        self.assertEqual(len(context["pods"]), 2) 
        self.assertEqual(len(context["pod_info_list"]), 1) 

        self.mock_get_utils_data.assert_called_once()
        self.mock_k8s_pods.getpods.assert_called_once()
        self.mock_k8s_pods.get_pod_info.assert_called_once()
        self.mock_k8s_pods.getPodsStatus.assert_called_once()


class PodInfoViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.kube_config_entry = KubeConfig.objects.create(
            path='/test/kube/config/path',
            path_type='file'
        )
        self.cluster = Cluster.objects.create(
            cluster_name='my-test-cluster',
            context_name='my-test-context',
            kube_config=self.kube_config_entry,
            id=101
        )

        self.patcher_k8s_pods = patch('dashboard.views.k8s_pods')
        self.mock_k8s_pods = self.patcher_k8s_pods.start()

        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()

        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_pods.stop()
        self.patcher_get_utils_data.stop()
        self.patcher_render.stop()

    def _setup_successful_mocks(self):
        mock_current_cluster = MagicMock()
        mock_current_cluster.context_name = self.cluster.context_name
        self.mock_get_utils_data.return_value = (
            str(self.cluster.id),  
            mock_current_cluster,  
            self.kube_config_entry.path,  
            ['cluster-A', 'my-test-cluster'], 
            ['default', 'kube-system'], 
            self.cluster.context_name 
        )
        self.mock_k8s_pods.get_pod_description.return_value = "Pod description"
        self.mock_k8s_pods.get_pod_logs.return_value = "Pod logs"
        self.mock_k8s_pods.get_pod_events.return_value = "Pod events"
        self.mock_k8s_pods.get_pod_yaml.return_value = "Pod yaml"

    def test_pod_info_view_successful_rendering(self):
        self._setup_successful_mocks()
        request = self.factory.get(f'/dashboard/pod_info/{self.cluster.id}/default/pod-1/')
        response = pod_info(request, self.cluster.id, "default", "pod-1")

        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/workloads/pod_info.html')

        context = args[2]
        self.assertIn("pod_info", context)
        self.assertIn("cluster_id", context)
        self.assertIn("pod_name", context)
        self.assertIn("registered_clusters", context)
        self.assertIn("current_cluster", context)

        pod_info_dict = context["pod_info"]
        self.assertEqual(pod_info_dict["describe"], "Pod description")
        self.assertEqual(pod_info_dict["logs"], "Pod logs")
        self.assertEqual(pod_info_dict["events"], "Pod events")
        self.assertEqual(pod_info_dict["yaml"], "Pod yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["pod_name"], "pod-1")
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])

        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_pods.get_pod_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "pod-1"
        )
        self.mock_k8s_pods.get_pod_logs.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "pod-1"
        )
        self.mock_k8s_pods.get_pod_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "pod-1"
        )
        self.mock_k8s_pods.get_pod_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "pod-1"
        )

    def test_pod_info_view_events_none(self):
        self._setup_successful_mocks()
        self.mock_k8s_pods.get_pod_events.return_value = None
        request = self.factory.get(f'/dashboard/pod_info/{self.cluster.id}/default/pod-1/')
        response = pod_info(request, self.cluster.id, "default", "pod-1")

        context = self.mock_render.call_args[0][2]
        self.assertEqual(context["pod_info"]["events"], "< None >")

    def test_pod_info_view_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/pod_info/{self.cluster.id}/default/pod-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            pod_info(request, self.cluster.id, "default", "pod-1")
        self.mock_k8s_pods.get_pod_description.assert_not_called()
        self.mock_k8s_pods.get_pod_logs.assert_not_called()
        self.mock_k8s_pods.get_pod_events.assert_not_called()
        self.mock_k8s_pods.get_pod_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_pod_info_view_k8s_api_failure(self):
        self._setup_successful_mocks()
        self.mock_k8s_pods.get_pod_description.side_effect = Exception("K8s error")
        self.mock_k8s_pods.get_pod_logs.side_effect = Exception("K8s error")
        self.mock_k8s_pods.get_pod_events.side_effect = Exception("K8s error")
        self.mock_k8s_pods.get_pod_yaml.side_effect = Exception("K8s error")

        request = self.factory.get(f'/dashboard/pod_info/{self.cluster.id}/default/pod-1/')
        with self.assertRaises(Exception):
            pod_info(request, self.cluster.id, "default", "pod-1")
        
        
class ReplicasetViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.kube_config_entry = KubeConfig.objects.create(
            path='/test/kube/config/path',
            path_type='file'
        )
        self.cluster = Cluster.objects.create(
            cluster_name='my-test-cluster',
            context_name='my-test-context',
            kube_config=self.kube_config_entry,
            id=101
        )
        self.patcher_k8s_replicaset = patch('dashboard.views.k8s_replicaset')
        self.mock_k8s_replicaset = self.patcher_k8s_replicaset.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_replicaset.stop()
        self.patcher_get_utils_data.stop()
        self.patcher_render.stop()

    def _setup_utils_data(self):
        mock_current_cluster = MagicMock()
        mock_current_cluster.context_name = self.cluster.context_name
        self.mock_get_utils_data.return_value = (
            str(self.cluster.id),
            mock_current_cluster,
            self.kube_config_entry.path,
            ['cluster-A', 'my-test-cluster'],
            ['default', 'kube-system'],
            self.cluster.context_name
        )

    def test_replicasets_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_replicaset.getReplicasetStatus.return_value = {"Running": 2, "Failed": 0}
        self.mock_k8s_replicaset.getReplicaSetsInfo.return_value = [
            {"name": "rs-1", "replicas": 3},
            {"name": "rs-2", "replicas": 1}
        ]
        request = self.factory.get(f'/dashboard/replicasets/{self.cluster.id}/')
        response = replicasets(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/workloads/replicasets.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["replicaset_info_list"], self.mock_k8s_replicaset.getReplicaSetsInfo.return_value)
        self.assertEqual(context["rs_status"], self.mock_k8s_replicaset.getReplicasetStatus.return_value)
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_replicaset.getReplicasetStatus.assert_called_once_with(self.kube_config_entry.path, self.cluster.context_name)
        self.mock_k8s_replicaset.getReplicaSetsInfo.assert_called_once_with(self.kube_config_entry.path, self.cluster.context_name)

    def test_replicasets_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/replicasets/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            replicasets(request, self.cluster.id)
        self.mock_k8s_replicaset.getReplicasetStatus.assert_not_called()
        self.mock_k8s_replicaset.getReplicaSetsInfo.assert_not_called()
        self.mock_render.assert_not_called()

    def test_replicasets_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_replicaset.getReplicasetStatus.side_effect = Exception("K8s error")
        self.mock_k8s_replicaset.getReplicaSetsInfo.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/replicasets/{self.cluster.id}/')
        with self.assertRaises(Exception):
            replicasets(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_replicaset.getReplicasetStatus.assert_called_once()
        self.mock_k8s_replicaset.getReplicaSetsInfo.assert_not_called()  # Because first call raises

    def test_rs_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_replicaset.get_replicaset_description.return_value = "RS description"
        self.mock_k8s_replicaset.get_replicaset_events.return_value = "RS events"
        self.mock_k8s_replicaset.get_yaml_rs.return_value = "RS yaml"
        request = self.factory.get(f'/dashboard/rs_info/{self.cluster.id}/default/rs-1/')
        response = rs_info(request, self.cluster.id, "default", "rs-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/workloads/rs_info.html')
        context = args[2]
        self.assertIn("rs_info", context)
        self.assertEqual(context["rs_info"]["describe"], "RS description")
        self.assertEqual(context["rs_info"]["events"], "RS events")
        self.assertEqual(context["rs_info"]["yaml"], "RS yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["rs_name"], "rs-1")
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_replicaset.get_replicaset_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "rs-1"
        )
        self.mock_k8s_replicaset.get_replicaset_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "rs-1"
        )
        self.mock_k8s_replicaset.get_yaml_rs.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "rs-1"
        )

    def test_rs_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/rs_info/{self.cluster.id}/default/rs-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            rs_info(request, self.cluster.id, "default", "rs-1")
        self.mock_k8s_replicaset.get_replicaset_description.assert_not_called()
        self.mock_k8s_replicaset.get_replicaset_events.assert_not_called()
        self.mock_k8s_replicaset.get_yaml_rs.assert_not_called()
        self.mock_render.assert_not_called()

    def test_rs_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_replicaset.get_replicaset_description.side_effect = Exception("K8s error")
        self.mock_k8s_replicaset.get_replicaset_events.side_effect = Exception("K8s error")
        self.mock_k8s_replicaset.get_yaml_rs.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/rs_info/{self.cluster.id}/default/rs-1/')
        with self.assertRaises(Exception):
            rs_info(request, self.cluster.id, "default", "rs-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_replicaset.get_replicaset_description.assert_called_once()
        self.mock_k8s_replicaset.get_replicaset_events.assert_not_called()
        self.mock_k8s_replicaset.get_yaml_rs.assert_not_called()
        
class DeploymentsViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.kube_config_entry = KubeConfig.objects.create(
            path='/test/kube/config/path',
            path_type='file'
        )
        self.cluster = Cluster.objects.create(
            cluster_name='my-test-cluster',
            context_name='my-test-context',
            kube_config=self.kube_config_entry,
            id=101
        )
        self.patcher_k8s_deployments = patch('dashboard.views.k8s_deployments')
        self.mock_k8s_deployments = self.patcher_k8s_deployments.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_deployments.stop()
        self.patcher_get_utils_data.stop()
        self.patcher_render.stop()

    def _setup_utils_data(self):
        mock_current_cluster = MagicMock()
        mock_current_cluster.context_name = self.cluster.context_name
        self.mock_get_utils_data.return_value = (
            str(self.cluster.id),
            mock_current_cluster,
            self.kube_config_entry.path,
            ['cluster-A', 'my-test-cluster'],
            ['default', 'kube-system'],
            self.cluster.context_name
        )

    def test_deployments_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_deployments.getDeploymentsStatus.return_value = {"Running": 2, "Failed": 0}
        self.mock_k8s_deployments.getDeploymentsInfo.return_value = [
            {"name": "deploy-1", "replicas": 3},
            {"name": "deploy-2", "replicas": 1}
        ]
        request = self.factory.get(f'/dashboard/deployments/{self.cluster.id}/')
        deployments(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/workloads/deployment.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["dep_status"], self.mock_k8s_deployments.getDeploymentsStatus.return_value)
        self.assertEqual(context["deployment_info_list"], self.mock_k8s_deployments.getDeploymentsInfo.return_value)
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_deployments.getDeploymentsStatus.assert_called_once_with(self.kube_config_entry.path, self.cluster.context_name)
        self.mock_k8s_deployments.getDeploymentsInfo.assert_called_once_with(self.kube_config_entry.path, self.cluster.context_name)

    def test_deployments_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/deployments/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            deployments(request, self.cluster.id)
        self.mock_k8s_deployments.getDeploymentsStatus.assert_not_called()
        self.mock_k8s_deployments.getDeploymentsInfo.assert_not_called()
        self.mock_render.assert_not_called()

    def test_deployments_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_deployments.getDeploymentsStatus.side_effect = Exception("K8s error")
        self.mock_k8s_deployments.getDeploymentsInfo.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/deployments/{self.cluster.id}/')
        with self.assertRaises(Exception):
            deployments(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_deployments.getDeploymentsStatus.assert_called_once()
        self.mock_k8s_deployments.getDeploymentsInfo.assert_not_called() 

    def test_deploy_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_deployments.get_deployment_description.return_value = "Deploy description"
        self.mock_k8s_deployments.get_deploy_events.return_value = "Deploy events"
        self.mock_k8s_deployments.get_yaml_deploy.return_value = "Deploy yaml"
        request = self.factory.get(f'/dashboard/deploy_info/{self.cluster.id}/default/deploy-1/')
        deploy_info(request, self.cluster.id, "default", "deploy-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/workloads/deploy_info.html')
        context = args[2]
        self.assertIn("deploy_info", context)
        self.assertEqual(context["deploy_info"]["describe"], "Deploy description")
        self.assertEqual(context["deploy_info"]["events"], "Deploy events")
        self.assertEqual(context["deploy_info"]["yaml"], "Deploy yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["deploy_name"], "deploy-1")
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_deployments.get_deployment_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "deploy-1"
        )
        self.mock_k8s_deployments.get_deploy_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "deploy-1"
        )
        self.mock_k8s_deployments.get_yaml_deploy.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "deploy-1"
        )

    def test_deploy_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/deploy_info/{self.cluster.id}/default/deploy-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            deploy_info(request, self.cluster.id, "default", "deploy-1")
        self.mock_k8s_deployments.get_deployment_description.assert_not_called()
        self.mock_k8s_deployments.get_deploy_events.assert_not_called()
        self.mock_k8s_deployments.get_yaml_deploy.assert_not_called()
        self.mock_render.assert_not_called()

    def test_deploy_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_deployments.get_deployment_description.side_effect = Exception("K8s error")
        self.mock_k8s_deployments.get_deploy_events.side_effect = Exception("K8s error")
        self.mock_k8s_deployments.get_yaml_deploy.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/deploy_info/{self.cluster.id}/default/deploy-1/')
        with self.assertRaises(Exception):
            deploy_info(request, self.cluster.id, "default", "deploy-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_deployments.get_deployment_description.assert_called_once()
        self.mock_k8s_deployments.get_deploy_events.assert_not_called()
        self.mock_k8s_deployments.get_yaml_deploy.assert_not_called()

class StatefulsetsViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.kube_config_entry = KubeConfig.objects.create(
            path='/test/kube/config/path',
            path_type='file'
        )
        self.cluster = Cluster.objects.create(
            cluster_name='my-test-cluster',
            context_name='my-test-context',
            kube_config=self.kube_config_entry,
            id=101
        )
        self.patcher_k8s_statefulset = patch('dashboard.views.k8s_statefulset')
        self.mock_k8s_statefulset = self.patcher_k8s_statefulset.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_statefulset.stop()
        self.patcher_get_utils_data.stop()
        self.patcher_render.stop()

    def _setup_utils_data(self):
        mock_current_cluster = MagicMock()
        mock_current_cluster.context_name = self.cluster.context_name
        self.mock_get_utils_data.return_value = (
            str(self.cluster.id),
            mock_current_cluster,
            self.kube_config_entry.path,
            ['cluster-A', 'my-test-cluster'],
            ['default', 'kube-system'],
            self.cluster.context_name
        )

    def test_statefulsets_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_statefulset.getStatefulsetStatus.return_value = {"Running": 2, "Failed": 0}
        self.mock_k8s_statefulset.getStatefulsetList.return_value = [
            {"name": "sts-1", "replicas": 3},
            {"name": "sts-2", "replicas": 1}
        ]
        request = self.factory.get(f'/dashboard/statefulsets/{self.cluster.id}/')
        statefulsets(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/workloads/statefulsets.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["statefulsets_list"], self.mock_k8s_statefulset.getStatefulsetList.return_value)
        self.assertEqual(context["statefulsets_status"], self.mock_k8s_statefulset.getStatefulsetStatus.return_value)
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_statefulset.getStatefulsetStatus.assert_called_once_with(self.kube_config_entry.path, self.cluster.context_name)
        self.mock_k8s_statefulset.getStatefulsetList.assert_called_once_with(self.kube_config_entry.path, self.cluster.context_name)

    def test_statefulsets_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/statefulsets/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            statefulsets(request, self.cluster.id)
        self.mock_k8s_statefulset.getStatefulsetStatus.assert_not_called()
        self.mock_k8s_statefulset.getStatefulsetList.assert_not_called()
        self.mock_render.assert_not_called()

    def test_statefulsets_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_statefulset.getStatefulsetStatus.side_effect = Exception("K8s error")
        self.mock_k8s_statefulset.getStatefulsetList.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/statefulsets/{self.cluster.id}/')
        with self.assertRaises(Exception):
            statefulsets(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_statefulset.getStatefulsetStatus.assert_called_once()
        self.mock_k8s_statefulset.getStatefulsetList.assert_not_called()  

    def test_sts_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_statefulset.get_statefulset_description.return_value = "STS description"
        self.mock_k8s_statefulset.get_sts_events.return_value = "STS events"
        self.mock_k8s_statefulset.get_yaml_sts.return_value = "STS yaml"
        request = self.factory.get(f'/dashboard/sts_info/{self.cluster.id}/default/sts-1/')
        sts_info(request, self.cluster.id, "default", "sts-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/workloads/sts_info.html')
        context = args[2]
        self.assertIn("sts_info", context)
        self.assertEqual(context["sts_info"]["describe"], "STS description")
        self.assertEqual(context["sts_info"]["events"], "STS events")
        self.assertEqual(context["sts_info"]["yaml"], "STS yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["sts_name"], "sts-1")
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_statefulset.get_statefulset_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "sts-1"
        )
        self.mock_k8s_statefulset.get_sts_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "sts-1"
        )
        self.mock_k8s_statefulset.get_yaml_sts.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "sts-1"
        )

    def test_sts_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/sts_info/{self.cluster.id}/default/sts-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            sts_info(request, self.cluster.id, "default", "sts-1")
        self.mock_k8s_statefulset.get_statefulset_description.assert_not_called()
        self.mock_k8s_statefulset.get_sts_events.assert_not_called()
        self.mock_k8s_statefulset.get_yaml_sts.assert_not_called()
        self.mock_render.assert_not_called()

    def test_sts_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_statefulset.get_statefulset_description.side_effect = Exception("K8s error")
        self.mock_k8s_statefulset.get_sts_events.side_effect = Exception("K8s error")
        self.mock_k8s_statefulset.get_yaml_sts.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/sts_info/{self.cluster.id}/default/sts-1/')
        with self.assertRaises(Exception):
            sts_info(request, self.cluster.id, "default", "sts-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_statefulset.get_statefulset_description.assert_called_once()
        self.mock_k8s_statefulset.get_sts_events.assert_not_called()
        self.mock_k8s_statefulset.get_yaml_sts.assert_not_called()
        
class DaemonsetViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.kube_config_entry = KubeConfig.objects.create(
            path='/test/kube/config/path',
            path_type='file'
        )
        self.cluster = Cluster.objects.create(
            cluster_name='my-test-cluster',
            context_name='my-test-context',
            kube_config=self.kube_config_entry,
            id=101
        )
        self.patcher_k8s_daemonset = patch('dashboard.views.k8s_daemonset')
        self.mock_k8s_daemonset = self.patcher_k8s_daemonset.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_daemonset.stop()
        self.patcher_get_utils_data.stop()
        self.patcher_render.stop()

    def _setup_utils_data(self):
        mock_current_cluster = MagicMock()
        mock_current_cluster.context_name = self.cluster.context_name
        self.mock_get_utils_data.return_value = (
            str(self.cluster.id),
            mock_current_cluster,
            self.kube_config_entry.path,
            ['cluster-A', 'my-test-cluster'],
            ['default', 'kube-system'],
            self.cluster.context_name
        )

    def test_daemonset_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_daemonset.getDaemonsetStatus.return_value = {"Running": 2, "Failed": 0}
        self.mock_k8s_daemonset.getDaemonsetList.return_value = [
            {"name": "ds-1", "pods": 3},
            {"name": "ds-2", "pods": 1}
        ]
        request = self.factory.get(f'/dashboard/daemonset/{self.cluster.id}/')
        daemonset(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/workloads/daemonset.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["daemonset_status"], self.mock_k8s_daemonset.getDaemonsetStatus.return_value)
        self.assertEqual(context["daemonset_list"], self.mock_k8s_daemonset.getDaemonsetList.return_value)
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_daemonset.getDaemonsetStatus.assert_called_once_with(self.kube_config_entry.path, self.cluster.context_name)
        self.mock_k8s_daemonset.getDaemonsetList.assert_called_once_with(self.kube_config_entry.path, self.cluster.context_name)

    def test_daemonset_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/daemonset/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            daemonset(request, self.cluster.id)
        self.mock_k8s_daemonset.getDaemonsetStatus.assert_not_called()
        self.mock_k8s_daemonset.getDaemonsetList.assert_not_called()
        self.mock_render.assert_not_called()

    def test_daemonset_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_daemonset.getDaemonsetStatus.side_effect = Exception("K8s error")
        self.mock_k8s_daemonset.getDaemonsetList.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/daemonset/{self.cluster.id}/')
        with self.assertRaises(Exception):
            daemonset(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_daemonset.getDaemonsetStatus.assert_called_once()
        self.mock_k8s_daemonset.getDaemonsetList.assert_not_called()

    def test_daemonset_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_daemonset.get_daemonset_description.return_value = "DS description"
        self.mock_k8s_daemonset.get_daemonset_events.return_value = "DS events"
        self.mock_k8s_daemonset.get_daemonset_yaml.return_value = "DS yaml"
        request = self.factory.get(f'/dashboard/daemonset_info/{self.cluster.id}/default/ds-1/')
        daemonset_info(request, self.cluster.id, "default", "ds-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/workloads/daemonset_info.html')
        context = args[2]
        self.assertIn("daemonset_info", context)
        self.assertEqual(context["daemonset_info"]["describe"], "DS description")
        self.assertEqual(context["daemonset_info"]["events"], "DS events")
        self.assertEqual(context["daemonset_info"]["yaml"], "DS yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["daemonset_name"], "ds-1")
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_daemonset.get_daemonset_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "ds-1"
        )
        self.mock_k8s_daemonset.get_daemonset_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "ds-1"
        )
        self.mock_k8s_daemonset.get_daemonset_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "ds-1"
        )

    def test_daemonset_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/daemonset_info/{self.cluster.id}/default/ds-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            daemonset_info(request, self.cluster.id, "default", "ds-1")
        self.mock_k8s_daemonset.get_daemonset_description.assert_not_called()
        self.mock_k8s_daemonset.get_daemonset_events.assert_not_called()
        self.mock_k8s_daemonset.get_daemonset_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_daemonset_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_daemonset.get_daemonset_description.side_effect = Exception("K8s error")
        self.mock_k8s_daemonset.get_daemonset_events.side_effect = Exception("K8s error")
        self.mock_k8s_daemonset.get_daemonset_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/daemonset_info/{self.cluster.id}/default/ds-1/')
        with self.assertRaises(Exception):
            daemonset_info(request, self.cluster.id, "default", "ds-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_daemonset.get_daemonset_description.assert_called_once()
        self.mock_k8s_daemonset.get_daemonset_events.assert_not_called()
        self.mock_k8s_daemonset.get_daemonset_yaml.assert_not_called()


class JobsViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.kube_config_entry = KubeConfig.objects.create(
            path='/test/kube/config/path',
            path_type='file'
        )
        self.cluster = Cluster.objects.create(
            cluster_name='my-test-cluster',
            context_name='my-test-context',
            kube_config=self.kube_config_entry,
            id=101
        )
        self.patcher_k8s_jobs = patch('dashboard.views.k8s_jobs')
        self.mock_k8s_jobs = self.patcher_k8s_jobs.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()
        # Only patch if validate_and_patch_resource exists in dashboard.views
        try:
            self.patcher_validate_and_patch_resource = patch('dashboard.views.validate_and_patch_resource')
            self.mock_validate_and_patch_resource = self.patcher_validate_and_patch_resource.start()
        except AttributeError:
            self.patcher_validate_and_patch_resource = None
            self.mock_validate_and_patch_resource = None
        if self.patcher_validate_and_patch_resource:
            self.patcher_validate_and_patch_resource.stop()
            
    def tearDown(self):
        self.patcher_k8s_jobs.stop()
        self.patcher_get_utils_data.stop()
        self.patcher_render.stop()
        if self.patcher_validate_and_patch_resource:
            self.patcher_validate_and_patch_resource.stop()

    def _setup_utils_data(self):
        mock_current_cluster = MagicMock()
        mock_current_cluster.context_name = self.cluster.context_name
        self.mock_get_utils_data.return_value = (
            str(self.cluster.id),
            mock_current_cluster,
            self.kube_config_entry.path,
            ['cluster-A', 'my-test-cluster'],
            ['default', 'kube-system'],
            self.cluster.context_name
        )

    def test_jobs_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_jobs.getJobsStatus.return_value = {"Running": 2, "Failed": 0}
        self.mock_k8s_jobs.getJobsList.return_value = [
            {"name": "job-1", "pods": 3},
            {"name": "job-2", "pods": 1}
        ]
        request = self.factory.get(f'/dashboard/jobs/{self.cluster.id}/')
        jobs(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/workloads/jobs.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["jobs_status"], self.mock_k8s_jobs.getJobsStatus.return_value)
        self.assertEqual(context["jobs_list"], self.mock_k8s_jobs.getJobsList.return_value)
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_jobs.getJobsStatus.assert_called_once_with(self.kube_config_entry.path, self.cluster.context_name)
        self.mock_k8s_jobs.getJobsList.assert_called_once_with(self.kube_config_entry.path, self.cluster.context_name)

    def test_jobs_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/jobs/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            jobs(request, self.cluster.id)
        self.mock_k8s_jobs.getJobsStatus.assert_not_called()
        self.mock_k8s_jobs.getJobsList.assert_not_called()
        self.mock_render.assert_not_called()

    def test_jobs_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_jobs.getJobsStatus.side_effect = Exception("K8s error")
        self.mock_k8s_jobs.getJobsList.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/jobs/{self.cluster.id}/')
        with self.assertRaises(Exception):
            jobs(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_jobs.getJobsStatus.assert_called_once()
        self.mock_k8s_jobs.getJobsList.assert_not_called()


    def test_jobs_info_post_patch_failure(self):
        if self.mock_validate_and_patch_resource is None:
            self.skipTest("validate_and_patch_resource is not available to patch")
        self._setup_utils_data()
        self.mock_k8s_jobs.get_job_description.return_value = "Job description"
        self.mock_k8s_jobs.get_job_events.return_value = "Job events"
        self.mock_k8s_jobs.get_yaml_job.side_effect = ["Job yaml", "Job edit", "New yaml", "New edit"]
        self.mock_validate_and_patch_resource.return_value = {
            "success": False,
            "message": "Patch failed"
        }
        request = self.factory.post(f'/dashboard/jobs_info/{self.cluster.id}/default/job-1/', data={'job_yaml': 'bad yaml'})
        jobs_info(request, self.cluster.id, "default", "job-1")
        context = self.mock_render.call_args[0][2]
        self.assertTrue(context["job_info"]["show_modal"])
        self.assertEqual(context["job_info"]["message"], "Patch failed")
        self.assertEqual(context["job_info"]["yaml"], "New yaml")
        self.assertEqual(context["job_info"]["edit"], "New edit")

    def test_jobs_info_post_patch_success(self):
        if self.mock_validate_and_patch_resource is None:
            self.skipTest("validate_and_patch_resource is not available to patch")
        self._setup_utils_data()
        self.mock_k8s_jobs.get_job_description.return_value = "Job description"
        self.mock_k8s_jobs.get_job_events.return_value = "Job events"
        self.mock_k8s_jobs.get_yaml_job.side_effect = ["Job yaml", "Job edit", "New yaml", "New edit"]
        self.mock_validate_and_patch_resource.return_value = {
            "success": True,
            "message": "Patched successfully",
            "changes": {"field": "value"}
        }
        request = self.factory.post(f'/dashboard/jobs_info/{self.cluster.id}/default/job-1/', data={'job_yaml': 'good yaml'})
        jobs_info(request, self.cluster.id, "default", "job-1")
        context = self.mock_render.call_args[0][2]
        self.assertTrue(context["job_info"]["show_modal"])
        self.assertEqual(context["job_info"]["message"], "Patched successfully")
        self.assertEqual(context["job_info"]["changes"], {"field": "value"})
        self.assertEqual(context["job_info"]["yaml"], "New yaml")
        self.assertEqual(context["job_info"]["edit"], "New edit")

    def test_jobs_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/jobs_info/{self.cluster.id}/default/job-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            jobs_info(request, self.cluster.id, "default", "job-1")
        self.mock_k8s_jobs.get_job_description.assert_not_called()
        self.mock_k8s_jobs.get_job_events.assert_not_called()
        self.mock_k8s_jobs.get_yaml_job.assert_not_called()
        self.mock_render.assert_not_called()

    def test_jobs_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_jobs.get_job_description.side_effect = Exception("K8s error")
        self.mock_k8s_jobs.get_job_events.side_effect = Exception("K8s error")
        self.mock_k8s_jobs.get_yaml_job.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/jobs_info/{self.cluster.id}/default/job-1/')
        with self.assertRaises(Exception):
            jobs_info(request, self.cluster.id, "default", "job-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_jobs.get_job_description.assert_called_once()
        self.mock_k8s_jobs.get_job_events.assert_not_called()
        self.mock_k8s_jobs.get_yaml_job.assert_not_called()
        
class CronJobsViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.kube_config_entry = KubeConfig.objects.create(
            path='/test/kube/config/path',
            path_type='file'
        )
        self.cluster = Cluster.objects.create(
            cluster_name='my-test-cluster',
            context_name='my-test-context',
            kube_config=self.kube_config_entry,
            id=101
        )
        self.patcher_k8s_cronjobs = patch('dashboard.views.k8s_cronjobs')
        self.mock_k8s_cronjobs = self.patcher_k8s_cronjobs.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()
        try:
            self.patcher_validate_and_patch_resource = patch('dashboard.views.validate_and_patch_resource')
            self.mock_validate_and_patch_resource = self.patcher_validate_and_patch_resource.start()
        except AttributeError:
            self.patcher_validate_and_patch_resource = None
            self.mock_validate_and_patch_resource = None
        if self.patcher_validate_and_patch_resource:
            self.patcher_validate_and_patch_resource.stop()

    def tearDown(self):
        self.patcher_k8s_cronjobs.stop()
        self.patcher_get_utils_data.stop()
        self.patcher_render.stop()
        if self.patcher_validate_and_patch_resource:
            self.patcher_validate_and_patch_resource.stop()

    def _setup_utils_data(self):
        mock_current_cluster = MagicMock()
        mock_current_cluster.context_name = self.cluster.context_name
        self.mock_get_utils_data.return_value = (
            str(self.cluster.id),
            mock_current_cluster,
            self.kube_config_entry.path,
            ['cluster-A', 'my-test-cluster'],
            ['default', 'kube-system'],
            self.cluster.context_name
        )

    def test_cronjobs_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_cronjobs.getCronJobsStatus.return_value = {"Running": 2, "Failed": 0}
        self.mock_k8s_cronjobs.getCronJobsList.return_value = [
            {"name": "cronjob-1", "pods": 3},
            {"name": "cronjob-2", "pods": 1}
        ]
        request = self.factory.get(f'/dashboard/cronjobs/{self.cluster.id}/')
        cronjobs(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/workloads/cronjobs.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["cronjobs_status"], self.mock_k8s_cronjobs.getCronJobsStatus.return_value)
        self.assertEqual(context["cronjobs_list"], self.mock_k8s_cronjobs.getCronJobsList.return_value)
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_cronjobs.getCronJobsStatus.assert_called_once_with(self.kube_config_entry.path, self.cluster.context_name)
        self.mock_k8s_cronjobs.getCronJobsList.assert_called_once_with(self.kube_config_entry.path, self.cluster.context_name)

    def test_cronjobs_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/cronjobs/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            cronjobs(request, self.cluster.id)
        self.mock_k8s_cronjobs.getCronJobsStatus.assert_not_called()
        self.mock_k8s_cronjobs.getCronJobsList.assert_not_called()
        self.mock_render.assert_not_called()

    def test_cronjobs_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_cronjobs.getCronJobsStatus.side_effect = Exception("K8s error")
        self.mock_k8s_cronjobs.getCronJobsList.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/cronjobs/{self.cluster.id}/')
        with self.assertRaises(Exception):
            cronjobs(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_cronjobs.getCronJobsStatus.assert_called_once()
        self.mock_k8s_cronjobs.getCronJobsList.assert_not_called()

    def test_cronjob_info_post_patch_failure(self):
        if self.mock_validate_and_patch_resource is None:
            self.skipTest("validate_and_patch_resource is not available to patch")
        self._setup_utils_data()
        self.mock_k8s_cronjobs.get_cronjob_description.return_value = "CronJob description"
        self.mock_k8s_cronjobs.get_cronjob_events.return_value = "CronJob events"
        self.mock_k8s_cronjobs.get_yaml_cronjob.side_effect = ["CronJob yaml", "CronJob edit", "New yaml", "New edit"]
        self.mock_validate_and_patch_resource.return_value = {
            "success": False,
            "message": "Patch failed"
        }
        request = self.factory.post(f'/dashboard/cronjob_info/{self.cluster.id}/default/cronjob-1/', data={'cronjob_yaml': 'bad yaml'})
        cronjob_info(request, self.cluster.id, "default", "cronjob-1")
        context = self.mock_render.call_args[0][2]
        self.assertTrue(context["cronjob_info"]["show_modal"])
        self.assertEqual(context["cronjob_info"]["message"], "Patch failed")
        self.assertEqual(context["cronjob_info"]["yaml"], "New yaml")
        self.assertEqual(context["cronjob_info"]["edit"], "New edit")

    def test_cronjob_info_post_patch_success(self):
        if self.mock_validate_and_patch_resource is None:
            self.skipTest("validate_and_patch_resource is not available to patch")
        self._setup_utils_data()
        self.mock_k8s_cronjobs.get_cronjob_description.return_value = "CronJob description"
        self.mock_k8s_cronjobs.get_cronjob_events.return_value = "CronJob events"
        self.mock_k8s_cronjobs.get_yaml_cronjob.side_effect = ["CronJob yaml", "CronJob edit", "New yaml", "New edit"]
        self.mock_validate_and_patch_resource.return_value = {
            "success": True,
            "message": "Patched successfully",
            "changes": {"field": "value"}
        }
        request = self.factory.post(f'/dashboard/cronjob_info/{self.cluster.id}/default/cronjob-1/', data={'cronjob_yaml': 'good yaml'})
        cronjob_info(request, self.cluster.id, "default", "cronjob-1")
        context = self.mock_render.call_args[0][2]
        self.assertTrue(context["cronjob_info"]["show_modal"])
        self.assertEqual(context["cronjob_info"]["message"], "Patched successfully")
        self.assertEqual(context["cronjob_info"]["changes"], {"field": "value"})
        self.assertEqual(context["cronjob_info"]["yaml"], "New yaml")
        self.assertEqual(context["cronjob_info"]["edit"], "New edit")

    def test_cronjob_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/cronjob_info/{self.cluster.id}/default/cronjob-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            cronjob_info(request, self.cluster.id, "default", "cronjob-1")
        self.mock_k8s_cronjobs.get_cronjob_description.assert_not_called()
        self.mock_k8s_cronjobs.get_cronjob_events.assert_not_called()
        self.mock_k8s_cronjobs.get_yaml_cronjob.assert_not_called()
        self.mock_render.assert_not_called()

    def test_cronjob_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_cronjobs.get_cronjob_description.side_effect = Exception("K8s error")
        self.mock_k8s_cronjobs.get_cronjob_events.side_effect = Exception("K8s error")
        self.mock_k8s_cronjobs.get_yaml_cronjob.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/cronjob_info/{self.cluster.id}/default/cronjob-1/')
        with self.assertRaises(Exception):
            cronjob_info(request, self.cluster.id, "default", "cronjob-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_cronjobs.get_cronjob_description.assert_called_once()
        self.mock_k8s_cronjobs.get_cronjob_events.assert_not_called()
        self.mock_k8s_cronjobs.get_yaml_cronjob.assert_not_called()

class NamespaceViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.kube_config_entry = KubeConfig.objects.create(
            path='/test/kube/config/path',
            path_type='file'
        )
        self.cluster = Cluster.objects.create(
            cluster_name='my-test-cluster',
            context_name='my-test-context',
            kube_config=self.kube_config_entry,
            id=101
        )
        self.patcher_clusters_DB = patch('dashboard.views.clusters_DB')
        self.mock_clusters_DB = self.patcher_clusters_DB.start()
        self.patcher_k8s_namespaces = patch('dashboard.views.k8s_namespaces')
        self.mock_k8s_namespaces = self.patcher_k8s_namespaces.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()

    def tearDown(self):
        self.patcher_clusters_DB.stop()
        self.patcher_k8s_namespaces.stop()
        self.patcher_render.stop()
        self.patcher_get_utils_data.stop()

    def test_namespace_successful_rendering(self):
        self.mock_clusters_DB.get_cluster_names.return_value = ['cluster-A', 'my-test-cluster']
        self.mock_k8s_namespaces.namespaces_data.return_value = ['default', 'kube-system']
        request = self.factory.get('/dashboard/namespace/', {'cluster_id': str(self.cluster.id)})
        response = namespace(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/cluster_management/namespace.html')
        context = args[2]
        self.assertEqual(context['cluster_id'], str(self.cluster.id))
        self.assertEqual(context['registered_clusters'], ['cluster-A', 'my-test-cluster'])
        self.assertEqual(context['namespaces'], ['default', 'kube-system'])
        self.assertEqual(context['namespaces_count'], 2)
        self.assertEqual(context['current_cluster'], self.cluster)
        self.mock_clusters_DB.get_cluster_names.assert_called_once()
        self.mock_k8s_namespaces.namespaces_data.assert_called_once_with(self.kube_config_entry.path, self.cluster.context_name)

    def test_namespace_no_namespaces(self):
        self.mock_clusters_DB.get_cluster_names.return_value = ['cluster-A']
        self.mock_k8s_namespaces.namespaces_data.return_value = []
        request = self.factory.get('/dashboard/namespace/', {'cluster_id': str(self.cluster.id)})
        response = namespace(request, self.cluster.id)
        context = self.mock_render.call_args[0][2]
        self.assertEqual(context['namespaces'], [])
        self.assertEqual(context['namespaces_count'], 0)

    def test_namespace_cluster_does_not_exist(self):
        request = self.factory.get('/dashboard/namespace/', {'cluster_id': 9999})
        with self.assertRaises(Cluster.DoesNotExist):
            namespace(request, 9999)
        self.mock_render.assert_not_called()

    def test_ns_info_successful_rendering(self):
        mock_utils_data = (
            str(self.cluster.id),
            self.cluster,
            self.kube_config_entry.path,
            ['cluster-A', 'my-test-cluster'],
            ['default', 'kube-system'],
            self.cluster.context_name
        )
        self.mock_get_utils_data.return_value = mock_utils_data
        self.mock_k8s_namespaces.get_namespace_description.return_value = "Namespace description"
        self.mock_k8s_namespaces.get_namespace_yaml.return_value = "Namespace yaml"
        request = self.factory.get(f'/dashboard/ns_info/{self.cluster.id}/default/')
        response = ns_info(request, self.cluster.id, "default")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/cluster_management/ns_info.html')
        context = args[2]
        self.assertIn("ns_info", context)
        self.assertEqual(context["ns_info"]["describe"], "Namespace description")
        self.assertEqual(context["ns_info"]["yaml"], "Namespace yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["namespace"], "default")
        self.assertEqual(context["registered_clusters"], mock_utils_data[3])
        self.assertEqual(context["current_cluster"], mock_utils_data[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_namespaces.get_namespace_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default"
        )
        self.mock_k8s_namespaces.get_namespace_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default"
        )

    def test_ns_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/ns_info/{self.cluster.id}/default/')
        with self.assertRaises(Cluster.DoesNotExist):
            ns_info(request, self.cluster.id, "default")
        self.mock_k8s_namespaces.get_namespace_description.assert_not_called()
        self.mock_k8s_namespaces.get_namespace_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_ns_info_k8s_api_failure(self):
        mock_utils_data = (
            str(self.cluster.id),
            self.cluster,
            self.kube_config_entry.path,
            ['cluster-A', 'my-test-cluster'],
            ['default', 'kube-system'],
            self.cluster.context_name
        )
        self.mock_get_utils_data.return_value = mock_utils_data
        self.mock_k8s_namespaces.get_namespace_description.side_effect = Exception("K8s error")
        self.mock_k8s_namespaces.get_namespace_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/ns_info/{self.cluster.id}/default/')
        with self.assertRaises(Exception):
            ns_info(request, self.cluster.id, "default")
        self.mock_render.assert_not_called()
        self.mock_k8s_namespaces.get_namespace_description.assert_called_once()
        self.mock_k8s_namespaces.get_namespace_yaml.assert_not_called()
        
class NodesViewsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.kube_config_entry = KubeConfig.objects.create(
            path='/test/kube/config/path',
            path_type='file'
        )
        self.cluster = Cluster.objects.create(
            cluster_name='my-test-cluster',
            context_name='my-test-context',
            kube_config=self.kube_config_entry,
            id=101
        )
        self.patcher_k8s_nodes = patch('dashboard.views.k8s_nodes')
        self.mock_k8s_nodes = self.patcher_k8s_nodes.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_nodes.stop()
        self.patcher_get_utils_data.stop()
        self.patcher_render.stop()

    def _setup_utils_data(self):
        mock_current_cluster = MagicMock()
        mock_current_cluster.context_name = self.cluster.context_name
        self.mock_get_utils_data.return_value = (
            str(self.cluster.id),
            mock_current_cluster,
            self.kube_config_entry.path,
            ['cluster-A', 'my-test-cluster'],
            ['default', 'kube-system'],
            self.cluster.context_name
        )

    def test_nodes_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_nodes.get_nodes_info.return_value = [
            {"name": "node-1", "status": "Ready"},
            {"name": "node-2", "status": "NotReady"}
        ]
        self.mock_k8s_nodes.getNodesStatus.return_value = (1, 1, 2)
        request = self.factory.get(f'/dashboard/nodes/{self.cluster.id}/')
        nodes(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/cluster_management/nodes.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["nodes"], self.mock_k8s_nodes.get_nodes_info.return_value)
        self.assertEqual(context["ready_nodes"], 1)
        self.assertEqual(context["not_ready_nodes"], 1)
        self.assertEqual(context["total_nodes"], 2)
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_nodes.get_nodes_info.assert_called_once_with(self.kube_config_entry.path, self.cluster.context_name)
        self.mock_k8s_nodes.getNodesStatus.assert_called_once_with(self.kube_config_entry.path, self.cluster.context_name)

    def test_nodes_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/nodes/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            nodes(request, self.cluster.id)
        self.mock_k8s_nodes.get_nodes_info.assert_not_called()
        self.mock_k8s_nodes.getNodesStatus.assert_not_called()
        self.mock_render.assert_not_called()

    def test_nodes_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_nodes.get_nodes_info.side_effect = Exception("K8s error")
        self.mock_k8s_nodes.getNodesStatus.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/nodes/{self.cluster.id}/')
        with self.assertRaises(Exception):
            nodes(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_nodes.get_nodes_info.assert_called_once()
        self.mock_k8s_nodes.getNodesStatus.assert_not_called()

    def test_node_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_nodes.get_node_description.return_value = "Node description"
        self.mock_k8s_nodes.get_node_yaml.return_value = "Node yaml"
        request = self.factory.get(f'/dashboard/node_info/{self.cluster.id}/node-1/')
        node_info(request, self.cluster.id, "node-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/cluster_management/node_info.html')
        context = args[2]
        self.assertIn("node_info", context)
        self.assertEqual(context["node_info"]["describe"], "Node description")
        self.assertEqual(context["node_info"]["yaml"], "Node yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["node_name"], "node-1")
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_nodes.get_node_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "node-1"
        )
        self.mock_k8s_nodes.get_node_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "node-1"
        )

    def test_node_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/node_info/{self.cluster.id}/node-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            node_info(request, self.cluster.id, "node-1")
        self.mock_k8s_nodes.get_node_description.assert_not_called()
        self.mock_k8s_nodes.get_node_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_node_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_nodes.get_node_description.side_effect = Exception("K8s error")
        self.mock_k8s_nodes.get_node_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/node_info/{self.cluster.id}/node-1/')
        with self.assertRaises(Exception):
            node_info(request, self.cluster.id, "node-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_nodes.get_node_description.assert_called_once()
        self.mock_k8s_nodes.get_node_yaml.assert_not_called()
