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
