// Initialize charts
function createStatChart(ctx, label, unit) {
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: label,
                data: [],
                borderWidth: 1,
                borderColor: 'rgba(0,0,0,0)',
                backgroundColor: 'rgba(0,0,0,0)'
            }]
        },
        options: {
            responsive: true,
            animation: false,
            scales: {
                x: { 
                    display: true,
                    title: { display: true, text: 'Time' },
                    grid: {
                        display: true,
                        color: 'rgba(0,0,0,0.1)'
                    }
                },
                y: { 
                    display: true,
                    title: { display: true, text: unit },
                    grid: {
                        display: true,
                        color: 'rgba(0,0,0,0.1)'
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    enabled: true,
                    callbacks: {
                        label: function(context) {
                            const stat = context.raw;
                            return [
                                `First: ${stat.first} ${unit}`,
                                `Last: ${stat.last} ${unit}`,
                                `Min: ${stat.minimum} ${unit}`,
                                `Max: ${stat.maximum} ${unit}`,
                                `Avg: ${stat.y} ${unit}`
                            ];
                        }
                    }
                }
            }
        }
    });
}

// Initialize chart contexts
const tempCtx = document.getElementById('tempChart').getContext('2d');
const co2Ctx = document.getElementById('co2Chart').getContext('2d');

// Create charts
const tempChart = createStatChart(tempCtx, 'Temperature', '°C');
const co2Chart = createStatChart(co2Ctx, 'CO2', 'ppm');

// Update chart with data
function updateChart(chart, data) {
    if (!data || !data.timestamps || !data.stats || data.timestamps.length === 0) {
        console.log("No data to display");
        return;
    }

    console.log("Updating chart with data:", data);

    // Calculate Y-axis range
    const allValues = data.stats.reduce((acc, stat) => {
        acc.push(stat.minimum, stat.maximum, stat.first, stat.last);
        return acc;
    }, []);
    const minValue = Math.min(...allValues);
    const maxValue = Math.max(...allValues);
    const padding = (maxValue - minValue) * 0.1;

    // Update chart data
    chart.data.labels = data.timestamps;
    chart.data.datasets = [{
        label: chart.canvas.id === 'tempChart' ? 'Temperature' : 'CO2',
        data: data.stats.map((stat, i) => ({
            x: i,
            y: stat.average,
            minimum: stat.minimum,
            maximum: stat.maximum,
            first: stat.first,
            last: stat.last
        })),
        borderColor: 'rgba(0,0,0,0)',
        backgroundColor: 'rgba(0,0,0,0)'
    }];

    chart.options.scales.y.min = minValue - padding;
    chart.options.scales.y.max = maxValue + padding;

    // Update without animation
    chart.update('none');

    // Custom drawing
    const ctx = chart.ctx;
    const yScale = chart.scales.y;
    const xScale = chart.scales.x;

    data.stats.forEach((stat, i) => {
        const x = xScale.getPixelForValue(i);
        const width = xScale.getPixelForValue(1) - xScale.getPixelForValue(0);
        const candleWidth = Math.min(width * 0.8, 15);  // Limit candle width

        // Determine color based on first/last values
        const color = stat.first <= stat.last ? 'blue' : 'red';

        // Draw whiskers (min to max)
        ctx.beginPath();
        ctx.strokeStyle = color;
        ctx.lineWidth = 1;
        ctx.moveTo(x, yScale.getPixelForValue(stat.minimum));
        ctx.lineTo(x, yScale.getPixelForValue(stat.maximum));
        ctx.stroke();

        // Draw box (first to last)
        const firstY = yScale.getPixelForValue(stat.first);
        const lastY = yScale.getPixelForValue(stat.last);
        const boxTop = Math.min(firstY, lastY);
        const boxHeight = Math.abs(firstY - lastY) || 1;

        ctx.fillStyle = color;
        ctx.fillRect(x - candleWidth/2, boxTop, candleWidth, boxHeight);
    });
}

// Fetch data from API
async function fetchData() {
    try {
        const res = await fetch('/stats');
        const json = await res.json();
        
        updateChart(tempChart, json.temperature);
        updateChart(co2Chart, json.co2);
    } catch (error) {
        console.error('Error fetching data:', error);
    }
}

// Initial data fetch
fetchData();
// Update every 10 seconds
setInterval(fetchData, 10000);
