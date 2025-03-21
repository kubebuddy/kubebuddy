document.addEventListener('DOMContentLoaded', function() {

    async function fetchClusterStatus(cluster) {
        try {
            const response = await fetch(`/get_cluster_status/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: JSON.stringify(cluster),
            });
    
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
    
            const data = await response.json();
            // now change data in html
            updateClusterCard(data.received_data);
        } catch (error) {
            console.error("Error fetching cluster status:", error);
        }
    }

    function updateClusterCard(clusterData) {
        const clusterElement = document.getElementById(clusterData.id);
        if (!clusterElement) {
            console.warn(`Cluster card with ID ${clusterData.id} not found.`);
            return;
        }

        // Updating cluster information
        clusterElement.querySelector("span#cluster_nodes").innerText = clusterData.number_of_nodes;
        
        // Updating Control Plane status
        const controlPlaneElement = clusterElement.querySelector("p:nth-child(3) span");
        controlPlaneElement.textContent = clusterData.control_plane_status || "Checking...";
        controlPlaneElement.classList.remove("text-primary");
        controlPlaneElement.classList.add(clusterData.control_plane_status === "Running" ? "text-success" : "text-danger")

        // Updating CoreDNS status
        const coreDNSElement = clusterElement.querySelector("p:nth-child(4) span");
        coreDNSElement.textContent = clusterData.core_dns_status || "Checking...";
        coreDNSElement.classList.remove("text-primary");
        coreDNSElement.classList.add(clusterData.core_dns_status === "Running" ? "text-success" : "text-danger")

        // update styling of cards and links
        clusterElement.querySelector("a").href = (clusterData.core_dns_status === 'Running' && clusterData.control_plane_status === 'Running') ? `/${clusterData.cluster_name}/dashboard?cluster_id=${clusterData.id}` : `/${clusterData.cluster_name}/cluster_error`;
        clusterElement.querySelector("a").style.pointerEvents = (clusterData.core_dns_status === 'Running' && clusterData.control_plane_status === 'Running') ? 'auto' : 'auto';
        clusterElement.querySelector("a").style.cursor = (clusterData.core_dns_status === 'Running' && clusterData.control_plane_status === 'Running') ? 'pointer' : 'pointer';

        const cardHeader = clusterElement.querySelector("#card-head");
        if (cardHeader) {
            cardHeader.classList.remove("bg-secondary");

            if (clusterData.core_dns_status === 'Running' && clusterData.control_plane_status === 'Running') {
                cardHeader.classList.add("bg-success", "text-white"); // Green background for healthy clusters
            } else {
                cardHeader.classList.add("bg-danger", "text-white"); // Red background for uunavailable clusters
            }
        } else {
            console.warn(`Card header not found for cluster ${clusterData.id}`);
        }

        // tooltip for statuses
        
    }

    clusters.forEach((cluster) => {
        fetchClusterStatus(cluster);
    });
});