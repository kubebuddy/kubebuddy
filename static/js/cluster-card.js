const createVerticalBarChart = (id, percentage, color) => {
    new Chart(document.getElementById(id), {
        type: 'bar',
        data: {
            labels: [''],
            datasets: [{
                data: [percentage],
                backgroundColor: color,
                barThickness: 50
            }]
        },
        options: {
            responsive: false,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true, max: 100 } }
        }
    });
};

createVerticalBarChart('cluster-cpuUsageChart', 60, 'red');
createVerticalBarChart('cluster-memoryUsageChart', 50, 'green');
