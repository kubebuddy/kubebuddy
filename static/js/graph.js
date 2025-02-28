function renderGaugeChart(canvasId, chartData, object_name) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    delete chartData["Count"];
    // Define a fixed color mapping for known labels
    const labelColors = {
        "Running": "#198754",
        "Pending": "#ffc107",
        "Failed": "#dc3545",
        "Succeeded": "#0dcaf0",
        "Completed": "#0dcaf0",
        "Total": "#007bff",
        "Ready": "#198754",
        "Not Ready": "#dc3545"
    };

    // Get labels and data dynamically
    const labels = Object.keys(chartData);
    const dataValues = Object.values(chartData);

    // Assign colors based on labels, fallback to a random color if not in labelColors
    const backgroundColors = labels.map(label => labelColors[label] || "#6c757d");

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                label: 'Count',
                data: dataValues,
                backgroundColor: backgroundColors,
            }]
        },
        options: {
            rotation: -90,
            circumference: 180,
            cutout: '90%',
            plugins: {
                legend: { display: false },
                title: {
                    display: true,
                    position: 'bottom',
                    text:  `${object_name} Status Summary`,
                    color: '#e4e4e4',
                    font: {
                        size: 20,
                        weight: 'normal'
                    }
                }
            }
        },
        plugins: [{
            beforeDraw: function (chart) {
                let width = chart.width,
                    height = chart.height,
                    ctx = chart.ctx;

                ctx.restore();
                let fontSize = (height / 120).toFixed(2);
                ctx.font = fontSize + "em sans-serif";
                ctx.textBaseline = "middle";

                let text = "KB";
                let textX = Math.round((width - ctx.measureText(text).width) / 2);
                let textY = height / 1.8;

                ctx.fillText(text, textX, textY);
                ctx.save();
            }
        }]
    });
}