function renderGaugeChart(canvasId, chartData, object_name) {
    const canvas = document.getElementById(canvasId);
    canvas.width = 280;  // Set desired width
    canvas.height = 280; // Set desired height
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

    function getTitleColor() {
        return document.body.classList.contains("dark-mode") ? "#e4e4e4" : "#000000";
    }

    let gaugeChart = new Chart(ctx, {
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
            responsive: true,
            maintainAspectRatio: false,
            cutout: '90%',
            plugins: {
                legend: { display: false },
                title: {
                    display: true,
                    position: 'bottom',
                    text:  `${object_name} Status Summary`,
                    color: getTitleColor(),
                    font: {
                        size: 20,
                        weight: 'normal'
                    }
                }
            }
        },
        plugins: [{
            beforeDraw: function (chart) {
                let { width, height, ctx } = chart;
                ctx.save();

                // Set font size based on chart size
                let fontSize = (height / 10).toFixed(2); // Adjusted for better scaling
                ctx.font = fontSize + "px sans-serif";
                ctx.textAlign = "center"; // Center text horizontally
                ctx.textBaseline = "middle"; // Center text vertically

                let text = "KB";
                let textX = width / 2; // Middle of the canvas
                let textY = height / 2; // Middle of the canvas

                ctx.fillText(text, textX, textY);
                ctx.restore();
            }
        }]
    });
    document.addEventListener("darkModeChanged", function () {
        gaugeChart.options.plugins.title.color = getTitleColor();
        gaugeChart.update();
    });
}