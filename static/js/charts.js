// Custom plugin for candlestick rendering
const candlestickPlugin = {
    id: 'candlestick',
    afterDatasetsDraw: function(chart, args, options) {
        const ctx = chart.ctx;
        const yScale = chart.scales.y;
        const xScale = chart.scales.x;
        const dataset = chart.data.datasets[0];

        dataset.data.forEach((stat, i) => {
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
};

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
                borderColor: 'transparent',
                backgroundColor: 'transparent'
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
                                `Avg: ${stat.y} ${unit}`,
                                stat.count ? `Count: ${stat.count} samples` : ''
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

// Register custom plugin
Chart.register(candlestickPlugin);

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
            last: stat.last,
            count: stat.count
        })),
        borderColor: 'rgba(0,0,0,0)',
        backgroundColor: 'rgba(0,0,0,0)'
    }];

    chart.options.scales.y.min = minValue - padding;
    chart.options.scales.y.max = maxValue + padding;

    // Update without animation
    chart.update('none');
}

// Global variable to store current interval
let currentInterval = '1min';

// Function to change interval
function changeInterval(interval) {
    currentInterval = interval;
    fetchData();
}

// Fetch data from API
async function fetchData() {
    try {
        const res = await fetch(`/stats?interval=${currentInterval}`);
        const json = await res.json();
        
        updateChart(tempChart, json.temperature);
        updateChart(co2Chart, json.co2);
        
        // Update chart titles with interval information
        const intervalText = {
            '1min': '1 Minute',
            '10min': '10 Minutes',
            '1hour': '1 Hour',
            '1day': '1 Day'
        }[currentInterval];
        
        document.querySelector('#tempChart').closest('.chart-container').querySelector('h2')
            .textContent = `Temperature Statistics (°C) - ${intervalText} Intervals`;
        document.querySelector('#co2Chart').closest('.chart-container').querySelector('h2')
            .textContent = `CO2 Statistics (ppm) - ${intervalText} Intervals`;
    } catch (error) {
        console.error('Error fetching data:', error);
    }
}

// Initial data fetch
fetchData();

// Update interval based on data frequency
const updateIntervals = {
    '1min': 10000,    // 10 seconds
    '10min': 30000,   // 30 seconds
    '1hour': 60000,   // 1 minute
    '1day': 300000    // 5 minutes
};

// Function to manage update interval
function startUpdateInterval() {
    const interval = updateIntervals[currentInterval];
    return setInterval(fetchData, interval);
}

let updateTimer = startUpdateInterval();

// Update timer when interval changes
document.getElementById('interval').addEventListener('change', function() {
    clearInterval(updateTimer);
    updateTimer = startUpdateInterval();
});
