from flask import Flask, render_template_string, jsonify
from threading import Thread
import time
import json
import queue
import paho.mqtt.client as mqtt

app = Flask(__name__)
sensor_data_queue = queue.Queue(maxsize=100)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Sensor Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <h2>Live Temperature Data</h2>
    <canvas id="tempChart" width="800" height="400"></canvas>
    <script>
        const ctx = document.getElementById('tempChart').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Temperature (°C)',
                    data: [],
                    borderColor: 'blue',
                    fill: false
                }]
            },
            options: {
                scales: {
                    x: { display: true, title: { display: true, text: 'Timestamp' }},
                    y: { display: true, title: { display: true, text: '°C' }}
                }
            }
        });

        async function fetchData() {
            const res = await fetch('/data');
            const json = await res.json();
            chart.data.labels = json.timestamps;
            chart.data.datasets[0].data = json.temperatures;
            chart.update();
        }

        setInterval(fetchData, 2000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/data')
def get_data():
    temperatures = []
    timestamps = []
    for item in list(sensor_data_queue.queue):
        for reading in item['readings']:
            if reading['type'] == 'temperature':
                temperatures.append(reading['value'])
                timestamps.append(item['timestamp'])
    return jsonify({'temperatures': temperatures, 'timestamps': timestamps})

def mqtt_listener():
    def on_connect(client, userdata, flags, rc):
        client.subscribe("home/livingroom/env/sensor1")

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            if sensor_data_queue.full():
                sensor_data_queue.get()
            sensor_data_queue.put(payload)
        except Exception as e:
            print("Error:", e)

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("127.0.0.1", 1883, 60)
    client.loop_forever()

# MQTTを別スレッドで開始
Thread(target=mqtt_listener, daemon=True).start()

# Flask起動
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
