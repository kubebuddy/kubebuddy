function deleteCluster(event, clusterId) {
    event.stopPropagation();
    fetch(`/delete_cluster/${clusterId}/`, {
        method: 'GET',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
        },
    }).then(response => response.json()).then(data => {
        if (data.status === 'deleted') {
            location.reload();
        }
    });
}

// namesapce filtering
document.addEventListener("DOMContentLoaded", function () {
    document.querySelector("form").addEventListener("submit", function (event) {
        event.preventDefault(); // Prevent default form submission
        let selectedNamespace = document.getElementById("categorySelect").value;
        // Construct the new URL and reload the page with the selected namespace
        let newUrl = `/${current_cluster}/dashboard/?cluster_id=${cluster_id}`;
        if (selectedNamespace !== "all") {
            newUrl += `&namespace=${selectedNamespace}`;
        }

        window.location.href = newUrl;
    });
});