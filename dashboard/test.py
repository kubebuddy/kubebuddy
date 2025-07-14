from django.test import TestCase, RequestFactory
from unittest.mock import patch, MagicMock
from main.models import KubeConfig, Cluster 
from dashboard.views import get_utils_data, pods, pod_info, replicasets, rs_info, deployments, deploy_info, statefulsets, sts_info, daemonset, daemonset_info, jobs, jobs_info, cronjob_info, cronjobs, namespace, ns_info, nodes, node_info, limitrange, limitrange_info, resourcequota_info, resourcequotas,pdb,pdb_info, configmaps, configmap_info, secret_info, secrets, services, service_info, endpoints, endpoint_info, persistentvolume, pv_info, persistentvolumeclaim, pvc_info, storageclass, storageclass_info, np, np_info, ingress, ingress_info, role, role_info, role_binding_info, rolebinding, clusterrole, clusterrole_info, clusterrolebinding, cluster_role_binding_info, serviceAccount, serviceAccountInfo, pod_metrics, node_metrics, events, execute_command
from django.http import JsonResponse
import os
import json



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
        self.mock_k8s_nodes.get_nodes_status.return_value = (1, 1, 2)
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
        self.mock_k8s_nodes.get_nodes_status.assert_called_once_with(self.kube_config_entry.path, self.cluster.context_name)

    def test_nodes_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/nodes/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            nodes(request, self.cluster.id)
        self.mock_k8s_nodes.get_nodes_info.assert_not_called()
        self.mock_k8s_nodes.get_nodes_status.assert_not_called()
        self.mock_render.assert_not_called()

    def test_nodes_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_nodes.get_nodes_info.side_effect = Exception("K8s error")
        self.mock_k8s_nodes.get_nodes_status.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/nodes/{self.cluster.id}/')
        with self.assertRaises(Exception):
            nodes(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_nodes.get_nodes_info.assert_called_once()
        self.mock_k8s_nodes.get_nodes_status.assert_not_called()

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
        
class LimitRangeViewsTests(TestCase):
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
        self.patcher_k8s_limit_range = patch('dashboard.views.k8s_limit_range')
        self.mock_k8s_limit_range = self.patcher_k8s_limit_range.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_limit_range.stop()
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

    def test_limitrange_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_limit_range.get_limit_ranges.return_value = (
            [
                {"name": "lr-1", "namespace": "default"},
                {"name": "lr-2", "namespace": "kube-system"}
            ],
            2
        )
        request = self.factory.get(f'/dashboard/limitrange/{self.cluster.id}/')
        limitrange(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/cluster_management/limitrange.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["limitranges"], self.mock_k8s_limit_range.get_limit_ranges.return_value[0])
        self.assertEqual(context["total_limitranges"], 2)
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_limit_range.get_limit_ranges.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_limitrange_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/limitrange/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            limitrange(request, self.cluster.id)
        self.mock_k8s_limit_range.get_limit_ranges.assert_not_called()
        self.mock_render.assert_not_called()

    def test_limitrange_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_limit_range.get_limit_ranges.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/limitrange/{self.cluster.id}/')
        with self.assertRaises(Exception):
            limitrange(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_limit_range.get_limit_ranges.assert_called_once()

    def test_limitrange_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_limit_range.get_limit_range_description.return_value = "LimitRange description"
        self.mock_k8s_limit_range.get_limitrange_events.return_value = "LimitRange events"
        self.mock_k8s_limit_range.get_limitrange_yaml.return_value = "LimitRange yaml"
        request = self.factory.get(f'/dashboard/limitrange_info/{self.cluster.id}/default/lr-1/')
        limitrange_info(request, self.cluster.id, "default", "lr-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/cluster_management/limitrange_info.html')
        context = args[2]
        self.assertIn("limitrange_info", context)
        self.assertEqual(context["limitrange_info"]["describe"], "LimitRange description")
        self.assertEqual(context["limitrange_info"]["events"], "LimitRange events")
        self.assertEqual(context["limitrange_info"]["yaml"], "LimitRange yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["limitrange_name"], "lr-1")
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_limit_range.get_limit_range_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "lr-1"
        )
        self.mock_k8s_limit_range.get_limitrange_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "lr-1"
        )
        self.mock_k8s_limit_range.get_limitrange_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "lr-1"
        )

    def test_limitrange_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/limitrange_info/{self.cluster.id}/default/lr-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            limitrange_info(request, self.cluster.id, "default", "lr-1")
        self.mock_k8s_limit_range.get_limit_range_description.assert_not_called()
        self.mock_k8s_limit_range.get_limitrange_events.assert_not_called()
        self.mock_k8s_limit_range.get_limitrange_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_limitrange_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_limit_range.get_limit_range_description.side_effect = Exception("K8s error")
        self.mock_k8s_limit_range.get_limitrange_events.side_effect = Exception("K8s error")
        self.mock_k8s_limit_range.get_limitrange_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/limitrange_info/{self.cluster.id}/default/lr-1/')
        with self.assertRaises(Exception):
            limitrange_info(request, self.cluster.id, "default", "lr-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_limit_range.get_limit_range_description.assert_called_once()
        self.mock_k8s_limit_range.get_limitrange_events.assert_not_called()
        self.mock_k8s_limit_range.get_limitrange_yaml.assert_not_called()

class ResourceQuotaViewsTests(TestCase):
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
        self.patcher_k8s_resource_quota = patch('dashboard.views.k8s_resource_quota')
        self.mock_k8s_resource_quota = self.patcher_k8s_resource_quota.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_resource_quota.stop()
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

    def test_resourcequotas_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_resource_quota.get_resource_quotas.return_value = (
            [
                {"name": "rq-1", "namespace": "default"},
                {"name": "rq-2", "namespace": "kube-system"}
            ],
            2
        )
        request = self.factory.get(f'/dashboard/resourcequotas/{self.cluster.id}/')
        resourcequotas(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/cluster_management/resourcequotas.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["resourcequotas"], self.mock_k8s_resource_quota.get_resource_quotas.return_value[0])
        self.assertEqual(context["total_quotas"], 2)
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_resource_quota.get_resource_quotas.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_resourcequotas_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/resourcequotas/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            resourcequotas(request, self.cluster.id)
        self.mock_k8s_resource_quota.get_resource_quotas.assert_not_called()
        self.mock_render.assert_not_called()

    def test_resourcequotas_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_resource_quota.get_resource_quotas.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/resourcequotas/{self.cluster.id}/')
        with self.assertRaises(Exception):
            resourcequotas(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_resource_quota.get_resource_quotas.assert_called_once()

    def test_resourcequota_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_resource_quota.get_resourcequota_description.return_value = "RQ description"
        self.mock_k8s_resource_quota.get_resourcequota_events.return_value = "RQ events"
        self.mock_k8s_resource_quota.get_resourcequota_yaml.return_value = "RQ yaml"
        request = self.factory.get(f'/dashboard/resourcequota_info/{self.cluster.id}/default/rq-1/')
        resourcequota_info(request, self.cluster.id, "default", "rq-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        context = args[2]
        self.assertIn("resourcequota_info", context)
        self.assertEqual(context["resourcequota_info"]["describe"], "RQ description")
        self.assertEqual(context["resourcequota_info"]["events"], "RQ events")
        self.assertEqual(context["resourcequota_info"]["yaml"], "RQ yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["resourcequota_name"], "rq-1")
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_resource_quota.get_resourcequota_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "rq-1"
        )
        self.mock_k8s_resource_quota.get_resourcequota_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "rq-1"
        )
        self.mock_k8s_resource_quota.get_resourcequota_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "rq-1"
        )

    def test_resourcequota_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/resourcequota_info/{self.cluster.id}/default/rq-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            resourcequota_info(request, self.cluster.id, "default", "rq-1")
        self.mock_k8s_resource_quota.get_resourcequota_description.assert_not_called()
        self.mock_k8s_resource_quota.get_resourcequota_events.assert_not_called()
        self.mock_k8s_resource_quota.get_resourcequota_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_resourcequota_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_resource_quota.get_resourcequota_description.side_effect = Exception("K8s error")
        self.mock_k8s_resource_quota.get_resourcequota_events.side_effect = Exception("K8s error")
        self.mock_k8s_resource_quota.get_resourcequota_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/resourcequota_info/{self.cluster.id}/default/rq-1/')
        with self.assertRaises(Exception):
            resourcequota_info(request, self.cluster.id, "default", "rq-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_resource_quota.get_resourcequota_description.assert_called_once()
        self.mock_k8s_resource_quota.get_resourcequota_events.assert_not_called()
        self.mock_k8s_resource_quota.get_resourcequota_yaml.assert_not_called()
        
class PDBViewsTests(TestCase):
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
        self.patcher_k8s_pdb = patch('dashboard.views.k8s_pdb')
        self.mock_k8s_pdb = self.patcher_k8s_pdb.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_pdb.stop()
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

    def test_pdb_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_pdb.get_pdb.return_value = (
            [
                {"name": "pdb-1", "namespace": "default"},
                {"name": "pdb-2", "namespace": "kube-system"}
            ],
            2
        )
        request = self.factory.get(f'/dashboard/pdb/{self.cluster.id}/')
        pdb(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/cluster_management/pdb.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["pdbs"], self.mock_k8s_pdb.get_pdb.return_value[0])
        self.assertEqual(context["pdbs_count"], 2)
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_pdb.get_pdb.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_pdb_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/pdb/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            pdb(request, self.cluster.id)
        self.mock_k8s_pdb.get_pdb.assert_not_called()
        self.mock_render.assert_not_called()

    def test_pdb_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_pdb.get_pdb.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/pdb/{self.cluster.id}/')
        with self.assertRaises(Exception):
            pdb(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_pdb.get_pdb.assert_called_once()

    def test_pdb_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_pdb.get_pdb_description.return_value = "PDB description"
        self.mock_k8s_pdb.get_pdb_events.return_value = "PDB events"
        self.mock_k8s_pdb.get_pdb_yaml.return_value = "PDB yaml"
        request = self.factory.get(f'/dashboard/pdb_info/{self.cluster.id}/default/pdb-1/')
        pdb_info(request, self.cluster.id, "default", "pdb-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/cluster_management/pdb_info.html')
        context = args[2]
        self.assertIn("pdb_info", context)
        self.assertEqual(context["pdb_info"]["describe"], "PDB description")
        self.assertEqual(context["pdb_info"]["events"], "PDB events")
        self.assertEqual(context["pdb_info"]["yaml"], "PDB yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_pdb.get_pdb_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "pdb-1"
        )
        self.mock_k8s_pdb.get_pdb_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "pdb-1"
        )
        self.mock_k8s_pdb.get_pdb_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "pdb-1"
        )

    def test_pdb_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/pdb_info/{self.cluster.id}/default/pdb-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            pdb_info(request, self.cluster.id, "default", "pdb-1")
        self.mock_k8s_pdb.get_pdb_description.assert_not_called()
        self.mock_k8s_pdb.get_pdb_events.assert_not_called()
        self.mock_k8s_pdb.get_pdb_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_pdb_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_pdb.get_pdb_description.side_effect = Exception("K8s error")
        self.mock_k8s_pdb.get_pdb_events.side_effect = Exception("K8s error")
        self.mock_k8s_pdb.get_pdb_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/pdb_info/{self.cluster.id}/default/pdb-1/')
        with self.assertRaises(Exception):
            pdb_info(request, self.cluster.id, "default", "pdb-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_pdb.get_pdb_description.assert_called_once()
        self.mock_k8s_pdb.get_pdb_events.assert_not_called()
        self.mock_k8s_pdb.get_pdb_yaml.assert_not_called()
        
class ConfigmapsTests(TestCase):
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
        self.patcher_k8s_configmaps = patch('dashboard.views.k8s_configmaps')
        self.mock_k8s_configmaps = self.patcher_k8s_configmaps.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_configmaps.stop()
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

    def test_configmaps_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_configmaps.get_configmaps.return_value = (
            [
                {"name": "cm-1", "namespace": "default"},
                {"name": "cm-2", "namespace": "kube-system"}
            ],
            2
        )
        request = self.factory.get(f'/dashboard/configmaps/{self.cluster.id}/')
        configmaps(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/config_secrets/configmaps.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["configmaps"], self.mock_k8s_configmaps.get_configmaps.return_value[0])
        self.assertEqual(context["total_count"], 2)
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_configmaps.get_configmaps.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_configmaps_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/configmaps/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            configmaps(request, self.cluster.id)
        self.mock_k8s_configmaps.get_configmaps.assert_not_called()
        self.mock_render.assert_not_called()

    def test_configmaps_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_configmaps.get_configmaps.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/configmaps/{self.cluster.id}/')
        with self.assertRaises(Exception):
            configmaps(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_configmaps.get_configmaps.assert_called_once()

    def test_configmap_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_configmaps.get_configmap_description.return_value = "configmap description"
        self.mock_k8s_configmaps.get_configmap_events.return_value = "configmap events"
        self.mock_k8s_configmaps.get_configmap_yaml.return_value = "configmap yaml"
        request = self.factory.get(f'/dashboard/configmap_info/{self.cluster.id}/default/configmap-1/')
        configmap_info(request, self.cluster.id, "default", "configmap-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/config_secrets/configmap_info.html')
        context = args[2]
        self.assertIn("configmap_info", context)
        self.assertEqual(context["configmap_info"]["describe"], "configmap description")
        self.assertEqual(context["configmap_info"]["events"], "configmap events")
        self.assertEqual(context["configmap_info"]["yaml"], "configmap yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["configmap_name"], "configmap-1")
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_configmaps.get_configmap_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "configmap-1"
        )
        self.mock_k8s_configmaps.get_configmap_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "configmap-1"
        )
        self.mock_k8s_configmaps.get_configmap_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "configmap-1"
        )

    def test_configmap_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/configmap_info/{self.cluster.id}/default/configmap-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            configmap_info(request, self.cluster.id, "default", "configmap-1")
        self.mock_k8s_configmaps.get_configmap_description.assert_not_called()
        self.mock_k8s_configmaps.get_configmap_events.assert_not_called()
        self.mock_k8s_configmaps.get_configmap_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_configmap_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_configmaps.get_configmap_description.side_effect = Exception("K8s error")
        self.mock_k8s_configmaps.get_configmap_events.side_effect = Exception("K8s error")
        self.mock_k8s_configmaps.get_configmap_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/configmap_info/{self.cluster.id}/default/configmap-1/')
        with self.assertRaises(Exception):
            configmap_info(request, self.cluster.id, "default", "configmap-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_configmaps.get_configmap_description.assert_called_once()
        self.mock_k8s_configmaps.get_configmap_events.assert_not_called()
        self.mock_k8s_configmaps.get_configmap_yaml.assert_not_called()
        
        
class SecretsTests(TestCase):
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
        self.patcher_k8s_secrets = patch('dashboard.views.k8s_secrets')
        self.mock_k8s_secrets = self.patcher_k8s_secrets.start()
        self.patcher_k8s_namespaces = patch('dashboard.views.k8s_namespaces')
        self.mock_k8s_namespaces = self.patcher_k8s_namespaces.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_secrets.stop()
        self.patcher_k8s_namespaces.stop()
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

    def test_secrets_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_namespaces.get_namespace.return_value = ['default', 'kube-system']
        self.mock_k8s_secrets.list_secrets.return_value = (
            [
                {"name": "secret-1", "namespace": "default"},
                {"name": "secret-2", "namespace": "kube-system"}
            ],
            2
        )
        request = self.factory.get(f'/dashboard/secrets/{self.cluster.id}/')
        secrets(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/config_secrets/secrets.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["secrets"], self.mock_k8s_secrets.list_secrets.return_value[0])
        self.assertEqual(context["total_secrets"], 2)
        self.assertEqual(context["namespaces"], self.mock_k8s_namespaces.get_namespace.return_value)
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_namespaces.get_namespace.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )
        self.mock_k8s_secrets.list_secrets.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_secrets_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/secrets/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            secrets(request, self.cluster.id)
        self.mock_k8s_secrets.list_secrets.assert_not_called()
        self.mock_render.assert_not_called()

    def test_secrets_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_namespaces.get_namespace.return_value = ['default']
        self.mock_k8s_secrets.list_secrets.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/secrets/{self.cluster.id}/')
        with self.assertRaises(Exception):
            secrets(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_secrets.list_secrets.assert_called_once()

    def test_secret_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_secrets.get_secret_description.return_value = "secret description"
        self.mock_k8s_secrets.get_secret_events.return_value = "secret events"
        self.mock_k8s_secrets.get_secret_yaml.return_value = "secret yaml"
        request = self.factory.get(f'/dashboard/secret_info/{self.cluster.id}/default/secret-1/')
        secret_info(request, self.cluster.id, "default", "secret-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/config_secrets/secret_info.html')
        context = args[2]
        self.assertIn("secret_info", context)
        self.assertEqual(context["secret_info"]["describe"], "secret description")
        self.assertEqual(context["secret_info"]["events"], "secret events")
        self.assertEqual(context["secret_info"]["yaml"], "secret yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["secret_name"], "secret-1")
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_secrets.get_secret_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "secret-1"
        )
        self.mock_k8s_secrets.get_secret_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "secret-1"
        )
        self.mock_k8s_secrets.get_secret_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "secret-1"
        )

    def test_secret_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/secret_info/{self.cluster.id}/default/secret-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            secret_info(request, self.cluster.id, "default", "secret-1")
        self.mock_k8s_secrets.get_secret_description.assert_not_called()
        self.mock_k8s_secrets.get_secret_events.assert_not_called()
        self.mock_k8s_secrets.get_secret_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_secret_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_secrets.get_secret_description.side_effect = Exception("K8s error")
        self.mock_k8s_secrets.get_secret_events.side_effect = Exception("K8s error")
        self.mock_k8s_secrets.get_secret_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/secret_info/{self.cluster.id}/default/secret-1/')
        with self.assertRaises(Exception):
            secret_info(request, self.cluster.id, "default", "secret-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_secrets.get_secret_description.assert_called_once()
        self.mock_k8s_secrets.get_secret_events.assert_not_called()
        self.mock_k8s_secrets.get_secret_yaml.assert_not_called()
        
        
class ServicesTests(TestCase):
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
        self.patcher_k8s_services = patch('dashboard.views.k8s_services')
        self.mock_k8s_services = self.patcher_k8s_services.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_services.stop()
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

    def test_services_successful_rendering(self):
        self._setup_utils_data()
        mock_services = [
            {"name": "svc-1", "namespace": "default"},
            {"name": "svc-2", "namespace": "kube-system"}
        ]
        self.mock_k8s_services.list_kubernetes_services.return_value = mock_services
        request = self.factory.get(f'/dashboard/services/{self.cluster.id}/')
        services(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/services/services.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["services"], mock_services)
        self.assertEqual(context["total_services"], 2)
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_services.list_kubernetes_services.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_services_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/services/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            services(request, self.cluster.id)
        self.mock_k8s_services.list_kubernetes_services.assert_not_called()
        self.mock_render.assert_not_called()

    def test_services_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_services.list_kubernetes_services.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/services/{self.cluster.id}/')
        with self.assertRaises(Exception):
            services(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_services.list_kubernetes_services.assert_called_once()

    def test_service_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_services.get_service_description.return_value = "service description"
        self.mock_k8s_services.get_service_events.return_value = "service events"
        self.mock_k8s_services.get_service_yaml.return_value = "service yaml"
        request = self.factory.get(f'/dashboard/service_info/{self.cluster.id}/default/svc-1/')
        service_info(request, self.cluster.id, "default", "svc-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/services/service_info.html')
        context = args[2]
        self.assertIn("service_info", context)
        self.assertEqual(context["service_info"]["describe"], "service description")
        self.assertEqual(context["service_info"]["events"], "service events")
        self.assertEqual(context["service_info"]["yaml"], "service yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["service_name"], "svc-1")
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_services.get_service_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "svc-1"
        )
        self.mock_k8s_services.get_service_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "svc-1"
        )
        self.mock_k8s_services.get_service_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "svc-1"
        )

    def test_service_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/service_info/{self.cluster.id}/default/svc-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            service_info(request, self.cluster.id, "default", "svc-1")
        self.mock_k8s_services.get_service_description.assert_not_called()
        self.mock_k8s_services.get_service_events.assert_not_called()
        self.mock_k8s_services.get_service_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_service_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_services.get_service_description.side_effect = Exception("K8s error")
        self.mock_k8s_services.get_service_events.side_effect = Exception("K8s error")
        self.mock_k8s_services.get_service_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/service_info/{self.cluster.id}/default/svc-1/')
        with self.assertRaises(Exception):
            service_info(request, self.cluster.id, "default", "svc-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_services.get_service_description.assert_called_once()
        self.mock_k8s_services.get_service_events.assert_not_called()
        self.mock_k8s_services.get_service_yaml.assert_not_called()


class EndpointsTests(TestCase):
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
        self.patcher_k8s_endpoints = patch('dashboard.views.k8s_endpoints')
        self.mock_k8s_endpoints = self.patcher_k8s_endpoints.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_endpoints.stop()
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

    def test_endpoints_successful_rendering(self):
        self._setup_utils_data()
        mock_endpoints = [
            {"name": "ep-1", "namespace": "default"},
            {"name": "ep-2", "namespace": "kube-system"}
        ]
        self.mock_k8s_endpoints.get_endpoints.return_value = mock_endpoints
        request = self.factory.get(f'/dashboard/endpoints/{self.cluster.id}/')
        endpoints(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/services/endpoints.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["endpoints"], mock_endpoints)
        self.assertEqual(context["total_endpoints"], 2)
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_endpoints.get_endpoints.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_endpoints_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/endpoints/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            endpoints(request, self.cluster.id)
        self.mock_k8s_endpoints.get_endpoints.assert_not_called()
        self.mock_render.assert_not_called()

    def test_endpoints_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_endpoints.get_endpoints.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/endpoints/{self.cluster.id}/')
        with self.assertRaises(Exception):
            endpoints(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_endpoints.get_endpoints.assert_called_once()

    def test_endpoint_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_endpoints.get_endpoint_description.return_value = "endpoint description"
        self.mock_k8s_endpoints.get_endpoint_events.return_value = "endpoint events"
        self.mock_k8s_endpoints.get_endpoint_yaml.return_value = "endpoint yaml"
        request = self.factory.get(f'/dashboard/endpoint_info/{self.cluster.id}/default/ep-1/')
        endpoint_info(request, self.cluster.id, "default", "ep-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/services/endpoint_info.html')
        context = args[2]
        self.assertIn("endpoint_info", context)
        self.assertEqual(context["endpoint_info"]["describe"], "endpoint description")
        self.assertEqual(context["endpoint_info"]["events"], "endpoint events")
        self.assertEqual(context["endpoint_info"]["yaml"], "endpoint yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["endpoint_name"], "ep-1")
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_endpoints.get_endpoint_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "ep-1"
        )
        self.mock_k8s_endpoints.get_endpoint_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "ep-1"
        )
        self.mock_k8s_endpoints.get_endpoint_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "ep-1"
        )

    def test_endpoint_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/endpoint_info/{self.cluster.id}/default/ep-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            endpoint_info(request, self.cluster.id, "default", "ep-1")
        self.mock_k8s_endpoints.get_endpoint_description.assert_not_called()
        self.mock_k8s_endpoints.get_endpoint_events.assert_not_called()
        self.mock_k8s_endpoints.get_endpoint_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_endpoint_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_endpoints.get_endpoint_description.side_effect = Exception("K8s error")
        self.mock_k8s_endpoints.get_endpoint_events.side_effect = Exception("K8s error")
        self.mock_k8s_endpoints.get_endpoint_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/endpoint_info/{self.cluster.id}/default/ep-1/')
        with self.assertRaises(Exception):
            endpoint_info(request, self.cluster.id, "default", "ep-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_endpoints.get_endpoint_description.assert_called_once()
        self.mock_k8s_endpoints.get_endpoint_events.assert_not_called()
        self.mock_k8s_endpoints.get_endpoint_yaml.assert_not_called()


class PersistentVolumeTests(TestCase):
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
        self.patcher_k8s_pv = patch('dashboard.views.k8s_pv')
        self.mock_k8s_pv = self.patcher_k8s_pv.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_pv.stop()
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

    def test_persistentvolume_successful_rendering(self):
        self._setup_utils_data()
        mock_pvs = [
            {"name": "pv-1", "capacity": "10Gi"},
            {"name": "pv-2", "capacity": "5Gi"}
        ]
        self.mock_k8s_pv.list_persistent_volumes.return_value = (mock_pvs, 2)
        request = self.factory.get(f'/dashboard/persistentvolume/{self.cluster.id}/')
        persistentvolume(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/persistent_storage/persistentvolume.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["pvs"], mock_pvs)
        self.assertEqual(context["total_pvs"], 2)
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_pv.list_persistent_volumes.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_persistentvolume_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/persistentvolume/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            persistentvolume(request, self.cluster.id)
        self.mock_k8s_pv.list_persistent_volumes.assert_not_called()
        self.mock_render.assert_not_called()

    def test_persistentvolume_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_pv.list_persistent_volumes.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/persistentvolume/{self.cluster.id}/')
        with self.assertRaises(Exception):
            persistentvolume(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_pv.list_persistent_volumes.assert_called_once()

    def test_pv_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_pv.get_pv_description.return_value = "PV description"
        self.mock_k8s_pv.get_pv_yaml.return_value = "PV yaml"
        request = self.factory.get(f'/dashboard/pv_info/{self.cluster.id}/pv-1/')
        pv_info(request, self.cluster.id, "pv-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/persistent_storage/pv_info.html')
        context = args[2]
        self.assertIn("pv_info", context)
        self.assertEqual(context["pv_info"]["describe"], "PV description")
        self.assertEqual(context["pv_info"]["yaml"], "PV yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["pv_name"], "pv-1")
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_pv.get_pv_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "pv-1"
        )
        self.mock_k8s_pv.get_pv_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "pv-1"
        )

    def test_pv_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/pv_info/{self.cluster.id}/pv-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            pv_info(request, self.cluster.id, "pv-1")
        self.mock_k8s_pv.get_pv_description.assert_not_called()
        self.mock_k8s_pv.get_pv_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_pv_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_pv.get_pv_description.side_effect = Exception("K8s error")
        self.mock_k8s_pv.get_pv_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/pv_info/{self.cluster.id}/pv-1/')
        with self.assertRaises(Exception):
            pv_info(request, self.cluster.id, "pv-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_pv.get_pv_description.assert_called_once()
        self.mock_k8s_pv.get_pv_yaml.assert_not_called()

class PersistentVolumeTests(TestCase):
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
        self.patcher_k8s_pv = patch('dashboard.views.k8s_pv')
        self.mock_k8s_pv = self.patcher_k8s_pv.start()
        self.patcher_k8s_pvc = patch('dashboard.views.k8s_pvc')
        self.mock_k8s_pvc = self.patcher_k8s_pvc.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_pv.stop()
        self.patcher_k8s_pvc.stop()
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

    def test_persistentvolume_successful_rendering(self):
        self._setup_utils_data()
        mock_pvs = [
            {"name": "pv-1", "capacity": "10Gi"},
            {"name": "pv-2", "capacity": "5Gi"}
        ]
        self.mock_k8s_pv.list_persistent_volumes.return_value = (mock_pvs, 2)
        request = self.factory.get(f'/dashboard/persistentvolume/{self.cluster.id}/')
        persistentvolume(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/persistent_storage/persistentvolume.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["pvs"], mock_pvs)
        self.assertEqual(context["total_pvs"], 2)
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_pv.list_persistent_volumes.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_persistentvolume_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/persistentvolume/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            persistentvolume(request, self.cluster.id)
        self.mock_k8s_pv.list_persistent_volumes.assert_not_called()
        self.mock_render.assert_not_called()

    def test_persistentvolume_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_pv.list_persistent_volumes.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/persistentvolume/{self.cluster.id}/')
        with self.assertRaises(Exception):
            persistentvolume(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_pv.list_persistent_volumes.assert_called_once()

    def test_pv_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_pv.get_pv_description.return_value = "PV description"
        self.mock_k8s_pv.get_pv_yaml.return_value = "PV yaml"
        request = self.factory.get(f'/dashboard/pv_info/{self.cluster.id}/pv-1/')
        pv_info(request, self.cluster.id, "pv-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/persistent_storage/pv_info.html')
        context = args[2]
        self.assertIn("pv_info", context)
        self.assertEqual(context["pv_info"]["describe"], "PV description")
        self.assertEqual(context["pv_info"]["yaml"], "PV yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["pv_name"], "pv-1")
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_pv.get_pv_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "pv-1"
        )
        self.mock_k8s_pv.get_pv_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "pv-1"
        )

    def test_pv_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/pv_info/{self.cluster.id}/pv-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            pv_info(request, self.cluster.id, "pv-1")
        self.mock_k8s_pv.get_pv_description.assert_not_called()
        self.mock_k8s_pv.get_pv_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_pv_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_pv.get_pv_description.side_effect = Exception("K8s error")
        self.mock_k8s_pv.get_pv_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/pv_info/{self.cluster.id}/pv-1/')
        with self.assertRaises(Exception):
            pv_info(request, self.cluster.id, "pv-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_pv.get_pv_description.assert_called_once()
        self.mock_k8s_pv.get_pv_yaml.assert_not_called()

    def test_persistentvolumeclaim_successful_rendering(self):
        self._setup_utils_data()
        mock_pvc = [
            {"name": "pvc-1", "namespace": "default"},
            {"name": "pvc-2", "namespace": "kube-system"}
        ]
        self.mock_k8s_pvc.list_pvc.return_value = (mock_pvc, 2)
        request = self.factory.get(f'/dashboard/persistentvolumeclaim/{self.cluster.id}/')
        persistentvolumeclaim(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/persistent_storage/persistentvolumeclaim.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["pvc"], mock_pvc)
        self.assertEqual(context["total_pvc"], 2)
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_pvc.list_pvc.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_persistentvolumeclaim_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/persistentvolumeclaim/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            persistentvolumeclaim(request, self.cluster.id)
        self.mock_k8s_pvc.list_pvc.assert_not_called()
        self.mock_render.assert_not_called()

    def test_persistentvolumeclaim_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_pvc.list_pvc.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/persistentvolumeclaim/{self.cluster.id}/')
        with self.assertRaises(Exception):
            persistentvolumeclaim(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_pvc.list_pvc.assert_called_once()

    def test_pvc_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_pvc.get_pvc_description.return_value = "PVC description"
        self.mock_k8s_pvc.get_pvc_events.return_value = "PVC events"
        self.mock_k8s_pvc.get_pvc_yaml.return_value = "PVC yaml"
        request = self.factory.get(f'/dashboard/pvc_info/{self.cluster.id}/default/pvc-1/')
        pvc_info(request, self.cluster.id, "default", "pvc-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/persistent_storage/pvc_info.html')
        context = args[2]
        self.assertIn("pvc_info", context)
        self.assertEqual(context["pvc_info"]["describe"], "PVC description")
        self.assertEqual(context["pvc_info"]["events"], "PVC events")
        self.assertEqual(context["pvc_info"]["yaml"], "PVC yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["pvc_name"], "pvc-1")
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_pvc.get_pvc_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "pvc-1"
        )
        self.mock_k8s_pvc.get_pvc_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "pvc-1"
        )
        self.mock_k8s_pvc.get_pvc_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "pvc-1"
        )

    def test_pvc_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/pvc_info/{self.cluster.id}/default/pvc-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            pvc_info(request, self.cluster.id, "default", "pvc-1")
        self.mock_k8s_pvc.get_pvc_description.assert_not_called()
        self.mock_k8s_pvc.get_pvc_events.assert_not_called()
        self.mock_k8s_pvc.get_pvc_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_pvc_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_pvc.get_pvc_description.side_effect = Exception("K8s error")
        self.mock_k8s_pvc.get_pvc_events.side_effect = Exception("K8s error")
        self.mock_k8s_pvc.get_pvc_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/pvc_info/{self.cluster.id}/default/pvc-1/')
        with self.assertRaises(Exception):
            pvc_info(request, self.cluster.id, "default", "pvc-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_pvc.get_pvc_description.assert_called_once()
        self.mock_k8s_pvc.get_pvc_events.assert_not_called()
        self.mock_k8s_pvc.get_pvc_yaml.assert_not_called()
        
class StorageClassViewsTests(TestCase):
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
        self.patcher_k8s_storage_class = patch('dashboard.views.k8s_storage_class')
        self.mock_k8s_storage_class = self.patcher_k8s_storage_class.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_storage_class.stop()
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

    def test_storageclass_successful_rendering(self):
        self._setup_utils_data()
        mock_sc = [
            {"name": "sc-1", "provisioner": "kubernetes.io/aws-ebs"},
            {"name": "sc-2", "provisioner": "kubernetes.io/gce-pd"}
        ]
        self.mock_k8s_storage_class.list_storage_classes.return_value = (mock_sc, 2)
        request = self.factory.get(f'/dashboard/storageclass/{self.cluster.id}/')
        storageclass(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/persistent_storage/storageclass.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["sc"], mock_sc)
        self.assertEqual(context["total_sc"], 2)
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_storage_class.list_storage_classes.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_storageclass_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/storageclass/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            storageclass(request, self.cluster.id)
        self.mock_k8s_storage_class.list_storage_classes.assert_not_called()
        self.mock_render.assert_not_called()

    def test_storageclass_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_storage_class.list_storage_classes.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/storageclass/{self.cluster.id}/')
        with self.assertRaises(Exception):
            storageclass(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_storage_class.list_storage_classes.assert_called_once()

    def test_storageclass_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_storage_class.get_storage_class_description.return_value = "SC description"
        self.mock_k8s_storage_class.get_storage_class_events.return_value = "SC events"
        self.mock_k8s_storage_class.get_sc_yaml.return_value = "SC yaml"
        request = self.factory.get(f'/dashboard/storageclass_info/{self.cluster.id}/sc-1/')
        storageclass_info(request, self.cluster.id, "sc-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/persistent_storage/storageclass_info.html')
        context = args[2]
        self.assertIn("sc_info", context)
        self.assertEqual(context["sc_info"]["describe"], "SC description")
        self.assertEqual(context["sc_info"]["events"], "SC events")
        self.assertEqual(context["sc_info"]["yaml"], "SC yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_storage_class.get_storage_class_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "sc-1"
        )
        self.mock_k8s_storage_class.get_storage_class_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "sc-1"
        )
        self.mock_k8s_storage_class.get_sc_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "sc-1"
        )

    def test_storageclass_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/storageclass_info/{self.cluster.id}/sc-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            storageclass_info(request, self.cluster.id, "sc-1")
        self.mock_k8s_storage_class.get_storage_class_description.assert_not_called()
        self.mock_k8s_storage_class.get_storage_class_events.assert_not_called()
        self.mock_k8s_storage_class.get_sc_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_storageclass_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_storage_class.get_storage_class_description.side_effect = Exception("K8s error")
        self.mock_k8s_storage_class.get_storage_class_events.side_effect = Exception("K8s error")
        self.mock_k8s_storage_class.get_sc_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/storageclass_info/{self.cluster.id}/sc-1/')
        with self.assertRaises(Exception):
            storageclass_info(request, self.cluster.id, "sc-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_storage_class.get_storage_class_description.assert_called_once()
        self.mock_k8s_storage_class.get_storage_class_events.assert_not_called()
        self.mock_k8s_storage_class.get_sc_yaml.assert_not_called()

class NetworkPolicyViewsTests(TestCase):
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
        self.patcher_k8s_np = patch('dashboard.views.k8s_np')
        self.mock_k8s_np = self.patcher_k8s_np.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_np.stop()
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

    def test_np_successful_rendering(self):
        self._setup_utils_data()
        mock_nps = [
            {"name": "np-1", "namespace": "default"},
            {"name": "np-2", "namespace": "kube-system"}
        ]
        self.mock_k8s_np.get_np.return_value = (mock_nps, 2)
        request = self.factory.get(f'/dashboard/np/{self.cluster.id}/')
        np(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/networking/np.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["nps"], mock_nps)
        self.assertEqual(context["nps_count"], 2)
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_np.get_np.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_np_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/np/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            np(request, self.cluster.id)
        self.mock_k8s_np.get_np.assert_not_called()
        self.mock_render.assert_not_called()

    def test_np_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_np.get_np.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/np/{self.cluster.id}/')
        with self.assertRaises(Exception):
            np(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_np.get_np.assert_called_once()

    def test_np_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_np.get_np_description.return_value = "NP description"
        self.mock_k8s_np.get_np_events.return_value = "NP events"
        self.mock_k8s_np.get_np_yaml.return_value = "NP yaml"
        request = self.factory.get(f'/dashboard/np_info/{self.cluster.id}/default/np-1/')
        np_info(request, self.cluster.id, "default", "np-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/networking/np_info.html')
        context = args[2]
        self.assertIn("np_info", context)
        self.assertEqual(context["np_info"]["describe"], "NP description")
        self.assertEqual(context["np_info"]["events"], "NP events")
        self.assertEqual(context["np_info"]["yaml"], "NP yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_np.get_np_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "np-1"
        )
        self.mock_k8s_np.get_np_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "np-1"
        )
        self.mock_k8s_np.get_np_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "np-1"
        )

    def test_np_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/np_info/{self.cluster.id}/default/np-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            np_info(request, self.cluster.id, "default", "np-1")
        self.mock_k8s_np.get_np_description.assert_not_called()
        self.mock_k8s_np.get_np_events.assert_not_called()
        self.mock_k8s_np.get_np_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_np_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_np.get_np_description.side_effect = Exception("K8s error")
        self.mock_k8s_np.get_np_events.side_effect = Exception("K8s error")
        self.mock_k8s_np.get_np_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/np_info/{self.cluster.id}/default/np-1/')
        with self.assertRaises(Exception):
            np_info(request, self.cluster.id, "default", "np-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_np.get_np_description.assert_called_once()
        self.mock_k8s_np.get_np_events.assert_not_called()
        self.mock_k8s_np.get_np_yaml.assert_not_called()
        
class IngressViewsTests(TestCase):
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
        self.patcher_k8s_ingress = patch('dashboard.views.k8s_ingress')
        self.mock_k8s_ingress = self.patcher_k8s_ingress.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_ingress.stop()
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

    def test_ingress_successful_rendering(self):
        self._setup_utils_data()
        mock_ingress = [
            {"name": "ingress-1", "namespace": "default"},
            {"name": "ingress-2", "namespace": "kube-system"}
        ]
        self.mock_k8s_ingress.get_ingress.return_value = (mock_ingress, 2)
        request = self.factory.get(f'/dashboard/ingress/{self.cluster.id}/')
        ingress(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/networking/ingress.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["ingress"], mock_ingress)
        self.assertEqual(context["ingress_count"], 2)
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_ingress.get_ingress.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_ingress_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/ingress/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            ingress(request, self.cluster.id)
        self.mock_k8s_ingress.get_ingress.assert_not_called()
        self.mock_render.assert_not_called()

    def test_ingress_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_ingress.get_ingress.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/ingress/{self.cluster.id}/')
        with self.assertRaises(Exception):
            ingress(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_ingress.get_ingress.assert_called_once()

    def test_ingress_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_ingress.get_ingress_description.return_value = "Ingress description"
        self.mock_k8s_ingress.get_ingress_events.return_value = "Ingress events"
        self.mock_k8s_ingress.get_ingress_yaml.return_value = "Ingress yaml"
        request = self.factory.get(f'/dashboard/ingress_info/{self.cluster.id}/default/ingress-1/')
        ingress_info(request, self.cluster.id, "default", "ingress-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/networking/ingress_info.html')
        context = args[2]
        self.assertIn("ingress_info", context)
        self.assertEqual(context["ingress_info"]["describe"], "Ingress description")
        self.assertEqual(context["ingress_info"]["events"], "Ingress events")
        self.assertEqual(context["ingress_info"]["yaml"], "Ingress yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_ingress.get_ingress_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "ingress-1"
        )
        self.mock_k8s_ingress.get_ingress_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "ingress-1"
        )
        self.mock_k8s_ingress.get_ingress_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "ingress-1"
        )

    def test_ingress_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/ingress_info/{self.cluster.id}/default/ingress-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            ingress_info(request, self.cluster.id, "default", "ingress-1")
        self.mock_k8s_ingress.get_ingress_description.assert_not_called()
        self.mock_k8s_ingress.get_ingress_events.assert_not_called()
        self.mock_k8s_ingress.get_ingress_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_ingress_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_ingress.get_ingress_description.side_effect = Exception("K8s error")
        self.mock_k8s_ingress.get_ingress_events.side_effect = Exception("K8s error")
        self.mock_k8s_ingress.get_ingress_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/ingress_info/{self.cluster.id}/default/ingress-1/')
        with self.assertRaises(Exception):
            ingress_info(request, self.cluster.id, "default", "ingress-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_ingress.get_ingress_description.assert_called_once()
        self.mock_k8s_ingress.get_ingress_events.assert_not_called()
        self.mock_k8s_ingress.get_ingress_yaml.assert_not_called()

class RoleViewsTests(TestCase):
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
        self.patcher_k8s_role = patch('dashboard.views.k8s_role')
        self.mock_k8s_role = self.patcher_k8s_role.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_role.stop()
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

    def test_role_successful_rendering(self):
        self._setup_utils_data()
        mock_roles = [
            {"name": "role-1", "namespace": "default"},
            {"name": "role-2", "namespace": "kube-system"}
        ]
        self.mock_k8s_role.list_roles.return_value = (mock_roles, 2)
        request = self.factory.get(f'/dashboard/role/{self.cluster.id}/')
        role(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/RBAC/role.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["role"], mock_roles)
        self.assertEqual(context["total_role"], 2)
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_role.list_roles.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_role_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/role/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            role(request, self.cluster.id)
        self.mock_k8s_role.list_roles.assert_not_called()
        self.mock_render.assert_not_called()

    def test_role_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_role.list_roles.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/role/{self.cluster.id}/')
        with self.assertRaises(Exception):
            role(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_role.list_roles.assert_called_once()

    def test_role_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_role.get_role_description.return_value = "Role description"
        self.mock_k8s_role.get_role_events.return_value = "Role events"
        self.mock_k8s_role.get_role_yaml.return_value = "Role yaml"
        request = self.factory.get(f'/dashboard/role_info/{self.cluster.id}/default/role-1/')
        role_info(request, self.cluster.id, "default", "role-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/RBAC/role_info.html')
        context = args[2]
        self.assertIn("role_info", context)
        self.assertEqual(context["role_info"]["describe"], "Role description")
        self.assertEqual(context["role_info"]["events"], "Role events")
        self.assertEqual(context["role_info"]["yaml"], "Role yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_role.get_role_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "role-1"
        )
        self.mock_k8s_role.get_role_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "role-1"
        )
        self.mock_k8s_role.get_role_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "role-1"
        )

    def test_role_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/role_info/{self.cluster.id}/default/role-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            role_info(request, self.cluster.id, "default", "role-1")
        self.mock_k8s_role.get_role_description.assert_not_called()
        self.mock_k8s_role.get_role_events.assert_not_called()
        self.mock_k8s_role.get_role_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_role_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_role.get_role_description.side_effect = Exception("K8s error")
        self.mock_k8s_role.get_role_events.side_effect = Exception("K8s error")
        self.mock_k8s_role.get_role_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/role_info/{self.cluster.id}/default/role-1/')
        with self.assertRaises(Exception):
            role_info(request, self.cluster.id, "default", "role-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_role.get_role_description.assert_called_once()
        self.mock_k8s_role.get_role_events.assert_not_called()
        self.mock_k8s_role.get_role_yaml.assert_not_called()
        
class RoleBindingViewsTests(TestCase):
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
        self.patcher_k8s_rolebindings = patch('dashboard.views.k8s_rolebindings')
        self.mock_k8s_rolebindings = self.patcher_k8s_rolebindings.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_rolebindings.stop()
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

    def test_rolebinding_successful_rendering(self):
        self._setup_utils_data()
        mock_rolebindings = [
            {"name": "rb-1", "namespace": "default"},
            {"name": "rb-2", "namespace": "kube-system"}
        ]
        self.mock_k8s_rolebindings.list_rolebindings.return_value = (mock_rolebindings, 2)
        request = self.factory.get(f'/dashboard/rolebinding/{self.cluster.id}/')
        rolebinding(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/RBAC/rolebinding.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["rolebinding"], mock_rolebindings)
        self.assertEqual(context["total_rolebinding"], 2)
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_rolebindings.list_rolebindings.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_rolebinding_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/rolebinding/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            rolebinding(request, self.cluster.id)
        self.mock_k8s_rolebindings.list_rolebindings.assert_not_called()
        self.mock_render.assert_not_called()

    def test_rolebinding_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_rolebindings.list_rolebindings.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/rolebinding/{self.cluster.id}/')
        with self.assertRaises(Exception):
            rolebinding(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_rolebindings.list_rolebindings.assert_called_once()

    def test_role_binding_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_rolebindings.get_role_binding_description.return_value = "RoleBinding description"
        self.mock_k8s_rolebindings.get_role_binding_events.return_value = "RoleBinding events"
        self.mock_k8s_rolebindings.get_role_binding_yaml.return_value = "RoleBinding yaml"
        request = self.factory.get(f'/dashboard/rolebinding_info/{self.cluster.id}/default/rb-1/')
        role_binding_info(request, self.cluster.id, "default", "rb-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/RBAC/rolebinding_info.html')
        context = args[2]
        self.assertIn("role_binding_info", context)
        self.assertEqual(context["role_binding_info"]["describe"], "RoleBinding description")
        self.assertEqual(context["role_binding_info"]["events"], "RoleBinding events")
        self.assertEqual(context["role_binding_info"]["yaml"], "RoleBinding yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_rolebindings.get_role_binding_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "rb-1"
        )
        self.mock_k8s_rolebindings.get_role_binding_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "rb-1"
        )
        self.mock_k8s_rolebindings.get_role_binding_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "rb-1"
        )

    def test_role_binding_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/rolebinding_info/{self.cluster.id}/default/rb-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            role_binding_info(request, self.cluster.id, "default", "rb-1")
        self.mock_k8s_rolebindings.get_role_binding_description.assert_not_called()
        self.mock_k8s_rolebindings.get_role_binding_events.assert_not_called()
        self.mock_k8s_rolebindings.get_role_binding_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_role_binding_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_rolebindings.get_role_binding_description.side_effect = Exception("K8s error")
        self.mock_k8s_rolebindings.get_role_binding_events.side_effect = Exception("K8s error")
        self.mock_k8s_rolebindings.get_role_binding_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/rolebinding_info/{self.cluster.id}/default/rb-1/')
        with self.assertRaises(Exception):
            role_binding_info(request, self.cluster.id, "default", "rb-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_rolebindings.get_role_binding_description.assert_called_once()
        self.mock_k8s_rolebindings.get_role_binding_events.assert_not_called()
        self.mock_k8s_rolebindings.get_role_binding_yaml.assert_not_called()

class RoleBindingViewsTests(TestCase):
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
        self.patcher_k8s_rolebindings = patch('dashboard.views.k8s_rolebindings')
        self.mock_k8s_rolebindings = self.patcher_k8s_rolebindings.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_rolebindings.stop()
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

    def test_rolebinding_successful_rendering(self):
        self._setup_utils_data()
        mock_rolebindings = [
            {"name": "rb-1", "namespace": "default"},
            {"name": "rb-2", "namespace": "kube-system"}
        ]
        self.mock_k8s_rolebindings.list_rolebindings.return_value = (mock_rolebindings, 2)
        request = self.factory.get(f'/dashboard/rolebinding/{self.cluster.id}/')
        rolebinding(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/RBAC/rolebinding.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["rolebinding"], mock_rolebindings)
        self.assertEqual(context["total_rolebinding"], 2)
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_rolebindings.list_rolebindings.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_rolebinding_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/rolebinding/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            rolebinding(request, self.cluster.id)
        self.mock_k8s_rolebindings.list_rolebindings.assert_not_called()
        self.mock_render.assert_not_called()

    def test_rolebinding_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_rolebindings.list_rolebindings.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/rolebinding/{self.cluster.id}/')
        with self.assertRaises(Exception):
            rolebinding(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_rolebindings.list_rolebindings.assert_called_once()

    def test_role_binding_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_rolebindings.get_role_binding_description.return_value = "RoleBinding description"
        self.mock_k8s_rolebindings.get_role_binding_events.return_value = "RoleBinding events"
        self.mock_k8s_rolebindings.get_role_binding_yaml.return_value = "RoleBinding yaml"
        request = self.factory.get(f'/dashboard/rolebinding_info/{self.cluster.id}/default/rb-1/')
        role_binding_info(request, self.cluster.id, "default", "rb-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/RBAC/rolebinding_info.html')
        context = args[2]
        self.assertIn("role_binding_info", context)
        self.assertEqual(context["role_binding_info"]["describe"], "RoleBinding description")
        self.assertEqual(context["role_binding_info"]["events"], "RoleBinding events")
        self.assertEqual(context["role_binding_info"]["yaml"], "RoleBinding yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_rolebindings.get_role_binding_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "rb-1"
        )
        self.mock_k8s_rolebindings.get_role_binding_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "rb-1"
        )
        self.mock_k8s_rolebindings.get_role_binding_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "rb-1"
        )

    def test_role_binding_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/rolebinding_info/{self.cluster.id}/default/rb-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            role_binding_info(request, self.cluster.id, "default", "rb-1")
        self.mock_k8s_rolebindings.get_role_binding_description.assert_not_called()
        self.mock_k8s_rolebindings.get_role_binding_events.assert_not_called()
        self.mock_k8s_rolebindings.get_role_binding_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_role_binding_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_rolebindings.get_role_binding_description.side_effect = Exception("K8s error")
        self.mock_k8s_rolebindings.get_role_binding_events.side_effect = Exception("K8s error")
        self.mock_k8s_rolebindings.get_role_binding_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/rolebinding_info/{self.cluster.id}/default/rb-1/')
        with self.assertRaises(Exception):
            role_binding_info(request, self.cluster.id, "default", "rb-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_rolebindings.get_role_binding_description.assert_called_once()
        self.mock_k8s_rolebindings.get_role_binding_events.assert_not_called()
        self.mock_k8s_rolebindings.get_role_binding_yaml.assert_not_called()

class ClusterRoleViewsTests(TestCase):
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
        self.patcher_k8s_cluster_roles = patch('dashboard.views.k8s_cluster_roles')
        self.mock_k8s_cluster_roles = self.patcher_k8s_cluster_roles.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_cluster_roles.stop()
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

    def test_clusterrole_successful_rendering(self):
        self._setup_utils_data()
        mock_clusterroles = [
            {"name": "cr-1"},
            {"name": "cr-2"}
        ]
        self.mock_k8s_cluster_roles.get_cluster_role.return_value = (mock_clusterroles, 2)
        request = self.factory.get(f'/dashboard/clusterrole/{self.cluster.id}/')
        clusterrole(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/RBAC/clusterrole.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["clusterrole"], mock_clusterroles)
        self.assertEqual(context["total_clusterrole"], 2)
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_cluster_roles.get_cluster_role.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_clusterrole_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/clusterrole/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            clusterrole(request, self.cluster.id)
        self.mock_k8s_cluster_roles.get_cluster_role.assert_not_called()
        self.mock_render.assert_not_called()

    def test_clusterrole_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_cluster_roles.get_cluster_role.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/clusterrole/{self.cluster.id}/')
        with self.assertRaises(Exception):
            clusterrole(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_cluster_roles.get_cluster_role.assert_called_once()

    def test_clusterrole_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_cluster_roles.get_cluster_role_description.return_value = "ClusterRole description"
        self.mock_k8s_cluster_roles.get_cluster_role_events.return_value = "ClusterRole events"
        self.mock_k8s_cluster_roles.get_cluster_role_yaml.return_value = "ClusterRole yaml"
        request = self.factory.get(f'/dashboard/clusterrole_info/{self.cluster.id}/cr-1/')
        clusterrole_info(request, self.cluster.id, "cr-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/RBAC/clusterrole_info.html')
        context = args[2]
        self.assertIn("cluster_role_info", context)
        self.assertEqual(context["cluster_role_info"]["describe"], "ClusterRole description")
        self.assertEqual(context["cluster_role_info"]["events"], "ClusterRole events")
        self.assertEqual(context["cluster_role_info"]["yaml"], "ClusterRole yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_cluster_roles.get_cluster_role_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "cr-1"
        )
        self.mock_k8s_cluster_roles.get_cluster_role_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "cr-1"
        )
        self.mock_k8s_cluster_roles.get_cluster_role_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "cr-1"
        )

    def test_clusterrole_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/clusterrole_info/{self.cluster.id}/cr-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            clusterrole_info(request, self.cluster.id, "cr-1")
        self.mock_k8s_cluster_roles.get_cluster_role_description.assert_not_called()
        self.mock_k8s_cluster_roles.get_cluster_role_events.assert_not_called()
        self.mock_k8s_cluster_roles.get_cluster_role_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_clusterrole_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_cluster_roles.get_cluster_role_description.side_effect = Exception("K8s error")
        self.mock_k8s_cluster_roles.get_cluster_role_events.side_effect = Exception("K8s error")
        self.mock_k8s_cluster_roles.get_cluster_role_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/clusterrole_info/{self.cluster.id}/cr-1/')
        with self.assertRaises(Exception):
            clusterrole_info(request, self.cluster.id, "cr-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_cluster_roles.get_cluster_role_description.assert_called_once()
        self.mock_k8s_cluster_roles.get_cluster_role_events.assert_not_called()
        self.mock_k8s_cluster_roles.get_cluster_role_yaml.assert_not_called()

class ClusterRoleBindingViewsTests(TestCase):
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
        self.patcher_k8s_cluster_role_bindings = patch('dashboard.views.k8s_cluster_role_bindings')
        self.mock_k8s_cluster_role_bindings = self.patcher_k8s_cluster_role_bindings.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_cluster_role_bindings.stop()
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

    def test_clusterrolebinding_successful_rendering(self):
        self._setup_utils_data()
        mock_clusterrolebindings = [
            {"name": "crb-1"},
            {"name": "crb-2"}
        ]
        self.mock_k8s_cluster_role_bindings.get_cluster_role_bindings.return_value = (mock_clusterrolebindings, 2)
        request = self.factory.get(f'/dashboard/clusterrolebinding/{self.cluster.id}/')
        clusterrolebinding(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/RBAC/clusterrolebinding.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["clusterrolebinding"], mock_clusterrolebindings)
        self.assertEqual(context["total_clusterrolebinding"], 2)
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_cluster_role_bindings.get_cluster_role_bindings.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_clusterrolebinding_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/clusterrolebinding/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            clusterrolebinding(request, self.cluster.id)
        self.mock_k8s_cluster_role_bindings.get_cluster_role_bindings.assert_not_called()
        self.mock_render.assert_not_called()

    def test_clusterrolebinding_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_cluster_role_bindings.get_cluster_role_bindings.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/clusterrolebinding/{self.cluster.id}/')
        with self.assertRaises(Exception):
            clusterrolebinding(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_cluster_role_bindings.get_cluster_role_bindings.assert_called_once()

    def test_cluster_role_binding_info_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_cluster_role_bindings.get_cluster_role_binding_description.return_value = "ClusterRoleBinding description"
        self.mock_k8s_cluster_role_bindings.get_cluster_role_binding_events.return_value = "ClusterRoleBinding events"
        self.mock_k8s_cluster_role_bindings.get_cluster_role_binding_yaml.return_value = "ClusterRoleBinding yaml"
        request = self.factory.get(f'/dashboard/clusterrolebinding_info/{self.cluster.id}/crb-1/')
        cluster_role_binding_info(request, self.cluster.id, "crb-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/RBAC/clusterrolebinding_info.html')
        context = args[2]
        self.assertIn("cluster_role_binding_info", context)
        self.assertEqual(context["cluster_role_binding_info"]["describe"], "ClusterRoleBinding description")
        self.assertEqual(context["cluster_role_binding_info"]["events"], "ClusterRoleBinding events")
        self.assertEqual(context["cluster_role_binding_info"]["yaml"], "ClusterRoleBinding yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_cluster_role_bindings.get_cluster_role_binding_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "crb-1"
        )
        self.mock_k8s_cluster_role_bindings.get_cluster_role_binding_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "crb-1"
        )
        self.mock_k8s_cluster_role_bindings.get_cluster_role_binding_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "crb-1"
        )

    def test_cluster_role_binding_info_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/clusterrolebinding_info/{self.cluster.id}/crb-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            cluster_role_binding_info(request, self.cluster.id, "crb-1")
        self.mock_k8s_cluster_role_bindings.get_cluster_role_binding_description.assert_not_called()
        self.mock_k8s_cluster_role_bindings.get_cluster_role_binding_events.assert_not_called()
        self.mock_k8s_cluster_role_bindings.get_cluster_role_binding_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_cluster_role_binding_info_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_cluster_role_bindings.get_cluster_role_binding_description.side_effect = Exception("K8s error")
        self.mock_k8s_cluster_role_bindings.get_cluster_role_binding_events.side_effect = Exception("K8s error")
        self.mock_k8s_cluster_role_bindings.get_cluster_role_binding_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/clusterrolebinding_info/{self.cluster.id}/crb-1/')
        with self.assertRaises(Exception):
            cluster_role_binding_info(request, self.cluster.id, "crb-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_cluster_role_bindings.get_cluster_role_binding_description.assert_called_once()
        self.mock_k8s_cluster_role_bindings.get_cluster_role_binding_events.assert_not_called()
        self.mock_k8s_cluster_role_bindings.get_cluster_role_binding_yaml.assert_not_called()
        
class ServiceAccountViewsTests(TestCase):
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
        self.patcher_k8s_service_accounts = patch('dashboard.views.k8s_service_accounts')
        self.mock_k8s_service_accounts = self.patcher_k8s_service_accounts.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_service_accounts.stop()
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

    def test_serviceAccount_successful_rendering(self):
        self._setup_utils_data()
        mock_service_accounts = [
            {"name": "sa-1", "namespace": "default"},
            {"name": "sa-2", "namespace": "kube-system"}
        ]
        self.mock_k8s_service_accounts.get_service_accounts.return_value = (mock_service_accounts, 2)
        request = self.factory.get(f'/dashboard/serviceAccount/{self.cluster.id}/')
        serviceAccount(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/RBAC/serviceAccount.html')
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["serviceAccount"], mock_service_accounts)
        self.assertEqual(context["total_serviceAccount"], 2)
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_service_accounts.get_service_accounts.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_serviceAccount_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/serviceAccount/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            serviceAccount(request, self.cluster.id)
        self.mock_k8s_service_accounts.get_service_accounts.assert_not_called()
        self.mock_render.assert_not_called()

    def test_serviceAccount_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_service_accounts.get_service_accounts.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/serviceAccount/{self.cluster.id}/')
        with self.assertRaises(Exception):
            serviceAccount(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_service_accounts.get_service_accounts.assert_called_once()

    def test_serviceAccountInfo_successful_rendering(self):
        self._setup_utils_data()
        self.mock_k8s_service_accounts.get_sa_description.return_value = "SA description"
        self.mock_k8s_service_accounts.get_sa_events.return_value = "SA events"
        self.mock_k8s_service_accounts.get_sa_yaml.return_value = "SA yaml"
        request = self.factory.get(f'/dashboard/serviceAccountInfo/{self.cluster.id}/default/sa-1/')
        serviceAccountInfo(request, self.cluster.id, "default", "sa-1")
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        self.assertEqual(args[0], request)
        self.assertEqual(args[1], 'dashboard/RBAC/serviceAccountInfo.html')
        context = args[2]
        self.assertIn("serviceAccountInfo", context)
        self.assertEqual(context["serviceAccountInfo"]["describe"], "SA description")
        self.assertEqual(context["serviceAccountInfo"]["events"], "SA events")
        self.assertEqual(context["serviceAccountInfo"]["yaml"], "SA yaml")
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_service_accounts.get_sa_description.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "sa-1"
        )
        self.mock_k8s_service_accounts.get_sa_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "sa-1"
        )
        self.mock_k8s_service_accounts.get_sa_yaml.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, "default", "sa-1"
        )

    def test_serviceAccountInfo_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/serviceAccountInfo/{self.cluster.id}/default/sa-1/')
        with self.assertRaises(Cluster.DoesNotExist):
            serviceAccountInfo(request, self.cluster.id, "default", "sa-1")
        self.mock_k8s_service_accounts.get_sa_description.assert_not_called()
        self.mock_k8s_service_accounts.get_sa_events.assert_not_called()
        self.mock_k8s_service_accounts.get_sa_yaml.assert_not_called()
        self.mock_render.assert_not_called()

    def test_serviceAccountInfo_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_service_accounts.get_sa_description.side_effect = Exception("K8s error")
        self.mock_k8s_service_accounts.get_sa_events.side_effect = Exception("K8s error")
        self.mock_k8s_service_accounts.get_sa_yaml.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/serviceAccountInfo/{self.cluster.id}/default/sa-1/')
        with self.assertRaises(Exception):
            serviceAccountInfo(request, self.cluster.id, "default", "sa-1")
        self.mock_render.assert_not_called()
        self.mock_k8s_service_accounts.get_sa_description.assert_called_once()
        self.mock_k8s_service_accounts.get_sa_events.assert_not_called()
        self.mock_k8s_service_accounts.get_sa_yaml.assert_not_called()
        
class PodMetricsViewTests(TestCase):
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
        self.patcher_k8s_pod_metrics = patch('dashboard.views.k8s_pod_metrics')
        self.mock_k8s_pod_metrics = self.patcher_k8s_pod_metrics.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_pod_metrics.stop()
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

    def test_pod_metrics_successful_new_format(self):
        self._setup_utils_data()
        pod_metrics_data = [
            {"name": "pod-1", "cpu": "10m", "memory": "20Mi"},
            {"name": "pod-2", "cpu": "5m", "memory": "10Mi"}
        ]
        self.mock_k8s_pod_metrics.get_pod_metrics.return_value = (pod_metrics_data, 2, True)
        request = self.factory.get(f'/dashboard/pod_metrics/{self.cluster.id}/')
        pod_metrics(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        context = args[2]
        self.assertEqual(context["all_pod_metrics"], pod_metrics_data)
        self.assertEqual(context["total_pods"], 2)
        self.assertTrue(context["metrics_available"])
        self.assertIsNone(context["error_message"])
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_pod_metrics.get_pod_metrics.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_pod_metrics_successful_old_format(self):
        self._setup_utils_data()
        pod_metrics_data = [
            {"name": "pod-1", "cpu": "10m", "memory": "20Mi"}
        ]
        self.mock_k8s_pod_metrics.get_pod_metrics.return_value = (pod_metrics_data, 1)
        request = self.factory.get(f'/dashboard/pod_metrics/{self.cluster.id}/')
        pod_metrics(request, self.cluster.id)
        context = self.mock_render.call_args[0][2]
        self.assertEqual(context["all_pod_metrics"], pod_metrics_data)
        self.assertEqual(context["total_pods"], 1)
        self.assertTrue(context["metrics_available"])
        self.assertIsNone(context["error_message"])

    def test_pod_metrics_error_in_metrics(self):
        self._setup_utils_data()
        error_dict = {"error": "Metrics server not available"}
        self.mock_k8s_pod_metrics.get_pod_metrics.return_value = (error_dict, 0, False)
        request = self.factory.get(f'/dashboard/pod_metrics/{self.cluster.id}/')
        pod_metrics(request, self.cluster.id)
        context = self.mock_render.call_args[0][2]
        self.assertEqual(context["all_pod_metrics"], [])
        self.assertEqual(context["total_pods"], 0)
        self.assertFalse(context["metrics_available"])
        self.assertEqual(context["error_message"], "Metrics server not available")

    def test_pod_metrics_error_in_old_format(self):
        self._setup_utils_data()
        error_dict = {"error": "Metrics server not available"}
        self.mock_k8s_pod_metrics.get_pod_metrics.return_value = (error_dict, 0)
        request = self.factory.get(f'/dashboard/pod_metrics/{self.cluster.id}/')
        pod_metrics(request, self.cluster.id)
        context = self.mock_render.call_args[0][2]
        self.assertEqual(context["all_pod_metrics"], [])
        self.assertEqual(context["total_pods"], 0)
        self.assertFalse(context["metrics_available"])
        self.assertEqual(context["error_message"], "Metrics server not available")

    def test_pod_metrics_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/pod_metrics/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            pod_metrics(request, self.cluster.id)
        self.mock_k8s_pod_metrics.get_pod_metrics.assert_not_called()
        self.mock_render.assert_not_called()

    def test_pod_metrics_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_pod_metrics.get_pod_metrics.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/pod_metrics/{self.cluster.id}/')
        with self.assertRaises(Exception):
            pod_metrics(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_pod_metrics.get_pod_metrics.assert_called_once()

class NodeMetricsViewTests(TestCase):
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
        self.patcher_k8s_node_metrics = patch('dashboard.views.k8s_node_metrics')
        self.mock_k8s_node_metrics = self.patcher_k8s_node_metrics.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()

    def tearDown(self):
        self.patcher_k8s_node_metrics.stop()
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

    def test_node_metrics_successful_new_format(self):
        self._setup_utils_data()
        node_metrics_data = [
            {"name": "node-1", "cpu": "100m", "memory": "200Mi"},
            {"name": "node-2", "cpu": "50m", "memory": "100Mi"}
        ]
        self.mock_k8s_node_metrics.get_node_metrics.return_value = (node_metrics_data, 2, True)
        request = self.factory.get(f'/dashboard/node_metrics/{self.cluster.id}/')
        node_metrics(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        context = args[2]
        self.assertEqual(context["node_metrics"], node_metrics_data)
        self.assertEqual(context["total_nodes"], 2)
        self.assertTrue(context["metrics_available"])
        self.assertIsNone(context["error_message"])
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_node_metrics.get_node_metrics.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name
        )

    def test_node_metrics_successful_old_format(self):
        self._setup_utils_data()
        node_metrics_data = [
            {"name": "node-1", "cpu": "100m", "memory": "200Mi"}
        ]
        self.mock_k8s_node_metrics.get_node_metrics.return_value = (node_metrics_data, 1)
        request = self.factory.get(f'/dashboard/node_metrics/{self.cluster.id}/')
        node_metrics(request, self.cluster.id)
        context = self.mock_render.call_args[0][2]
        self.assertEqual(context["node_metrics"], node_metrics_data)
        self.assertEqual(context["total_nodes"], 1)
        self.assertTrue(context["metrics_available"])
        self.assertIsNone(context["error_message"])

    def test_node_metrics_error_in_metrics(self):
        self._setup_utils_data()
        error_dict = {"error": "Metrics server not available"}
        self.mock_k8s_node_metrics.get_node_metrics.return_value = (error_dict, 0, False)
        request = self.factory.get(f'/dashboard/node_metrics/{self.cluster.id}/')
        node_metrics(request, self.cluster.id)
        context = self.mock_render.call_args[0][2]
        self.assertEqual(context["node_metrics"], [])
        self.assertEqual(context["total_nodes"], 0)
        self.assertFalse(context["metrics_available"])
        self.assertEqual(context["error_message"], "Metrics server not available")

    def test_node_metrics_error_in_old_format(self):
        self._setup_utils_data()
        error_dict = {"error": "Metrics server not available"}
        self.mock_k8s_node_metrics.get_node_metrics.return_value = (error_dict, 0)
        request = self.factory.get(f'/dashboard/node_metrics/{self.cluster.id}/')
        node_metrics(request, self.cluster.id)
        context = self.mock_render.call_args[0][2]
        self.assertEqual(context["node_metrics"], [])
        self.assertEqual(context["total_nodes"], 0)
        self.assertFalse(context["metrics_available"])
        self.assertEqual(context["error_message"], "Metrics server not available")

    def test_node_metrics_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/node_metrics/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            node_metrics(request, self.cluster.id)
        self.mock_k8s_node_metrics.get_node_metrics.assert_not_called()
        self.mock_render.assert_not_called()

    def test_node_metrics_k8s_api_failure(self):
        self._setup_utils_data()
        self.mock_k8s_node_metrics.get_node_metrics.side_effect = Exception("K8s error")
        request = self.factory.get(f'/dashboard/node_metrics/{self.cluster.id}/')
        with self.assertRaises(Exception):
            node_metrics(request, self.cluster.id)
        self.mock_render.assert_not_called()
        self.mock_k8s_node_metrics.get_node_metrics.assert_called_once()
        
        
class EventsViewTests(TestCase):
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
        self.patcher_k8s_events = patch('dashboard.views.k8s_events')
        self.mock_k8s_events = self.patcher_k8s_events.start()
        self.patcher_get_utils_data = patch('dashboard.views.get_utils_data')
        self.mock_get_utils_data = self.patcher_get_utils_data.start()
        self.patcher_render = patch('dashboard.views.render')
        self.mock_render = self.patcher_render.start()
        self.patcher_paginator = patch('dashboard.views.Paginator')
        self.mock_paginator = self.patcher_paginator.start()
        self.patcher_page_not_an_integer = patch('dashboard.views.PageNotAnInteger', Exception)
        self.mock_page_not_an_integer = self.patcher_page_not_an_integer.start()
        self.patcher_empty_page = patch('dashboard.views.EmptyPage', Exception)
        self.mock_empty_page = self.patcher_empty_page.start()

    def tearDown(self):
        self.patcher_k8s_events.stop()
        self.patcher_get_utils_data.stop()
        self.patcher_render.stop()
        self.patcher_paginator.stop()
        self.patcher_page_not_an_integer.stop()
        self.patcher_empty_page.stop()

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

    def test_events_successful_rendering(self):
        self._setup_utils_data()
        mock_events = [{"type": "Normal", "message": "Pod started"} for _ in range(10)]
        self.mock_k8s_events.get_events.return_value = mock_events
        mock_page_obj = MagicMock()
        self.mock_paginator.return_value.page.return_value = mock_page_obj
        request = self.factory.get(f'/dashboard/events/{self.cluster.id}/', {'page': 1})
        events(request, self.cluster.id)
        self.mock_render.assert_called_once()
        args, kwargs = self.mock_render.call_args
        context = args[2]
        self.assertEqual(context["cluster_id"], str(self.cluster.id))
        self.assertEqual(context["events"], mock_page_obj)
        self.assertEqual(context["registered_clusters"], self.mock_get_utils_data.return_value[3])
        self.assertEqual(context["namespaces"], self.mock_get_utils_data.return_value[4])
        self.assertEqual(context["page_obj"], mock_page_obj)
        self.assertEqual(context["current_cluster"], self.mock_get_utils_data.return_value[1])
        self.mock_get_utils_data.assert_called_once_with(request)
        self.mock_k8s_events.get_events.assert_called_once_with(
            self.kube_config_entry.path, self.cluster.context_name, False
        )
        self.mock_paginator.assert_called_once_with(mock_events, 50)
        self.mock_paginator.return_value.page.assert_called_once_with('1')

    def test_events_non_list_events(self):
        self._setup_utils_data()
        self.mock_k8s_events.get_events.return_value = None
        mock_page_obj = MagicMock()
        self.mock_paginator.return_value.page.return_value = mock_page_obj
        request = self.factory.get(f'/dashboard/events/{self.cluster.id}/', {'page': 1})
        events(request, self.cluster.id)
        self.mock_paginator.assert_called_once_with([], 50)
        self.mock_render.assert_called_once()

    def test_events_page_not_an_integer(self):
        self._setup_utils_data()
        self.mock_k8s_events.get_events.return_value = [{"type": "Normal"}]
        mock_page_obj = MagicMock()
        paginator_instance = self.mock_paginator.return_value
        paginator_instance.page.side_effect = [Exception, mock_page_obj]
        request = self.factory.get(f'/dashboard/events/{self.cluster.id}/', {'page': 'notanint'})
        events(request, self.cluster.id)
        self.mock_render.assert_called_once()
        self.assertEqual(self.mock_render.call_args[0][2]["events"], mock_page_obj)

    def test_events_get_utils_data_failure(self):
        self.mock_get_utils_data.side_effect = Cluster.DoesNotExist("Cluster not found")
        request = self.factory.get(f'/dashboard/events/{self.cluster.id}/')
        with self.assertRaises(Cluster.DoesNotExist):
            events(request, self.cluster.id)
        self.mock_k8s_events.get_events.assert_not_called()
        self.mock_render.assert_not_called()


# Define current_working_directory at module level for patching in tests
current_working_directory = None

class ExecuteCommandViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        # Patch global current_working_directory for each test
        patcher = patch(__name__ + '.current_working_directory', os.getcwd())
        self.addCleanup(patcher.stop)
        self.mock_cwd = patcher.start()

    @patch('os.path.isdir')
    @patch('os.path.abspath')
    @patch('os.path.expanduser')
    def test_cd_command_changes_directory(self, mock_expanduser, mock_abspath, mock_isdir):
        mock_expanduser.side_effect = lambda x: x
        mock_abspath.side_effect = lambda x: x
        mock_isdir.return_value = True

        request = self.factory.post('/execute_command/', content_type='application/json',
                                    data='{"command": "cd testdir"}')
        response = execute_command(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Changed directory to", json.loads(response.content)['output'])

    @patch('os.path.isdir')
    @patch('os.path.abspath')
    @patch('os.path.expanduser')
    def test_cd_command_directory_not_found(self, mock_expanduser, mock_abspath, mock_isdir):
        mock_expanduser.side_effect = lambda x: x
        mock_abspath.side_effect = lambda x: x
        mock_isdir.return_value = False

        request = self.factory.post('/execute_command/', content_type='application/json',
                                    data='{"command": "cd notfound"}')
        response = execute_command(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Error: Directory not found", json.loads(response.content)['output'])

    @patch('os.path.expanduser')
    @patch('os.path.abspath')
    @patch('os.path.isdir')
    def test_cd_without_argument_goes_home(self, mock_isdir, mock_abspath, mock_expanduser):
        mock_expanduser.return_value = '/home/testuser'
        mock_abspath.return_value = '/home/testuser'
        mock_isdir.return_value = True

        request = self.factory.post('/execute_command/', content_type='application/json',
                                    data='{"command": "cd"}')
        response = execute_command(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Changed directory to", json.loads(response.content)['output'])

    @patch('subprocess.run')
    @patch('os.name', 'posix')
    def test_execute_shell_command_unix(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "file1\nfile2\n"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        request = self.factory.post('/execute_command/', content_type='application/json',
                                    data='{"command": "ls"}')
        response = execute_command(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['output'], "file1\nfile2\n")

    @patch('subprocess.run')
    @patch('os.name', 'nt')
    def test_execute_shell_command_windows(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = " Volume in drive C is Windows\n"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        request = self.factory.post('/execute_command/', content_type='application/json',
                                    data='{"command": "ls"}')
        response = execute_command(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Volume in drive", json.loads(response.content)['output'])

    @patch('subprocess.run')
    def test_command_error(self, mock_subprocess_run):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error: command not found"
        mock_subprocess_run.return_value = mock_result

        request = self.factory.post('/execute_command/', content_type='application/json',
                                    data='{"command": "badcommand"}')
        response = execute_command(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Error: command not found", json.loads(response.content)['output'])

    def test_non_post_method(self):

        request = self.factory.get('/execute_command/')
        response = execute_command(request)
        self.assertIsNone(response)
        # Should not execute anything, so response should be None