function initBreadcrumbNavigation() {
  const breadcrumbContainer = document.querySelector('.breadcrumb');
  
  // Get current URL path and query parameters
  const currentPath = window.location.pathname;
  const queryParams = new URLSearchParams(window.location.search);
  const clusterId = queryParams.get('cluster_id');
  
  // Remove leading slash and split path into segments
  const pathSegments = currentPath.replace(/^\//, '').split('/');
  breadcrumbContainer.innerHTML = '';
  
  // Define display name mapping
  // Add the url routes and associated Name to display on the Navigation Bar
  const displayNameMap = {
      'dashboard': 'Dashboard',
      'pods': 'Pods',
      'replicasets': 'ReplicaSets',
      'deployments': 'Deployments',
      'statefulsets': 'StatefulSets',
      'daemonset': 'DaemonSets',
      'jobs': 'Jobs',
      'cronjobs': 'CronJobs',
      'nodes': 'Nodes',
      'namespace': 'Namespaces',
      'limitrange': 'Limit Ranges',
      'resourcequotas': 'Resource Quotas',
      'pdb': 'Pod Disruption Budgets',
      'services': 'Services',
      'endpoints': 'EndPoints',
      'configmaps': 'ConfigMaps',
      'secrets': 'Secrets',
      'events': 'Events',
      'pv': 'Persistent Volumes',
      'pvc': 'Persistent Volume Claims',
      'storageclass': 'Storage Classes',
      'np': 'Network Policies',
      'ingress': 'Ingress',
      'role': 'Roles',
      'rolebinding': 'Role Bindings',
      'clusterrole': 'Cluster Roles',
      'clusterrolebinding': 'Cluster Role Bindings',
      'serviceAccount': 'Service Accounts',
      'sa': 'Service Accounts',
      'pod_metrics': 'Pod Metrics',
      'node_metrics': 'Node Metrics',
      'certificate': 'Certificates'  
  };

  // Define custom breadcrumb structure
  const breadcrumbs = [];
  
  // First segment always goes to KubeBuddy
  if (pathSegments[0]) {
    // Get display name if it exists, otherwise use original
    const displayText = displayNameMap[pathSegments[0]] || pathSegments[0];
    
    breadcrumbs.push({
      text: displayText,
      url: '/KubeBuddy',
      active: false
    });
  }
  
  // Second segment (if exists)
  if (pathSegments[1]) {
    // Get display name if it exists, otherwise use original
    const displayText = displayNameMap[pathSegments[1]] || pathSegments[1];
    
    breadcrumbs.push({
      text: displayText,
      url: `/${pathSegments[0]}/${pathSegments[1]}`,
      active: false
    });
  }
  
  // Special case: For paths like /docker-desktop/daemonset/demo-namespace/my-daemonset/
  // Combine namespace and resource name into a single breadcrumb
  if (pathSegments[2] && pathSegments[3]) {
    const combinedText = `${pathSegments[2]}/${pathSegments[3]}`;
    breadcrumbs.push({
      text: combinedText,
      url: `/${pathSegments[0]}/${pathSegments[1]}/${pathSegments[2]}/${pathSegments[3]}`,
      active: true
    });
  } else if (pathSegments[2]) {
    // Handle case where there's only a third segment
    // Get display name if it exists, otherwise use original
    const displayText = displayNameMap[pathSegments[2]] || pathSegments[2];
    
    breadcrumbs.push({
      text: displayText,
      url: `/${pathSegments[0]}/${pathSegments[1]}/${pathSegments[2]}`,
      active: true
    });
  }
  
  // Create breadcrumb items from our custom structure
  breadcrumbs.forEach((crumb, index) => {
    const listItem = document.createElement('li');
    listItem.className = 'breadcrumb-item';
    
    if (crumb.active || index === breadcrumbs.length - 1) {
      listItem.classList.add('active');
      listItem.setAttribute('aria-current', 'page');
      listItem.textContent = crumb.text;
    } else {
      // Create link for non-active items
      const link = document.createElement('a');
      
      let href = crumb.url;
      if (clusterId) {
        href += `?cluster_id=${clusterId}`;
      }
      
      link.href = href;
      link.textContent = crumb.text;
      link.className = 'text-decoration-none';
      
      link.addEventListener('click', function(e) {
        e.preventDefault();
        window.location.href = href;
      });
      
      listItem.appendChild(link);
    }
    
    breadcrumbContainer.appendChild(listItem);
  });
  
  if (breadcrumbContainer.children.length === 0) {
    const breadcrumbNav = document.querySelector('[aria-label="breadcrumb"]');
    if (breadcrumbNav) {
      breadcrumbNav.style.display = 'none';
    }
  }
}

document.addEventListener('DOMContentLoaded', initBreadcrumbNavigation);
window.addEventListener('popstate', initBreadcrumbNavigation);