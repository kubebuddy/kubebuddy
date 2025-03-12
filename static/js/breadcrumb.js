// Function to initialize breadcrumb navigation
function initBreadcrumbNavigation() {
    const breadcrumbContainer = document.querySelector('.breadcrumb');
    
    // Get current URL path and query parameters
    const currentPath = window.location.pathname;
    const queryParams = new URLSearchParams(window.location.search);
    const clusterId = queryParams.get('cluster_id');
    
    // Remove leading slash and split path into segments
    const pathSegments = currentPath.replace(/^\//, '').split('/');
    
    // Clear any existing breadcrumbs
    breadcrumbContainer.innerHTML = '';
  
    // Define custom breadcrumb structure
    const breadcrumbs = [];
    
    // First segment always goes to KubeBuddy
    if (pathSegments[0]) {
      breadcrumbs.push({
        text: pathSegments[0],
        url: '/KubeBuddy',
        active: false
      });
    }
    
    // Second segment (if exists)
    if (pathSegments[1]) {
      breadcrumbs.push({
        text: pathSegments[1],
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
      breadcrumbs.push({
        text: pathSegments[2],
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
        
        // Add cluster_id if it exists
        let href = crumb.url;
        if (clusterId) {
          href += `?cluster_id=${clusterId}`;
        }
        
        link.href = href;
        link.textContent = crumb.text;
        link.className = 'text-decoration-none';
        
        // Add click event listener
        link.addEventListener('click', function(e) {
          e.preventDefault();
          window.location.href = href;
        });
        
        listItem.appendChild(link);
      }
      
      // Add to breadcrumb container
      breadcrumbContainer.appendChild(listItem);
    });
    
    // If no breadcrumb items were added, hide the breadcrumb
    if (breadcrumbContainer.children.length === 0) {
      const breadcrumbNav = document.querySelector('[aria-label="breadcrumb"]');
      if (breadcrumbNav) {
        breadcrumbNav.style.display = 'none';
      }
    }
  }
  
  // Initialize breadcrumbs when DOM is loaded
  document.addEventListener('DOMContentLoaded', initBreadcrumbNavigation);
  
  // Update breadcrumbs when URL changes
  window.addEventListener('popstate', initBreadcrumbNavigation);