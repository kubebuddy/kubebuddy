from unittest import TestCase
from unittest.mock import patch, MagicMock

from .src.workloads.k8s_cronjobs import (
    getCronJobCount, getCronJobsStatus, getCronJobsList,
    get_cronjob_description, get_cronjob_events, get_yaml_cronjob
)
from .src.workloads.k8s_daemonset import (
    getDaemonsetStatus, getDaemonsetList, get_daemonset_description,
    get_daemonset_events, get_daemonset_yaml
)
from dashboard.src.workloads.k8s_deployments import (
    getDeploymentsInfo, getDeploymentsStatus, get_deployment_description,
    get_deploy_events, get_yaml_deploy, get_deployment_details
)
from dashboard.src.workloads.k8s_jobs import (
    getJobsStatus, getJobsList,
    get_job_description, get_job_events, get_yaml_job, get_job_details
)
from dashboard.src.workloads.k8s_pods import (
    getpods, getPodsStatus, getPodStatus, get_pod_info, get_pod_description,
    get_pod_logs, get_pod_events, get_pod_yaml, get_pod_details
)
from datetime import datetime, timezone, timedelta
import yaml
from kubernetes import client

class TestCronJobFunctions(TestCase):

    @patch('dashboard.src.workloads.k8s_cronjobs.config.load_kube_config')
    @patch('dashboard.src.workloads.k8s_cronjobs.client.BatchV1Api')
    def test_get_cronjob_count(self, mock_batch_api, mock_config):
        mock_batch_api.return_value.list_cron_job_for_all_namespaces.return_value.items = [1, 2, 3]
        count = getCronJobCount()
        self.assertEqual(count, 3)

    @patch('dashboard.src.workloads.k8s_cronjobs.configure_k8s')
    @patch('dashboard.src.workloads.k8s_cronjobs.client.BatchV1Api')
    def test_get_cronjobs_status(self, mock_batch_api, mock_configure):
        mock_cronjob_1 = MagicMock()
        mock_cronjob_1.status.active = None
        mock_cronjob_2 = MagicMock()
        mock_cronjob_2.status.active = ['pod1']
        mock_batch_api.return_value.list_cron_job_for_all_namespaces.return_value.items = [mock_cronjob_1, mock_cronjob_2]
        status = getCronJobsStatus('fake-path', 'fake-context')
        self.assertEqual(status, {'Running': 1, 'Completed': 1, 'Count': 2})

    @patch('dashboard.src.workloads.k8s_cronjobs.configure_k8s')
    @patch('dashboard.src.workloads.k8s_cronjobs.client.BatchV1Api')
    @patch('dashboard.src.workloads.k8s_cronjobs.calculateAge', return_value="1d")
    def test_get_cronjobs_list(self, mock_age, mock_batch_api, mock_configure):
        cronjob = MagicMock()
        cronjob.metadata.namespace = "default"
        cronjob.metadata.name = "test-cron"
        cronjob.spec.schedule = "* * * * *"
        cronjob.spec.time_zone = "UTC"
        cronjob.spec.suspend = False
        cronjob.status.active = ['pod1']
        cronjob.status.last_schedule_time = datetime.now(timezone.utc)
        cronjob.metadata.creation_timestamp = datetime.now(timezone.utc)
        mock_batch_api.return_value.list_cron_job_for_all_namespaces.return_value.items = [cronjob]

        jobs = getCronJobsList('path', 'context')
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['name'], 'test-cron')

    @patch('dashboard.src.workloads.k8s_cronjobs.configure_k8s')
    @patch('dashboard.src.workloads.k8s_cronjobs.client.BatchV1Api')
    @patch('dashboard.src.workloads.k8s_cronjobs.filter_annotations', return_value={"custom": "value"})
    def test_get_cronjob_description(self, mock_filter, mock_batch_api, mock_configure):
        cronjob = MagicMock()
        cronjob.metadata.name = "test-cron"
        cronjob.metadata.namespace = "default"
        cronjob.metadata.labels = {"app": "job"}
        cronjob.metadata.annotations = {"internal": "skip"}
        cronjob.spec.schedule = "* * * * *"
        cronjob.spec.concurrency_policy = "Allow"
        cronjob.spec.suspend = False
        cronjob.spec.successful_jobs_history_limit = 3
        cronjob.spec.failed_jobs_history_limit = 1
        cronjob.spec.starting_deadline_seconds = 30
        cronjob.spec.selector.match_labels = {"foo": "bar"}
        cronjob.spec.job_template.spec.template.metadata.labels = {"pod": "label"}
        container = MagicMock()
        container.name = "main"
        container.image = "busybox"
        container.command = ["echo", "hi"]
        container.env = []
        container.volume_mounts = []
        cronjob.spec.job_template.spec.template.spec.containers = [container]
        cronjob.spec.job_template.spec.template.spec.volumes = []
        cronjob.spec.job_template.spec.template.spec.node_selector = {}
        cronjob.spec.job_template.spec.template.spec.tolerations = []
        cronjob.status.active = []
        cronjob.status.last_schedule_time = datetime.now(timezone.utc)

        mock_batch_api.return_value.read_namespaced_cron_job.return_value = cronjob

        result = get_cronjob_description('p', 'c', 'default', 'test-cron')
        self.assertEqual(result['name'], 'test-cron')
        self.assertEqual(result['schedule'], '* * * * *')

    @patch('dashboard.src.workloads.k8s_cronjobs.configure_k8s')
    @patch('dashboard.src.workloads.k8s_cronjobs.client.CoreV1Api')
    def test_get_cronjob_events(self, mock_core_api, mock_configure):
        event1 = MagicMock()
        event1.involved_object.name = "test-cron"
        event1.involved_object.kind = "CronJob"
        event1.reason = "Created"
        event1.message = "CronJob created successfully"
        event2 = MagicMock()
        event2.involved_object.name = "other-cron"
        event2.involved_object.kind = "CronJob"
        mock_core_api.return_value.list_namespaced_event.return_value.items = [event1, event2]

        result = get_cronjob_events('p', 'c', 'ns', 'test-cron')
        self.assertIn("Created: CronJob created successfully", result)

    @patch('dashboard.src.workloads.k8s_cronjobs.configure_k8s')
    @patch('dashboard.src.workloads.k8s_cronjobs.client.BatchV1Api')
    @patch('dashboard.src.workloads.k8s_cronjobs.filter_annotations', return_value={})
    def test_get_yaml_cronjob(self, mock_filter, mock_batch_api, mock_configure):
        cronjob = MagicMock()
        cronjob.to_dict.return_value = {'metadata': {'name': 'test-cron'}}
        cronjob.metadata.annotations = {}
        mock_batch_api.return_value.read_namespaced_cron_job.return_value = cronjob
        result = get_yaml_cronjob('p', 'c', 'ns', 'test-cron')
        self.assertIn('metadata:', result)
        self.assertEqual(yaml.safe_load(result)['metadata']['name'], 'test-cron')


class TestDaemonsetFunctions(TestCase):

    @patch('dashboard.src.workloads.k8s_daemonset.configure_k8s')
    @patch('dashboard.src.workloads.k8s_daemonset.client.AppsV1Api')
    def test_get_daemonset_status(self, mock_apps_api, mock_configure):
        ds1 = MagicMock()
        ds1.status.number_ready = 2
        ds1.status.desired_number_scheduled = 2
        ds1.status.current_number_scheduled = 2

        ds2 = MagicMock()
        ds2.status.number_ready = 1
        ds2.status.desired_number_scheduled = 2
        ds2.status.current_number_scheduled = 2

        mock_apps_api.return_value.list_daemon_set_for_all_namespaces.return_value.items = [ds1, ds2]

        result = getDaemonsetStatus('p', 'c')
        self.assertEqual(result, {'Running': 1, 'Pending': 1, 'Count': 2})

    @patch('dashboard.src.workloads.k8s_daemonset.configure_k8s')
    @patch('dashboard.src.workloads.k8s_daemonset.client.AppsV1Api')
    @patch('dashboard.src.workloads.k8s_daemonset.calculateAge', return_value="1d")
    def test_get_daemonset_list(self, mock_age, mock_apps_api, mock_configure):
        ds = MagicMock()
        ds.metadata.namespace = "default"
        ds.metadata.name = "my-daemon"
        ds.status.desired_number_scheduled = 2
        ds.status.current_number_scheduled = 2
        ds.status.number_ready = 2
        ds.metadata.creation_timestamp = datetime.now(timezone.utc)

        mock_apps_api.return_value.list_daemon_set_for_all_namespaces.return_value.items = [ds]

        result = getDaemonsetList('p', 'c')
        self.assertEqual(result[0]['name'], 'my-daemon')
        self.assertEqual(result[0]['age'], '1d')

    @patch('dashboard.src.workloads.k8s_daemonset.configure_k8s')
    @patch('dashboard.src.workloads.k8s_daemonset.client.AppsV1Api')
    @patch('dashboard.src.workloads.k8s_daemonset.filter_annotations', return_value={'test': 'value'})
    def test_get_daemonset_description(self, mock_filter, mock_apps_api, mock_configure):
        ds = MagicMock()
        ds.metadata.name = 'ds1'
        ds.metadata.namespace = 'default'
        ds.metadata.labels = {'app': 'demo'}
        ds.metadata.annotations = {'internal': 'skip'}
        ds.spec.selector.match_labels = {'k8s-app': 'ds'}
        ds.spec.template.metadata.labels = {'tier': 'backend'}
        ds.spec.template.spec.service_account_name = 'default'
        ds.spec.template.spec.containers = []
        ds.spec.template.spec.volumes = []
        ds.spec.template.spec.priority_class_name = None
        ds.spec.template.spec.node_selector = {}
        ds.spec.template.spec.tolerations = []
        ds.status.conditions = []
        ds.status.desired_number_scheduled = 2
        ds.status.current_number_scheduled = 2
        ds.status.number_ready = 2
        ds.status.number_available = 2

        mock_apps_api.return_value.read_namespaced_daemon_set.return_value = ds

        result = get_daemonset_description('p', 'c', 'ns', 'ds1')
        self.assertEqual(result['name'], 'ds1')
        self.assertIn('template', result)

    @patch('dashboard.src.workloads.k8s_daemonset.configure_k8s')
    @patch('dashboard.src.workloads.k8s_daemonset.client.CoreV1Api')
    def test_get_daemonset_events(self, mock_core_api, mock_configure):
        e1 = MagicMock()
        e1.involved_object.name = "ds1"
        e1.involved_object.kind = "DaemonSet"
        e1.reason = "Created"
        e1.message = "DaemonSet created"

        e2 = MagicMock()
        e2.involved_object.name = "other"
        e2.involved_object.kind = "DaemonSet"

        mock_core_api.return_value.list_namespaced_event.return_value.items = [e1, e2]

        result = get_daemonset_events('p', 'c', 'ns', 'ds1')
        self.assertIn("Created: DaemonSet created", result)

    @patch('dashboard.src.workloads.k8s_daemonset.configure_k8s')
    @patch('dashboard.src.workloads.k8s_daemonset.client.AppsV1Api')
    @patch('dashboard.src.workloads.k8s_daemonset.filter_annotations', return_value={})
    def test_get_daemonset_yaml(self, mock_filter, mock_apps_api, mock_configure):
        ds = MagicMock()
        ds.metadata.annotations = {}
        ds.to_dict.return_value = {'metadata': {'name': 'ds1'}}

        mock_apps_api.return_value.read_namespaced_daemon_set.return_value = ds

        result = get_daemonset_yaml('p', 'c', 'ns', 'ds1')
        self.assertIn('metadata:', result)
        self.assertEqual(yaml.safe_load(result)['metadata']['name'], 'ds1')
        

class TestDeploymentFunctions(TestCase):

    @patch('dashboard.src.workloads.k8s_deployments.configure_k8s')
    @patch('dashboard.src.workloads.k8s_deployments.client.AppsV1Api')
    @patch('dashboard.src.workloads.k8s_deployments.calculateAge', return_value='1d')
    def test_get_deployments_info(self, mock_age, mock_apps_api, mock_configure):
        deployment = MagicMock()
        deployment.metadata.namespace = 'default'
        deployment.metadata.name = 'test-deploy'
        deployment.status.ready_replicas = 2
        deployment.spec.replicas = 3
        deployment.spec.template.spec.containers = [MagicMock(image='nginx:latest')]
        deployment.metadata.creation_timestamp = datetime.now(timezone.utc)

        mock_apps_api.return_value.list_deployment_for_all_namespaces.return_value.items = [deployment]
        result = getDeploymentsInfo('path', 'context')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'test-deploy')

    @patch('dashboard.src.workloads.k8s_deployments.configure_k8s')
    @patch('dashboard.src.workloads.k8s_deployments.client.AppsV1Api')
    def test_get_deployments_status(self, mock_apps_api, mock_configure):
        d1 = MagicMock()
        d1.status.replicas = d1.status.ready_replicas = d1.status.available_replicas = 2

        d2 = MagicMock()
        d2.status.replicas = 2
        d2.status.ready_replicas = 1
        d2.status.available_replicas = 1

        mock_apps_api.return_value.list_deployment_for_all_namespaces.return_value.items = [d1, d2]
        result = getDeploymentsStatus('path', 'context')
        self.assertEqual(result['Running'], 1)
        self.assertEqual(result['Pending'], 1)
        self.assertEqual(result['Count'], 2)

    @patch('dashboard.src.workloads.k8s_deployments.configure_k8s')
    @patch('dashboard.src.workloads.k8s_deployments.client.AppsV1Api')
    @patch('dashboard.src.workloads.k8s_deployments.filter_annotations', return_value={"key": "value"})
    def test_get_deployment_description(self, mock_filter, mock_apps_api, mock_configure):
        dep = MagicMock()
        dep.metadata.name = 'mydeploy'
        dep.metadata.namespace = 'default'
        dep.metadata.labels = {'app': 'web'}
        dep.metadata.annotations = {'internal': 'hide'}
        dep.spec.selector.match_labels = {'app': 'web'}
        dep.status.replicas = 3
        dep.status.updated_replicas = 2
        dep.status.available_replicas = 2
        dep.status.unavailable_replicas = 1
        dep.spec.strategy.type = 'RollingUpdate'
        dep.spec.strategy.rolling_update.max_unavailable = 1
        dep.spec.strategy.rolling_update.max_surge = 1
        dep.spec.min_ready_seconds = 0
        container = MagicMock()
        container.name = 'web'
        container.image = 'nginx'
        container.ports = []
        container.env = []
        container.volume_mounts = []
        dep.spec.template.metadata.labels = {'tier': 'frontend'}
        dep.spec.template.spec.containers = [container]
        dep.spec.template.spec.volumes = []
        dep.spec.template.spec.node_selector = {}
        dep.spec.template.spec.tolerations = []
        dep.status.conditions = []
        dep.status.oldReplicaSets = []
        dep.status.newReplicaSet.name = 'rs-new'

        mock_apps_api.return_value.read_namespaced_deployment.return_value = dep
        result = get_deployment_description('p', 'c', 'ns', 'mydeploy')
        self.assertEqual(result['name'], 'mydeploy')
        self.assertIn('replicas', result)

    @patch('dashboard.src.workloads.k8s_deployments.configure_k8s')
    @patch('dashboard.src.workloads.k8s_deployments.client.CoreV1Api')
    def test_get_deploy_events(self, mock_core_api, mock_configure):
        e1 = MagicMock()
        e1.involved_object.name = 'mydeploy'
        e1.involved_object.kind = 'Deployment'
        e1.reason = 'Created'
        e1.message = 'Deployment created'

        mock_core_api.return_value.list_namespaced_event.return_value.items = [e1]
        result = get_deploy_events('p', 'c', 'ns', 'mydeploy')
        self.assertIn('Created: Deployment created', result)

    @patch('dashboard.src.workloads.k8s_deployments.configure_k8s')
    @patch('dashboard.src.workloads.k8s_deployments.client.AppsV1Api')
    @patch('dashboard.src.workloads.k8s_deployments.filter_annotations', return_value={})
    def test_get_yaml_deploy(self, mock_filter, mock_apps_api, mock_configure):
        deploy = MagicMock()
        deploy.to_dict.return_value = {'metadata': {'name': 'mydeploy'}}
        deploy.metadata.annotations = {}

        mock_apps_api.return_value.read_namespaced_deployment.return_value = deploy
        result = get_yaml_deploy('p', 'c', 'ns', 'mydeploy')
        self.assertIn('metadata:', result)
        self.assertEqual(yaml.safe_load(result)['metadata']['name'], 'mydeploy')

    @patch('dashboard.src.workloads.k8s_deployments.config.load_incluster_config')
    @patch('dashboard.src.workloads.k8s_deployments.config.load_kube_config')
    @patch('dashboard.src.workloads.k8s_deployments.client.AppsV1Api')
    def test_get_deployment_details(self, mock_api, mock_kube_config, mock_incluster_config):
        deployment = MagicMock()
        deployment.metadata.name = 'mydeploy'
        deployment.metadata.namespace = 'default'
        deployment.spec.replicas = 3
        deployment.status.updated_replicas = 2
        deployment.status.available_replicas = 2
        deployment.metadata.creation_timestamp = datetime.now(timezone.utc)

        mock_api.return_value.list_deployment_for_all_namespaces.return_value.items = [deployment]
        result = get_deployment_details()
        self.assertEqual(result[0]['name'], 'mydeploy')
        
class TestK8sJobs(TestCase):

    @patch('dashboard.src.workloads.k8s_jobs.configure_k8s')
    @patch('dashboard.src.workloads.k8s_jobs.client.BatchV1Api')
    def test_get_jobs_status(self, mock_batch_api, mock_configure):
        job1 = MagicMock()
        job1.status.succeeded = 1
        job1.spec.completions = 1
        job1.status.failed = None
        job1.spec.backoff_limit = 2

        job2 = MagicMock()
        job2.status.failed = 3
        job2.spec.backoff_limit = 2
        job2.status.succeeded = None
        job2.spec.completions = 1

        job3 = MagicMock()
        job3.status.succeeded = None
        job3.status.failed = None
        job3.spec.backoff_limit = 2
        job3.spec.completions = 1

        mock_batch_api.return_value.list_job_for_all_namespaces.return_value.items = [job1, job2, job3]
        result = getJobsStatus('path', 'context')

        self.assertEqual(result['Completed'], 1)
        self.assertEqual(result['Failed'], 1)
        self.assertEqual(result['Running'], 1)
        self.assertEqual(result['Count'], 3)

    @patch('dashboard.src.workloads.k8s_jobs.configure_k8s')
    @patch('dashboard.src.workloads.k8s_jobs.client.BatchV1Api')
    @patch('dashboard.src.workloads.k8s_jobs.calculateAge', return_value="1d")
    def test_get_jobs_list(self, mock_age, mock_batch_api, mock_configure):
        job = MagicMock()
        job.metadata.namespace = 'default'
        job.metadata.name = 'test-job'
        job.status.succeeded = 1
        job.spec.completions = 1
        job.status.failed = None
        job.status.completion_time = datetime.now(timezone.utc)
        job.status.start_time = job.status.completion_time - timedelta(minutes=5)
        job.metadata.creation_timestamp = datetime.now(timezone.utc)

        mock_batch_api.return_value.list_job_for_all_namespaces.return_value.items = [job]
        result = getJobsList('path', 'context')
        self.assertEqual(result[0]['name'], 'test-job')
        self.assertEqual(result[0]['status'], 'Completed')

    @patch('dashboard.src.workloads.k8s_jobs.configure_k8s')
    @patch('dashboard.src.workloads.k8s_jobs.client.BatchV1Api')
    @patch('dashboard.src.workloads.k8s_jobs.filter_annotations', return_value={})
    def test_get_job_description(self, mock_filter, mock_batch_api, mock_configure):
        job = MagicMock()
        job.metadata.name = 'job1'
        job.metadata.namespace = 'default'
        job.metadata.labels = {'app': 'demo'}
        job.metadata.annotations = {}
        job.spec.selector.match_labels = {'foo': 'bar'}
        job.spec.parallelism = 1
        job.spec.completions = 1
        job.spec.completion_mode = 'NonIndexed'
        job.spec.suspend = False
        job.spec.backoff_limit = 6
        job.status.start_time = datetime.now(timezone.utc) - timedelta(minutes=10)
        job.status.completion_time = datetime.now(timezone.utc)
        job.status.active = 0
        job.status.succeeded = 1
        job.status.failed = 0
        job.spec.template.metadata.labels = {}

        container = MagicMock()
        container.name = 'main'
        container.image = 'busybox'
        container.command = ['sleep', '30']
        container.env = []
        container.volume_mounts = []
        job.spec.template.spec.containers = [container]
        job.spec.template.spec.volumes = []
        job.spec.template.spec.node_selector = {}
        job.spec.template.spec.tolerations = []

        mock_batch_api.return_value.read_namespaced_job.return_value = job

        result = get_job_description('path', 'context', 'default', 'job1')
        self.assertEqual(result['name'], 'job1')
        self.assertEqual(result['completions'], 1)

    @patch('dashboard.src.workloads.k8s_jobs.configure_k8s')
    @patch('dashboard.src.workloads.k8s_jobs.client.CoreV1Api')
    def test_get_job_events(self, mock_core_api, mock_configure):
        e = MagicMock()
        e.involved_object.name = 'job1'
        e.involved_object.kind = 'Job'
        e.reason = 'Completed'
        e.message = 'Job finished successfully'

        mock_core_api.return_value.list_namespaced_event.return_value.items = [e]

        result = get_job_events('path', 'context', 'ns', 'job1')
        self.assertIn('Completed: Job finished successfully', result)

    @patch('dashboard.src.workloads.k8s_jobs.configure_k8s')
    @patch('dashboard.src.workloads.k8s_jobs.client.BatchV1Api')
    @patch('dashboard.src.workloads.k8s_jobs.filter_annotations', return_value={})
    def test_get_yaml_job(self, mock_filter, mock_batch_api, mock_configure):
        job = MagicMock()
        job.metadata.annotations = {}
        job.to_dict.return_value = {'metadata': {'name': 'job1'}}

        mock_batch_api.return_value.read_namespaced_job.return_value = job

        result = get_yaml_job('p', 'c', 'ns', 'job1')
        self.assertIn('metadata:', result)
        self.assertEqual(yaml.safe_load(result)['metadata']['name'], 'job1')

    @patch('dashboard.src.workloads.k8s_jobs.config.load_kube_config')
    @patch('dashboard.src.workloads.k8s_jobs.client.BatchV1Api')
    def test_get_job_details(self, mock_batch_api, mock_load_config):
        job = MagicMock()
        job.metadata.name = 'job1'
        job.metadata.namespace = 'default'
        job.status.succeeded = 1
        job.metadata.creation_timestamp = datetime.now(timezone.utc) - timedelta(hours=1)
        job.status.start_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        job.status.completion_time = datetime.now(timezone.utc)

        mock_batch_api.return_value.list_job_for_all_namespaces.return_value.items = [job]

        result = get_job_details()
        self.assertEqual(result[0]['name'], 'job1')
        self.assertEqual(result[0]['namespace'], 'default')
        
class TestK8sPods(TestCase):

    @patch('dashboard.src.workloads.k8s_pods.configure_k8s')
    @patch('dashboard.src.workloads.k8s_pods.client.CoreV1Api')
    def test_getpods(self, mock_core_api, mock_configure):
        mock_pod = MagicMock()
        mock_pod.metadata.name = 'pod1'
        mock_core_api.return_value.list_pod_for_all_namespaces.return_value.items = [mock_pod]
        names, count = getpods('path', 'context')
        self.assertEqual(names, ['pod1'])
        self.assertEqual(count, 1)

    @patch('dashboard.src.workloads.k8s_pods.configure_k8s')
    @patch('dashboard.src.workloads.k8s_pods.client.CoreV1Api')
    def test_getPodsStatus(self, mock_core_api, mock_configure):
        pod1 = MagicMock()
        pod1.status.phase = "Succeeded"

        pod2 = MagicMock()
        pod2.status.phase = "Pending"

        pod3 = MagicMock()
        pod3.status.phase = "Running"
        status = MagicMock()
        status.state.running = True
        pod3.status.container_statuses = [status]

        mock_core_api.return_value.list_pod_for_all_namespaces.return_value.items = [pod1, pod2, pod3]

        result = getPodsStatus('p', 'c')
        self.assertEqual(result["Succeeded"], 1)
        self.assertEqual(result["Pending"], 1)
        self.assertEqual(result["Running"], 1)

    def test_getPodStatus(self):
        pod = MagicMock()
        pod.status.phase = "Running"
        status = MagicMock()
        status.state.running = True
        pod.status.container_statuses = [status]
        result = getPodStatus(pod)
        self.assertEqual(result, "Running")

    @patch('dashboard.src.workloads.k8s_pods.configure_k8s')
    @patch('dashboard.src.workloads.k8s_pods.client.CoreV1Api')
    @patch('dashboard.src.workloads.k8s_pods.calculateAge', return_value="1d")
    def test_get_pod_info(self, mock_age, mock_core_api, mock_configure):
        pod = MagicMock()
        pod.metadata.name = 'pod1'
        pod.metadata.namespace = 'default'
        pod.metadata.creation_timestamp = datetime.now(timezone.utc) - timedelta(days=1)
        pod.spec.node_name = 'node1'
        pod.status.pod_ip = '10.0.0.1'
        pod.status.container_statuses = []
        pod.spec.containers = []
        pod.status.phase = "Running"

        mock_core_api.return_value.list_pod_for_all_namespaces.return_value.items = [pod]

        result = get_pod_info('p', 'c')
        self.assertEqual(result[0]['name'], 'pod1')

    @patch('dashboard.src.workloads.k8s_pods.configure_k8s')
    @patch('dashboard.src.workloads.k8s_pods.client.CoreV1Api')
    @patch('dashboard.src.workloads.k8s_pods.filter_annotations', return_value={})
    def test_get_pod_description(self, mock_filter, mock_core_api, mock_configure):
        pod = MagicMock()
        pod.metadata.name = 'pod1'
        pod.metadata.namespace = 'default'
        pod.metadata.annotations = {}
        pod.metadata.labels = {}
        pod.spec.priority = 0
        pod.status.phase = 'Running'
        pod.spec.node_name = 'node1'
        pod.status.pod_ip = '10.0.0.1'
        pod.status.host_ip = '192.168.0.1'
        pod.status.start_time = datetime.now(timezone.utc)
        pod.spec.node_selector = None
        pod.spec.tolerations = None
        pod.spec.service_account_name = 'default'
        pod.spec.containers = []
        pod.spec.volumes = []
        pod.status.conditions = []
        pod.metadata.owner_references = []
        pod.status.container_statuses = []

        mock_core_api.return_value.read_namespaced_pod.return_value = pod

        result = get_pod_description('p', 'c', 'ns', 'pod1')
        self.assertEqual(result['name'], 'pod1')

    @patch('dashboard.src.workloads.k8s_pods.configure_k8s')
    @patch('dashboard.src.workloads.k8s_pods.client.CoreV1Api')
    def test_get_pod_logs(self, mock_core_api, mock_configure):
        mock_core_api.return_value.read_namespaced_pod_log.return_value = "log output"
        logs = get_pod_logs('p', 'c', 'ns', 'pod1')
        self.assertEqual(logs, "log output")

    @patch('dashboard.src.workloads.k8s_pods.configure_k8s')
    @patch('dashboard.src.workloads.k8s_pods.client.CoreV1Api')
    def test_get_pod_events(self, mock_core_api, mock_configure):
        event = MagicMock()
        event.involved_object.name = 'pod1'
        event.reason = 'Scheduled'
        event.message = 'Pod scheduled on node'

        mock_core_api.return_value.list_namespaced_event.return_value.items = [event]

        result = get_pod_events('p', 'c', 'ns', 'pod1')
        self.assertIn('Scheduled: Pod scheduled on node', result)

    @patch('dashboard.src.workloads.k8s_pods.configure_k8s')
    @patch('dashboard.src.workloads.k8s_pods.client.CoreV1Api')
    @patch('dashboard.src.workloads.k8s_pods.filter_annotations', return_value={})
    def test_get_pod_yaml(self, mock_filter, mock_core_api, mock_configure):
        pod = MagicMock()
        pod.metadata.annotations = {}
        pod.to_dict.return_value = {'metadata': {'name': 'pod1'}}

        mock_core_api.return_value.read_namespaced_pod.return_value = pod

        result = get_pod_yaml('p', 'c', 'ns', 'pod1')
        self.assertIn('metadata:', result)
        self.assertEqual(yaml.safe_load(result)['metadata']['name'], 'pod1')

    @patch('dashboard.src.workloads.k8s_pods.config.load_kube_config')
    @patch('dashboard.src.workloads.k8s_pods.client.CoreV1Api')
    def test_get_pod_details(self, mock_core_api, mock_load_config):
        pod = MagicMock()
        pod.metadata.name = 'pod1'
        pod.metadata.namespace = 'default'
        pod.status.phase = 'Running'
        pod.metadata.creation_timestamp = datetime.now(timezone.utc) - timedelta(hours=2)
        pod.spec.node_name = 'node1'
        pod.status.container_statuses = []

        mock_core_api.return_value.list_pod_for_all_namespaces.return_value.items = [pod]

        result = get_pod_details()
        self.assertEqual(result[0]['name'], 'pod1')
        self.assertEqual(result[0]['status'], 'Running')
