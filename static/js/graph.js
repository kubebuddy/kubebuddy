function renderGaugeChart(canvasId, chartData, object_name) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  canvas.width = 280;  // Set desired width
  canvas.height = 280; // Set desired height
  const ctx = document.getElementById(canvasId).getContext('2d');
  delete chartData["Count"];
  // Define a fixed color mapping for known labels
  const labelColors = {
      "Running": "#32CD32",
      "Pending": "#ffc107",
      "Failed": "#DC143C",
      "Succeeded": "#0dcaf0",
      "Completed": "#0dcaf0",
      "Total": "#007bff",
      "Ready": "#32CD32",
      "Not Ready": "#DC143C"
  };

  // Get labels and data dynamically
  const labels = Object.keys(chartData);
  const dataValues = Object.values(chartData);
  // Assign colors based on labels, fallback to a random color if not in labelColors
  const backgroundColors = labels.map(label => labelColors[label] || "#6c757d");

  function getTitleColor() {
      return localStorage.getItem("theme") === "dark" ? "#e4e4e4" : "#000000";
  }

  let gaugeChart = new Chart(ctx, {
      type: 'pie',
      data: {
          labels: labels,
          datasets: [{
              label: 'Count',
              data: dataValues,
              backgroundColor: backgroundColors,
              borderWidth: 1,
          }],
          
      },
      options: {
          responsive: true,
          maintainAspectRatio: false,
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
  });
  
  document.addEventListener("darkModeChanged", function () {
      gaugeChart.options.plugins.title.color = getTitleColor();
      gaugeChart.update();
  });
  window.addEventListener("load", function () {
      gaugeChart.options.plugins.title.color = getTitleColor();
      gaugeChart.update();
  });
}