function renderGaugeChart(canvasId, chartData, object_name) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    canvas.width = 280; // Set desired width
    canvas.height = 280; // Set desired height
    const ctx = document.getElementById(canvasId).getContext('2d');
    delete chartData["Count"];
  
    // Define a fixed color mapping for known labels
    const labelColors = {
      "Running": "RGB(50, 205, 50)",
      "Pending": "#ffc107",
      "Failed": "RGB(220, 20, 60)",
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
      return localStorage.getItem("theme") === "dark" ? "#e4e4e4" : "#000000";
    }
    
    // Create an image object for the center of the chart
    const logoImage = new Image();
    logoImage.src = "https://www.thinknyx.com/wp-content/uploads/2025/03/KUBEBUDDY-light.png";
    
    let gaugeChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          label: 'Count',
          data: dataValues,
          backgroundColor: backgroundColors,
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '90%', // Keep the large cutout to create a thin ring
        plugins: {
          legend: {
            display: false
          },
          title: {
            display: true,
            position: 'bottom',
            text: `${object_name} Status Summary`,
            color: getTitleColor(),
            font: {
              size: 20,
              weight: 'normal'
            }
          }
        }
      },
      plugins: [{
        beforeDraw: function(chart) {
          let { width, height, ctx } = chart;
          ctx.save();
          
          // Calculate the inner radius of the donut
          const innerRadius = (chart.chartArea.width / 2) * (chart.options.cutout / 100);
          
          // Make the image smaller - 25% of chart width
          const imgSize = width * 0.25;
          
          // Only draw the image if it's loaded
          if (logoImage.complete) {
            // Draw the image precisely in the center
            ctx.drawImage(
              logoImage,
              width / 2 - imgSize / 2, // X position (centered)
              height / 2 - imgSize / 2, // Y position (centered)
              imgSize, // Width of the image
              imgSize // Height of the image
            );
          } else {
            // Set up the image to draw once it loads
            logoImage.onload = function() {
              ctx.drawImage(
                logoImage,
                width / 2 - imgSize / 2,
                height / 2 - imgSize / 2,
                imgSize,
                imgSize
              );
              chart.update();
            };
          }
          
          ctx.restore();
        }
      }]
    });
  
    document.addEventListener("darkModeChanged", function() {
      gaugeChart.options.plugins.title.color = getTitleColor();
      gaugeChart.update();
    });
  
    window.addEventListener("load", function() {
      gaugeChart.options.plugins.title.color = getTitleColor();
      gaugeChart.update();
    });
  }