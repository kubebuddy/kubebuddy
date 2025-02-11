function deleteCluster(clusterId) {
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

function toggleMonitoring(clusterId) {
    // fetch(`/toggle_monitoring/${clusterId}/`, {
    //     method: 'GET',
    //     headers: {
    //         'X-Requested-With': 'XMLHttpRequest',
    //     },
    // }).then(response => response.json()).then(data => {
    //     if (data.status === 'toggled') {
    //         location.reload();
    //     }
    // });
}
